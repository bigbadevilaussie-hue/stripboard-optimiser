# Stripboard Optimiser — Version 2.00

**Release milestone:** Version 2.00 — Consolidation of Two Repositories (24 November 2026).

**Git version:** `v2.00` · **npm/package version:** `2.0.0`.

See [CHANGELOG.md](CHANGELOG.md) for release scope.

## Headless solver

**This repository is for the standalone optimiser, not a GUI or web application.**
The legacy Tk desktop application, Next.js editor, Django backend and deployment
configuration have been removed from the current branch. Git history retains
earlier versions if needed for archaeology; they are not part of this product.

## What remains

- Native C decoder and strip router: `src/frontend/components/stripboard/v5wasm/`
- TypeScript placement, routing, finishing and wire-polish engine:
  `src/frontend/components/stripboard/` (headless modules only)
- Node.js native/strict solver CLI: `src/frontend/tests/solver/v5Solve.js`
- Independent saved-layout validator: `src/frontend/tests/solver/auditSavedStrict.js`
- Python benchmarks, JSON auditing, speed probes, seed sweeps and qualification
  scripts: `scripts/`
- Versioned circuit/footprint test inputs: `test-fixtures/`
- Standalone, non-browser SVG board and schematic renderers:
  `src/frontend/standalone-renderer/`

The `src/frontend/` directory name is retained **only to preserve solver
script paths**. It no longer contains a frontend application.

## Install / compile

Requires Node.js, npm, Python 3 and Clang. From repository root:

```sh
cd src/frontend
npm install
npm run build:solver
npm run build:native
npm run build:native:edge
npm run build:renderers
```

The former web-application package lock was removed because it included Next.js
and other GUI dependencies. `npm install` generates a new headless lockfile
locally; commit that regenerated lockfile when the dependency install is verified.

## Native solver and strict verification

Example invocation (from `src/frontend/`, after the builds above):

```sh
node tests/solver/v5Solve.js --data /path/to/input-folder --id 1 --seed 37 --moves 500000 --native 1 --strict 1 --drilled 0 --nostack 0 --wire-polish 1 --routing-preference wires --save /path/to/output.json
```

The input folder contains `projects/1.json`; the original is never overwritten
by the CLI. Use `--drilled 0` for knife cuts allowed and `--nostack 0` for
stacked jumpers allowed. Board rows/columns are locked by the input project's
`board.lockedRows` and `board.lockedCols`, not by a GUI.

```sh
npm run test:solver
npm run test:board
node tests/solver/testAuditSavedStrict.js
```

The independent audit takes a saved JSON and the *prepared input* used in
the original run:

```sh
node tests/solver/auditSavedStrict.js /path/to/candidate.json /path/to/input/projects/1.json
```

### MOTOEX winner-ladder results

The saved 500k/seed-37/USB-column-23 board was independently verified on the
user's iMac at **27 wires / 43 cuts**, 24×56 board, with six explicitly permitted
stacked jumpers and no reported body-overhang warnings. The output remains
on the user's Desktop; **saved sweep outputs are not stored in Git**.

To independently requalify archived candidates without another anneal:

```sh
python3 scripts/requalify_motoex_winner_ladder.py
```

See `docs/motoex-seed37-winner-ladder-2026-11-24.md` for the exact original
reproducible experiment and archive locations.

## Standalone SVG renderers

From `src/frontend/`, after `npm run build:renderers`:

```sh
node standalone-renderer/dist/standalone-renderer/cli.js /path/to/project.json --output /tmp/board-render
node standalone-renderer/dist/standalone-renderer/schematic/cli.js /path/to/project.json --output /tmp/schematic-render
```

These produce `board-top.svg`, `board-copper.svg` and `schematic.svg`.
No browser, web server, Tk, Next.js or Django process is required.

## Development policy

Maintain independent validation of electrical opens/shorts, component-body
crossings, jumper direction, physical pin/cut/wire bounds, and 24×56 lock
contracts as applicable. **Stacking and drilled-only are optional constraints,
not universal validity rules.** Package-only overhang is an advisory warning.
Keep the native CLI and renderer buildable as standalone utilities.

Historical solver notes live under `docs/`. They describe experiments and
may mention the now-removed desktop and web applications.
