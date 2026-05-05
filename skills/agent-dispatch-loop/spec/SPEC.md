# `agent-dispatch-loop` — implementation spec

A skill that runs an iterated 7-step build loop, decomposing each
iteration into focused subagent dispatches.

## 1. Trigger conditions

Activate when the user requests iterative SDLC work:

- "Build X iteratively"
- "Loop until done"
- "Run the implement-test-review cycle on this"
- "Iterate on this until tests pass"
- "Run a full SDLC pass" / "Do the loop on this"

Negative triggers:
- One-shot tasks (use `parallel-subagent-fanout` if decomposable, or
  just dispatch one subagent).
- Pure research / exploration.
- Tight feedback loops where a human is in the loop already.

## 2. Inputs

- **Goal** (string)
- **Spec file path** (optional) — if there's a SPEC.md to follow
- **Min loops** (default: 3) — must run at least this many iterations
- **Max loops** (default: 10) — hard cap regardless of state
- **Stop condition** (default: `all_tests_pass`) — also: `coverage>X`,
  `manual` (user confirms each iteration)
- **Test command** (default: auto-detect — `pytest`, `npm test`, etc.)
- **Coverage target** (optional)

## 3. The 7 steps (per iteration)

### Step 1 — implement / fix

If iteration 1 (or "first time"):
- Subagent reads the spec, builds the initial implementation.
- Output: code committed to a feature branch + PR.

If iteration N>1:
- Subagent reads the prior iteration's failure analysis (from step 6)
  and fixes the bugs.
- Output: code committed + PR.

The brief follows the `subagent-prompting` skill's template, including
the explicit "don't refactor unrelated code" / "don't add new
features" / "report PR# and test count" deliverables.

### Step 2 — review the impl PR

Independent subagent reviews the impl PR against the spec. Verdict:
APPROVE / REQUEST CHANGES. Blocking issues are listed with file:line
refs. Non-blocking are recorded for next iteration.

If REQUEST CHANGES:
- Dispatcher posts the comments on the PR.
- Returns to step 1 with the comments as context.
- Counts as the same iteration (not a re-loop).

If APPROVE:
- Dispatcher merges the PR.
- Continues to step 3.

### Step 3 — write or expand tests

Subagent writes (iteration 1) or expands (iteration N>1) the test
suite. Each iteration should:

- Pin assertions that were too permissive last iteration
- Add tests for new behaviors
- Increase coverage of weak modules
- Add edge cases

The brief includes the test count delta target and any specific gaps
to fill, taken from the prior iteration's review notes.

### Step 4 — review the test PR

Independent subagent reviews the tests. Looks for:
- False-pass candidates (tests that would pass on a broken impl)
- Test correctness issues (mocks too permissive, assertions
  irrelevant)
- Coverage gaps still important

REQUEST CHANGES → comment + return to step 3 (same iteration).
APPROVE → merge + continue.

### Step 5 — run all tests

Subagent runs the full suite with verbose output, durations, JUnit
XML, and coverage. Captures logs to `/tmp/iter-N-pytest.log` and
similar.

Reports back: total / passed / failed / errored / skipped, slowest 10
tests, coverage by module, any warnings.

### Step 6 — analyze failures

If step 5 reported any failures:
- Subagent investigates each failure.
- For each: real impl bug or test bug?
- If test bug: returns to step 3 (test fix), with note in the next
  iteration's brief.
- If impl bug: feeds into step 1 of next iteration.

If 0 failures:
- Brief "all green, nothing to analyze" and continue to step 7.

### Step 7 — continue / exit decision

Decision tree:

```
if loops_done >= max_loops:
    EXIT (record max-loops reached)
elif loops_done >= min_loops and stop_condition_met():
    EXIT (success)
else:
    LOOP back to step 1
```

stop_condition checks vary:
- `all_tests_pass`: 0 failures in step 5
- `coverage>X`: coverage% from step 5 ≥ X
- `manual`: ask user

On EXIT:
- Write the iteration report (see `self-retrospective` skill's
  output format).
- Commit the report.
- Return summary to dispatcher.

## 4. State tracking

The dispatcher uses TodoWrite to track loop position:

```
[iter-1] step-1: implement (in_progress)
[iter-1] step-2: review impl (pending)
...
```

This makes recovery from a dispatcher restart trivial — read the todo
list, resume from the in-progress step.

State persisted to `loops/<run_id>/state.json`:

```json
{
  "run_id": "...",
  "min_loops": 3,
  "max_loops": 10,
  "stop_condition": "all_tests_pass",
  "current_loop": 2,
  "iterations": [
    {"loop": 1, "impl_pr": 5, "test_pr": 6, "tests_passed": 67, "tests_failed": 0, "coverage": 0.87},
    {"loop": 2, "impl_pr": 7, "test_pr": 8, "tests_passed": 110, "tests_failed": 0, "coverage": 0.92}
  ]
}
```

## 5. Default templates

### Step 1 brief (initial)

```
You are implementing the spec at <SPEC_PATH>.

## Goal
<GOAL>

## Repo
- Path: <REPO_ROOT>
- Branch: <FEATURE_BRANCH> (work directly here)

## Build
<priority list extracted from spec>

## Don't
- Don't write tests yet (separate subagent will).
- Don't refactor unrelated code.
- Don't add features beyond the spec.

## Deliverables
- Real code, not skeletons.
- Commit + push to <FEATURE_BRANCH>.
- Open PR via mcp__github__create_pull_request.
- Report PR number, files created, any caveats.
```

### Step 1 brief (fix iteration)

```
You are fixing bugs found in iteration <N-1>.

## Bugs to fix
<list from step 6 of prior iteration>

## Repo + branch
<as above>

## Constraint
Each fix should be the smallest correct change. Don't refactor.

## Deliverables
<as above>
```

### Step 2 / step 4 brief (review)

```
You are reviewing PR #<N>.

## Spec
<SPEC_PATH or summary>

## Review focus
- Correctness vs spec
- Per-section coverage
- Bugs (file:line refs required)
- Test quality (for step 4)

## Output
- Verdict: APPROVE / REQUEST CHANGES
- Blocking issues (numbered, file:line refs)
- Non-blocking issues
- Recommendation

Under <WORD_BUDGET> words. Don't post to GitHub.
Don't modify files. Don't merge.
```

### Step 5 brief (run)

```
Run the full test suite for <REPO>.

1. cd <REPO_ROOT>
2. <test_command_with_verbose_durations_junit>
3. Coverage pass: <coverage_command>

## Output
- Pass/fail summary
- Failed tests (test id + 1-line summary)
- Slowest 10 tests
- Coverage by module
- Warnings
- Files referenced (exact log paths)
- Verdict: ALL_PASS / SOME_FAILED / SETUP_BROKEN

Don't modify any test or impl file.
```

### Step 6 brief (analyze)

```
You are analyzing test failures from iteration <N>.

## Logs
- /tmp/iter-<N>-pytest.log
- /tmp/iter-<N>-coverage.log

## Per failure
- Test id
- Likely cause: real impl bug / test bug / flake / setup issue
- Recommendation: fix in step 1 (impl) / step 3 (test) / monitor / xfail

## Output
- Per-failure verdict
- Aggregate recommendation: continue with which fixes
- Don't fix anything yourself

Under <WORD_BUDGET> words.
```

## 6. Anti-patterns

- **Doing the impl yourself.** Wastes dispatcher context. Always
  dispatch to a subagent.
- **Skipping reviews.** They catch design drift tests can't.
- **Letting subagents decide "done."** Always specify exact
  deliverables.
- **Treating "tests pass" as "ready to ship."** The min-loops floor
  forces refinement even when tests already pass at iteration 1.
- **Force-pushing a feature branch back to main mid-iteration.** Auto-
  closes any open PR from that branch. Always merge first, then sync.
- **Letting subagent reports balloon.** Cap word counts in briefs;
  long reports erode dispatcher context.

## 7. The exit step (writes the report)

On clean exit, dispatcher invokes the `self-retrospective` skill (or
its in-loop equivalent) to produce a structured iteration report:

```markdown
# POC iteration report

Multi-agent loop run on <DATE>.

| Iter | Impl PR | Test PR | Tests | Coverage | All pass? |
|------|---------|---------|-------|----------|-----------|
| 1    | #1      | #2      | 67    | 87%      | ✅        |
| 2    | #3      | #4      | 110   | 92%      | ✅        |
| 3    | #5      | #6      | 177   | 95%      | ✅        |

## Loop structure
[explanation of the 7-step pattern]

## Per-iteration narrative
[brief for each iteration covering goal, what shipped, review notes,
test deltas, any deviations]

## Decision: exit
[which stop condition fired]

## Coverage details (final)
[module-by-module]

## Spec coverage matrix
[checklist of spec sections vs implementation status]

## Notable deviations / deferrals
[anything not fully implemented + why]

## Process notes
[subagents dispatched, time elapsed, any operational mishaps]

## Final repository state
[main HEAD, test count, coverage]
```

## 8. Integration with other skills

- Step 1 brief uses `subagent-prompting` template patterns.
- Steps 1, 3 use `parallel-subagent-fanout` if the iteration's work
  decomposes into N pieces.
- Step 5/6 may use `live-debug-from-mcp-only` if the test runner is
  itself a workflow.
- The exit step is a `self-retrospective` invocation.
- The cleanup of feature branches follows
  `forensic-vs-aggressive-cleanup`.

## 9. Test plan (when built)

- Unit: state machine transitions for all stop-condition combinations.
- Unit: report generation from a populated state object.
- Integration: dry-run mode that prints all dispatches without
  spawning real subagents.
- Live: a 3-loop run on a small toy spec (e.g., "implement a small
  CLI utility iteratively"). Verify all 3 PRs land, report is
  written, branches are cleaned up.

## 10. Future variants

- **Adaptive min/max** based on test churn (if every iteration is
  finding new bugs, raise the cap).
- **Failure-injection mode** for testing the loop itself.
- **Multi-track loops** (impl track + docs track in parallel).

Non-goals for v1.
