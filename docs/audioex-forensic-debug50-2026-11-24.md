# AUDIOEX 50-seed forensic rerun — 24 Nov 2026

Investigate native finish and strict-audit mismatches on the SAME 50 seeds as the random 50-seed run. No solver, fixture or qualification-rule changes.

## Mac commands (from repository root)

    cd ~/Documents/stripboard-optimiser
    git pull --ff-only
    cd src/frontend
    npm run build:solver
    npm run build:native
    npm run build:native:edge
    cd ../..
    python3 -m unittest scripts.tests.test_audioex_debug50 -v
    python3 scripts/run_audioex_debug50.py --jobs 4

## Configuration

AUDIOEX 24x56 locked; BMS row -2, col 24, locked Edge, Slide disabled.
Native and strict enabled; drilled-only OFF (knife cuts allowed); stacking ON.
50k moves, 50 exact seeds from the prior campaign, four workers.
Wire polishing OFF; finish-trace and move-summary ON for diagnostics.

## Fresh output

~/Desktop/audioex_debug50_git/

- debug_results.csv: one row per trial; nested net, wire and rotation data serialized as JSON
- debug_results.jsonl: one flat diagnostic record per seed
- CLAUDE_HANDOFF.md: strict failure counts and high-cut seed evidence
- jobs/seed_XXXX/diagnostic.json: full CLI result and every finish trace
- jobs/seed_XXXX/stdout.log and stderr.log, plus independent audit logs
- passed/ and rejected/: saved layouts named seed_XXXX_Wn_Cn.json
- manifest.json and selected_seeds.txt: settings, exact seeds and source/binary hashes

To resume with unchanged binaries and fixture:

    cd ~/Documents/stripboard-optimiser
    python3 scripts/run_audioex_debug50.py --jobs 4 --resume

For a different new run, provide a fresh --out folder.

## Verification boundary

A strict PASS requires CLI acceptance, separate saved-board audit and unchanged BMS/board locks. The saved-board audit shares some electrical and geometry helpers with the CLI; it is NOT a disjoint copper-graph oracle. The CSV explicitly labels independentCopperOracle=NOT_IMPLEMENTED and rotationDomainCheck=NOT_INDEPENDENTLY_CHECKED. Do not treat those as independent certifications. Diagnostic flags may alter timing; compare the actual saved layouts with previous archived outputs.

The companion scripts/run_audioex_random50.py reproduces the original search without extra trace flags.
