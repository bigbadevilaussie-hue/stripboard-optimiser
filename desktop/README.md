# Desktop application — current prototype

The desktop application is a Python/Tkinter prototype in this directory. It is separate from the inherited Next.js/Django web application.

**Status:** the current UI and renderer integration are in the repository, but the desktop optimiser is not currently launch-ready. `ui/main_window.py` imports `stripboard_optimizer.solver.worker.SolveWorker`; the corresponding `solver/worker.py` file is absent from the current tree. Do not describe solver execution as operational until that module and its integration are implemented and verified.

There is no desktop `pyproject.toml`, requirements file, installer or packaging workflow in the current repository.

## Actual directory structure

This is the current tracked structure, not a proposed future architecture:

```text
desktop/
├── README.md
└── src/
    └── stripboard_optimizer/
        ├── main.py
        ├── board_estimator.py
        ├── filters.py
        ├── controllers/
        │   └── project_controller.py
        ├── models/
        │   └── project.py
        ├── services/
        │   └── import_service.py
        ├── validation/
        │   └── preflight.py
        ├── solver/
        │   └── __init__.py
        ├── storage/
        │   └── __init__.py
        ├── ui/
        │   ├── main_window.py
        │   ├── board_viewer.py
        │   ├── project_panel.py
        │   └── validation_panel.py
        └── resources/
            └── standalone-renderer/  # Bundled compiled JavaScript runtime
```

The solver, storage, models, validation and service directories are not yet the complete architecture described in the project specification. Empty package initialisers are not implemented modules.

## What the current UI contains

The tracked UI code provides:

- Project JSON selection and loading through `ProjectController` and `ImportService`.
- Optional .net file selection and a basic pin-count cross-check.
- KiCad ZIP selection and basic footprint/pad inspection.
- A preflight panel for board dimensions, footprint matches and lock-state reporting.
- Manual, full-auto and two-pass mode selection controls.
- A worker queue interface and Stop control intended for solver progress.
- A separate board viewer with three selectable views:
  - **Front (Top)** — component side.
  - **Back (Copper)** — copper side.
  - **Schematic** — schematic drawing when the schematic renderer produced it.
- Fit/100% image scaling and scrollbars.

The presence of UI controls does not prove that the corresponding optimisation, validation or worker functionality is implemented. In particular, the solver worker import currently prevents the application from starting.

## Renderer integration

The desktop runtime copy is located at:

`src/stripboard_optimizer/resources/standalone-renderer/`

It contains compiled JavaScript and data required by the standalone board and schematic CLIs. The Python UI locates the runtime relative to its own package directory.

The TypeScript source of truth is **not** in the desktop directory. It is:

`../src/frontend/standalone-renderer/` (relative to the repository root)

The compiled frontend output is:

`../src/frontend/standalone-renderer/dist/`

The desktop runtime copy must be kept in sync with the compiled renderer files when renderer changes are made. There is currently no documented automated sync command.

### External runtime tools

The desktop render path calls:

- Node.js to execute the compiled board and schematic CLIs.
- `rsvg-convert` (librsvg) to convert generated SVG files to PNG.
- Pillow (`PIL`) for image loading and display in the Tkinter viewer.
- Tkinter, which is part of the Python installation on supported desktop distributions.

The current code uses `shutil.which("node")` and then falls back to `/usr/local/bin/node`. The macOS `open` command is used by the best-board preview path. These assumptions need to be addressed before cross-platform packaging.

### Render JSON workflow

The current `Render JSON...` path:

1. Selects a project JSON file.
2. Runs the board renderer to create `board-top.svg` and `board-copper.svg`.
3. Runs the schematic renderer separately to create `schematic.svg`, when that CLI is available and succeeds.
4. Converts the generated SVGs to PNG using `rsvg-convert`.
5. Loads the available PNGs into the three-view board viewer.

Output is written under:

`~/Desktop/stripboard-renders/`

The viewer enables the Schematic selector only when a schematic PNG exists. The separate `Preview board` action currently uses the board renderer only; it does not generate the schematic view.

## Current known blocker

`desktop/src/stripboard_optimizer/ui/main_window.py` contains:

```python
from stripboard_optimizer.solver.worker import SolveWorker
```

But the tracked `desktop/src/stripboard_optimizer/solver/` directory currently contains only `__init__.py`. The missing worker module must be implemented and integrated before the application can launch and the optimisation controls can be exercised.

Do not work around this by creating a duplicate desktop project or moving code outside the tracked repository.

## Documentation and implementation boundary

The root [project.md](../project.md) is the canonical specification for the intended optimiser, validation, candidate management, export and distribution requirements. It describes target behaviour, not a claim that every module exists today.

The repository root [README.md](../README.md) describes the inherited web application and the current renderer/desktop status. The renderer's source, build instructions and parity tests are documented in [the standalone renderer README](../src/frontend/standalone-renderer/README.md).

There is currently no desktop-specific automated test directory in the tracked tree. Do not invent test commands or claim desktop tests have passed.
