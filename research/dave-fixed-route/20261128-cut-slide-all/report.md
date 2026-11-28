# Dave fixed-placement routing experiment

Zero annealing; fixed components; at most one existing cut moved on its row, preserving cut kind/count and component pin partitions. All-variant mode checks each eligible relocation with a per-variant state cap; ONE_CUT_GRAPH_INFEASIBLE means every eligible variant was exhausted in this model. SEARCH_CAP and NO_REPAIR remain inconclusive.

| Seed | Result | Before Q3 | After Q3 | Method |
|---:|---|---:|---:|---|
| 26 | SEARCH_CAP | 68.61 | — | — |
| 94 | ONE_CUT_GRAPH_INFEASIBLE | 64.8 | — | — |

Strict rescues: 0/2

Full independent copper graph and saved-board audit results in report.json.
