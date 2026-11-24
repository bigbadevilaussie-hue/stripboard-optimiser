# Stripboard Optimiser — Version 2.00 project contract

**Milestone:** Consolidation of Two Repositories (24 November 2026).

The current `main` branch is version 2.00. This is a repository-structure and
version milestone; it is not a claim of a new solver algorithm or independently
verified build on a fresh machine.


This repository retains **one headless native optimisation engine**, verification,
research scripts, fixture inputs and standalone schematic/board SVG renderers.
A new **Route-Mate PySide6 desktop GUI shell** is now included at the donor's
original `gui/` and `run_gui.py` locations. The first GUI milestone is deliberately
limited to JSON sniff + input integrity checks, with all solver entry points
disabled. There is still no web UI, Django backend or deployment stack.

## Purpose

Generate electrically correct, physically buildable stripboard layouts from
project JSON, preserving all component identities, pin/net assignments and
the original input. The annealer/finisher may optimise component placement,
vertical jumpers and copper cuts; final saved layouts must be independently
verified before they enter the qualified ranking.

## Native pipeline

1. Validate and prepare the input JSON without overwriting it.
2. Optionally measure solver speed with the existing decode probe.
3. Run repeatable, independently archived seeds/budgets using the native
   C decoder and TypeScript finisher.
4. Save all candidate JSONs and their exact settings, failures and timing.
5. Audit output connectivity, shorts/opens, placement, legal copper,
   jumper direction, body collisions, component locks and board dimensions.
6. Rank **qualified** layouts by wires, cuts, wire length and price.
7. Preserve best, top-five and rejected candidates with restartable checkpoints.

Current default research policy: drilled-only OFF (knife cuts allowed),
wire stacking ON (insulated overlapping jumpers allowed), rows and columns
locked by the supplied JSON. Edge mounting and Slide are optional specialist
controls, not part of ordinary optimisation.

The actual solver source stays generic; no test-specific USB/GPS constraints
are hard-coded. For project-specific fixtures and verified MOTOEX results,
see `test-fixtures/`, `scripts/` and the `docs/` research records.

## Standalone renderers

Retain `src/frontend/standalone-renderer/` for board component-side,
board copper-side and schematic SVG generation from saved JSON.
Do not add React/web editor dependencies to the headless renderer runtime.

## Source entry points

- Native C decode: `src/frontend/components/stripboard/v5wasm/decode.c`
- Native C wire router: `src/frontend/components/stripboard/v5wasm/route.c`
- Solver CLI: `src/frontend/tests/solver/v5Solve.js`
- Independent audit: `src/frontend/tests/solver/auditSavedStrict.js`
- Scripts: `scripts/`
- Native, board and solver regression tests: `src/frontend/tests/`
- Renderers: `src/frontend/standalone-renderer/`

The historical `src/frontend/` pathname is preserved to avoid silently
breaking existing tested CLI/benchmark paths. It is not a frontend application.
