# Native CLI v1.61 diagnostic tools — budget sweep and physical failure matrix

23 November 2026 · **CLI-only**. The Tkinter GUI is intentionally out of scope and may remain stale.

## Decision from Claude's 80-run review

The v1.60 profile established that the final selector did not discard compliant candidates:

| Observation | Measured result |
|---|---:|
| Original output fingerprints | 80 / 80 matched |
| Strict-compliant selected outputs | 1 / 80 |
| Strict-compliant repair outputs | 0 / 80 |
| Repair candidates with `ok=true` | 0 / 80 |
| Both finish candidates failed | 79 / 80 |
| Valid finish candidates discarded | 0 / 80 |
| Proposals rejected after full decode | 1,072,704 / 1,600,000 (67.0%) |
| Same-board proposals | 446,966 / 1,600,000 (27.9%) |
| `repairSlantWires` routing time | 98.6 ms mean; 1,307.3 ms max at four workers |

**Implications:** Do not give the router/repair score asymmetry top priority. It is real, but did not account for a lost compliant result in this sample. Do not ship unproved early rejection, modify seed RNG, or cap slant repair yet. Longer anneal budgets may improve placement quality and should be tested before changing the objective.

The observation that the placement is *unfinishable* applies to the **two available finishing methods at 20k moves**, not a mathematical proof that no legal board exists at that placement or any other placement. Electrical and geometry checks still reuse harness validators rather than a new independent netlist verifier.

## Verified code assumptions

`src/frontend/components/stripboard/autoLayout5.ts` currently uses:

```ts
const seedsN = Math.max(1, options?.seeds ?? 6);
const capMoves = options?.effort !== undefined
  ? effortMoves(nPins, options.effort)
  : Math.min(1280000, Math.max(40000, 16000 * (nPins - 13)));
const movesN = options?.moves ?? /* time-budget override or capMoves */;
const seedList = options?.seedIndex !== undefined
  ? [options.seedIndex]
  : [...Array(seedsN).keys()].map((k) => k + (options?.seedBase ?? 0));
```

The *native CLI* `v5Solve.js` supplies `seedIndex: seed`, so **one seed per native solve**, not the six-seed portfolio default. `--moves 20000` overrides the usual minimum of 40k and potential 1.28M maximum. Importantly, `rampEnd: movesN * rampEndFrac` scales the penalty ramp to each budget, and cooling is also defined by movesN. Therefore 100k/500k are **independent anneals with different temperature/ramp schedules**, **not continuation** of a 20k board or proof that quality changes monotonically.

At 4 configs × 3 seeds × 3 budgets, the proposed experiment is **36 runs**, not 24.

## Tool A — analyse the existing 80-run failure matrix, instantly

```sh
python3 scripts/native_failure_matrix.py
```

Reads the existing `/tmp/stripboard_drill_stack_80/cli_profile_v160_full80/finish_matrix.csv` and prints:

- Per-configuration totals for selected-compliant, either-finish-compliant, minimum zero/one/two fail categories.
- Failure counts for `COLUMN_SHIFT`, `CROSSINGS`, `STACKED`, `KNIFE`, and `GEOMETRY` in *repair*, *router*, a **closest** candidate, and both candidates.
- Electrical failures, any compliant candidate discarded, and strict pass counts.

The **closest** candidate is explicitly chosen by *fewest electrical failures* first, then fewest distinct validation failures, with selected candidate as the final tie-breaker. It is an analysis-only convention, not a new solver ranking. `minimumFailures` independently reports the literal smaller number of failed categories across either candidate. `BOTH` means a problem is present in the two current finish candidates; it is not proof that the constraint is infeasible for that placement.

Output: `.../cli_profile_v160_full80/failure_breakdown.csv`. It does not modify the source matrix.

## Tool B — MOTOMIX native move-budget sweep

```sh
python3 scripts/sweep_native_move_budget.py --jobs 4 --resume
```

Defaults:

- Source: **MOTOMIX** locked 24 × 56 benchmark copy, with the four drill/stack combinations exactly as stored in the baseline CSV.
- Seeds: `897,1036,1552`; 897 is the clean baseline case, 1036 the geometry-sensitive case and 1552 the routing-spike case.
- Budgets: `20,000`, `100,000`, `500,000` moves.
- Native decoder and native router, `routing-preference=wires`, one explicit seed, `--strict 1`, `--finish-trace 1`, `--move-summary 1`.
- Worker count `--jobs 4`, capped at available physical cores. **Use `--jobs 1` for timing comparisons; parallel per-run timing is contended.**

**Golden gate:** all 12 runs at 20k must match the original saved-board SHA1 `sig` fingerprints *and* the original CLEAN verdict. A mismatch or CLI error stops the sweep before running 100k or 500k. At higher budgets, changed signatures are **expected**, not errors. Missing candidate diagnostics, bad score reconstruction or failed project checks remain errors at *all budgets*.

**Data safety:** The script snapshots the original CSV with its SHA256, saves its configuration, writes each case to its own `moves_XXXXXXX` subdirectory with atomic checkpoints, and refuses reuse of an output directory with a different baseline SHA256/config. Neither the original CSV nor its saved layouts is replaced. Use `--resume` after interruption; rerunning without it recalculates cases only inside the sweep output directory.

Outputs under `/tmp/stripboard_drill_stack_80/cli_budget_sweep_v161/`:

- `budget_results.csv`: each individual candidate's actual metrics, score terms, failure reasons, route phases, acceptance histogram, strict validity and 20k fingerprint gate.
- `budget_summary.csv`: per-budget/per-configuration compliance and the minimum number of failed categories.
- `failure_breakdown.csv`: per-run closest/actual/common failure comparison across budgets.
- `moves_0020000`, `moves_0100000`, `moves_0500000`: raw per-run outputs, stderr logs, checkpoints and results.
- `baseline_snapshot.csv`, `sweep_config.json`: reproducibility metadata.

Options include `--project`, `--seeds`, `--budgets`, `--bench`, `--out`, `--jobs`, `--resume`. Custom `--budgets` **must start at 20000** to preserve the baseline gate. For a smoke run with the same validation, supply `--budgets 20000`; it runs 12 original-seed cases.

**Interpretation:** Compare compliance counts, candidate-level failure categories and `minimumFailures` across budgets. A steep reduction with more moves supports under-budgeting as a material factor; a persistent plateau supports investigating native objective gaps, though a plateau at these three budgets is not proof that the search can never solve it. A fixed seed is not an identical temperature sequence across budgets.

## Verification command for the Mac

One terminal paste runs static Python checks, pure-Python unit tests, the *existing* 80-run failure breakdown and the independent native budget sweep. It does **not** launch or modify the GUI.

```bash
cd ~/Documents/stripboard-optimiser && \
set -o pipefail && \
git pull --ff-only origin main && \
python3 -m py_compile scripts/native_failure_matrix.py scripts/sweep_native_move_budget.py scripts/profile_native_cli.py scripts/tests/test_native_cli_matrix.py && \
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_native_cli_matrix.py' -v && \
python3 scripts/native_failure_matrix.py && \
(cd src/frontend && npx tsc -p tests/solver/tsconfig.json) && \
python3 scripts/sweep_native_move_budget.py --jobs 4 --resume 2>&1 | tee ~/Desktop/stripboard_v161_cli_sweep.log
```

**Version separation:** `v1.61-cli-budget-sweep` identifies the new Python experiment tools; the native CLI remains **v1.60-cli-audit** and the native solver binary/scoring remains unchanged. No GUI version bump is part of this release.

## Deliberately not implemented yet

- **Native early rejection:** Need a conservative lower bound at the actual current anneal energy (including dynamic temperature/ramp and hard penalties) and RNG-preserving differential tests before enabling.
- **Same-board optimisation:** Genome drift may be useful; same-board accepts are already detected before grid/routing. Don't skip without comparative quality evidence.
- **Repair-slant work cap:** The 1,307 ms route-phase outlier is demonstrated, but no cap/no-progress heuristic is shipped without testing that it does not discard better layouts.
- **Annealing stacking objective:** No native stacking term currently, but the budget sweep precedes changing the objective.
- **Independent netlist/physical validation:** The checks still use the repository harness; a separate rigorous validator remains future work.

Focus for subsequent work: **native CLI, C decoder, TypeScript finishing library as invoked by CLI, and native benchmark scripts only. Leave GUI integration stale.**
