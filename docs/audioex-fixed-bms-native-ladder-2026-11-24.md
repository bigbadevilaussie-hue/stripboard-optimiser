# AUDIOEX fixed-BMS native ladder (24 November 2026)

**Goal:** solve the previously unbuildable AUDIO board with the BMS
physically fixed for the case, its plastic package overhanging the *top*
edge. No GUI work; all optimization uses the existing Karl native C +
TypeScript CLI and its independent saved-board checker.

## Ground-truth fixture and prepared input

Source: `test-fixtures/masters/audio/audioex.json` (Git original never
overwritten). Verified 19 components, 29 nets, 85 assignments and 24×56
board locked in both directions. The source has four pre-existing cuts and
one locked BMS at **row -2, column 24**, rotation **0**; eight BMS electrical
pins are all within rows 2..9 of the physical board.

The original JSON does **not** spell out `edge` or `slide`, so the
isolated **prepared** input snapshot explicitly sets:

- BMS: `locked=true`, `edge=true`, `slide=false`.
- Position/rotation: `boardPos={row:-2,col:24}`, `rotation=0` — **never move**.
- 24×56 board: `lockedRows=true`, `lockedCols=true`.
- Body-only overhang is permitted; electrical pins and copper must stay
  on the physical board. Any anchor movement or failure to retain the
  edge/slide flags disqualifies the candidate.
- The native CLI deliberately **clears incoming cuts and wires** before
  routing. The four existing cuts remain in the untouched source
  `original_audioex.json`, but are not treated as immutable cuts by
  the solver. The isolated prepared CLI input sets `cuts=[]` and `wires=[]`.

The runner refuses an unexpected source BMS position, a sliding BMS, a
changed pin footprint or a second locked part. It does **not** falsely
claim the original BMS was flagged `edge=true` in Git.

## Native solver configuration

**Drill OFF** = `--drilled 0`, so knife/between-hole cuts **allowed**.
**Stack ON** = `--nostack 0`, so insulated vertical jumper overlap allowed.
Native `--strict 1`, `--native 1`, `--routing-preference wires`.
Use the explicitly **edge-enabled decoder** built by
`npm run build:native:edge` (env `V5_NATIVE_LIB_DIR` points at its
native shared library). Router is normal native router.
`--drill-domain 0` and `--wire-polish 0` so experiments are comparable
to the baseline search and no untested post-processor changes ranking.
Use `tests/solver/auditSavedStrict.js` after every saved candidate to
independently check locked board, unchanged component IDs/definitions and
net assignments, electrical completion and shorts, pins/cuts/wires,
verticality, geometry and wire-body crossings. Body-only overhang is a
warning, not an automatic rejection.

**Run schedule:** ten independent seeds (1..10) per budget:

- **Pass A:** 5k, 10k, 15k, …, 50k (5k step, 10 budgets).
- **Pass B:** 100k, 125k, 150k, …, 500k (25k step, 17 budgets).
- **Total:** 27 budgets × 10 seeds = **270 independent trials**.
- Each budget starts a fresh solve; this is **not** a warm-start continuation
  of a previously solved layout.

## Root cause and opt-in decoder repair — 24 Nov 2026

The first AUDIOEX campaign completed **270/270** but returned
`UNSOLVED_NO_FEASIBLE_PLACEMENT` for every seed, 0 qualified layouts.
The source BMS has a **negative fixed anchor** (row -2), which triggered an
impossible graph in native `decode.c`: the ordinary source-edge constraint
`y >= 0` and the BMS's locked equality `y == -2` cannot both hold.
The X graph had the same issue for left-edge mounts.

The native fix skips the zero-origin lower bound **only** for an explicitly
locked, rigid, opt-in Edge-mount part when its locked axis value is negative.
It is compiled **only** into `npm run build:native:edge`; standard native
and WASM code paths retain their original zero-bound semantics.
Locked placement, physical board dimensions, on-board pins/cuts/wires,
collision checks, and the independent saved-board auditor are unchanged.

**Do not resume the 270 archived failures after changing the binary.**
The runner prevents this by comparing native SHA-256 fingerprints. Preserve
`~/Desktop/audioex_bms_fixed_native_ladder/` as evidence. First run a
targeted native regression and a single-seed smoke into a **new output
directory**. A successful decode is **not** yet a strictly routed pass.

## Second stage — finished-board physical gate (24 Nov 2026)

A single 5k smoke with the edge decoder fixed advanced from
`NO_FEASIBLE_PLACEMENT` to **`NO_PHYSICAL_FINISH`**. Investigation found
a second generic validator mismatch in `autoLayout5.ts`:
`physicalFit()` rejected **every** negative component anchor, even when
that part was explicitly `locked + edge` and the body alone overhung the
purchased 24×56 PCB. The isolated C decoder had already placed it legally.

The fix exempts only a rigid explicitly locked Edge part **at its
unchanged locked position and rotation** from the anchor-in-bounds test.
All actual pin positions, copper cuts/jumper endpoints, board dimensions,
and ordinary component bounds remain checked. The saved-board auditor
still requires unchanged net assignments and the exact locked BMS.

**Regression:** `node tests/solver/testNativeNegativeEdgeFinish.js`
invokes a real native solve on a BMS-only AUDIOEX-derived project, verifies
it does not return either UNSOLVED sentinel, and verifies the original
negative BMS anchor is preserved in the saved JSON. This is intentionally
not proof that the **full** AUDIOEX board routes successfully.

Previous rejected folders are immutable evidence. A fresh smoke needs a
**new** output folder:
`~/Desktop/audioex_bms_edgefix2_smoke`. Do not resume or overwrite
`audioex_bms_edgefix2_smoke` or `audioex_bms_fixed_native_ladder`.

## Mac commands

From repository root, after `git pull --ff-only`:

```sh
cd ~/Documents/stripboard-optimiser/src/frontend
npm run build:solver
npm run build:native
npm run build:native:edge
node tests/solver/testNativeNegativeEdgeAnchor.js
node tests/solver/testNativeNegativeEdgeFinish.js
cd ../..

PYTHONPATH=scripts python3 -m unittest scripts.tests.test_audioex_native_ladder -v

# New isolated archive (do NOT overwrite the original 270 rejected runs):
python3 scripts/run_audioex_native_ladder.py --jobs 4 \
  --out ~/Desktop/audioex_bms_fixed_native_ladder_edgefix2
```

Default archive remains `~/Desktop/audioex_bms_fixed_native_ladder/`,
but that contains the **old 270 rejected attempts**; use
`~/Desktop/audioex_bms_fixed_native_ladder_edgefix2/` for the repaired native
build. If an
existing run is interrupted, **do not delete the folder**:

```sh
python3 scripts/run_audioex_native_ladder.py --jobs 4 --resume \
  --out ~/Desktop/audioex_bms_fixed_native_ladder_edgefix2
```

Optional small verification without entering the full campaign:

```sh
python3 scripts/run_audioex_native_ladder.py --jobs 1 --seeds 1 --moves 5000 \
  --out ~/Desktop/audioex_bms_edgefix2_smoke
```

**Do not** run a different `--moves`/`--seeds` set in the same archive;
resume checks the source/prepared-input SHA-256, flags, schedule and
native binary fingerprints. For a modified schedule choose a new `--out`.

## Outputs and qualification

- `manifest.json`: source, preparation, seed/budget policy and hashes
  of CLI, auditor, decoder, router, addon and compiled solver.
- `input/projects/1.json`: immutable prepared campaign input.
- `original_audioex.json`: copy of the original Git fixture.
- `jobs/moves_XXXXXX_seed_YYY/`: exact input, stdout, stderr and
  independent audit logs for each attempt.
- `passed/`: **every** independently qualified JSON, even if it misses
  top five. Never discard distinct successful trials.
- `rejected/`: saved invalid/rejected JSONs for forensic review.
- `results.jsonl`: durable per-attempt checkpoint, including strict
  failure reasons and independent-audit findings.
- `results.csv`, `passed_index.jsonl` and `summary.json`: ranked
  metrics and failure distribution, refreshed during the campaign.
- `top5/`: up to **five distinct best qualified** physical layouts,
  ranked by wires, cuts, jumper length and cost.
- `champion.json`: best qualified candidate, only if one exists.

The runner records a **PASS** only when all of the following hold:
native CLI returns exit 0 with `strictValid=true`, the original BMS
anchor/rotation/flags are unchanged, both board locks and dimensions are
unchanged, and the saved-board auditor returns `valid=true` with exit 0.
CLI exit 2 is a rejected candidate, **not** a crash. No candidate becomes
strictly qualified simply because it has fewer wires.

An archive of tests **does not** certify case clearance mechanically:
the body overhang is explicitly permitted, but the case fit still
requires a physical build check. No performance or survivor count is
claimed until the ladder actually runs on the iMac.
