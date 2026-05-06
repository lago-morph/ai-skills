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
