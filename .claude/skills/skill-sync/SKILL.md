---
name: skill-sync
description: Sync subscribed skills, ADRs, and agent-md instructions from the ai-skills registry (lago-morph/ai-skills) into the current consumer repository, and regenerate AGENTS.md + CLAUDE.md from the agents-md directory. Use in any repo that subscribes to ai-skills artifacts. Triggers include "skill sync", "sync skill", "sync skills", "update my skills", "sync agents", "update AGENTS.md", "update CLAUDE.md", "pull from registry", and combinations of those. Standalone — does not require any other skill in the consumer repo. Walks the user through name clashes when subscribed artifacts collide with existing local files. Reads version pins ("latest" or strict semver) from a single config file at resources/skill-sync-config.json. Treats AGENTS.md and CLAUDE.md as fully owned outputs: prior inline edits are captured into a timestamped extracted-<TS>.md candidate file in the agents-md directory before being overwritten.
---

# Skill: skill-sync

Sync subscribed artifacts from the `lago-morph/ai-skills` registry into
the current repository, and regenerate `AGENTS.md` and `CLAUDE.md`.

Read `ai/skill-management-v1.md` §7.2 in the registry repo for the
detailed design. This SKILL.md is the operating manual.

## When to use

Run inside any repository that has (or wants) a
`resources/skill-sync-config.json` (this skill's own config file —
templates are shipped here too) listing subscribed artifacts.

Triggers:

- "skill sync" / "sync skill" / "sync skills"
- "update my skills"
- "sync agents" / "update AGENTS.md" / "update CLAUDE.md"
- "pull from registry"

## What it does

1. **Ensure config exists.** If `resources/skill-sync-config.json` is
   missing, copy the Claude template (`skill-sync-config-template-claude.json`)
   into place. Codex template (`skill-sync-config-template-codex.json`) is
   shipped alongside; copy it manually if your harness is codex.
2. **Validate config** against
   `resources/schemas/skill-sync-config.schema.json`.
3. **Clone the registry** (default `lago-morph/ai-skills@main`) into
   `/tmp`. Load all four registry ledgers (validated against the
   registry's schema).
4. **For each subscribed artifact** (`skills`, then `agents_md`, then
   `adrs`):
   a. Resolve `"latest"` → `current_version`, or pinned semver to the
      matching entry in `versions[]`.
   b. Look at the local copy. If present **with** an `origin:
      github.com/lago-morph/ai-skills` metadata block, compare hashes:
      - same → no-op.
      - different & registry newer → upgrade (fetch artifact bytes at
        the recorded commit via `git show <commit>:<path>` /
        `git archive`).
   c. If present **without** ai-skills origin metadata → name clash.
      Report to user (agent decides next steps via AskUserQuestion).
   d. If absent → install.
   e. If the ledger entry's state is `deprecated` AND subscription is
      `"latest"` → emit a warning carrying the ledger `description`.
      Pinned subscriptions stay silent.
   f. If the ledger entry's state is `merged` or `implemented` → emit a
      warning naming the artifact it was folded into, but still install
      the last published version under the original name.
5. **If `subscriptions.agents_md` is non-empty**, regenerate
   `AGENTS.md`:
   - Concatenate the `# agent instruction` section bodies of every
     subscribed agents-md file in alphabetical-by-filename order.
   - Banner at top with the bold "DO NOT EDIT" notice and a pointer
     back to the agents-md directory.
   - If the current `AGENTS.md` differs from the regenerated output,
     write a candidate `extracted-<UTC>.md` to the agents-md directory
     capturing the prior content in the strict two-section format. The
     user can later promote it into a proper rule. Overwrite
     `AGENTS.md` unconditionally afterward.
   - Same treatment for `CLAUDE.md`: banner + pointer to `AGENTS.md`,
     prior content extracted as `extracted-claude-<UTC>.md`.
   - **If `subscriptions.agents_md` is empty, neither `AGENTS.md` nor
     `CLAUDE.md` is touched.**

## Driving the skill

Most invocations:

```
python .claude/skills/skill-sync/scripts/skill_sync.py
```

That single command does steps 1-5. It prints a structured report.

Useful flags:

- `--dry-run` — load + validate + plan, but make no changes.
- `--registry-clone PATH` — point at an existing clone (skip the
  network fetch).
- `--no-clone` — only valid alongside `--registry-clone`; refuses to
  clone.
- `--config PATH` — override the default config location.

The script does NOT call any LLM. Where human judgment is required
(name clash resolution, semver pinning decisions, AGENTS.md inline-edit
review), the agent reads the structured report and drives the
conversation with AskUserQuestion.

## Name-clash handling

If `_print_report` shows `name clashes: N -- requires user action`, the
agent should, for each:

1. Read the local file and the registry artifact.
2. Ask the user:
   - **skip** — leave local alone, don't sync this item this run.
   - **overwrite** — replace local with registry version (agent
     installs by re-running with the clash resolved, e.g. by deleting
     the local file first).
   - **rename local** — rename the local file out of the way (agent
     does the rename), then re-run sync.

This skill does NOT update the registry's ledger from the consumer
side. Name clashes are handled per-consumer.

## Config

`resources/skill-sync-config.json` (this skill's own; hash-excluded
from the skill's content hash):

```json
{
  "registry": { "repo": "lago-morph/ai-skills", "ref": "main" },
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
    "adrs":      []
  }
}
```

- `version` is `"latest"` or a strict semver (`MAJOR.MINOR.PATCH`,
  optionally `-rc.N`).
- Empty arrays in `subscriptions` mean "skip this artifact type".
- An empty `subscriptions.agents_md` ALSO disables `AGENTS.md` and
  `CLAUDE.md` regeneration.

The template files are not overwritten by sync; the user config is
authoritative and is never overwritten either.

## Files in this skill

```
SKILL.md                                   this file
resources/
  skill-sync-config.json                   user config (hash-excluded)
  skill-sync-config-template-claude.json
  skill-sync-config-template-codex.json
  agents-md-header.md                      AGENTS.md banner template
  claude-md-template.md                    CLAUDE.md template
  schemas/
    skill-sync-config.schema.json
scripts/
  canonical_json.py                        local copy (matches registry's)
  validate.py
  regen_agents_md.py                       AGENTS.md / CLAUDE.md rendering
  skill_sync.py                            main entry point
tests/
  test_regen_agents_md.py
  test_validate.py
```

## Hard rules

1. **All JSON written by this skill is canonical** (sorted keys, per-spec
   array sorts, 2-space indent, trailing newline).
2. **All JSON read by this skill is schema-validated** before use.
3. **No script in this skill calls an LLM.** Name-clash resolution and
   semver decisions are agent-driven via AskUserQuestion.
4. **`AGENTS.md` and `CLAUDE.md` are owned outputs.** Inline edits are
   not preserved — they are extracted into the agents-md directory as
   timestamped candidates and the file is overwritten.
5. **An empty agents-md subscription disables both `AGENTS.md` and
   `CLAUDE.md` regeneration entirely.**
