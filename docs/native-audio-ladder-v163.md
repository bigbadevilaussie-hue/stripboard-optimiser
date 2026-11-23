# v1.63 native CLI audio ladder — 5,000–50,000 moves

Purpose: repeat the earlier ten-rung budget ladder on the **AUDIO** master rather than MOTO/MOTOMIX. Native CLI only. No GUI changes and no native solver scoring changes.

## Input and experiment

Source: `test-fixtures/masters/audio/audio.json`, tracked in the repository. At inspection, the source board was **24 rows × 56 columns, locked in both directions**. The script refuses to silently modify these dimensions. For reproducibility it copies exact source bytes into the output's `input/projects/1.json` and records the input SHA256.

**Ten move budgets:** 5k, 10k, 15k, 20k, 25k, 30k, 35k, 40k, 45k, 50k. **Ten seeds:** 1–10 at every rung. **100 independent solves.** Each rung starts a fresh anneal; it does not continue the previous rung, and the temperature/penalty ramp is rescaled. A seed may improve or worsen at higher move counts.

The default flags deliberately match the original controlled ladder's loose physical settings: native decoder and router (`--native 1`), wires-first preference, `drilledCutsOnly` **OFF**, `noWireStacking` **OFF**. Cuts made with a knife and stacked wires are therefore **allowed** for this particular baseline experiment. A `--strict 1` check is always performed on each saved layout.

**Two quality predicates are reported separately:**

- `historicalClean`: Q0, zero **true slanted** wires (`offAxis=0`), no checker issues/conflicts/incomplete nets or geometry faults, and output exactly 24×56. This is comparable in spirit to the older 5k–50k ladder.
- `strictValid`: the newer CLI post-solve gate including zero **column-changing** wires (so horizontal jumpers also fail), zero crossings, electrical/geometry faults, locked parts and board constraints, plus drill/no-stack restrictions if requested. A failure exits 2 and is recorded as a completed but noncompliant solve.

These predicates are **not equivalent**, and a historical-clean result is not claimed to pass the modern strict constraints.

## Mac command (one paste)

```bash
cd ~/Documents/stripboard-optimiser && \
set -o pipefail && \
{
  git pull --ff-only origin main &&
  python3 -m py_compile scripts/ladder_native_audio.py scripts/tests/test_audio_ladder.py &&
  PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_audio_ladder.py' -v &&
  (cd src/frontend && npx tsc -p tests/solver/tsconfig.json) &&
  python3 scripts/ladder_native_audio.py --jobs 4
} 2>&1 | tee ~/Desktop/audio_ladder_v163.log
```

Output is isolated under `/tmp/audio_native_ladder_v163/`:

- `ladder_results.csv`: every seed and budget, quality/geometry/physical counters, both pass flags, timing and SHA1 solved-layout fingerprints.
- `ladder_summary.csv`: strict successes and historical-clean counts per rung, mean wire/cut counts, phase timings, best strict candidate seed and wire/cut counts.
- `runs/moves_05000/seed_01.json` etc.: full solved boards, including failed ones for diagnostics.
- `input/projects/1.json` and `ladder_config.json`: unchanged input bytes and SHA256 metadata.

To avoid overwriting prior evidence, the runner refuses an output directory containing `ladder_results.csv` or a mismatched input/config. Run with `--out /tmp/audio_native_ladder_v163_2` for a second experiment. The native process concurrency is capped at the host's physical core count; default `--jobs 4` is for quality and correctness throughput, **not** sequential speed comparisons. Run `--jobs 1` with a new `--out` for per-solve timing studies.

Optional `--drilled` and `--nostack` flags change the physical test constraints and require a new `--out` directory. They are **not** enabled by default in this comparison.

## Status

**Executed successfully on the iMac, 24 November 2026.** User-provided terminal log reports **4/4 unit tests passed** and **100/100 CLI solves completed** with no process errors. The detailed saved CSVs remain on the iMac and were **not independently re-read** for this documentation update. The solver remains `v1.60-cli-audit`; this test harness is `v1.63-native-audio-ladder`. The GUI stays stale by design.

### Recorded 100-run results

The AUDIO source SHA256 was `5e36871183d6afea9a4291aa43e3cc915afbdcf1ab688ac3beb599a343a1bb06`. Board 24×56 locked; native wires-first; drill OFF and no-stack OFF (knife cuts and stacks permitted). Four processes ran concurrently, so solve timings are affected by resource contention.

| Moves | Strict-clean / 10 | Historical-clean / 10 | Best strict seed | Best valid wires | Best valid cuts |
|---:|---:|---:|---:|---:|---:|
| 5,000 | 1 | 1 | 9 | 18 | 46 |
| 10,000 | 1 | 1 | 9 | 23 | 51 |
| 15,000 | 0 | 0 | — | — | — |
| 20,000 | 1 | 1 | 6 | 13 | 41 |
| 25,000 | 0 | 0 | — | — | — |
| 30,000 | 0 | 0 | — | — | — |
| 35,000 | 1 | 1 | 6 | 14 | 42 |
| 40,000 | 0 | 0 | — | — | — |
| 45,000 | 2 | 2 | 6 | 13 | 41 |
| 50,000 | 0 | 0 | — | — | — |
| **Total** | **6/100** | **6/100** | — | **13** | **41** |

At 45k seed 9 was also strictly clean at **15 wires / 43 cuts**. The best qualifying outputs tie at **13 wires / 41 cuts**, at 20k seed 6 and 45k seed 6. These are *not* drilled-only or no-stacking achievements; both restrictions were disabled during this experiment.

At 50k seed 7 produced **10 wires / 38 cuts**, but strict validation failed (Q0, column-shift 1; stack overlap 1 even though stacking was permitted). **Do not promote this as a valid record.** The exact failure list is in its per-run CSV/JSON, not established by the summarized terminal line.

### Interpretation and next diagnostic

- Clean yield is **6%** across this fixed-seed budget ladder and non-monotone across rungs: the 50k level was **0/10** clean despite the 45k level being **2/10**. Ten correlated seeds per rung do not demonstrate that extra moves generally worsen the solver, nor that the algorithm has reached a performance ceiling.
- Most displayed outputs were Q0 but not strict-compliant. The terminal's ↘ column is the strict **column-change count**, not necessarily a true slant; many nonclean outcomes show column shifts despite Q0. Aggregate per-criterion failure counts should come from `ladder_results.csv` before deciding whether search objective, placement or final routing is the dominant failure.
- Timings came from `--jobs 4` and **must not** be used to claim a per-solve speed gain or regression compared with sequential MOTO tests.
- Older MOTO benchmarks used a wrongly sized C1; this **AUDIO** input has its own SHA256 and should be compared only with AUDIO runs on the same master and settings.

**No solver code, scoring rules or native RNG behaviour were changed to produce these results.**
