# Stripboard Optimiser — Tkinter Desktop GUI

This is the desktop application that wraps the headless v5 solver into a multi-seed, validated optimisation workflow.

## Directory Structure

```
desktop/
├── pyproject.toml
├── README.md
├── src/
│   └── stripboard_optimizer/
│       ├── __init__.py
│       ├── main.py                # Application entry point
│       ├── app.py                 # Tkinter init, controller wiring
│       ├── ui/
│       │   ├── main_window.py     # Main layout, menus
│       │   ├── project_panel.py   # Open project, summary
│       │   ├── settings_panel.py  # Basic optimisation settings
│       │   ├── advanced_settings.py # Weights
│       │   ├── progress_panel.py  # Live run progress
│       │   ├── candidate_panel.py # Candidate list
│       │   ├── comparison_panel.py # Pareto comparison
│       │   ├── validation_panel.py # Preflight/validation findings
│       │   └── dialogs.py         # Reusable dialogs
│       ├── controllers/
│       │   ├── project_controller.py
│       │   ├── optimisation_controller.py
│       │   └── candidate_controller.py
│       ├── models/
│       │   ├── project.py
│       │   ├── settings.py
│       │   ├── candidate.py
│       │   └── run_manifest.py
│       ├── services/
│       │   ├── import_service.py
│       │   ├── preprocessing_service.py
│       │   ├── optimisation_service.py
│       │   ├── candidate_service.py
│       │   ├── ranking_service.py
│       │   └── export_service.py
│       ├── solver/
│       │   ├── solver_adapter.py  # Interface to headless solver
│       │   ├── worker.py          # One solver run
│       │   ├── worker_manager.py  # Concurrency
│       │   └── progress.py
│       ├── validation/
│       │   ├── preflight.py
│       │   ├── structural.py
│       │   ├── electrical.py
│       │   ├── mechanical.py
│       │   └── roundtrip.py
│       ├── storage/
│       │   ├── run_store.py
│       │   ├── candidate_store.py
│       │   └── manifest_store.py
│       └── utils/
│           ├── paths.py
│           ├── hashing.py
│           └── logging_config.py
├── resources/
│   ├── icons/
│   └── themes/
└── tests/
    ├── test_import.py
    ├── test_preflight.py
    ├── test_preprocessing.py
    ├── test_solver_adapter.py
    ├── test_worker_isolation.py
    ├── test_candidate_ranking.py
    └── test_export_roundtrip.py
```

## Module Responsibilities

- **UI**: Display information, collect input. No solver logic.
- **Controllers**: Coordinate actions. Pass requests to services.
- **Models**: Data structures. No UI widgets.
- **Services**: Import, preprocessing, optimisation, candidate handling, ranking, export. Independent of Tkinter.
- **Solver**: Interface to the existing C/WASM solver. Do not reimplement it in Python.
- **Validation**: Preflight, structural, electrical, mechanical, round-trip. Must be callable without GUI.
- **Storage**: Run directories, candidate files, manifests. Never write into fixtures.

## Tkinter Threading Rules

- All widget updates must happen on the main thread.
- Solver workers must never directly update Tkinter widgets.
- Workers communicate through a thread-safe queue.
- The GUI polls using root.after().
- Cancellation must stop new work safely.
- Completed candidates must survive cancellation.

## Directory Separation

```
test-fixtures/       Immutable original test inputs
desktop/             Tkinter application source
runs/                Generated optimisation runs
```

Each optimisation run gets a unique directory:

```
runs/
└── run-<unique-id>/
    ├── input/
    ├── workers/
    ├── candidates/
    ├── validation/
    ├── manifest.json
    └── report.json
```

## Implementation Stages

1. Working window, project import, preflight report.
2. Solver adapter and one isolated worker.
3. Multiple workers, candidate storage, progress reporting.
4. Candidate comparison, champion selection.
5. Export and packaging.

## Important Boundary

The root project.md remains the canonical specification. Do not modify the Moto-Mate or Audio-Mate master fixtures. Do not modify the seven preserved KiCad footprints.
