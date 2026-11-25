# Changelog

### GUI 2.17 — Full-width native Qt6 Pass One dashboard (25 November 2026)
- Move live Pass One analytics to the entire main board-preview canvas via QStackedWidget; restore the large board preview on user request and keep the sidebar as Overview/Activity only.
- Replace five-row leaderboard with original antialiased QPainter rounded KPI cards, live audited quality and wire/cut plots, outcome donut, per-seed runtime bars and worker/progress/ETA cards in existing Arctic Ice + Colourburst colours. No web content, fake chart samples or extra package dependencies.
- On start/resume, show the live dashboard and reconstruct historical chart points from confirmed Pass One CSV entries. Stream the single strict-audited champion (Q, W, C and seed) and current seed timings from the unchanged native worker.
- When Pass One completes, save champion JSON and both SVGs, then ask Yes/No (default No) to view the top verified board. No leaves the dashboard visible; Yes opens saved SVG board preview. Board preview and Live dashboard controls permit explicit switching.
- Add offscreen Qt GUI and pure audited-ranking regression coverage; preserve Work directory, original project files, campaign CSV schema and Pass Two candidate-import-only behaviour.
- Source-level integration complete; target macOS end-to-end GUI visual and regression run remains outstanding.

### GUI 2.16 — Live strict Pass One leaderboard and winner-preview consent (25 November 2026)
- Add a dedicated, scrolling 🏆 Scoreboard tab without reducing the board canvas or crowding the compact Overview footer.
- Live progress updates now carry the five highest independently audited strict PASS seeds, ranked by Q descending, then fewer wires, cuts and lower seed. Resume immediately restores verified leaders from retained CSV rows.
- Show checked/PASS/error counts, latest seed result, move budget and debug/full mode, then retain final leaders after completion.
- Persist the champion's component/copper SVGs and JSON before asking "Do you want to see the winning board now?" No preserves the existing viewer; Yes opens the saved SVGs. The Scoreboard has a "View saved winner" button to open them later without rerunning the solver.
- Clearing or loading a new project resets stale scoreboard content; no existing campaign CSV schema, Work directories, native decoder or strict audit rules changed.
- Add GUI and campaign regression tests for ranking, resume, progress streaming and declining winner previews. Full Mac Qt test run pending.

### GUI 2.15 — Compact overview with fixed Pass One results (25 November 2026)
- Keep the champion summary, live Pass One activity/progress, worker count and elapsed/ETA visibly anchored below the scrolling preparation checklist.
- Reduce checklist padding and row spacing; show cuts and wire-stacking settings inline rather than on extra lines.
- Drop the redundant long instructions in the checklist and condense lock counts to one line. Full checks remain accessible by scrolling on smaller window sizes.
- Add a regression test for the separate scrolling checklist and fixed result footer. No solver, source JSON, seed CSV or Work workspace changes.

### GUI 2.14 — StripSolve copper-trace artwork and splash correction (25 November 2026)
- Replace improvised 10 toolbar SVGs with consistent Arctic Ice / copper-board / blue-teal routing designs, while preserving the existing QAction connections, 24px icon sizes and HiDPI scaling.
- Commit the user's approved 1024px copper-circuit S application PNG; retain the SVG fallback for read-only or incomplete installs.
- Redesign the skippable splash to feature the approved large app icon, readable StripSolve identity, honest Pass One/Pass Two capability labels and interface-only progress.
- Versioned asset migration refreshes old generated toolbar icons once, preserves later custom SVG edits, and never replaces the approved app PNG with the vector fallback.
- Add regression tests for artwork refresh, approved 1024px PNG and populated splash image. No native optimiser, CSV, workspaces, or seed-selection changes.

### GUI 2.12 — Prompt for Pass One immediately after successful move calibration (25 November 2026)
- After a successful native 100-decode measurement, schedule the existing Pass One 10k/20k confirmation dialog once the calibration worker has finished. The user is no longer required to find the toolbar button.
- No optimisation starts, and no Work folder is cleared, until the user ticks **Are you sure?** and explicitly presses **GO**. Cancel preserves all files and the toolbar remains available for later manual launch.
- Failed/cancelled calibration and closing the GUI do not open a Pass One prompt. No changes to Pass Two or the native solver.
- The six pending cosmetic improvements remain deferred.

### GUI 2.11 — Make cut and stacking choices unmistakable (25 November 2026)
- The existing dedicated routing-rules popup now shows two large, labelled radio-button groups: knife/drilled cut policy and allowed/forbidden jumper stacking. Defaults remain knife allowed and stacking allowed.
- Explicit "I have checked both routing settings" confirmation is required before the popup can continue to CPU and 100-decode calibration. Cancel still starts no probes and never clears Work.
- Pass One's launch confirmation repeats the selected policies so the operator can review them before GO. The GUI retains the selected values and passes them to the unchanged native solver.
- No change to Pass Two CSV import, pass-directory cleanup, source JSON, or native optimiser.

### GUI 2.10 — Persistent Work, explicit Pass One/Two buttons, CSV-only Pass One (25 November 2026)
- Stable \`Work/pass 1\`, \`Work/pass 2\`, \`Work/jsons\`, \`Work/logs\` under the checkout; creating/opening GUI never deletes results.
- Each pass folder is cleared ONLY after its own explicit GO confirmation. Pass Two never clears Pass One or the shared JSONs directory.
- Pass One button opens 10k/20k move radio choices, 100-point decoder-timing estimate, Are-you-sure checkbox and GO. No automatic pass start.
- Real Pass One 2,000-seed native strict CLI trials use the existing selected cut/stack policies and original 3/4 worker recommendation. Independent saved-board audit gates every CSV row.
- Pass One outputs only \`results.csv\` (seed,cut,w,q,time_taken) and \`activity.log\`; candidate solved boards are temporary and discarded. Q/100 uses the existing AUDIOEX quality100 formula, not native CLI quality=0.
- Pass Two button works from a fresh GUI launch without JSON import. Reads all Pass One CSV rows; on explicit GO writes \`pass 2/candidates.csv\` and \`pass 2/activity.log\`.
- Pass Two's search strategy and move budget are not yet defined. CSV import is not mislabelled a completed optimisation pass.
- No changes to native solver, original JSON, post-routing final Electrical PASS or automatic Pass Two launch.


### GUI 2.09 — Cut/stack popup, experimental Slide visibility, actionable native diagnostics (24 November 2026)
- Replace sidebar cut/stack dropdowns with one routing-rules popup after component lock review and before worker/move probes.
- Default Drilled only OFF (knife cuts allowed) and Allow stacked wires ON; explain how each choice affects the native solver.
- Keep Cuts and Wire stacking as read-only checklist milestones showing the confirmed settings.
- Label Edge+Slide EXPERIMENTAL in bright red, remove obsolete Quick Solve attempt counts and unavailable slide_fit diagnostics.
- Surface native input rejection reasons in Activity and the failed-stage message without loosening constraints.
- No changes to the native solver, physical-board rules, 100 decoder samples, original CPU probe or optimisation passes.


### GUI 2.08 — Native decoder 100-point move check and policy controls (24 November 2026)
- Replace mistaken 100 full solver attempts with one native \`--speedprobe 100\` decoder-only measurement; zero optimisation passes.
- Cut policy (drilled-only vs knife-allowed) and wire-stacking selection occur before CPU probe and move check.
- Remove obsolete component-spacing popup; keep board dimensions and per-part lock dialogs.
- Activity records actual/preferred board, locked anchors, CLI flags, native stdout/stderr, probe timing and limitations.
- Move-calibration progress is indeterminate until native probe completes; stop before Pass 1 and keep final Electrical PASS pending.
- Preserve source JSON, native solver algorithm, original Route-Mate worker CPU probe. GUI 2.08.


### GUI 2.07 — Respect the selected physical board in native audit (24 November 2026)
- The 100-check native solver audit now locks the GUI-selected physical rows and columns in its temporary input snapshot, so native strict mode cannot resize the selected board.
- The imported JSON and GUI project remain unmodified; no changes to the original CPU speed probe or optimisation passes.
- Add a regression test for a 24×56 physical board imported with unlocked dimensions.


### GUI 2.06 — PySide6 splash constructor fix (24 November 2026)
- Fix renderer revision splash constructor to use the PySide6-supported `(pixmap, flags)` signature.
- Prevent the splash error from interrupting JSON import and lock review.
- No changes to solver audit, speed probe, optimisation stages, board dimensions or toolbar.


### GUI 2.05 — original speed probe restored and 100-check solver audit (24 November 2026)
- Restore original Route-Mate 1.44 synthetic CPU worker speed probe; 3/4 worker selection.
- Existing board dimensions and locks feed exactly 100 native strict checks, paired 10k/20k with independent saved-board audit.
- Approved eleven-stage Overview, existing progress bars, unwanted toolbar buttons removed.
- Hard stop after solver audit; no optimisation passes or final electrical verification.
- Bump gui/VERSION to 2.05 only; no solver algorithm changes.


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

### AUDIOEX native edge diagnostics and four-edge regressions (24 November 2026)

- Extended synthetic edge decoder tests across top/bottom/left/right overhangs,
  distinguishing allowed locked body overhang from off-board electrical pins.
- Added a CLI validation regression that rejects a BMS pin outside the board
  with a precise pre-solve reason (no move-budget waste).
- Archived the native CLI's existing `firstFeasibleMove` and
  `firstFeasibleMs` diagnostic fields in the AUDIOEX ladder checkpoint/CSV,
  and included first-fit and failure reason in each printed trial line.
- Verified from AUDIOEX: custom footprint labelled "10-pin" actually defines
  eight pins, only B+ and B− have net assignments; floating-pin isolation
  remains unchanged. No fabricated pins or clearance rule changes.
- Native solver C/TS, saved-board auditor, case-locked BMS, original AUDIOEX
  fixture, GUI implementation and GUI version are unchanged.
- Target Mac must run the extended tests before a fresh smoke/ladder.

### Route-Mate GUI 2.03 — executable revision splashes (24 November 2026)

- Expose a persistent launch identity in the desktop Activity log, separately for
  the compiled board renderer and schematic renderer; avoid repeating it for every
  component-highlight preview. Warn clearly when an old compiled renderer has no
  revision stamp. GUI window title and Activity header show the checked-out Git
  commit alongside GUI 2.03.
- The native solver CLI prints a distinctive startup revision splash to **stderr**
  without changing its single machine-readable JSON result on stdout.
- Both Node renderer CLIs print their release, checked-out Git commit and
  SHA-256 fingerprint of the actual compiled renderer JavaScript, also to stderr.
- Root VERSION stays 2.00. Native decoder, router, anneal and strict constraints
  are unchanged; this is diagnostic visibility, not a new solver release.
- Headless rendering requires rebuilding compiled files: `cd src/frontend && npm run build:renderers`.

### Route-Mate GUI 2.04 — visible Qt Render and Schematic splash (24 November 2026)

- The first invocation of each distinct compiled Render/Schematic revision now
  produces a **non-modal 1.8-second Qt splash screen** with its exact executable
  revision, in addition to the persistent Activity log and GUI title identity.
- Multiple component highlight renders do not repeatedly interrupt the operator;
  a new compiled revision can generate a fresh splash. GUI-only visibility;
  the native CLI and both headless renderer CLIs retain their stderr splashes.
- No wiring, routing, strict acceptance, SVG content or saved project changes.

### Standalone renderer compiled CLI splash sync (24 November 2026)

- Committed the built renderer and schematic JavaScript entry points and the
  shared compiled revision helper alongside their TypeScript source, so a clean
  `git pull` displays revision splashes without a local build or dirty dist.
- Added lightweight Node startup checks for both compiled renderers.
