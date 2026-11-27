# Stripboard Optimiser — Version 2.00

**Release milestone:** Version 2.00 — Consolidation of Two Repositories (24 November 2026).

**Consolidation designation:** `2.00` (no Git tag published) · **npm/package version:** `2.0.0` · **StripSolve GUI:** `2.39` (`gui/VERSION`).

**START HERE IF CONTINUING IN A NEW CHAT:** [Active handoff — latest Karl forensic research, Moto results and GUI status](docs/ACTIVE_HANDOFF_2026-11-24.md). It records the native solver call chain, opt-in diagonal qualification, unfinished work, historical WR results and **destructive rerun warnings**.

**Current engineering reference:** [Full repository audit (24 Nov 2026)](docs/REPOSITORY_AUDIT_2026-11-24.md) · [Documentation index](docs/INDEX.md) · [CHANGELOG.md](CHANGELOG.md).

The audit records verified source checks and outstanding target-Mac tests; it does **not** claim the native solver or all tests passed on this machine.

**26 November 2026 verification update:** The owner reports that the macOS GUI regression suite passed after the Slide-label and dashboard-return fixes, and that **all 7 headless Node solver suites passed**. This is a user-reported test outcome, separate from the older static audit; no new 5,000-seed Moto hunt or packaged standalone app verification is claimed.

## Current research checkpoint — 27 November 2026

**Main only.** All four former branches are merged and deleted; the 100 Mortal Kombat boards and forensic scripts are preserved. [Current revision, final championship results, source defects and verification gates](docs/KARL_FORENSICS_2026-11-27.md). Research additions only; no GUI version bump or production solver change. No upstream submissions.

## Native V5 experimental candidate modes (26 November 2026)

The solver CLI and saved-board auditor now support opt-in `--candidate-policy strict|diagonal|crossings|archive` qualification. The new `scripts/run_candidate_hunt.py` archives native-generated layouts and separates strict winners from diagonal and routing-repair research candidates. **The C annealer, native strict exit codes, and GUI's existing strict Pass One have not been relaxed**; GUI Pass Two still imports candidates but does not execute a search. See [candidate policies and verified Mac tests](docs/CANDIDATE_POLICIES.md). A small new-campaign smoke test is recommended before another 5,000 seeds.

## StripSolve desktop GUI (PySide6)

**StripSolve** is the Arctic Ice + Colourburst desktop GUI for the existing
native stripboard solver. It is the successor brand to the original Route-Mate
GUI; the GitHub repository path and historical donor docs retain their names.

## Current release: StripSolve GUI 2.39 / Q3 (25 November 2026)

Budget recommendation: [100-point JSON complexity sniff](docs/JSON_SNIFF.md). CPU allocation is separate; no native decodes or qualification trials run before GO.

GUI 2.26 gives Open/Save file-dialog navigation buttons a 22 px icon and dedicated compact padding, preserving the Arctic Ice theme. Pass One completion updates the status bar before the winner-consent popup; viewing a winner may then show its own status.

GUI 2.26: the run-outcomes ring shows campaign completion (definitive PASS + FAIL divided by scheduled seeds). Qualification rate is displayed separately, to one decimal. Errors remain retryable, not completed seeds.

GUI 2.26 uses plain-English quality and construction labels, displays the live audited pass rate to one decimal place (excluding errors and pending seeds), and separates elapsed time from estimated remaining time. The winner dialog displays actual verified metrics and freezes the campaign timer before the user decides whether to view the saved board. Q3 is the current scoring version; the CSV structure is unchanged.

GUI 2.26: renderer-version popup windows removed entirely; revision stamps remain in Activity and CLI stderr. Seed count appears only above the progress bar, not inside the ETA text.

The live construction score is Q3, with W = jumper count, C = cut count,
L = total jumper span in mm (2.54 mm pitch), D = nonvertical jumper count,
U = unplaced on-board component count, S = maximum simultaneous vertical
hole-to-hole overlap. S = 0 for no jumpers and 1 for unstacked jumpers.
Touching endpoints do not stack.

`Q3 = round(max(0, 100 - 0.4*(0.6*W + 0.4*C + 0.02*L + 10*D + 15*U + max(0,S-1)**2)), 2)`

Strict audit qualification and the native engine are unchanged. The GUI ranks
only audited passes. Q3 uses the existing campaign paths, with schema 2,
quality_version=Q3, and S and wire_length_mm in the CSV. Q1/Q2 campaigns cannot
resume or feed Pass Two; explicitly overwrite the selected old campaign to
start fresh. Do not relabel old scores. Historical WR research JSONs and
reports remain historical evidence. No score is a percent of theoretical
optimum.

The dashboard displays W/C/S/Q3, champion wire length in mm/inches, audited
outcomes, runtime and one progress/ETA control. No duplicated sidebar progress,
project/workspace box, worker count or noisy quality/complexity chart. CPU
allocation is max(1, available logical CPUs - 1); the 100-point JSON sniff
assesses board complexity and recommends 10k/20k, without solver calls. CPU allocation is recorded in disk logs. On completion,
save winner JSON and both SVGs before the themed trophy consent dialog.
Pass Two is still an import-only stage.

See [Q3 calibration and archive comparison](docs/QUALITY_Q3_2026-11-25.md) for the formula, research evidence and reproducible rescoring command. Target range 85–95 (default 90) is reserved for a future independently verified stopping policy in Pass Two/Grand Final; Pass One runs all selected seeds.

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
optimisation search.** Q1/Q2 CSVs are obsolete for active campaigns; replace them through confirmed overwrite.

StripSolve comes with 10 copper/teal SVG toolbar icons and a 1024px
StripSolve app icon, generated entirely offline with PySide6. A short splash
shows desktop start-up only and does not simulate solver activity.

\`\`\`sh
python3 -m pip install -r requirements-gui.txt
python3 tools/build_icons.py  # optional; GUI also generates missing assets
PATH="/opt/local/bin:$PATH" python3 run_gui.py
\`\`\`

Use **Load JSON** and review board dimensions, placement locks, cuts, stacks,
automatic CPU allocation and the static 100-point JSON complexity assessment before pressing
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

## Search budget probe

Historical GUI 2.26 budget policy (superseded by 2.39): the former speed and qualification probes are documented in [budget probe](docs/BUDGET_PROBE.md). Current GUI uses the static JSON complexity sniff before GO. Locked Edge decoder selection remains separate.

## macOS standalone application

From the repository root: `bash build_mac_app.sh`. The build copies the verified bundle to your Desktop. See [macOS build and validation](docs/STANDALONE_MACOS.md). Target-Mac validation outstanding.

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

**Experimental native candidate policies:** [diagonal / routing discovery, independent saved-board qualification and resumable 5k-seed runner](docs/CANDIDATE_POLICIES.md). This is opt-in; existing GUI Pass One and strict validation are unchanged.

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


## Board preview display diagnostic

GUI 2.26 diagnostic: component and mirrored copper previews now use the same 2400 px librsvg → PNG display path as schematic, with a bounded cache. Original SVG bytes go directly to librsvg; the Qt-only text CSS overrides are removed. QtSvg fallback is logged in Activity. Standalone SVG generation, Python overlays, exports and solver remain unchanged. This isolates display-backend effects from Karl's print-vs-interactive renderer differences; visual parity is not yet established. See [details](docs/BOARD_PREVIEW_BACKEND.md).


GUI 2.27 restores Open Solved as an idle-only, read-only JSON preview. It opens both sides in a separate BoardView with the same librsvg pipeline, Fit and zoom controls; it does not enter project preparation, change the active campaign or certify the imported board.
