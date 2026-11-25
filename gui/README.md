# StripSolve GUI 2.26 — Arctic Ice + Colourburst

## Current release: StripSolve GUI 2.26 / Q2 (25 November 2026)

GUI 2.26 gives Open/Save file-dialog navigation buttons a 22 px icon and dedicated compact padding, preserving the Arctic Ice theme. Pass One completion updates the status bar before the winner-consent popup; viewing a winner may then show its own status.

GUI 2.26: the run-outcomes ring shows campaign completion (definitive PASS + FAIL divided by scheduled seeds). Qualification rate is displayed separately, to one decimal. Errors remain retryable, not completed seeds.

GUI 2.26 uses plain-English quality and construction labels, displays the live audited pass rate to one decimal place (excluding errors and pending seeds), and separates elapsed time from estimated remaining time. The winner dialog displays actual verified metrics and freezes the campaign timer before the user decides whether to view the saved board. Q2 remains the internal scoring version; the formula and data formats are unchanged.

GUI 2.26: renderer-version popup windows removed entirely; revision stamps remain in Activity and CLI stderr. Seed count appears only above the progress bar, not inside the ETA text.

The live construction score is Q2, with W = jumper count, C = cut count,
L = total jumper span in mm (2.54 mm pitch), D = nonvertical jumper count,
U = unplaced on-board component count, S = maximum simultaneous vertical
hole-to-hole overlap. S = 0 for no jumpers and 1 for unstacked jumpers.
Touching endpoints do not stack.

`Q2 = round(max(0, 100 - 0.6*W - 0.4*C - 0.02*L - 10*D - 15*U - max(0,S-1)**2), 2)`

Strict audit qualification and the native engine are unchanged. The GUI ranks
only audited passes. Q2 uses the existing campaign paths, with schema 2,
quality_version=Q2, and S and wire_length_mm in the CSV. Q1 campaigns cannot
resume or feed Pass Two; explicitly overwrite the selected old campaign to
start fresh. Do not relabel old scores. Historical WR research JSONs and
reports remain historical evidence. No score is a percent of theoretical
optimum.

The dashboard displays W/C/S/Q2, champion wire length in mm/inches, audited
outcomes, runtime and one progress/ETA control. No duplicated sidebar progress,
project/workspace box, worker count or noisy quality/complexity chart. CPU
allocation is max(1, available logical CPUs - 1); the 100-decode calibration
only estimates speed. CPU allocation is recorded in disk logs. On completion,
save winner JSON and both SVGs before the themed trophy consent dialog.
Pass Two is still an import-only stage.

See [Q2 research](../docs/QUALITY_Q2_2026-11-25.md) for the 1,053-board comparison.


**Strict audit metadata correction (2.18):** The native CLI now restores
the original `locked` attribute on saved components after its search-only
normalisation. This resolves false rejects for movable parts with explicit
`locked:false` while preserving every physical/electrical audit rule. Already
recorded FAIL rows are unchanged; **do not pull or restart while a campaign
is running**. Finish and preserve the original CSV before considering targeted
seed replay from the same prepared input.

**Historical dashboard (2.17–2.18; superseded by Q2):** The full main preview area—not the
sidebar—is replaced by a modern native Qt6 dashboard when Pass One starts.
Four rounded KPI cards show seeds checked, independent strict PASS, best
audited Q and that board's wires/cuts. Antialiased QPainter charts show
real quality history, wires/cuts trends, audited outcomes, and recent seed
runtimes. A control panel shows workers, progress, last seed and measured
elapsed/ETA. Values update on every worker progress signal. Resume restores
already verified historical rows; no synthetic data or top-five list is shown.

The board-preview toolbar still works. Use **Board preview** inside the
dashboard to inspect the board and **Live dashboard** above the main area
to return to the charts. On completion, save winner JSON and both SVGs
before asking **"Do you want to see the winning board now?"** (Yes/No,
default No). Choosing No leaves the full dashboard on screen; **View saved
winner** opens the already-saved SVGs without rerunning the solver.

**Current app name: StripSolve.** The original Route-Mate donor lineage
described below is historical and still relevant for provenance. The GitHub
repository and `Work/` project identifiers intentionally keep their existing
paths so prior runs are not lost.

The current PySide6 GUI has Pass One 10k/20k campaigns with 200-seed DEBUG
and 2,000-seed FULL modes, per-budget CSV status tracking, resume and
explicit overwrite confirmation. Pass One independently audits each PASS,
replays its best surviving candidate, and saves winner JSON plus two SVGs.
Pass Two currently **imports** vetted survivors; the Pass Two native search
strategy remains unimplemented. No source JSON is overwritten.

The 10 toolbar icons and 1024x1024 application icon use the custom
StripSolve copper-stripboard S artwork. To regenerate artwork offline:

```sh
python3 tools/build_icons.py
# optional: python3 tools/build_icons.py --png
PATH="/opt/local/bin:$PATH" python3 run_gui.py
```

Assets are generated into `gui/icons/` and `gui/assets/`, with an in-memory
SVG fallback when those directories are read-only. The approved 1024px app PNG is source-controlled and never regenerated\non normal launch (or `--force`). Toolbar SVGs refresh once on the first\nlaunch of this artwork revision, then preserve local edits; use `--force`\nto refresh the 10 toolbar SVGs again.
The short splash only indicates desktop UI startup; it does not claim to run
native solver checks.

## Historical donor notes

# Route-Mate GUI 2.08 — direct PySide6 GUI import

Donor: `bigbadevilaussie-hue/Route-Mate`, audited commit
`bb764a0b61cbf813d4abc687ef6c596243abc929` (Route-Mate GUI 1.44).

The original `gui/main.py`, `run_gui.py`, Qt workflow, board-viewer classes
and source icon are transplanted into their donor path structure.
Import/sanity/geometry/sidecar support is also directly reused.

**FIRST CHECKPOINT: original Route-Mate import workflow and lock dialogs,
then STOP before Pass 1.**

The GUI's **Load JSON** and sequential `_ask_lock_settings()` workflow
comes from Route-Mate 1.44 at the pinned donor commit. The imported methods
were adapted after the transplant to cache schematic previews and enforce
the native-solver hard stop; the original board-size, spacing, highlighted
component-lock dialogs and decision order are preserved.

Original sequence:
1. Select a JSON file.
2. Set **actual** and **preferred** board rows/columns in BoardSizeDialog.
3. Choose component spacing with SpacingDialog.
4. Validate with the donor collector, run electrical sanity, perform read-only
   PRE-SOLVE footprint analysis and record the pipeline/geometry sidecars.
5. Preview the selected board size through the local production SVG renderer.
6. Show each positioned part with an individual highlighted board preview
   and the original Fixed / Movable / Edge / Slide LockDialog.
7. Record the reviewed locks and reach `solve_board()`, which has a hard
   disabled-return guard. **No search or optimiser executes.**

The fixture's 99×500 raw canvas is not the physical board: choose 24×56
in BoardSizeDialog when testing MOTOEX. The source JSON is not overwritten.
Donor pipeline and geometry sidecar files **are** saved beside the JSON.

`gui.preflight` remains an **additional headless, read-only input diagnostic**
tool; it does not replace the GUI's original collector and dialogs.

**There is no Python Quick Solve or Hell Mode optimiser in this repository.**
The former Python solver worker and startup probe remain disconnected.
The actual future engine is the existing native C/TypeScript CLI.

## Current budget selection

GUI 2.26: speed calibration remains a 100-decode timing-only measurement. The separate actual-JSON budget probe uses strict native solves and independent saved-board audits, targets 100 survivors per 2,000 seeds (5%), and compares 10k/20k only as needed. Compatible completed FULL history takes priority. See [budget probe](../docs/BUDGET_PROBE.md). Locked Edge mounts automatically select the Edge decoder in speed calibration, probe, Pass One and replay. No Slide search or strict-rule change.

## Standalone macOS build

macOS standalone build: [build_mac_app.sh](../build_mac_app.sh) adapts the Mac-tested Route-Mate packaging workflow to StripSolve, including the native V5 CLI, Node, SVG renderers, librsvg converter and approved artwork. See [STANDALONE_MACOS.md](../docs/STANDALONE_MACOS.md). Packaged Work lives in `~/Library/Application Support/StripSolve/Work/`; source checkout Work is unchanged. The new StripSolve bundle is not yet Mac-verified.

## Launch from repository root

```sh
python3 -m pip install -r requirements-gui.txt
PATH="/opt/local/bin:$PATH" python3 run_gui.py
```

Without Qt, use the separate read-only preflight:

```sh
python3 -m gui.preflight test-fixtures/masters/moto/motoex.json
python3 -m unittest discover -s tests -p 'test_gui_*' -v
```

Build optional board preview from `src/frontend/` with
`npm install && npm run build:renderers` (no remote source fetched).

## Next integration seam

`RouteMateWindow.load_json()` and `_ask_lock_settings()` are the original
Route-Mate import/constraint boundary. The existing `solve_board()` is now
a disabled hard stop. Later, connect a tested subprocess adapter to the existing
`src/frontend/tests/solver/v5Solve.js` native CLI. Do not reactivate the
donor Python Quick Solve/Hell Mode routing engines.

The donor handover and native integration roadmap are in `docs/`.

## Schematic tab in the existing SVG viewer

The **Schematic** button sits beside Component side and Copper side in the
original Route-Mate toolbar. On a successful JSON import, the existing **local**
standalone TypeScript/Node renderer produces `schematic.svg` once (using a
temporary copy of the imported project with all `schematicWires`, labels and
net assignments). The SVG is cached in memory and displayed when the button is
clicked. No input JSON or new persistent file is written.

The existing component-side preview and lock-by-lock highlighted board views
stay unchanged. Changing views does not re-run the renderer or modify locks.
The schematic renderer does not launch the native CLI or any solver, and the
Pass 1 hard-stop remains in place. A missing/unbuilt schematic CLI is reported
in the Activity log but does not prevent board sizing or lock review.

Build using the existing `cd src/frontend && npm run build:renderers` command.
The compiled CLI is at `src/frontend/standalone-renderer/dist/standalone-renderer/schematic/cli.js`.

## Qt schematic label contrast

The standalone schematic renderer draws dark labels with a white text outline
behind each glyph using SVG `paint-order="stroke"`. On some macOS QtSvg builds,
the outline is painted **on top**, making component labels and pin text almost
invisible. `render/qt_schematic_svg.py` removes that white halo from **text
elements only**, solely in the in-memory Qt schematic preview.

The compiled standalone schematic renderer and the original `schematic.svg`
output are unchanged. This schematic-only fallback remains separate from the board raster path.
Regression tests: `python3 -m unittest tests.test_qt_schematic_svg -v`

## Visual parity with the original Tk GUI

The old Tk GUI did not display the standalone SVG through Qt: it ran
`rsvg-convert -w 2400 -b white -o schematic.png schematic.svg` and showed
the **PNG**. Direct QtSvg rendering changes text/paint-order handling, making
labels look missing. The new GUI now runs the **same old Tk conversion**
on the already-generated schematic SVG, then shows that PNG in the existing
right-side Qt graphics view. The PNG is cached for instant view switching.

Requires `rsvg-convert` on your Mac, exactly as the old Tk GUI did.
If missing on the user's **MacPorts** installation, run `sudo port install librsvg` and check `/opt/local/bin/rsvg-convert --version`. The Activity tab
reports a clear warning and uses the old QtSvg fallback if this dependency
is not present.

Neither the compiled schematic generator, original project/sidecars nor
the original component-side/copper SVG board viewer is altered. Component
locks, board dimensions and the disabled native CLI remain untouched.
Regression test: `python3 -m unittest discover -s tests -p 'test_schematic_tk_raster.py' -v`.

## Current audit and preflight/strict distinction

See [the full source audit](../docs/REPOSITORY_AUDIT_2026-11-24.md) and
[documentation index](../docs/INDEX.md).

The electrical **input sanity** check validates JSON-side connection
references. It does not run routing, certify a saved board, or substitute for
`tests/solver/auditSavedStrict.js`. GUI control actions labelled Pass 1 remain
disabled. The original 0/1/2 spacing choices are still donor metadata and
are **not mapped to the native CLI**. Edge+Slide remains a specialist control;
its old Python position estimator references an intentionally absent module
and catches that ImportError.

The physical board size and locks selected in the dialog must be carried into
a new immutable prepared input before the native solver can run. No GUI/native
adapter exists yet.

## GUI version policy

**GUI release: 2.04** (`gui/VERSION`). The Git repository's consolidated
solver milestone remains **2.00** (`VERSION`). The window title and GUI
Activity startup message read `gui/VERSION`, not the root file.

**Every change to the GUI or its rendering/import integration must bump
`gui/VERSION` in the same commit** (2.05, 2.06, etc.) and document the
change in `CHANGELOG.md`. Changes only to the headless solver or tests do
not require a GUI version bump.

## Visible executable revisions (GUI 2.04)

- Native solver CLI (`src/frontend/tests/solver/v5Solve.js`) prints a **SOLVER**
  startup banner with the repository Git revision and CLI SHA-256 to **stderr**.
  Its JSON stdout remains unchanged for strict-audit and batch scripts. The
  desktop GUI's solver remains intentionally disconnected in this preflight
  checkpoint; no dummy solver splash is presented as a real solve.
- The compiled **RENDER** and **SCHEMATIC** CLIs each print their own banner
  showing Git revision and a fingerprint of the **actual compiled dist tree**.
  This helps identify stale builds instead of incorrectly labelling them as
  current code.
- Since GUI 2.20, renderer revisions appear **only in Activity**, once per
  distinct stamp. No renderer splash window or status-bar interruption.
  The standalone CLI stderr provenance and the branded application startup splash remain.
- Compiled JavaScript is committed with the TypeScript source. A clean
  `git pull --ff-only` is sufficient; rebuilding is optional unless sources
  have subsequently changed. Regression check:
  `python3 -m unittest tests.test_tool_revision_splashes tests.test_gui_version -v`.


## GUI 2.05 — restored original speed probe and 100-check audit

The original Route-Mate synthetic CPU worker speed probe is restored verbatim from the 1.44 donor commit. It chooses 3 or 4 workers using the original 15% near-tie policy. No Seed 69 experiment is run. The native strict solver audit uses exactly 100 trials: matching seeds 1–50 at 10k and 20k moves, independently verified using the saved-board auditor. The existing board dimensions and lock dialogs feed the audit. Original Overview styling and approved workflow stages are retained. Stops at Solver audit; Pass 1, Pass 2, Final Pass and final Electrical PASS remain unexecuted. Source JSON is not overwritten.


## GUI 2.08 — no more 100 full solver runs

The 100-point move check calls the existing native V5 \`--speedprobe 100\`
decoder-speed instrument once. It measures 100 random genome decodes, then
stops without annealing, routing or saving any board. The measured mean
milliseconds per **decode** is not a complete per-move runtime or an
evidence-based optimal move budget. Drilled-only may change decoder cost.
Wire stacking affects finishing/routing, not this decoder-only measurement.
The original CPU worker scaling probe is unchanged.

Cuts (Drilled only / Knife allowed) and Wire stacking (Allowed / Off) are
chosen from Overview before either probe. The unnecessary legacy Quick Solve
component-spacing popup is gone. The original board-size and per-component
lock dialogs remain. Activity receives full diagnostic stdout/stderr and
explicit flags/physical-board settings. Stops before Pass 1.


## GUI 2.09 — routing rules popup and Slide experimental warning

After the per-component lock prompts, one modal Routing rules dialog
appears. **Drilled only** defaults OFF (knife and drilled cuts allowed).
**Allow stacked jumper wires** defaults ON. The popup explains each flag,
including that the native 100-decoder check exercises drilled-domain
constraints but does NOT measure stacking/router performance. Cancelling
stops before either speed probe. The Overview's Cuts and Wire stacking rows
show the accepted choices instead of editable dropdowns.

The Slide checkbox is labelled **EXPERIMENTAL** in bright red. Its warning
explains that native edge anchors must already touch or overhang the actual
physical board, and the decoder rejects inconsistent input. Old
Quick Solve position-count predictions were removed; no solve passes run.
The native probe's exact rejection reason appears in Activity and in the
Overview error text. The native engine and source JSON remain unchanged.


## GUI 2.10 — Persistent Work and button-controlled Pass One/Two

\`Work/\` is permanently rooted beside \`gui/\` in the checked-out repository,
with \`pass 1/\`, \`pass 2/\`, \`jsons/\`, and \`logs/\` underneath. Opening
the GUI or JSON only creates missing directories, never clears anything.
A pass folder is cleared **only** when that pass's explicit GO button is
pressed. Pass Two never removes Pass One results or the shared JSONs folder.

**Pass One:** After the 100-point speed check, click Pass One in the toolbar.
Choose **10k or 20k** moves per seed (radio buttons), tick **Are you sure?**
and press **GO**. The timing-based default recommendation is only a decoder
throughput heuristic, not experimentally established layout quality.
The existing 3/4-worker probe selects concurrent workers. Exactly 2,000
native strict seeds are attempted. A seed qualifies for the CSV only after
the independent saved-board audit confirms electrical/geometry/copper/locked
board validity. Its Q/100 score uses the repository's existing AUDIOEX
quality100 formula (separate from native CLI quality=0). Pass One persists
only \`Work/pass 1/results.csv\` and \`Work/pass 1/activity.log\`; temporary
candidate JSONs used to audit successful attempts are deleted. The CSV
columns are \`seed,cut,w,q,time_taken\` (elapsed wall seconds).

**Pass Two:** Click Pass Two from a fresh GUI session without loading a
project. It finds \`Work/pass 1/results.csv\`, validates all recorded seed
metrics, and displays a confirmation. On GO, only \`Work/pass 2/\` is cleared
and all rows are copied into \`candidates.csv\`, with a separate Activity
log. No Pass Two optimiser algorithm, budget or filtering is implied or
executed: the GUI labels this as imported candidate data, not an
optimisation success. The original Pass One CSV and all other folders remain.


## GUI 2.11 — routing rules must be reviewed in their own popup

After component placement-lock review, a dedicated modal clearly presents
**Cuts** (knife/drilled allowed or drilled-only) and **Wire stacking**
(allowed or forbidden) as separate radio-button groups. Defaults remain
knife allowed and stacking allowed. The **CONFIRM RULES / CONTINUE** button
stays disabled until the operator checks **I have checked both routing
settings**. Cancelling starts no probes and preserves all work folders.

The Overview stages continue to display the selected policies. Pass One
also repeats those choices in its launch popup before its separate
**Are you sure? / GO** confirmation. The selected policies are used by
the existing native solver and are not changed by the Pass One dialog.
Pass Two remains CSV import only.

## GUI 2.12 — automatic Pass One launch prompt after calibration

When the 100-decode native calibration completes successfully and its worker
has fully finished, Route-Mate automatically opens the **existing Pass One**
10k/20k launch dialog. The user still has to select a budget, tick
**Are you sure?**, and press **GO** to start any optimisation or clear
`Work/pass 1`. **Cancel** changes no work files; Pass One can be opened
again with its toolbar button. No prompt is shown for a failed, cancelled,
or closing calibration. Pass Two remains independently available on startup.


## Board preview backend (2.26)

GUI 2.26 diagnostic: component and mirrored copper previews now use the same 2400 px librsvg → PNG display path as schematic, with a bounded cache. Original SVG bytes go directly to librsvg; the Qt-only text CSS overrides are removed. QtSvg fallback is logged in Activity. Standalone SVG generation, Python overlays, exports and solver remain unchanged. This isolates display-backend effects from Karl's print-vs-interactive renderer differences; visual parity is not yet established. See [details](../docs/BOARD_PREVIEW_BACKEND.md).


GUI 2.27 restores Open Solved as an idle-only, read-only JSON preview. It opens both sides in a separate BoardView with the same librsvg pipeline, Fit and zoom controls; it does not enter project preparation, change the active campaign or certify the imported board.
