# MOTOEX native exhaustive USB Slide sweep — 200 seeds × up to 51 positions × 25k moves

**Status:** implemented on feature branch \`main\`. Code and pure controller tests committed, **not yet executed on user's iMac**. This is a separate experiment from the completed **fixed USB col47** 200×25k sweep (0 strict passes).

## Exact contract

For **each seed independently**, try every one of the **51 USB bottom-edge columns** in nearest-to-original order, starting at **47**, then **46, 48, 45, 49, 44, 50, 43, ...**, until either:
- **Strict PASS:** save that solved JSON and stop trying further columns **for that seed only**. Other seeds continue; no global early exit.
- **All 51 fail:** record failure with all individual candidate JSONs and diagnostics, then continue with the next seed.

The sweep runs exactly **200 seeds** (\`1..200\`). One trial consists of **25,000 annealing moves at one USB position**. Maximum **10,200 native solves / 255 million annealing moves** if no seed ever qualifies; actual attempts may be much lower due to per-seed early stopping. **Four workers**, each processing its own seed's columns sequentially; \`--workers 3\` is also supported. Every process and saved-input file has a unique seed + column directory, so inputs never race.

The same rules from the user's immediately preceding fixed sweep apply:
- **Drilled-only OFF** (\`--drilled 0\`): knife cuts are legal.
- **Stacking allowed** (\`--nostack 0\`): overlapping wires legal.
- **Generic drilled rotation-domain OFF** (not relevant without drilled-only).
- **Optional wire-column polisher ON** (\`--wire-polish yes\`) by default.
- **Strictly enforced:** 24×56 locked purchased board; only USB body 2-row explicit overhang; USB pins/copper/cuts/wire endpoints on-board; valid parts/locks, no electrical shorts or missing connections, no nonvertical jumpers, no crossings through component bodies. No GPS/net/USB name special-casing in the solver.
- USB row **13**, rotation **0**, USB fixed to the tested column **within each native solve**. Every trial uses a fresh copied fixture; canonical master remains unmodified.

## Run once, one copy-paste

\`\`\`bash
cd ~/Documents/stripboard-optimiser && \
git pull --ff-only && \
PYTHONPATH=scripts python3 -m unittest discover \
  -s scripts/tests -p 'test_motoex_native_full_slide_sweep.py' -v && \
cd src/frontend && \
npx tsc -p tests/solver/tsconfig.json && \
npm run build:native && \
npm run build:native:edge && \
cd ../.. && \
python3 scripts/run_motoex_native_full_slide_sweep.py \
  --seeds 200 --moves 25000 --workers 4 \
  --wire-polish yes \
  --out ~/Desktop/motoex_native_full_slide_200x25k_v1
\`\`\`

The test runs without annealing; new runtime code is still pending iMac verification.

## Crash recovery / resume

The controller writes **one durable \`results.jsonl\` record immediately after every attempted USB column**, with per-attempt stdout/stderr, detailed time and success status. It verifies source and compiled binary SHA256s before resuming. If interrupted, run the **same** invocation with \`--resume\`; do not rebuild or alter the native code between runs. Resume skips all completed columns and finished seeds, then continues each seed at its next legal column. The command accepts **only 3 or 4 workers**.

Run settings recorded in \`manifest.json\`; all results in a new output directory unrelated to \`motoex_native_fixed_200x25k_v1\`.

## Preserved archive

\`\`\`text
~/Desktop/motoex_native_full_slide_200x25k_v1/
  manifest.json                 git revision, SHA256 of original master and native binaries, flags, threads
  progress.log                  per-position and per-seed emoji progress
  results.jsonl                 crash-resumable full per-position checkpoint
  results.json                  per-position diagnostic records and per-seed outcomes
  results.csv                   sortable per-position timings and strict failure codes
  summary.json                  top5, all strict winners, timing distribution, per-column stats
  solved_index.jsonl            ranked metadata for all strict winners
  report.md                     human-readable strict top five, failure histogram
  solved/                       every independently verified strict winner JSON
  rejected/                     every failed/invalid candidate JSON for post-analysis
  top5/                         five best distinct strictly valid layouts (copies)
  jobs/
    seed_0001_col_47/
      input/projects/1.json
      stdout.log
      stderr.log
      [candidate.json moved to solved/ or rejected/]
    seed_0001_col_46/
    ...
\`\`\`

Ranks **only strictly solved** layouts by **fewest wires, then cuts, wire length, weighted price**. The full physical signature includes placements/rotations, copper cuts and wire positions, so distinct alternative physical layouts remain distinct. **Every strict solved JSON is kept even if two results are duplicates**; only the copied top five are deduplicated. A seed stops at its first independent strict pass, so at most one solved layout per seed.

Times include process elapsed wall time, internal solve/CPU/memory timing, first in-cap move and per-seed total attempted CPU across visited columns. Failure diagnostics include incomplete nets, wire violations, crossing components, stack partners, knife blockers, solver issues, move acceptance summary and finisher tracing. Every rejected result is available for targeted polish or placement repairs.

No promises about strict pass count or run duration can be made before the actual Mac run. If none passes, \`top5/\` stays empty; the invalid candidates are never mislabelled as solved.

**Other reference:** [Fixed USB 200×25k run](native-fixed-usb-200x25k-sweep.md); [full new-chat handover](START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md).
