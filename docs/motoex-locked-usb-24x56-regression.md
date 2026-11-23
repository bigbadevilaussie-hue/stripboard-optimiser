# MOTOEX — fixed 24×56 / overhanging locked USB regression

**Source:** `test-fixtures/masters/moto/motoex.json` committed by the user at local commit `744c284` and now visible on GitHub main. This is the source of truth, not the older MOTO board.

## What the actual JSON contains

- Project name: `Moto-Mate V 1.00 (copy)`.
- Original canvas is **99 rows × 500 columns**, `lockedRows=true`, `lockedCols=false`. These are **not** the requested test dimensions.
- **45 components**, **123 netAssignments**, **10 `offBoard` components**.
- Component labelled **USB**, ID `8cee7751-5442-4b06-aaff-7af39f032ec3`, is the **only placement lock retained in the test**.
- Its custom footprint `USB Charger` is **6 columns × 13 rows** in its current rotation 0; locked origin **row 13, column 47**.
- On a board of **rows 0–23, columns 0–55**, USB body occupies **rows 13–25 and columns 47–52**, hence **2 rows of body overhang** below the physical edge. This is intentional, **not** two missing rows to add to the board.
- USB electrical pins `IN+` and `GND` have offsets `(0,0)` and `(0,5)` and thus remain on board: at **(13,47)** and **(13,52)**.
- Another part, **TVS**, has `locked=true` and `boardPos=(2,2)` in the original source; this test specifically clears that lock and all other existing placements. The original JSON is never modified.

## Contract

`scripts/test_motoex_usb_lock.py` produces a temporary **24×56**, **rows locked**, **columns locked** input containing the full original electrical netlist, component definitions and off-board assignments. It discards all existing on-board placements except USB, retains USB's full source identity and rotation, and removes every other part's `locked` key. On any candidate it independently checks:

1. **Exact 24×56 output**, with both board dimension locks retained. **26×56 is failure**, even though the USB body reaches row 25.
2. USB ID, locked status, `boardPos=(13,47)`, `rotation=0` unchanged.
3. No other part re-locked; all source component IDs preserved; footprints, nets and netAssignments unchanged.
4. Native CLI `--strict 1` must report `strictValid=true` with exit 0 (electrical shorts/opens, physical geometry, vertical jumper rule, lock dimensions, and optional drill/stack rules checked by the CLI). A strict exit 2 remains **diagnosable** and saves the layout, but **does not count as passing**.
5. Every seed gets a saved board and stderr log; an unplaceable or oversized candidate is recorded as an explicit failure. The benchmark does **not** silently expand the board or relabel a failure as passing.

**Important:** the solver's existing geometry checker may currently count the USB overhanging body as out of bounds and the finishing logic may expand the physical board to fit it. This adversarial test is designed to *expose* that behaviour, not weaken the checks. A future solver change must allow an explicitly mounted edge-overhanging locked component **only when all electrical pins and legal connection holes remain on the 24×56 board**, without ignoring overlaps or shorts.

## Run on the iMac

No source, netlist or WR files are touched. The command below compiles only the existing TS CLI and runs the checked fixture for three native seeds with drilled-only, no-stacking and the normal solver:

```bash
cd ~/Documents/stripboard-optimiser && \
set -o pipefail && \
{
  git pull --ff-only origin main &&
  python3 -m py_compile scripts/test_motoex_usb_lock.py scripts/tests/test_motoex_usb_lock.py &&
  PYTHONPATH=scripts python3 -m unittest discover -s scripts/tests -p 'test_motoex_usb_lock.py' -v &&
  (cd src/frontend && npx tsc -p tests/solver/tsconfig.json) &&
  python3 scripts/test_motoex_usb_lock.py --moves 20000 --seeds 3 \
    --drilled --nostack \
    --out ~/Desktop/motoex_locked_usb_24x56_v1
} 2>&1 | tee ~/Desktop/motoex_locked_usb_24x56_v1.log
```

Test exit 0 means all requested seeds passed **every** gate; exit 2 means one or more seeds failed, with detailed reasons under `results.json`, and exit 64 denotes input/test setup failure.

Inspect `~/Desktop/motoex_locked_usb_24x56_v1/results.json` plus the saved `motoex_seed_*.json` for the exact failure. To compare the opt-in faster **same solver**, run separately with `--fast` and a *fresh* `--out`, after building `npm run build:native:fast`.

```bash
cd ~/Documents/stripboard-optimiser/src/frontend
npm run build:native:fast
```

At this stage this commit **adds a regression test, not a claim that MOTOEX already passes**. The original WR evidence remains unchanged.


## First executed native regression — 24 November 2026 (FAILED, as intended)

The user's iMac passed all **5 fixture/preparation contract unit tests**; then ran:

```bash
python3 scripts/test_motoex_usb_lock.py --moves 20000 --seeds 3 --drilled --nostack --out ~/Desktop/motoex_locked_usb_24x56_v1
```

The original master SHA256 was `e078b01bd5e563f0b9cd37289143e7fa7000a36a8b8a90d9474ce70b6f6d4bae`. The fixture preparation printed 45 parts, 123 assignments, 10 off-board components and a single locked USB at (13,47), rotation 0, footprint 6×13.

| Seed | Actual finished board | Wires | Cuts | Strict failures |
|---|---|---:|---:|---|
| 1 | 26×56 (**wrong**) | 45 | 62 | `QUALITY_3`, `INCOMPLETE_3`, `NONVERTICAL_5`, `SLANTED_4`, `CROSSINGS_13`, `SOLVER_ISSUES`, `LOCKED_ROWS`, `KNIFE_10`, `STACKED_5` |
| 2 | 26×56 (**wrong**) | 43 | 60 | `QUALITY_3`, `INCOMPLETE_3`, `NONVERTICAL_2`, `SLANTED_2`, `CROSSINGS_3`, `SOLVER_ISSUES`, `LOCKED_ROWS`, `KNIFE_12`, `STACKED_2` |
| 3 | 26×56 (**wrong**) | 49 | 63 | `NONVERTICAL_2`, `SLANTED_2`, `CROSSINGS_4`, `SOLVER_ISSUES`, `LOCKED_ROWS`, `KNIFE_5`, `STACKED_3` |

**0/3 passed.** Solver outputs were saved, not accepted. Crucially, **seed 3 has no `QUALITY` or `INCOMPLETE` failure**, showing that dimension and physical-routing compliance are not simply side effects of an electrically incomplete placement. **Do not treat the 26×56 result as a successful 24×56 layout.**

### Root causes confirmed in source (distinct from timing speed work)

1. `v5wasm/decode.c`: the decoder's size measurement uses `H = max(H, y + geoH)` for **every rigid part**, including a locked part whose *body* deliberately overhangs; its `lockOver` term therefore sees two extra rows. The electrical USB pins themselves remain within 24×56.
2. `layout2/finish.ts` (router finish): `H = Math.max(padded.rows, lockedRowsCap)` sets a **minimum**, not a maximum. Later `rows = Math.max(lockedRowsCap, maxR + 1)` repeats the enlargement. Thus a locked footprint body reaching row 25 produces **26** rows even when only 24 are permitted.
3. `layout2/finish.ts` (repair finish): the repaired route also uses the decoder's expanded skeleton/wiring geometry, so merely changing one router-finisher formula is insufficient.
4. **Separate routing violations:** the final plans still have nonvertical jumpers, crossing/stacked wires and knife cuts even with `--drilled 1 --nostack 1`. The strict CLI correctly catches them; the CLI flags are not proof the solver generated a compliant board.

**Engineering constraint:** a mounted, locked edge-overhanging rigid body's *unpopulated footprint cells* may lie outside the physical board; **every pin, copper strip, cut, jumper endpoint and conductor must still lie within 24×56**. A fix must not clip or silently delete wires/cuts or hide shorts/opens. Board clipping by changing a final `rows` field alone is NOT a valid fix.

**Next implementation scope:** make the physical board dimensions a separate, immutable locked-frame constraint in the decoder and both finishers, while retaining the full overhanging locked package body as a collision obstacle; route copper only inside that immutable frame. Then test independent electrical and clearance validation and the original MOTO/AUDIO baseline fingerprints before promoting. This is a core constraint/geometry change, not a compiler speed tweak. The five unit tests establish fixture preparation and diagnostic gates only; they do not establish a successful solve.
