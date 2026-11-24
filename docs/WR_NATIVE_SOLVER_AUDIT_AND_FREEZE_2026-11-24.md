# Native solver audit and WR freeze protocol — 24 November 2026

## Scope / decision

Retain the native decoder and existing strict auditor. Do not replace them with Route-Mate. The currently witnessed 20k original-audio.net drilled-only test passed **3 of 50** seeds (6: 12W/40C; 26: 13W/41C; 32: 19W/47C). AUDIOEX fixed-BMS 25k baseline has 85 passing seed IDs, champion seed 1575 (13W/47C, construction score 69.03). Those are independent experiment observations, not a general success-rate guarantee.

**Solver core remains unchanged by this audit.** The WR freeze is conditional on replay and independent strict audit, not automatic upon writing this document.

## Source findings, in order of priority

1. `layout2/finish.ts` finalises layouts after a `Chooser` that ranks by electrical problems, wire mess and construction cost; `layout2/chooser.ts` calls `deriveCompletion`. In drilled mode, `deriveCompletion` is still allowed to produce between-hole cuts, later penalised and converted opportunistically. An unsuccessful conversion can survive final selection. `autoLayout5.ts` `finalize` chooses the router or repair by score and special-case physical edge fit, not complete strict construction eligibility. The CLI and independent auditor catch and reject illegal boards. A strict candidate-choice change requires A/B regression: rejection alone does not increase valid output.
2. `cutPlanning.ts` `upgradeCutsToDrills` only tests the two holes immediately adjacent to each between-hole cut. It does not explore the full electrically equivalent cut interval or reroute wire endpoints. `tidyScore.ts` `avoidableBetweenCuts` excludes only between-cuts with pins on both flanks; **avoidable is a heuristic classification, not proof a valid drilled conversion exists**. Saved seed 12 has a between-hole cut at row 15,col 13 and wire endpoints near that cut; seed 34 at row 2,col 27. No evidence yet proves either is convertible without a reroute.
3. `decode.c` uses `W_LOCKOVER=5000.0`, while `layout2/boardPrice.ts` declares `W_LOCKOVER=150`. This is a concrete divergence in nominally aligned objectives. Both are *soft search penalties*. The special locked-edge native feasibility ratchet only applies to explicit locked edge mounts, while final CLI strict board-size checks apply more generally. Do **not** change this coefficient just before WR runs: changing it alters native anneal trajectories; first compare feasibility and passing seeds on identical seed sets.
4. Normal and experimental routing distinguish electrically connected candidates from physically legal ones. The 50 original-audio.net Drill ON experiment produced 47 rejected boards, usually with nonvertical wires, crossings or prohibited knife cuts, although their reported incomplete/conflict counts were zero. This establishes the search-to-finish physical gap; it does not prove one root cause.
5. The locked AUDIOEX BMS (row -2, col 24) has adjacent pads at board row 9 cols 26,27,28. The existing electrical model treats those pads as separate floating terminals; hence pure drilled-only isolation at that locked orientation is impossible without sacrificing a pad. Do not make that a WR drilled-only benchmark. The legitimate WR case is knife-capable/drill-preferred **only after hybrid support and independent validation**.

## What may be frozen and what cannot

- The physical board dimension / component lock and strict electrical, geometry, vertical-wire, crossing and cut-mode acceptance criteria **must be hard** at delivery.
- The annealer may temporarily visit over-cap states to reach a feasible locked board; outright banning every intermediate overflow without proof can trap the search. Distinguish a search transition from a qualified saved board.
- Keep `--wire-polish 0`, `--drill-domain`, `--drilled`, native artifacts, board fixture and score formula explicit in manifests. An A/B that changes a flag is **a separate contender**, not the frozen baseline.
- Freeze by Git commit **and** SHA-256 of compiled native/WASM outputs, fixtures and strict auditor. A Git hash alone does not freeze local compiled binaries. Never conflate old `audioex.json` and the original `audio.json` / `audio.net`.

## Required freeze gate

Run `python3 scripts/wr_solver_freeze_gate.py` after pulling the latest Git changes. It does not edit solver sources; it performs four short CLI solve-and-audit replays into a new archive folder:

- Original audio.net-compatible audio.json, Drill ON / drill rotation domain ON / 20k: seeds 6,26,32. Require strict pass, exact wires/cuts and original saved-layout signatures.
- AUDIOEX fixed-BMS, Drill OFF / drill rotation domain OFF / 25k: seed 1575. Require strict pass and originally witnessed 13W/47C.

Any failed test means **do not freeze**. Inspect native artifact hashes, flags, fixtures and routing logs. Only after the gate passes, make an annotated Git tag, pin the compiled outputs and record the gate manifest. The exact AUDIOEX layout signature has not been recovered from the complete baseline, so that comparison is limited to strictness and wire/cut counts; preserve its original champion JSON separately.

## Proposed WR campaign after verified freeze

**Pass 0 — provenance:** Preserve original fixtures and champion boards, baseline 25k results, Git source SHA, compiled binary hashes, original 100-point construction-score formula and strict audit. Capture flags per run. No mutable Desktop output.

**Pass 1 — exploration:** Fixed seed range 1..2000 (extend only as a new labelled batch), 25,000 moves per seed, 3 workers; AUDIOEX 24×56 BMS (-2,24), stacking ON, Drill OFF/knife-capable, strict and independent saved-board auditing. Preserve **every** strict-passing JSON plus every failed result record, per-seed duration and progress emojis. The 85 passing seed IDs from the completed 25k baseline are a valid frozen point of comparison; do not silently discard older qualifying boards or infer full new-run equivalence.

**Pass 1 qualifying rule:** No electrical/physical violations, no invalid cuts, locked board/part unchanged, no nonvertical wire or crossing. All strict qualifiers advance, not merely top 20. Rank valid boards on the existing 100-point score, then wire/cut counts, jumper length, placement usability; use layout signatures to identify duplicates but retain provenance.

**Pass 2 — survivor challenge:** Every Pass 1 qualifier gets a larger budget *as a new labelled solve* (e.g., 100k then 250k, subject to benchmarking). **Important:** simply running the same seed at more moves is a fresh anneal trajectory, not a continuation from the saved board. Preserve each earlier winning JSON and compare the challenge result against it. A genuine warm-start/continuation pass requires separate verified support; do not pretend a reseed is warm-start. Never let an inferior/non-strict result overwrite a champion.

**Grand final:** Independent saved-board audit of top distinct boards, manufacturing usability review (drilled holes consume solder points, knife cuts preserve both adjacent points), optional circuit-specific electrical quality check, champion/layout SHA capture, completed timing/diagnostic report. Separate drilled-only open-audio contests from locked AUDIOEX knife-capable contests.

## Engineering backlog (do not change frozen contenders midcampaign)

1. Test candidate eligibility at the router-vs-repair choice with paired fixed skeletons, to prove whether a strict-valid alternative is being ignored.
2. Instrument `drillRemainingCuts` for each rejected cut: available flanks, blocked reason, wire endpoint occupancy, and alternatives considered. Do not interpret `avoidableKnife` as a proof.
3. Test whether the C/TypeScript lockOver scoring divergence affects successful fixed-board search (equal moves/seeds, both binary builds separately labelled).
4. Explore constrained cut sliding / landing-hole reassignment only with independent electrical re-verification. Do not simply re-tag a knife cut as a drilled hole.
5. Explore a small fixed-placement reroute matrix before broad algorithm changes.

Acceptance standard: statistically better *independently verified* strict-pass rate and better retained champion quality, at comparable compute/time, with no regression on all four freeze-gate winners.
