# Dave fixed-placement routing experiment

Zero annealing; fixed components and cuts. Repair search bounded. GRAPH_INFEASIBLE means the fixed-cut legal-edge model exhausted all relay-conflict assignments, not universal physical impossibility. SEARCH_CAP or NO_REPAIR is inconclusive.

| Seed | Result | Before Q3 | After Q3 | Method |
|---:|---|---:|---:|---|
| 26 | GRAPH_INFEASIBLE | 68.61 | — | — |
| 94 | GRAPH_INFEASIBLE | 64.8 | — | — |
| 20 | SEARCH_CAP | 59.49 | — | — |
| 21 | SEARCH_CAP | 58.75 | — | — |
| 40 | SEARCH_CAP | 51.39 | — | — |

Strict rescues: 0/5

Full independent copper graph and saved-board audit results in report.json.
