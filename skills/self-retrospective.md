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

_To be filled in after the second skill-creator review pass._
