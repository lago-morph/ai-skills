# `agent-dispatch-loop` skill

An iterative SDLC skill that runs a 7-step build loop, decomposing each
iteration into focused subagent dispatches:

**implement → review → test-write → test-review → run → analyze → continue/exit**

## Why

Without a structured loop, each iteration drifts: sometimes the review
gets skipped, sometimes the test-runner doesn't get full logs, sometimes
the dispatcher loses track of which iteration it's on.

This skill enforces the full cycle every time, producing multiple pull
requests (one impl + one test PR per iteration), a final iteration report,
and consolidated subagent documentation.

## Usage

```
Run the agent-dispatch-loop skill.
Goal: implement a small CLI utility
Spec: specs/cli-tool.md
Min loops: 3
Stop condition: all_tests_pass
Max loops: 10
```

## Outputs

- One impl PR and one test PR per iteration.
- `loops/<run_id>/state.json` tracking all iterations.
- Final iteration report committed to the repo.

## Status

Spec only — see `SPEC.md`.

## See also

- `parallel-subagent-fanout` — one-shot decomposition (no iteration).
- `subagent-prompting` — brief templates used in steps 1–6.
- `self-retrospective` — report format used at exit.
