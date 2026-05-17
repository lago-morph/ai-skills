# Skill Registry Manager — Project Specification

## Status: Pre-Implementation

**Companion documents:**
- `use-cases-spec.md` — the standard user workflows (UC1–UC7). Reviewable independently from this spec.

> **Architecture summary:** the app is a single-page web app hosted on GitHub Pages (decision 0). It talks to the GitHub REST API directly from the browser and uses a dedicated GitHub repo as its database. It **never invokes Claude directly** — instead it creates GitHub issues with structured task descriptions, and the user tells their Claude session (Claude Code CLI, Claude.ai with GitHub MCP, Claude Desktop, etc.) to process them. Claude posts results as comments; the app polls for them. See decisions 0 and 16 for full detail.

-----

## DECISIONS REQUIRED BEFORE IMPLEMENTATION BEGINS

These must be resolved before writing any code. Claude Code should prompt the user for each remaining open item before proceeding.

> **Status overview:** Decisions 0, 6, 7, 8 are resolved (0 decided; 6 and 8 answered by 0; 7 superseded by 16) and decision 4 is superseded by 16. Decisions 1, 2, 3, 5, 9–16 are still open.

### 0. Hosting Architecture and Auth — *DECIDED*

**Hosting:** Single-page web app hosted as **static files on GitHub Pages**.

**Auth:** **GitHub OAuth Device Flow**, using a registered public OAuth App. No `client_secret` needed (Device Flow is designed for clients that cannot keep secrets, so the `client_id` is safe to embed in the JS bundle).

**Implications:**
- No backend in v0.x. The SPA talks directly to the GitHub REST API (CORS-supported for authenticated requests). All persistent state lives in the canonical GitHub repo — GitHub *is* the database
- No `claude -p`, no Agent SDK, no `ANTHROPIC_API_KEY`. Claude work flows through GitHub issues consumed by whatever Claude interface the user is in (decision 16)
- Works on iPad Safari and every desktop browser. iPad Safari ITP evicts script-writable storage after ~7 days inactivity; user re-runs Device Flow after a gap

**Device Flow specifics:**
- Register a public OAuth App on the canonical repo's owning account. Capture `client_id` and embed in the SPA
- Requested scopes: `repo` (read/write tracked repos), `read:org` (to discover repos in user's orgs). Confirm scope set
- Flow: SPA calls `POST https://github.com/login/device/code` with `client_id` and `scope` → receives `device_code`, `user_code`, `verification_uri`, `expires_in`, `interval` → SPA displays `user_code` and a link/QR to `verification_uri` → SPA polls `POST https://github.com/login/oauth/access_token` at `interval` until success → receives `access_token`
- Token stored client-side in IndexedDB. Encryption approach still open (see sub-questions below)

**Remaining sub-questions within the decided direction:**
- **SPA framework:** React + Vite (recommended for documented Pages deployment and small bundle), Svelte + SvelteKit static export, or vanilla TS?
- **Token persistence:** passphrase-encrypted IndexedDB (user supplies passphrase on app open; WebCrypto + PBKDF2/argon2 to derive key) vs. plaintext IndexedDB (simpler; relies on browser-level protection only) vs. session-only (re-run Device Flow each session)?
- **GitHub OAuth App registration:** does the user own a personal OAuth App they want to reuse, or register a fresh one specifically for this app?

**Future re-architecture (deferred until the app needs to drive agents directly):**
- **GitHub Actions** triggered by `repository_dispatch` from the SPA — stays on GitHub infra, cold-start 10–30s, 2,000 free Action minutes per month on private repos
- **AWS Lambda** — sub-second response, more setup. Right answer if Action latency proves a problem or long-lived stateful agents are needed
- User prefers GitHub Actions if viable; revisit when the Agent SDK becomes part of the design

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

### 6. GitHub Authentication — *ANSWERED by decision 0*

> Resolved: **GitHub OAuth Device Flow** via a registered public OAuth App. Token stored in browser IndexedDB (encryption approach is the one remaining sub-question under decision 0). No PAT, no `safeStorage`. Original text retained below for history.

- The Electron app needs a GitHub token
- Scope needed: at minimum `repo` (read/write to private repos)
- How is the token stored? Electron's `safeStorage` API (OS keychain) is recommended — confirm this is acceptable
- Does the user have a GitHub Personal Access Token (classic) or will they use a fine-grained token?

### 7. Agent SDK Integration (June 15, 2026) — *SUPERSEDED by decision 16*

> This decision is obsoleted by the issues-as-message-bus model in decision 16. The app no longer needs to call Claude directly — the user's Claude session is the agent. The Agent SDK may become relevant later if the app evolves to drive agents itself (see decision 0's "Future re-architecture" section), but it is not part of v0.x. Retained below for historical reference only.

- On June 15, the todo directory + manual Claude Code step gets replaced by Agent SDK calls
- Max 20x plan = $200/month Agent SDK credit
- One-time opt-in required at claude.ai before June 15
- Confirm: is the intent to replace the todo directory entirely, or keep it as a fallback?

### 8. Target Platforms — *ANSWERED by decision 0*

> Resolved: **modern browsers**. Primary targets: iPad Safari, desktop Chrome / Firefox / Safari / Edge. No native packaging, no code signing, no OS-specific build artifacts. Original text retained below for history.

- Windows confirmed
- macOS also? (affects packaging and code-signing decisions)

### 9. Retrospective Harvesting

See **UC7** in `use-cases-spec.md` for the full workflow. The harvester recognizes two source formats:

- **Structured (Mode B output of the `self-retrospective` skill in this repo).** Produced as a `retrospective/` directory tree on a `feat/retrospective-<YYYYMMDD>` branch. Layout: `retrospective/README.md` (skill-index table), `retrospective/<skill-name>/{README.md, SPEC.md, excerpts.jsonl?, examples/?}` per proposed skill, and `retrospective/agents-md-template/{README.md, SPEC.md}` for proposed AGENTS.md rules. The skill's quality bar requires each `SPEC.md` to be self-contained, so structured-source extraction needs no Claude work for skill / fragment proposals
- **Free-form.** Any other markdown that looks like a retrospective (`RETROSPECTIVE.md`, `retros/*.md`, `*retrospect*.md`). Extraction requires Claude via a `task:harvest-retrospective` issue (decision 16)

Open items:

- **Directory matching pattern:** case-insensitive substring `retrospect` (catches `retrospective/`, `retros/`, `Retrospect/`, `session-retrospectives/`). Confirm
- **Branch scanning:** scan `feat/retrospective-*` branches (Mode B convention) in addition to the default branch? Pro: catches freshest material before merge. Con: rate-limit cost. Confirm
- **Free-form report identification:** by conventional filename (`RETROSPECTIVE.md`, `report.md`), the newest `.md`, or every `.md` in a matched directory? Confirm
- **Deduplication:** hash of `(source_repo, source_path, content_hash)` for exact-match; for cross-retrospective same-proposal detection, Claude-generated fingerprint via a `task:proposal-fingerprint` issue. Confirm
- **AGENTS.md template handling:** Mode B emits a single `agents-md-template/SPEC.md` containing numbered rules. Split into per-rule fragments at harvest time (one entry in `proposals/agents-md/` per rule) or import as one composite fragment? Confirm
- **ADR extraction from Mode B:** the self-retrospective skill does not directly emit ADR proposals — they must be derived from Part 1 narrative or scope-decision sections via a `task:extract-adrs` issue per retrospective. Confirm this approach
- **Frequency:** manual user-triggered, scheduled scan, or both?

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
- **ADR enrichment requirement:** each ADR proposal must include enough context from its source retrospective that it can be implemented without re-reading the original report. Enrichment is performed by Claude during harvest via a `task:enrich-adr-proposal` issue (decision 16). Confirm
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

The guided reconciliation workflow (UC6) uses the standard issue protocol from decision 16 with the `task:reconcile` label. Reconciliation is not a separate channel; it is one task type in the unified issue queue. The user's Claude session processes `task:reconcile` issues the same way it processes any other `task:*` label.

Remaining sub-questions:

- **Single task type or two-stage flow?** Decision 16's `task:reconcile` covers the in-app reconciliation flow. An earlier draft proposed a separate `reconciliation-pending` label for *user-initiated downstream sessions* (someone running `gh issue list --label task:reconcile` outside the app's flow). These are the same issues — the label is shared. Confirm
- **Fallback to a working-directory file** (e.g. `proposals/reconciliations/<entry-id>-<timestamp>.md`) for cases where issue creation isn't appropriate (rare; mostly when GitHub is down)
- **Issue body format** is specified by decision 16's `task:reconcile` schema (entry ID, versions compared, expected output). The `claude-result` block returned by Claude contains the inventory of distinct ideas and recommendations
- **Conversation continuation:** the issue itself holds the multi-turn conversation per decision 16 (Claude posts `final: false` until the user signals `final: true`). The accepted result is written back to the canonical entry by the app; the issue is closed with a summary comment

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
  - `task:drift-summary` — semantic diff of two versions of an entry
  - `task:harvest-retrospective` — extract proposals from a free-form retrospective (UC7)
  - `task:extract-adrs` — identify and draft ADR proposals from a retrospective's narrative (UC7)
  - `task:enrich-adr-proposal` — add retrospective context to a proposed ADR
  - `task:proposal-fingerprint` — generate a normalized fingerprint for cross-source dedup
  - `task:reconcile` — guided reconciliation (UC6)
  - `task:ingest-similarity-check` — repo→canonical similarity comparison (UC5)
  - `task:compose-agents-md` — assemble an AGENTS.md preview from selected fragments
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

Issue title: `[task:drift-summary] Compare canonical skill skl_a3f9k2 against owner/repo-a copy`

Labels: `task:drift-summary`

Issue body:

````markdown
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
expected_output: |
  A `claude-result` block containing JSON with fields:
    summary: 1-3 sentence semantic summary of the differences
    categories: list of difference categories (e.g. "expanded triggers", "wording")
    recommendation: "canonical-wins" | "target-wins" | "merge-needed"
---

Please compare these two versions of the same skill and post a `claude-result`
block describing the semantic differences. This is fully automated input; reply
only with the result block.
````

Claude's response comment:

````markdown
```claude-result
{
  "summary": "Target adds two new trigger keywords (.dotx, .docm) and rephrases the 'when to use' section more concisely. Canonical is otherwise identical.",
  "categories": ["expanded triggers", "wording"],
  "recommendation": "merge-needed",
  "final": true
}
```
````

-----

## PROJECT OVERVIEW

**Name (working title):** Skill Registry Manager

**What it is:** A browser-based single-page web application, hosted as static files on GitHub Pages, that manages Claude skill files (SKILL.md), AGENTS.md fragments, and Architecture Decision Records across multiple GitHub repositories. It provides a canonical source of truth in a dedicated GitHub repo, drift detection, AI-assisted reconciliation (delegated to whatever Claude interface the user is in, via GitHub issues), proposal harvesting from retrospectives, and modular composition of skills / fragments / ADRs per repo.

**Why it exists:** The user works across multiple platforms (Claude web, Claude for Windows, Claude Code CLI, iPad, iPhone) and uses Claude skills + AGENTS.md fragments + ADRs stored in individual repositories. When any of these is updated in one repo, copies in other repos diverge. There is currently no way to detect or reconcile this drift without manually inspecting each repo. The app being a browser SPA means it is usable from any of those platforms, including iPad.

-----

## ARCHITECTURE

### Components

#### 1. Canonical Store (GitHub Repository)

- A dedicated GitHub repository that is the single source of truth for skills, AGENTS.md fragments, ADRs, manifests, proposals, lineage, and provenance
- Git history serves as the full version history
- Proposed layout (each directory name still subject to confirmation in its respective decision):
  - `skills/` — canonical skill library (decision 5)
  - `agents-md/` — canonical AGENTS.md fragment library (decision 11)
  - `adrs/` — canonical ADR library (decision 12)
  - `proposals/{skills,agents-md,adrs}/` — harvested-but-not-yet-implemented entries (decision 10)
  - Per-repo manifests, location TBD (decisions 2 and 11)
  - Lineage data: per-entry frontmatter + optional derived cache (decision 13)
- GitHub Issues in this repo serve as the message bus to the user's Claude session (decision 16)

#### 2. SPA on GitHub Pages

- Static HTML / CSS / JS bundle hosted from a GitHub Pages site
- GitHub Pages serves arbitrary JavaScript; the browser executes it like any other web app. Full SPA interactivity (state, dynamic rendering, IndexedDB, WebCrypto, fetch) is available
- Talks directly to the GitHub REST API via Octokit-rest browser build. GitHub's REST API supports CORS for authenticated requests, so `fetch('https://api.github.com/...')` with the Device Flow token in the `Authorization` header works directly — no proxy required
- Auth: GitHub OAuth Device Flow against a registered public OAuth App; access token stored in browser IndexedDB
- Renders UI, performs all reads/writes against the canonical repo and tracked repos, creates issues, polls issue comments for Claude responses
- No backend; no server-side code. Anything that needs server-side execution (Lambda, scheduled jobs) is out of scope for v0.x

#### 3. User's Claude Interface (out-of-process agent)

- The app **never invokes Claude directly**. It writes labeled issues into the canonical repo containing structured task descriptions (decision 16)
- The user, working in their preferred Claude interface (Claude Code CLI, Claude.ai with the GitHub MCP connector, Claude Desktop), tells Claude: "process the open issues with label `task:<type>`"
- Claude reads each issue, performs the work, posts results as a comment containing a fenced `claude-result` block
- The SPA polls the issue's comments endpoint for the result and continues
- For multi-turn tasks (reconciliation), the conversation happens inside the issue and the SPA waits for `final: true`

-----

## FEATURES

### Phase 1 — Core (Build Now)

#### Repo Cataloging

- Authenticate via GitHub OAuth Device Flow (decision 0)
- Discover and list all repos the token has access to
- Scan each repo for skills, AGENTS.md fragments, ADRs, and retrospective sources (per decisions 5, 11, 12, 9)
- Display a catalog: which entries exist in which repos, and the lineage / provenance status of each

#### Drift Detection

- Compare each repo's copy of an entry against the canonical version
- Flag repos where the entry has diverged
- For semantic summaries (not line-by-line diff), open a `task:drift-summary` issue per decision 16 and surface Claude's response in the UI

#### Manifest Management

- Read and write the per-repo and master manifests (decision 2)
- UI to assign skills, AGENTS.md fragments, and ADRs to repos (UC3)
- UI to set auto-refresh policy per repo

#### Issue Creator and Response Poller

- Generate structured GitHub issues against the canonical repo per decision 16
- Each task type has its own label and YAML-frontmatter body schema
- Poll the issue's comments endpoint for a `claude-result` fenced block; surface the response in the UI; close the issue on `final: true`
- "Pending issues" panel surfaces queued work so the user knows what to ask Claude to process

#### Skill Reconciliation Workflow

- When drift is detected, open a `task:reconcile` issue (decision 16) containing every relevant version (canonical, target, history, sibling repos)
- User drives the conversation with Claude inside the issue; the app waits for `final: true` and applies the agreed result to the canonical entry (with a new lineage record per decision 13)

#### Retrospective Harvester

- See UC7 in `use-cases-spec.md` for the full workflow
- Discovers structured Mode B output (`retrospective/` tree from the `self-retrospective` skill) and free-form retrospectives across tracked repos
- Structured sources are parsed directly with no Claude work for skill / fragment proposals; ADR derivation and free-form harvesting open `task:extract-adrs` / `task:harvest-retrospective` issues per decision 16
- Writes proposals into the proposal queue with full provenance; deduplicates against prior harvests

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
- All Claude-touching work in both sync directions uses the issue protocol (decision 16) — `task:drift-summary` for semantic drift, `task:ingest-similarity-check` for repo→canonical similarity, `task:reconcile` for guided reconciliation. See UC4, UC5, UC6 in `use-cases-spec.md`

### Phase 2 — Optional Backend for Direct Agent Driving (Future)

The v0.x architecture delegates all Claude work to the user's own Claude session via labeled issues (decision 16). A future phase may add an automated agent that processes issues without the user manually telling Claude "go work the queue." Options when that time comes:

- **GitHub Actions** triggered by issue events or scheduled cron — Agent SDK runs inside the Action runner, polls the issue queue, posts results. Stays on GitHub infra, cold-start ~10–30s
- **AWS Lambda** triggered by GitHub webhooks — lower latency, more setup. Right answer if Action latency or runner limits become problems

This phase is not part of v0.x and does not affect the SPA architecture.

### Phase 3 — Skill Improvement UI (Future / Version 2)

- Interactive editor for improving skills
- Side-by-side comparison of skill versions
- Open a `task:suggest-improvements` issue (decision 16) asking Claude for targeted improvement proposals
- Publish improved version back to canonical with a new lineage record per decision 13

-----

## TECHNOLOGY DECISIONS

|Concern             |Decision                                |Notes                                                                       |
|--------------------|----------------------------------------|----------------------------------------------------------------------------|
|Hosting             |GitHub Pages (static)                   |Decision 0                                                                  |
|App shell           |Single-page web app                     |Pure browser, no backend                                                    |
|SPA framework       |TBD — React + Vite suggested            |Decision 0 sub-question; React + Vite recommended for Pages and bundle size |
|GitHub API client   |Octokit (`@octokit/rest`, browser build)|CORS supported with token auth                                              |
|Auth                |GitHub OAuth Device Flow                |Decision 0; public OAuth App; no `client_secret` exposure                   |
|Token storage       |Browser IndexedDB                       |Encryption approach TBD (decision 0 sub-question)                           |
|Claude integration  |GitHub issues as message bus            |Decision 16; app never invokes Claude directly                              |
|Canonical store     |Dedicated GitHub repository             |TBD — which repo (decision 3)                                               |

-----

## KNOWN CONSTRAINTS & RISKS

- **iPad Safari ITP:** Script-writable storage (IndexedDB) is evicted after ~7 days of inactivity. The user re-runs OAuth Device Flow after a gap. Acceptable; surface clearly in the UI when re-auth is needed.
- **GitHub Pages is static-only:** No server-side code. If a backend is ever needed (e.g. webhook listener for low-latency issue completion), it has to live elsewhere — GitHub Actions, a Cloudflare Worker, or a small Lambda.
- **GitHub OAuth Device Flow polling:** Polling interval is dictated by the response (commonly 5s). The SPA must respect it or risk being rate-limited (`slow_down` response).
- **Anthropic ToS:** Do not attempt to automate the Claude.ai web interface (e.g. via Playwright). Violates terms and risks account suspension.
- **Skill semantic identity:** Skills are not line-by-line comparable. All diff/merge is AI-assisted via the issue queue, not mechanical.
- **GitHub API rate limits:** 5,000 requests/hour for authenticated users. Cataloging many repos in bulk must be throttled. Bulk sync (UC4) capped at ~5 concurrent per decision 14.
- **Issue queue latency:** Because Claude work is gated on the user telling Claude to process the queue, there is no real-time guarantee. UI should surface "N pending issues" clearly so the user knows when work is queued vs. complete.
- **Token compromise blast radius:** A leaked Device Flow access token gives whoever holds it the granted scopes against the user's repos until rotated. Minimize scope; surface token rotation in the UI.

-----

## SESSION CONTEXT (for Claude Code handoff)

> **Note:** These bullets capture the original Claude.ai session that produced the first draft of this spec. The architecture has since been clarified by decisions 0 and 16. The still-relevant items are flagged below; the rest are marked *(superseded)*.

- The user has a **Claude Max subscription** (likely 20x tier) and does **not** have a separate Anthropic API key — *still relevant context; informs the issue-protocol design since the app does not need Claude API access*
- *(superseded)* The user is building for Windows using Electron — **now: SPA on GitHub Pages, browser targets (decision 0)**
- *(superseded)* The user confirmed the June 15, 2026 Agent SDK credit announcement — *Agent SDK is not part of v0.x (decision 16 replaces it with the issue protocol); may return in a future re-architecture per decision 0's "Future re-architecture" notes*
- *(superseded)* The intended build strategy is: build with `claude -p` now, migrate to Agent SDK on June 15 — **now: app never invokes Claude; user's Claude session processes labeled issues (decision 16)**
- *(superseded)* Claude Code CLI non-interactive mode (`claude -p`) is the correct bridge mechanism — **same supersession**
- Using Playwright to automate Claude.ai was explicitly ruled out (ToS violation) — *still relevant constraint*
- Using Claude Cowork was ruled out (not programmable) — *still relevant context*
- *(superseded as a concern)* There is currently no IPC mechanism to inject prompts into a running interactive Claude Code session — *not a problem under decision 16, since the user manually drives Claude to process the queue*
- The GitHub MCP connector was **not connected** in Claude.ai at time of writing — *still relevant; connecting it makes decision 16's workflow much smoother for iPad use*

-----

## SUGGESTED FIRST STEPS FOR CLAUDE CODE

1. Present the "Decisions Required" section to the user and collect answers for the still-open items. Status: decision 0 decided; 6 and 8 answered by 0; 4 and 7 superseded by 16; 1, 2, 3, 5, 9–16 still open
1. Once decisions are recorded, update this spec with the confirmed answers
1. Register a public GitHub OAuth App on the canonical-repo-owning account; capture `client_id`
1. Scaffold the SPA (suggested: React + Vite for a clean GitHub Pages deployment story)
1. Implement OAuth Device Flow against the registered app; persist the token to IndexedDB
1. Implement Octokit-rest repo cataloging via the stored token
1. Build the entry scanners (skills, AGENTS.md fragments + sub-files, ADRs, retrospectives) per the conventions in decisions 5, 11, 12, 9
1. Build the manifest reader/writer (decision 2; per-repo + master)
1. Build the issue creator and response poller per decision 16, with the agreed task labels
1. Build drift detection: file fetch + per-entry comparison; for semantic summaries, open a `task:drift-summary` issue and wait for the result
1. Build the proposals queue UI (decision 10): list, review, accept, reject, promote
1. Build the per-repo composition UI (UC3): skills + AGENTS.md fragments + ADRs side-by-side
1. Build the sync flows (UC4 canonical → repo, UC5 repo → canonical with provenance)
1. Build the guided reconciliation flow (UC6) using the issue protocol
1. Deploy to GitHub Pages via Actions workflow
