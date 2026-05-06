---
name: agent-dispatch-loop
description: Run an iterated 7-step build loop over a codebase, dispatching each step to a focused subagent. The dispatcher owns the loop, state, and exit decision; subagents own the work. Use when the user says "build X iteratively", "loop until done", "run the implement-test-review cycle on this", "iterate on this until tests pass", or "run a full SDLC pass".
---

# Skill: agent-dispatch-loop

Run an iterated 7-step build loop over a codebase, dispatching each step
to a focused subagent. The dispatcher (you) owns the loop, state, and
exit decision — subagents own the work.

---

## Trigger phrases

Use this skill when the user says any of:

- "Build X iteratively"
- "Loop until done"
- "Run the implement-test-review cycle on this"
- "Iterate on this until tests pass"
- "Run a full SDLC pass" / "Do the loop on this"

Do **not** use for one-shot tasks, pure research, or tight human-in-the-loop
flows.

---

## Step 0 — collect inputs

Before starting the loop, resolve these values. Ask the user for any that
are missing and have no sensible default.

| Input | Default | Notes |
|-------|---------|-------|
| `GOAL` | (required) | What to build or fix |
| `SPEC_PATH` | none | Path to a SPEC.md the impl subagent should follow |
| `REPO_ROOT` | current working directory | Absolute path |
| `FEATURE_BRANCH` | `loop/<run_id>` | Branch for impl work |
| `MIN_LOOPS` | `3` | Must run at least this many full iterations |
| `MAX_LOOPS` | `10` | Hard cap |
| `STOP_CONDITION` | `all_tests_pass` | Also: `coverage>N` (e.g. `coverage>80`), `manual` |
| `TEST_COMMAND` | auto-detect | Prefer `pytest -v` / `npm test` / `go test ./...` |
| `COVERAGE_COMMAND` | auto-detect | e.g. `pytest --cov` / `jest --coverage` |
| `WORD_BUDGET` | `600` | Max words for review and analysis subagent reports |

Generate `run_id` as `YYYYMMDD-HHMMSS` from the current timestamp.

---

## Step 0b — initialise state

Create `loops/<run_id>/state.json` with:

```json
{
  "run_id": "<run_id>",
  "goal": "<GOAL>",
  "spec_path": "<SPEC_PATH or null>",
  "min_loops": <MIN_LOOPS>,
  "max_loops": <MAX_LOOPS>,
  "stop_condition": "<STOP_CONDITION>",
  "test_command": "<TEST_COMMAND>",
  "coverage_command": "<COVERAGE_COMMAND>",
  "feature_branch": "<FEATURE_BRANCH>",
  "current_loop": 0,
  "exit_reason": null,
  "iterations": []
}
```

Use TodoWrite to seed the first iteration's steps:

```
[iter-1] step-1: implement    (pending)
[iter-1] step-2: review impl  (pending)
[iter-1] step-3: write tests  (pending)
[iter-1] step-4: review tests (pending)
[iter-1] step-5: run tests    (pending)
[iter-1] step-6: analyze      (pending)
[iter-1] step-7: decide       (pending)
```

---

## The loop

Repeat steps 1–7. On each iteration N, mark each todo `in_progress` before
starting the step and `completed` immediately after.

---

### Step 1 — implement / fix

Mark `[iter-N] step-1` in_progress.

**If N == 1 (initial implementation):**

Dispatch a subagent with this brief (fill in `<...>` placeholders):

```
You are implementing the spec at <SPEC_PATH> (or the goal below if no spec).

## Goal
<GOAL>

## Repo
- Root: <REPO_ROOT>
- Branch: <FEATURE_BRANCH>  ← commit and push here

## Build priorities
<If SPEC_PATH exists: list the major sections from the spec.
 Otherwise: derive 3–5 bullet points from GOAL.>

## Constraints
- Don't write tests (a separate subagent will).
- Don't refactor unrelated code.
- Don't add features beyond the spec / goal.
- Real code only — no skeletons, no TODOs.

## Deliverables
1. Code committed and pushed to <FEATURE_BRANCH>.
2. PR opened via mcp__github__create_pull_request targeting main.
3. Report back: PR number, files created/modified, line counts, caveats.
```

Wait for the subagent to return. Extract: `impl_pr` number and any caveats.

**If N > 1 (fix iteration):**

Read `loops/<run_id>/state.json` → `iterations[N-2].failure_analysis` for
the bug list from the prior iteration's step 6.

Dispatch a subagent with:

```
You are fixing bugs found in iteration <N-1>.

## Bugs to fix
<failure_analysis from prior iteration — impl bugs only>

## Repo
- Root: <REPO_ROOT>
- Branch: <FEATURE_BRANCH>

## Constraint
Each fix must be the smallest correct change. Don't refactor. Don't add
features.

## Deliverables
1. Fixes committed and pushed to <FEATURE_BRANCH>.
2. PR opened via mcp__github__create_pull_request targeting main.
3. Report back: PR number, files changed, one-line summary per fix.
```

Update `loops/<run_id>/state.json`: set `current_loop = N`, append a new
object `{"loop": N, "impl_pr": <pr_number>}` to `iterations`.

Mark `[iter-N] step-1` completed.

---

### Step 2 — review the impl PR

Mark `[iter-N] step-2` in_progress.

Dispatch a subagent with:

```
You are reviewing PR #<impl_pr>.

## Context
<If SPEC_PATH: "Spec is at <SPEC_PATH>."
 Else: "Goal: <GOAL>">

## Review focus
- Correctness vs spec / goal
- Coverage of every required section
- Bugs (must include file:line refs)
- Missing error handling or edge cases

## Output format
Verdict: APPROVE or REQUEST CHANGES
Blocking issues: (numbered list, each with file:line ref)
Non-blocking issues: (numbered list)
Recommendation: one sentence

Under <WORD_BUDGET> words.
Do NOT post to GitHub, modify files, or merge.
```

Parse the verdict.

**If REQUEST CHANGES:**
- Post blocking issues as a comment on `impl_pr` via
  `mcp__github__add_issue_comment`.
- Dispatch a follow-up fix subagent (same brief as step 1 fix, but with
  the review comments as the bug list).
- Re-request the review (loop back to step 2 with the new PR).
- This counts as the same iteration N — do not increment the loop counter.

**If APPROVE:**
- Merge `impl_pr` via `mcp__github__merge_pull_request`.
- Record `"impl_review": "APPROVE"` in `iterations[N-1]`.

Mark `[iter-N] step-2` completed.

---

### Step 3 — write or expand tests

Mark `[iter-N] step-3` in_progress.

**If N == 1:**

Dispatch a subagent with:

```
You are writing the initial test suite for <REPO_ROOT>.

## Goal
<GOAL>

## Spec (if exists)
<SPEC_PATH>

## Requirements
- Achieve meaningful coverage of every module / function.
- Include happy paths, error paths, and at least 3 edge cases.
- Do NOT modify implementation files.

## Test command
<TEST_COMMAND>

## Deliverables
1. Tests committed and pushed to <FEATURE_BRANCH>.
2. PR opened via mcp__github__create_pull_request targeting main.
3. Report back: PR number, test file(s) created, total test count.
```

**If N > 1:**

Read `iterations[N-2]` for: prior `tests_passed`, `coverage`, and any
test-specific notes from step 6's `failure_analysis`.

Dispatch a subagent with:

```
You are expanding the test suite for iteration <N>.

## Prior state
- Tests passing last iteration: <tests_passed>
- Coverage last iteration: <coverage>%
- Notes from failure analysis: <test_bug_notes from prior step 6>

## What to add this iteration
- Pin assertions that were too permissive.
- Add tests for any new behaviors shipped in iteration <N>.
- Increase coverage of the weakest modules (from prior coverage report).
- Add edge cases for: <specific gaps noted in prior step 4 review>.
- Target at least <tests_passed + 10> total passing tests.

## Constraints
- Don't modify implementation files.

## Deliverables
1. Tests committed and pushed to <FEATURE_BRANCH>.
2. PR opened.
3. Report back: PR number, tests added (delta), new total.
```

Extract `test_pr` number. Mark `[iter-N] step-3` completed.

---

### Step 4 — review the test PR

Mark `[iter-N] step-4` in_progress.

Dispatch a subagent with:

```
You are reviewing test PR #<test_pr>.

## Context
<GOAL or SPEC_PATH summary>

## Review focus
- False-pass candidates: tests that would pass even on a broken implementation
- Mocks too permissive (masking real behavior)
- Assertions that don't actually verify the spec
- Important coverage gaps remaining

## Output format
Verdict: APPROVE or REQUEST CHANGES
Blocking issues: (numbered, file:line)
Non-blocking issues: (numbered)

Under <WORD_BUDGET> words.
Do NOT post to GitHub, modify files, or merge.
```

**If REQUEST CHANGES:** same flow as step 2 — post comments, request fix
subagent, re-review. Counts as same iteration.

**If APPROVE:** merge `test_pr`. Record `"test_review": "APPROVE"` in
`iterations[N-1]`.

Mark `[iter-N] step-4` completed.

---

### Step 5 — run all tests

Mark `[iter-N] step-5` in_progress.

Dispatch a subagent with:

```
Run the full test suite for the repo at <REPO_ROOT>.

## Commands
1. <TEST_COMMAND> --verbose (capture stdout+stderr to /tmp/iter-<N>-pytest.log)
2. <COVERAGE_COMMAND> (capture to /tmp/iter-<N>-coverage.log)

## Output
- Summary: total / passed / failed / errored / skipped
- Each failed test: test id + one-line cause
- Slowest 10 tests (id + duration)
- Coverage by module (name + %)
- Any warnings
- Exact log file paths
- Verdict: ALL_PASS | SOME_FAILED | SETUP_BROKEN

Do NOT modify any test or implementation file.
```

Extract and record in `iterations[N-1]`:
- `tests_passed`, `tests_failed`, `tests_errored`, `tests_skipped`
- `coverage` (overall %)
- `verdict` (ALL_PASS / SOME_FAILED / SETUP_BROKEN)
- `log_path` (`/tmp/iter-<N>-pytest.log`)

Mark `[iter-N] step-5` completed.

---

### Step 6 — analyze failures

Mark `[iter-N] step-6` in_progress.

**If `verdict == ALL_PASS`:** record `"failure_analysis": null` and mark
step 6 completed immediately — no subagent needed.

**Otherwise**, dispatch a subagent with:

```
You are analyzing test failures from iteration <N>.

## Logs
- /tmp/iter-<N>-pytest.log
- /tmp/iter-<N>-coverage.log

## Per failure, provide
- Test id
- Likely cause: impl_bug | test_bug | flake | setup_issue
- Recommendation: fix_in_impl | fix_in_tests | monitor | xfail

## Aggregate output
- impl_bugs: list of bugs to fix in step 1 next iteration (file:line + description)
- test_bugs: list of test fixes for step 3 next iteration
- overall_recommendation: one sentence

Under <WORD_BUDGET> words.
Do NOT fix anything yourself.
```

Record `failure_analysis` (the full subagent output) in `iterations[N-1]`.
Save `loops/<run_id>/state.json`.

Mark `[iter-N] step-6` completed.

---

### Step 7 — continue / exit decision

Mark `[iter-N] step-7` in_progress.

Evaluate:

```
loops_done = N

if loops_done >= MAX_LOOPS:
    EXIT — reason: "max_loops reached"

elif loops_done >= MIN_LOOPS and stop_condition_met():
    EXIT — reason: "stop_condition: <STOP_CONDITION>"

else:
    CONTINUE — seed todos for iter-(N+1) and loop back to step 1
```

**stop_condition_met() logic:**

| Condition | Passes when |
|-----------|-------------|
| `all_tests_pass` | `iterations[N-1].tests_failed == 0 and verdict == ALL_PASS` |
| `coverage>X` | `iterations[N-1].coverage >= X` |
| `manual` | Ask the user "Iteration N complete. Continue? (y/n)" and wait |

**On CONTINUE:**

Add TodoWrite entries for iter-(N+1):

```
[iter-(N+1)] step-1: implement    (pending)
[iter-(N+1)] step-2: review impl  (pending)
[iter-(N+1)] step-3: write tests  (pending)
[iter-(N+1)] step-4: review tests (pending)
[iter-(N+1)] step-5: run tests    (pending)
[iter-(N+1)] step-6: analyze      (pending)
[iter-(N+1)] step-7: decide       (pending)
```

Mark `[iter-N] step-7` completed and loop back to step 1.

**On EXIT:** proceed to the exit step below.

---

## Exit step — write the iteration report

When the loop exits, write the following report to
`loops/<run_id>/iteration-report.md`:

```markdown
# Iteration report — <run_id>

Multi-agent loop run on <DATE>.

## Summary table

| Iter | Impl PR | Test PR | Passed | Failed | Coverage | All pass? |
|------|---------|---------|--------|--------|----------|-----------|
<one row per iteration from state.json>

## Exit decision
<exit_reason> after <N> iterations.
Stop condition: <STOP_CONDITION>.

## Loop structure
Each iteration ran 7 steps: implement → review impl → write tests →
review tests → run tests → analyze failures → continue/exit decision.
Each step was executed by an independent subagent; the dispatcher owned
state, loop control, and PR merges.

## Per-iteration narrative
<For each iteration: one paragraph covering goal, what shipped,
review verdict, test delta, notable failures, and any deviations.>

## Coverage details (final iteration)
<Module-by-module coverage from final step 5 log.>

## Spec coverage matrix
<If SPEC_PATH exists: checklist of spec sections vs implementation status.>

## Notable deviations / deferrals
<Anything not fully implemented and why.>

## Process notes
Total subagents dispatched: <count>
Any operational issues encountered: <list or "none">

## Final repository state
Branch: main (post all merges)
Total tests: <final tests_passed + tests_failed>
Coverage: <final coverage>%
```

Commit the report:

```
git add loops/<run_id>/
git commit -m "loop <run_id>: iteration report (<N> iterations, <exit_reason>)"
git push -u origin <FEATURE_BRANCH>
```

Tell the user the loop is complete, print the summary table, and state the
exit reason.

---

## Recovery from restart

If the dispatcher is interrupted mid-loop:

1. Read `loops/<run_id>/state.json` to find `current_loop`.
2. Check TodoWrite for the last `in_progress` step.
3. Resume from that step. Re-dispatch the subagent if the result was lost.
4. Never re-run a step whose result is already recorded in `state.json`.

---

## Anti-patterns (never do these)

- **Implement the code yourself.** Always dispatch. Doing it yourself
  consumes dispatcher context and bypasses the review gate.
- **Skip a review step** because the prior step "looked fine."
- **Let a subagent decide whether to exit.** The exit decision lives in
  step 7, owned by the dispatcher.
- **Treat "tests pass on iteration 1" as done.** MIN_LOOPS exists to
  force refinement even when the first iteration succeeds.
- **Force-push the feature branch to main mid-iteration.** This silently
  closes open PRs. Always merge via PR first.
- **Accept unbounded subagent reports.** Enforce WORD_BUDGET in every
  review and analysis brief.
