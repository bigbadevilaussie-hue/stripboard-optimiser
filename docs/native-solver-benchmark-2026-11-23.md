# Native solver profiling and F1 lock experiments — 23 November 2026

This is the reproducibility record for the **v1.58-debug** Stripboard Optimiser investigation. Results below were pasted from the user's iMac Terminal. They are measurements, **not** proof of a lock-related causal speedup, and are not a claim that the solver's `quality: 0` alone guarantees a buildable board.

## Purpose

1. Determine where per-seed runtime is spent (native anneal vs. finishing).
2. Measure the performance impact of a locked F1 component.
3. Determine whether increasing annealing moves improves the rate and quality of *fully checked* layouts.
4. Keep GUI tournament and CLI experiments distinguishable.

## Runtime and experimental settings

- Platform: macOS iMac, Node native v5 solver (`--native 1`), profiler `STRIPBOARD_TIMING=1`.
- Debug GUI: Pass 1 **200 seeds × 15,000 moves**; Pass 2 remains **25,000–100,000 moves in 5,000-move steps**, unchanged by profiling.
- CLI benchmarks: `--routing-preference wires`, **no** `--drilled 1`, **no** `--nostack 1`. Therefore **knife cuts and wire stacking were allowed**. Results must not be described as drilled-only or non-stacked. The CLI harness can emit off-axis wires, which are rejected by the benchmark's `clean` check; omitting a diagonal option does not by itself force zero diagonals.
- Board in the 20-seed comparisons and ladder input: `rows=24`, `cols=56`, `lockedRows=true`, `lockedCols=true`. Benchmarks check the **output** dimensions rather than assuming they were respected.
- For the *controlled* ladder, both A/B configurations are **copies of the same root `motomix.json`**, with only the detected F1 component's `locked` boolean changed: `FREE=false`, `LOCKED=true`. The starting F1 position is preserved, and the same seed indices and move budgets are used.
- The earlier *noncontrolled* comparison used two separate inputs: `test-fixtures/masters/moto/moto.json` (F1 unlocked) vs. root `motomix.json` (F1 locked). Do **not** interpret its differences as solely caused by the lock.
- Each move budget is a **fresh solve**, not a continuation of a prior ladder rung. Seeds are independent starting arrangements.

### Operational commands

Build the frontend solver after changing the TypeScript profiler:

```sh
cd ~/Documents/stripboard-optimiser/src/frontend
npx tsc -p tests/solver/tsconfig.json
```

Launch the GUI with file-backed profiling from the repo root:

```sh
STRIPBOARD_TIMING=1 PYTHONPATH=desktop/src python3 -m stripboard_optimizer.main
```

The native CLI entry point is `src/frontend/tests/solver/v5Solve.js`. Minimal single-seed invocation from `src/frontend` (the `--data` directory must contain `projects/1.json`):

```sh
STRIPBOARD_TIMING=1 node tests/solver/v5Solve.js --data /tmp/moto_lock_ladder/LOCKED --id 1 --seed 3 --moves 20000 --native 1 --routing-preference wires
```

Full ladder CSV, produced locally by the Python command from the November 23 debugging session: `/tmp/moto_lock_ladder/ladder_results.csv`. Earlier comparison CSV: `/tmp/moto_lock_benchmark/comparison.csv`. These `/tmp` files are **local and not committed**; paths may expire. The CLI benchmark scripts were pasted into Terminal, not added as a tracked script.

## Profiling: first 100 GUI seeds at 15k moves

Source: GUI v1.58-debug log from **2026-11-23 22:05:53 AEST**, full JSONL at local `motomix_work/seed_timings_20261123_220553.jsonl`.

| Seeds | Solve avg (ms) | Anneal (ms) | Extract (ms) | Skeleton (ms) | Repair (ms) | Routing (ms) | Clean by profiler |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1–25 | 1,159 | 969 | 15 | 17 | 45 | 73 | 8/25 |
| 26–50 | 1,145 | 943 | 13 | 15 | 35 | 107 | 6/25 |
| 51–75 | 1,172 | 957 | 14 | 34 | 36 | 87 | 7/25 |
| 76–100 | 1,245 | 992 | 14 | 15 | 37 | 156 | 12/25 |
| **Mean of batch means** | **1,180** | **965** | **14** | **20** | **38** | **106** | **33/100** |

**Interpretation:** `annealMs` is ~82% of `solveMs`, so the hot path is the native C annealing loop (including calls to `decode()`). This profiler does **not** independently measure C mutation, decode, scoring and acceptance. `exactRepairMs` was 0 in the reported run. Routing has occasional expensive outliers.

The initial two-seed direct CLI smoke test returned **37×38** and **33×44** output boards even though the intended GUI benchmark was 24×56. It is useful for phase timing, **not** for directly comparing layout quality or fixed-board compliance. On that smoke test seed 2, `quality=0` coexisted with `geo=1`, `offAxis=1`, crossings and issues: **Q0 alone is insufficient**.

## Completed 20-seed experiment: different source files, 15k moves

Source: user's local 40-solve Terminal output. Seeds 1–20 were run for each case.

| Metric | MOTO (F1 free) | MOTOMIX (F1 locked) |
|---|---:|---:|
| Mean annealing | 851.0 ms | 853.1 ms |
| Mean extraction | 10.6 ms | 10.8 ms |
| Mean skeleton | 25.2 ms | 13.0 ms |
| Mean repair | 33.3 ms | 30.8 ms |
| Mean routing | 148.4 ms | 56.4 ms |
| Mean solve | 1,097.7 ms | 996.4 ms |
| Median solve | 989 ms | 970 ms |
| Mean wires | 44.1 | 39.8 |
| Mean cuts | 62.0 | 56.3 |
| Clean by benchmark predicate | 0/20 | 2/20 |

MOTO seed 9 had a **1,696 ms routing outlier**, inflating the mean. The 0.3% difference in mean annealing does not indicate a material penalty from locking F1 **in this cross-project comparison**. Different source data and placements are confounders.

## Controlled A/B ladder: same MOTOMIX source, 10 seeds per rung

**Status: COMPLETE — all 200 solves reported.** Ten independent seeds (1–10) at each of the ten move budgets from 5,000 to 50,000, in 5,000-move steps, under each F1 configuration. All statistics below come from the uploaded Terminal transcript; the local raw CSV is at `/tmp/moto_lock_ladder/ladder_results.csv` and is not committed.

| Moves | FREE clean | LOCKED clean | FREE mean solve | LOCKED mean solve | FREE mean anneal | LOCKED mean anneal | Best clean FREE (W/C) | Best clean LOCKED (W/C) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 5,000 | 0/10 | 0/10 | 628 ms | 534 ms | 307 ms | 298 ms | — | — |
| 10,000 | 0/10 | 0/10 | 882 ms | 763 ms | 601 ms | 595 ms | — | — |
| 15,000 | 2/10 | 1/10 | 1,154 ms | 1,000 ms | 912 ms | 861 ms | 46/61 | 38/53 |
| 20,000 | 5/10 | 2/10 | 1,382 ms | 1,358 ms | 1,162 ms | 1,177 ms | 33/48 | 25/41 |
| 25,000 | 6/10 | 2/10 | 1,682 ms | 1,754 ms | 1,490 ms | 1,568 ms | 29/45 | 42/58 |
| 30,000 | 5/10 | 2/10 | 2,246 ms | 2,020 ms | 1,984 ms | 1,829 ms | 23/39 | 31/46 |
| 35,000 | 6/10 | 3/10 | 2,274 ms | 2,213 ms | 2,098 ms | 2,021 ms | 25/42 | 32/47 |
| 40,000 | 5/10 | 3/10 | 2,544 ms | 2,572 ms | 2,363 ms | 2,396 ms | 30/45 | 27/43 |
| 45,000 | 4/10 | 4/10 | 2,887 ms | 2,917 ms | 2,707 ms | 2,748 ms | 28/44 | 26/41 |
| 50,000 | 7/10 | 4/10 | 3,029 ms | 3,018 ms | 2,875 ms | 2,855 ms | 23/38 | **21/36** |
| **Overall** | **40/100** | **21/100** | — | — | **1,650 ms** | **1,635 ms** | **23/38** | **21/36** |

**Best reported clean candidate:** F1 **LOCKED**, **50k, seed #03**, **21 jumpers and 36 cuts**. The corresponding FREE seed #03 at 50k gave **23 jumpers and 38 cuts**. The best locked result is 4 jumpers and 5 cuts better than the prior locked 20k seed #03 (25/41). These counts are **not drilled-only** and **not stack-free** because both restrictions were disabled during the benchmark.

**Clean rate:** FREE 40/100 (40%); LOCKED 21/100 (21%). Within this ten-seed-per-budget experiment, locked F1 yielded fewer automatically clean layouts, despite producing the best individual layout. As a descriptive statistic only, mean annealing time across all 100 FREE runs was **1,650 ms** and across LOCKED runs **1,635 ms** (approximately 0.9% faster locked). That difference should not be interpreted as a reliable speed improvement.

**Effect of extra moves:** At 5k and 10k, both groups had zero clean layouts. The highest observed clean rate within each configuration occurred at **50k**: FREE 7/10, LOCKED 4/10. Individual-rung success rates are **not monotonic** (for example, FREE 6/10 at 25k, 5/10 at 30k; LOCKED 4/10 at both 45k and 50k). Independent budgets are fresh solves, and ten seeds per rung are insufficient to infer a global optimum.

**Routing and outliers:** Mean solve times vary beyond the annealing component; native routing occasionally takes substantially longer on difficult layouts. Compare medians and the raw per-seed rows when investigating routing performance rather than relying only on mean solve time.

## Completed 80-run drill/stack matrix (20k moves, 10 common seeds)

**Metric correction (subsequent CLI audit):** The old `diagonals_actual` field counted every wire with different endpoint **columns**—including horizontal wires. The harness `offAxis` metric counts only genuine slants where both row and column change. Therefore the 80-run `clean` gate was *vertical-wires-only*, not simply 'no diagonal wires'. The original results are preserved for comparability; see [CLI audit](cli-audit-2026-11-23.md) for the corrected categories.



A separate test used [`scripts/benchmark_drill_stack.py`](../scripts/benchmark_drill_stack.py) with fixed sampled seeds **382, 639, 736, 820, 897, 1036, 1121, 1277, 1437, 1552** (all between 1 and 2,000), **20,000 moves** per run, native solver, wire-priority routing. Each input was forced to a **locked 24×56 board**. The MOTO source's F1 remained **unlocked and unplaced**; the MOTOMIX source's F1 remained **locked at row 0, col 1**. Thus the *boards* were locked in both projects, but **F1 was not locked in MOTO**. These are different source projects, not a controlled lock-only comparison.

All 80 processes finished. The harness output includes actual endpoint-column diagonal counts (`↘`), knife cuts (`🔪`) and stacked wires (`🧵`). The benchmark independently inspects the saved layout for output dimensions and F1 lock retention, and its strict `clean` predicate requires zero diagonals, Q0, zero electrical/geometry problems, and the drill/stack restrictions selected for that run.

| Project | Drilled only | Stacking allowed | Clean / 10 | Mean solve (ms) | Mean anneal (ms) | Mean diagonals | Mean knife cuts | Mean stacked wires |
|---|---|---|---:|---:|---:|---:|---:|---:|
| MOTO | ON | OFF | 0/10 | 1,350 | 1,140 | 3 | 6 | 3 |
| MOTO | OFF | OFF | 0/10 | 1,353 | 1,150 | 3 | 13 | 2 |
| MOTO | OFF | ON | 0/10 | 1,290 | 1,140 | 3 | 13 | 4 |
| MOTO | ON | ON | 0/10 | 1,291 | 1,121 | 3 | 6 | 4 |
| MOTOMIX | ON | OFF | 0/10 | 1,476 | 1,235 | 4 | 5 | 2 |
| MOTOMIX | OFF | OFF | 0/10 | 1,521 | 1,242 | 2 | 12 | 2 |
| MOTOMIX | OFF | ON | **1/10** | **1,403** | 1,198 | 2 | 12 | 4 |
| MOTOMIX | ON | ON | 0/10 | 1,446 | 1,207 | 3 | 5 | 4 |

**The only strict pass:** MOTOMIX **DRILL_OFF_STACK_ON**, **seed 897**, **33 jumpers / 48 cuts**, Q0, zero diagonals, zero geometry findings and about **1,296 ms** solve time. It had **8 knife cuts and 3 stacked wires**, which the configuration explicitly allowed. This candidate is not drilled-only or stack-free.

**Critical known solver limitation:** both `--drilled 1` and `--nostack 1` were passed correctly to the harness, but the solver still emitted forbidden knife cuts and stacked wires. Physical-rule flags must be treated as *requests*, not guarantees. Independent post-solve validation correctly rejected all 40 MOTO layouts and 39 of 40 MOTOMIX layouts in this trial. Q0 and `geo=0` alone do not ensure compliance.

**Speed:** with drilling OFF and stacking ON, mean solve time was lowest of the four tested combinations for both projects (MOTO 1,290 ms, MOTOMIX 1,403 ms). However 10 seeds per group and routing variability mean this is descriptive, not an established universal optimum.

**Files:** local CSV `/private/tmp/stripboard_drill_stack_80/comparison.csv` and saved layouts under `/private/tmp/stripboard_drill_stack_80/`. These paths are on the user's Mac and are not committed. The test transcript was provided in the conversation.

## Validity and measurement caveats

The benchmark Python predicate for `clean` required all of:

- `quality == 0`, `conflicts == 0`, `incomplete == 0`, `geo == 0`, `offAxis == 0`;
- `issues` empty;
- output `rows == 24` and `cols == 56` for the controlled ladder.

A `clean` flag is an **automated screening result**, not independent proof that every locked part remained at its required coordinate, every cut was drilled, or wires were unstacked. The benchmark did not enforce drilled-only or no-stacking rules. The GUI worker's own qualifier can use a different predicate; do not equate GUI `🎯Q0` with this script's `clean` count.

Interpretation across the completed 5k–50k ladder:

- Anneal cost rises with move budget in both configurations; no consistent material F1-lock speed penalty is established.
- Clean results first appeared at 15k; the largest observed clean count in both configurations was at 50k. Rates vary at intermediate rungs and do not prove 50k is universally optimal.
- Routing outliers distort averages; report median or distributions alongside means in follow-up tests.
- Larger samples and strict input/output lock checks are needed before causal claims or release-quality validation.

## Next debugging steps

1. Inspect the saved **locked 50k seed-3** board: exact F1 position/rotation, knife-cut count, wire stacking, electrical and geometry checks. Also compare its placement against the free 50k seed-3 board.
2. For a **drilled-only** benchmark pass `--drilled 1`; for **no stacking** pass `--nostack 1`; these are new experimental constraints, not properties of the recorded results.
3. If speed optimisation continues, add *opt-in* instrumentation inside native `v5_annealStep()` to separate mutation, `decode()`, scoring, failed decodes and accepted/new-best moves. Preserve deterministic solver outputs and compare fingerprints before and after changes.
4. Keep the complete raw per-seed CSV alongside any future reproducibility package; this documentation reports aggregate results, not the complete machine-readable 200-seed dataset.
