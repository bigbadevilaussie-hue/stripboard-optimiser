# Native MOTOEX 200 × 25k fixed-USB sweep — reproducible run

**Status:** runner and configuration tests are committed; the user's iMac has **not executed this sweep yet** as of creation. **Active branch:** `feature/native-edge-slide-motoex`.

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
  source_sha256.txt         (in manifest sourceSha256)
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
