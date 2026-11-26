# Sister — StripSolve forensic handoff 🦂

**From:** Brother (Moto-Mate project)  
**Date:** 2026-11-26  
**Owner:** Sister — you own the solver, the architecture, the fixes and the final engineering decisions.

Sis, we went looking for a better seed and ended up finding a much more interesting mess. 😂 The failed boards are telling us more than the winners. This is my evidence, hypotheses, proposed tests and ideas, not an instruction to blindly implement my guesses. Please challenge everything, especially my assumptions about routing and physical geometry.

## 0. Guardrails and provenance

- Baseline: Moto V1.40, 24 rows × 56 columns locked, zero component position locks, knives and stacking enabled, native strict hunt, 2,000 seeds × 100,000 moves, two workers.
- Local campaign directory: `~/Desktop/WR_Moto_V140_100k_STRICT_2000/`. Contains `results.csv`, `prepared_input.json`, `manifest.json`, `candidates/seed_XXXX.json.gz`. Controller-reported input SHA256: `0eee8b94847ebf622c4b2b0d580644f8456bb079a159617c0c72b65f76d09313`. Do not equate that hash with a raw file hash without checking controller semantics.
- Do not interrupt the live campaign, rebuild its binary, mutate its archives or overwrite its results. Work in an isolated branch/build and a fresh output directory. Preserve the original input and best layouts. No weakening of the strict independent saved-board audit to manufacture passes.
- Current reported baseline champion (latest known): seed 0858, Q82.35, 29W/45C/S2, 100k, zero nonvertical wires and body crossings. Not an independently verified manufacturing release.
- Evidence below comes from user-provided local console snapshots and source extracts, not a complete native source review. Counts refer to different snapshots; do not merge denominators. My diagnostic scripts ran locally under the user's control. No solver changes have been made by Brother.
- This repository is public. Keep complete board archives, private machine information and raw local logs out of this document unless separately authorised.

## 1. Executive findings — prioritise the actual defects

| ID | Finding | Evidence / status |
|---|---|---|
| SS-003 | GPS UART orientation-dependent routing pathology | 752 identical two-net failures independently reproduced; later comparison: 777 failures all at 0/180°, 792 electrically complete all at 90/270°. Root cause not yet known. |
| SS-004 | Locked row count changes | Nine saved outputs violate 24-row lock: eight have 25 rows, one 26; both locks still true. Confirmed output invariant violation; responsible path unknown. |
| SS-006/007 | Body crossings and nonvertical wires dominate rejected output | Large opportunity; determine whether search permits infeasible intermediates intentionally and whether final selection/repair is deficient. |
| SS-010 | Package collision | Seed 0232: 12v Mosfet and USB GND packages overlap. |
| SS-011 | MPU connectivity isolation | Seed 0286: MPU GND/SDA/SCL disconnected, plus GPS UART pair. |
| SS-001/002 | Defensive audit-policy inconsistencies | Concrete source-level counterexamples below; final independent audit still guards acceptance. |
| SS-005 | Q3 nonvertical mismatch | JS audit rejects horizontal/zero-length as well as diagonal wires; Python score only tests differing columns. |
| SS-008 | Possible loss of best feasible states | Hypothesis only; needs trace/replay. |
| SS-009 | Copper graph relationship | Strong empirical pattern, useful diagnostic; not an asserted universal invariant. |

## 2. Evidence: GPS pathology

At the 1,586-seed snapshot: 20 strict, 1,566 rejected, no execution errors or status disagreements. Among rejected boards: 1,487 nonvertical, 1,477 body crossings, 1,447 both; 871 electrically incomplete, 717 INCOMPLETE_2. There were 676 electrically complete failures with both geometry violations and no hard failures, nine with only nonvertical violations, six with only body crossings. These labels overlap.

At the 1,675-seed net autopsy snapshot: 752 recorded INCOMPLETE_2 cases, all 752 reproduced by the repository's electrical verifier. EXACTLY the same two entries in all 752:

- net25 / 0c069745-ebf2-462e-a98e-cb6fb7a87adb: ESP32 RX ↔ GPS TX.
- net29 / 10e3d982-9ef3-4fe5-8a40-066e834e506a: R12 pin 1 ↔ GPS RX.

Each net has exactly two disconnected groups, each containing a single endpoint; no unplaced pins. No replay disagreements in 16 full audit replays; zero read/verification errors in that report. 763 archived boards had electrical detail recovered.

Later GPS rotation autopsy (selected groups only, not all completed seeds):

| Rotation | INCOMPLETE_2 | Electrically complete |
|---|---:|---:|
| 0° | 547 | 0 |
| 90° | 0 | 340 |
| 180° | 230 | 0 |
| 270° | 0 | 452 |
| Total | 777 | 792 |

Perfect separation among 1,569 selected boards. Other incomplete failure classes were excluded; 90/270° does NOT guarantee strict validity, and the last 777 cases were selected by failure code, not all independently replayed for net identity. Same GPS defId in all selected boards: custom-6bcf83ae-5b58-49df-a9a3-34caa40020c5. Multiple board positions overlap between outcomes.

### Hypotheses, in order I would test

1. **Copper strip access / footprint geometry:** at some orientations, consecutive pins may share a horizontal strip. Knife cuts can isolate a pin to a segment with no legal vertical jumper landing hole outside the body. RX/TX may be internal header pins while the outer pins can escape. This is plausible, not confirmed; inspect actual definition, board copper pattern and transformed pins first.
2. **Native vs JS geometry semantics:** pin rotation pivot, row/col sign, body rectangle, footprint override, mirrored or rotated dimensions, boundary touch semantics, pin-on-body exemptions, off-board expansion, standing/flexible geometry. Compare actual native intermediate pin/obstacle data to JS, not just final coordinates.
3. **Router completeness:** net ordering, greedy jumper choices, segmentation, occupancy, per-net route attempt budget, inability to rip up/reroute, stale net/segment cache after placement rotation or cuts, missing local repair.
4. **Objective/final state:** valid orientation may exist during search and be lost in favour of cheaper but incomplete placement. Need historical best feasible state trace. Verify native objective rather than assuming it uses Q3.

### Falsifiable next experiments

- Replay saved seed 0019 (isolated GPS pair, 180°) and controls 0001 (270°, electrically complete), 0005 (90°, electrically complete) and 0858 (strict). Dump original GPS definition and transformed absolute pin coordinates, obstacles, copper segments, allowed landing holes, assigned nets, cuts and wires.
- Run the detailed electrical verifier on *all* archived boards, including other incomplete counts. Build unconditional per-rotation denominators and per-net missing rates. Include absolute position, edge distance, neighbouring footprints and route ordering. Separate electrically complete from strict.
- For each failed GPS endpoint, enumerate its copper-connected segment, every exposed legal hole and reachable vertical jumper destination. Record precise rejection reasons. Distinguish no possible legal route from router failing to find one.
- Minimal synthetic fixtures: same GPS/custom footprint and a few terminals, all four rotations, translated interior/edge placements, knives on/off, stacks on/off. Compare native/JS pin and segment parity. Include mirrored/asymmetric footprints and a terminal trapped between two cuts.
- Controlled orientation restriction to 90/270° only in a separate experimental run, never as a hardcoded GPS-specific production fix. Compare identical seeds/configs. If missing pair disappears, useful mitigation, not proof of mechanism.
- If access is truly impossible, add generic orientation/placement feasibility checking, early rejection or repair. Do not globally forbid 0/180°; assess each footprint and legal placement.

## 3. Evidence: locked-board expansion

Prepared board: rows=24, cols=56, lockedRows=true, lockedCols=true. The autopsy compared all 1,675 rows with stored audits and agreed in every case.

- 25×56: 0114, 0262, 0519, 0819, 1075, 1108, 1307, 1395.
- 26×56: 0415.
- Both flags remain true, columns unchanged. This is genuine dimension change in saved output, not a dropped flag or just an audit naming problem.

Trace dimensions at prepared input → native deserialization → initialization → placement mutation → routing/repair → normalization → export → final saved board. Find FIRST change. Suspect unguarded auto-grow, flexible/standing component placement, edge adjustment, postprocessing or serializer. Instrument the caller and reason for dimension changes. Add assertions and regression tests at API boundaries. Reject or rollback invalid operations atomically. **Never truncate rows back to 24 after routing**; doing so can invalidate placed parts, wires or cuts. Distinguish zero component locks from board dimension locks.

## 4. Graph-topology clue

For 1,657 of 1,675 archived outputs, including all nine expanded boards, the observed relation is:

```
rows + cuts - wires - incomplete_net_count = 40
```

For normal 24-row boards, cuts = wires + incomplete + 16. For 25 rows residual is 15; for 26 rows residual is 14. The 18 exceptions include some highly incomplete boards and some apparently electrically complete outputs.

Possible explanation: in a simple horizontal-strip graph, cuts create connected copper components and effective jumper unions merge them. A disconnected net with k groups needs at least k−1 additional unions. But cut kind, duplicate cuts, hole cuts, empty segments, redundant/cyclic wires, multiple disconnected groups, unused nets and conflicts all complicate the identity.

Build an explicit independent copper graph / union-find diagnostic using the actual copper pattern. Count components before/after cuts and wires, effective unions, redundant wires, net groups and unassigned copper islands. Compare native and JS graphs. Replace incomplete-net count with sum of group deficits when appropriate. Use the relation as a debugging signal, NEVER a qualification shortcut or universal invariant.

## 5. The wildcard is not a winner

Seed 0286: Q82.94, 28W/49C/S1, 312.42 mm, no nonvertical/body crossings, five incomplete nets. Seed 0858: Q82.35, 29W/45C/S2, 386.08 mm, strict. The wildcard is missing the two GPS nets AND the MPU's GND, SDA and SCL branches. The five missing nets each have two groups in the recovered verifier output. A naive repair adding five jumpers would give 33W, but actual repair may alter cuts, placement and jumper count. Do not mistake fewer wires achieved by omitting connections for an optimisation victory.

Seed 0232: INCOMPLETE_3 (GPS pair plus 12v Switched split into three groups), one nonvertical, one body crossing and one package overlap: 12v Mosfet and USB GND.

## 6. Scoring and policy findings

Relevant supplied source: scripts/run_candidate_hunt.py, gui/quality.py, src/frontend/tests/solver/candidatePolicy.js, auditSavedStrict.js, helpers.js and metricsLib.js in the same test directory, compiled out/components/stripboard/offBoard.js and partGeometry.js.

Q3 from gui/quality.py:
```
P = .6*W + .4*C + .02*L_mm + 10*D + 15*U + max(0,S-1)**2
Q3 = round(max(0, 100 - .4*P), 2)
```
D tests unequal columns only; U counts unplaced non-offboard/nonexcluded parts; S is maximum positive-length vertical overlap depth. JS audit wireLength uses grid pitches (multiply by 2.54); stacked counts overlapping wires, not maximum depth. Do not compare those metrics directly. Q3 has no direct penalty for incomplete nets, conflicts, body crossings or board-lock change. That's fine for a construction score if feasibility is a separate hard gate. Do not silently redefine Q3: version any changed formula and retain baseline comparisons.

JS strict audit nonvertical condition also rejects same-row wires (including zero-length). Python D misses horizontal and zero-length wires. Review scoring and validation semantics. Body overhang is presently a warning, not a strict failure; physical acceptability needs a separate explicit decision (including real header clearances). Keep audit requirements and construction-quality ranking distinct.

Two source-level counterexamples to add as regression tests:
- classifySavedAudit({valid:false, failures:["NONVERTICAL_3"], nonvertical:1, crossings:0}, "diagonal") can qualify because it checks positive-count presence, not exact numeric agreement. Same issue for body crossings. Require consistency of numeric counts and failure code counts, reject malformed provided values and contradictory duplicates as appropriate.
- classifyNativeDiagnostic({strictValid:false, strictFailures:[]}, "strict") reports prequalified:true because blockingFailures is empty. Reject inconsistent native diagnostics (also consider true plus nonempty list) or explicitly document prequalification semantics. The saved-board audit remains mandatory, so neither example proves a false strict pass in the campaign.

Potential further review: JS audit early returns can hide preceding failures; ensure diagnostics preserve useful detail without weakening validity. Its electricalComplete flag is derived from specific failure prefixes, not a substitute for strictValid. Unknown faults remain hard failures.

## 7. Proposed solver architecture (your call)

**Feasibility before construction quality; exploration may remain infeasible.** Keep two archives: best independently feasible candidate and best infeasible candidates with useful, distinct violation patterns. A search can traverse infeasible states if the algorithm requires it, but never discard the best feasible state just because a lower-cost invalid state appears. Return the best valid state if one exists; preserve invalid research candidates separately.

- Define violation vector: board/netlist/placement invariants, missing pins/conflicts, connectivity group deficit, package geometry, body crossings, nonvertical wires, then construction metrics. Use a lexicographic or constraint-dominance rule for incumbent selection. Consider adaptive search penalties rather than hard rejection of all intermediate connectivity failures, which might make the search unable to escape local minima.
- Early generic orientation/placement feasibility: compute actual pin coordinates, segments, necessary cuts and legal escape/landing holes. Cache with precise invalidation. Only reject provably impossible states; use heuristics for likely difficult states.
- Route the most constrained nets first (fewest legal exits, shortest available segment, narrow bottleneck), revisit failed routes with bounded rip-up/retry. Measure impact versus existing ordering. Never hardcode GPS or specific net IDs in generic solver code.
- Add strict local repair: legal vertical jumper rerouting, cut relocation, controlled component rotations/translations, bounded neighbourhood search; independently verify net isolation/completeness after every accepted repair. Avoid naive addition of wires or cuts.
- Unify geometry semantics or add exhaustive cross-language parity tests. Specifically test package overlap vs wire-body crossings, endpoints on boundaries, header pin/body exceptions, physical board overhang and cut kinds.
- Track routing failures by net identity and reason instead of aggregate count. Add structured diagnostic output without changing normal acceptance policy.

## 8. Trace instrumentation and tests

Opt-in deterministic trace, sampled/first-event to avoid enormous output: seed, actual moves, RNG/build/input identity, operator, stage, board dimensions before/after, transformed pin coordinates, net ID, segment ID, candidate landing holes, attempted routes, rejection reason, accepted/rejected mutation, objective breakdown, cache invalidation, first connected/first strict move, best feasible state and whether retained, final export state. Separate diagnostics overhead from performance benchmarks.

Regression queue:
| Seed | Purpose |
|---|---|
| 0002, 0003 | GPS at 0°/180° with repeated missing pair |
| 0019 | Isolated GPS pair; no nonvertical/body crossing |
| 0001, 0005 | Electrically complete orientation controls |
| 0123 | Exactly one body crossing, otherwise audit clean |
| 0564 | Exactly one nonvertical, otherwise audit clean |
| 0114, 0415 | 25-row / 26-row lock violations |
| 0232 | MOSFET/USB GND overlap, three missing nets |
| 0286 | High-Q invalid, GPS + MPU isolation |
| 0858 | Positive strict control, Q82.35 |
| 0223 | Second strict control, Q79.59, 30W/46C/S3 |

First reproduce saved audit, then reproduce native run with identical prepared input, binary/config/seed/moves; confirm deterministic behaviour or quantify variability. Do not assume different move budgets are prefixes of the same run. Add unit/property tests for all rotation transforms, cut boundaries, graph union consistency, lock-preserving mutation and rollback, and no-loss feasible incumbent. Keep a known-good strict archive immutable.

Compare baseline and patched builds using paired seeds and identical inputs: strict rate, electrical completion, GPS pair rate by rotation, lock violations, geometry/crossing/nonvertical rates, Q3 among strict, W≤30 strict rate, time and actual moves. Report regressions, denominators and paired outcomes; use fresh holdout seeds/circuits to avoid overfitting Moto-Mate. No arbitrary promised pass-rate gain.

## 9. Pass Two / Grand Final — recommendations, secondary to debugging

Original qualification rule: hardFailures empty, electricalComplete true, bodyCrossings zero, nonvertical count 0..3; plus highest Q3 rejected wildcard (explicit failures). Compute actual metrics from every gzip archive with gui.quality.construction_metrics(saved), not blank rejected CSV scores. Latest qualification snapshot was 1,198 seeds, 15 strict + 3 one + 2 two + 0 three + 1 wildcard = 21. Not the current final pool.

100k–1M, 50k steps: reuse 100k, 18 new trials per seed, 378 for 21, two workers. Consider Pareto fronts within feasibility groups (Q3, W/C/S/length), diversity and repair deficit; don't eliminate promising seeds based solely on 100k. Broad probes at 150/350/550/800/1000k then evidence-guided gap filling. Reordering the same deterministic trials does not improve final max; adaptive allocation only changes outcome if job set/budget changes. Optional additional rescue seeds by failure-signature diversity would change workload and needs approval. Grand Final requires independent strict PASS and ≤30W, best two DISTINCT seeds by highest qualifying Q3, local productive budget band(s) at 1k increments. Confirm actual band-selection strategy and whether budget changes annealing schedule. Preserve the best valid parent, never promote a wildcard without strict audit.

I would defer major new search spending until the P0 defects are understood, while allowing the existing hunt to finish.

## 10. Moto-Mate physical architecture is a separate experiment

ESP32 has fitted headers and currently sits in breadboard; final header/socket clearance still to verify. SHT40 off-board is a physical design requirement for useful ambient readings. RTC and GPS may be off-board. Preserve on-board connector footprints, netlist semantics and external harness counts when designing V1.41. Keep original V1.40 input for debugging; removing GPS would hide the failure mode, not fix the solver. Do not conflate relaxed physical footprints with relaxed electrical checks.

## 11. What I'd love back from you, Sis

Your independent diagnosis, the actual source paths/call sites responsible, which hypotheses you disproved, a minimal reproduction, tests that fail before and pass after, and a paired-seed comparison. You decide architecture and patch sequence. If my graph theory is bollocks or the GPS orientation is physically impossible rather than a software defect, say so and show why. If the current solver already implements any of these ideas, tell us where and why the observed failures still occur.

Priority: isolate lock expansion (hard invariant) and GPS routing mechanism (dominant failure), then geometry parity, feasible incumbent/repair, policy hardening, then search efficiency. Keep the independent validator the authority.

We came for a world record. We found a solver research programme instead. The failures are the treasure.

Over to you, boss. Go nuts — scientifically. 😂

— Brother
