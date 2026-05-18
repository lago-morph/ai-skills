# Ledger: skills

> Auto-generated from `000-ledger.json`. Do not edit by hand.

| Name | Version | State | Description |
|------|---------|-------|-------------|
| `agent-dispatch-loop` | 0.1.0 | live | An orchestration pattern for fanning a task out across many subagents and consolidating their results. Use when the workload can be parallelized across independent agents and the parent agent needs a single combined answer. |
| `codex-skill-creator` | 0.1.0 | live | A skill-creation pipeline tuned to the codex harness (OpenAI agents). Mirrors the upstream Anthropic skill-creator structure but targets the codex YAML/file conventions. |
| `parallel-subagent-fanout` | 0.1.0 | live | Discipline for issuing many parallel subagent calls efficiently without blocking on the slowest. Covers prompt design, result merging, and failure handling. |
| `self-retrospective` | 0.1.0 | live | Harvest the knowledge accumulated in a session before it is lost to context truncation. Produces a structured retrospective on disk with skill specs, ADR drafts, and per-rule agents-md additions in canonical filename form. |
| `subagent-prompting` | 0.1.0 | live | How to write prompts for subagents so they can pick up the task cold. Covers context handoff, scope framing, expected output format, and common failure modes. |

## Detail

### `agent-dispatch-loop`

- **Current version:** `0.1.0`
- **Current hash:** `ca2e88b7dfe641604450d986371cba3a455ffe68814d8a8c723ca1a697d85b9e`
- **State:** `live`

  An orchestration pattern for fanning a task out across many subagents and consolidating their results. Use when the workload can be parallelized across independent agents and the parent agent needs a single combined answer.

  **Version history:**

  - `0.1.0` — hash `ca2e88b7dfe641604450d986371cba3a455ffe68814d8a8c723ca1a697d85b9e` (commit `bootstrap`)

### `codex-skill-creator`

- **Current version:** `0.1.0`
- **Current hash:** `07eecbc32fb4ab4de1aef7aa07417ff425ae9b572426303de57f089818b760a4`
- **State:** `live`

  A skill-creation pipeline tuned to the codex harness (OpenAI agents). Mirrors the upstream Anthropic skill-creator structure but targets the codex YAML/file conventions.

  **Version history:**

  - `0.1.0` — hash `07eecbc32fb4ab4de1aef7aa07417ff425ae9b572426303de57f089818b760a4` (commit `bootstrap`)

### `parallel-subagent-fanout`

- **Current version:** `0.1.0`
- **Current hash:** `978d4a5d04c14ab3fa4565ef40c39da72949ad303da82736b8ce819d8c6bb4b6`
- **State:** `live`

  Discipline for issuing many parallel subagent calls efficiently without blocking on the slowest. Covers prompt design, result merging, and failure handling.

  **Version history:**

  - `0.1.0` — hash `978d4a5d04c14ab3fa4565ef40c39da72949ad303da82736b8ce819d8c6bb4b6` (commit `bootstrap`)

### `self-retrospective`

- **Current version:** `0.1.0`
- **Current hash:** `6bfa009abfb9351686812fdb97dffa5c6126fa712060e75451be8da12c5ad5f6`
- **State:** `live`

  Harvest the knowledge accumulated in a session before it is lost to context truncation. Produces a structured retrospective on disk with skill specs, ADR drafts, and per-rule agents-md additions in canonical filename form.

  **Version history:**

  - `0.1.0` — hash `6bfa009abfb9351686812fdb97dffa5c6126fa712060e75451be8da12c5ad5f6` (commit `bootstrap`)

### `subagent-prompting`

- **Current version:** `0.1.0`
- **Current hash:** `3e876f2ece6208ef8821e79e4fce4d96b344bb93f2dee15c93b9cb6507db80c3`
- **State:** `live`

  How to write prompts for subagents so they can pick up the task cold. Covers context handoff, scope framing, expected output format, and common failure modes.

  **Version history:**

  - `0.1.0` — hash `3e876f2ece6208ef8821e79e4fce4d96b344bb93f2dee15c93b9cb6507db80c3` (commit `bootstrap`)
