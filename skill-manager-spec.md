# Skill Registry Manager — Project Specification

## Status: Pre-Implementation

**Companion documents:**
- `use-cases-spec.md` — the standard user workflows (UC1–UC6) referenced from decisions 14, 15 and the Features section. Reviewable independently from this spec.

> **Architecture clarification (latest):** the app **does not invoke Claude directly**. There is no `claude -p` subprocess, no Agent SDK integration, no `ANTHROPIC_API_KEY` anywhere. The app's sole job is to produce GitHub issues with structured task descriptions; the user, working in their preferred Claude interface (Claude Code CLI, Claude.ai with GitHub MCP, Claude Desktop, web), tells Claude "process the open issues with label X"; Claude reads each issue, does the work, and posts results as comments (and/or commits/PRs); the app polls the issue for the structured response and continues. This is captured in decision 0 (rewritten) and decision 16 (new). Decisions 4 (Todo Directory) and 7 (Agent SDK June 15) are **superseded** by this model — see the deprecation notes on those sections.

-----

## DECISIONS REQUIRED BEFORE IMPLEMENTATION BEGINS

These must be resolved before writing any code. Claude Code should prompt the user for each of these before proceeding.

> **Note:** Decision 0 below dominates decisions 6, 8, large parts of the Architecture and Technology Decisions sections, and the framing of Phase 1 features. Resolve decision 0 first; the answers to 1–16 may shift depending on it. (Decisions 4 and 7 are superseded by decision 0's clarified interaction model — see notes on those sections.)

### 0. Hosting Architecture and Auth (clarified)

Two requirements drive this decision:
1. The app must be usable **from an iPad** as well as from a computer; the user does not want to build a native iPad app
2. The app **does not call Claude directly** — Claude work flows through GitHub issues consumed by whatever Claude interface the user is in (see decision 16). The app's only runtime job is GitHub API calls plus UI

**Options walked through:**

**A. Electron desktop app.** Killed by the iPad requirement. Skip.

**B. SPA hosted on GitHub Pages. *(RECOMMENDED for v0.x)***
- Just static HTML / CSS / JS in a GitHub Pages repo. Free hosting. Works on iPad Safari and every desktop browser
- Talks directly to the GitHub REST API (CORS is supported for authenticated requests)
- **No backend needed** because the LLM work is delegated to the user's Claude session via issues (decision 16). The SPA's job is: render UI, read and write files in the canonical repo via the GitHub API, create issues, poll issue comments
- All persistent state lives in the canonical GitHub repo (manifests, libraries, proposal queue, lineage, provenance). GitHub *is* the database

**C. SPA + small backend (AWS Lambda, Cloudflare Worker, etc.).**
- Worth it only when you need (a) true OAuth Web Flow with `client_secret` protection, (b) shared state across devices outside GitHub, or (c) long-running background work that cannot run in the user's Claude session. None apply right now
- Defer to the Agent-SDK-era rearchitecture

**Recommendation: Option B.**

**Note on dynamic hosting:** GitHub Pages is static-only. For server-side work, GitHub Actions can act as a poor-man's backend (event- or schedule-triggered, cold-start 10-30s). Not needed in v0.x because of the issues-as-message-bus model; may return when the Agent SDK is integrated.

**Auth options for Option B** (ordered easiest to most "proper"):

1. **Pasted fine-grained PAT *(v0.1 recommendation - simplest possible)*.** User creates a fine-grained PAT in GitHub Settings, scopes to the relevant repos, pastes into the app. App encrypts with a passphrase-derived key (WebCrypto) and stores in IndexedDB. Zero infrastructure, zero secrets in the app. Downside: fine-grained PATs cap at 1-year expiry; user must rotate
2. **GitHub OAuth Device Flow *(v0.2 - better UX, still no backend)*.** SPA shows a 6-char user code; user visits `github.com/login/device`, enters code, authorizes. SPA polls for the access token. **Device Flow does not require a `client_secret`** - it is designed for clients that cannot keep secrets, so `client_id` can safely be embedded in the JS bundle. Requires registering a public OAuth App
3. **GitHub App with user-to-server tokens.** Modern, granular permissions. Requires `client_secret` handling, which needs a tiny serverless function for the code exchange. Right answer eventually; overkill now

**iPad storage caveat:** Safari ITP evicts script-writable storage (IndexedDB) after roughly 7 days of inactivity. User re-authenticates after a gap. Acceptable; not a blocker.

**Future re-architecture (post Agent SDK, when the app needs to drive agents directly):**
- **GitHub Actions** triggered by `repository_dispatch` from the SPA - stays on GitHub infra, no AWS. Cold-start 10-30s. Private repos: 2,000 Action minutes per month on Free
- **AWS Lambda** - sub-second response, more setup. Right answer if Action latency becomes a problem or long-lived stateful agents are needed
- User has expressed preference for staying on GitHub Actions if viable; revisit when the Agent SDK becomes part of the design

**If Option B is confirmed, these spec sections need rewriting** (deferred to follow-up PR after decisions are locked):
- ARCHITECTURE - components become SPA + GitHub Pages + canonical-repo-as-database + Claude-via-issues, not Electron + Node + CLI subprocess
- TECHNOLOGY DECISIONS - Electron becomes a SPA framework (suggested: React + Vite for documented Pages deployment and small bundle); remove `claude -p` and Agent SDK from the v0.x stack
- Decision 6 (GitHub Auth) - supersede with the auth tier above
- Decision 7 (Agent SDK June 15) - **superseded** by decision 16; the app does not host Claude at all
- Decision 8 (Target platforms) - replace with browser targets (iPad Safari, desktop Chrome / Firefox / Edge / Safari)
- Decision 4 (Todo Directory) - **superseded** by decision 16 (issues as message bus)
- Phase 1 features - reframe "Todo Directory Writer" as "Issue Creator" per decision 16
- KNOWN CONSTRAINTS - add: iPad Safari ITP 7-day storage eviction; remove `claude -p` cold-start; remove Agent SDK credit-limit relevance

**Open sub-questions within Option B:**
- SPA framework: React + Vite (recommended), Svelte + SvelteKit static export, or vanilla TS?
- Auth tier to ship in v0.1: pasted PAT (lightest) or jump straight to Device Flow?
- Token encryption: passphrase-derived key (user supplies passphrase on app open) or session-only (re-paste or re-auth each session)?

### 1. Skill Identity & Versioning

- How is a skill uniquely identified across repos? By filename only (e.g. `SKILL.md`)? By a name field inside the file? By directory path (e.g. `/mnt/skills/public/docx/SKILL.md`)?
- What versioning scheme? Options:
  - A `version:` field embedded in the SKILL.md frontmatter (e.g. `version: 1.3.0`)
  - Git commit hash of the canonical copy
  - Date-based (e.g. `2026-05-16`)
- Decision affects: drift detection, manifest format, reconciliation UI

### 2. Manifest Format

- The manifest records which skills belong in which repos and refresh policy
- Where does the manifest live? In the canonical repo only? Or also in each target repo?
- Format: JSON or YAML?
- Draft schema to decide on:
  
  ```
  skills:
    - id: docx
      canonical_path: skills/docx/SKILL.md
      repos:
        - owner/repo-a: { auto_refresh: true }
        - owner/repo-b: { auto_refresh: false }
  ```
- Confirm or revise this schema with user before implementation

### 3. Canonical Repository

- Which GitHub repository will serve as the canonical skill store?
- What directory structure inside that repo?
- Should old versions be kept as git history only, or also as named snapshot files?

### 4. Todo Directory Format — *SUPERSEDED by decision 16*

> This decision is obsoleted by the issues-as-message-bus model in decision 16. The "todo directory" concept is replaced by GitHub issues created in the canonical repo. The format question moves to decision 16's "issue body format" section. Retained below for historical reference only.

- The bridge mechanism (pre-Agent SDK): the app writes structured task files into a `/todo` directory in target repos, and the user manually points Claude Code at them
- Format of task files: JSON? YAML? Markdown with frontmatter?
- Draft structure to confirm:
  
  ```json
  {
    "task": "update_skill",
    "skill_id": "docx",
    "action": "replace",
    "source_path": "skills/docx/SKILL.md",
    "target_path": ".claude/skills/docx/SKILL.md",
    "canonical_version": "1.3.0",
    "notes": "Reconcile with local edits in lines 40-55"
  }
  ```
- Confirm or revise with user

### 5. Skills Location Convention in Target Repos

- Where do skills live inside each non-canonical repo? Options:
  - `/mnt/skills/` (current convention observed from this session)
  - `.claude/skills/`
  - `ai/skills/`
- Must be consistent or configurable per repo

### 6. GitHub Authentication

- The Electron app needs a GitHub token
- Scope needed: at minimum `repo` (read/write to private repos)
- How is the token stored? Electron’s `safeStorage` API (OS keychain) is recommended — confirm this is acceptable
- Does the user have a GitHub Personal Access Token (classic) or will they use a fine-grained token?

### 7. Agent SDK Integration (June 15, 2026) — *SUPERSEDED by decision 16*

> This decision is obsoleted by the issues-as-message-bus model in decision 16. The app no longer needs to call Claude directly — the user's Claude session is the agent. The Agent SDK may become relevant later if the app evolves to drive agents itself (see decision 0's "Future re-architecture" section), but it is not part of v0.x. Retained below for historical reference only.

- On June 15, the todo directory + manual Claude Code step gets replaced by Agent SDK calls
- Max 20x plan = $200/month Agent SDK credit
- One-time opt-in required at claude.ai before June 15
- Confirm: is the intent to replace the todo directory entirely, or keep it as a fallback?

### 8. Target Platforms for the Electron App

- Windows confirmed
- macOS also? (affects packaging and code-signing decisions)

### 9. Retrospective Harvesting

- Directory matching: case-insensitive substring match on `retrospect` in the directory name (e.g. `retrospective/`, `retros/`, `Retrospect/`, `session-retrospectives/`). Confirm
- How is the retrospective report identified inside a matched directory? Options:
  - A conventional filename (e.g. `RETROSPECTIVE.md`, `retrospective.md`, `report.md`)
  - The newest `.md` file
  - Every `.md` file in the directory
- Are retrospective reports structured (parseable sections we can split mechanically) or free-form (require Claude to extract proposals)? Default assumption: free-form, extracted by `claude -p`
- Deduplication: if the same retrospective is harvested twice, or the same proposal appears in multiple retrospectives, how do we detect and collapse duplicates? Hash of source path + a Claude-generated proposal fingerprint?
- Frequency: is harvesting a manual user-triggered action, a scheduled background scan, or both?

### 10. Proposal Queue

- Working name for the queue that holds harvested-but-not-yet-implemented artifacts: **`proposals/`** (in the canonical repo). Confirm or rename
- Subdirectory layout to confirm:

  ```
  proposals/
    skills/         # Draft specs for proposed new skills
    agents-md/      # Proposed modifications to AGENTS.md fragments
    adrs/           # Proposed Architecture Decision Records
  ```
- Proposal file format: Markdown with frontmatter capturing `source_repo`, `source_retrospective`, `harvested_at`, `status`, `proposal_type`. Confirm
- **ADR enrichment requirement:** each ADR proposal must include enough context drawn from its source retrospective that it can be implemented without re-reading the original report. Enrichment is performed by Claude during harvest (one `claude -p` call per proposal). Confirm
- Status lifecycle: `proposed` → `accepted` → `implemented` → `archived` (or `rejected`). Confirm
- Promotion: when a `proposals/skills/foo.md` is accepted, does the app move it to `skills/foo/SKILL.md` (and update the manifest), or does the user do that by hand?

### 11. AGENTS.md Modular Composition

- A library of `AGENTS.md` fragments lives in the canonical repo, analogous to `skills/`. Proposed directory name: **`agents-md/`**. Confirm or rename
- Each fragment is a small, self-contained snippet — a section, a convention, a command block — that composes into a full `AGENTS.md`
- Per-repo composition: a manifest entry per target repo lists which fragments to include and their order in the assembled `AGENTS.md`
- Manifest placement: does the per-repo AGENTS.md composition live in the same manifest file as the skills assignment, or in its own file (e.g. `agents-md-manifest.{json,yaml}`)?
- Fragment metadata: do fragments need tags/categories (e.g. `git`, `testing`, `style`, `commit-conventions`) so the user can browse and select them in the UI?
- "Sub-files" handling: `AGENTS.md` may reference other files (e.g. `.claude/commands/*.md`, nested `AGENTS.md` in subdirectories). Are those also packaged as fragments and composed per-repo, or treated separately?
- Drift detection: when a target repo's `AGENTS.md` or any of its constituent fragments diverges from the canonical composition, surface it the same way as skill drift?

### 12. ADR Library & Surfacing

- A canonical library of Architecture Decision Records lives in the canonical repo at **`adrs/`**, structured analogously to `skills/` and `agents-md/`. Each ADR is a markdown file with frontmatter (`status`, `date`, `deciders`, `context_summary`, `tags`) and a body containing context, decision, and consequences. Confirm directory name and frontmatter schema
- ADR sources to harvest into this library:
  - **Retrospective harvest** (via the retrospective harvester) — proposals flow through `proposals/adrs/` and are promoted into `adrs/` on acceptance
  - **Existing ADR scavenging** — scan tracked repos for existing ADR directories using conventional patterns (`adr/`, `adrs/`, `decisions/`, `docs/adr/`, `architecture/decisions/`) and ingest the ADRs found there. Confirm the directory-name match patterns
- Deduplication across sources: hash of normalized title + harvest-time Claude fingerprint, same approach as proposal deduplication
- Per-repo composition: a manifest entry per target repo lists which ADRs from `adrs/` to surface in that repo. Mirrors the skills and AGENTS.md manifests. Confirm whether this lives in the unified manifest or its own file
- **Surfacing mechanism in target repos — RECOMMENDATION:** use the new modular AGENTS.md system. Ship a single canonical fragment (e.g. `agents-md/adr-loader.md`) that instructs Claude: "ADRs for this repo live in `adrs/`. Each has frontmatter with `status` and `context_summary` — read frontmatter to decide relevance, and load the full file only when you need to reference the decision." The selected ADR files are written into the target repo's `adrs/` directory, and the `adr-loader` fragment is composed into that repo's `AGENTS.md`. Rationale:
  - ADRs are **reference material consumed on demand**, not behavior triggers — they fit the AGENTS.md "always-known pointer" model more naturally than the skills "trigger-to-activate" model
  - One always-on fragment of negligible token cost beats N per-ADR `SKILL.md` files polluting the skills index
  - Composition naturally rides on the per-repo AGENTS.md manifest already required in section 11
- Alternatives considered (open to user override):
  - A dedicated `adr-loader` skill instead of an AGENTS.md fragment — adds indirection without clear benefit, since the loader instruction needs to be always-in-context
  - One `SKILL.md` per ADR (parallel skill per ADR) — proliferates the skills index, and ADR frontmatter (status, deciders, consequences) doesn't map cleanly to skill trigger metadata (description, when-to-use)
- Confirm the recommendation or pick an alternative before implementation

### 13. Library Entry Identity, Lineage & Refactoring

The user will continually recategorize and refactor library entries — splitting one skill into two, merging two into one, renaming, retiring. Manifests in target repos must keep resolving correctly across these refactors. This decision applies uniformly to all three libraries (`skills/`, `agents-md/`, `adrs/`).

- **Immutable identifier:** every entry has an opaque, immutable ID that never changes for the life of the entry, regardless of rename or recategorization. Proposed format: short stable slug with a type prefix, e.g. `skl_a3f9k2`, `amd_x7q1m4`, `adr_p2k8z3`. Confirm format (alternatives: full UUIDs, content-hash-derived IDs, sequential numeric IDs)
- A human-readable `name:` field is **separate** from the ID and may change freely. Manifests reference entries by ID; UI displays `name`. Filenames on disk may track `name` for readability, but resolution is by ID via frontmatter
- **Lineage frontmatter** on every entry records its provenance:
  - `id:` — the immutable ID
  - `predecessors: []` — IDs this entry was derived from (empty for an original entry)
  - `status: active | superseded | retired`
  - `superseded_by: []` — populated when the entry is no longer active; lists the IDs of its successors (empty for `retired` with no replacement)
- **Refactoring operations** supported by the app, each preserving the lineage trail:
  - **Rename:** edit `name:` only. ID and lineage unchanged
  - **Recategorize:** move between subdirectories or change tags. ID unchanged
  - **Split** (one → many): create N new entries, each with `predecessors: [old_id]`. Mark the old entry `status: superseded`, `superseded_by: [new_id_1, …, new_id_N]`
  - **Merge** (many → one): create one new entry with `predecessors: [old_id_1, old_id_2, …]`. Mark each old entry `status: superseded`, `superseded_by: [new_id]`
  - **Retire:** mark `status: retired`, `superseded_by: []`
- **Manifest resolution at sync time:** when a target-repo manifest references an ID:
  - `active` → use it directly
  - `superseded` → follow `superseded_by` recursively to the terminal successors and surface **all** of them. For a split, the repo receives all N successors; for a merge, the repo receives the single consolidated successor; for a chain of renames, the repo receives the latest
  - `retired` → surface a UI warning; write nothing to the target repo for that reference
  - The app offers to rewrite the manifest in place to point at the resolved terminal IDs so future syncs are direct (no lineage walk needed)
- **Superseded entry storage:** superseded entries stay as tombstones (with full frontmatter) so the reference trail is preserved both in git history and via direct lookup. Open: do tombstones remain in the active library directory, or move to `skills/_superseded/` (and analogous) to keep the active set clean?
- **Lineage truth:** is the canonical source of lineage the per-entry frontmatter (decentralized, lives with the data, requires a scan to do reverse lookups), a separate `lineage.{json,yaml}` graph file (centralized, fast lookup, easy to drift), or both (frontmatter as truth, lineage file as derived cache)? Recommendation: per-entry frontmatter as truth + a derived cache rebuilt by the app
- Confirm this design — ID format, tombstone placement, lineage truth, and whether the scheme applies uniformly across all three library types

### 14. Sync Direction & Provenance

- **Repo → canonical match logic** (UC5): when ingesting a skill / fragment / ADR from a tracked repo, how do we decide it matches an existing canonical entry? Proposal: content hash for fast exact-match, then Claude-assisted similarity check for near-matches (catches reformatted-but-equivalent entries). Confirm
- **Provenance schema:** each entry tracks one or more provenance records of the form `{source_repo, source_path, ingested_at, ingested_by, content_hash_at_ingest}`. Stored as a list in the entry's frontmatter, or as a separate `provenance.{json,yaml}` file. Confirm placement
- **Tag-vs-create semantics on ingest:** if an entry matches an existing canonical entry, the existing entry receives an additional provenance record (indicating it also lives in this repo) rather than creating a duplicate. If no match, a new entry is created with a fresh immutable ID. Confirm
- **Bulk parallel sync** (UC4): max concurrency for parallel repo writes — proposal: 5 concurrent (respects GitHub's 5,000 req/hr rate limit with typical repo size and leaves headroom). Confirm
- **Cross-repo skill drift detection:** when the same skill ID is provenanced in multiple repos and they have diverged, this surfaces as a multi-way reconciliation in UC6

### 15. Reconciliation Output Channel

- **Default output channel** for the guided reconciliation workflow (UC6): proposal is **a GitHub issue** opened against the canonical repo with a specific label (proposed: `reconciliation-pending`). A separate Claude Code session can then process the queue with `gh issue list --label reconciliation-pending`. Confirm the channel and the label name
- **Fallback channel:** a file in a working directory (e.g. `proposals/reconciliations/<entry-id>-<timestamp>.md`) for cases where issue creation isn't appropriate
- **Issue body format:** structured markdown with frontmatter capturing entry ID, versions compared, and the Claude-generated inventory of distinct ideas + recommendations. The format must be parseable by a downstream Claude Code session so it can pick up the conversation
- **Conversation continuation:** when a separate Claude Code session works an issue, where does the resulting decision go — back into the issue as comments, into a PR against the canonical repo, or both?

### 16. Issue Protocol (the app's only Claude integration)

**Architecture in one sentence:** the app produces GitHub issues containing structured task descriptions; the user, working in any Claude interface (Claude Code CLI, Claude.ai with the GitHub MCP connector, Claude Desktop, web), tells Claude "process the open issues with label X"; Claude reads each issue, performs the work, and posts results as issue comments (and / or commits, PRs, etc.); the app polls the issue or listens via webhook to learn when a response has been posted, then continues. This replaces both decision 4 (todo directory) and decision 7 (Agent SDK integration) for the v0.x phase.

**Why this design:**
- Eliminates the need for the app to host Claude (no `claude -p`, no Agent SDK in-process, no `ANTHROPIC_API_KEY`, no `CLAUDE_CODE_OAUTH_TOKEN`)
- Lets the user drive Claude in whatever interface they prefer (iPad → Claude.ai with GitHub MCP; desktop → Claude Code CLI or Desktop)
- Uses GitHub as both the message bus and the audit trail — every task and every Claude response is preserved as issue history
- Keeps the app pure-frontend, which is what makes the SPA-on-GitHub-Pages hosting viable

**Decisions to lock down:**

- **Issue location:** in the canonical repo (so a single Claude session can see all pending work across all tracked repos). Confirm
- **Labels per task type:** each task type gets its own label so the user can scope a Claude session to one class of work. Proposed labels (confirm and revise):
  - `task:drift-summary` - semantic diff of two versions of an entry
  - `task:harvest-retrospective` - extract proposals from a retrospective directory
  - `task:enrich-adr-proposal` - add retrospective context to a proposed ADR
  - `task:reconcile` - guided reconciliation (UC6)
  - `task:ingest-similarity-check` - repo→canonical similarity comparison (UC5)
  - `task:compose-agents-md` - assemble an AGENTS.md preview from selected fragments
- **Issue body format:** structured markdown with a YAML frontmatter block at top capturing:
  - `task_id` (uniquely identifies this task instance — UUID or hash)
  - `task_type` (matches the label suffix)
  - `created_by: skill-registry-app`
  - `created_at`
  - `inputs:` (everything Claude needs — entry IDs, file paths, links to specific blob versions via `https://github.com/.../blob/<sha>/path`)
  - `expected_output:` (description of what the response comment should contain)
  - The body below the frontmatter is human-readable context (prose explanation of the task, links to relevant docs)
- **Response format:** Claude posts a comment whose body contains a fenced code block tagged `claude-result` (e.g. ` ```claude-result\n...\n``` `) wrapping structured JSON or YAML. The app polls comments and processes the first comment whose body contains that fence. Confirm marker name
- **Completion signal:** for single-shot tasks, the first `claude-result` comment is the answer. For multi-turn tasks (reconciliation), the response includes `final: false` until the conversation is done; the user (in Claude) signals completion with `final: true`. The app considers a task complete on `final: true` (or implicit `true` if absent for single-shot task types)
- **Polling cadence:** when the user is actively in the app, poll the issue's `comments` endpoint every N seconds (proposed: 5s). When the app isn't open, no polling — the user manually triggers a "check for responses" action on app open. Confirm cadence
- **Webhook alternative (optional later):** GitHub webhook → tiny serverless endpoint (Cloudflare Worker free tier) → SSE / WebSocket back to the app for low-latency completion. Adds infrastructure; nice-to-have, not required for v0.x
- **Issue closure:** after the app processes the final response and updates state, the app closes the issue (with a final comment summarizing what was done). Confirm: app closes, or leave open for the user?
- **Stale-issue handling:** if an issue sits unresolved for N days, surface in the app's "needs attention" view. Confirm staleness threshold
- **Conversation continuity for multi-step tasks:** the app does not need to participate in the conversation itself — it just watches for `final: true`. This means the user can have an arbitrarily long back-and-forth with Claude inside one issue, and the app picks up only when complete

**Worked example — drift summary task:**

```
Issue title:    [task:drift-summary] Compare canonical skill `skl_a3f9k2` against owner/repo-a copy
Labels:         task:drift-summary
Body:
  ---
  task_id: 0192f8a3-bc4d-7e21-9876-543210abcdef
  task_type: drift-summary
  created_by: skill-registry-app
  created_at: 2026-05-17T14:32:18Z
  inputs:
    entry_id: skl_a3f9k2
    entry_name: docx-converter
    canonical_blob: https://github.com/owner/canonical/blob/abc123/skills/docx-converter/SKILL.md
    target_blob: https://github.com/owner/repo-a/blob/def456/.claude/skills/docx-converter/SKILL.md
  expected_output:
    A `claude-result` block containing JSON with fields:
      summary: 1-3 sentence semantic summary of the differences
      categories: list of difference categories (e.g. "expanded triggers", "new examples", "wording")
      recommendation: "canonical-wins" | "target-wins" | "merge-needed"
  ---
  Please compare these two versions of the same skill and post a `claude-result` block
  describing the semantic differences. This is fully automated input; reply only with
  the result block.

Claude's response comment:
  ```claude-result
  {
    "summary": "Target adds two new trigger keywords (`.dotx`, `.docm`) and rephrases the
                'when to use' section more concisely. Canonical is otherwise identical.",
    "categories": ["expanded triggers", "wording"],
    "recommendation": "merge-needed",
    "final": true
  }
  ```
```

-----

## PROJECT OVERVIEW

**Name (working title):** Skill Registry Manager

**What it is:** An Electron desktop application for Windows that manages Claude AI skill files (SKILL.md and related documents) across multiple GitHub repositories. It provides a canonical source of truth, drift detection, AI-assisted reconciliation, and (eventually) automated skill propagation.

**Why it exists:** The user works across multiple platforms (Claude web, Claude for Windows, Claude Code CLI, iPad, iPhone) and uses Claude skills stored in individual repositories. When a skill is updated in one repo, copies in other repos diverge. There is currently no way to detect or reconcile this drift without manually inspecting each repo.

-----

## ARCHITECTURE

### Components

#### 1. Canonical Skill Store (GitHub Repository)

- A dedicated GitHub repository that is the single source of truth for all skills
- Contains every skill in versioned form
- Git history serves as the full version history
- Contains the master manifest file

#### 2. Electron Application (Windows)

- Built with Electron + Node.js
- Communicates with GitHub via Octokit (official GitHub REST/GraphQL SDK for Node.js)
- Uses `claude -p` (Claude Code CLI, non-interactive) for AI tasks now
- Migrates to Claude Agent SDK (TypeScript) on June 15, 2026
- No separate Anthropic API key required — uses Max subscription OAuth credentials

#### 3. Todo Directory (Bridge Mechanism — Pre-June 15)

- The app writes structured task files to a `/todo` directory in target repos
- User manually tells Claude Code: “go look in the todo directory and do what it says”
- This is replaced by Agent SDK integration on June 15

-----

## FEATURES

### Phase 1 — Core (Build Now)

#### Repo Cataloging

- Connect to GitHub using a personal access token
- Discover and list all repos the token has access to
- Scan each repo for skill files based on known path conventions
- Display a catalog: which skills exist in which repos, and what version

#### Drift Detection

- Compare each repo’s copy of a skill against the canonical version
- Flag repos where the skill has diverged
- Show a human-readable summary of what changed (not line-by-line diff — semantic summary via Claude)

#### Manifest Management

- Read and write the master manifest
- UI to assign skills to repos
- UI to set auto-refresh policy per repo

#### Todo Directory Writer

- Generate structured task files for Claude Code to execute
- Tasks include: update skill to canonical, reconcile drift, add new skill
- User runs Claude Code manually against the todo directory

#### Skill Reconciliation Workflow

- When drift is detected, user can invoke AI-assisted reconciliation
- The app sends both versions to Claude with a prompt asking it to:
  - Explain what changed and why each version might be right
  - Propose a merged/reconciled version
  - Ask the user to approve or edit before writing back to canonical

#### Retrospective Harvester

- Scan every tracked repo for directories whose names contain `retrospect` (case-insensitive)
- Read retrospective reports inside those directories
- Use Claude (`claude -p`) to extract three classes of proposals from each report:
  - Specs for proposed new skills
  - Proposed modifications to `AGENTS.md` fragments
  - Proposed Architecture Decision Records
- For each ADR proposal, inject enough context from the source retrospective that the ADR is independently implementable
- Write each proposal into the proposal queue in the canonical repo, tagged with source repo, source retrospective, and harvest date
- Deduplicate against existing queue entries on subsequent harvests

#### Proposal Queue

- A `proposals/` directory in the canonical repo holds harvested-but-not-yet-implemented artifacts in three subdirectories (`skills/`, `agents-md/`, `adrs/`)
- UI for reviewing, editing, accepting, or rejecting proposals
- On acceptance, the app promotes the proposal into the corresponding library (`skills/`, `agents-md/`, `adrs/`), assigning a fresh immutable ID per decision 13
- Rejected and archived proposals stay in `proposals/` with `status:` frontmatter for the record

#### AGENTS.md Modular Composition

- A library of `AGENTS.md` fragments lives in the canonical repo at `agents-md/`, analogous to `skills/`
- Each fragment is a small, focused snippet — a section, a convention, a command block — that composes into a full `AGENTS.md`
- A per-repo composition manifest selects which fragments to include for each target repo and their order
- The app assembles (and canonicalizes) the target repo's `AGENTS.md` from the selected fragments
- Drift detection on the assembled `AGENTS.md` and on individual fragments, with AI-assisted reconciliation analogous to the skills flow

#### ADR Library

- Maintain a canonical library of Architecture Decision Records in `adrs/`, analogous to `skills/` and `agents-md/`
- Populate the library from two sources:
  - **Retrospective harvest:** ADR proposals from retrospectives flow into `proposals/adrs/` and, on acceptance, are promoted into `adrs/`
  - **Existing ADR scavenging:** scan tracked repos for existing ADR directories (working patterns: `adr/`, `adrs/`, `decisions/`, `docs/adr/`, `architecture/decisions/`) and ingest the ADRs found there, deduplicating against existing entries
- Each ADR carries frontmatter (`id`, `status`, `date`, `deciders`, `context_summary`, `tags`) so Claude and the user can decide relevance without loading the full body
- Per-repo composition: select which ADRs from the library to surface in each target repo and write them into that repo's `adrs/` directory
- Surfacing in target repos rides on the AGENTS.md modular composition system (see decision 12) — a single `adr-loader` fragment instructs Claude how to discover ADRs by frontmatter and load only what it needs

#### Library Refactoring Tools

- UI operations for **rename, recategorize, split, merge, and retire** across all three libraries (`skills/`, `agents-md/`, `adrs/`)
- Each operation preserves the lineage trail by writing `predecessors` / `superseded_by` frontmatter per decision 13
- Manifest resolution follows superseded links automatically so target repos always receive the current successor(s) without manual manifest edits — the UI also offers to rewrite manifests to point at the new IDs directly
- Lineage visualization: per-entry "where did this come from / what did it become" view

#### Sync Direction & Provenance Tools

- Per-repo and bulk sync operations in both directions (canonical → repo and repo → canonical)
- Provenance tracking for entries that originated in or also appear in tracked repos
- "GitHub issue with label" output channel for reconciliation proposals, so a separate Claude Code session can pick the queue up by label and process it conversationally (see UC5 and UC6 below)

### Phase 2 — Agent SDK Integration (June 15, 2026)

- Replace todo directory + manual Claude Code step with direct Agent SDK calls
- The app sends tasks to Claude programmatically and receives results
- Reduces manual steps: user approves actions in the app UI instead of switching to a terminal
- Requires one-time opt-in at claude.ai for Agent SDK credit

### Phase 3 — Skill Improvement UI (Future / Version 2)

- Interactive editor for improving skills
- Side-by-side comparison of skill versions
- Prompt Claude to suggest improvements to a skill
- Publish improved version back to canonical with version bump

-----

## TECHNOLOGY DECISIONS

|Concern                  |Decision                          |Notes                             |
|-------------------------|----------------------------------|----------------------------------|
|Desktop framework        |Electron                          |Windows primary target            |
|GitHub API               |Octokit (`@octokit/rest`)         |Official Node.js GitHub SDK       |
|AI integration (now)     |`claude -p` CLI subprocess        |Max subscription OAuth, no API key|
|AI integration (June 15+)|Claude Agent SDK (TypeScript)     |$200/month credit on Max 20x      |
|Token storage            |Electron `safeStorage`            |OS keychain, not plaintext        |
|UI framework             |TBD — decide before implementation|React recommended for Electron    |
|Canonical store          |GitHub repository                 |TBD — which repo                  |

-----

## KNOWN CONSTRAINTS & RISKS

- **`claude -p` cold start:** Each CLI invocation costs 3–5 seconds startup time (Node.js init, auth handshake). Acceptable for infrequent reconciliation tasks; not for high-frequency calls.
- **Agent SDK credit limit:** $200/month on Max 20x. Unused credits don’t roll over. Overages go to pay-as-you-go if extra usage is enabled.
- **Anthropic ToS:** Do not attempt to automate the Claude.ai web interface (e.g. via Playwright). Violates terms and risks account suspension.
- **Skill semantic identity:** Skills are not line-by-line comparable. All diff/merge must be AI-assisted, not mechanical.
- **GitHub rate limits:** Octokit respects GitHub API rate limits (5,000 requests/hour for authenticated users). Cataloging many repos in bulk should be throttled.

-----

## SESSION CONTEXT (for Claude Code handoff)

> **Note (May 2026 update):** The bullets below capture the original Claude.ai session that produced the first draft of this spec. Several items have since been clarified or superseded — see the **Architecture clarification** note at the top of this document, and decisions 0 and 16. In particular: the app no longer hosts Claude (no `claude -p`, no Agent SDK), and Electron is replaced by an SPA on GitHub Pages because of the iPad requirement.

This spec was created in a Claude.ai chat session. The following were established during that conversation:

- The user has a **Claude Max subscription** (likely 20x tier) and does **not** have a separate Anthropic API key
- The user is building for **Windows** using **Electron**
- The user confirmed the **June 15, 2026 Agent SDK credit** announcement from Anthropic’s official support page: `https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan`
- The intended build strategy is: **build with `claude -p` now, migrate to Agent SDK on June 15**
- Claude Code CLI non-interactive mode (`claude -p`) is the correct bridge mechanism — it uses Max subscription OAuth credentials, not an API key
- Using Playwright to automate Claude.ai was explicitly ruled out (ToS violation)
- Using Claude Cowork was ruled out (not programmable)
- There is currently **no IPC mechanism** to inject prompts into a running interactive Claude Code session — this is a known feature gap as of May 2026
- The GitHub MCP connector was **not connected** in Claude.ai at time of writing — user may want to connect it for future sessions

-----

## SUGGESTED FIRST STEPS FOR CLAUDE CODE

1. Present the “Decisions Required” section to the user and collect answers for each item
1. Once decisions are recorded, update this spec with the confirmed answers
1. Initialize the Electron project scaffold (main process, renderer process, basic window)
1. Implement GitHub token input and storage via `safeStorage`
1. Implement Octokit-based repo cataloging
1. Build the skill file scanner
1. Build drift detection (text comparison first, AI summary layer second)
1. Build the manifest reader/writer
1. Build the todo directory writer
1. Wire up `claude -p` for AI reconciliation tasks
1. (June 15+) Replace `claude -p` subprocess calls with Agent SDK TypeScript calls
