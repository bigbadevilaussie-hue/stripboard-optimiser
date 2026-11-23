# Native speed lab v1.65 — measured v1.64 results and held-out confirmation

**Recorded 24 November 2026**  
**Source:** user-supplied iMac terminal output, v1.64 speed lab, saved original CSVs on iMac; this repository does not yet contain their raw CSV or saved layouts.  
**Status:** preliminary same-output speed gain **observed**; production solver unchanged.

## Completed v1.64 experiment

The user ran the complete serial decoder and router speed labs after the `parse_json_line` correction. All six Python speed-lab unit tests passed; 11 decoder binaries compiled; 7 router binaries compiled. Each reported candidate matched the original saved project JSON SHA256, CLI output, exit-code/strict status, and reference binary for the 24 tested project/policy/seed/repeat cases.

**Design:** locked 24×56 AUDIO and corrected MOTO, three seeds (1–3), two repeats, two routing configurations (loose and drilled/no-stack), fixed 20,000 moves, `--native 1`, `--strict 1`, `--routing-preference wires`. These are comparisons of identical solver outputs, **not** a claim that every file in the sample was a new physically build-ready WR. CLI strict eligibility and electrical correctness are separate from the speed result.

### Exact summary as supplied from iMac

| Decoder `clang` variant | Median solve throughput gain | Median anneal throughput gain | Full-output equivalence |
|---|---:|---:|---:|
| `o2` | −1.50% | −1.27% | 24/24 |
| `fp_off` | +0.26% | +0.32% | 24/24 |
| `cpu` | −0.23% | −1.08% | 24/24 |
| `no_errno` | −0.55% | −0.62% | 24/24 |
| `unroll` | −0.37% | +0.03% | 24/24 |
| `grid` | −0.28% | +1.41% | 24/24 |
| `identical` | +2.95% | +3.32% | 24/24 |
| **`both`** | **+4.64%** | **+5.76%** | **24/24** |
| `cpu_both` | +1.56% | +1.62% | 24/24 |
| `lto` | −0.17% | −0.33% | 24/24 |

| Native router variant | Median solve throughput gain | Median anneal throughput gain | Full-output equivalence |
|---|---:|---:|---:|
| `o2` | +0.60% | +0.04% | 24/24 |
| `fp_off` | +1.32% | +0.58% | 24/24 |
| `cpu` | +1.50% | +0.95% | 24/24 |
| `no_errno` | +0.07% | +0.06% | 24/24 |
| `unroll` | +0.99% | −0.63% | 24/24 |
| `lto` | +0.97% | +0.57% | 24/24 |

**Interpretation:** the combined identical-genome + bulk grid-clear decoder is the strongest current candidate; its advantage was seen under both the AUDIO and MOTO cases in console percentages, though individual measurements have substantial noise. The `grid` change by itself has no reliable whole-solve benefit; the combined effect may be due to instruction layout, memory/cache effects, or actual interaction and must be measured with more seeds. CPU-native flags reduce the gain when combined on this machine. Router-only compiler flags yield about 0–1.5%, within observed noise. Do not automatically promote a router flag.

All reference files produced **exact same JSON** in this sample. No silent WR edits and no normal-build changes.

## Changes for v1.65 controlled retest

The next laboratory adds a **third disabled** C experiment, `V5_EXPERIMENT_FAST_GENOME_COPY`, using built-in bulk copy for the disjoint accepted/proposal genome buffers instead of per-element loops.

Two new decoder variants:

- `copy`: `-O3 -DV5_EXPERIMENT_FAST_GENOME_COPY=1`
- `copy_both`: the copy macro plus the two previously tested macros

These are *not known to be faster*; they simply test whether proposal array copying is worth optimising. Ordinary production builds have none of these macros. This source change does not affect the default native or WASM solver.

Also added:

- `--seed-start` to use genuinely unseen seeds instead of repeatedly evaluating seeds 1–3.
- `speed_lab_stratified.csv` providing median solve/anneal speed, sample count, exact-match count and number of paired speed wins for each **variant × fixture × routing policy**, preventing a pooled median from hiding a MOTO regression.
- Test checks for the additional flag combinations and more parser cases.

## Confirmation run (iMac): held-out seeds 4–23

**This command is not yet executed.** It deliberately *excludes* seeds 1–3 used to choose the first candidate. Test four focused variants and the baseline at the same move budget and fixed constraints. Output is separate from previous CSVs.

```bash
cd ~/Documents/stripboard-optimiser && \
set -o pipefail && \
{
  git pull --ff-only origin main &&
  python3 -m py_compile scripts/speed_lab_native.py scripts/tests/test_speed_lab_native.py &&
  PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_speed_lab_native.py' -v &&
  (cd src/frontend && npx tsc -p tests/solver/tsconfig.json) &&
  python3 scripts/speed_lab_native.py \
    --target decoder --seed-start 4 --seeds 20 --repeats 2 \
    --moves 20000 \
    --variants o3,grid,identical,both,copy,copy_both \
    --out ~/Desktop/stripboard_speedlab_v165_decoder_holdout
} 2>&1 | tee ~/Desktop/stripboard_speedlab_v165_holdout.log
```

This schedules `2 fixtures × 2 policies × 20 seeds × 2 repeats × (1 existing native baseline + 2 `-O3` references + 5 alternatives) = 1,280` serial solves. Every candidate result must pass the exact saved-JSON equivalence gate. Failures are preserved for inspection.

After this run, use different seeds and budgets (5k and 50k), and assess change across both WR-producing fixture versions including original MOTO input if available. **Do not claim record parity without matching both original WR files and their exact historical flags and input hashes.**

### Acceptance gate

Do not promote a variant until:

1. Every input and policy yields exact original output on expanded held-out seeds and multiple budgets; no unexplained parity mismatch.
2. The per-policy medians on **both** AUDIO and MOTO are convincingly positive under repeat serial timing, not just the pooled median.
3. The gains persist after thermal, order and startup effects are separated. Candidate speed is measured as *solve throughput* and CPU seconds, not merely per-run percentages.
4. Original WR artefacts, configuration semantics and build footprints stay unchanged.

Once a candidate passes, commit a **separate, reversible** production speed patch and immediately run native regression and fixed WR reproduction; otherwise leave experimental macros disabled.

## Important constraints from the source

The native decoder already shares reusable arena/grid buffers. Its `decode()` already detects same-*board* proposals and exits before full grid assessment; many same-board changes involve different genomes and cannot be dropped from the annealing chain. The new `identical` macro only shortcuts a byte-identical genome, which avoids those unsafe same-board skips. This still needs broad replay because decode can mutate strip-group labels and consume its own tie-protection random stream under conflicts.

The previously measured **67.0% Metropolis reject-after-decode** rate remains the largest potential opportunity, but attempting earlier rejection demands a rigorous lower bound of the complete schedule-dependent objective and preservation of random draw ordering. Do not approximate such a bound and corrupt WR search.

## Source references

- [Baseline audit and 80-case profile](cli-audit-2026-11-23.md)
- [v1.64 experiment framework](native-speed-lab-v164.md)
- [Native solver / Route-Mate GUI deferred migration](route-mate-native-solver-integration-roadmap.md)

---

## Held-out v1.65 outcome — user-supplied iMac results (24 November 2026)

**Status: completed.** The previously specified decoder held-out run finished successfully for **seeds 4–23**, **20,000 moves**, **AUDIO + corrected MOTO**, **loose + drilled/no-stack**, **two serial repeats**. The user supplied the terminal summary (original full CSVs and the individual saved project JSONs remain on the iMac, and have not been independently reviewed here).

| Experimental decoder | Median solve throughput gain | Median anneal throughput gain | Exact output matches |
|---|---:|---:|---:|
| `grid` | +1.12% | +1.27% | 160/160 |
| `identical` | +3.04% | +3.29% | 160/160 |
| **`both`** | **+5.24%** | **+6.08%** | **160/160** |
| `copy` | +0.32% | +0.10% | 160/160 |
| `copy_both` | +5.03% | +5.91% | 160/160 |

All **800 candidate comparisons** reported exact matches. Both shortcuts together are the best candidate; genome copying adds no measured benefit on this trial. Compared with the v1.64 discovery trial (`both`: +4.64% solve, +5.76% anneal, 24/24), the held-out result supports a reproducible approximately 5% gain, though individual run speed still varies. **The per-fixture / per-policy stratified CSV was not included in the supplied summary, so subgroup regressions remain unassessed.** No claim of matching the two historical WR artifacts is made from these newer input fixtures.

### Opt-in build provided; regular solver still unchanged

`src/frontend/package.json` now offers `npm run build:native:fast`, which compiles only the `both` C decoder into `src/frontend/tests/solver/native/build/fast/libv5decode.so`; **it does not overwrite** the default `libv5decode.so`, the router, the native addon, the browser WASM, or any world-record file.

```bash
cd ~/Documents/stripboard-optimiser
git pull --ff-only origin main
cd src/frontend
npm run build:native:fast
```

The existing CLI takes the **fast C decoder via an opt-in environment variable**, with the same native engine and same unchanged CLI protocol:

```bash
cd ~/Documents/stripboard-optimiser/src/frontend
V5_NATIVE_LIB_DIR="$PWD/tests/solver/native/build/fast" \
node tests/solver/v5Solve.js --data /path/to/fixture-directory --id 1 \
  --seed 4 --moves 20000 --native 1 --routing-preference wires \
  --drilled 1 --nostack 1 --strict 1 --save /tmp/v5-fast-candidate.json
```

Unsetting `V5_NATIVE_LIB_DIR` returns to the original solver binary; the extra library exists only as a lab-side experiment. **Do not treat this opt-in binary as production-approved yet.**

### Next parity gate — test different move schedules, not just more 20k seeds

The 20k cases do **not** prove parity at 5k or 50k. Run 5k and 50k tests on unseen seeds (24–35), with both 24×56 projects, both routing policies and two serial repeats. Use separate output folders to preserve the original evidence:

```bash
cd ~/Documents/stripboard-optimiser && \
set -o pipefail && \
{
  git pull --ff-only origin main &&
  PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_speed_lab_native.py' -v &&
  python3 scripts/speed_lab_native.py \
    --target decoder --seed-start 24 --seeds 12 --repeats 2 \
    --moves 5000 --variants o3,both \
    --out ~/Desktop/stripboard_speedlab_v165_5k &&
  python3 scripts/speed_lab_native.py \
    --target decoder --seed-start 24 --seeds 12 --repeats 2 \
    --moves 50000 --variants o3,both \
    --out ~/Desktop/stripboard_speedlab_v165_50k
} 2>&1 | tee ~/Desktop/stripboard_speedlab_v165_budget_gate.log
```

Each budget entails **384 serial solves** including the reference and bookend baselines; full test **768 solves**. On completion, review **both** stratified CSVs before deciding whether `both` can be defaulted; the speed gain must not hide an adverse MOTO or drilled-only subgroup. Verify full WR input snapshots and record settings separately before promoting to the native default. **No route logic or search algorithm changed.**

---

## Multi-budget WR-safety performance gate — iMac results, 24 November 2026

**Completed** the previously specified 5k and 50k follow-up on **seeds 24–35** (disjoint from 1–23), each using AUDIO and corrected MOTO, `loose` and `drilled_no_stack`, with two repeats. **All full saved JSON comparisons reported identical** to baseline.

| Native decoder | Moves per seed | Median solve throughput gain | Median anneal throughput gain | Saved JSON + strict CLI matches |
|---|---:|---:|---:|---:|
| **`both`** | **5,000** | **+2.91%** | **+5.44%** | **96/96** |
| **`both`** | **50,000** | **+5.51%** | **+5.92%** | **96/96** |

Adding the 20,000-move discovery (24/24) and held-out confirmation (160/160), the same `both` decoder has **376/376 reported exact baseline matches across three move budgets**. The original 6 unit tests also passed in the follow-up log. This is **very strong evidence for the deterministic replay compatibility** of the two compile-time decoder optimisations in these tested inputs, modes, and seeds. It does **not** reproduce the original historical WR files or certify the physical buildability of a layout that the baseline itself did not qualify.

### Breakdown by project/policy (approximately, from rounded terminal percentages)

The user supplied the complete terminal transcript but not the unrounded per-case CSV, so these medians were calculated from the printed one-decimal speedups. The script's exact pooled medians above come from its CSV values and supersede estimates below.

| Moves | Fixture | Cut/stack policy | Median solve gain, estimated | Positive solve-speed cases |
|---:|---|---|---:|---:|
| 5k | AUDIO | loose | +1.55% | 20/24 |
| 5k | AUDIO | drilled/no-stack | +3.00% | 19/24 |
| 5k | MOTO | loose | +2.85% | 20/24 |
| 5k | MOTO | drilled/no-stack | +3.20% | 20/24 |
| 50k | AUDIO | loose | +5.70% | 24/24 |
| 50k | AUDIO | drilled/no-stack | +5.65% | 22/24 |
| 50k | MOTO | loose | +5.35% | 24/24 |
| 50k | MOTO | drilled/no-stack | +5.10% | 21/24 |

All eight approximate subgroup medians are positive. The 5k solve-time metric can be dominated by finite CLI startup/finalisation costs, which vary more than anneal time; the 50k signal is substantially stronger and more consistent. A few large positive and negative outlier percentages in 5k demonstrate the importance of medians, per-fixture stratification, warm machine state and isolated processes.

**Engineering decision:** `-DV5_EXPERIMENT_FAST_GRID_CLEAR=1 -DV5_EXPERIMENT_FAST_IDENTICAL_GENOME=1` is the leading implementation. The `copy` variants bring no statistically persuasive improvement; do not enable copy. Router compiler flags remain unpromoted.

### Opt-in fast native CLI (already implemented)

The proven `both` variant remains available through `npm run build:native:fast` and `V5_NATIVE_LIB_DIR`, leaving ordinary `npm run build:native`, committed WASM, output formats and GUI unchanged. This is **the same native C solver**, never a secondary solver. Example:

```bash
cd ~/Documents/stripboard-optimiser/src/frontend
npm run build:native:fast
V5_NATIVE_LIB_DIR="$PWD/tests/solver/native/build/fast" \
  node tests/solver/v5Solve.js --data /path/to/input-dir --id 1 \
  --seed 24 --moves 50000 --native 1 \
  --routing-preference wires --drilled 1 --nostack 1 --strict 1 \
  --save /tmp/v5-fast-50k.json
```

**Remaining production gate:** the two historical WR input projects, exact historical seed/move/schedule and record files are not in GitHub fixtures. They must be replayed and compared independently before changing the normal default native build. As of this note, **no default native compilation flags or stored WR files were modified**.

Original iMac outputs for reference: `~/Desktop/stripboard_speedlab_v165_5k/speed_lab_stratified.csv`, `~/Desktop/stripboard_speedlab_v165_50k/speed_lab_stratified.csv`, with their matching full `speed_lab_raw.csv` and `results/.../*.json`. Those files remain on the user's machine; not fabricated or committed here.
