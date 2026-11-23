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

**Code committed but not yet run on the iMac.** The output statistics, success rates and best audio layout are not known until the command above completes. Results should be reported from the resulting CSV, not inferred from earlier MOTO benchmarks. The solver remains `v1.60-cli-audit`; this native test harness is `v1.63-native-audio-ladder`. The GUI stays stale by design.
