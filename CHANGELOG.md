# Changelog

## Version 2.00 — Consolidation of Two Repositories
**Date:** 24 November 2026  
**Branch:** `main`  
**Version designation:** `v2.00` (package version `2.0.0`)

This release marks the two-repository consolidation milestone and
establishes the unified repository as a **headless stripboard optimiser**.

### Retained
- Native C decoder/router and TypeScript optimisation/finishing pipeline.
- Node.js solver CLI, strict independent qualification and saved-board auditing.
- Python speed probes, sweeps, diagnostics and regression tests.
- Circuit and footprint fixtures.
- Standalone SVG schematic renderer.
- Standalone SVG board (top/copper) renderer.

### Removed during consolidation
- Legacy Tk desktop GUI.
- Next.js web editor and its UI-only assets.
- Django backend, Nginx and Docker deployment stack.
- Web-only dependencies and obsolete GUI-only test sources.

### Validation and compatibility
- No optimiser algorithm change is introduced by **this version bump**.
- Existing CLI and renderer source paths remain at `src/frontend/` to avoid
  breaking research scripts; the directory contains no web frontend.
- The saved MOTOEX 27-wire/43-cut candidate remains an independently
  verified archived benchmark under the specified stacking/knife policy.
- Native solver and renderer builds still require validation on the target
  machine following the consolidation cleanup.

### Versioning
The project-facing designation **2.00** maps to the semantic package version
**2.0.0**. This commit updates `VERSION`, the package metadata and project
documentation together. A Git release tag is separate from the branch version.

### Version 2.00 — Route-Mate GUI import checkpoint (24 November 2026)

- Directly copied the Route-Mate GUI source and startup structure, plus
  non-optimising collector, electrical sanity, package geometry, pipeline
  records and Qt requirements.
- Kept the existing local board SVG renderer; disabled donor's Git clone
  and remote-renderer fetching.
- Added `gui.preflight` for read-only JSON sniff, input electrical integrity,
  footprint inventory, dimension and lock reporting, plus regression tests.
- Removed donor Python Quick Solve worker imports and startup calibration.
  **No solver is invoked.** All solve controls are disabled and the workflow
  pauses immediately after the checks.
- The existing C/TypeScript native CLI remains the sole future solver.
- Both repository release version and GUI title remain **2.00**.

### Version 2.00 — Restore donor GUI board sizing + sequential lock decisions

- Restored the **unmodified Route-Mate 1.44** `load_json()` and
  `_ask_lock_settings()` methods from commit `bb764a0`.
- Board-size/spacing dialogs now run before the donor import checks.
- Each positioned component is highlighted and presented with the original
  Fixed/Movable/Edge/Slide lock dialog.
- Selected board size drives both the on-screen preview and in-memory
  prepared project; input JSON remains unchanged.
- Donor pipeline/geometry sidecars are written as in Route-Mate.
- Existing `solve_board()` guard still stops before Pass 1, no solver starts.

### Version 2.00 — Embedded standalone schematic view

- Added a checkable **Schematic** toolbar button using Route-Mate's existing SVG viewport.
- Automatically rendered/cached the unmodified schematic from the already
  compiled Node standalone schematic CLI on successful JSON import.
- Kept existing board renderer, highlighted lock review and board-size dialogs intact.
- Did not add an alternative routing/optimisation engine or start Pass 1.
- Added headless CLI-bridge unit tests and Qt offscreen view-switch checks.

### Version 2.00 — Qt schematic text legibility

- Fixed washed-out schematic labels in Route-Mate's PySide6 SVG viewport:
  QtSvg cannot reliably honour the standalone SVG's white text halo
  `paint-order`. Strip the halo for the **Qt schematic preview only**.
- Kept the original schematic SVG generator, board/copper renderers, lock
  dialogs, input JSON and disabled solver unchanged.
- Added three targeted, headless text-renderer regression tests.

### Version 2.00 — Restore exact original Tk schematic preview pipeline

- Compared original Tk GUI and current standalone schematic sources: the
  schematic TS/JS renderer is byte-for-byte unchanged from before cleanup.
- Diagnosed divergent rendering backends: original Tk used librsvg PNG,
  whereas the new Qt GUI was displaying the SVG directly in QtSvg.
- Restored the old `rsvg-convert -w 2400 -b white` raster conversion for
  schematic **display only**; the existing SVG generator remains authoritative.
- Cache the PNG and show it in the existing Qt board preview canvas when
  Schematic is selected. The native renderer's raw SVG remains unchanged.
- Keep source JSON, persistent sidecars, board/copper views, exact donor
  dimensions/spacing/lock-review workflow and solver hard stop untouched.
- Add unit and Qt smoke test coverage of raster generation and switching.

### Route-Mate GUI 2.01 — independent GUI versioning (24 November 2026)

- Bumped the desktop GUI to **2.01** after the schematic-view integration
  and the restored Tk-compatible librsvg schematic display.
- Added `gui/VERSION` as the single source of the GUI's displayed version.
- Kept the root `VERSION` and npm package release at **2.00 / 2.0.0**.
- Required future changes to GUI and GUI-renderer/import integration to
  increment `gui/VERSION` and update this changelog in the same commit.
- No changes to the native solver, SVG drawing code, original lock workflow
  or hard stop before Pass 1.

### Version 2.00 / GUI 2.01 — repository-wide static audit (24 November 2026)

- Inspected tracked structure, native CLI and verifier, GUI/pipeline and
  standalone renderer boundaries, tests, dependencies and source imports.
- Restored fixture hash integrity: refreshed current MOTO JSON/net digests,
  added MOTOEX to SHA256SUMS, preserved the old values in the audit report,
  and **did not change circuit files**.
- Added read-only `scripts/audit_repo_integrity.py` with a targeted test.
  This checks tracked paths, versions, manifest, JSON references, local
  TypeScript imports, Python syntax and disabled GUI solve guard.
- Added [full repository audit](docs/REPOSITORY_AUDIT_2026-11-24.md) and
  [documentation index](docs/INDEX.md). Updated README, project, GUI,
  headless and renderer documentation. Flagged older roadmap/handoff
  documents as historical rather than silently rewriting them.
- Corrected MacPorts librsvg setup instructions and excluded generated
  Route-Mate sidecars from Git tracking.
- **No GUI/solver/renderer behaviour changes.** GUI stays at 2.01,
  repository version stays 2.00. Target-Mac runtime tests remain pending.

### Route-Mate GUI 2.02 — fix GUI smoke regression (24 November 2026)

- Fixed `tests/test_gui_shell_smoke.py`: the schematic PNG viewer mock
  was removed before `QAction.trigger()`, so it incorrectly reported zero
  PNG calls even though the interactive schematic was working.
- Keep the mock active during the action click; check the **STOPPED BEFORE
  PASS 1** status immediately after import, before view switching legitimately
  updates the status bar.
- Update GUI version metadata to **2.02** per project change policy.
- **No changes** to `gui/main.py`, Qt drawing, standalone SVG/PNG renderer,
  component locks, circuit inputs, native CLI, or the pre-Pass-1 hard stop.
- Actual PySide6 regression suite must be rerun on the user's Mac.

### Version 2.00 / GUI 2.02 — AUDIOEX fixed-BMS native ladder harness (24 November 2026)

- Added `scripts/run_audioex_native_ladder.py`, a resume-safe **native CLI** controller,
  with independent saved-board audit, retained every-pass and rejected layouts,
  a distinct physical top five, and per-seed logs/checkpoints.
- Uses the 24×56 AUDIOEX source, fixed top-edge BMS anchor (row -2, col 24),
  Edge ON, Slide OFF, knives allowed and wire stacking allowed.
- Schedules 5k–50k in 5k increments and 100k–500k in 25k increments,
  ten independent seeds per budget (270 total).
- Documents that the native CLI starts with blank cuts/wires; original four
  source cuts and JSON remain untouched in a preserved copy.
- Added targeted source/policy/ranking/checkpoint unit regressions and
  `docs/audioex-fixed-bms-native-ladder-2026-11-24.md`.
- **No GUI, native C, TS solver, renderer, or source fixture changes.**
  Version remains repo 2.00 / GUI 2.02.

### Native Edge build — negative locked BMS anchor feasibility fix (24 November 2026)

- Diagnosed AUDIOEX 270/270 `NO_FEASIBLE_PLACEMENT`: C graph imposed
  y >= 0 on a locked panel-body origin at row -2, contradictory to its
  locked equality. Mirrored x constraint for negative left-edge origin.
- In `V5_EXPERIMENT_EDGE_MOUNT` only, exempt the zero-origin floor solely
  for a locked rigid `pSides=-2` Edge mount with negative locked coordinate.
- Added `testNativeNegativeEdgeAnchor.js` native regression; preserve
  existing ordinary/edge rejects, physical board, pin, collision constraints.
- Update AUDIOEX documentation to preserve first-run 270 rejects and require
  **new output folder** plus a single-seed smoke before rerunning a ladder.
- No GUI change (2.02), no donor/Python solver and no source fixture edits.
  Run targeted Mac native test to confirm; results not yet independently observed.

### Native Edge finish-gate correction — 24 November 2026

- AUDIOEX 5k smoke advanced past the decoder but reached `NO_PHYSICAL_FINISH`.
- Corrected `physicalFit()` in `autoLayout5.ts`: a rigid locked Edge part
  may retain its **negative body anchor** at exactly the original position
  and rotation; no exemption for non-edge/unlocked parts or electrical pins.
- Added native CLI integration regression `testNativeNegativeEdgeFinish.js`
  for an isolated BMS-derived project, including saved anchor verification.
- Updated AUDIOEX ladder instructions to run the finish regression and use
  fresh `edgefix2` archives rather than resuming the previous failed builds.
- No GUI source change: GUI 2.02 retained. Full AUDIOEX strict solve not yet validated.
