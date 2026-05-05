# agent-dispatch-loop

An AI skill for iterative, multi-agent software development. Runs a structured
7-step build loop, dispatching each step to a focused subagent while the
dispatcher owns loop control, state, and the exit decision.

```
implement → review impl → write tests → review tests → run tests → analyze → continue/exit
```

## When to use

Use this skill when iterative quality improvement matters more than speed:

- "Build X iteratively"
- "Loop until all tests pass"
- "Run the implement-test-review cycle on this"
- "Iterate on this until tests pass"
- "Run a full SDLC pass"

**Not** for one-shot tasks (use `parallel-subagent-fanout`), pure research, or
workflows where a human is already providing tight feedback.

## Inputs

| Parameter | Default | Description |
|-----------|---------|-------------|
| `GOAL` | required | What to build or fix |
| `SPEC_PATH` | none | Path to a `SPEC.md` for the implementation subagent |
| `MIN_LOOPS` | `3` | Minimum full iterations (enforces refinement even when tests pass early) |
| `MAX_LOOPS` | `10` | Hard cap — exits regardless of stop condition |
| `STOP_CONDITION` | `all_tests_pass` | `all_tests_pass`, `coverage>N` (e.g. `coverage>80`), or `manual` |
| `TEST_COMMAND` | auto-detect | e.g. `pytest -v`, `npm test`, `go test ./...` |
| `COVERAGE_COMMAND` | auto-detect | e.g. `pytest --cov`, `jest --coverage` |
| `FEATURE_BRANCH` | `loop/<run_id>` | Branch for all work |

## The 7 steps

Each iteration runs all seven steps in order. The dispatcher never writes
implementation or test code itself — it only orchestrates subagents.

| Step | Who does it | What happens |
|------|-------------|--------------|
| 1 — implement / fix | subagent | Writes initial impl (iter 1) or applies bug fixes (iter N>1). Opens a PR. |
| 2 — review impl | subagent | Reviews the impl PR vs spec. APPROVE → merge. REQUEST CHANGES → fix loop (same iter). |
| 3 — write / expand tests | subagent | Writes initial tests (iter 1) or expands coverage (iter N>1). Opens a PR. |
| 4 — review tests | subagent | Reviews test PR for false-passes and gaps. APPROVE → merge. REQUEST CHANGES → fix loop. |
| 5 — run tests | subagent | Runs full suite with coverage. Captures logs to `/tmp/iter-N-*.log`. |
| 6 — analyze failures | subagent | Classifies each failure as impl bug, test bug, flake, or setup issue. |
| 7 — decide | dispatcher | Evaluates stop condition + loop counts. Exits or continues. |

## State

All loop state is written to `loops/<run_id>/state.json` after every step.
This enables recovery from a dispatcher restart: read the file, check the
TodoWrite list for the last in-progress step, and resume.

See [`state-schema.json`](./state-schema.json) for the full schema.

## Outputs

- **One impl PR and one test PR per iteration**, merged to main.
- **`loops/<run_id>/state.json`** — machine-readable iteration history.
- **`loops/<run_id>/iteration-report.md`** — human-readable summary committed
  at exit, including a table of all iterations, per-iteration narrative,
  coverage details, spec coverage matrix, and process notes.

Example iteration report table:

| Iter | Impl PR | Test PR | Passed | Failed | Coverage | All pass? |
|------|---------|---------|--------|--------|----------|-----------|
| 1    | #5      | #6      | 67     | 3      | 71%      | ❌        |
| 2    | #7      | #8      | 110    | 0      | 87%      | ✅        |
| 3    | #9      | #10     | 131    | 0      | 92%      | ✅        |

## Anti-patterns

- **Implementing code as the dispatcher** — always dispatch to a subagent.
- **Skipping the review steps** — they catch design drift that tests can't.
- **Treating "tests pass on iteration 1" as done** — `MIN_LOOPS` prevents this.
- **Letting subagents decide when to exit** — step 7 is always dispatcher-owned.
- **Uncapped subagent reports** — enforce `WORD_BUDGET` (default 600) in every brief.

## Integration with other skills

| Skill | Used where |
|-------|-----------|
| `subagent-prompting` | Brief templates for steps 1–6 |
| `parallel-subagent-fanout` | Steps 1 and 3 when work decomposes into parallel pieces |
| `self-retrospective` | Exit report format |
| `live-debug-from-mcp-only` | Steps 5/6 when the test runner is itself a workflow |
| `forensic-vs-aggressive-cleanup` | Branch cleanup after the loop exits |

## Files in this skill

```
skills/agent-dispatch-loop/
├── README.md            ← this file
├── skill.md             ← dispatcher instructions (the executable skill)
├── state-schema.json    ← JSON Schema for loops/<run_id>/state.json
└── spec/
    ├── README.md        ← original overview from the spec repo
    └── SPEC.md          ← full implementation spec
```
