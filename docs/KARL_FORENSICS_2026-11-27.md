# 27 November 2026 — main-only consolidation and Karl forensic research

**Latest: [Dave's MOTOEX Edge ladder and Claude Q86.80 verification](DAVE_MOTOEX_EDGE_2026-11-27.md). Q86.80 arithmetic independently reproduced; raw final archive and full replay outstanding. MOTOEX separate baseline 8/100 strict, Q81.92.**


## Revision and scope

- Repository milestone: 2.00 (root VERSION); headless package: 2.0.0; StripSolve GUI: 2.39; construction score: Q3.
- Baseline after consolidation: `84cdc2315a2afe72b71c27fca5bd4852c0cb455d`. GitHub verification after cleanup returned only main. The four former branch tips are ancestors of main.
- Research scripts and archives were added; active solver, GUI and renderer implementations were not modified by consolidation. GUI version policy does not require a bump for research/documentation-only changes. No new release tag.
- Owner's standing rule: work directly on main, never create branches or pull requests, and never submit reports, fixes, comments or contributions to Karl's upstream repository. Research lives in directories within main. Changes must carry their revision and documentation updates together. Do not change unrelated user files.
- Owner's Mac cleanup output showed main and origin/main only, with pre-existing tracked renderer modification and untracked local research files preserved. Do not reset, clean, stash or commit those indiscriminately.

## Completed Mortal Kombat — archived evidence

Source: [manifest](../research/mortal-kombat/manifest.json), [scorecard](../research/mortal-kombat/scorecard.csv), [championship](../research/mortal-kombat/championship.json), and 100 compressed saved candidates with individual result JSONs. All 50 rounds completed. Each budget is a fresh anneal, not a warm start; 10k–500k in 10k steps; one worker per fighter, 30-second interval between rounds. Fixed 24×56, knives and stacking allowed. Experimental orientation decoder used; do not assume it is the production binary.

Manifest input SHA-256: `0eee8b94847ebf622c4b2b0d580644f8456bb079a159617c0c72b65f76d09313`.
Manifest decoder SHA-256: `265ce63fb3828d467d4aff4307a658cbcbb3e550cee384e2ffeeb53504948064`. These are recorded fingerprints, not a fresh binary verification.

| Metric | Dave / Sub-Zero 1216 | Steve / Scorpion 1859 |
|---|---:|---:|
| Championship points | 234 | 216 |
| Round wins | 26 | 16 |
| Strict passes | 14/50 | 11/50 |
| Best strict Q3 | 85.58 at 450k | 85.66 at 500k |
| W/C/S at best | 23/39/1 | 22/38/2 |
| Cumulative solve seconds | 733.699 | 740.129 |

Eight drawn rounds; 25 strict passes, 75 failures. Championship scoring is distinct from strict qualification and best Q3. Neither reaches Q86. These two selected seeds are not an unbiased sample of solver performance. No additional competition run authorized.

## Forensic source findings (not runtime regression results)

Source reviewed against the repository code preceding consolidation:

1. `layout2/finish.ts:573–576,594–596`: endpoint repick and channel repair reject nonvertical wires at entry. Other repair paths exist; a reproducible saved-board rescue would establish impact.
2. `layout2/slantRepairPass.ts:59` and `layout2/finish.ts:182`: tap selection checks lockedIds, not c.locked; caller passes an empty set. A locked one-hole tap can enter the candidate set. No illegal adoption demonstrated; Moto fixture has no locked components.
3. `layout2/finish.ts:372`: final crossing score uses original padded comps rather than chosen updated placements. Possible stale-geometry scoring after movement; runtime reproduction pending.
4. `v5wasm/route.c:125,683–741,946–967`: relay budget prioritises wider donated tails, retaining free groups even beyond nominal cap; one intermediate relay per connection attempt. Search limitations, not yet established causes of Moto failure.
5. `layout2/finish.ts:535–536,826`: final repair eligibility tests no new geometry violations relative to the starting layout, not zero violations. Saved strict audit remains mandatory.

Source locations are under src/frontend/components/stripboard/. Do not describe these as fixed or claim a measured speedup.

Priority archive cases: seed 1216 at 280k (Q73.82, NONVERTICAL_1), 350k (Q81.97, BODY_CROSSINGS_1), 360k (Q80.04, BODY_CROSSINGS_1), 490k (Q79.76, BODY_CROSSINGS_2). Archived audit records report zero conflicts, incomplete nets, geometry violations and unplaced components for these cases.

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

Previous project record 85.66 at seed1859/500k; new owner-reported record 86.40 at seed1216/460k plus deterministic surgery (+0.74 over prior record, +1.20 over its own original). Not Q86 at 2k. Original 460k board had 21W/37C/S3; direct endpoint method preserves W/C and vertical span, so +1.20 is consistent with S3→S2; owner report confirms 21W/37C/S2, exact coordinates below; saved files still require independent verification. No additional annealing or placement changes. Two cut rescues move one existing cut without changing kind/count. All accepted variants passed saved strict audit and separate copper graph; graph shares pin transforms and is not independent manufacturing certification.

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

### Next gate

Preserve 11 improved output JSONs (nine originals plus two overlapping witness variants), report and verification against the existing exact input in research/karl-autopsy/20261127. Record audit, Q3 and file hashes; inspect runtime summary. Stop repeatedly optimising these already high-budget seeds: S1 has no remaining stack penalty, so further gains require wire/cut/length improvement. Establish what the previous 2k paired A/C experiment actually produced from its local results CSVs and manifests. A strict-only polishing stage cannot rescue a failed 2k placement; if no strict passes, investigate failure categories and earlier placement/routing constraints first. No new seed campaign until evidence review. Production integration remains proposed; preserve native default and GUI 2.39.

### Historical iterative stack-polish design (completed)

Stack-polish experiment: owner verified all seven witness boards with saved strict audit and Python Q3, pushed dd0c1d0; remote main-only and verification.json inspected. New isolated scripts/karl_stack_polish.js processes original 25 strict boards and seven independently re-audited witnesses as distinct cohorts (four witnesses derive from original strict boards; do not count as 32 independent placements). Deterministic greedy maximum-depth then overlapping edge-pair reduction, strict decreasing potential allows plateau steps, max64 relocations per board. Preserve same two strips, same rows, wire length/count, cuts, placements and netlist; forbid occupied/used holes and crossings; final strict and copper graph audit; keep incumbent unless Q3 strictly improves and both checks pass. Verify canonical input and witness hashes. No native search, no rebuild, no production changes. Actual extracted synthetic tests (three-to-one stack, obstacle, determinism, cap and touching endpoints) passed in AI tooling, JS syntax checked; target-Mac archive run completed as recorded above. New outputs in fresh directory, no original changes. This is a research prototype, not exhaustive optimisation.

### Historical witness preservation gate (completed)

Do not rerun the 100-board archive just to obtain the same evidence. The original compressed boards are on main, but seven repaired JSONs and full report are still on the owner's Mac. Inspect exact before/after endpoints, cuts, Q3 and strict status; preserve report and witness artifacts before further experiments. Specifically identify the record's stack change, two cut offsets, and the net-wide rescue's new attachments.

Production comparison (static source verified): autoFinish.ts:168–216 restricts cut slides to the offending jumper's two endpoint rows, tries seven nearest positions per cut and caps full reroutes at 60; its acceptance uses fewer offending wires and non-increasing starved/shared-joint counts. layout2/finish.ts:573–591 repick accepts first valid alternative between the original strips; 669–673 only invokes repair for badWire (crossings or forbidden stacking), not legal-but-expensive stack depth. This suggests separate validity rescue and strict Q3 improvement opportunities. Exact causal reason each archived case was missed remains unverified until witness deltas and actual finish path are checked. Do not increase brute-force budget blindly; propose opt-in bounded deterministic finisher only after witness inspection, regression tests and measured runtime. Retain strict original incumbent; no production or GUI changes here.

## 27 November — 2k paired campaign partial evidence

Owner local campaign ~/StripSolve_2K_CHALLENGE_20261126_232031, manifest 2,000 moves, 2,000 planned seeds per arm, two workers, exact same prepared-input SHA-256 as Mortal Kombat, fixed 24×56. Observed CSV snapshot: 1,666 rows per arm (334 per arm absent relative to plan; reason/finished state not established). All recorded FAIL, zero strict. A: 199 electrically complete, 80 routing-only, 852 locked-board changed, 367 geometry failures, 1,467 incomplete, 1,658 nonvertical, 1,651 body crossings. C: 989 complete, 421 routing-only, 732 locked-board changed, 367 geometry, 677 incomplete, 1,665 nonvertical, 1,664 body crossings. C completeness 59.36% vs A 11.94% (4.97x); routing-only 25.27% vs 4.80% (5.26x). Every C routing-only record has both NONVERTICAL and BODY_CROSSINGS categories; no inference yet about distinct offending wires or repairability. Counts are owner-provided CSV summary; paired seed identity not yet verified. Orientation intervention is experimental and fixture-specific. No 2k strict result.

Next: read-only scripts/karl_2k_triage.js replays the selected A/C saved archives (80+421 expected) using frozen prepared input, checks row seed IDs and CSV hashes, reproduces strict audit and copper graph, counts distinct offending jumpers (a single wire can cross several bodies), reports histogram and 20 closest candidates sorted by distinct offender count then raw Q3. Missing archives and mismatches reported; no changes to boards, no annealing, no new campaign. JS syntax checked; actual Mac replay pending. Original campaign completeness and low-budget repair feasibility remain open.

## Earlier smoke evidence (historical)


### 27 November — OWNER MAC PASS: single-cut surgery (source 11ec46f)

Report: ~/KARL_AUTOPSY_SMOKE_20261127_103416/report.json. Owner pasted complete terminal summary; saved witness JSON and report details have not yet been independently inspected. Prepared input fingerprint matched the manifest; all synthetic graph/path/cut-partition tests passed. Six boards replayed, two original strict champions reproduced, zero electrical graph disagreements, four single-offender near-misses. Two distinct rejected boards were rescued; ten accepted candidate variants across those two boards. No champion improvement.

| Seed 1216 budget | Cut positions considered | Anchor/graph-safe | Candidate audits for cut routes | Accepted cut routes | Best rescued strict Q3 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 280k | 2803 | 183 | 0 | 0 | — |
| 350k | 2444 | 246 | 3 | 3 | 81.93 (raw original 81.97) |
| 360k | 2590 | 204 | 7 | 7 | 80.04 (raw original 80.04) |
| 490k | 2644 | 196 | 0 | 0 | — |

All cut searches report zero truncation and no audit-cap hit. Each rescue changes one existing cut position, not cut count/kind, plus replacement jumper(s); original component placement, 24×56 dimensions, original netlist/locks and remaining wires preserved by harness construction. Both saved strict audit and separate copper graph accepted the results. The graph still shares pin transforms. Exact cut displacement and replacement wire details require reading the saved report. No Q86 or WR improvement. Two of four selected failures rescued; 2/6 original strict to 4/6 if rescued variants retained. This is a concrete missed finishing opportunity, not proof of a particular production function defect or a population-wide doubling of strict pass rate.

Next: freeze the current research algorithm and replay the complete 100-board Mortal Kombat archive, one process, zero annealing, no rebuild, fresh output directory. Compare original strict 25/100 against strict survivors plus unique newly rescued boards; separately report eligible single-offender denominator, cut-route variants, champion improvement, graph disagreements and bounded-search truncation. The 100 boards are selected seeds 1216 and 1859 over budgets 10k–500k, not an independent random seed campaign. Owner report deltas now documented above; independently audit saved witness files, then compare the missed cut positions with the existing autoFinish.ts cut-slide and finish.ts repair logic before proposing a production patch. No production code or GUI revision change.

Owner command: `cd ~/Documents/stripboard-optimiser && git pull --ff-only && /opt/local/bin/python3.13 scripts/run_karl_autopsy.py --all`. Preserve smoke reports and original archives.


Owner Mac net-wide smoke (report KARL_AUTOPSY_SMOKE_20261127_103201): 6/6 replay, two strict, zero graph disagreements, zero rescues or improvements. Seed1216 280k source/target free holes 52/68, zero eligible cross-group column pairs; 350k 27/19, all 9 pairs blocked by bodies; 360k 9/14, 1/1 blocked; 490k 1/33, 1/1 blocked. All had zero clean edges and no search truncation. This disproves only the tested endpoint/relay search under existing cuts, occupied-hole restrictions and no shared solder holes, not arbitrary fixed-placement routability. Next gate: single existing cut slide, preserving kind/count, all component pin and existing wire-anchor copper partitions, original locks/netlist, remaining wires and 24×56 dimensions. Enumerate every candidate single-cut column, prioritize shortest displacement; require independent graph before rerouting and both audits after rerouting. Four-hop bounded search (5,000 queued states and eight paths per cut), 256 candidate audits per board, explicit truncation/cap reporting. JS syntax and extracted graph/path/cut-partition tests passed; owner runtime completed as recorded above. No production or GUI change.

Owner Mac six-board smoke (27 Nov, report KARL_AUTOPSY_SMOKE_20261127_102846): exact input fingerprint matched, graph self-test passed, 6/6 boards replayed, 2 strict reproduced, zero electrical graph disagreements, four single offending wires (490k crosses two bodies), zero rescues/improvements. Each rejected board reached only one audit trial (redundant offending-wire removal). Direct and one-empty-strip relay searches produced no audit candidates. This is a negative result for the restricted search, not proof of placement infeasibility. Follow-up net-wide search removes the same offending wire and considers all copper strips joined to either side, plus pinless transit groups, with unique new endpoint holes, no cuts/placement changes and at most four hops. Bounded at 20,000 queued states and 64 paths per board, reports truncation and blocked edges; not exhaustive. JS syntax and extracted graph/path self-tests pass; net-wide Mac replay completed as recorded above. No production change.

**Smoke gate update:** run `scripts/run_karl_autopsy.py` with MacPorts Python from the checkout after pulling main. It locates the original prepared input by the manifest fingerprint and defaults to the four near-misses and two champions; `--all` requires separate explicit invocation after smoke review. The JS harness independently rechecks the fingerprint, skips electrical graph disagreements and attempts removing a redundant offending wire. JavaScript syntax and extracted graph self-test passed in AI tooling. Initial six-board Mac smoke completed as recorded above; full 100-board replay completed as recorded above; cut-slide smoke now has two rescues as recorded above.

- [scripts/karl_autopsy.js](../scripts/karl_autopsy.js), original commit 8e42c3f: fixed-placement/cut wire surgery, existing isolated relay strips, redundant jumper removal, stack reduction and a horizontal copper-graph replay. Original JavaScript syntax checked before commit. Current harness synthetic tests and six-board replay have passed on the Mac; full archive replay completed as recorded above. The graph reuses repository pin transforms; not a fully independent physical verifier. Verify prepared-input provenance against manifest using the canonical Python fingerprint and confirm compiled helper compatibility before running. Preserve original archives; report results separately; one worker; no annealing or board growth.
- [scripts/sister_forensics.js](../scripts/sister_forensics.js), original commit 628a3d1: independent graph/topology research, runtime validation pending.
- [Historical legal-topology patch](../research/legacy-topology/README.md): archived obsolete desktop worker, not active GUI implementation.
- Candidate policy source already matched main byte-for-byte at merge; newer main documentation retained.

The fixed-placement rescue objective has been demonstrated on three archived failures; two require one relocated cut. Only a verified rescue is evidence of a missed router opportunity. The eventual 2k strict Q86 goal remains a research target, not a result. GUI Pass Two is still import-only. Production tests were last owner-reported passing on 26 November; no post-consolidation rebuild or regression run reported.
