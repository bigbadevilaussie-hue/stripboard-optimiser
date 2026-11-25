# Stripboard Optimiser — Version 2.00 project contract

## Current release: StripSolve GUI 2.19 / Q2 (25 November 2026)

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

See [Q2 research](docs/QUALITY_Q2_2026-11-25.md) for the 1,053-board comparison.

**Earlier GUI integration milestones below are historical where they conflict with the current release.**

**Milestone:** Consolidation of Two Repositories (24 November 2026). GUI version **2.19** is independently tracked in `gui/VERSION` (24 Nov 2026).

**Current live-work handoff:** [Audio/Moto 12k WR sweep, results, multipass plan and GUI boundaries](docs/ACTIVE_HANDOFF_2026-11-24.md). **Historic static audit:** [Repository integrity and integration audit](docs/REPOSITORY_AUDIT_2026-11-24.md). Historical handovers remain useful but their future-phase language may now be outdated.

The current `main` branch is version 2.00. This is a repository-structure and
version milestone; it is not a claim of a new solver algorithm or independently
verified build on a fresh machine.


This repository retains **one headless native optimisation engine**, verification,
research scripts, fixture inputs and standalone schematic/board SVG renderers.
A new **Route-Mate PySide6 desktop GUI shell** is now included at the donor's
original `gui/` and `run_gui.py` locations. The first GUI milestone is deliberately
limited to the original board-size dialog, collector/electrical sanity checks,
component-spacing dialog and individually highlighted lock decisions. All
solver entry points remain disabled. There is still no web UI, Django backend
or deployment stack.

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
6. Rank **qualified** GUI candidates by Q2, then fewer wires, cuts and seed. Research harnesses may retain their historical Q1 formula.
7. Preserve best, top-five and rejected candidates with restartable checkpoints.

**Important harness distinction:** Steps 4 and 7 above describe the full forensic/ladder research harness, **not** every script. The current `scripts/run_wr_audio_moto.py` 12k sweep intentionally **keeps only strict-passing saved JSONs**, prints only passes, has **no failure database and no resume**, and **deletes each existing WR output folder before starting that rung**. It must not be restarted casually. It calls the same native V5 engine and saved-board auditor through `scripts/run_audioex_native_ladder.py`; Python is only orchestration and post-pass scoring. See [active handoff](docs/ACTIVE_HANDOFF_2026-11-24.md) for exact datasets and latest reported status.

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

## GUI/native adapter release gate

The GUI performs the original board-size, spacing and individually highlighted
lock review, then stops. The **CLI integration is not yet present**.

When the adapter is implemented, it must transfer the exact prepared board
(`rows=24`, `cols=56`, `lockedRows=true`, `lockedCols=true` for the
locked MOTOEX test), preserved nets/pins and Fixed/Edge/Slide decisions into
the *existing* native CLI. The original MOTOEX fixture is 99×500 with columns
not locked; its raw JSON is not a valid substitute for the prepared 24×56 input.

Default research policy remains drill-only OFF, stacking ON, board rows and
columns locked, ranking valid outputs by wires before cuts. The imported
Route-Mate spacing control (0/1/2) is *not yet wired* to native solver
`partSpacing`. A JSON sanity PASS is not a saved-layout strict PASS.

Never add another Python placement/routing solver. Before enabling Pass 1:
exercise direct-CLI parity, exit 2 handling, saved-board independent audit,
speed probe, campaign persistence, cancel/resume and Pass 1→Pass 2 survivor
qualification on MOTOEX, MOTO and AUDIO.

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
