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

These are non-mechanical suggestions surfaced by a second skill-creator pass.
Each requires judgement / content changes and is left for a human reviewer.

- **Reorganize `spec/` to match the skill-creator anatomy.** Skill-creator
  defines `references/`, `scripts/`, and `assets/` as the canonical bundled-
  resource subdirectories. The current `spec/SPEC.md` is reference material
  for runtime use, so renaming `spec/` to `references/` (and adjusting
  cross-references) would align the skill with the standard layout and make
  it easier for other tooling to discover the bundled docs.
- **Reduce duplication between `SKILL.md` and `spec/SPEC.md`.** The two files
  cover largely the same pipeline; SPEC.md repeats the YAML plan shape, the
  branching commands, and the conflict-strategy table. Skill-creator's
  progressive-disclosure model favors a lean SKILL.md that points at deeper
  references on demand. Either trim SPEC.md to the parts SKILL.md doesn't
  cover (e.g., the test plan and future variants), or fold the unique parts
  into SKILL.md and delete SPEC.md.
- **Remove or replace the dead reference to `forensic-vs-aggressive-cleanup`.**
  Both `README.md` and `spec/SPEC.md` cite this skill for "branch cleanup
  conventions", but no such skill exists in this repo. Either inline the
  branch-cleanup guidance directly, drop the cross-reference, or replace it
  with a link to wherever that skill actually lives.
- **Make the description pushier.** Skill-creator notes that Claude tends to
  under-trigger skills and recommends descriptions that explicitly tell the
  model to use the skill in adjacent situations. The current description
  already includes "even if they don't explicitly say 'fanout'", which is
  good; consider adding more triggering surface (e.g., "multi-PR rollouts",
  "split work into branches") and running the description-optimizer loop
  (`scripts/run_loop.py` in the upstream skill-creator) to validate.
- **Drop the in-body "Trigger phrases" section in `SKILL.md`.** Skill-creator
  is explicit that all "when to use" information belongs in the frontmatter
  description, not the body. The current Trigger phrases section now
  duplicates information that already lives in the description; removing it
  would shorten the body and reduce drift between the two locations.
- **Add a top-of-file table of contents to `SKILL.md`.** At 362 lines the
  body is approaching skill-creator's 500-line guideline, and a short TOC up
  front would help dispatchers jump directly to the step they're resuming
  from (which is exactly the recovery flow described in the final section).
- **Add evals.** Skill-creator strongly recommends `evals/evals.json` for
  skills with verifiable outputs. This skill produces concrete artifacts
  (state.json, report.md, branch layout, PR), so a couple of test prompts
  with assertions like "report.md contains a summary table with N rows" or
  "all sub-branches were deleted post-merge" would fit naturally and let the
  skill be benchmarked against future revisions.
- **Bundle a brief-template `script` or `reference`.** The full subagent
  brief shape is inlined in Step 3 of `SKILL.md`. Extracting it into
  `references/brief-template.md` (or a tiny `scripts/render_brief.py`) would
  follow skill-creator's guidance to "look for repeated work across test
  cases" and keep the SKILL.md body focused on the dispatcher's decisions
  rather than the brief boilerplate.
- **Soften imperative emphasis where the rationale is already clear.**
  Skill-creator flags ALL-CAPS MUSTs and bolded warnings as a yellow flag
  and recommends explaining the why instead. Most of this skill already
  does this well, but a few spots ("Critical:", "Never silently…",
  "Do not proceed…") could be reframed as explanations of the failure mode
  the rule prevents.
