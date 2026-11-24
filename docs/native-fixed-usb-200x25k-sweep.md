# Native MOTOEX 200 × 25k fixed-USB sweep — reproducible run

**Status updated from the user's iMac log, 24 November 2026:** **200/200 completed, 0 strict solved, 150.08 s wall time.** Exact run command and build tests passed. The earlier pre-run description below is historical. **Active branch:** `feature/native-edge-slide-motoex`. See measured diagnostics in the next section.

## Measured result — Mac run 200 × 25k, USB fixed col47 (no slide)

The user pasted the entire 200-seed terminal run. Native build, config tests (6/6) and fixed tournament completed. There were **0/200 strict passes**, so **no top five solved JSONs exist**. The `top5/` folder was correctly left empty; candidates were retained under `rejected/`, with per-seed timing and diagnostics in `results.jsonl`, `results.csv` and `jobs/`.

| Metric | Measured |
|---|---:|
| Seeds finished | **200 / 200** |
| USB slide | **OFF**, row 13 col 47 for all 200 |
| Moves per seed | 25,000 |
| Strict passes | **0** |
| Wall clock | **150.08 seconds** |
| Mean per-job duration in terminal | **4.45 seconds** |
| Electrically complete routed boards | **63 / 199** |
| No feasible placement | **1 (seed 162)** |
| Electrically complete AND zero nonvertical wires | **1 (seed 157)** |
| Electrically complete AND zero component crossings | **1 (seed 129)** |
| Electrically complete AND both zero | **0** |

**Five closest *strictly invalid* candidates (not claimed solved):**

| Seed | Wires / cuts | Nonvertical | Crossings | Knives (allowed) | Stacks (allowed) | Opens |
|---:|---:|---:|---:|---:|---:|---:|
| **157** | 43 / 59 | **0** | **1** | 10 | 7 | 0 |
| **129** | 40 / 56 | **1** | **0** | 7 | 4 | 0 |
| 151 | 40 / 56 | 1 | 2 | 9 | 6 | 0 |
| 111 | 42 / 58 | 1 | 2 | 9 | 6 | 0 |
| 69 | 56 / 72 | 1 | 2 | 24 | 18 | 0 |

These rankings were derived from the pasted terminal log as an **electrical-first/physical-defect-first post-analysis**, not from the strict top-five winner list (which has zero entries). They are **NOT build-ready**. The original runner already saved their JSONs in `rejected/`; no need to rerun 5 million moves.

**High-value next repair:** inspect wire crossings for seed **157** and nonvertical wiring for seed **129**. The general-purpose solver needs a bounded conflict-directed component/wire reroute rather than more seeds at the same budget. The user explicitly allowed knife cuts and stacking in this sweep. Do **not** relax opens, body crossings, exact locked board bounds, or nonvertical wire rules to manufacture a strict PASS.

**New post-analysis tool:** `scripts/analyze_motoex_native_sweep.py` ranks the nearest **electrically complete** but strictly invalid boards, copies their JSONs to a separate `analysis/near_misses/` directory, and writes `analysis/near_miss_report.md`, `analysis/near_miss_summary.json`, and `analysis/near_misses.csv` including full stored per-wire component-crossing and stack-partner diagnostics, timing and move summary. The source results and JSONs are unchanged.

```bash
cd ~/Documents/stripboard-optimiser
git pull --ff-only
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_analyze_motoex_native_sweep.py' -v
python3 scripts/analyze_motoex_native_sweep.py \
  --out ~/Desktop/motoex_native_fixed_200x25k_v1 --top 5
```

The analyzer and its synthetic tests were committed **after** the 200-seed run; they must still be run on the Mac. This post-processing is fast and requires **zero** additional anneals. The actual `results.jsonl` files provide more detailed timings than the terminal log, and are the authoritative input for deeper analysis.

## Decisions and controls

This is a **one-pass tournament**, not Edge+Slide discovery. The same physical layout problem is presented to 200 native v5 seeds. Core solver remains general purpose; the MOTOEX-specific JSON preparation is confined to the benchmark controller `scripts/run_motoex_native_sweep.py`.

| Setting | Selection |
|---|---|
| USB Slide | **OFF** (`--slide no`), a different explicit `--slide yes` experiment is later |
| USB position | Original source **row 13, column 47**, rotation 0, locked |
| USB edge | **ON**, two rows of body overhang only; pins stay on the purchased board |
| Other locks | Ignored per established fixture contract |
| Board | **24×56**, rows and columns immutably locked |
| GPS | Full physical footprint on-board; ordinary solver choice of placement/rotation |
| Solves | **200 total** independent seeds, **25,000 moves per seed** = 5 million attempted annealing moves |
| Native build | Separate Edge decoder, standard native route library and portable Node addon |
| Drilled-only | **OFF**, so between-hole knife cuts are allowed |
| Stacking forbidden | **OFF**, so stacked jumpers are allowed |
| Rotation drill domain | **OFF**, because drilled-only is not requested |
| Strict quality checks retained | Zero electrical opens/shorts, legal placement, no nonvertical/horizontal jumper, no wire crossing through component bodies, exact physical board and locks |
| Polisher | **ON** (`--wire-polish yes`) for wire-column improvement, not mandatory for stack/knife constraints; records per-seed stats |
| Ranking | First wire count, then cut count, then total wire length, then weighted price; rank **strict passes only** |
| Duplicate policy | **Physical layout** signature includes placements, rotations, exact cuts, exact wire endpoints — alternate wiring remains distinct |
| Candidate preservation | **EVERY strict-solved project JSON** in `solved/`, even duplicate signatures, plus every rejected project in `rejected/`. Top 5 get separate `top5/` copies. None of the master files are edited. |
| Parallelism | Six isolated Node processes by default in the example, each with its own input JSON and logs |
| Reporting | Progress emojis, independent validation, per-seed timing breakdown, CPU and RSS, move acceptance/rejection histogram, finisher trace, first in-cap move, strict failure codes |
| Interrupt/restart | `--resume` validates source and binary fingerprints, uses `results.jsonl` checkpoint, skips completed seeds |

## Run on the user's iMac

```bash
cd ~/Documents/stripboard-optimiser && \
git pull --ff-only && \
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_motoex_native_sweep.py' -v && \
cd src/frontend && \
npx tsc -p tests/solver/tsconfig.json && \
npm run build:native && \
npm run build:native:edge && \
cd ../.. && \
python3 scripts/run_motoex_native_sweep.py \
  --slide no --column 47 \
  --seeds 200 --seed-start 1 --moves 25000 \
  --workers 6 --rank wires --wire-polish yes \
  --out ~/Desktop/motoex_native_fixed_200x25k_v1
```

**Do not insert `--slide yes` for this run** and do not use the older `run_motoex_native_edge_slide.py` 51-anchor controller, which searches a different problem. A failed *seed* is retained with diagnostics; only a failed build/test or genuine runner error should stop the batch.

If the runner is interrupted and the original Git/build/source fingerprints remain unchanged, resume with the **same arguments** plus `--resume` (no rebuilding after interruption if avoidable). If binaries or source change, use a new output directory to preserve comparability.

## Output tree

```text
~/Desktop/motoex_native_fixed_200x25k_v1/
  manifest.json             source SHA256, Git commit, options, library/addon hashes
  progress.log              emoji progress + final top five
  results.jsonl             crash-resistant checkpoint: one complete record per seed
  results.json              all 200 attempts, statuses, timings, physical diagnostics
  results.csv               one row per seed, filters and time columns
  summary.json              timing distribution, failure histogram, top five, all solved
  solved_index.jsonl        ranked metadata for every strict-solved board
  report.md                 human-readable summary and top-five table
  top5/                    copies of up to five distinct physically solved layouts
  solved/                  **all** strict-solved JSONs (not just five)
  rejected/                saved failed/partial JSONs for post-analysis
  jobs/
    seed_0001_col_47/
      input/projects/1.json
      stdout.log
      stderr.log
      [candidate.json moved to solved/ or rejected/]
    ... up to seed_0200_col_47/
```

A zero-qualifier result is reported as **0 strict passes** and an empty top-five list, not five best invalid boards. All failures remain in `results.json`/CSV with full violation codes and saved rejected JSONs.

## Later USB Slide sweep (a separate study)

There is an **explicit separate** option: `--slide yes --columns all`, or `--slide yes --columns 25,41`. With Slide ON, the 200 seeds are **distributed round-robin** over the selected legal anchors, still exactly one solve per seed. This future run must use a **different `--out`**. The fixed sweep does not move or test USB columns.

## Known interpretation boundary

Allowing knife cuts and wire stacking does **not** relax electrical completeness, board size, component-body crossing or vertical-wire constraints. The physical checker is still authoritative; best score is not a certificate. Timings are measured on the user's Mac, so no speculative runtime is recorded here before execution. See [full engineering handover](START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md).
