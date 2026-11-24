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
output are unchanged. This is not applied to the component/copper board views.
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
- The GUI shows a **non-blocking Qt splash** on first use of each renderer
  revision, plus a permanent banner in Activity; repeated part highlights do
  not raise repeated splashes. The GUI title includes its own 2.04 revision.
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
