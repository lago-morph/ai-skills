# agent-dispatch-loop review report

## Summary

Reviewed `skills/agent-dispatch-loop/` against the upstream Anthropic
skill-creator standard. The skill's content and structure are solid; the
core compliance gaps were file-naming and missing required frontmatter.
Applied two mechanical fixes (rename + add frontmatter) plus one link
update; no semantic content was changed.

## Changes made

- **Renamed `skills/agent-dispatch-loop/skill.md` -> `skills/agent-dispatch-loop/SKILL.md`**
  via `git mv`. The skill-creator spec lists `SKILL.md` (uppercase) as
  the required entry point in the "Anatomy of a Skill" section.
- **Added required YAML frontmatter (`name`, `description`) to `skills/agent-dispatch-loop/SKILL.md`.**
  The upstream skill-creator marks both fields as required; the
  description was synthesized verbatim from the existing opening
  paragraph and the existing "Trigger phrases" list, so no new guidance
  was introduced. The description includes "use when..." trigger
  phrases per the skill-creator's "pushy description" recommendation.
- **Updated the file-tree block in `skills/agent-dispatch-loop/README.md`**
  to reference `SKILL.md` instead of `skill.md`, keeping the README
  consistent with the on-disk filename after the rename.

## Proposed future changes

These are non-mechanical suggestions surfaced by a second pass against
the upstream skill-creator standard. Each would change semantic content
or structure, so they were intentionally left out of the mechanical PR.

- **Trim `SKILL.md` body below the 500-line ideal.** It is currently
  about 518 lines. skill-creator recommends staying under 500 and
  adding a layer of hierarchy (e.g. references) when approaching the
  limit. The biggest savings come from moving the six inline subagent
  brief templates into a `references/` file (see next item).
- **Move subagent brief templates to `references/briefs.md`.**
  skill-creator's progressive disclosure pattern says large repeatable
  blocks belong in `references/` and should be pulled in only when
  needed. This would shrink `SKILL.md`, make briefs easier to edit, and
  match the canonical layout used by skill-creator itself.
- **Adopt `references/` instead of `spec/` for the original spec.**
  skill-creator's "Anatomy of a Skill" lists `references/` as the
  standard directory for docs loaded as needed; `spec/` is non-standard
  and risks confusing users / tools that expect the canonical layout.
  The contents of `spec/SPEC.md` could become `references/spec.md`.
- **De-duplicate trigger phrases.** Trigger phrases now live in three
  places: the frontmatter `description`, the `## Trigger phrases`
  section in `SKILL.md`, and the "When to use" block in `README.md`.
  skill-creator says all "when to use" info should live in the
  description; consider slimming the body section or removing it.
- **Make the frontmatter description more "pushy".** skill-creator
  warns Claude tends to undertrigger skills, and recommends
  descriptions that explicitly nudge usage in adjacent contexts
  ("multi-step build workflows", "iterative refactor with test gates",
  etc.) rather than relying solely on the listed trigger phrases.
- **Reframe heavy "Do NOT" / "never" instructions with reasoning.**
  skill-creator flags all-caps ALWAYS/NEVER and rigid prohibitions as
  yellow flags and recommends explaining *why* a rule matters so the
  model can generalize. The Anti-patterns section and several brief
  constraints (e.g. "Do NOT post to GitHub, modify files, or merge")
  could each gain a one-line rationale.
- **Add an `evals/evals.json` with 2-3 realistic prompts.**
  skill-creator's standard workflow includes capturing eval prompts
  (and later assertions) so the skill can be benchmarked and
  iteratively improved. The skill has objectively verifiable behavior
  (loop terminates, PRs created, report exists), making it a good
  candidate for assertions.
- **Consider a `LICENSE.txt`** matching the convention used by
  upstream skill-creator and the local `codex-skill-creator` skill, so
  users redistributing the skill have clear terms.
- **Move `state-schema.json` under `references/` (or `assets/`).**
  Top-level non-`SKILL.md` files are not part of the canonical
  layout; relocating it makes the structure self-describing and lets
  `SKILL.md` link to it as a reference.
- **Resolve external skill references in `README.md`.** The
  Integration table mentions `live-debug-from-mcp-only` and
  `forensic-vs-aggressive-cleanup`, which do not exist in this repo.
  Either drop them, mark them as aspirational/external, or replace
  them with skills that do exist (`subagent-prompting`,
  `parallel-subagent-fanout`, `self-retrospective`).
