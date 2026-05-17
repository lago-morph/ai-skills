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
