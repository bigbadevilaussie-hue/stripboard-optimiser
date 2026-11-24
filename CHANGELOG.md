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
