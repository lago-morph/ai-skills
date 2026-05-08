# parallel-subagent-fanout

Decompose a goal into independent subtasks, run them concurrently, merge results into one PR.

```mermaid
flowchart TD
    S0[Collect inputs] --> S1
    S1[Decompose GOAL into N subtasks\nYAML plan] --> AP{User approves?}
    AP -- revise --> S1
    AP -- approved --> S2

    S2[Create branches\nfeat/run--sub-01\nfeat/run--sub-02\n...] --> S3

    S3[Dispatch ALL subagents\nin one message] --> W{N > MAX_PARALLEL?}
    W -- yes --> WV[Wave 1 → wait → Wave 2 → ...]
    W -- no --> PAR

    subgraph PAR["Parallel subagents (each on its own sub-branch)"]
        A1[sub-01\nbuild + push + open PR]
        A2[sub-02\nbuild + push + open PR]
        AN[sub-N\nbuild + push + open PR]
    end

    WV --> PAR
    PAR --> S4

    S4[Collect results\nupdate state.json] --> F{Any failures?}
    F -- yes --> FU[Ask user:\nskip / re-dispatch / abort]
    FU --> S4
    F -- no --> S5

    S5[Merge sub-branches into feature branch\nin PLAN ORDER] --> MC{Conflict?}
    MC -- fail/manual --> UU[Surface to user\nwait for resolution]
    UU --> S5
    MC -- ours/theirs --> S5
    MC -- none --> S6

    S6[Write report.md\nCommit\nOpen PR feat → main]
```

```mermaid
flowchart LR
    subgraph Dispatcher
        plan[Plan & approve]
        branches[Create branches]
        state[state.json]
        merge[Merge in plan order]
        report[report.md + PR]
    end
    subgraph Subagents["Subagents (parallel)"]
        s1[sub-01]
        s2[sub-02]
        sn[sub-N]
    end
    Dispatcher -- briefs --> Subagents
    Subagents -- PR + report --> Dispatcher
```

## Branch naming

```
main
└── feat/<run_id>          ← feature branch (dispatcher merges here)
    ├── feat/<run_id>--sub-01   ← subagent 1 (double-dash, not slash)
    ├── feat/<run_id>--sub-02
    └── feat/<run_id>--sub-N
```

## Conflict strategies

| `CONFLICT_STRATEGY` | Action |
|---------------------|--------|
| `fail` (default) | Stop, surface to user |
| `ours` | Prefer feature branch side |
| `theirs` | Prefer sub-branch side |
| `manual` | Leave markers, wait for user |
