# Skill Registry Manager — Project Specification

## Status: Pre-Implementation

-----

## DECISIONS REQUIRED BEFORE IMPLEMENTATION BEGINS

These must be resolved before writing any code. Claude Code should prompt the user for each of these before proceeding.

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

### 4. Todo Directory Format

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

### 7. Agent SDK Integration (June 15, 2026)

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
