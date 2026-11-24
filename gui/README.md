# Route-Mate 2.00 — direct PySide6 GUI import

Donor: `bigbadevilaussie-hue/Route-Mate`, audited commit
`bb764a0b61cbf813d4abc687ef6c596243abc929` (Route-Mate GUI 1.44).

The original `gui/main.py`, `run_gui.py`, Qt workflow, board-viewer classes
and source icon are transplanted into their donor path structure.
Import/sanity/geometry/sidecar support is also directly reused.

**FIRST CHECKPOINT: JSON SNIFF ONLY, then STOP.**

The GUI's **Load JSON** action now calls the non-mutating `gui.preflight`
module, which performs the Route-Mate collector's JSON schema check and its
electrical input sanity check. It reports dimensions, locks, placements,
components, nets, pin assignments, missing footprint definitions, and
warnings. The independent .net comparison is available via the CLI
`--net` argument but is not yet exposed in the desktop picker.

The GUI may preview an already saved board using the *local* standalone Node
renderer. This is not a solve or new routing pass. Preview failure is advisory
and does not change the import result.

**There is no Python Quick Solve or Hell Mode engine in the destination.**
The old solver worker, startup probe, lock-to-solve automatic transition and
toolbar solve path are disabled. No speed probe, pass1, pass2, or native CLI
solver starts from this checkpoint. No input or sidecar output is written.

## Launch from repository root

```sh
python3 -m pip install -r requirements-gui.txt
python3 run_gui.py
```

Without Qt, use the same preflight:

```sh
python3 -m gui.preflight test-fixtures/masters/moto/motoex.json
python3 -m unittest discover -s tests -p 'test_gui_*' -v
```

Build optional board preview from `src/frontend/` with
`npm install && npm run build:renderers` (no remote source fetched).

## Next integration seam

`RouteMateWindow.load_project_path()` is the proven import/pause boundary.
Connect a **new, tested Python subprocess adapter to the existing
`src/frontend/tests/solver/v5Solve.js` CLI** later; do not reactivate
donor Quick Solve methods, reuse an old 24-attempt backend or implement a
second stripboard solver.

The donor handover and native integration roadmap are in `docs/`.
