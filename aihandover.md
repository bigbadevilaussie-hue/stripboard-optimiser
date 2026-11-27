# StripSolve — AI Handover

## CURRENT CHECKPOINT — 2026-11-27 (read this first)

This section supersedes earlier dated handoffs. Historical results are evidence, not instructions to rerun campaigns. Read this file, [project.md](project.md), the current [forensic checkpoint](docs/KARL_FORENSICS_2026-11-27.md) and relevant source before making changes. Check actual main HEAD and local status before proposing commands. Owner calls the original solver Karl; the current project is StripSolve, separate from Moto-Mate firmware and OSA. Brother's Moto-Mate aihandover.md supplied the organisational model only (source checkpoint 90940f6); do not import its device-specific rules or change other products.

### Owner's non-negotiable rules

- **MAIN ONLY.** No new branches or pull requests. No upstream reports, issues, comments or code submissions to Karl. Work within the owner's fork; research belongs in separate directories, not branches. Never force-push or discard local work.
- **Revision control and documentation are part of every change.** Update this current checkpoint, CHANGELOG.md and affected current docs together with approved implementation/research changes. GUI/renderer/import changes bump gui/VERSION in the same commit; repository milestone VERSION and package version are separate. Do not increment a version just to imply progress. Report commit SHA, files, actual changes and validation status.
- **Quality and physical validity first.** A locked 24×56 board means exactly 24×56. No widening the board or silently weakening strict rules to get a PASS. Preserve component locks, original netlist/definitions, legal geometry and electrical completeness. Human-buildable vertical wires; stacking and cut modes follow selected settings. Drilled cuts preferred by owner for human construction; specific research runs may explicitly allow knives. Q3 is construction quality, not electrical validity or percentage of optimum.
- Prefer small reproducible counterexamples, deterministic replay, one-worker forensic tests, fewer moves and smaller boards over indiscriminate brute force. Target useful 2k-move layouts; Q86 at 2k remains a research goal; Q86.40 at 460k plus zero-anneal surgery is now owner-reported. No new wagers.
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
| Outstanding validation | Post-consolidation production regressions, independent inspection of seven repaired witness JSONs, standalone Mac app qualification |

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

Previous project record 85.66 at seed1859/500k; new owner-reported record 86.40 at seed1216/460k plus deterministic surgery (+0.74 over prior record, +1.20 over its own original). Not Q86 at 2k. Original 460k board had 21W/37C/S3; direct endpoint method preserves W/C and vertical span, so +1.20 is consistent with S3→S2; exact repaired W/C/S and wire coordinates require inspection of saved JSON/report. No additional annealing or placement changes. Two cut rescues move one existing cut without changing kind/count. All accepted variants passed saved strict audit and separate copper graph; graph shares pin transforms and is not independent manufacturing certification.

Full log aggregates: 22 cut-slide searches, 58,226 positions considered, 5,122 anchor-safe and graph-safe, 7 cut positions yielding paths, 10 candidate route audits accepted (two distinct boards), zero reported truncations or audit-cap hits. 23 net-wide searches, one rescue. Zero fixed two-strip direct rescues and zero isolated-relay rescues. This is a finished research replay, not a production fix.

### Next gate — preserve and inspect seven witnesses

Do not rerun the 100-board archive just to obtain the same evidence. The original compressed boards are on main, but seven repaired JSONs and full report are still on the owner's Mac. Inspect exact before/after endpoints, cuts, Q3 and strict status; preserve report and witness artifacts before further experiments. Specifically identify the record's stack change, two cut offsets, and the net-wide rescue's new attachments.

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
