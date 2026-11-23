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
