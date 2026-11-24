# MOTOEX winner ladder — seed 37, USB column 23

**Current branch:** main. **Baseline:** saved 44 wires / 60 cuts at USB row 13, col 23. The original JSON must remain unchanged.

## Run after stopping the old sweep

From repository root, after \`git pull --ff-only\`:

\`\`\`bash
cd src/frontend
npx tsc -p tests/solver/tsconfig.json
npm run build:native:edge
node tests/solver/testPackageBodyBoardBounds.js
node tests/solver/testNativeBodyBoardBounds.js
cd ../..
PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_motoex_winner_ladder.py' -v
python3 scripts/run_motoex_winner_ladder.py
\`\`\`

Requires the existing native route library and Node addon, the canonical
\`test-fixtures/masters/moto/motoex.json\` and
\`~/Desktop/MOTOEX_STRICT_44W_60C.json\` (the preserved winner).

The runner makes **43 independent native solves** with 5k, 10k, 15k, ... 200k,
300k, 400k and 500k C moves: **5.3 million requested anneal moves** in all.
Every rung starts with **the canonical master and seed 37**; USB stays at
row 13, column 23, Edge+Slide flags preserved. It does **not** warm-start from
the solved JSON because native genome/placement warm-start is not implemented.
The saved JSON is the ranking baseline, not a mutable input to the annealer.

Settings: 24×56 fixed physical board, knives permitted, stacking permitted,
drill rotation-domain off, wire polish on, rank by **wires → cuts → wire length →
price**. Electrical opens/shorts, geometry clashes, nonvertical wires, wire
crossings over other component bodies, out-of-board pins/copper and lock drift
remain **fatal**. **Package body overhang alone is a nonfatal build warning**;
the native solver still models the full-size body, treats it as an obstacle,
and soft-penalizes overhang. Q1 and C6's observed overhangs do not change C6's
470 µF value or the modelled 10 mm body.

## Results and recovery

Results are written to \`~/Desktop/motoex_seed37_col23_ladder/\`:

- \`original_winner_44W_60C.json\` — unchanged baseline copy
- \`manifest.json\` — exact source/binary hashes, settings and complete ladder
- \`results.jsonl\` — fsynced checkpoint after each budget
- \`summary.json\`, \`results.csv\`, \`progress.log\` — all attempts and ranking
- \`runs/moves_005000/\`, \`runs/moves_010000/\`, etc — input, saved solved/rejected JSON, stdout/stderr
- \`top5/\` — best five **distinct** qualified candidate layouts including baseline
- \`champion.json\` — current best valid/warning-tolerant candidate, maintained after every rung

Interrupted runs resume with:

\`\`\`bash
python3 scripts/run_motoex_winner_ladder.py --resume
\`\`\`

It refuses changed source/binaries/settings or missing archives rather than
mixing incompatible results. The baseline is never overwritten. Only candidates
with an independent strict electrical/routing/geometry pass can beat it.

For a tiny smoke test in a **different output folder**:

\`\`\`bash
python3 scripts/run_motoex_winner_ladder.py --moves 5000 --out ~/Desktop/motoex_ladder_smoke
\`\`\`
