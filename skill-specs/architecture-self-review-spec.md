{"name":"architecture-self-review-spec","origin":"github.com/lago-morph/ai-skills","content_hash":"c101f9f6a10bd7c47ee0851ea012b4898809cd722da0827e131d19706b889312","version":"0.1.0","state":"live","implemented_as":null,"merged_into":null}
# architecture-self-review-spec

A discipline for critically reviewing your own architecture document before the user has to. Apply when an architecture document is at a milestone (end of a major work session, before sign-off, before handoff to implementers) and you have the chance to find gaps before they do.

## When to use

- You've just produced or substantively revised an architecture document.
- The user asks for a review, critique, or "what's missing."
- You're about to wrap up a session and want to leave a clean state.
- The document is going to be used by implementers who can't easily ask follow-up questions.

## Categories of review findings

Group findings by type. Each type warrants a different response from the user.

### 1. Real gaps — things named but not described

Something is referenced in the document but not actually defined. A section title that promises content the section doesn't deliver. A term used as if it's been defined but isn't. A flow described at one level of abstraction but never at the level needed to implement.

Example: "Multi-tenancy story" listed in the explanation docs but no multi-tenancy model anywhere in the architectural views.

Response from user: usually "add it" or "defer it explicitly to the backlog."

### 2. Inconsistencies

The same concept is described differently in different places. Two diagrams disagree. A decision in section 6 contradicts a decision in section 14. Terminology drifts (sometimes "Platform Agent," sometimes "platform agent," sometimes just "agent" with no qualifier).

Response from user: usually "fix it" — but be careful: sometimes the inconsistency is intentional (different perspectives), and the user will explain.

### 3. Underspecified flows

A use case is described but the flow has gaps. What happens on failure? What happens at the boundaries? What's the expected error mode for the recipient? These are easy to miss because the happy path is what gets diagrammed.

Specifically check: what happens when an upstream component is unavailable, what happens when a request times out, what happens when the response is malformed, what happens when authentication expires mid-flow.

Response from user: case-by-case — some go in the document, some are explicitly deferred to design.

### 4. Things raised in conversation that didn't make it into the document

Long sessions have decisions buried in earlier turns that didn't land. The conversation said "use X" but the document still references the older option. The user gave a constraint that should be a callout but is invisible.

Response from user: "fix it" — usually a short edit.

### 5. Things implicit that should be explicit

Things the document assumes the reader knows but that aren't stated. A pattern repeated three times without naming it as a pattern. A platform-wide rule that's enforced everywhere but never written down.

Examples: "everything goes through LiteLLM" is implicit in many diagrams but should be a stated invariant; "RBAC is the floor, OPA can only restrict" is a powerful rule that, until stated, every reader has to reverse-engineer.

Response from user: usually "add it" — these are often the highest-leverage additions because they unify many paragraphs into one rule.

### 6. Open questions that should remain open but be tracked

Things you noticed that don't have answers yet and shouldn't be forced into answers. The right response is to add them to the backlog under "open questions to leave open," not to fabricate decisions.

Distinguish from gaps: gaps need filling; open questions are legitimately unfinished.

### 7. Terminology drift

Same word used for different things, or different words for the same thing. Common in long documents and in architectures with overlapping concept spaces. Worth a clean-up pass periodically.

Specifically: when a glossary term has been adopted, search for unqualified uses of the underlying word and decide each case (use the glossary term, or qualify with context for non-platform usage).

## Format of the review

When delivering the review:

- Group by category above.
- Within each category, list specific items concisely. One to three sentences each.
- For each item, suggest the response: add to the architecture, add to the backlog, fix as a small edit, or "discuss before deciding."
- Distinguish from items already captured in the backlog (don't re-raise things already tracked).
- Be honest about severity. A real gap and a minor cleanup are different; say which is which.

Length: long enough to cover the real findings, short enough to stay scannable. A typical review for a 1000-line document might be 400-800 words.

## What to look for during review

A checklist to walk through:

- Does each section deliver what its title promises?
- Are all terms used consistently?
- Are all decisions traceable to either the document or the backlog?
- Are there flows that the use case diagrams cover and others that are described in prose only? Should those have diagrams too?
- Are there concepts referenced in the architecture that are described only in passing?
- Are there cross-references that no longer match (after section renumbering, etc.)?
- Are there standard deliverables for components that aren't actually described as deliverables?
- Are there open issues in the conversation that should be on a todo list rather than left implicit?
- Are there decisions that have changed during the conversation but the document still reflects the original?
- Is there pretense of completeness where the architecture is actually still being designed?

## Anti-patterns to avoid

- **The cosmetic review.** Listing typo-level findings to look thorough. Don't.
- **The destructive review.** Using the review to push your own preferences against decisions the user already made. Don't. The user's decisions are decisions.
- **The exhaustive review.** Listing every possible improvement. Stick to what's actually a gap or a real problem.
- **The complimentary review.** Saying the document is great when it has real gaps. Critique honestly; the user asked for it.
- **The presumptuous review.** Adding findings about decisions you disagree with that the user has already made. Note them as alternatives in the backlog if appropriate, not as gaps in the architecture.

## After the review

Critically: do not edit the document based on the review until the user has reacted to it. The review is the input to a discussion about what to fix and what to defer. Apply edits only after the user has indicated which findings they want addressed and how.

This is the most important part of the discipline. Self-reviewing and then immediately rewriting based on your own findings is overstepping. The user asked for the review; let them direct the response.
