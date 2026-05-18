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

These are non-mechanical suggestions that emerged on a second pass against
skill-creator standards. Each would change content/meaning so was out of
scope for this PR, but the maintainer may want to consider them.

- **Reconcile the "9 sections" claim with the actual count.** README.md
  advertises a "9-section brief structure" and SKILL.md heading says the
  same, but `spec/SPEC.md` enumerates §2.1–§2.10 (ten sub-sections) and the
  template inside SKILL.md has roughly nine labeled blocks plus an identity
  sentence. Pick one canonical count, then update the table in README.md and
  the section numbering in SPEC.md to match. *Why:* the inconsistency
  weakens the structure-first message of the skill.

- **Move `spec/` into `references/` or drop it.** Skill-creator's "Anatomy
  of a Skill" only blesses `scripts/`, `references/`, and `assets/`. The
  `spec/SPEC.md` file is mostly a longer-form duplicate of SKILL.md. Either
  rename to `references/spec.md` (and adjust SKILL.md to point at it for
  deeper rationale) or remove the duplication entirely so SKILL.md is the
  single source of truth. *Why:* duplicate sources of truth drift; the
  current setup makes maintenance harder.

- **Refresh `spec/README.md` "Status: Spec only".** The skill is clearly
  built (full SKILL.md, examples directory, README), so the "Spec only"
  status line is stale. Replace with a brief note that the spec captures
  the original design intent or remove it. *Why:* stale status text
  misleads readers about implementation maturity.

- **De-duplicate top-level README.md vs SKILL.md.** README.md re-states the
  subagent-type table, parallel/serial rules, and anti-pattern table that
  already live in SKILL.md. Skill-creator wants SKILL.md to be the
  authoritative entrypoint and treats READMEs as optional. Consider trimming
  README.md to a short orientation (what, why, evidence, pointer to
  SKILL.md) and letting SKILL.md own the canonical content. *Why:* drift
  between the two is already visible (e.g., 9-section claim).

- **Add a generator script for "Generated mode".** SKILL.md describes a
  Generated mode that takes a structured input and produces a populated
  brief, but there is no `scripts/` directory implementing it. Skill-creator
  recommends scripts for deterministic, repetitive tasks — populating a
  template from a JSON-shaped input is a textbook fit. *Why:* the skill
  promises a capability that today must be reproduced from scratch on each
  use.

- **Tighten the description for stronger triggering.** Skill-creator
  explicitly recommends slightly "pushy" descriptions to combat
  undertriggering. The current description is informative but could add a
  prompt like "Make sure to use this skill any time you draft a prompt for
  the Agent tool, even if the user didn't ask explicitly." *Why:* missing
  triggers are the main failure mode of skills like this one.

- **Normalize code-fence languages.** Several fences in SKILL.md and the
  examples are unlabeled. Tagging the brief-template fence as `markdown`
  and tree diagrams as `text` would match the upstream skill-creator's
  conventions and improve renderer behavior. *Why:* small but improves
  readability and copy-paste fidelity.

- **Consider an `evals/` directory.** Even though brief quality is partly
  subjective, the Generated-mode output could be regression-tested (e.g.,
  given a fixed input, does the output contain all 9 spine sections, the
  exact test command, the time budget, etc.). *Why:* skill-creator
  encourages eval-driven iteration for skills with verifiable structure.

- **Fix the "duplicate 11" numbering in `examples/bad-brief-overscoped.md`.**
  The illustrative bad brief lists two items both numbered "11." This was
  left untouched because it appears inside the "problematic brief
  (outline)" code block and changing the numbering would change either the
  prose count ("11 deliverables") or the structure of the example.
  Resolution requires an editorial decision: renumber the second 11 to 12
  and update the prose, or merge the two items. *Why:* the duplicate is
  almost certainly an accidental typo, not an illustrative feature of a
  bad brief.
