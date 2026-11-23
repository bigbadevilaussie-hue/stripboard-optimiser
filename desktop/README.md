# Stripboard Optimiser — Tkinter Desktop GUI

The Tkinter desktop application is the active optimisation interface. It wraps the existing v5 solver through the repository's Node.js harness; it does not reimplement the solver in Python.

## Launch

From the repository root:

```bash
cd desktop && PYTHONPATH=src python3 -m stripboard_optimizer.main
```

The GUI is version **v1.60-debug** (November 2026). For current profiling and locked-F1 experiments, see [Native solver benchmark — 23 Nov 2026](../docs/native-solver-benchmark-2026-11-23.md).

## Runtime requirements

- Python 3 with Tkinter.
- Node.js available as `node` on PATH.
- The frontend v5 solver harness: `src/frontend/tests/solver/v5Solve.js`.
- Built solver output: `src/frontend/tests/solver/out/components/stripboard/autoLayout5.js`.
- WASM modules: `src/frontend/components/stripboard/v5wasm/v5decode.wasm` and `v5route.wasm`.
- Board preview additionally uses the bundled standalone renderer and `rsvg-convert`.

The solver adapter checks for the required harness and compiled solver/WASM assets before starting a run. Optional native mode requires its separately built native libraries.

## Current 2PASS tournament (v1.58-debug)

The current tournament is implemented in `src/stripboard_optimizer/solver/worker.py`; its present **debug settings** are:

- **Pass 1:** 200 independent seeds, 15,000 moves each, with strict Q0 and zero-off-axis qualification. Finalists are not arbitrarily capped at 10 in this debug build.
- **Pass 2:** all selected qualifiers are re-run at 25,000–100,000 moves, stepping by 5,000. The solver starts each run from the source project rather than continuing from an earlier budget. Retain the best 10 overall results.
- **Physical controls:** drilled cuts only and no stacking are independent opt-in constraints. With the corresponding controls off, knife cuts and stacked wires may appear. Do not assume zero diagonals or an overall Q0 score independently proves geometry, connectivity, locked component location or buildability.
- **Speed profiling:** launch with `STRIPBOARD_TIMING=1` to write full per-seed JSONL timings in the work directory and show two compact, emoji-labelled timing lines every 25 seeds. After editing `autoLayout5.ts`, rebuild with `cd src/frontend && npx tsc -p tests/solver/tsconfig.json`.
- **Detailed reproducibility record:** [Native solver profiling, MOTO/MOTOMIX comparison and 5k–50k locked-F1 ladder](../docs/native-solver-benchmark-2026-11-23.md). The full 5k–50k ladder is complete: 200 runs, with a best reported clean locked result of 21 wires / 36 cuts at 50k seed #03; knife cuts and stacking were allowed.

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
- [Native CLI audit](../docs/cli-audit-2026-11-23.md) documents strict post-solve validation, finish tracing, proposal histograms and parallel benchmark scripts. These are CLI-only development improvements; the desktop GUI still uses its own qualification path.
