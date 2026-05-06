# subagent-prompting review report

## Summary

Reviewed `skills/subagent-prompting/` against the upstream Anthropic
skill-creator standards. The skill content is well-structured and rich, but the
entrypoint file did not conform to the spec on two important points: filename
casing and missing YAML frontmatter. Made four small mechanical fixes to align
with skill-creator conventions; no semantic content was changed.

## Changes made

- **Renamed `skills/subagent-prompting/skill.md` -> `skills/subagent-prompting/SKILL.md`.**
  Skill-creator's "Anatomy of a Skill" specifies `SKILL.md` (uppercase) as the
  required entrypoint filename. The lowercase form would not be picked up by
  tooling that follows the spec.
- **Added YAML frontmatter (`name`, `description`) to `SKILL.md`.**
  The spec lists frontmatter with `name` and `description` as required; the
  description is the primary triggering mechanism. Description was synthesized
  from the existing top-of-file paragraph plus the "When to load this skill"
  section so it conveys both what the skill does and when to trigger it.
- **Updated `skills/subagent-prompting/README.md` file-tree.**
  The tree at the bottom of the README pointed at `skill.md`; updated to
  `SKILL.md` so the cross-reference is not broken after the rename.
- **Trimmed trailing blank line in `skills/subagent-prompting/spec/README.md`.**
  The file ended with `\n\n` instead of a single trailing newline; minor EOL
  normalization.

## Proposed future changes
