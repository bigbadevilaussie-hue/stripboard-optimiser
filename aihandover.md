# StripSolve — AI Handover

**27 November — Seven autopsy witnesses archived and re-audited: 7/7 STRICT PASS, Q3 scores reproduced, project record Q86.40. See `research/karl-autopsy/20261127/verification.json`. No production changes.**


## CURRENT CHECKPOINT — 2026-11-27 (read this first)

This section supersedes earlier dated handoffs. Historical results are evidence, not instructions to rerun campaigns. Read this file, [project.md](project.md), the current [forensic checkpoint](docs/KARL_FORENSICS_2026-11-27.md) and relevant source before making changes. Check actual main HEAD and local status before proposing commands. Owner calls the original solver Karl; the current project is StripSolve, separate from Moto-Mate firmware and OSA. Brother's Moto-Mate aihandover.md supplied the organisational model only (source checkpoint 90940f6); do not import its device-specific rules or change other products.

### Owner's non-negotiable rules

- **MAIN ONLY.** No new branches or pull requests. No upstream reports, issues, comments or code submissions to Karl. Work within the owner's fork; research belongs in separate directories, not branches. Never force-push or discard local work.
- **Revision control and documentation are part of every change.** Update this current checkpoint, CHANGELOG.md and affected current docs together with approved implementation/research changes. GUI/renderer/import changes bump gui/VERSION in the same commit; repository milestone VERSION and package version are separate. Do not increment a version just to imply progress. Report commit SHA, files, actual changes and validation status.
- **Quality and physical validity first.** A locked 24×56 board means exactly 24×56. No widening the board or silently weakening strict rules to get a PASS. Preserve component locks, original netlist/definitions, legal geometry and electrical completeness. Human-buildable vertical wires; stacking and cut modes follow selected settings. Drilled cuts preferred by owner for human construction; specific research runs may explicitly allow knives. Q3 is construction quality, not electrical validity or percentage of optimum.
- Prefer small reproducible counterexamples, deterministic replay, one-worker forensic tests, fewer moves and smaller boards over indiscriminate brute force. Target useful 2k-move layouts; Q86 at 2k remains a research goal; Q86.80 at 460k plus zero-anneal iterative polish is now owner-reported. No new wagers.
- Owner prefers concise, paste-ready Mac Terminal commands starting with cd, actual Git commits, no repeated questions, clean Qt6 Arctic Ice + Colourburst UI, and useful emoji terminal feedback. Do not claim background work, completed runtime tests, or local filesystem access without evidence.
- Preserve existing local files and experiment results. No destructive reruns or blanket git add/reset/clean/stash. No automatic launch of a new campaign; verify scope and provenance. Do not change Moto-Mate, Fan-Mate or OSA.

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
