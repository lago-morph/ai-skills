---
name: skill-registry
description: Manage the ai-skills registry. Sweeps tracked external repositories for new skills, skill specs, ADRs, and agents-md instructions; reconciles them against the registry by emitting per-item semantic-diff reports into /incoming/; walks the user through dispositions (discard, replace, merge, add-as-new) and updates the per-artifact-type ledger. Also self-bootstraps the four GitHub Actions that auto-regenerate ledger.md files on push to main. Use ONLY from inside the ai-skills registry repo. Triggered by "sweep skills", "sweep remotes", "ingest skills", "reconcile incoming", "process incoming", "check registry", "pull skills from tracked repos", "semantic-diff", "skill registry", or any combination thereof. The skill has four modes (sweep, reconcile, process-incoming, semantic-diff) plus an always-on workflow-installer pre-step.
---

# Skill: skill-registry

Manages the registry repository (`lago-morph/ai-skills`). Implements the
v1 system described in `resources/skill-management-v1.md` (a copy of the
spec, shipped with the skill so it remains self-contained). Read that
document first if you have not already — it is the source of truth.

## When to use

Use ONLY when running inside the `ai-skills` registry repo itself. From a
consumer repo, use `skill-sync` instead.

Triggers (any combination of these activates this skill):

- "sweep skills" / "sweep remotes" / "pull skills from tracked repos"
- "ingest skills" / "check registry"
- "reconcile incoming"
- "process incoming"
- "semantic-diff"
- "skill registry"

## Four modes + pre-step

| Mode | Script | Interactive? | Touches ledger? |
|------|--------|--------------|-----------------|
| (always) install-workflows | `scripts/install_workflows.py` | no | no |
| sweep | `scripts/sweep.py` | no | no |
| reconcile | `scripts/reconcile.py` | no | no |
| process-incoming | `scripts/process_incoming.py` | **yes** | **yes** |
| semantic-diff | `scripts/semantic_diff.py` | no | no |

### Pre-step: install-workflows

**Always run first**, on every invocation, in every mode:

```
python .claude/skills/skill-registry/scripts/install_workflows.py
```

This compares the workflow templates under `resources/_workflows/` (with
`__SKILL_PATH__` substituted) against `.github/workflows/` and copies in
any missing or differing files. Idempotent on a steady state. See
`resources/_workflows/` for the four ledger-render workflows plus the
test workflow.

### Mode 1: sweep

```
python .claude/skills/skill-registry/scripts/sweep.py
```

Loads `resources/registry-config.json`, schema-lints, then for each repo:
1. `git clone --depth 1` into `/tmp/skill-sweep-<id>/<org>/<repo>/`.
2. For each artifact type, walk the configured glob patterns.
3. Hash each candidate, look up in the registry ledger.
4. Copy unknown items into `/incoming/<org>/<repo>/<type>/...`.
5. Auto-invoke reconcile at the end.

The current registry repo itself is one of the tracked repos. The sweep
points at the **consumer-side** paths within this repo
(`.claude/skills/*/`, `.claude/agents-md/*.md`, `ai/adr/*.md`,
`retrospective/*/AGENTS-MD-*.md`, `retrospective/*/SKILL-SPEC-*.md`,
`retrospective/*/ADR-*.md`) — NOT the registry storage locations.

Per-repo path overrides are strict per-key replace: declare one path,
the rest fall through to defaults.

Filename patterns accepted for single-file types:
- pre-ingestion: `SKILL-SPEC-<10hex>-<kebab>.md`, etc. (the 10-hex UID is
  preserved through `/incoming/` and STRIPPED at promotion)
- registry: `<kebab>.md`

### Mode 2: reconcile

```
python .claude/skills/skill-registry/scripts/reconcile.py
```

Batch, non-interactive. For every artifact in `/incoming/`:
1. Run `semantic_diff.run()` to produce a markdown report.
2. Write `<name>-semantic-diff.md` next to the incoming artifact.

Never modifies the ledger. Idempotent: if a report already exists, it is
left alone. Re-run any time without consequence.

### Mode 3: process-incoming

This is the one mode that requires the agent and the user to talk to
each other. Drive it like this:

1. Run `list_pending(repo_root)` from `process_incoming.py` to enumerate
   pending items.
2. For each item:
   a. Read the semantic-diff report. If "## AI analysis" and "##
      Disposition recommendation" sections are placeholders, fill them
      in by inspecting both the incoming and the registry version of the
      artifact and reasoning about it.
   b. Present the item to the user with **AskUserQuestion**. The choices:
      - **discard** — never offer this artifact again from any source.
      - **replace** — overwrite the registry version with the incoming.
      - **merge** — propose a combined version, walk user through each
        delta. Write the merged result to a tmp file, then call
        `disposition_merge` with `merge_result_path=`.
      - **add-as-new** — when the name doesn't exist yet OR the user
        wants to fork to a new kebab name to resolve a clash.
   c. For `replace`, `merge`, or `add-as-new`, ask for a semver bump
      (patch / minor / major) or a literal version. For `add-as-new`,
      offer `0.1.0` and `1.0.0` as defaults. Validate strictly-greater
      for replace/merge.
   d. For `replace` and `merge`, also decide whether to refresh the
      ledger `description` field. Apply the rule from
      `resources/skill-management-v1.md` §5.3: keep current description
      if still accurate; rewrite only when it would otherwise become stale.
   e. Call `apply_disposition(repo_root, item, "<choice>", ...)`. This
      installs the artifact, updates the ledger atomically, and removes
      both the `/incoming/` entry and the semantic-diff report.

Special cases the agent must handle gracefully:

- **kebab-name clash**: if the incoming item has the same kebab as an
  existing registry artifact but is semantically different, offer
  `add-as-new` with a user-supplied alternative name. This automatically
  records `name_clash: [<alt-name>]` on the **original** entry only
  (one-way pointer — see spec §5.4). On future sweeps the dedup walker
  will skip incoming items whose hash matches the alt-name's ledger.
- **renamed-clash item modified downstream**: if a sweep notices that a
  name-clash item has been edited locally, surface a one-line notice
  ("name-clash item `<alt>` from `<source>` has been edited locally;
  consider renaming or removing the source"). Do not block, do not open
  a separate process step — it is a notice.
- **`merged` / `implemented` ledger states**: those items should never
  appear in `/incoming/` (the dedup walker filters them). If one does,
  refuse and explain.

### Mode 4: semantic-diff (direct invocation)

```
python .claude/skills/skill-registry/scripts/semantic_diff.py \
    <type> <registry-path-or-"-"> <incoming-path> [--org O] [--repo R]
```

Produces the same markdown report `reconcile` writes, but to stdout. Use
for ad-hoc comparisons.

## Configuration

User config: `resources/registry-config.json` (schema-linted; excluded
from this skill's content hash via `hash_exclude`).

Template:    `resources/registry-config-template.json`. When the skill
is freshly installed in a new place and no user config exists, the
template is copied in.

The user config can be edited freely; it is NEVER overwritten by sync.

Schema: `resources/schemas/registry-config.schema.json`.

## Files in this skill

```
SKILL.md                          this file
resources/
  skill-management-v1.md          v1 spec (canonical in-skill copy)
  registry-config.json            user config (hash-excluded)
  registry-config-template.json   default template
  schemas/
    ledger.schema.json
    skill-metadata.schema.json
    single-file-metadata.schema.json
    registry-config.schema.json
  _workflows/                     GH Action templates ( __SKILL_PATH__ placeholder)
    regen-skills-ledger-md.yml
    regen-skill-specs-ledger-md.yml
    regen-adrs-ledger-md.yml
    regen-agents-md-ledger-md.yml
    test-skill-registry.yml
scripts/
  canonical_json.py        canonical JSON dump/load (sort keys + per-spec arrays)
  hash_skill.py            Option A skill-directory hash
  hash_single_file.py      strip-first-line sha256
  validate.py              JSON Schema validators
  render_ledger.py         JSON -> 000-ledger.md
  install_workflows.py     copies _workflows/ into .github/workflows/
  sweep.py                 mode 1
  reconcile.py             mode 2
  semantic_diff.py         mode 4 (also called by mode 2)
  process_incoming.py      mode 3 helpers
tests/
  test_canonical_json.py   jq-parity + array-sort fixtures
  test_hash_skill.py       Option A behavior (incl. rename detection)
  test_hash_single_file.py round-trip + modification detection
  test_validate.py         schema lint fail modes
```

## Hard rules

1. **All JSON written by any script in this skill goes through
   `canonical_json.write` or `canonical_json.dumps`.** Never `json.dump`
   directly — that bypasses key/array sorting.
2. **Every read of a JSON file owned by the registry validates against
   the appropriate schema before use.** `validate.validate(kind, data)`.
3. **No script in this skill calls an LLM.** Where reasoning is needed
   (description regeneration, "## AI analysis" section, merge proposal),
   the agent does it directly using the tools at its disposal. Keeping
   scripts deterministic is what lets the tests assert byte-equality.
4. **Filename pre-ingestion UIDs are immutable in `/incoming/`.** They
   are stripped at promotion time, never recomputed.
5. **State transitions (`live` → `deprecated` / `merged` /
   `implemented`) are manual in v1.** A future v1.x skill will automate
   them.
