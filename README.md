# Stripboard Optimiser — Version 2.00

**Release milestone:** Version 2.00 — Consolidation of Two Repositories (24 November 2026).

**Consolidation designation:** `2.00` (no Git tag published) · **npm/package version:** `2.0.0` · **Route-Mate GUI:** `2.04` (`gui/VERSION`).

**Current engineering reference:** [Full repository audit (24 Nov 2026)](docs/REPOSITORY_AUDIT_2026-11-24.md) · [Documentation index](docs/INDEX.md) · [CHANGELOG.md](CHANGELOG.md).

The audit records verified source checks and outstanding target-Mac tests; it does **not** claim the native solver or all tests passed on this machine.

## Headless solver

**One native solver, plus an import-only desktop GUI shell.**
The obsolete Tkinter GUI, Next.js web editor, Django backend and deployment
stack have been removed. The Route-Mate PySide6 GUI is being directly transplanted
at the same `gui/` and `run_gui.py` paths, but **optimisation is disabled** until
the existing native CLI adapter has been implemented and independently tested.
The GUI is not a second optimiser.

## Current GUI milestone — Original Route-Mate import and lock review, then STOP

The Route-Mate 1.44 PySide6 window has been copied into the repository,
including its icons, source import support, electrical input sanity
checks, read-only geometry contracts and local standalone renderer bridge.
The old Python Quick Solve/Hell Mode routing engines are **not included**.

```sh
python3 -m pip install -r requirements-gui.txt
# MacPorts is used for the original Tk-compatible schematic PNG preview:
sudo port install librsvg
PATH="/opt/local/bin:$PATH" python3 run_gui.py
```

Use **Load JSON**. This invokes the **original Route-Mate 1.44 GUI workflow**:
choose actual/preferred board dimensions, choose the component-spacing setting,
run the collector/electrical input sanity and read-only PRE-SOLVE checks, preview
the board, and review each positioned component's Fixed / Movable / Edge / Slide
status with an individual highlighted board view. After the last lock decision,
**the solver remains disabled and the GUI stops before Pass 1**.

Board dimensions are supplied by the user in the dialog rather than blindly
rendering the JSON's large original working canvas (MOTOEX's raw fixture is
99×500). Choosing 24×56 displays 24×56, without overwriting the source file.

As in the donor GUI, stage/assumed-geometry sidecar files are saved alongside
the JSON. These are reports and provenance, **not optimiser output**.
No routing, worker calibration, speed probe, Python Quick Solve, native CLI
subprocess, or Pass 1 is started.

The same checks can be run without PySide6:

```sh
python3 -m gui.preflight test-fixtures/masters/moto/motoex.json
python3 scripts/audit_repo_integrity.py
python3 -m unittest discover -s tests -p 'test_*.py' -v
```

The donor workflow requires the local renderer for component/lock highlighting; if preview fails, the GUI displays an error and does not advance through lock review.
To enable preview, compile the existing local renderers:

```sh
cd src/frontend
npm install
npm run build:renderers
```

This is **not** an end-to-end GUI integration. Next milestone will bind
the same existing native CLI to the GUI, with no duplicate solver.


### Schematic preview

A **Schematic** button beside Component side / Copper side displays the existing
standalone schematic SVG renderer's output. The schematic renders once from the
imported JSON when loading succeeds, before component lock prompts begin;
clicking the button switches the same viewport without altering or solving the
board. Schematic display now uses the **original Tk GUI's 2400 px librsvg PNG
conversion** (requires `rsvg-convert`) for faithful label and part rendering,
while board/copper views retain their original QtSvg pipeline. See
[GUI integration notes](gui/README.md).

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

To independently requalify archived candidates without another anneal **on the Mac with the original prepared input and archived files**:

```sh
python3 scripts/requalify_motoex_winner_ladder.py
```

See `docs/motoex-seed37-winner-ladder-2026-11-24.md` for the exact original
reproducible experiment and archive locations.

## AUDIOEX locked-BMS native ladder

The `audioex.json` source retains a case-positioned BMS at **row −2, col 24**.
The dedicated native CLI ladder prepares an isolated input with BMS **Locked +
Edge, Slide OFF**, allows its *body* overhang while requiring all electrical
pins on-board, and runs with **drill OFF / stacking ON**. It executes ten seeds
per budget: 5k–50k by 5k, then 100k–500k by 25k (270 independent solves).
Every saved candidate is audited; **all strictly passing boards** are saved,
with the five best distinct layouts copied to `top5/`.

Build the existing native edge decoder with `npm run build:native:edge`, then:

```sh
python3 scripts/run_audioex_native_ladder.py --jobs 4
# After interruption:
python3 scripts/run_audioex_native_ladder.py --jobs 4 --resume
```

Outputs default to `~/Desktop/audioex_bms_fixed_native_ladder/`. No GUI,
fixture JSON, or native solver code changes are needed. The existing four
manual source cuts are preserved in the original fixture, but the native
solver **always starts with blank cuts/wires**. See
[exact procedure and qualification](docs/audioex-fixed-bms-native-ladder-2026-11-24.md).

## Audit and test coverage

The headless `npm run test:solver` and `npm run test:board` scripts run
only their respective `*.test.js` suites. Important additional standalone
tests, including `testAuditSavedStrict.js` and native geometry regressions,
need explicit invocation. The complete current Mac command sequence is in
[the audit](docs/REPOSITORY_AUDIT_2026-11-24.md#target-mac-verification-matrix-not-run-in-this-github-only-audit).

The immutable fixture files remain unchanged; their 12-entry SHA-256 manifest
was corrected during the audit. Root GUI-import sidecars are local, not routed
layouts. **Electrical JSON sanity does not certify a solved board.**

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

### Route-Mate GUI integration reference

- [Route-Mate — Code Reuse & GUI Integration Handover](docs/Route-Mate_GUI_Code_Handover.md) documents the **donor Route-Mate 1.44** source modules, import, sidecars, checks, rendering, UI behaviour and tests, preserved unchanged from the source handover.
- [Native CLI integration roadmap](docs/route-mate-native-solver-integration-roadmap.md) defines **this project's** selected integration: a new GUI launches the existing Node/native C/TypeScript CLI and reads its independent verification results.

**Important:** The donor handover's references to `solve_for_display`, `solve_parallel_for_display`, and Hell Mode are historical descriptions of Route-Mate. They are **not** approval to use a second placement/router solver in Version 2.00. The new GUI must invoke the existing native solver CLI; Route-Mate is a source of reusable import, validation, rendering, provenance and UI ideas.
