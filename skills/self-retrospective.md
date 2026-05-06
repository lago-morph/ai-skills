# self-retrospective review report

## Summary

Reviewed `skills/self-retrospective/` against the upstream Anthropic
skill-creator standards. The skill content itself is well-organized and
substantive, but it failed two structural requirements: the entrypoint file
was named `skill.md` (lowercase) instead of the required `SKILL.md`, and it
lacked the required YAML frontmatter (`name`, `description`). Made three
purely mechanical fixes; no semantic content was changed.

## Changes made

- Renamed `skills/self-retrospective/skill.md` → `skills/self-retrospective/SKILL.md`
  via `git mv`. Skill-creator's "Anatomy of a Skill" section explicitly names
  the required entrypoint `SKILL.md` (uppercase). The lowercase form would not
  be recognized by skill-loading tooling.
- Added YAML frontmatter (`name`, `description`) to
  `skills/self-retrospective/SKILL.md`. Skill-creator lists `name` and
  `description` as required frontmatter fields and identifies the description
  as the primary triggering mechanism. The new description is composed from
  the file's existing intro paragraph and the existing direct/proactive
  trigger lists — no new substantive guidance was introduced.
- Updated the file-tree diagram in `skills/self-retrospective/README.md` to
  reference `SKILL.md` instead of `skill.md`, so the documentation matches the
  on-disk filename after the rename.

## Proposed future changes

A second skill-creator review pass against the now-updated skill suggests
the following non-mechanical follow-ups. They would change wording,
structure, or content meaning, so they are intentionally NOT included in
this PR — the user should decide.

- **Reword the description for triggering "pushiness".** Skill-creator
  explicitly recommends descriptions that combat under-triggering with
  language like "make sure to use this skill whenever the user mentions...".
  The current description is informative but reserved; tuning it (or running
  it through skill-creator's `run_loop.py` description optimizer) would
  likely improve trigger accuracy.
- **Fix the `### 3.x` subsection numbering under `## Step 1` of `SKILL.md`.**
  The scan-checklist subsections are numbered 3.1–3.8, but their parent is
  "Step 1 — scan the session". The numbering is a holdover from
  `spec/SPEC.md` (where they were section 3) and is also referenced by the
  table in `README.md`. Renumbering to `1.1`–`1.8` (and updating the README
  table to match) would make the hierarchy self-consistent. Left as a future
  change because it touches cross-document references and risks being
  mistaken for a semantic edit.
- **Move `spec/SPEC.md` content into a `references/` directory.** The
  upstream anatomy uses `references/` for docs "loaded into context as
  needed". The current `spec/SPEC.md` is exactly that kind of content;
  renaming `spec/` → `references/` and adding a clear pointer from `SKILL.md`
  (e.g., "for full implementation detail see `references/spec.md`") would
  align the skill with the conventional skill layout.
- **Reduce overlap between `SKILL.md`, `README.md`, `spec/README.md`, and
  `spec/SPEC.md`.** All four restate the trigger lists, the three-part
  output, and the two-mode split with subtle wording variants.
  Skill-creator's progressive-disclosure model favors a tight `SKILL.md`
  plus on-demand `references/`. Per review instructions, all README files
  are preserved here, so consolidation is left for the user to direct.
- **Add an `evals/evals.json`.** Skill-creator's iteration loop assumes
  test cases exist in `evals/evals.json`. A small set of realistic
  retrospective prompts (with `expected_output` / `expectations`) would
  make this skill measurable via `aggregate_benchmark.py` and amenable to
  description optimization.
- **Resolve the Mode B branch-name contradiction.** `SKILL.md` step B-1
  prescribes `feat/retrospective-<YYYYMMDD>` while `spec/SPEC.md` 5.1
  example uses `feat/retrospective-skill-specs`. Aligning these (or
  marking one as authoritative) removes a doc-internal contradiction.
  This is a semantic edit because it changes which branch name the skill
  instructs agents to create.
- **Tighten the `--since` flag spec.** `SKILL.md` lists
  `/retrospective --since "2025-01-15"` in the flag table but neither
  `SKILL.md` nor `SPEC.md` explains how the skill scopes by timestamp
  inside a session. Either flesh out the semantics or drop the flag.
- **Consider compressing `SKILL.md` toward the 500-line guideline.** The
  current `SKILL.md` is ~355 lines, which is comfortably under the soft
  cap, but consolidating Mode A and Mode B mechanics into shorter
  recipes plus references would leave more room for explaining "why"
  (a writing-style recommendation skill-creator emphasizes).
