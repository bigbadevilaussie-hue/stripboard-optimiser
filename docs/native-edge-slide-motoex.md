# MOTOEX native Edge + Slide — implementation and iMac test

**Status: opt-in feature branch, not yet verified on the user's iMac.** No WR or default build was changed.

## Real fixture and required semantics

The canonical `test-fixtures/masters/moto/motoex.json` source is a 99×500 working canvas. The test makes a copy with the purchased board fixed at **24×56** (both dimensions locked). It removes all non-USB locks, including the TVS, and clears all other old placements.

USB is a **6-column × 13-row** rigid charger, locked at **row 13, column 47**, rotation 0, pins at **(13,47)** and **(13,52)**. Its plastic occupies rows 13–25, overhanging the board's bottom by two rows. Those two body rows must **not** become new PCB rows or trigger an over-board body collision, but the body still blocks other parts and wires *within* the physical board. USB pins, all copper, all cuts and all wire endpoints must stay within 24×56.

- **Edge=no / Slide=no:** old exact locked footprint rule (expected 26×56 error for this case).
- **Edge=yes / Slide=no:** same original row/col/rotation; external body overhang permitted, electrical and physical routing strict.
- **Edge=yes / Slide=yes:** search **every one of the 51 bottom-edge columns 0..50**, starting col 47 and checking nearest neighbours first. Row 13 and rotation 0 never change. Each candidate invokes **the same native C Karl solver** with USB locked in the candidate position. Stop at the first *strictly compliant* board, not the first merely fitting placement. If none succeeds, report all 51 separate failures.
- **Edge=no / Slide=yes:** invalid combination.

Route-Mate already collects the three boolean fields `locked`, `edge`, `slide` in `gui/main.py`. The native feature follows its external search-controller approach instead of building a new optimiser. Route-Mate's `debug_slide.py` supports body overhang and fixed perpendicular position. Its current `edge_slide_positions()` implementation incorrectly rejects an edge component when its body height exceeds board height; the native controller explicitly handles the MOTOEX overhang instead.

## Native integration (same ABI, opt-in)

`autoLayout5.ts` checks all electrical pins on-board, requires both board dimensions locked and a legitimate edge-mount. Its existing decoder side-mask slot uses the sentinel `-2` for a locked rigid edge-mount; the side-mask is unused for locked components, preserving ABI and non-edge behaviour.

With `-DV5_EXPERIMENT_EDGE_MOUNT=1`, `v5wasm/decode.c` counts only the on-board part of the locked edge body towards PCB dimensions, and ignores only outside-board body-cell occupancy. Pin cells and on-board body collision checks retain their full strength. `layout2/finish.ts` likewise excludes only outside-board edge body cells from the final extent calculation. The strict native CLI additionally rejects outside-board copper cuts and wire endpoints.

`npm run build:native:edge` builds a separate experimental decoder at `src/frontend/tests/solver/native/build/edge/libv5decode.so`. It also enables the previously verified grid-clear and identical-genome speed shortcuts. It does not overwrite the standard native decoder, native router, browser WASM, CLI protocol or WR artifacts.


## Controlled comparison and physical cut diagnostics

The optional `--drill-domain 0|1` CLI flag (and fixture-runner `--drill-domain no/yes`) runs **the exact same opt-in native Edge decoder** with the generic drilled rotation domain disabled or enabled. The compiled `FAST_GRID_CLEAR` and `FAST_IDENTICAL_GENOME` flags remain identical for both arms. The default continues to be enabled in drilled-only Edge trials. This allows direct signature checks against earlier hard-lock runs without changing other anneal flags. A synthetic opt-out RNG smoke test is provided; a full 80-signature regression is **not yet measured** and must be checked against a preserved historical baseline rather than assumed.

The read-only generic cut auditor `tests/solver/knifeCutAudit.js` records the row and copper gap for each knife cut, nearest actual pins and their net names, whether two directly adjacent pins on different nets force that exact gap, plus pin/wire-endpoint blockers and two **possible** drilled flank candidates. These are explanations, **not** automatic proof that cutting a particular hole preserves routing; the actual cut upgrader has additional electrical and geometry checks. `tests/solver/inspectSavedCuts.js` can inspect existing saved JSON without rerunning any anneal; the strict fixture output also writes `knifeCuts` into `results.json` and logs each one.

The filter is disabled for patterned boards, whose copper is not necessarily horizontal. For unlocked `halfTurnOnly` rigid parts, the mechanical domain remains 0/180; if neither orientation is drill-safe, it must report infeasible rather than silently grant 90/270. Locked user placements are never rotated. No named component is exempted or hardcoded.

## Experimental generic drill-only rotation domain

The native Edge build now optionally enforces **a proven necessary drill-only condition** for **every rigid footprint**, computed solely from the model's existing rotated pin coordinates and assigned net IDs. If any two pins of **different nets** are in **adjacent holes on the same horizontal strip**, no spare hole exists to drill between them, so that orientation cannot be used when drilled cuts are mandatory. A pin without a net claims a private floating net. Adjacent pins on the **same assigned net** are not restricted by this condition. This is **necessary but not sufficient** for a clean route: cuts, starved pins and other nets still need exact electrical/physical verification.

There are **no named component, footprint, project or rotation exceptions**. In the opt-in native decoder, initial unlocked rotations are chosen from the admissible domain; mutation stays inside it; direct decoding of a disallowed/locked rotation fails immediately. Unrestricted rotations and half-turn moves retain their original RNG draw semantics where possible. The wrapper activates this only for `drilledCutsOnly` when the native setter is present; the production WebAssembly build continues unchanged until independently verified. The native addon must be rebuilt to expose the opt-in setter.

Strict trial reports include `invalidDrilledOrientations` for every residual routed part whose actual rotation has adjacent differing-net pins, with explicit adjacent pin/net pairs. This field is only a diagnostic and is empty for an unsolved placeholder.

Before running further MOTOEX seeds, validate on the Mac:

```sh
cd ~/Documents/stripboard-optimiser && git pull --ff-only && \
cd src/frontend && npx tsc -p tests/solver/tsconfig.json && \
npm run build:native && npm run build:native:edge && \
node tests/solver/testDrilledRotationDomain.js
```

Then compare one existing poor-rotation fixture (USB column 25, same seed/budget as baseline). The rotation-domain test uses synthetic parts, not MOTOEX-specific rules. If the domain check proves too aggressive or changes a previously legal solution, halt rollout and inspect the counterexample.

## Native diagnostic contract (post 500k MOTOEX runs)

The opt-in native Edge-Mount decoder records **firstFeasibleMove** (0 for an in-cap starting placement, otherwise the 1-based accepted proposal count) and **firstFeasibleMs** (wall-clock ms since the anneal walk started). Both are `null` when no in-cap placement is accepted. This uses previously unused C shared-memory slots; no standard WASM ABI or release route is changed.

In strict CLI JSON and each per-column `results.json` entry, an empty fallback has `unsolvedReason: "NO_FEASIBLE_PLACEMENT"` (no in-cap anneal result) or `"NO_PHYSICAL_FINISH"` (in-cap anneal but all finishes exceed physical bounds). Its `strictFailures` explicitly says `UNSOLVED_...`, rather than `QUALITY_1, CONFLICTS_1, INCOMPLETE_35`. Raw numeric metrics of the empty placeholder are not meaningful; **do not rank it as a poor routed board**.

On attempted, in-bounds routed boards, `incompleteNets` includes ID, real net name, disconnected pin groups and unplaced pins. `wireViolations` names each offending wire and its endpoints, possible net name(s) inferred from the connected copper group, crossing components and overlapping earlier wires. Net label `UNRESOLVED` means the verification graph did not associate it with a specific net and must not be silently guessed. A wire can have multiple categories; aggregate violation counts must not be added as if they were independent wires.

**Validation still required** on the iMac after pulling: compile TypeScript, rebuild the opt-in native decoder and run the focused 20k-move regression on column 25 (expect explicit `UNSOLVED: NO_FEASIBLE_PLACEMENT` if it never fits) and column 41 (inspect per-wire details). Then compare a 500k-move run to the previous signature, remembering that any accepted out-of-cap step now changes the trajectory intentionally. Do not launch another 51-position sweep until these diagnostics have been checked.

## Hard physical lock ratchet (post 51-position diagnostic)

The first 51-position, 20k-move sweep confirmed correct 24×56 placement for 47 positions, but columns **25, 18, 12 and 8** still returned 30×56, 27×56, 28×56 and 27×56. These columns are **not infeasible**, just failed attempts: do not prune them.

The opt-in C anneal now **starts with its existing soft overflow penalty** so that a tight initial genome may improve into the board. Once the first in-cap placement is accepted, overflow becomes a hard rejection for the rest of that walk. A running over-cap state can never be recorded as the returned best. The overflow-rejection branch consumes the same acceptance random draw an uphill proposed move would normally consume. Other projects and the old native decoder are unchanged.

The TypeScript seed collector rejects any initial/intermediate out-of-cap events. Both routed and repaired finish candidates must fit the purchased dimensions, every cut and wire endpoint must be within those dimensions, every pin must be on-board, and non-edge rigid bodies must fit fully. **It does not just rewrite a 30×56 result as 24×56.** If no physical fit survives, it returns an explicitly **UNSOLVED: LOCK_OVERFLOW** project at the original 24×56 dimensions, with no fabricated placed parts/cuts/wires. An invalid but in-bounds candidate can still be returned for diagnostic purposes; its strict failures must be preserved.

**Verification remains outstanding**: rerun the native C build, the standard tests, and a focused run on USB column 25. The expected result is either a real 24×56 routed candidate (possibly still electrically invalid) or an explicit UNSOLVED 24×56 project, never a larger board. The old 51-position sweep is evidence of the preceding bug, not proof the new ratchet passes.

## Run on the iMac

```bash
cd `/Documents/stripboard-optimiser
git fetch origin
git switch -c feature/native-edge-slide-motoex --track origin/feature/native-edge-slide-motoex

PYTHONPATH=scripts python3 -m unittest discover \
  -s scripts/tests -p 'test_motoex_native_edge_slide.py' -v
PYTHONPATH=scripts python3 -m unittest discover \
  -s scripts/tests -p 'test_motoex_usb_lock.py' -v

(cd src/frontend && npx tsc -p tests/solver/tsconfig.json && npm run build:native:edge)

python3 scripts/run_motoex_native_edge_slide.py \
  --edge yes --slide no --seeds 1 --moves 20000 \
  --out `/Desktop/motoex_native_edge_fixed_v1
```

The first run must finish **24×56**; a residual strict routing failure (knife, crossing, incomplete net) is separately reported and is not fixed simply by permitting overhang. Then run exhaustive Slide:

```bash
python3 scripts/run_motoex_native_edge_slide.py \
  --edge yes --slide yes --seeds 1 --moves 20000 \
  --out `/Desktop/motoex_native_edge_slide_v1
```

The controller writes one saved JSON per attempted USB column, plus per-attempt stderr and a detailed `results.json`. It stops only on complete strict electrical and physical success. A run that tries 51 positions without a strict pass **does not** prove impossibility; more anneal moves and seeds may be required.

**Do not merge this feature into normal native/WASM until the iMac compile/unit gates pass and real fixture runs establish at least correct physical board sizing.** Keep original AUDIO/MOTO parity and the historical WR evidence intact.
