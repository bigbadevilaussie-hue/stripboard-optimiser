# Stripboard Optimiser — Tkinter Desktop GUI

The Tkinter desktop application is the active optimisation interface. It wraps the existing v5 solver through the repository's Node.js harness; it does not reimplement the solver in Python.

## Launch

From the repository root:

```bash
cd desktop && PYTHONPATH=src python3 -m stripboard_optimizer.main
```

The GUI is version **v1.36**.

## Runtime requirements

- Python 3 with Tkinter.
- Node.js available as `node` on PATH.
- The frontend v5 solver harness: `src/frontend/tests/solver/v5Solve.js`.
- Built solver output: `src/frontend/tests/solver/out/components/stripboard/autoLayout5.js`.
- WASM modules: `src/frontend/components/stripboard/v5wasm/v5decode.wasm` and `v5route.wasm`.
- Board preview additionally uses the bundled standalone renderer and `rsvg-convert`.

The solver adapter checks for the required harness and compiled solver/WASM assets before starting a run. Optional native mode requires its separately built native libraries.

## Current 2PASS tournament

The current two-pass workflow is implemented in `src/stripboard_optimizer/solver/worker.py`.

### Pass 1 — broad seed search

- 1,000 independent seeds by default (seeds 1–1,000).
- Each seed starts from the original project JSON.
- 25,000 moves per seed at effort 0.1.
- A candidate qualifies only when conflicts, incomplete connections and geometry errors are all zero and no issues are reported.
- Exact duplicate layout signatures are excluded from the finalist pool.
- Up to 10 unique valid finalists are selected.
- Progress is logged every 20 completed seeds.
- Individual PASS results are logged; individual FAIL lines are suppressed in Pass 1. Progress and duplicate notices are still logged.

### Pass 2 — finalist refinement

- Up to 10 Pass 1 finalists are retained.
- Each finalist uses its original Pass 1 seed.
- 40 independent move budgets are run: 5,000 to 200,000 moves in 5,000-move increments.
- Every budget starts from a fresh copy of the original project JSON. It does not continue from the previous budget's saved board.
- The best valid result per finalist seed is retained.
- The final retained finalists are ranked and saved as JSON files in the configured output directory.

### Ranking

Default wire-priority ranking is:

1. Lowest jumper-wire count.
2. Lowest track-cut count.
3. Lowest solver price.

Cut-priority mode ranks cuts first, then wires, then price. A PASS means the candidate passed the configured validity checks; it does not mean it beats the project benchmark.

## Current benchmark

The Moto-Mate reference layout is **W14/C30**: 14 jumper wires and 30 cuts on a 24 × 56 board. This is the project's current benchmark to beat, not a claim of a globally verified world record.

## Solver and output boundaries

- The Python worker launches one isolated Node harness process per seed/budget run.
- Each invocation receives its own temporary job directory and project copy.
- Pass 1 deduplication uses board dimensions plus non-excluded component IDs, positions and rotations. It is a layout fingerprint, not a full electrical-equivalence proof.
- Tournament output currently saves the final retained finalist JSONs. Do not assume every Pass 1 candidate is archived.
- The original input JSON is copied into each solver job; the worker does not intentionally use a prior budget's output as the next budget's starting state.

## Directory structure

```
desktop/
├── pyproject.toml
├── README.md
└── src/stripboard_optimizer/
    ├── main.py
    ├── ui/
    ├── controllers/
    ├── models/
    ├── services/
    ├── solver/
    │   ├── solver_adapter.py
    │   └── worker.py
    └── resources/
        └── standalone-renderer/
```

The actual repository tree is authoritative; this outline is intentionally limited to the active areas rather than promising modules that may not exist.

## Threading

- Solver work runs outside the Tkinter event thread.
- Workers communicate with the GUI through a thread-safe queue.
- Tkinter updates are performed by the GUI polling loop.
- Cancellation signals the worker and terminates registered solver processes.
- Completed work is not a guarantee that every candidate is persistently archived.

## Related documentation

- Root [project.md](../project.md) is the canonical specification and implementation-status record.
- Root [README.md](../README.md) describes the repository and inherited web application.
