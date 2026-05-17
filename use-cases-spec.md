# Skill Registry Manager — Use Cases

## Status: Pre-Implementation

Companion document to `skill-manager-spec.md`. These are the standard user workflows the app supports. Each use case can be reviewed and refined independently. Open questions inside each use case are surfaced for the user to resolve before implementation.

> **Cross-cutting note:** the hosting architecture (Electron desktop vs SPA on GitHub Pages + GitHub Actions) is still open — see decision 0 in `skill-manager-spec.md`. Use cases are written in technology-neutral language where possible; UI specifics will firm up once decision 0 is resolved.

-----

## UC1 — Configure Authentication

**Goal:** the user provides the credentials the app needs to talk to GitHub (and, in the GitHub Pages variant, to authorize the Action workflow that runs Claude).

**Preconditions:**
- User has a GitHub account with access to the repos they want to track
- User has a Claude Max subscription (and, for the Pages variant, has decided between Max OAuth token vs pay-as-you-go API key for the Action)

**Main flow:**
1. User opens the app's Settings / Authentication screen
2. User enters a GitHub credential — either via OAuth Device Flow (browser variant, iPad-friendly) or by pasting a fine-grained Personal Access Token with `repo` scope
3. App validates the credential against the GitHub API and reports scope / expiry / rate-limit status
4. App persists the credential — OS keychain via `safeStorage` (Electron variant) or encrypted IndexedDB (SPA variant)
5. User confirms (or rotates / removes) the credential at any time from the same screen

**Variations:**
- First-run flow: app prompts for credentials before any other action is possible
- Token expiry: app surfaces a banner and disables write operations until re-auth
- (SPA variant) For the Action workflow to run Claude, the user adds `CLAUDE_CODE_OAUTH_TOKEN` (preferred) or `ANTHROPIC_API_KEY` as a repo secret on the canonical repo. The app links the user to the GitHub Settings page rather than handling secrets itself

**Outputs:**
- Validated, persisted credential usable by all other use cases
- Visible credential health indicator

**Open questions:**
- For the SPA variant, OAuth Device Flow vs pasted PAT — both, or pick one?
- Token persistence in browser: passphrase-encrypted IndexedDB or session-only?

-----

## UC2 — Add and Remove Tracked Repositories

**Goal:** the user maintains the list of repositories the app is responsible for.

**Preconditions:**
- UC1 completed: app has working GitHub credentials

**Main flow (add):**
1. User opens the Repositories screen
2. App lists the repos the credential has access to (paginated, searchable)
3. User selects one or more repos and clicks Add
4. App performs an initial scan of each newly-added repo:
   - Skills present (using the convention from decision 5)
   - `AGENTS.md` and any referenced sub-files
   - ADR directories (using the patterns from decision 12)
   - Retrospective directories (case-insensitive `*retrospect*` match per decision 9)
5. Scan results populate the repo's catalog entry; app surfaces a summary

**Main flow (remove):**
1. User selects a tracked repo from the list and clicks Remove
2. App confirms — emphasizes that removal **does not** modify the repo on GitHub
3. App removes the repo from the catalog, the per-repo manifest, and any provenance records (or marks them inactive — see open questions)

**Variations:**
- Bulk add from a GitHub org
- Repo became inaccessible (deleted, perms revoked) → surface as a catalog warning, do not auto-remove
- Filter the addable list by org / topic / language

**Outputs:**
- Tracked repo list updated
- Initial scan results recorded in the catalog
- (Remove) Catalog entry archived

**Open questions:**
- On remove, hard-delete the repo's provenance records or keep them as historical (`status: inactive`)?
- Should the catalog persist scan results between runs or refresh on every app launch?

-----

## UC3 — Configure a Repository's Composition

**Goal:** for a selected tracked repo, the user picks exactly which skills, AGENTS.md fragments, and ADRs that repo should contain.

**Preconditions:**
- UC2 completed: repo is in the tracked list
- Canonical libraries (`skills/`, `agents-md/`, `adrs/`) have entries available

**Main flow:**
1. User selects a repo from the tracked list and opens its Composition view
2. View shows three panels (Skills, AGENTS.md Fragments, ADRs) with the canonical libraries on the left and the repo's current selections on the right
3. User adds, removes, or reorders entries (order matters for AGENTS.md fragments)
4. User saves; app updates the per-repo manifest in the canonical repo
5. Changes are **not applied to the target repo yet** — application happens via UC4 (Sync canonical → repo)

**Variations:**
- Browse libraries by tag/category (decision 11) for fragment selection
- Preview the composed `AGENTS.md` before saving
- Inherit from a template repo's composition as a starting point
- Surface lineage warnings: "this entry is `superseded`; on sync, repo will receive its successors instead" (per decision 13)

**Outputs:**
- Updated per-repo manifest in the canonical repo
- Diff between previous and new composition surfaced in the UI for review

**Open questions:**
- One unified manifest file per repo (skills + fragments + ADRs) or three separate files?
- Should add/remove operations queue (apply on save) or write through immediately?

-----

## UC4 — Sync Canonical → Repository (push down)

**Goal:** propagate the canonical state into one or more tracked repos so each repo actually contains what its manifest says it should.

**Preconditions:**
- UC1 completed
- Target repo(s) configured via UC3

**Main flow (single repo):**
1. User opens a repo's detail view and clicks Sync
2. App reads the per-repo manifest, resolves every entry ID through the lineage graph (decision 13), and computes the desired state of the target repo (skill files, ADR files, assembled `AGENTS.md`)
3. App compares desired vs actual state in the target repo and surfaces a diff
4. For any drift in the target repo (local changes not in canonical), app offers: overwrite-with-canonical, accept-into-canonical, or invoke UC6 reconciliation
5. User confirms; app writes changes to the target repo via the GitHub API
   - (Electron variant) Direct write
   - (SPA variant) App commits a task file under `tasks/` in the canonical repo; the GitHub Actions workflow picks it up and performs the writes against the target repo
6. App records the sync timestamp and outcome

**Main flow (bulk):**
1. User clicks Sync All (or selects a subset of tracked repos)
2. App runs syncs in parallel up to the configured concurrency limit (decision 14, proposed: 5)
3. App aggregates results into a single summary view: success counts, drift counts, errors

**Variations:**
- Dry-run mode: compute and display all changes without writing
- Scheduled bulk sync (nightly) via cron or scheduled GitHub Actions workflow
- Per-repo `auto_refresh: true` flag (decision 2) — skip the manual confirm step

**Outputs:**
- Target repo(s) updated to match canonical
- Drift surfaces redirected into UC6 where the user opted in
- Sync history recorded for audit

**Open questions:**
- Bulk parallelism limit: 5? Adjustable per-user?
- Should drift detection be a separate user-initiated step or always run as part of sync?
- For the SPA variant: how does the browser learn when an Action-driven sync completes — poll workflow runs API, poll target commits, or webhook → Pages rebuild?

-----

## UC5 — Sync Repository → Canonical (pull up, with provenance)

**Goal:** ingest the skills, AGENTS.md fragments, and ADRs that already exist in a tracked repo back into the canonical libraries so they can be managed centrally.

**Preconditions:**
- UC2 completed: repo is tracked
- Initial scan from UC2 has identified ingestible artifacts in the repo

**Main flow:**
1. User opens a repo's detail view and clicks Ingest from Repo
2. App lists every artifact found in the repo, grouped by type (skills, fragments, ADRs)
3. For each artifact, app determines match-vs-new against the canonical library:
   - Content hash match → exact duplicate of an existing canonical entry
   - Claude similarity check (decision 14) → near-match of an existing canonical entry
   - No match → new entry
4. App presents the user with the proposed disposition for each artifact: tag existing (with this repo as additional provenance), create new (with a fresh immutable ID), or skip
5. User reviews and adjusts dispositions, then confirms
6. App applies the dispositions to the canonical libraries:
   - **Tag existing:** append a provenance record to the existing entry's frontmatter (`source_repo`, `source_path`, `ingested_at`, `ingested_by`, `content_hash_at_ingest`)
   - **Create new:** add the entry to the appropriate library with a fresh immutable ID and an initial provenance record
   - **Skip:** record nothing
7. App optionally updates the source repo's manifest to point at the resolved canonical entries (so future syncs are bidirectional-consistent)

**Variations:**
- Bulk ingest across all tracked repos: useful for an initial seeding pass
- Re-ingest a repo to refresh provenance records (existing tag-vs-create logic handles dedup)
- Inspect the diff that triggered a near-match before confirming — user may want to merge differences rather than just tag

**Outputs:**
- Canonical libraries gain new entries and/or provenance records
- Provenance trail records every repo where each entry has been seen
- Optional: source repo's manifest updated

**Open questions:**
- Provenance records: in the entry's frontmatter or a separate `provenance.{json,yaml}` file (decision 14)?
- Similarity threshold for "near-match": confidence level reported by Claude, or a numeric similarity score?
- When ingesting an ADR scavenged from a `decisions/` or `docs/adr/` directory, should the harvester also propose moving it into the conventional `adrs/` location in the source repo on the next sync, or leave the source repo's layout alone?

-----

## UC6 — Guided Reconciliation Across Versions

**Goal:** for a library entry, walk through all its versions (current canonical, older git history, sibling versions tagged via UC5 from various tracked repos, superseded predecessors via lineage) and confirm the current canonical version captures every useful element that's ever appeared anywhere.

**Preconditions:**
- UC1 completed
- The entry exists in the canonical library
- Optional but typical: the entry has provenance records from multiple repos (UC5) or a lineage trail with superseded predecessors (decision 13)

**Main flow:**
1. User picks a library entry from the Skills / Fragments / ADRs list and clicks Reconcile
2. App gathers every available version:
   - Current canonical (active)
   - Git history of the canonical entry (selected commits)
   - Versions currently present in tracked repos (per provenance records)
   - Superseded predecessors via lineage
3. App sends all versions to Claude with a structured prompt asking for: an inventory of distinct ideas present in each version, plus a recommendation on which ideas the current canonical should retain or absorb
4. App presents Claude's inventory and recommendations in the UI
5. User accepts, edits, or rejects each recommendation in conversation with Claude
6. When the user is satisfied, app captures the result as either:
   - **(Recommended, default)** a GitHub issue opened against the canonical repo with label `reconciliation-pending` (or the label confirmed in decision 15), body containing the entry ID, versions compared, recommendations, and the user's decisions
   - A markdown file in a working directory (`proposals/reconciliations/<entry-id>-<timestamp>.md`)
7. A separate Claude Code session (run by the user later, e.g. `gh issue list --label reconciliation-pending`) picks up the issue, applies the agreed changes to the canonical entry, and closes the issue (or opens a PR) — conversationally if needed

**Variations:**
- Reconcile across repos only (no history walk) when the immediate goal is cross-repo divergence
- Reconcile through lineage only (no cross-repo) when consolidating split/merged entries
- Reconcile in batch: pick N entries, run Claude on each, collect all proposals into a single issue/PR per entry

**Outputs:**
- One GitHub issue (or working-directory file) per reconciled entry containing the proposal a downstream Claude Code session can act on
- (After downstream session) Updated canonical entry with a new lineage record if substantive changes were made

**Open questions:**
- Confirm the default output channel: GitHub issue with label, working-directory file, or both?
- Confirm the label name (`reconciliation-pending` proposed)
- Issue body format: structured markdown with frontmatter so the downstream session can parse fields, or freeform with sections?
- Where does the downstream session post its decisions: issue comments, a PR against the canonical repo, or both?
- Should the app open a single rollup issue per reconciliation batch or one issue per entry?

-----

## Use-Case Coverage Matrix

| Use case | Touches libraries | Touches manifests | Triggers Claude work | Output channel |
|----------|-------------------|-------------------|----------------------|----------------|
| UC1 — Auth | — | — | — | Credential store |
| UC2 — Track repos | — | — | — | Catalog |
| UC3 — Configure composition | — | Per-repo manifest | — | Per-repo manifest |
| UC4 — Sync canonical → repo | Read | Read | Optional (drift summary, reconciliation) | Target repo files |
| UC5 — Sync repo → canonical | Write (tag or create) | Optional update | Yes (similarity check) | Canonical libraries |
| UC6 — Reconcile | Read all versions | — | Yes (inventory + recommendations) | GitHub issue or working-dir file |
