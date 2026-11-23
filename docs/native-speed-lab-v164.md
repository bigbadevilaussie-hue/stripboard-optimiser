# Native v5 speed optimisation laboratory — v1.64

**Date:** 24 November 2026  
**Status:** instrumentation and **disabled** speed experiments committed. **No measured post-change speedup and no approved change to production defaults.**  
**Target:** preserve the heavily modified Karl solver's MOTO/AUDIO WR-capable behaviour; increase exact same-output layouts per CPU-second. GUI integration remains deferred.

## Evidence before changing the engine

The saved iMac measurements and existing source establish:

| Finding | Evidence / magnitude | Engineering consequence |
|---|---|---|
| Native decoder already beats WASM | `nativeInstance.js` cites about **1.6× faster** annealing on boards measured on 26 Sep 2026; native walks were identical there | Keep native CLI for timing. WASM compatibility is a separate gate |
| Annealing dominates | Native full 80-case profiling: approximately **1,179 ms anneal / 1,391 ms solve = 84.8%** of average solve time | Prioritise decoder, mutation, rejection and build flags |
| Expensive rejected proposals | **1,072,704/1,600,000 = 67.0%** proposals rejected after decode | Potential major opportunity **only with a sound conservative energy bound**; unsafe to skip without one |
| Same-board proposals | **446,966/1,600,000 = 27.9%** marked same-board | Decoder **already** returns early after integer placement equality but before occupancy/route/clearance; cannot simply discard differing genomes as their future transitions differ |
| Mutation failures | 2,942/1,600,000 (~0.18%) mutation failures; **zero failed decodes** in the selected 80 runs | Optimising this branch alone cannot yield a large improvement |
| Router outliers | `repairSlantWires` ~98.6 ms mean and **1,307.3 ms max** under contended four-worker profiler; initial route ~20.1 ms mean | Investigate separately; avoid truncating valid candidate repair for speed |
| Scratch grid reallocation | Decoder's `ensureGrid()` grows capacity only as needed and reuses arrays | This obvious optimisation was **already implemented** |
| Measurement levels | 20k AUDIO and MOTO each use locked 24×56 input; source complexity differs | Keep fixture/policy/seed/budget the same for binary speed A/B |

**Nothing above shows that the new experiments are faster.** Results are earlier baseline observations, or source-derived opportunities.

## Tested-by-design pipeline

1. Keep normal `decode.c`, `route.c`, TypeScript, CLI and GUI behaviour as the **reference**. Two C optimisations are added behind disabled `#ifdef` switches only. Do not enable them in `npm run build:native` or in the committed WASM.
2. Build native decoder or router variants into **new output directories**, with the **original other library unchanged**. The Node native loader accepts optional `V5_NATIVE_LIB_DIR` and `V5_NATIVE_ROUTE_LIB_DIR` solely for this lab. Unset both for existing solver behaviour.
3. For a fixed board, seed, move count and policy, run fresh serial `-O3` baseline; confirm it agrees with the existing native build. Run candidate flags; run `-O3` again to bracket CPU-clock/thermal drift.
4. Require **identical exit code, complete non-timing CLI result, strict failure reasons, layout fingerprint and SHA256 of entire saved JSON**. One difference immediately **disqualifies** that binary. The test does not lower the quality/validity threshold to claim speed.
5. Compare per-seed `solveMs`, `annealMs`, `routeMs`, `totalMs`. A printed +10% speedup means baseline seconds / variant seconds − 1 = 10%, **not** 10% fewer milliseconds; always label the metric.
6. Rank surviving variants by median **paired** speed, separated by AUDIO/MOTO and policy. Retest positive candidates on more seeds, different budgets, cold/warm runs and representative boards before production integration. One pair of clocks is not proof.

### Experimental variants

| Variant | Change | Risk / rationale |
|---|---|---|
| `o3` | Ordinary native `clang -O3` | Baseline |
| `o2` | Smaller code emphasis | Potential instruction-cache effect; may slow arithmetic |
| `fp_off` | `-ffp-contract=off` | Stronger floating reproducibility; may affect results or speed |
| `cpu` | Host-targeted `-march=native` (x86) or `-mcpu=native` (ARM) | Host-specific vector/instruction throughput; FP and portability need checking |
| `no_errno` | `-fno-math-errno` | Potential more efficient libm use; semantics gated |
| `unroll` | `-funroll-loops` | Potential loop win or instruction-cache penalty |
| `grid` | `V5_EXPERIMENT_FAST_GRID_CLEAR` | Bulk clear of used grid prefix via `__builtin_memset` for `occ=0`, `owner=-1`, `pinNetAt=-1`; **native decoder only** |
| `identical` | `V5_EXPERIMENT_FAST_IDENTICAL_GENOME` | Exact all-array genome equality guard before invoking decoder; mutate and acceptance path still run; **native decoder only** |
| `both` | Grid + identical shortcut together | Interaction effects |
| `cpu_both` | Host ISA + both guarded shortcuts | Potential maximum speed; highest reproducibility concern |
| `lto` | Link-time optimisation (if compiler/linker supports it) | Cross-function/native codegen changes |

**No `-ffast-math`, unsafe reciprocal, reassociation or altered anneal schedule** in this laboratory: those risk changing WR outcomes. A compiler variant with any output mismatch is not approved.

### Run on the iMac (one paste)

The native addon and normal build already exist in the previously run CLI work. Only new *experimental* libraries are built under Desktop output directories; **the script does not overwrite the default native libraries or committed WASM**.

```bash
cd ~/Documents/stripboard-optimiser && \
set -o pipefail && \
{
  git pull --ff-only origin main &&
  python3 -m py_compile scripts/speed_lab_native.py scripts/tests/test_speed_lab_native.py &&
  PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_speed_lab_native.py' -v &&
  (cd src/frontend && npx tsc -p tests/solver/tsconfig.json) &&
  python3 scripts/speed_lab_native.py --target decoder --seeds 3 --repeats 2 \
    --out ~/Desktop/stripboard_speedlab_v164_decoder &&
  python3 scripts/speed_lab_native.py --target router --seeds 3 --repeats 2 \
    --out ~/Desktop/stripboard_speedlab_v164_router
} 2>&1 | tee ~/Desktop/stripboard_speedlab_v164.log
```

Defaults: **AUDIO + corrected MOTO**, **three fixed seeds**, **two serial repeats**, **20,000 moves**, **loose and drilled/no-stack** policies, 11 decoder variants and 7 router variants. The full solved project JSON for every run is preserved. The candidate program never launches 4 jobs concurrently for timings.

If the original native build does not match the new `-O3` reference, stop: there may be a stale native binary, different compiler or unexpected source configuration. Do not call a speed win. Refresh the default native build separately only after establishing provenance, then use **new output directories** to rerun.

Each output directory contains:

- `speed_lab_config.json`: source SHA256, fixture SHA256, original binary SHA256, compiler version, host architecture and all flags
- `builds/<variant>/compile.txt` and candidate `.so`: exact compiler invocation and compiled binaries
- `results/<fixture>/<policy>/seed_*/rep_*/*.json`: complete solved boards, source-parity baseline plus candidates
- `speed_lab_raw.csv`: full paired runtime, binary status and exact-output comparison reason
- `speed_lab_summary.csv`: median solve and anneal speed by variant; **REJECTED_DIFFERENT_OUTPUT** if any mismatch

**Do not overwrite the historical WRs, 80-case baseline, 36-run budget sweep or AUDIO ladder.** Lab output is entirely separate.

## Remaining performance work — ranked by expected impact, not proven gain

1. **Decoder candidate rejection before full evaluation:** the big target given 67% rejected proposals. Requires provable lower bound for *all* energy terms under the current cooling/penalty schedule. Must preserve RNG and each accepted genome; unchanged outputs on only ten seeds are not sufficient proof.
2. **Expensive decoder stages:** measure per-phase CPU time in weighted sequence-pair y/x constraints, tied groups, occupied-hole rasterisation, island/cut/wire assessment and exact body/lead clearance, using C-level counters compiled only for diagnostic builds. Sampling/clock probes must be shown not to perturb annealing order. Avoid optimising the wrong stage based only on code appearance.
3. **Grid clearing and same-genome shortcuts:** implemented as off-by-default `#ifdef` variants. If either measures slower or changes a saved JSON, reject. The 27.9% same-*board* statistic does not establish a high identical-*genome* rate.
4. **Compiler architecture and optimisation differences:** test `-O2`, `-O3`, host CPU codegen, strict FP, loop unrolling and LTO for both decoder and router using the exact gate.
5. **Native router slow tail:** isolate `repairSlantWires`, obstruction checks, candidate rescoring and memoisation from `route.c` and `layout2/finish.ts`. Avoid arbitrary work caps that lose WR-quality candidates.
6. **Finisher duplication:** exact-finishing multiple candidates and router/repair both have costs; cache only proven identical finaliser inputs with source SHA and complete mode/constraint key, and verify no skipped candidate could win.
7. **CLI process startup:** each seed currently launches a fresh Node process. Measure `startupMs` and `inputMs`; a persistent worker may improve short 5k budgets but must isolate C global state/seed RNG, prevent cross-run leakage and preserve full parity.
8. **Serialization and result I/O:** avoid writing intermediate JSON or full move logs during production tournaments; keep per-seed `--save` and sidecar/strict reports for qualifying candidates and failures that need audit. For golden comparisons retain full saved outputs.
9. **CPU parallelism:** tune number of independent native processes only **after** per-solve serial speed testing; 4× concurrency is throughput, not a 4× per-seed speedup. Memory/cache pressure can make individual solves slower.
10. **Pass 1 budget selection:** use Route-Mate collector/presolve as **read-only** complexity predictors; train against measured strict survivors and Pass 2 uplift. This changes compute allocation, not solver speed; isolate from compiler/decoder A/B results.
11. **Deterministic scheduling:** different budgets rescale temperature/cut ramps; 50k is not continuation of 20k. Test both speed at equal moves and **useful survivor throughput** at optimised budgets; do not conflate these.
12. **WASM/native parity:** any eventual production speed patch must pass saved-output comparisons on the CLI's native build and tests/solver suite; if browser/WASM should share the change, build WASM separately with explicit golden gates, not automatically.

## Promotion rule

**Promote nothing on this commit.** Only a binary that (a) matches original saved JSON byte-for-byte and all strict criteria on a representative frozen suite, (b) demonstrates repeatable serial wall/anneal speed improvement beyond clock drift, and (c) does not jeopardise MOTO/AUDIO WR reproduction is eligible for an explicitly separate production change.

See [existing v1.60 profiling and failure matrix](cli-audit-2026-11-23.md), [AUDIO ladder](native-audio-ladder-v163.md), [MOTO C1 provenance](moto-c1-correction-v162.md), and [Route-Mate integration roadmap](route-mate-native-solver-integration-roadmap.md).
