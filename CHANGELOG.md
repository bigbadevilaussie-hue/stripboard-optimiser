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
