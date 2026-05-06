# parallel-subagent-fanout review report

## Summary

Reviewed `skills/parallel-subagent-fanout/` against the upstream Anthropic
skill-creator standard. The skill content is solid, but the entry-point file
was named `skill.md` (lowercase) instead of `SKILL.md`, and it was missing the
required YAML frontmatter (`name`, `description`) that drives skill triggering.
Both issues were fixed mechanically; cross-references were updated to match.

## Changes made

- Renamed `skills/parallel-subagent-fanout/skill.md` to
  `skills/parallel-subagent-fanout/SKILL.md` via `git mv`. Skill-creator
  requires the entry-point file to be `SKILL.md` (uppercase); the lowercase
  form prevents standard skill loaders from discovering the skill.
- Added YAML frontmatter (`name`, `description`) at the top of
  `skills/parallel-subagent-fanout/SKILL.md`. The description summarizes what
  the skill does and lists "when to use" cues (drawn directly from the
  existing trigger-phrases section), since skill-creator specifies that the
  description is the primary triggering mechanism and that all "when to use"
  info belongs there. The wording reuses the skill's own existing trigger
  phrases verbatim and adds no new guidance.
- Updated the file tree in `skills/parallel-subagent-fanout/README.md` to
  reference `SKILL.md` (uppercase) instead of `skill.md`, so the documented
  layout matches the actual filename after the rename.

## Proposed future changes
