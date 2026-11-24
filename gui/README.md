# Route-Mate 2.00 — direct PySide6 GUI import

Donor: `bigbadevilaussie-hue/Route-Mate`, audited commit
`bb764a0b61cbf813d4abc687ef6c596243abc929` (Route-Mate GUI 1.44).

The original `gui/main.py`, `run_gui.py`, Qt workflow, board-viewer classes
and source icon are transplanted into their donor path structure.
Import/sanity/geometry/sidecar support is also directly reused.

**FIRST CHECKPOINT: original Route-Mate import workflow and lock dialogs,
then STOP before Pass 1.**

The GUI's **Load JSON** method and sequential `_ask_lock_settings()` method
are copied verbatim from Route-Mate 1.44 at the pinned donor commit.

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
python3 run_gui.py
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
