# architecture-backlog-spec

A reusable structure and discipline for maintaining a parallel "preserved ideas" document that lives alongside an architecture overview. Apply when the architecture work is non-trivial and decisions are being made faster than they can be fully integrated, when alternatives are being considered seriously, and when the cost of losing context is high.

## When to use

- The architecture work is collaborative and iterative, with many turns of decision-making.
- Decisions are being made that have alternatives worth recording.
- Some decisions are explicitly deferred to design-time rather than architecture-time.
- The user values knowing *why* a decision was made, not just what was decided.
- The risk of "we already considered that" being relitigated is real.

## What the backlog is for

The architecture overview is the canonical source of truth for what the platform is. It does not have room for everything that informed that picture. The backlog is the parallel document that captures everything around the architecture: what was considered and rejected, what was deferred, what to revisit and when, what's still open.

The backlog is a living document. It grows during conversations and gets pruned when items resolve into the architecture overview.

## Section structure

Use these seven sections in this order.

1. **Deferred design decisions** — decisions punted to design-time. Each will need its own design spec or ADR before implementation. List the open question, what's already known, and what specifically needs to be decided.

2. **Alternatives considered and rejected** — for each major decision, the alternative path with rationale for choosing the other one. The point is preserving the *reasoning* so a future revisit has full context. Format: chosen option in bold, alternative path described, rationale concise.

3. **Evolution paths to revisit** — decisions that are right for the current scope but worth revisiting under specific triggers. For each: what we chose, the trigger condition, what we'd consider switching to.

4. **Topics that need further design before implementation** — concrete pieces of the architecture that need design specifications before code. Different from deferred decisions: these are things we know we'll build, we just need to design them.

5. **Open questions to leave open** — questions that don't need answers yet but should be revisited at the right moment. Don't force closure on these.

6. **Architecture-level invariants worth documenting as ADRs** — implicit invariants in the architecture that should become explicit. Good ADR candidates.

7. **ADR candidates** — decisions large enough to deserve their own Architecture Decision Records, prioritized.

## Maintenance discipline

**Update alongside the architecture overview, not after.** Whenever the overview changes, ask: did this resolve any deferred decision? If so, move it from "deferred" to integrated. Did this raise new deferred decisions? If so, add them.

**Move resolved items out of "deferred."** Don't leave them as historical clutter. They live in the architecture overview now.

**Keep "alternatives rejected" entries concise.** A few sentences each. The point is preserving the reasoning, not re-litigating the decision.

**Use the trigger language consistently in evolution paths.** "Trigger to revisit:" followed by the specific condition. Vague triggers ("if we have problems") are useless.

**Audit at each major session boundary.** When a long conversation wraps up, sweep the backlog: anything resolved? Anything new? Anything that should escalate to ADR candidate?

## What goes in the backlog vs the architecture overview

Goes in the **architecture overview**:
- Final decisions and the resulting architecture
- The rationale for decisions (briefly, in prose around the decision)
- Open questions that affect day-1 implementation

Goes in the **backlog**:
- Alternatives considered and rejected
- Decisions deferred to design-time
- Triggers for future revisits
- Open questions that don't block day-1 implementation
- ADR candidates
- Invariants worth formalizing later

When something appears in both, it has stayed too long in the backlog and should be promoted to the overview, OR it has too much detail in the overview and should be moved to the backlog. Don't duplicate.

## Format

Markdown. Same readable style as the architecture overview. Numbered sections and subsections. Each item is short prose, not a long essay. The backlog is for fast lookup, not deep reading.

## Quality checks

When reviewing a backlog, ask:

- Are all decisions traceable? For every choice in the architecture, is the rationale findable here or in the overview?
- Are evolution paths actually triggerable? Or are they so vague they'd never fire?
- Are there ADR candidates that have been on the list a long time without being written? Time to write them.
- Are deferred decisions becoming stale? If a decision has been deferred forever and never picked up, either it's not actually needed (delete it) or it should be elevated.
- Is the "alternatives rejected" section preserving real reasoning, or has it become a list of bare assertions?

## Common pitfalls

- **Letting the backlog become a graveyard.** Resolved items not pruned. Old open questions never revisited. The document becomes ignored.
- **Treating the backlog as a TODO list.** Action items live in todo.md or in a tracker. The backlog is for *decisions* and their context.
- **Vague trigger language.** "Revisit if needed" is useless. Specify the condition.
- **Overloading "alternatives considered."** Listing every option ever mentioned drowns the real choices. Include only options that were seriously considered.
- **Skipping the backlog entirely** because the architecture overview "covers it." It doesn't — the overview can't carry alternatives and deferrals without becoming bloated.
