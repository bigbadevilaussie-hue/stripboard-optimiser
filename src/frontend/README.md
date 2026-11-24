# Stripboard Optimiser — Frontend and native solver

This directory contains the inherited **Next.js** stripboard web editor plus the C/TypeScript v5 solver, native Node.js test harness, standalone renderer, and experimental general-purpose physical routing improvements.

**Current engineering handover (24 November 2026):** [START HERE — native solver](../../docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md). Also read the [root README](../../README.md), [project specification](../../project.md), and [native Edge/Slide implementation](../../docs/native-edge-slide-motoex.md).

## Current development status

- **Normal editor:** `npm run dev`; runs the inherited Next.js app. Do not infer it uses current experimental native Edge/Slide features.
- **Standard native solver:** `npm run build:native` builds `libv5decode.so`, `libv5route.so` and `v5native.node`. The portable `tests/solver/native/buildAddon.js` locates macOS/Linux Node development headers (on the user's Mac, `/usr/local/include/node`).
- **Experimental native Edge decoder:** `npm run build:native:edge` builds **separate** `tests/solver/native/build/edge/libv5decode.so`, with `V5_EXPERIMENT_EDGE_MOUNT`, `FAST_GRID_CLEAR`, `FAST_IDENTICAL_GENOME`. It does not overwrite the normal native decoder or browser WASM.
- **Solver CLI:** `tests/solver/v5Solve.js`; ordinary controls include `--data DIR --id N --seed N --moves N --native 1 --strict 1 --drilled 1 --nostack 1 --routing-preference wires`. Experimental flags: `--drill-domain 0|1` to opt out/in of the generic adjacent-different-net pin rotation exclusion and `--wire-polish 0|1` to opt in to fixed-board local wire/cut polish. Strict-invalid output exits 2; this is a completed *failed route*, not a process crash.
- **MOTOEX test controller:** `../../scripts/run_motoex_native_edge_slide.py`; the fixture stresses a purchased **24×56 locked board**, on-board GPS, and USB body allowed to overhang two rows. Source fixture `../../test-fixtures/masters/moto/motoex.json` remains immutable. Current controller slides the USB via independent fixed-column runs, **not** via a native annealer mutation.
- **General-purpose route polish:** `components/stripboard/wireColumnPolish.ts` is now integrated as an **optional** post-finisher for both locked dimensions. It searches alternative vertical jumper columns on unchanged copper groups and safely replaces between-cuts with drill holes when possible; it must independently preserve electrical completeness, avoid shorts, and avoid adding crossings, stacks, or knife cuts.
- **GUI status:** The newer native experiments are not established as integrated into the desktop Tk GUI or the inherited Next.js editor; GUI transition is deferred.

## Rebuild and test (from `src/frontend`)

```sh
npx tsc -p tests/solver/tsconfig.json
npm run build:native
npm run build:native:edge
node tests/solver/testDrilledRotationDomain.js
node tests/solver/testKnifeCutAudit.js
node tests/solver/testWireColumnPolish.js
```

**Latest Mac evidence:** native builds and the first two synthetic tests previously passed. The first `testWireColumnPolish.js` attempt failed *before its tests* because the test did not install the existing `@/` alias hook. The bootstrap was fixed in Git commit `b6aae85`, **not yet rerun on the Mac** as of this README. Check the real output before treating the new polish as validated.

### Inspect or polish saved candidates without reannealing

```sh
node tests/solver/inspectSavedCuts.js /path/to/saved-project.json
node tests/solver/inspectNetCorridors.js /path/to/saved-project.json --net net6
node tests/solver/polishSavedLayout.js /path/to/saved-project.json --out /path/to/new-polished-copy.json
```

The last command prints independent before/after quality checks; its output **must not overwrite input**. A separate synthetic test verifies stacking, knife-hole release and slant correction, but real saved-layout replay remains to be measured. Net names are command-line arguments for diagnostics, never solver hard-codes.

## Reproducibility and validation rules

No MOTOEX/GPS/USB names, net6 or preferred component rotations in generic search logic. Derive restrictions from actual pin geometry, net assignments, copper topology, user drill/knife preference, and allowed mechanical rotations. An in-bounds placement or `Q0` is not equivalent to a strict solved board. A strict candidate must have **zero electrical conflicts and opens, zero illegal component geometry, no nonvertical or crossing or stacked jumper wires, no knife cuts when drilled-only, and exact locked dimensions**. Empty no-fit results report explicit `UNSOLVED` reasons.

The verified 20k col25 native Edge A/B signature with drill-domain OFF is `e69806eb68fc` (matches the original hard-lock baseline). With the domain ON, first physical fit was move 1,194 / 77ms, no incomplete nets, but many route violations. User-supplied 500k comparisons are in the [handover](../../docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md). Neither column 25 nor 41 has a confirmed strict physical PASS.

## Running the inherited Next.js app

```sh
npm install
cp .env.local.example .env.local
npm run dev
```

The development editor is usually at `http://localhost:3000`; the Django backend is configured separately under `../backend`. Set real local environment variables outside Git. Refer to the root README for original/editor/deployment details. For native solver work, use the CLI harness and handover rather than assuming the web GUI is current.
