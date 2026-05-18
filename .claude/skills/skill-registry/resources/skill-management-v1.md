# Skill Management — v1 Specification

**Status:** Approved (conversation-derived). Pre-implementation.
**Scope:** v1 is skill-only (no SPA). The graphical system from `skill-manager-spec.md` is deferred to v2.
**Audience:** the agent implementing this, and the human reviewing it.

This document is the single source of truth for the v1 design. It supersedes
`skill-manager-spec.md` and `use-cases-spec.md` for v1 purposes; both of those
move to `/skill-specs/` to be re-evaluated as inputs to v2.

---

## 1. Concept

This repository (`lago-morph/ai-skills`) is the **registry** for four kinds of
artifact:

| Type        | Registry storage    | Single-file? | Filename in registry             |
|-------------|---------------------|--------------|----------------------------------|
| skill       | `/skills/<name>/`   | no (dir)     | dir named `<kebab-name>`         |
| skill-spec  | `/skill-specs/`     | yes          | `<kebab-name>.md`                |
| ADR         | `/adrs/`            | yes          | `<kebab-name>.md`                |
| agents-md   | `/agents-md/`       | yes          | `<kebab-name>.md`                |

Other repositories ("consumers") subscribe to a subset of these artifacts and
keep them in sync via the `skill-sync` skill. Authoring happens in the registry;
consumers receive copies.

Two skills implement the system, both authored in `.claude/skills/` so that the
first sweep folds them into the registry naturally:

- **`skill-registry`** — bundled. Sweeps tracked repos for new artifacts,
  reconciles incoming items against the registry, walks the user through
  decisions. Used **only** from inside the registry repo.
- **`skill-sync`** — standalone. Used in **consumer** repos (and in this repo
  for self-sync) to install/upgrade subscribed artifacts and regenerate
  `AGENTS.md` / `CLAUDE.md`.

---

## 2. Repository layout

```
/skills/
  000-ledger.json              ledger for skills (auto-rendered)
  000-ledger.md                rendered ledger
  <kebab-name>/
    SKILL.md
    resources/
      000-metadata.json        REGISTRY METADATA. excluded from hash.
    …                          all other files included in hash

/skill-specs/
  000-ledger.json
  000-ledger.md
  <kebab-name>.md              first line = single-line JSON metadata

/adrs/
  000-ledger.json
  000-ledger.md
  <kebab-name>.md              first line = single-line JSON metadata

/agents-md/
  000-ledger.json
  000-ledger.md
  <kebab-name>.md              first line = single-line JSON metadata,
                               then `# agent instruction`, then optional
                               other H1 sections (preserved but stripped
                               from AGENTS.md regeneration)

/incoming/
  .gitkeep
  <source-org>/<source-repo>/
    skills/<name>/             new skill candidate
    skills/<name>-semantic-diff.md
    skill-specs/<name>.md
    skill-specs/<name>-semantic-diff.md
    adrs/<name>.md
    adrs/<name>-semantic-diff.md
    agents-md/<name>.md
    agents-md/<name>-semantic-diff.md

/.claude/skills/
  skill-registry/              authoring location (until first sweep folds it in)
    SKILL.md
    resources/
      registry-config-template.json
      registry-config.json     user-edited; never overwritten by sync
      schemas/
        ledger.schema.json
        skill-metadata.schema.json
        single-file-metadata.schema.json
        registry-config.schema.json
      _workflows/
        regen-skills-ledger-md.yml
        regen-skill-specs-ledger-md.yml
        regen-adrs-ledger-md.yml
        regen-agents-md-ledger-md.yml
    scripts/
      render-ledger.py
      install-workflows.py
      canonical_json.py
      sweep.py
      reconcile.py
      semantic_diff.py
      process_incoming.py
      hash_skill.py
      hash_single_file.py
      validate_*.py

  skill-sync/
    SKILL.md
    resources/
      skill-sync-config-template-claude.json
      skill-sync-config-template-codex.json
      skill-sync-config.json   user-edited; never overwritten by sync
      claude-md-template.md    CLAUDE.md template with bold-red banner
      agents-md-template.md    AGENTS.md banner header
      schemas/
        skill-sync-config.schema.json
    scripts/
      skill_sync.py
      regen_agents_md.py
      regen_claude_md.py
      canonical_json.py        (shared with skill-registry; duplicated per skill)
      validate_*.py

/ai/
  skill-management-v1.md       this document
  review-reports/              one-shot review reports (not artifacts)

/.github/workflows/            installed by skill-registry on invocation
  regen-skills-ledger-md.yml
  regen-skill-specs-ledger-md.yml
  regen-adrs-ledger-md.yml
  regen-agents-md-ledger-md.yml
```

Empty-by-design directories carry a `.gitkeep`.

---

## 3. Hashing

### 3.1 Skill directory hash (Option A)

1. Walk the directory tree.
2. **Exclude** every file path listed in the skill's
   `resources/000-metadata.json` under `hash_exclude`. The default
   exclusion list is:
   - `resources/000-metadata.json`
   - any user-edited config the skill itself owns (e.g.
     `resources/registry-config.json`, `resources/skill-sync-config.json`)
3. For each remaining file, compute `file_hash = sha256(file_bytes)`.
4. Sort the resulting `(posix_relative_path, file_hash)` tuples
   lexicographically by `posix_relative_path` (using `/` separators).
5. Build the canonical serialization: for each tuple, emit
   `posix_relative_path + "\n" + hex(file_hash) + "\n"`.
6. `content_hash = sha256(canonical_serialization)`.

A pure rename of a file inside the skill **changes** the hash. This is
intentional: rename breaks internal references and is a real semantic change.

### 3.2 Single-file artifact hash

1. Read the file as bytes.
2. Strip the first line (`\n`-terminated).
3. `content_hash = sha256(remaining_bytes)`.

The first line carries our metadata (which includes `content_hash` itself);
stripping it is what makes the hash stable across metadata updates.

### 3.3 Implementation rule

Hashing is implemented once per artifact type in
`skill-registry/scripts/hash_skill.py` and `hash_single_file.py`. Every other
place that needs a hash imports those.

---

## 4. Metadata

### 4.1 Skill metadata (`resources/000-metadata.json`)

```json
{
  "name": "skill-name",
  "origin": "github.com/lago-morph/ai-skills",
  "content_hash": "<hex sha256>",
  "version": "0.1.0",
  "state": "live",
  "implemented_as": null,
  "merged_into": null,
  "hash_exclude": [
    "resources/000-metadata.json"
  ]
}
```

`hash_exclude` paths are POSIX-relative to the skill directory root.

### 4.2 Single-file artifact metadata (first line)

```
{"name":"foo","origin":"github.com/lago-morph/ai-skills","content_hash":"<hex>","version":"0.1.0","state":"live","implemented_as":null,"merged_into":null}
```

One physical line, terminated by `\n`. Strippable with `sed '1d'`.

Modification detection: strip line 1, recompute hash, compare to the
`content_hash` field on line 1. Mismatch ⇒ the artifact was modified
downstream without going through the registry process.

---

## 5. Ledger

One ledger per artifact type. Filenames `000-ledger.json` and `000-ledger.md`
(the `000-` prefix keeps them at the top of directory listings).

### 5.1 Schema

```json
{
  "artifact_type": "skills | skill-specs | adrs | agents-md",
  "items": {
    "<kebab-name>": {
      "current_version": "1.2.0",
      "current_hash": "<hex>",
      "state": "live | deprecated | merged | implemented",
      "description": "AI-authored 2-3 sentence summary. Always describes the latest version. For deprecated items, names the recommended replacement(s).",
      "implemented_as": null,
      "merged_into": null,
      "name_clash": [],
      "versions": [
        {"version": "0.1.0", "hash": "<hex>", "commit": "<git-sha-on-main>"},
        {"version": "1.0.0", "hash": "<hex>", "commit": "<git-sha-on-main>"},
        {"version": "1.2.0", "hash": "<hex>", "commit": "<git-sha-on-main>"}
      ],
      "discarded_hashes": ["<hex>", "<hex>"]
    }
  }
}
```

JSON Schema at
`.claude/skills/skill-registry/resources/schemas/ledger.schema.json`.

### 5.2 State machine

| State          | Meaning                                                              |
|----------------|----------------------------------------------------------------------|
| `live`         | Actively maintained. Default.                                        |
| `deprecated`   | Still served, but `skill-sync` warns subscribers using `"latest"`.   |
| `merged`       | Folded into another artifact. `merged_into` populated. Sweep discards incoming candidates that match this entry's hashes. |
| `implemented`  | Skill-spec that became a skill. `implemented_as` populated. Same dedup behavior as `merged`. |

State transitions in v1 are **manual** — the user edits the ledger (linted
on save). v1.x will add a dedicated skill for state transitions.

### 5.3 `description` lifecycle

- AI authors the initial description when an artifact is added.
- On `replace` or `merge` dispositions during `process-incoming`, the AI is
  prompted with: current description, the semantic-diff report, and the new
  content. The AI decides whether the existing description is still accurate.
  - If accurate → leave unchanged.
  - If stale → propose a new description, surface to user, save on accept.
  The goal is description stability: re-writing only when meaningfully needed.

### 5.4 `name_clash`

Set when the user resolves a kebab-name collision during `process-incoming`
by assigning the incoming item a new name. The clash is recorded **only on
the original** item's ledger entry (one-way pointer). The renamed item's
ledger entry does **not** back-point.

Why one-way: this is for deduping repeated incoming sweeps. Each future
sweep that brings in a clashing item with the same kebab-name and unknown
hash will:

1. Look up the kebab-name in the ledger.
2. If found, check `current_hash` and `versions[*].hash` and
   `discarded_hashes` — no match yet.
3. Walk `name_clash[]`, look up each pointer's ledger entry, check **its**
   hashes (incl. discarded). Match ⇒ silently skip; the user already
   handled this clash.
4. If still no match, full in-processing (semantic-diff, etc.). The user
   sees the source-repo provenance and may decide it's the same clash with
   a new edit.

If during sweep we find that the renamed item has been **modified** in the
user's consumer-side directory but the original still clashes, sweep emits
a one-time notice: "name-clash item `<renamed>` (from `<source-repo>`) has
been changed locally; consider changing the local implementation name or
deleting the source." This is **a notice, not a process step** — sweep
continues silently.

---

## 6. Canonical JSON I/O

Determinism matters: ledger diffs need to be readable and merge-friendly.

### 6.1 Rules

1. Every JSON file written by any v1 code is written through the **canonical
   dumper** defined in `scripts/canonical_json.py`.
2. The canonical dumper:
   - Sorts object keys recursively (lexicographic, like `jq -S`).
   - Sorts arrays according to a **per-path sort spec** declared per schema:
     - Default: lexicographic sort on each element's JSON string form (catches
       arrays of primitives).
     - For known arrays of objects, sort by a designated key (e.g. `versions`
       sorted by `version` parsed as semver; `name_clash`,
       `discarded_hashes`, `hash_exclude` sorted lexicographically). The spec
       lives in `canonical_json.py` next to the schemas.
   - Two-space indentation, trailing newline.
3. Every JSON file read by any v1 code uses a real JSON parser
   (`json` stdlib or `jq`). No string slicing.
4. Schemas are linted on both **read** (fail loudly, abort) and **write**
   (fail loudly, abort).

### 6.2 Unit tests (mandatory)

For every Python module that emits canonical JSON, the test suite must
include cases that:

- Feed the input with top-level keys deliberately out of order.
- Feed the input with nested-object keys out of order.
- Feed the input with array elements out of order (for arrays whose spec
  declares them sortable).
- Assert byte-for-byte equality against the reference output (the same
  data run through `jq -S` for the key-sort axis, and a second fixture for
  array sorts the test suite owns).

These tests run in CI via `.github/workflows/test-skill-registry.yml`
(installed by the registry skill the same way the ledger-render workflows
are; see §8).

---

## 7. Skills

### 7.1 `skill-registry`

Bundled skill; one `SKILL.md` with progressive disclosure into mode-specific
resources.

#### 7.1.1 Modes

- **sweep** — for every repo in `registry-config.json`:
  1. `git clone --depth N` into `/tmp/skill-sweep-<run-id>/<org>/<repo>`.
  2. Check out `main` (or the configured default branch).
  3. For each configured artifact path glob, find candidate files/dirs.
  4. Compute the hash of each candidate.
  5. Ledger lookup (see §5.4 for name-clash extension).
  6. If known (live/deprecated/merged/implemented/discarded) → skip.
  7. If unknown → copy into
     `/incoming/<org>/<repo>/<type>/<name>/…`, preserving directory structure
     for skills and copying single files verbatim for the other types.
  8. After all repos are walked, automatically invoke **reconcile**.

  Includes the registry repo itself in the sweep, pointed at consumer-side
  paths (`.claude/skills`, `.claude/agents-md`, `ai/adr`, retrospective
  globs). This catches local edits in the registry repo itself.

- **reconcile** — batch, non-interactive. For every item in `/incoming/`:
  1. Run semantic-diff against the corresponding registry artifact (or
     blank, if it's an add-as-new candidate).
  2. Write `<name>-semantic-diff.md` next to the incoming artifact.
  3. Never modifies the ledger or the registry. Idempotent.

- **process-incoming** — interactive. For each `*-semantic-diff.md` in
  `/incoming/`:
  1. Show the report. Ask user for disposition.
  2. Dispositions:
     - **discard** — add incoming hash to `discarded_hashes` on the matched
       entry. No semver prompt. Remove `/incoming/<…>` and report.
     - **replace** — overwrite registry artifact with incoming. Prompt for
       semver (patch/minor/major, or literal; allows rc). Update ledger
       (new version, hash, commit-pending). Update description (see §5.3).
       Remove `/incoming/<…>` and report.
     - **merge** — AI proposes a combined artifact; user accepts/rejects
       each delta. Then identical to **replace** from semver/ledger
       standpoint.
     - **add-as-new** — only for kebab-names not in the ledger (or for
       intentional name forks resolving a clash). Prompt for new name if
       clashing. Prompt for semver (defaults offered: `0.1.0`, `1.0.0`,
       freeform allowed). Insert ledger entry. AI authors description.
       Remove `/incoming/<…>` and report.
  3. After every disposition, write the new ledger (canonical JSON,
     schema-linted).

- **semantic-diff** — invokable directly. Takes
  `(registry-artifact-path, incoming-artifact-path)` and emits the report.
  For single-file types, the report is a textual diff plus an AI-authored
  analysis. For skills, the report compares the file-tree, per-file diffs,
  and the AI's analysis of structural vs content changes (it should flag
  cases where the content-bag is similar but the structure shifted, since
  Option A hashing won't catch this — the human reviewer needs the heads-up).

- **install-workflows** — every invocation of `skill-registry` (any mode)
  begins with a workflow self-bootstrap: compare each file in
  `resources/_workflows/` (with `__SKILL_PATH__` substituted) against
  `.github/workflows/`. Missing or differing files are overwritten blindly.
  Idempotent.

#### 7.1.2 Trigger phrases (SKILL.md `description`)

"sweep skills", "sweep remotes", "ingest skills", "reconcile incoming",
"process incoming", "check registry", "pull skills from tracked repos",
"semantic-diff", "skill registry".

#### 7.1.3 Registry config (`resources/registry-config.json`)

```json
{
  "defaults": {
    "skills":      [".claude/skills/*/"],
    "agents_md":   [".claude/agents-md/*.md", "retrospective/*/AGENTS-MD-*.md"],
    "adrs":        ["ai/adr/*.md", "retrospective/*/ADR-*.md"],
    "skill_specs": ["retrospective/*/SKILL-SPEC-*.md"]
  },
  "repos": [
    {"repo": "lago-morph/ai-skills"},
    {"repo": "lago-morph/software-factory"},
    {"repo": "lago-morph/some-other", "paths": {"skills": ["custom/path/*/"]}}
  ]
}
```

- v1: **GitHub only**. `repo` is `org/name`.
- Per-repo `paths` is a **strict per-key replace** of the default. If a repo
  redefines `skills`, the defaults for `agents_md`, `adrs`, `skill_specs`
  still apply.

**Filename-pattern handling for sweep (v1):** sweep recognizes two filename
forms for single-file artifacts:

- **Pre-ingestion form** with the retrospective UID prefix:
  `SKILL-SPEC-<10hex>-<kebab-name>.md`,
  `ADR-<10hex>-<kebab-name>.md`,
  `AGENTS-MD-<10hex>-<kebab-name>.md`. The `<10hex>` UID is immutable and
  **NEVER recomputed** when copied into `/incoming/`. It is **stripped**
  when promoted into the registry.
- **Registry form**: `<kebab-name>.md` (no prefix).

Sweep accepts either form in any configured source path. (v1.0.1 will
generalize this to a configurable list of recognizer patterns per type.)

### 7.2 `skill-sync`

Standalone. Run from a consumer repo OR from this repo (self-sync).

#### 7.2.1 Behavior

1. Self-install workflows-style bootstrap is **not** applicable to this
   skill — `skill-sync` has no workflows of its own.
2. Read `<consumer>/.claude/skills/skill-sync/resources/skill-sync-config.json`
   (or the codex equivalent). Schema-lint.
3. Clone the registry repo (`lago-morph/ai-skills`) into `/tmp`.
4. For each subscribed artifact:
   a. Resolve version:
      - `"latest"` → registry's `current_version`.
      - pinned semver → look it up in the ledger's `versions[]`, fetch the
        artifact bytes by `git show <commit>:<path>`.
   b. If the local file is absent → install.
   c. If the local file exists and has `origin: ai-skills` metadata:
      - Compare hash to registry's `current_hash`.
      - If different and registry version is newer → upgrade.
      - If same → no-op.
   d. If the local file exists and does **not** have `origin: ai-skills`
      metadata (name clash) → surface to user with the registry ledger
      info (description, current_version, hash). User decides: skip,
      overwrite, rename local.
   e. If the ledger entry is `deprecated` and the subscription uses
      `"latest"` → emit a warning containing the ledger `description`.
      If subscription is pinned → silent.
   f. If the ledger entry is `merged` or `implemented` → install the
      **last version under the original name** (final entry in `versions[]`
      before the state change), **and** warn the user that the artifact
      has been folded into `<merged_into>` / `<implemented_as>` in the
      registry; they may want to subscribe to that instead.

5. **AGENTS.md regeneration** (only if subscription includes any agents-md
   items, otherwise both AGENTS.md and CLAUDE.md are skipped entirely):
   a. Read all subscribed agents-md files from
      `<consumer>/<paths.agents_md>/`. For each, extract the body of the
      `# agent instruction` section (strip first-line metadata, strip
      everything from the next `#` heading onward).
   b. Sort by filename, alphabetical.
   c. Concatenate with section separators, prepend the AGENTS.md banner
      template.
   d. Compare to current `AGENTS.md`. If different:
      - Capture the diff body as a new candidate file
        `<paths.agents_md>/extracted-<UTC-timestamp>.md` (in the strict
        two-section format — `# agent instruction` body containing the
        delta, plus a `# justification` placeholder).
      - Warn user: "regenerated AGENTS.md may reorder sections;
        standalone-additions extracted cleanly into
        `extracted-<…>.md`; inline edits may produce noisy extracts —
        review manually before next sync."
      - Overwrite AGENTS.md unconditionally.

6. **CLAUDE.md regeneration** (only if AGENTS.md was regenerated):
   a. CLAUDE.md template is a banner + a pointer to AGENTS.md, nothing else.
   b. If current CLAUDE.md has content beyond the pointer → capture as
      `<paths.agents_md>/extracted-claude-<UTC-timestamp>.md` (same two-section
      format).
   c. Overwrite CLAUDE.md unconditionally.

   Both AGENTS.md and CLAUDE.md headers carry, in bold, a "**⚠ DO NOT EDIT
   THIS FILE — put additions in `<paths.agents_md>/` and run `skill-sync`.**"
   notice.

#### 7.2.2 Trigger phrases

"skill sync", "sync skill", "sync skills", "update my skills",
"sync agents", "update AGENTS.md", "update CLAUDE.md", "pull from registry".

#### 7.2.3 Consumer config (`.claude/skills/skill-sync/resources/skill-sync-config.json`)

```json
{
  "registry": {"repo": "lago-morph/ai-skills", "ref": "main"},
  "paths": {
    "skills":    ".claude/skills",
    "agents_md": ".claude/agents-md",
    "adrs":      "ai/adr"
  },
  "agents_md_output": {
    "agents_md": "AGENTS.md",
    "claude_md": "CLAUDE.md"
  },
  "subscriptions": {
    "skills":    [{"name": "self-retrospective", "version": "latest"}],
    "agents_md": [{"name": "test-before-claim",  "version": "1.2.0"}],
    "adrs":      [{"name": "branch-strategy",    "version": "latest"}]
  }
}
```

`version` is JSON-Schema-linted as either the literal string `"latest"` or a
valid semver (with optional `-rc.<N>` prerelease).

Templates:
- `resources/skill-sync-config-template-claude.json` — default paths as above.
- `resources/skill-sync-config-template-codex.json` — codex-equivalent paths
  (researched at implementation time; ADRs default to a sibling location to
  whatever codex uses for skills).

**Template-vs-user-config rule:** the **template** ships with the skill and is
overwritten by future syncs. The **user config** (`skill-sync-config.json`,
sitting next to the template) is **never overwritten** by sync. When
`skill-sync` runs for the first time and finds no `skill-sync-config.json`,
it copies the appropriate template into place.

The same rule applies to `registry-config.json` for `skill-registry`.

Both user config files are listed in their skill's `hash_exclude` so
syncing the skill into a new place doesn't carry the previous user's
configuration.

---

## 8. GitHub Actions

Four workflows, one per ledger. Pattern follows
`software-factory/.claude/skills/research-pipeline`:

- Path-filtered trigger on `main` for the specific `000-ledger.json`.
- Validates schema, normalizes the JSON via the canonical dumper,
  re-renders `000-ledger.md`, commits with `[skip ci]`.
- Templates at
  `.claude/skills/skill-registry/resources/_workflows/*.yml`
  using `__SKILL_PATH__` substitution.
- Installed (and updated) by `skill-registry`'s **install-workflows**
  pre-step on every invocation.

A fifth workflow runs the canonical-JSON unit-test suite on PRs touching
`scripts/` or `resources/schemas/`.

---

## 9. AGENTS.md per-file format

```
{"name":"…","origin":"…","content_hash":"…","version":"…","state":"…","implemented_as":null,"merged_into":null}
# agent instruction

<verbatim rule text. concatenated into AGENTS.md.>

# justification

<persuasion text. stripped during AGENTS.md regeneration. preserved in
the source file.>

# anything-else (optional)

<motivation, picture, limerick, whatever. also stripped from AGENTS.md.
also preserved in the source file.>
```

The rules:
- Line 1: single-line JSON metadata.
- Section 2: H1 must be exactly `# agent instruction` (case-sensitive). Its
  body — up to but not including the next `#` heading — is what's
  concatenated into AGENTS.md.
- Sections 3+: optional. Any further H1 heading and everything after is
  preserved in the source file and **stripped** from AGENTS.md
  regeneration.

---

## 10. Bootstrap (v1 initial commit, not a runtime step)

One-time, performed by the agent implementing v1:

1. Create `/skills/`, `/skill-specs/`, `/adrs/`, `/agents-md/`,
   `/incoming/` with `.gitkeep` where empty.
2. For every existing skill directory under `/skills/<name>/`:
   - Create `resources/000-metadata.json` if `resources/` doesn't exist or
     doesn't have it.
   - Set `version: 0.1.0`, `state: live`, compute initial hash.
3. Move existing markdown spec files (`skill-manager-spec.md`,
   `use-cases-spec.md`, `architecture-*-spec.md`,
   `iterative-architecture-conversation-spec.md`) into `/skill-specs/`.
   Add first-line metadata. `version: 0.1.0`, `state: live`.
4. Move existing "review report" markdown files
   (`agent-dispatch-loop.md`, `codex-skill-creator.md`, etc.) to
   `/ai/review-reports/` — they are not artifacts, they're historical
   one-shot review reports.
5. Populate all four ledgers. AI authors each `description` field.
6. Render initial `000-ledger.md` for each ledger using the canonical
   render script.
7. Author `.claude/skills/skill-registry/` and
   `.claude/skills/skill-sync/`.

The bootstrap does NOT install the GitHub Actions — the registry skill's
self-bootstrap step takes care of that on first invocation.

---

## 11. Out of scope for v1

- The SPA / graphical system (v2).
- Non-GitHub source repos (v1.x).
- Configurable filename-recognizer patterns (v1.0.1).
- Dedicated state-transition skill for `deprecated` / `merged` /
  `implemented` (v1.x).
- Reconciliation between a consumer's local agents-md edits and the registry
  beyond the "extract the diff into a new candidate file" mechanism (v1.x).
- Codex consumer-side support beyond shipping a template (real-world testing
  deferred until v1.x).

---

## 12. PR sequence for implementation

1. **PR 1** (`claude/refactor-agent-skills-45am4`): this spec.
2. **PR 2** (branches off PR 1): bootstrap of existing artifacts —
   metadata, ledger entries, file moves.
3. **PR 3** (branches off PR 2): `skill-registry` skill (full implementation,
   workflows, tests).
4. **PR 4** (branches off PR 3): `skill-sync` skill (full implementation,
   templates, tests).

Each PR opens as draft. Each depends on the previous being merged before
its branch can collapse cleanly, but the work can proceed unattended.
