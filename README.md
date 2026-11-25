# Stripboard Optimiser — Version 2.00

**Release milestone:** Version 2.00 — Consolidation of Two Repositories (24 November 2026).

**Consolidation designation:** `2.00` (no Git tag published) · **npm/package version:** `2.0.0` · **StripSolve GUI:** `2.16` (`gui/VERSION`).

**START HERE IF CONTINUING IN A NEW CHAT:** [Active handoff — WR Audio/Moto discovery, multipass plans and current GUI boundary](docs/ACTIVE_HANDOFF_2026-11-24.md). It records the native solver call chain, completed 5k/10k Audio results, unfinished work, reference WRs, and the **destructive rerun warning**.

**Current engineering reference:** [Full repository audit (24 Nov 2026)](docs/REPOSITORY_AUDIT_2026-11-24.md) · [Documentation index](docs/INDEX.md) · [CHANGELOG.md](CHANGELOG.md).

The audit records verified source checks and outstanding target-Mac tests; it does **not** claim the native solver or all tests passed on this machine.

## StripSolve desktop GUI (PySide6)

**StripSolve** is the Arctic Ice + Colourburst desktop GUI for the existing
native stripboard solver. It is the successor brand to the original Route-Mate
GUI; the GitHub repository path and historical donor docs retain their names.

The GUI imports donor JSON files, checks electrical/physical preparation,
shows component/copper/schematic views, reviews locks and routing policy, and
runs the existing native strict solver through **Pass One**. Choose a 10k or
20k move budget; optional DEBUG runs **200 seeds**, while FULL runs **2,000**.
Each campaign records PASS/FAIL/ERROR, completion state and timing in isolated
per-project and per-budget folders. Resume preserves finished PASS/FAIL seeds,
and overwriting prior results requires an explicit confirmation.

On a completed campaign with qualifying seeds, the best audited seed is
strictly replayed, saved to JSON and rendered as component and copper SVGs.
**Pass Two currently imports qualified survivors but does not yet run an
optimisation search.** Historical CSVs remain readable and undisturbed.

StripSolve comes with 10 copper/teal SVG toolbar icons and a 1024px
StripSolve app icon, generated entirely offline with PySide6. A short splash
shows desktop start-up only and does not simulate solver activity.

\`\`\`sh
python3 -m pip install -r requirements-gui.txt
python3 tools/build_icons.py  # optional; GUI also generates missing assets
PATH="/opt/local/bin:$PATH" python3 run_gui.py
\`\`\`

Use **Load JSON** and review board dimensions, placement locks, cuts, stacks,
CPU worker selection and the 100-point decoder timing check before pressing
Pass One GO. The old Python Quick Solve/Hell Mode engine is intentionally
disabled; the native CLI is the only live solver. Existing \`Work/\` paths,
source JSONs and compiled solver code are preserved.

For strict regression checks:

\`\`\`sh
QT_QPA_PLATFORM=offscreen PATH="/opt/local/bin:$PATH" \
  python3 -B -m unittest discover -s tests -v
\`\`\`

The imported board/copper/schematic previews require the existing local
renderer build; from \`src/frontend/\` run \`npm install && npm run build:renderers\`
if necessary. For exact schematic raster parity the macOS installation also
uses MacPorts \`librsvg\` (\`rsvg-convert\`).

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

## Active WR Audio + Moto 12,000-trial discovery

The passes-only runner `scripts/run_wr_audio_moto.py` executes 2,000 seeds at each of 5k/10k/20k moves for Audio and Moto. It is **Python orchestration of the same native V5 CLI and strict saved-board auditor**, not the donor Route-Mate Python solver. Current settings: locked 24×56, **drill OFF (knife allowed), stacking ON**, wire preference, no wire polish. Every audited strict pass is saved and scored; unsuccessful trials are silent and discarded.

**Do not rerun casually:** each circuit/budget output directory under `~/Desktop/WR_Audio/` or `~/Desktop/WR_Moto/` is **deleted and recreated** at the start of that rung. There is **no resume support**. Latest user-reported completed runs: Audio 5k **113/2000** strict passes, Audio 10k **170/2000**, highest reported Audio score **74.14** at 10k seed **1171** (11 wires, 39 cuts). Audio 20k was in progress at last update. Moto figures have not yet been reported. See [active handoff](docs/ACTIVE_HANDOFF_2026-11-24.md) for provenance and next-chat instructions.

### Static 100-check Audio/Moto input audit

Run `node scripts/audit_100_audio_moto.js` to check **100 JSON/KiCad preflight conditions per circuit**, without altering inputs or running the optimiser. The 24 Nov source run found **Audio 99 PASS / 1 planning WARN**, **Moto 91 PASS / 9 planning WARN**, and **zero hard input FAILs**. Moto's greater pin and component pressure suggests a tougher move budget, but this is **not** a speed probe or a saved-board strict verdict. See [full audit + explicitly uncertain predictions](docs/AUDIO_MOTO_100_CHECK_PREFLIGHT_2026-11-24.md).

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
