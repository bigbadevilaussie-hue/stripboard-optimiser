# StripSolve — AI Handover

**27 November — MOTOEX Edge baseline completed: 8/100 strict at 100k, seed97 Q81.92. MOTO Q86.80 independently reproduced by Claude; final raw archive/full replay pending. See [Dave's evidence and verification checkpoint](docs/DAVE_MOTOEX_EDGE_2026-11-27.md). No production changes.**


## CURRENT CHECKPOINT — 2026-11-27 (read this first)

This section supersedes earlier dated handoffs. Historical results are evidence, not instructions to rerun campaigns. Read this file, [project.md](project.md), the current [forensic checkpoint](docs/KARL_FORENSICS_2026-11-27.md) and relevant source before making changes. Check actual main HEAD and local status before proposing commands. Owner now calls the solver Dave (historical Karl names retained); the current project is StripSolve, separate from Moto-Mate firmware and OSA. Brother's Moto-Mate aihandover.md supplied the organisational model only (source checkpoint 90940f6); do not import its device-specific rules or change other products.

## CURRENT OWNER DIRECTION — ONE ACTIVE SOLVER: DAVE

Owner explicitly instructs "lock in the new one ... i doint want more than one solver." Canonical native build now includes the tested Edge/Fast flags and GPS/MPU rotation restrictions directly in decode.c, not a generated alternate. TS validates exact MOTOEX component IDs, definition IDs, footprint offsets, pin IDs, and assigned net names; applies the pair only to both unlocked matched rigid components on ordinary horizontal stripboard with knives permitted. Other projects and explicit locks retain their original domain; drill-only mode uses its existing generic constraint. C initialization, mutation rejection and direct decode enforce GPS90/270 MPU0/180. Native addon exposes setter and native loader rejects stale addon/decoder and alternate paths; Edge/Fast build commands are aliases of canonical build and generated aliases are symlinks to same library. GUI calibration/Pass1 always canonical; manifest records decoder hash for every project, so older campaigns cannot resume mixed trajectories. GUI version2.40. MOTOEX sweep always pair policy, default10k, historical --orientation-pair is compatibility no-op, old generated builder retired. Research archives and original evidence retained, standalone failed repair methods not promoted. Strict acceptance, dimensions, cuts, stacking, Q3 unchanged. New native regression plus amended Python tests added but native/TS/Python suites not run in this environment; owner must rebuild and test on Mac. Tracked WASM binary not rebuilt here; build:wasm uses same canonical source/flags, explicit pair fails closed if stale WASM used. Native GUI path is sole supported current solver. No new seed campaign authorized or launched. 69/100 electrical completeness is evidence from original isolated pair, not proof of strict yield or parity for this integration; 0/100 strict remains baseline. No further surgery.

## CURRENT OWNER DIRECTION — 10k candidate yield only

Owner: "I want the most candidates at 10k thats it no more". Supersedes the previous exploratory routing and 2k-target research agenda for this task. Objective is distinct strict-valid MOTOEX candidates per equal seed cohort at exactly 10,000 annealing moves per seed. Count strict-valid saved/audited boards and distinct layouts, not merely electrical completeness, raw Q3 or near misses. Maintain locked 24x56, electrical, vertical and geometry rules and identical baseline routing/USB settings. Q3 ranks valid candidates, not the primary experiment success criterion. No higher move budgets, no more individual rejected-board surgery, no follow-up cut search on the two capped variants. No new solver experiment or implementation until a reviewed architecture proposal and finite test plan are approved; avoid endless sequential patches. Previous 100-seed baseline and GPS/MPU restricted runs both yielded 0 strict, electrical completeness 22/100→69/100. Keep that distinction.

Final single-cut investigation: owner Mac 35 synthetic checks passed; archive 2a103b7641d4f258510d9c6328720ce503f6bbac, research/dave-fixed-route/20261128-cut-slide-all/report.json. All1321 eligible single same-row pin-partition-preserving variants scanned, zero routed/strict witnesses, 1319 graph-infeasible and two capped. Seed26: 730/732 graph-infeasible, two capped (zero-based cut index58 row4 col39→33 or32; best conflict pairs1),471572 search states. Seed94:589/589 graph-infeasible,10043 states. These conclusions apply only to the tested fixed-placement single-cut model. Close this research line; do not launch more variants. Archive retained as evidence, no production or GUI changes.

### Owner's non-negotiable rules

- **MAIN ONLY.** No new branches or pull requests. No upstream reports, issues, comments or code submissions to Karl. Work within the owner's fork; research belongs in separate directories, not branches. Never force-push or discard local work.
- **Revision control and documentation are part of every change.** Update this current checkpoint, CHANGELOG.md and affected current docs together with approved implementation/research changes. GUI/renderer/import changes bump gui/VERSION in the same commit; repository milestone VERSION and package version are separate. Do not increment a version just to imply progress. Report commit SHA, files, actual changes and validation status.
- **Quality and physical validity first.** A locked 24×56 board means exactly 24×56. No widening the board or silently weakening strict rules to get a PASS. Preserve component locks, original netlist/definitions, legal geometry and electrical completeness. Human-buildable vertical wires; stacking and cut modes follow selected settings. Drilled cuts preferred by owner for human construction; specific research runs may explicitly allow knives. Q3 is construction quality, not electrical validity or percentage of optimum.
- Prefer small reproducible counterexamples, deterministic replay, one-worker forensic tests, fewer moves and smaller boards over indiscriminate brute force. Target useful 2k-move layouts; Q86 at 2k remains a research goal; Q86.80 at 460k plus zero-anneal iterative polish is now owner-reported. No new wagers.
- Owner prefers concise, paste-ready Mac Terminal commands starting with cd, actual Git commits, no repeated questions, clean Qt6 Arctic Ice + Colourburst UI, and useful emoji terminal feedback. Do not claim background work, completed runtime tests, or local filesystem access without evidence.
- Preserve existing local files and experiment results. No destructive reruns or blanket git add/reset/clean/stash. No automatic launch of a new campaign; verify scope and provenance. Do not change Moto-Mate, Fan-Mate or OSA.

## 27 November — MOTOEX fixed USB edge test with cooldown

Owner calls the solver Dave now (historical Karl filenames retained). MOTOEX source test-fixtures/masters/moto/motoex.json: 45 components, 123 assignments, 10 off-board. Existing prepare_trial clears all non-USB locks/placements (including TVS), fixes 24×56 both locks, preserves USB row13 col47 rotation0 locked=true edge=true slide=false; two body rows overhang, both pins on-board. No master edit. Use native Edge build, not the separate Arm C orientation binary; knives and stacks allowed, drill-domain off, strict checks mandatory, historical wire-first ranking unchanged.

Approved test scope: 100 seeds × 2k, three workers, 30 seconds after each fully completed batch of 10 new seeds, no final cooldown. New optional --cooldown-every/--cooldown-seconds flags in scripts/run_motoex_native_sweep.py; defaults zero preserve existing behavior. Only submit current batch, drain all futures and checkpoint all results before sleeping. Resume batches count new pending seeds in that invocation. Record cooldown configuration in manifest and summary, reject changed resume cooldown settings; legacy manifests default zero. Added mocked scheduling tests. Mac 8/8 tests passed and 2k/10k/50k/100k ladder completed (see latest checkpoint); no production solver/GUI changes. Bum Mode not implemented, remains off.

### Latest completed MOTOEX and Claude checkpoint

Read [full evidence and exact fingerprints](docs/DAVE_MOTOEX_EDGE_2026-11-27.md). Same 100 sequential seeds, fixed USB row13 col47 Edge ON Slide OFF, locked 24×56, knives/stacks allowed, drill-domain OFF, three workers, nine 30s idle pauses. 2k/10k/50k 0/100 each; 100k 8/100 strict (10,16,51,60,66,71,79,97), 60 electrically complete, all 100 reported geometry=0, wall565.42s including270s cooldown. Owner Mac eight unit tests passed. winner2.zip directly inspected: all eight raw hashes and dimension/lock/net/endpoint invariants match; Q3 recalculated, seed97 29W45C, 6 knives, S2,439.42mm Q81.92, theoretical S1 ceiling82.32. Seed60 C1 body-overhang warning requires fit review. No full independent electrical/body replay yet. 37 exactly-three incomplete: 32 GPS GND/net25/net29, five MPU GND/net10/net11; diagnosis not causal proof. Candidate offenders 18,21,26,62 need rejected JSONs. Proposed next paired Edge+orientation-domain test, not launched. MOTO Q86.80 separate: Claude independently reproduced three states and all64 report-state Q values, 11 improvements, W/C/L fixed. Final JSON named original_1216_460000.json is polished, not original; rename on archival, record full representation-specific hashes. Final raw artifacts and independent repo-based replay pending. No new campaign or solver edits.

## 27 November — systematic high-ID seed sampling (requested, not yet run)

Owner requests 100 evenly spaced IDs over conservative exact JavaScript seed-initialisation range, 10k moves per seed, 15s smoko. Keep three workers; use batches of ten (assumed cadence from earlier 100-seed tests), nine pauses. autoLayout5.ts multiplies (seed+1) by 0x9e3779b9 and 0x85ebca6b before >>>0; floor((2^53−1)/0x9e3779b9)−1 = 3,393,262 guarantees exact integer products, not a proof of a hard solver limit or unique layouts. Step=floor(3393262/100)=33932; seeds i*33932 for i=1..100, last3393200. Systematic ID sampling is not random or uniformly covering RNG states; even stride shares low bits. Optional --seed-stride default1, manifest and summary preserve stride, resume validates it (legacy default1) and rejects off-schedule checkpoint records. Runner now refuses IDs beyond conservative bound; native solver unchanged. Same 24×56 USB Edge fixed col47, strict knives/stacks allowed, drill-domain off. Added schedule/bound test; Mac execution pending. No GUI version bump.

## 27 November — completed 10k breadth tests and local forensic sniff

Owner final terminal results: sequential 1,000 × 10k, 0 strict, 510.64s, ~/DAVE_EDGE_10K_1000_20261127_144302; systematic Safari 300 × 10k, 0 strict, 207.84s, ~/DAVE_EDGE_SAFARI_300_20261127_145216, seed IDs 1 + i×11310 for i=0..299, last3381691. Three workers, sequential 10s per100 and Safari 15s per45, nine/six pauses respectively as requested. Seed1 overlaps; not 1300 independent random seeds. Same intended Edge fixture/rules; compare recorded binary/config/input fingerprints before causal conclusions. No new 10k survivors. Actual local campaign data not received; results based on owner final logs.

Owner requests standalone Python local HDD processing, no large ZIP. New scripts/sniff_motoex_campaigns.py reads two completed campaign directories, validates seed schedule and saved hashes, measures Q3/S from saved JSON, compares lock/board/net/endpoint invariants against prepared inputs, counts placement/layout signatures and overlaps, aggregates incomplete-net combinations and component rotations, distinguishes distinct wire offenders from wire/body crossing records, ranks routing-only research candidates (1–3 distinct offending wires), records errors and manifest comparison. Reads only; no solver, Node, Qt, pip, board modifications or promotion of rejected layouts. Missing diagnostics not treated as zero. Electrical and body status remains CLI-reported; independent copper graph/body replay still outstanding. Unit tests supplied; Mac execution pending. Compact generated report.md/summary.json/seeds.csv to research/dave-sniff/20261127-10k/ (commit only those after local execution); raw campaign directories stay local. No production/GUI changes.

## 27 November — completed local 10k forensic sniff: orientation evidence

Owner Mac report archived in [research/dave-sniff/20261127-10k](research/dave-sniff/20261127-10k/) at e6dd9578e022aa7f0875156e89cbb40c043f098a. Read report.md, summary.json, seeds.csv; standalone sniffer executed locally, no raw rejected boards transferred. Both campaigns' recorded fixture, binary hashes, board, USB and solver flags match each other and recorded 100k baseline fingerprints; all inspected prepared input raw hashes 0554804ce7ef1fb2c527d6adbbe7996085d00fd598b9781a842dae76c9176dce. 1000 consecutive / 300 spaced attempts, 40/13 unsolved, 960/287 saved hashes verified, 262/86 reported electrically complete, 698/201 incomplete, 1/0 conflicts, 29/10 zero crossing, 19/13 zero nonvertical. All inspected placements/layouts distinct within campaigns; one shared seed and layout across them. Zero recorded invariant, net/wire diagnostic mismatch or read/schema errors. This rules out duplicate layout saturation in these inspected samples, not all possible seed-distribution effects. No strict survivors. Counts are attempt-weighted and include the repeated seed once per campaign.

Aggregated from summary.json rotation-by-net-pattern counters (not a new geometry/graph replay):

| GPS rotation | Saved boards | Reported electrically complete | Contains GND/net25/net29 |
| ---: | ---: | ---: | ---: |
| 0 | 690 | 0 | 690 |
| 90 | 300 | 211 | 0 |
| 180 | 71 | 0 | 71 |
| 270 | 186 | 137 | 0 |

GPS horizontal 761/761 contain triple, vertical 0/486; 348/486 vertical electrically complete (71.6%). Exact GPS triple alone 561 (435+126), not all 761. All 348 complete boards have GPS 90/270.

| MPU rotation | Saved boards | Reported electrically complete | Contains GND/net10/net11 |
| ---: | ---: | ---: | ---: |
| 0 | 909 | 273 | 0 |
| 90 | 36 | 0 | 36 |
| 180 | 228 | 75 | 1 |
| 270 | 74 | 0 | 74 |

All 110 MPU 90/270 contain triple, only one of 1137 MPU 0/180 contains triple. Exact MPU triple alone 33 (27+6). All 348 complete boards have MPU 0/180. These are final-state associations, not proof that orientation masks improve search; test counterfactual with fixed settings. Candidate narrow experimental masks: GPS 90/270, MPU 0/180. Validate fixture footprint/pin transforms first; do not apply historical seven-part Arm C restrictions blindly. Proposed paired 10k comparison on same seeds and native Edge build plus only validated two-part restrictions; no new campaign authorised by this note. Keep strict rules and no board growth.

47 routing-only candidates from sniffer (34 sequential, 13 Safari): 6 with 1 distinct offending wire, 16 with 2, 25 with 3. One-offender seed IDs (one-based wire numbers) Safari 327991 wire6 44W/60C rawQ68.33; sequential 514 wire13 46/62 Q68.02, 902 wire13 48/64 Q67.50, 542 wire53 53/69 Q64.46, 949 wire10 56/72 Q62.44, 399 wire24 58/74 Q60.09. All six have one nonvertical; all except 542 also cross bodies. Seed542 no recorded crossing, clean slant repair test. Raw Q on rejected boards not strict or proof of repairability. Crossing records sum across campaigns: ESP32 1556, GPS 1297, MPU 970, M1 802, Switched Buck 719 (wire/body incidences, not unique jumpers). The sniffer validates endpoint indices and recorded diagnostics against raw board fields; cannot independently establish pin occupancy/body crossings/electrical completeness. Full independent replay and surgery pending. No production/GUI change.

## 27 November — approved GPS/MPU pair experiment (staged; Mac execution pending)

Owner approved 100 sequential seeds 1..100 at 10k, three workers, latest smoko cadence 15s after each 45 completed (two pauses), fixed USB col47, 24×56 both locked, knives/stacks allowed, drill-domain and wire-polish OFF. Baseline is first 100 of archived 10k sequential 1000-seed campaign, not 100k. Compare strict, electrical complete, paired gains/losses, triple nets, distinct offending wires and Q3; cooldown differs from original 1000-seed run, so separate solve timings from wall time. New --orientation-pair opt-in builds a separate native Edge decoder under ignored native/build/edge_gps_mpu_<generated hash>, using original Edge flags and source, without editing production decode.c or rebuilding baseline/route/addon. Requires exact recorded MOTOEX source and baseline native fingerprints. GPS UUID adb3d26e-a0af-4dda-b90e-51b263b6f9a8 (five consecutive horizontal pins at 0°, four assigned), MPU UUID 77c3cebd-3237-48d9-85c5-b0b0dfaec1c9 (eight consecutive vertical pins at 0°, four assigned). Verify fixture pin offsets and named nets before compile; generated C matches four transformed pin-line shapes and four assigned pins, requires unique matches and unlocked parts; aborts on ambiguous/missing match, incompatible GPS half-turn capability or active drill rotation mode. Initial GPS 90°, MPU 0°; existing rotation proposal RNG retained, reject disallowed proposal without redrawing inside mutation. Other parts and costs unchanged. Runtime stderr marker and saved UUID rotations checked, bad experimental contract cannot pass and stops after current batch drained. Generated source/decoder/compiler/baseline hashes and masks stored in build metadata and manifest; resume compares metadata. Geometry matching is intentionally fixture-limited, not general API or proof of future fixture identity. Source anchors inspected; static unit tests included, no Mac compilation or live result claimed. No GUI bump or production decoder change. 


### Orientation-pair generator regression fix

Owner Mac first test run: saved-mask test passed, double-patch guard test failed (1/2 passed); no compile or solve launched. Original C anchors survive insertions, so anchor counting did not detect repeated patching. Explicitly reject source containing the experiment marker or helper identifiers before modifying it; retain and extend regression test. Generated first-pass C remains unchanged. Mac rerun pending.

## 27 November — completed controlled GPS/MPU orientation pair at 10k

Owner final log: 0/100 strict, 84.95s wall, ~/DAVE_EDGE_GPS_MPU_10K_20261127_151448/report.md. Local sniff archived at bfe25bfb6e39e49e8f36797f792ccf9339e08004, research/dave-sniff/20261127-orientation-pair/{report.md,summary.json,seeds.csv}. Directly read summary and paired CSV slices (rows 2–101 baseline seeds 1–100, rows 1002–1101 experiment seeds 1–100). Compare matched seed IDs, not the entire 1000 baseline. Fixture, USB, board and solver settings match; route/addon fingerprints unchanged; decoder changed intentionally. Native compile and campaign completed on owner Mac, no independent rerun here. Experimental generated C SHA 55737e5c71f1dd86b5e2a1050f3c430f39d8f72b905d9f8d3d95b0b70d4fb569, decoder SHA 4d3390ee4eea1f9cfabed54a015f8558b5c1e034f930adf8d261837e34552ddb, original C SHA ef0370ae7db2a59cb89723a153834fdc4d6135e28ad0d2030d423f3587b993e5, Apple clang16 x86_64. All96 saved hashes verified, no reported invariant/diagnostic/read errors. GPS 82 at90 and14 at270; MPU 85 at0 and11 at180 (all within masks). No raw boards transferred. No independent electrical/body replay.

| Paired metric (100 attempts each) | Original | Restricted |
| --- | ---: | ---: |
| Strict | 0 | 0 |
| Saved / feasible | 96 | 96 |
| Reported electrically complete | 22 | 69 |
| Reported incomplete | 74 | 27 |
| Contains GPS triple GND/net25/net29 | 64 | 0 |
| Contains MPU triple GND/net10/net11 | 7 | 0 |
| Exactly GPS triple | 45 | 0 |
| Exactly MPU triple | 3 | 0 |
| Geometry nonzero | 2 | 3 |
| Near misses (1–3 distinct offending wires, electrical complete, geometry0, other sniffer gates) | 1 | 5 |
| Median solve ms (all attempts) | 860.935 | 1036.33 |

Paired electrical outcomes: 14 both complete,55 gains,8 losses,23 neither. +47 percentage points; 69/22=3.13636×; exact two-sided paired binomial/McNemar p=9.761673086614714e-10 under independent discordant-pair sign null (not proof of generalization to other fixtures). All 96 restricted saved boards still have crossing and nonvertical errors; remaining net failures mostly isolated (26 one-net, one two-net). Original unsolved11,54,74,84; experiment43,47,50,100. Distinct layouts96 each, no overlap between experiment and entire original1000. Electrical-complete subset means: crossing incidences11.5909→11.0435; crossing wires5.5→5.0870; nonvertical5.7273→5.5652; union offenders6.5455→6.6522; wires48.7273→50.0725; cuts64.7273→66.0725; raw Q3 45.9759→45.9278. Among14 complete in both, mean distinct offenders6.4286→6.3571 (median6 both). All-saved mean offenders6.1667→7.09375, crossing incidences9.65625→11.52083; avoid conflating changed composition with causal routing degradation. No demonstrated strict improvement.

Near misses: baseline seed59 3 offenders 41W/57C rawQ61.35; restricted seed26 two offenders wires24,28 (one nonvertical, two crossing wires, four wire/body incidences) 47W/63C Q68.61; seed94 three offenders18,23,42 42/58 Q64.80; seed20 three8,9,21 48/64 Q59.49; seed21 three23,28,30 54/70 Q58.75; seed40 three24,36,45 60/76 Q51.39. No single-wire near misses in restricted cohort. Candidate Q3 descriptive only. Remaining bottleneck strict routing; recommend inspect fixed-placement rerouting/surgery on selected boards rather than immediately increase seeds or moves. No new run or code change authorized by this report. Keep isolated masks as research arm, not production default. 

## 28 November — approved bounded fixed-placement multi-wire repair

Owner requests patch/test following GPS/MPU 69/100 electrically complete, zero strict. Add standalone scripts/dave_fixed_route.js; no production solver or GUI changes. Exact archived five-board cohort (26,94,20,21,40) and results/manifest/input/saved SHA checks before replay. Replay original saved audit, independent horizontal hole union-find (drilled holes removed, floating pin netKeys isolated), crossing predicate, original offender IDs and Q3. If baseline disagreement, do not promote. Two fixed-cut/fixed-placement arms: remove all offending wires retaining clean ones, then independently rip up all wires. Enumerate clear same-column endpoints from real geometry and occupied-hole helpers; forbid new shared solder holes and floating/other-net joins. Reconnect most constrained split copper group via bounded paths through pinless groups, backtrack across alternatives; 128 distinct search states per arm, 4 hops, 8 paths, 1200 queued states per path search. Rank first independently audited strict result from each arm by Q3 then wire count. Every accepted board must pass auditSavedStrict, hole graph, endpoint occupancy, vertical and body checks. No cut moves, no annealing, no changes to raw archive. Bounds are not exhaustive; no-path is not infeasibility proof. Eight synthetic assertions executed in JS tool against the exact pure graph/routing functions (two nets, relay, distinct solder holes, floating short, blocked route, cap, drilled split and endpoint). Mac Node harness and actual five saved board replays pending; user has local HDD only. Outputs report.json/report.md and strict witnesses only; archive in research/dave-fixed-route/20261128 after local run. Do not automatically promote to production.

## 28 November — fixed-placement routing outcome and reachability diagnosis

Owner Mac eight synthetic assertions passed and five-board test completed, archived at 565b1b8fd2159b80a7f8f31e644d897f83a688ef, research/dave-fixed-route/20261128/report.json and report.md. All five original boards replayed electrical-complete on strict checker AND independent hole union-find including floating keys, geometry0, exact offender and Q3 match. Strict rescues0/5. Retain-clean all five stop at one state, no path search, zero available outgoing degree from at least one split group under exclusive-endpoint rule. Full-ripup all five hit 128-state cap (seed21 one queue cap, seed40 three); no proof of infeasibility. Legal edges 4343/4276/4410/5012/4455 for seeds26/94/20/21/40. Existing body overhang warnings seed26 C1,C6; seed20 C1; seed21 L1; seed40 C6; seed94 none. Do not conflate warnings with recorded strict failures.

Important experimental restriction: previous repair forbids new shared jumper solder holes, unlike production boardPins.ts which explicitly permits daisy-chaining. Next read-only --diagnose mode in scripts/dave_fixed_route.js compares three exact copper-group reachability graphs: retained clean jumpers with endpoints reserved, retained with endpoint reuse allowed as a relaxation, full rip-up without reserved endpoints. For every split net, reports all terminal groups, actual free attachment coordinates, neighbor counts and disconnected clusters. Exhaustive BFS over legal vertical edges (no hop or search-state cap); other-net/floating groups excluded, no future competition for pinless relays or solder holes modelled, so disconnected nets cannot be reconnected under the given fixed-cut graph assumptions; reachable does not imply joint routability. Diagnostic only; no change to repair acceptance, no solver or board changes. Four additional synthetic reachability assertions executed here; actual Mac diagnosis pending. Archive to research/dave-fixed-route/20261128-reachability. If full-ripup graph disconnected, inspect cut relocation/placement constraints; if only reserved mode disconnected, investigate bounded daisy-chain repair; if full graph connected, improve multi-net resource search rather than arbitrarily raise annealing. No production change.

## 28 November — reachability result and group-level router experiment

Owner Mac 12 synthetic assertions passed; reachability reports committed 0c610c1d9eb7004e430b245e6bdd6be7641bead0, research/dave-fixed-route/20261128-reachability/report.json and report.md. Direct report inspection: seeds26/94/20/21/40 have 2/3/3/3/3 disconnected nets with clean wires retained; identical even permitting endpoint reuse. Every affected split terminal group has free holes but zero legal outgoing group neighbors in both retained modes (28 groups total). Names: 26 net28,net25; 94 GND,12v Switched,net6; 20 net6,net10,net11; 21 net3,net6,net27; 40 GND,net24,net3. Full rip-up leaves 16/19/16/14/18 split nets respectively, all individually reachable, no zero-degree terminal groups. This demonstrates that existing wire allocation blocks potential paths; does NOT prove simultaneous routing feasibility or identify a specific stolen relay without further trace. Keep cuts and placements fixed for next test; no need for cut-slide escalation yet.

Add opt-in --group-route in scripts/dave_fixed_route.js for same five source-hash-verified boards. Full rip-up; collapse equivalent legal endpoint pairs into a copper-group edge with preference for shorter and unused ends. Allow same-net endpoint reuse as production permits (not relaxation of strict crossing/vertical/electrical rules). First join same-net labeled groups directly without consuming neutral copper, then verify all remaining net terminal groups reachable before allocating further relays; choose lowest-degree split group and least reachability slack; branch over shortest distinct paths, alternate first relays and individual relay exclusions, dedup by copper partition; prune on unreachable net. 512 states and 16 candidate paths per branching state, no claim of exhaustive feasibility; first strict result, not Q3 optimum. Independent hole graph, saved audit, original locks/placement/cuts, endpoint occupancy and geometry required unchanged. Old modes unchanged. Five new synthetic assertions exercised (two-net shared-relay competition, legal daisy, infeasible exclusive relay, direct joins, state cap); all 17 pure assertions executed here against exact functions. Actual Mac test pending. Archive new output to research/dave-fixed-route/20261128-group-route. No production solver or GUI modifications.

## 28 November — group-route outcome and conflict-based fixed-cut feasibility

Owner Mac 17 synthetic assertions passed; five-board V2 experiment archived 3311c93b0a341e6af707c482ca25089f747c838d, research/dave-fixed-route/20261128-group-route/report.json. All five original graphs and audit prerequisites replayed. Strict rescues 0/5. Seed26/94/20 explored 71/6/35 states respectively, no state or branch cap, forward prunes37/2/17, maxdepth5/3/4. This exhausts only the heuristic path generation, not all possible allocations. Seeds21/40 both hit512-state cap, forward prunes208/201, maxdepth12. No branch cap reported in any. Do not infer impossible fixed-cut routing from V2.

Add opt-in --conflict-route for same five hash-verified boards, no placement/cut changes. Build static graph of individual copper groups and legal vertical edges (same geometry/occupied-hole predicates). With stacking and same-net endpoint reuse allowed, collapse each pair of copper groups to one shortest edge. Single-net BFS tree can use only its own terminal groups and unassigned copper not forbidden by branch constraints. Independently route every split net. If neutral copper claimed by two nets, branch by forbidding it to either net and reroute only affected net; dedup forbidden-set states and cache per-net routes, reject disconnected branches. No hop or path-count caps. This is complete for node-disjoint connected-subgraph feasibility on the fixed legal-edge graph if search exhausts the frontier; 4096 expanded state cap produces SEARCH_CAP, never infeasibility. GRAPH_INFEASIBLE refers only to that fixed-cut, fixed-position graph with the exact endpoint/body model and floating isolation, not arbitrary cut or placement changes. Final strict audit, independent hole graph, endpoint and wire checks unchanged, first valid witness not Q3 optimum. Existing modes preserved. Seven new synthetic checks executed here, including comparison with exhaustive neutral-group assignments on 96 deterministic seven-node graphs, blocked shared relay, alternative relay, cap, direct join, floating pin and eight-hop route. All 24 synthetic assertions executed on exact pure functions; Mac actual replay pending. Output research/dave-fixed-route/20261128-conflict-route. No production or GUI changes.

## 28 November — conflict-route outcomes and one-cut relocation experiment

Owner Mac 24 synthetic checks passed; actual five-board conflict-route archive e0c6ad0467299e92e252ecba5d37a28ea7ede06f, research/dave-fixed-route/20261128-conflict-route/report.json. All five baseline replays valid electrically, geometry0, no rescues. Seeds26/94 exhaust fixed-cut legal-edge graph in 605/19 states, best conflict pairs3 both; conflict routing time14.989/3.440ms. Seeds20/21/40 cap4096, best pairs5/2/4, route time52.107/77.989/99.211ms. Proven infeasible only under the fixed-cut graph model for first two; three remain inconclusive. No production change.

Opt-in --cut-slide in scripts/dave_fixed_route.js targets only seeds26 and94 (proven-infeasible cases). Components, dimensions, netlist, cut count/type fixed; enumerate one existing cut shifted along same row, preserving original copper connectivity partition of all component pin anchors (including floating), no duplicate cut coordinates or drilled pins. Unlike previous autopsy, wire endpoint partitions not frozen: all jumpers rebuilt. Compute geometric legal vertical edge superset once with no cuts, filter drilled endpoints per variant. Probe up to512 eligible variants ordered by displacement with one conflict-search state each; rank unresolved by best conflict pair count then displacement, deep-search up to32 variants with4096 states each. No claim exhaustive across all cut variants; report caps and per-variant outcomes. Audit every returned candidate with actual new cut occupancy, independent hole graph, strict saved audit, vertical/body and unique wire IDs; choose best valid Q3 then wire count. No cut additions/deletions, placement movement, annealing or raw archive changes. Eight new synthetic checks executed on exact functions (includes formerly infeasible shared-relay graph made routable by one cut relocation, pin partition, drilled endpoints and cap); all32 pure assertions executed here, Mac replay pending. Output research/dave-fixed-route/20261128-cut-slide. No production or GUI change.

## 28 November — single-cut relocation outcome and complete variant coverage

Owner Mac 32 synthetic assertions passed. Archive 4a5f514ba65ae0773dab11928018fde4ca518139, research/dave-fixed-route/20261128-cut-slide/report.json. No strict rescue. Seed26: 732 eligible variants,512 probed (13 immediately graph-infeasible),32 deep all graph-infeasible,45 distinct variants proved infeasible total,687 not resolved,14218 states,10871 route calls. Seed94:589 eligible,512 probed (19 graph-infeasible),32 deep all graph-infeasible,51 distinct variants proved infeasible total,538 not resolved,1888 states,11717 route calls. Deep shortlist concentrated on cut indices56,57 for26 and20,55,56 for94. Best conflict pair count3 for26,2 for94 (zero-based row0 col35→42 knife and row10 col25→43 drill). No witness. Raw board/strict rules unchanged. This is limited coverage, not evidence that every single-cut relocation fails.

Add --cut-slide-all: same two hash-verified boards; visit EVERY eligible single same-row cut variant preserving cut type/count and pin-anchor partition, with4096 conflict states per variant. No ranking shortlist; every variant accounted for exactly once, progress every100. Retain best strict Q3 across audited witnesses. If all variants exhaust without route report ONE_CUT_GRAPH_INFEASIBLE (model-specific); any unresolved cap reports SEARCH_CAP; audit rejects separate. Original bounded --cut-slide still available. Three additional pure assertions run here (full coverage/accounting, witness retention, cap accounting), total35; actual Mac run pending. Output research/dave-fixed-route/20261128-cut-slide-all. No production, GUI or annealer changes. Do not extrapolate one-cut failure to multi-cut or placement infeasibility.

### What is checked in vs what is verified

| Item | Current checkpoint |
| --- | --- |
| Repository milestone | 2.00 (VERSION) |
| Headless package | 2.0.0 (src/frontend/package.json) |
| GUI | 2.39 (gui/VERSION), PySide6 |
| Construction score | Q3, campaign schema 2 |
| Consolidation commit | 84cdc2315a2afe72b71c27fca5bd4852c0cb455d |
| Documentation reconciliation | 28d8aa571979c8f2b17f936b0746f0f350331d04 |
| Remote branch state | main only; all four former branches merged and deleted |
| Last owner-reported tests | 26 Nov: Python GUI regression suite passed after two fixes; all 7 Node headless suites passed |
| Outstanding validation | Post-consolidation production regressions, archive and independent re-audit of iterative-polish results, standalone Mac app qualification |

Current code unchanged by branch consolidation or documentation reconciliation. Do not equate Git HEAD with a locally rebuilt executable. Owner's local cleanup reported a modified compiled renderer cli.js and untracked scripts, JSONs, test folders and workspaces; preserve them. No new tests were run by the AI for this handover. Current app launch/build state on the iMac is not independently verified.

### Architecture and fixed contracts

One native optimisation engine, not a Python replacement:

Qt6 GUI / Python orchestration → native V5 Node CLI (src/frontend/tests/solver/v5Solve.js) → autoLayout5.ts → C decoder/annealer (v5wasm/decode.c) → final router/repair (layout2/finish.ts, v5wasm/route.c) → saved JSON → separate strict audit (auditSavedStrict.js) → Q3 ranking and SVG preview.

Relevant source lives under src/frontend/components/stripboard/ unless stated otherwise. The saved audit shares repository electrical/geometry helpers; the new independent copper-graph replay still reuses pin transformations. Neither is an independent manufacturing sign-off.

GUI Pass One is implemented, strict-only, button-triggered. Preflight uses static 100-point JSON complexity sniff (gui/json_sniff.py), recommends 10k or 20k without running qualification trials before GO. Keep both options, explicit confirmation, existing CPU allocation, project-specific Work directories, live activity and board preview. Save pass CSV, winner JSON and both SVGs; after pass completion ask whether to see the single champion (no top-five popup). Pass Two imports survivors but optimisation search and genome save/load are NOT implemented. Do not claim otherwise. Historical GUI screenshots/plans do not override current source.

Q3 contract (gui/quality.py):
`Q3 = round(max(0, 100 - 0.4*(0.6*W + 0.4*C + 0.02*L + 10*D + 15*U + max(0,S-1)**2)), 2)`.
W jumpers, C cuts, L mm at 2.54 mm pitch, D column-changing wires, U unplaced on-board components, S maximum simultaneous vertical positive-length overlap (0 no wires, 1 no stack). Strict audit separately enforces physical/electrical validity. Raw Q3 cannot override a failed audit. Q1/Q2 campaign history cannot be resumed as Q3. See [quality contract](docs/QUALITY_Q3_2026-11-25.md).

Opt-in candidate policies strict/diagonal/crossings/archive exist in CLI and scripts/run_candidate_hunt.py. Only STRICT_PASS is build-ready. Research candidates retain actual faults and audit status; default strict exit semantics unchanged. See [candidate policies](docs/CANDIDATE_POLICIES.md).

### Current research — Operation Break Karl

Latest completed evidence in [research/mortal-kombat](research/mortal-kombat/): 100 saved candidates, 50 rounds, independent fresh anneals 10k–500k at 10k increments, experimental orientation decoder, fixed 24×56, knives and stacking permitted. One worker per fighter; future forensic runs prefer one worker total.

| Fighter | Seed | Points | Round wins | Strict passes | Best strict Q3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Dave / Sub-Zero | 1216 | 234 | 26 | 14/50 | 85.58 at 450k, 23W/39C/S1 |
| Steve / Scorpion | 1859 | 216 | 16 | 11/50 | 85.66 at 500k, 22W/38C/S2 |

8 draws; 25 strict, 75 failed. Championship points differ from strict qualification. Neither original championship board reached Q86; subsequent surgery reached 86.40. Manifest input and decoder hashes are preserved; do not substitute a different prepared input or call the experimental decoder production. Results are from two selected seeds, not an unbiased benchmark. Larger budgets use fresh cooling schedules, not progressive warm starts.

Earlier Arm C orientation-domain work, owner logs: baseline Arm A 23/2000 strict at 100k vs Arm C 55/2000, paired overlap 1. Rotation mask changes were fixture-specific, experimental, not production; no claim of general proof or 2k success. Local later 117-seed ladder stopped at 500k; owner directed no further extension. Those earlier reports and local archives must be checked before quoting further statistics. Do not assume every local artifact is in Git.

Static source targets, not fixed or runtime-confirmed bugs:
1. finish.ts:573–576,594–596 — repick/channel reject nonvertical wires.
2. slantRepairPass.ts:59 and finish.ts:182 — lock ID set empty, no c.locked test in movable one-hole tap selection; illegal adoption not demonstrated.
3. finish.ts:372 — final crossing score uses initial padded comps, potentially stale after chosen placement changes.
4. route.c:125,683–741,946–967 — nominal 32 relay budget favours wide donated tails; one intermediate relay per connection attempt; free groups exempt from cap.
5. finish.ts:535–536,826 — inherited geometry violations can pass no-new-violations eligibility.

[Detailed findings and limitations](docs/KARL_FORENSICS_2026-11-27.md). Priority boards seed1216 at 280k (one nonvertical), 350k/360k (one crossing each), 490k (two crossings). All four archived audits report zero conflicts, incomplete, geometry and unplaced.

## 27 November — completed 100-board autopsy, Q86.40 project record

Owner terminal evidence: ~/KARL_AUTOPSY_ALL_20261127_103543/report.json; research implementation 11ec46f, replay launched after documentation commit f630793. Exact prepared-input fingerprint matched; graph/path/cut-partition synthetic tests passed. All 100 archived boards replayed; 25 original strict, 23 eligible single-offender failures, zero graph disagreements/skips. Three distinct failures rescued, four original strict layouts improved, no additional annealing. Retaining originals or strict improvements gives 28/100 usable (25% → 28%, +3 percentage points, +12% relative); 3/23 eligible failures rescued (13.0%), 4/25 strict improved (16%). This selected two-seed budget ladder is not a random-seed benchmark.

| Seed | Budget | Original Q3 | New strict Q3 | Method | Outcome |
| --- | ---: | ---: | ---: | --- | --- |
| 1216 | 120k | 78.68 | 79.08 | direct_endpoint | strict improved |
| 1216 | 350k | 81.97 | 81.93 | cut_slide_path | rescued |
| 1216 | 360k | 80.04 | 80.04 | cut_slide_path | rescued |
| 1216 | 390k | 79.63 | 81.63 | direct_endpoint | strict improved |
| 1216 | 400k | 77.83 | 79.83 | direct_endpoint | strict improved |
| 1216 | 460k | 85.20 | **86.40** | direct_endpoint | strict improved; project record |
| 1859 | 470k | 75.42 | 75.73 | net_wide_path | rescued |

Previous project record 85.66 at seed1859/500k; new owner-reported record 86.40 at seed1216/460k plus deterministic surgery (+0.74 over prior record, +1.20 over its own original). Not Q86 at 2k. Original 460k board had 21W/37C/S3; direct endpoint method preserves W/C and vertical span, so +1.20 is consistent with S3→S2; owner report now confirms 21W/37C/S2, exact w0 coordinates below; saved files still require independent verification. No additional annealing or placement changes. Two cut rescues move one existing cut without changing kind/count. All accepted variants passed saved strict audit and separate copper graph; graph shares pin transforms and is not independent manufacturing certification.

Full log aggregates: 22 cut-slide searches, 58,226 positions considered, 5,122 anchor-safe and graph-safe, 7 cut positions yielding paths, 10 candidate route audits accepted (two distinct boards), zero reported truncations or audit-cap hits. 23 net-wide searches, one rescue. Zero fixed two-strip direct rescues and zero isolated-relay rescues. This is a finished research replay, not a production fix.

## Exact witness deltas — owner report inspection, 27 November

Zero-based coordinates (row,col). Owner pasted all seven best detail records from the full replay. These are observed report deltas; actual repaired JSON files still local, not yet independently fetched or audited by AI.

| Seed/budget | Wire | Before → after | W/C/S before → after | Length mm before → after |
| --- | --- | --- | --- | --- |
| 1216/120k | w10 | (10,40)-(19,40) → (10,42)-(19,42) | 36/52/2 → 36/52/1 | 495.30 → 495.30 |
| 1216/350k | w12 | (4,27)-(23,27) → (2,8)-(23,8) | 30/46/2 → 30/46/2 | 383.54 → 388.62 |
| 1216/360k | w4 | (7,22)-(22,22) → (7,8)-(22,8) | 33/49/2 → 33/49/2 | 474.98 → 474.98 |
| 1216/390k | w13 | (17,20)-(19,20) → (17,21)-(19,21) | 27/43/4 → 27/43/3 | 426.72 → 426.72 |
| 1216/400k | w7 | (5,15)-(13,15) → (5,17)-(13,17) | 29/45/4 → 29/45/3 | 551.18 → 551.18 |
| 1216/460k | w0 | (0,1)-(8,1) → (0,3)-(8,3) | 21/37/3 → 21/37/2 | 279.40 → 279.40 |
| 1859/470k | w23 | (4,19)-(23,19) → (4,18)-(0,18) | 39/55/3 → 39/55/3 | 601.98 → 563.88 |

350k: drilled cut index36 at (23,18) moved to (23,7). 360k: drilled cut index37 at (22,18) moved to (22,7). Both 11-column relocations, same count/type. Existing autoFinish seven-nearest-candidate cap is a credible limitation, but actual legal candidate ranking and finish path still need verification. 350k also changes source attachment row. Net-wide 470k rescue shortens jumper by 15 holes (38.10mm). All four strict improvements are solely stack-depth reductions. New record Q86.40 = Q85.20 + 0.4*(4−1) = +1.20; two-hole sideways relocation, no additional length/cuts/placement changes. Original Q85.66 record surpassed.

Next gate: preserve seven repaired files plus report and exact prepared input in research/karl-autopsy/20261127 (not a branch), verify with existing auditor and Q3, review file scope before committing. No further anneal needed. Then evaluate a bounded strict-incumbent-preserving stack-polish pass first, isolated from cut rescue; benchmark earlier/lower-move archived campaigns, no production changes until reviewed. Remote branch API still returns main only at df394ba; pasted older branch upload output is historical, not evidence of current branch.

## 27 November — completed iterative stack polish: Q86.80, S1

Owner Mac terminal evidence: source 596f129, report ~/KARL_STACK_POLISH_20261127_105635/report.json. Prepared-input fingerprint and synthetic tests passed. 25 original strict layouts and seven previously verified witnesses processed, nine original improvements (36%), two witness improvements, 15 plateau-only attempts, zero final-audit fallbacks and zero move-cap hits. Witnesses overlap the original cohort; do not count 32 independent placements. No additional annealing, cut/placement changes, wire count or length changes. Retain strict incumbents when Q3 does not improve.

| Seed | Budget | Original Q3 | Polished Q3 | Stack depth |
| --- | ---: | ---: | ---: | --- |
| 1216 | 120k | 78.68 | 79.08 | 2→1 |
| 1859 | 310k | 83.30 | 84.50 | 3→2 |
| 1859 | 360k | 78.06 | 81.26 | 4→2 |
| 1216 | 370k | 82.41 | 83.61 | 3→2 |
| 1216 | 380k | 79.74 | 80.94 | 3→2 |
| 1216 | 390k | 79.63 | 81.63 | 4→3 |
| 1216 | 400k | 77.83 | 81.03 | 4→2 |
| 1216 | 460k | 85.20 | **86.80** | 3→1 |
| 1859 | 500k | 85.66 | **86.06** | 2→1 |

1216/460k: 21W, 37C, 279.4mm unchanged; four relocations from original, three from Q86.40 witness, both achieve 86.80. 1859/500k: 22W, 38C, S1 after four relocations. Both unstacked under Q3 definition. New project record Q86.80, +0.40 over prior repaired Q86.40 and +1.14 over original Q85.66. The 400k witness improved 79.83→81.03, 460k witness 86.40→86.80. Results passed harness's saved strict auditor and separate graph; exact new witness files, per-board timings and Python Q3 recheck remain pending archival. No new production changes, no claimed 2k record.

## 27 November — 2k paired campaign partial evidence

Owner local campaign ~/StripSolve_2K_CHALLENGE_20261126_232031, manifest 2,000 moves, 2,000 planned seeds per arm, two workers, exact same prepared-input SHA-256 as Mortal Kombat, fixed 24×56. Observed CSV snapshot: 1,666 rows per arm (334 per arm absent relative to plan; reason/finished state not established). All recorded FAIL, zero strict. A: 199 electrically complete, 80 routing-only, 852 locked-board changed, 367 geometry failures, 1,467 incomplete, 1,658 nonvertical, 1,651 body crossings. C: 989 complete, 421 routing-only, 732 locked-board changed, 367 geometry, 677 incomplete, 1,665 nonvertical, 1,664 body crossings. C completeness 59.36% vs A 11.94% (4.97x); routing-only 25.27% vs 4.80% (5.26x). Every C routing-only record has both NONVERTICAL and BODY_CROSSINGS categories; no inference yet about distinct offending wires or repairability. Counts are owner-provided CSV summary; paired seed identity not yet verified. Orientation intervention is experimental and fixture-specific. No 2k strict result.

Next: read-only scripts/karl_2k_triage.js replays the selected A/C saved archives (80+421 expected) using frozen prepared input, checks row seed IDs and CSV hashes, reproduces strict audit and copper graph, counts distinct offending jumpers (a single wire can cross several bodies), reports histogram and 20 closest candidates sorted by distinct offender count then raw Q3. Missing archives and mismatches reported; no changes to boards, no annealing, no new campaign. JS syntax checked; actual Mac replay pending. Original campaign completeness and low-budget repair feasibility remain open.

### Next gate — preserve polish evidence and triage 2k archives

Preserve 11 improved output JSONs (nine originals plus two overlapping witness variants), report and verification against the existing exact input in research/karl-autopsy/20261127. Record audit, Q3 and file hashes; inspect runtime summary. Stop repeatedly optimising these already high-budget seeds: S1 has no remaining stack penalty, so further gains require wire/cut/length improvement. 2k partial owner CSV summary recorded above; inspect actual archives and distinct offender counts before attempting repairs. A strict-only polishing stage cannot rescue a failed 2k placement; if no strict passes, investigate failure categories and earlier placement/routing constraints first. No new seed campaign until evidence review. Production integration remains proposed; preserve native default and GUI 2.39.

### Historical iterative stack-polish design (completed)

Stack-polish experiment: owner verified all seven witness boards with saved strict audit and Python Q3, pushed dd0c1d0; remote main-only and verification.json inspected. New isolated scripts/karl_stack_polish.js processes original 25 strict boards and seven independently re-audited witnesses as distinct cohorts (four witnesses derive from original strict boards; do not count as 32 independent placements). Deterministic greedy maximum-depth then overlapping edge-pair reduction, strict decreasing potential allows plateau steps, max64 relocations per board. Preserve same two strips, same rows, wire length/count, cuts, placements and netlist; forbid occupied/used holes and crossings; final strict and copper graph audit; keep incumbent unless Q3 strictly improves and both checks pass. Verify canonical input and witness hashes. No native search, no rebuild, no production changes. Actual extracted synthetic tests (three-to-one stack, obstacle, determinism, cap and touching endpoints) passed in AI tooling, JS syntax checked; target-Mac archive run completed as recorded above. New outputs in fresh directory, no original changes. This is a research prototype, not exhaustive optimisation.

The original iterative-polish command is historical; do not rerun just to recreate the same output.

### Historical witness preservation gate (completed)

Do not rerun the 100-board archive just to obtain the same evidence. The original compressed boards are on main, but seven repaired JSONs and full report are still on the owner's Mac. Owner report endpoint and cut deltas inspected and recorded above. Preserve and independently audit actual witness JSONs and report before further experiments.

Production comparison (static source verified): autoFinish.ts:168–216 restricts cut slides to the offending jumper's two endpoint rows, tries seven nearest positions per cut and caps full reroutes at 60; its acceptance uses fewer offending wires and non-increasing starved/shared-joint counts. layout2/finish.ts:573–591 repick accepts first valid alternative between the original strips; 669–673 only invokes repair for badWire (crossings or forbidden stacking), not legal-but-expensive stack depth. This suggests separate validity rescue and strict Q3 improvement opportunities. Exact causal reason each archived case was missed remains unverified until witness deltas and actual finish path are checked. Do not increase brute-force budget blindly; propose opt-in bounded deterministic finisher only after witness inspection, regression tests and measured runtime. Retain strict original incumbent; no production or GUI changes here.

Earlier smoke stages and their historical commands are recorded in [forensic report](docs/KARL_FORENSICS_2026-11-27.md). Sister forensic script runtime remains pending; genome save/load is still proposed, GUI Pass Two import-only.

### Mac directory and command contract

Source checkout: ~/Documents/stripboard-optimiser. MacPorts Python: /opt/local/bin/python3.13. Local source Work separate from packaged ~/Library/Application Support/StripSolve/Work/. Known arena: ~/MORTAL_KOMBAT_DAVE_STEVE; previous orientation campaign: ~/ARM_C_ORIENTATION_20261126_211658; candidate ladders and other archives may exist locally. Verify filenames, exact prepared input and binary hashes before using. Do not infer a clean working tree or delete old work.

Owner sync (no overwrite of unrelated changes):
```bash
cd ~/Documents/stripboard-optimiser
git status --short
git pull --ff-only
git branch -a
```

Regression commands, only when no solver campaign is active; build commands may regenerate outputs, so preserve existing tracked/local renderer changes:
```bash
cd ~/Documents/stripboard-optimiser/src/frontend
npm run test:headless
cd ../..
QT_QPA_PLATFORM=offscreen PATH="/opt/local/bin:$PATH" /opt/local/bin/python3.13 -B -m unittest discover -s tests -v
```
No new regression outcome implied. See [headless build docs](src/frontend/README.md), [GUI](gui/README.md), [standalone Mac](docs/STANDALONE_MACOS.md). The old scripts/run_wr_audio_moto.py clears existing rung outputs and has no resume; **do not rerun it casually**.

## Historical evidence and reading order

- [Project contract](project.md) — owner rules and accepted architecture.
- [Changelog](CHANGELOG.md) — revision history; update alongside this file.
- [Documentation index](docs/INDEX.md) — detailed research and contracts.
- [Legacy dated active handoff](docs/ACTIVE_HANDOFF_2026-11-24.md) — historical campaign details; current checkpoint here takes precedence.
- [V1.40 fixture](docs/MOTO_V1_40_FIXTURE.md) and [warm-start design](docs/MOTO_V1_40_LADDER_AND_WARM_START_2026-11-26.md) — frozen inputs, historical results and proposed save/load.
- [Repository audit](docs/REPOSITORY_AUDIT_2026-11-24.md) — historical static audit, not a fresh test report.

At the end of each engineering change, refresh the current checkpoint with actual revisions, checked-in vs running state, evidence, remaining blockers, decisions and the exact next owner command if needed. Preserve dated history in linked documents instead of accumulating contradictory current instructions. Never treat this handover as a substitute for inspecting source.
