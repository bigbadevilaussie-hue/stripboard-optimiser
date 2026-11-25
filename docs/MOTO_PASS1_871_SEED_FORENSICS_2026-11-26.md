# Moto Pass One — 871-seed live regression and failure forensics

26 November 2026. Cross-chat engineering handoff requested by owner. Observational research only; no change to solver, GUI, scoring, strict rules or campaign policy authorised here.

## Provenance and run conditions

Owner supplied a partial StripSolve GUI 2.38 activity log, source revision 56fc268507e8. SHA256 of supplied Markdown attachment: 05266ad6a47b686c0929e61de8b417d20bcb7ac50ada2e861b4d4899f07dda4a. Original log not copied into repository (contains local paths). Parsed every PASS/FAIL/ERROR result independently using Python; unique seeds 1–871, no missing/duplicate IDs. Compared with the saved WR_Moto/20k archive at a84e9d11c54f3210076eae0b538006803639951a using Git tree filenames. This is not a new native solve or electrical audit.

Input moto.json, 24x56 locked dimensions, 44 components (32 on-board, 12 excluded/off-board), 35 nets, 123 assignments, zero initial positioned components/anchors, no initial cuts/wires. Knife allowed, drilled-only false, stacking allowed. Campaign input SHA256 eaf4795307296d2cc1178f69da8d4aed26cec1fcc79ffa9f86e21c489dc16983. 2,000 seeds x 20,000 moves scheduled (40 million move budget, not proof of actual evaluated moves). Preflight electrical sanity PASS; physical fit not verified by preflight. 44 package assumptions, no unknown bodies. GUI 2.38 uses older 100-decode timing preflight: 0.395962 ms/decode, 2,525.50 decodes/s, 0 solve attempts. This is not optimiser throughput. GUI 2.39 main already replaces this preflight with JSON complexity sniff; do not treat older log as current GUI implementation.

## Results

871 completed (43.55%), 16 PASS (1.837%), 855 FAIL, zero logged ERROR. Historical 20k 37/2000 (1.85%). All 16 current passing IDs exactly match the 16 archived passing IDs within 1–871; no extras or missing IDs. Strong qualification regression evidence, not proof of byte-identical layouts or independent verification of every historical failure. Archive is passes-only.

| Seed | W | C | S | Q3 | Seconds |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0025 | 39 | 55 | 2 | 76.44 | 1.919 |
| 0079 | 42 | 58 | 2 | 74.69 | 1.695 |
| 0160 | 42 | 58 | 2 | 75.30 | 1.832 |
| 0182 | 38 | 54 | 2 | 77.47 | 1.731 |
| 0199 | 48 | 64 | 3 | 70.04 | 3.025 |
| 0213 | 46 | 62 | 2 | 73.50 | 2.764 |
| 0305 | 36 | 52 | 2 | 77.58 | 1.552 |
| 0385 | 47 | 63 | 3 | 71.80 | 2.246 |
| 0428 | 38 | 54 | 2 | 76.98 | 1.747 |
| 0451 | 40 | 56 | 3 | 75.43 | 1.952 |
| 0471 | 40 | 56 | 2 | 76.73 | 1.612 |
| 0567 | 46 | 62 | 2 | 72.73 | 1.595 |
| 0588 | 49 | 65 | 2 | 72.06 | 1.603 |
| 0642 | 50 | 66 | 3 | 70.25 | 2.121 |
| 0697 | 34 | 51 | 1 | 80.06 | 1.962 |
| 0820 | 38 | 54 | 2 | 76.88 | 1.845 |

Champion sequence 0025 -> 0182 -> 0305 -> 0697. S1 = no positive-length vertical stacking. Manual Moto reference 14W/30C/S2/215.90mm Q3 89.71 (owner reference, not reaudited). Historical later 20k examples 0986 = 26W/42C/S4/Q3 80.07; 1443 = 31W/47C/S1/Q3 81.69. Historical overall Moto champion 25k/0937 = 28W/44C/S2/Q3 83.00. See QUALITY_Q3_2026-11-25.md; historical examples are not current run results or guaranteed future outcomes.

## Failure forensics

Counts of rejected records containing each flag family (overlapping; denominator 855):

| Flag | Count |
| --- | ---: |
| SOLVER_ISSUES | 812 |
| NONVERTICAL | 793 |
| CROSSINGS | 779 |
| SLANTED | 763 |
| INCOMPLETE | 508 |
| QUALITY | 508 |
| GEOMETRY | 6 |
| LOCKED_ROWS | 6 |

QUALITY is the native rejection flag, not Q3 construction score. Do not conflate them. INCOMPLETE suffix distribution: 1=32, 3=418, 4=31, 5=18, 7=1, 14=5, 15=3. Exactly three accounts for 82.28% of incomplete-flag records. Investigate which nets/segments are involved and what the suffix counts actually represent in the native/auditor contract; log alone cannot establish that the same three nets are involved.

347 FAILs have no INCOMPLETE flag (not proof of electrically valid connectivity). 43 have only QUALITY/INCOMPLETE flags. 59 have NONVERTICAL_1 and no INCOMPLETE flag (may have other violations). Seeds 0202 and 0299 have precisely CROSSINGS_1,SOLVER_ISSUES. They are promising forensic near-miss examples, not accepted boards. Exact seed runtimes 2.600s and 1.678s.

## Timing

Per-result logged elapsed seconds, not aggregate campaign wall/CPU time: minimum 1.331, median 1.814, mean 1.898964, maximum 5.524, p95 2.6394 (Python statistics.quantiles inclusive of all results using default exclusive quantile method). PASS mean 1.950063, FAIL mean 1.898008. No clear useful pass predictor from elapsed time alone; do not infer causation or hardware throttling without further data.

## Research opportunities (not approval to implement)

1. Preserve current strict solver, independent qualification, hard constraints and working GUI. Do not change the proven solver just because these statistics are interesting.
2. Examine exact rejection reasons and native/auditor semantics for a small controlled set. For recurring INCOMPLETE_3, inspect failing net/segment identity and common placement geometry before hypothesising a bug.
3. Isolated forensic replay of 0202/0299 under identical input/flags could reveal whether a single crossing is locally repairable. Preserve rejected candidate JSON and detailed reasons in a separate experimental directory if the owner approves; keep rejected data out of qualified archives. Existing summary logs alone cannot recover candidate geometry.
4. Pass Two can be genuine optimisation of qualified layouts once a safe warm-start/refinement mechanism exists. A higher-budget same-seed rerun is a new search, not refinement of saved board. Separate near-miss repair research from qualified Pass Two, and independently strictly verify every resulting candidate. No relaxation of electrical/physical constraints.
5. Do not restart the running campaign or invoke the historical destructive passes-only runner. No modifications to Work folders or archive. Current Pass Two remains import-only. No new search or solver change in this handoff.

The purpose is to reduce actual construction effort (wires, cuts, wire length and stacking), not maximise an arbitrary score at the expense of correct boards. Owner's handmade 14W/30C Moto is the practical benchmark.
