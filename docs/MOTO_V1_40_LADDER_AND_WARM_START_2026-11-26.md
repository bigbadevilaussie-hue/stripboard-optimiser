# Moto V1.40 research — ladder, routing forensics and MAME-style save states

**26 November 2026 — active research handoff.** This note records the owner/Claude/ChatGPT design discussion and partial Mac observations. No native, GUI or fixture change is implemented by this note. GUI 2.39 / Q3 remains current, Pass Two remains import-only, and the existing native V5 solver remains the only authorised optimiser.

## 1. Frozen input and separate wager

- [V1.40 fixture](MOTO_V1_40_FIXTURE.md): exact committed hardware JSON, blob `cd54ad2fe22b9ece9cc3888c5f19c08cb5e8aace`, 24 × 56 locked board, **zero locked components** (owner confirmed). Q1/Q2 have initial positions but are not locked.
- SNIFF1 computed from the repository mounting and footprint rules: 87.01/100 vs old Moto 78.03. 35 on-board / 9 off-board components, 99 on-board assignments, 125 total assignments, 34 nets, demand 91, fanout 28, nominal rectangle area 504 cells (37.5% vs old 293/1344 = 21.8%). GPS and RTC add 206 nominal cells. This is a complexity heuristic, not calibrated success probability or exact occupied area.
- [Frozen three-way wager](MOTO_V1_40_WR_WAGER_2026-11-26.md): Claude 78.56, GPT Sister 79.76, ChatGPT 80.72; closest absolute error to the best independently saved-audited strict Q3 in a separate completed 2,000 × 20k batch. Boundaries 79.16 and 80.24, ties shared, no strict pass = no winner. Do not count the research ladder or later repair runs. No retrospective footprint changes or solver tuning for the frozen contest. Claude's physical footprint concerns remain unverified build caveats, not fixture edits.
- Before the official batch: verify the frozen input and exact runtime/build fingerprints; record tracked worktree cleanliness or diffs, wire polish OFF and agreed rules. Do not silently treat a Git HEAD as proof of the executed binary.

## 2. Standalone Mac research ladder (running at last report)

Owner requested a paste-ready Python heredoc controller, delivered in chat as `~/Documents/stripboard-optimiser/moto_v140_ladder.py`. **Local script, not committed by this note.** Do not claim access to the Mac or rerun/rebuild while the live job is running.

| Setting | Value |
|---|---|
| Move budgets | 2k, 4k, …, 30k (15 rungs) |
| Seeds | 1–500 repeated at each rung |
| Total | 7,500 independent solves |
| Workers | 3 |
| Native options | native=1, strict=1, drilled=0, drill-domain=0, nostack=0, wire-polish=0, routing-preference=wires |
| Candidate policy | diagonal; otherwise valid DIAG_PASS separate from STRICT_PASS |
| Exact-best | not enabled (no --exact flag) |
| Decoder | standard native directory, because no locked Edge part |
| Timeout | 1,800 seconds per native/audit process |
| Output | timestamped Desktop directory, full CSV, manifest, exact input, champion JSONs; temporary rejected JSONs removed |
| Console | emoji lines for strict/diagonal passes only, plus stage summaries |

First launch failed before any solve because the local checkout lacked V1.40. Owner received pull/build/run instructions; subsequent live output confirms trials are running. No need to recreate the script or restart this campaign.

Last reported output folder: `~/Desktop/WR_Moto_V140_20261126_142101/`. `results.csv` contains every completed attempt, result and full failure codes, Q3 for saved non-UNSOLVED boards (including invalid boards), W/C/S, length mm, diagonal/slant/horizontal counts, crossings, incomplete nets, conflicts, geometry, audit/native JSON, process codes and timings. **Never take max Q3 without filtering STRICT_PASS.** Diagonal and rejected scores are research only. Separate stage/overall champions are saved only for qualifying classes; no near-miss genomes or rejected board JSONs are retained by this particular script. Fresh invocation creates a new directory, not a resume; Ctrl-C may wait for active subprocesses. No results are claimed beyond the owner's supplied snapshot.

## 3. Last measured snapshot — 2,318 / 7,500 trials

All 2,318 were FAIL, no strict or diagonal passes, no reported ERROR rows or shorts. The 10k rung was partial (318/500). This is not the final result. Zero ERROR rows means the harness reported no execution/verdict disagreements; it does not certify the solver or prove every internal metric agrees.

| Moves | Trials | Electrically complete | Clean geometry | Routing-only candidates | Avg solve wall s |
|---|---:|---:|---:|---:|---:|
| 2k | 500 | 78 | 382 | 29 | 0.614 |
| 4k | 500 | 89 | 422 | 59 | 0.719 |
| 6k | 500 | 107 | 448 | 79 | 1.084 |
| 8k | 500 | 126 | 451 | 102 | 1.254 |
| 10k partial | 318 | 76 | 300 | 65 | 1.318 |
| Total | 2318 | 476 | 2003 | 334 | — |

Failure groups overlap:

| Moves | Incomplete | Nonvertical | Body crossings | Geometry | Board dimensions |
|---|---:|---:|---:|---:|---:|
| 2k | 422 | 497 | 495 | 118 | 255 |
| 4k | 411 | 499 | 497 | 78 | 172 |
| 6k | 393 | 497 | 497 | 52 | 127 |
| 8k | 374 | 496 | 499 | 49 | 112 |
| 10k partial | 242 | 316 | 316 | 18 | 64 |
| Total | 1842 | 2305 | 2304 | 315 | 730 |

Exactly two incomplete nets in 873 rows (47.4% of electrically incomplete trials); this does **not** establish their identities. Identify nets via replay/diagnostics, not hard-coded GPS/RTC labels. Routing-only group is based on saved audit: electrical completion, zero geometry faults, no hard failures, no ERROR, only nonvertical/body-crossing violations. It grows from 5.8% at 2k to 20.4% at 8k (also 20.4% in partial 10k). Binary presence of routing faults is still ~99%; severity and joint validity matter more than flag presence.

| Budget | Near-miss seed | W | C | Nonvertical | Crossings | Q3 (not WR) |
|---|---:|---:|---:|---:|---:|---:|
| 2k | 0227 | 55 | 71 | 3 | 4 | 54.95 |
| 4k | 0053 | 54 | 70 | 3 | 3 | 55.93 |
| 6k | 0365 | 48 | 64 | 2 | 3 | 65.16 |
| 8k | 0013 | 45 | 61 | 1 | 4 | 68.68 |
| 10k partial | 0289 | 43 | 59 | 1 | 2 | 70.52 |

Seed 0289/10k is a priority forensic replay; no saved rejected board is available from this controller. Use identical input, options and decoder, archive replayed geometry and actual incomplete-net identities if available. Compare old Moto as a control before calling a regression. The historical WR runner explicitly selected the Edge decoder library even for non-Edge projects; the new controller selects standard. This is a genuine experimental difference, not proof of a regression. Replay identical cases across both libraries before conclusions.

Informal ladder side guesses, not official WR wager: owner 5 (interpreted in chat as strict passes across 7,500); ChatGPT 8 strict and 12 diagonal, mostly at 24–30k. No final count known.

## 4. Board-lock source finding

Verified in `src/frontend/components/stripboard/autoLayout5.ts` and `v5wasm/decode.c`:

- `physicalEdgeLock = parts.some(p => p.locked && p.comp.edge === true)` (around line 450); false for V1.40. It is the absence of a **locked Edge mount**, not simply absence of component locks, that disables the special checks.
- Standard native energy includes `W_LOCKOVER = 5000.0` times overflow. It is a soft penalty, not categorical exclusion.
- The opt-in Edge native build activates a feasibility ratchet only for appropriate locked Edge mounts: may explore overflow initially, then prevents leaving the cap after first feasible accepted state. TS guards selection of in-cap incumbents, exact repairs, finish alternatives and final selection with `physicalEdgeLock`. If no physical solution is found in that path, an explicit UNSOLVED board is returned rather than clamping illegal copper.
- Standard non-Edge search can retain/return overflow incumbents; strict CLI and saved audit reject them. `LOCKED_ROWS|LOCKED_BOARD_CHANGED` in the reported CSV demonstrates this is occurring. This is a known pre-existing design limitation, not evidence that the candidate-policy change broke the solver.
- Future experiment: opt-in physical-lock generalisation, distinguish temporary traversal from admissible returned incumbent; preserve original default path and compare same seeds, strict yield, Q3 and runtime. No change authorised/implemented in this note. Do not alter the running ladder or frozen wager.

## 5. New project: MAME-style save games for Pass Two

Owner's model: **SAVE → LOAD → OPTIMISE → SAVE**, each qualifying Pass One seed gets a `.sav`, reload those survivors rather than redoing discovery. The phrase "cheat mode" / MAME save-state is a humorous working concept, not an implemented GUI shortcut. This is iterated annealing from elites, not genetic crossover.

Two different operations:
1. Exact checkpoint: pause a predetermined N-move anneal, restore complete state and finish the same schedule. Could support interruption recovery later.
2. **Warm start (priority):** take a completed best genome, initialise a new anneal from it, deliberately reheat/refine, retain the better audited parent/child. This is not an extension of the original schedule and must not be described as bit-identical resume.

Geometric cooling depends on total moves (default T0=150, Tend=0.15); a 10k run finishes cold and is not the first half of a fresh 20k run. Independent ladder budgets remain independent. Exact recovery is lower priority given short individual trials; campaign-level checkpointing is separate.

### Native/TS implementation research — not implemented

Source paths:
- `src/frontend/components/stripboard/v5wasm/decode.c`
- `src/frontend/components/stripboard/v5wasm/v5Wasm.ts`
- `src/frontend/components/stripboard/autoLayout5.ts`
- `src/frontend/tests/solver/native/addon.c`, `nativeInstance.js`, `v5Solve.js`
- `src/frontend/tests/solver/auditSavedStrict.js`, `candidatePolicy.js`
- `gui/quality.py`

Current C loop `v5_annealStart` / `v5_annealStep` initialises fresh genome and retries decode up to 50 times. Events occur at start/new-best/end, not arbitrary move boundaries. TS `cur()` exposes current accepted genome, decoded metrics, iteration and event energy; `rngGet/rngSet` expose main RNG; `writeGenome` loads proposal buffers for decode. Current genome at end is not necessarily the best genome. Hidden state includes secondary RNG `strictState`, tie protection `strictTies`, temperature, iteration, energy, schedule, reference/accepted-state arrays and feasibility flags. Exact checkpoint needs all relevant C and TS state, including best incumbent; not just a genome or board JSON.

Claude's proposed minimal warm-start hook: separate `V5_EXPERIMENT_WARM_START` build, optional `v5_annealWarm(i32)` export, after `annealStart` load parent with `writeGenome`, activate warm mode; skip fresh init/retry on first step, fail cleanly if parent cannot decode. Reuse normal decode/accept path and initialise native best energy from parent. Implement matching optional addon export/TS capability checks and CLI input/output flags; no implicit fallback to fresh seed when warm requested. Build in isolated library directory via existing V5_NATIVE_LIB_DIR. Verify ABI compatibility and that shared addon/CLI edits do not perturb standard behaviour. Compile flag alone is not proof of isolation.

Strip-group write-back: decode can alter stored ties; accepted genome from `cur()` is post-write-back, but re-decoding can still change layout. Save the actual winning genome and verify round trip. Board-equivalent genomes may differ in future transitions. Do not reconstruct a genome from a routed JSON.

Exact-best complication: if --exact enabled, a second-half exact-repair result can beat the final genome's finished result. Current TS exact candidate stores {final, score}, not its producing genome. Track genome provenance at every competing finish and save the one actually selected. Current ladder does not enable exact-best. Also preserve finish choice/options, seed-dependent behavior and optional postprocessing.

### Proposed versioned .sav format

Compressed JSON with .sav extension initially; no need for a new binary format. Proposed fields, not a frozen schema:
- Format/version/type (warm-start parent vs future exact checkpoint), checksum of canonical payload, fixture/prepared-input SHA256 and blob ID.
- Solver revision and runtime hashes (decoder, router, addon/compiled solver as applicable); input/options compatibility check, genome shape/version.
- Winning post-write-back genome (gp, gn, rot, hv, br, gap, xgap, grp), placement/decode signature; seed, moves, lineage, schedule/finish parameters, exact-best provenance.
- Audited original finished board and audit verdict; Q3/W/C/S/length, diagonal/crossing counts, hard failures, separate strict versus research classification.
- Future exact-checkpoint type additionally stores full native/TS loop state and RNGs; warm-start need not restore a completed loop's hidden state.

Suggested workspace: existing project/budget/debug scoped Work paths, `saves/seed_XXXX.sav` per strict survivor, separate research pool for eligible near-misses, not one global cross-project folder. Keep existing CSV workflows and champion JSON/SVG. All strict Pass One survivors remain eligible for Pass Two per owner instruction; research pool size/diversity may be bounded (proposed 16–32 parents across seeds for pilot, not a cap on strict survivors). Save atomically, never silently overwrite parent on regression. Existing Q3 CSVs without genomes cannot magically warm start; replay under compatible engine or keep import-only.

## 6. Experimental protocol and scoring

Q3 remains construction metric, separate from native energy and electrical/physical qualification. Native wires preference selects wWire=16, wCut=0.01 in TS; cuts preference 1 and 0.25. Knife/between-cut penalty is separate. C area 0.35/cell, length 0.4/hole-unit, final slant/cross penalty 400. Q3's W:C cost ratio is 0.24:0.16; Q3 also includes exact max stack depth. Native energy is not Q3. Arbitrary weight tuning needs a small TS/CLI change; defer until basic proof. Never discard a higher-Q3 strict parent merely because a child has lower native energy.

- Test reheat T0 candidates 0.15, 1, 3, 8, 20, 50 and fresh T0=150 control. These are hypotheses. T=1 and 0.15 differ for small energy changes even if both rarely accept +16.
- Normal mess penalty ramps 25→400. Proposed repair arm `rampStart=400` holds it flat at 400, strongly discouraging decoded slants/crossings throughout. Does not guarantee final router validity; decoder estimates and final routing differ.
- Cool to 0.15 over the child's own move count. Use separate experimental configuration.
- Preserve parent board and genome; strict Q3 ranks strict survivors (then standard W/C/seed tie breaks). Near-misses separately prioritise no hard faults, electrical completeness, distance to strict, then construction metrics/diversity; never promote crossings or diagonals to a build-ready record.
- Rank only actually finished and saved-audited results; native best energy is search guidance, not final elitism. Verify board lock and full audit. Keep multiple parent/child generations only when justified.

### Development gates (agreed direction)

1. **SAVE/LOAD** experimental implementation and versioned payload. No production GUI integration yet.
2. **Round-trip proof**: confirm saved genome dimensions, fingerprint and checksum; decode and compare H/W, energy, wires/cuts, slants/crossings, yI/xI and other required metrics. Then run full same finish and compare canonical actual board placements, wires, cuts and audit/Q3 (not just matching counts). Reject mismatches. Test several hundred diverse genomes if available; include electrically complete near-misses and strict controls (old Moto/Audio if V1.40 has none). Test wrong fixture, options, malformed/corrupt .sav and unavailable warm export. Claude volunteered to draft the detailed round-trip spec; not yet supplied.
3. **Default regression gate**: same seeds, same signatures/audit verdicts on unchanged default engine; use existing paired seed and headless suites. Freeze existing campaign/wager binary fingerprints. No runtime tests performed for this proposal.
4. **Small proof**: about 20 diverse eligible parents, 5k additional moves each, T0=8, flat 400; compare cold 0.15 control and fresh equal-move control. Preserve all parents. Predeclare success: reproducible strict improvement in Q3 where strict parent exists or improvement in distance to strict for eligible near-miss, no qualification regression in retained champion; report conversion to strict separately. Any improvement proves feasibility only, not superiority.
5. **Larger confirmation**: equal total anneal moves including discovery, compare actual wall/finish costs; fresh-only vs warm allocation (e.g. half discovery/half children), disjoint seed-block pipeline replicates, proposed ≥20, tune pilot blocks then untouched confirmatory blocks. Report best strict Q3, yield, time/moves to first strict, no-pass runs and distance-to-strict as separately predeclared endpoints, uncertainty/multiple-comparison correction if testing many arms. No automatic post-hoc endpoint switch. Do not require wall time/finish count to agree if the method genuinely changes overhead; measure and report.
6. Integrate only a verified winning approach into GUI Pass Two and later Grand Final. Existing Pass One strict/default rules unchanged until explicit approval. Existing GUI theme/dashboard and user consent workflow remain intact.

## 7. Immediate handoff

- Let current Mac ladder finish without rebuilding or editing the active solver. Obtain full CSV and manifest from owner when available; no asynchronous monitoring claimed.
- Analyse per-budget strict/diag yield, error rows, failure severity and joint qualification, exact incomplete-net identities via replay, and representative near-misses. Investigate standard vs Edge with matched seeds; document final results separately.
- Keep the independent 2,000 × 20k wager frozen and separate.
- Draft warm-start round-trip spec and isolated implementation plan before code changes. Owner has requested documentation, not implementation in this turn.

**No solver, GUI, fixture, scoring, campaign or wager changes made.**
