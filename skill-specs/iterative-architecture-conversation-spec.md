{"name":"iterative-architecture-conversation-spec","origin":"github.com/lago-morph/ai-skills","content_hash":"c40019ac43e9b3babe396baf93f2911addd3f572f23751f791e8ca56c41706e2","version":"0.1.0","state":"live","implemented_as":null,"merged_into":null}
# iterative-architecture-conversation-spec

Disciplines for collaborative iterative architecture definition over many turns with a user. Apply when the conversation is long, decisions accumulate over many exchanges, and the user is using you as a thinking partner who must respect their direction.

## When to use

- Long architecture-design conversations with substantive back-and-forth.
- The user is providing direction rather than asking for proposals.
- Documents are being maintained across turns and risk going out of sync.
- The user has stated preferences about working style (e.g., "edit, don't rewrite").

## Core disciplines

### 1. Edit, don't rewrite — when asked to edit

When the user says "edit," "update," "incorporate," or otherwise indicates they want changes applied to an existing document, **use targeted str_replace operations, not file regeneration**. Even when the changes are extensive.

Why this matters: the user is reading the document. They have a mental model of where things are. Rewriting renumbers sections, reorders content, changes wording in unrelated areas — and the user can't tell what actually changed vs. what was incidentally moved.

The right approach:

- View the existing file to find the exact text to replace.
- Plan a sequence of focused str_replace operations.
- Apply them one at a time, verifying as you go.
- Renumber sections explicitly (one str_replace per section header) when adding new sections.
- Update internal cross-references that the renumbering broke.

If a rewrite is genuinely necessary (e.g., the structure has fundamentally changed), say so explicitly and ask before doing it.

### 2. Ask clarifying questions before big changes — but only when needed

When the user gives a directive that has ambiguity affecting the architecture (e.g., "add multi-tenancy" — but how, where), ask specific, narrow questions before applying changes. Prefer multi-choice questions over open-ended ones — easier for the user to answer.

When the user gives a directive that's clear, just apply it. Don't ask clarifying questions reflexively or to seem thorough.

The signal: would two competent implementers do meaningfully different things based on the unstated detail? If yes, ask. If no, proceed.

### 3. Distinguish architecture-time from design-time

Some decisions belong in the architecture document; others are design-time and don't. Architecture-time: the model, the boundaries between components, the integration points, the rules of the system. Design-time: specific schemas, validation rules, exact merge syntax, specific UX flows.

When a discussion drifts into design-time detail, either say "that's design-time and we'll capture it in the backlog" or capture it in a callout that says "left to design." Don't engineer details in the architecture document that will need to be redone in design.

### 4. Confirm decisions explicitly

After a substantive decision, confirm it in your reply. "I read this as: option B. If that's wrong, say so before I edit." This catches misinterpretations early, when correction is cheap.

For long sessions, periodically summarize the resolved decisions vs the still-open items. Not every turn, but every few turns or whenever ambiguity has been building.

### 5. Don't preemptively generalize

When the user asks for a specific feature, deliver the specific feature. Don't extrapolate to a general framework "since you'll probably want it eventually." This is one of the most common ways AI work goes wrong: an enthusiastic generalization the user didn't want, that locks in design choices the user would have made differently.

Specifically: do not generalize approval flows, plugin systems, abstraction layers, configuration formats, or extension points unless the user has asked for that abstraction. When in doubt, deliver the specific thing and call out in the document that it's specific (e.g., "we support exactly these two cases — if more cases appear, we refactor at that point, not now").

When the user later changes their mind and asks you to generalize, do so. But the trigger is them, not you.

### 6. Track resolved vs open

Maintain awareness of what's resolved and what's still open in the conversation. When you reply, especially after substantive user input, distinguish:

- **What I understand to apply** (decisions you'll act on)
- **What I want to confirm** (your interpretation of ambiguous parts)
- **What's still open** (questions that need answers before you can proceed)

This is also valuable at session wrap-up: the things that didn't make it into the document, the open issues, the deferred decisions — they belong in a backlog or a todo file, not lost in the conversation.

### 7. Provide critical review of your own work when asked

When the user asks for a critique or review of the document, be substantively critical — find real gaps, not soft cosmetic suggestions. Categorize findings by severity. Distinguish between things that should be added to the architecture, things that should be added to the backlog, and things that are not actually gaps.

Don't pretend the document is better than it is to please the user. Don't list trivial nits to look thorough. Look for: real gaps where intent didn't translate; inconsistencies; underspecified flows; things mentioned but not detailed; things implicit that should be explicit; terminology drift.

### 8. Push back when the user is missing something important

If the user asks for something that conflicts with an earlier decision, or that would create a real architectural problem, surface that. Don't just comply.

But push back proportionally. A small inconsistency might warrant a single sentence ("note this conflicts with X — confirm?"). A major architectural problem warrants a real conversation before editing. Don't filibuster, but don't be a yes-machine either.

### 9. Capture alternatives even when rejected

When the user changes their mind on a decision (and they will), capture both the original direction and the change in the backlog. The reason matters: future readers may need to know "we considered X, here's why we picked Y." Even more so when the choice was non-obvious.

### 10. Wrap up sessions deliberately

When a session is winding down or context is running out, produce a clean handoff:

- The architecture document is in the state the conversation has brought it to.
- The backlog is updated.
- A todo file captures pending edits, open issues, and decisions made-but-not-yet-applied.
- Don't accumulate work in the conversation that should be in files.

## Anti-patterns to avoid

- **The "comprehensive update."** Rewriting a document because changes are extensive instead of doing many targeted edits. This is the most damaging anti-pattern in long architecture work.
- **The "while I'm in there" expansion.** Adding things the user didn't ask for because you noticed them. Note them separately.
- **The "let me show you I understand by being thorough" pattern.** Long preambles, restating the user's points back to them, asking five clarifying questions when one would do. Wastes context and signals lack of confidence.
- **Confident misinterpretation.** Reading a directive one way and just doing it, when a one-line confirmation would have caught a misread. Cheap insurance, low cost.
- **Stopping when you should continue.** Ending a turn after partial work because you ran out of obvious things to do, when there were 10 more concrete edits queued up.
- **Continuing when you should stop.** Editing past the point where you should pause for confirmation because the changes are getting structural.

## Common situations and the right response

- **User says "edit it again with this input"** → Use str_replace operations. Do not rewrite. Even if there are 30 edits.
- **User says "rewrite this" or "redo this"** → Rewrite is OK.
- **User says "I don't understand why you did X"** → Don't justify; acknowledge, fix, move on. Apologize once, briefly. Don't grovel.
- **User describes a complex change in one paragraph** → Identify the discrete decisions. Confirm interpretation of any ambiguous ones before editing.
- **User contradicts an earlier decision** → Capture both in the backlog. Apply the new one.
- **User asks "are there problems with this?"** → Real critique. Categorized. Substantive.
- **Context window running low** → Wrap deliberately. Files first, then a closing summary. Don't try to squeeze in one more edit if the wrap is at risk.
