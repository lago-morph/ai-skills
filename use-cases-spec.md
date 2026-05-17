# Skill Registry Manager — Use Cases

## Status: Pre-Implementation

Companion document to `skill-manager-spec.md`. These are the standard user workflows the app supports. Each can be reviewed and refined independently. Open questions inside each use case are surfaced for the user to resolve before implementation.

**Architecture reminders** (full detail in `skill-manager-spec.md` decisions 0 and 16):

- The app is a **single-page web app on GitHub Pages**. No backend
- Auth: **GitHub OAuth Device Flow** against a registered public OAuth App
- The app **never invokes Claude directly**. All LLM work is delegated to the user's Claude session via labeled GitHub issues in the canonical repo (the **issue protocol**)
- The canonical GitHub repo *is* the database: skills, AGENTS.md fragments, ADRs, proposals, manifests, lineage, and provenance all live there as files

-----

## UC1 — Configure Authentication

**Goal:** the user authorizes the app to read and write GitHub repos on their behalf via OAuth Device Flow.

**Preconditions:**
- User has a GitHub account with access to the repos they want to track
- App is loaded in a browser (iPad Safari, desktop, etc.)

**Main flow:**
1. User opens the app's Settings / Authentication screen
2. App calls `POST https://github.com/login/device/code` with the embedded `client_id` and the requested scopes (`repo`, `read:org`); receives a `device_code`, `user_code`, `verification_uri`, and polling `interval`
3. App displays the `user_code` and a link / QR code to `verification_uri` ("Open `github.com/login/device` on any device and enter `ABCD-1234`")
4. User completes the authorization on github.com
5. App polls `POST https://github.com/login/oauth/access_token` at the returned `interval`, respecting `slow_down` responses, until it receives an `access_token`
6. App persists the token to browser IndexedDB (encryption approach TBD per decision 0 sub-question)
7. App displays auth status, granted scopes, and a "sign out" action

**Variations:**
- First-run: app routes directly to UC1 before any other action
- Storage evicted by Safari ITP after ~7 days inactivity → user re-runs Device Flow
- User signs out → app clears the IndexedDB token entry

**Outputs:**
- Persisted access token usable by all other use cases
- Visible credential health indicator (token present, scopes, last-used time)

**Open questions:**
- Token encryption at rest: passphrase-derived key (WebCrypto + PBKDF2/argon2) vs. plaintext IndexedDB vs. session-only?
- Reuse a personal OAuth App the user owns, or register a fresh one for this project?

-----

## UC2 — Add and Remove Tracked Repositories

**Goal:** the user maintains the list of repositories the app is responsible for managing.

**Preconditions:**
- UC1 completed

**Main flow (add):**
1. User opens the Repositories screen
2. App lists the repos the token has access to (paginated, searchable, filterable by org / topic / language)
3. User selects one or more repos and clicks Add
4. App performs an initial scan of each newly-added repo against its default branch:
   - Skills (using the convention from decision 5)
   - `AGENTS.md` and any referenced sub-files (decision 11)
   - ADR directories (per the patterns in decision 12: `adr/`, `adrs/`, `decisions/`, `docs/adr/`, `architecture/decisions/`)
   - Retrospective sources (case-insensitive substring `retrospect` in directory names per decision 9; UC7 details the harvest)
5. Scan results populate the repo's catalog entry; app shows a summary

**Main flow (remove):**
1. User selects a tracked repo from the list and clicks Remove
2. App confirms — emphasizes that removal does **not** modify the repo on GitHub
3. App removes the repo from the catalog and from any per-repo manifest

**Variations:**
- Bulk add from a GitHub org
- Repo becomes inaccessible (deleted or permissions revoked) → surfaced as a catalog warning, not auto-removed

**Outputs:**
- Tracked repo list updated in the canonical repo
- Initial scan results recorded in the catalog

**Open questions:**
- On remove, hard-delete provenance records or keep as historical (`status: inactive`)?
- Persist scan results between sessions, or rescan on every app open?

-----

## UC3 — Configure a Repository's Composition

**Goal:** for a selected tracked repo, the user picks which skills, AGENTS.md fragments, and ADRs that repo should contain.

**Preconditions:**
- UC2 completed (repo is tracked)
- Canonical libraries (`skills/`, `agents-md/`, `adrs/`) have entries available

**Main flow:**
1. User selects a repo and opens its Composition view
2. View shows three panels (Skills, AGENTS.md Fragments, ADRs) with the canonical libraries on the left and the repo's current selections on the right
3. User adds, removes, or reorders entries (order matters for AGENTS.md fragments)
4. User saves; app updates the per-repo manifest in the canonical repo
5. Changes are **not applied to the target repo yet** — application happens via UC4

**Variations:**
- Browse libraries by tag / category (decision 11) when picking fragments
- Preview the composed `AGENTS.md` before saving (assembled via a `task:compose-agents-md` issue per decision 16, or assembled client-side if fragments are simple concatenation)
- Inherit a template repo's composition as a starting point
- Surface lineage warnings: "entry `skl_x` is `superseded`; on sync, repo will receive its successors instead" (per decision 13)

**Outputs:**
- Updated per-repo manifest in the canonical repo
- Diff between previous and new composition surfaced in the UI for review

**Open questions:**
- One unified manifest per repo (skills + fragments + ADRs) or three separate files (decision 11)?
- Apply on save vs queue-and-apply?

-----

## UC4 — Sync Canonical → Repository (push down)

**Goal:** propagate the canonical state into one or more tracked repos so each repo actually contains what its manifest says it should.

**Preconditions:**
- UC1 completed
- Target repo(s) configured via UC3

**Main flow (single repo):**
1. User opens a repo's detail view and clicks Sync
2. App reads the per-repo manifest, resolves every entry ID through the lineage graph (decision 13), and computes the desired state of the target repo (skill files, ADR files, assembled `AGENTS.md`)
3. App compares desired vs actual state in the target repo and surfaces a diff. For semantic drift summaries (not line-by-line), app opens one `task:drift-summary` issue per drifted entry and waits for Claude's response per decision 16
4. For any drift in the target repo (local changes not in canonical), app offers: overwrite-with-canonical, accept-into-canonical (UC5), or invoke UC6 reconciliation
5. User confirms; app writes changes to the target repo directly via the GitHub API (commit + push, no intermediate workflow)
6. App records the sync timestamp and outcome

**Main flow (bulk):**
1. User clicks Sync All (or selects a subset)
2. App runs syncs in parallel up to the configured concurrency limit (decision 14, proposed: 5)
3. App aggregates results into a single summary view: success counts, drift counts, errors

**Variations:**
- Dry-run mode: compute and display all changes without writing
- Per-repo `auto_refresh: true` flag (decision 2) skips the confirm step for non-drifted entries
- Scheduled bulk sync is a Phase 2 capability (would need a small backend or a scheduled GitHub Action — see Phase 2 in main spec)

**Outputs:**
- Target repo(s) updated to match canonical
- Drift surfaces redirected into UC6 where the user opted in
- Sync history recorded in the canonical repo

**Open questions:**
- Bulk parallelism limit: 5 (decision 14) — adjustable per-user?
- Should drift detection always run as part of sync, or be a separate user-initiated action?
- For batches of drift summaries, open one issue per drifted entry (many small Claude requests) or one rollup issue (one bigger request)?

-----

## UC5 — Sync Repository → Canonical (pull up, with provenance)

**Goal:** ingest the skills, AGENTS.md fragments, and ADRs that already exist in a tracked repo back into the canonical libraries so they can be managed centrally.

**Preconditions:**
- UC2 completed
- Initial scan has identified ingestible artifacts in the repo

**Main flow:**
1. User opens a repo's detail view and clicks Ingest from Repo
2. App lists every artifact found, grouped by type (skills, fragments, ADRs)
3. For each artifact, app determines match-vs-new against the canonical library:
   - Content hash match → exact duplicate of an existing canonical entry
   - For near-matches, app opens a `task:ingest-similarity-check` issue (decision 16) with both versions; Claude returns a similarity verdict; app uses it to classify match-vs-new (decision 14)
   - No match → new entry
4. App presents the proposed disposition per artifact: tag existing (add provenance record), create new (fresh immutable ID), or skip
5. User reviews and adjusts dispositions, then confirms
6. App applies the dispositions to the canonical libraries:
   - **Tag existing:** append a provenance record to the existing entry's frontmatter (`source_repo`, `source_path`, `ingested_at`, `ingested_by`, `content_hash_at_ingest`)
   - **Create new:** add entry with a fresh immutable ID and an initial provenance record
   - **Skip:** record nothing
7. App optionally updates the source repo's manifest to point at the resolved canonical IDs (so future syncs are bidirectional-consistent)

**Variations:**
- Bulk ingest across all tracked repos (initial seeding pass)
- Re-ingest a repo to refresh provenance records — tag-vs-create logic handles dedup
- Inspect the diff that triggered a near-match before confirming; user may prefer to merge differences rather than tag

**Outputs:**
- Canonical libraries gain new entries and / or provenance records
- Provenance trail records every repo where each entry has been seen
- Optional: source repo's manifest updated

**Open questions:**
- Provenance records: in the entry's frontmatter or a separate `provenance.{json,yaml}` file (decision 14)?
- Similarity threshold for "near-match": confidence level reported by Claude vs. a numeric similarity score?
- When ingesting an ADR scavenged from `decisions/` or `docs/adr/`, should the app also propose moving it into the conventional `adrs/` location on the source repo's next sync, or leave the source repo's layout alone?

-----

## UC6 — Guided Reconciliation Across Versions

**Goal:** for a library entry, walk through all its versions (current canonical, git history, sibling versions from tracked repos via provenance, superseded predecessors via lineage) and confirm the current canonical captures every useful element that has ever appeared anywhere.

**Preconditions:**
- UC1 completed
- The entry exists in the canonical library
- Typical (not required): entry has provenance from multiple repos or a lineage trail

**Main flow:**
1. User picks a library entry and clicks Reconcile
2. App gathers every available version:
   - Current canonical (active)
   - Selected git history commits of the canonical entry
   - Versions in tracked repos (per provenance records)
   - Superseded predecessors via lineage
3. App opens a `task:reconcile` issue per decision 16 with all versions referenced (by blob URL) and a structured prompt asking Claude to: inventory the distinct ideas in each version, recommend which ideas the current canonical should retain or absorb, and propose a merged version
4. User goes to their Claude interface, runs the queue, has the conversation directly in the issue's comments. The conversation can be multi-turn — Claude posts intermediate `claude-result` comments with `final: false`, the user replies in-thread, and signals completion with `final: true`
5. App polls and recognizes `final: true`; surfaces the final proposal in the UI
6. User accepts the proposal; app applies the agreed result to the canonical entry, writes a new lineage record per decision 13, and closes the issue with a summary comment

**Variations:**
- Reconcile across repos only (no history walk)
- Reconcile through lineage only (no cross-repo) — for consolidating split/merged entries
- Batch reconcile: pick N entries, open one issue per entry, let the user work through them in one Claude session

**Outputs:**
- One `task:reconcile` issue per reconciled entry, containing the full conversation and the final proposal
- Updated canonical entry on acceptance, with a new lineage record if substantive changes were made

**Open questions:**
- Confirm the label `task:reconcile` (used elsewhere in decision 16)
- Reconciliation triggered outside the app (decision 15 mentions `reconciliation-pending` as a label for *user-initiated* downstream Claude sessions) — is `task:reconcile` the same workflow, or are these two distinct flows? If same, consolidate the label
- Should the app open a single rollup issue for batch reconciliation, or one issue per entry?

-----

## UC7 — Harvest Retrospectives

**Goal:** discover retrospective material in tracked repos, extract proposed skills, AGENTS.md fragments, and ADRs, and write them into the proposal queue with enough enrichment for each proposal to be implemented independently.

**Source formats (per decision 9):**

- **Structured (Mode B of the `self-retrospective` skill):** a `retrospective/` directory tree on a `feat/retrospective-<YYYYMMDD>` feature branch, with the layout:
  ```
  retrospective/
    README.md                          # top-level index with skill priority table
    <skill-name>/
      README.md                        # human motivation
      SPEC.md                          # implementation-grade, self-contained spec
      excerpts.jsonl                   # verbatim session evidence (optional)
      examples/                        # concrete templates (optional)
    agents-md-template/
      README.md
      SPEC.md                          # proposed AGENTS.md rules
  ```
  The skill's quality bar guarantees each `SPEC.md` is self-contained, so skill / fragment proposals can be extracted mechanically with no Claude work
- **Free-form:** any other retrospective markdown (`RETROSPECTIVE.md`, `retros/*.md`, files in any directory whose name contains `retrospect`). Extraction requires Claude via a `task:harvest-retrospective` issue per decision 16

**Preconditions:**
- UC2 completed (repo is tracked)
- Initial scan or branch-list scan has identified at least one retrospective source

**Main flow:**

1. User opens the Retrospectives screen, selects a repo (or "all tracked repos"), and clicks Scan
2. App enumerates retrospective sources:
   - Default branch: directories matching case-insensitive substring `retrospect`
   - Feature branches matching `feat/retrospective-*` (Mode B convention — see open questions for whether to scan branches)
   - For each candidate, classify as Mode B (has `<skill-name>/SPEC.md` subdirectories) or free-form
3. App lists discovered retrospectives with a per-source summary:
   - Mode B: parse `retrospective/README.md` skill-index table — display skill names + priorities + one-line summaries (no Claude work needed)
   - Free-form: display filename + a Claude-generated one-line summary (opens a small `task:harvest-retrospective` summary issue, or batch all free-form summaries into one issue)
4. User picks which retrospectives to harvest, then clicks Harvest
5. For each selected source, the app extracts proposals:

   **Mode B path (no Claude needed for skills / fragments):**
   - For each `retrospective/<skill-name>/` subdirectory, create `proposals/skills/<skill-name>.md` with:
     - YAML frontmatter: `source_repo`, `source_branch`, `source_path: retrospective/<skill-name>/`, `harvested_at`, `status: proposed`, `proposal_type: skill`, `priority` (from `retrospective/README.md` skill-index table)
     - Body: verbatim contents of `SPEC.md` (self-contained per the skill's quality bar)
     - `## Motivation` section: contents of `README.md`
     - `## Session evidence` section: verbatim records from `excerpts.jsonl` if present
   - For `retrospective/agents-md-template/SPEC.md`, extract proposed AGENTS.md rules. The skill emits rules as numbered `N. **<Rule name>.** "..."` blocks. Two options (decision 9 sub-question):
     - Split: one entry in `proposals/agents-md/` per rule, with the rule's "grounded in" reference preserved
     - Composite: one entry containing the whole template, left for later splitting
   - **ADR derivation:** Mode B does not directly emit ADRs. App opens one `task:extract-adrs` issue per retrospective with the full `retrospective/` tree referenced; Claude identifies architecture-level decisions in Part 1 narrative and section 3.6 scope decisions, drafts each as a self-contained ADR proposal (already enriched with context per the issue's `expected_output`), and posts a `claude-result` block. App writes the resulting ADRs into `proposals/adrs/` with provenance

   **Free-form path (Claude for everything):**
   - Open one `task:harvest-retrospective` issue per source with the retrospective markdown as the input. `expected_output` instructs Claude to return a single `claude-result` block containing structured arrays of proposed skills, proposed AGENTS.md rules, and proposed ADRs in the same schema the app uses for Mode B output
   - App writes the resulting entries into the proposal queue with provenance

6. Both paths: deduplicate against existing proposals per decision 9 (hash for exact matches, `task:proposal-fingerprint` for near-matches across sources)
7. App reports a harvest summary: N skills, M fragments, K ADRs added; X duplicates skipped

**Variations:**
- Bulk harvest across all tracked repos and all `feat/retrospective-*` branches (rate-limit aware per decision 14)
- Re-harvest a previously-harvested source: provenance records track `content_hash_at_ingest`, so re-harvest skips unchanged sources and refreshes proposals whose source changed
- Watch mode (Phase 2): subscribe to push events on tracked repos and auto-harvest on new retrospective material — requires a webhook listener (out of scope for v0.x given pure-SPA hosting)

**Outputs:**
- New entries in `proposals/skills/`, `proposals/agents-md/`, `proposals/adrs/` per source
- Full provenance trail (source repo, branch, path, content hash, harvest date) on every proposal
- Harvest history record per source so re-harvest can skip unchanged material

**Open questions:**
- Scan `feat/retrospective-*` branches in addition to the default branch?
- AGENTS.md template: split into per-rule fragments at harvest, or import as a composite fragment?
- Run ADR extraction (`task:extract-adrs`) only on Mode B sources, or also on free-form sources where the body might mention architecture decisions?
- Configurable additional match patterns per repo (e.g. a repo that uses `LESSONS.md` at root instead of a `retrospective/` directory)?

-----

## Use-Case Coverage Matrix

| Use case | Touches canonical libraries | Touches manifests | Opens Claude issues | Writes to target repos |
|----------|----------------------------|-------------------|---------------------|------------------------|
| UC1 — Auth | — | — | — | — |
| UC2 — Track repos | — | — | — | — |
| UC3 — Configure composition | Read | Write per-repo | Optional (`task:compose-agents-md` preview) | — |
| UC4 — Sync canonical → repo | Read | Read | Optional (`task:drift-summary`, `task:reconcile`) | Yes |
| UC5 — Sync repo → canonical | Write (add or tag) | Optional update | Yes (`task:ingest-similarity-check`) | Optional manifest update |
| UC6 — Reconcile | Read all versions; write on accept | — | Yes (`task:reconcile`) | — |
| UC7 — Harvest retrospectives | Write to `proposals/` | — | Conditional (Mode B: only `task:extract-adrs`; free-form: `task:harvest-retrospective`) | — |
