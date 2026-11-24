# Route-Mate — Code Reuse & GUI Integration Handover

**Source:** https://github.com/bigbadevilaussie-hue/Route-Mate  
**Audited branch:** `main` at commit `bb764a0b61cbf813d4abc687ef6c596243abc929`  
**GUI version in source:** 1.44 (`VERSION`, `gui/main.py`)  
**Inventory:** 71 non-test Python files; 64 Python test files (source-tree inventory).  
**Purpose:** Let a different GUI or AI coding assistant integrate the *existing* engine without cloning/reimplementing the current PySide6 screens.

## Executive summary

Route-Mate imports Karl's circuit exports, validates net assignments, derives footprints and board geometry, places components, routes horizontal copper with cuts and jumper wires, and checks connectivity and provisional physical geometry. **Quick Solve** is the main solver exposed to the existing desktop GUI. **Hell Mode** is a separate experimental deep-search CLI and is not yet a physically certified solver or a complete GUI feature. The same JSON project model is passed among modules.

**Recommended boundary:** New GUI (any toolkit) → a small Python service or direct Python function calls → `solve/desktop_integration.py` / `solve/parallel_quick.py` (Quick Solve), `hellmode/demo.py` (Hell Mode exploration), `solve/verify.py` plus `hellmode/verify_layout.py` (independent results), `render/standalone_bridge.py` (SVG boards). Let the GUI display states; **do not implement your own copper/net legality rules**.

## 1. Canonical project and result conventions

The engine uses Python dictionaries parsed from JSON. Important fields (check specific input schema before constructing them):

```json
{
  "board": {"rows": 24, "cols": 56, "cuts": [], "wires": []},
  "components": [{"id": "C1", "defId": "...", "boardPos": {"row": 0, "col": 0}}],
  "componentDefs": [],
  "netAssignments": [{"componentId": "C1", "pinId": "1", "netId": "N1"}]
}
```

This is an **illustrative shape**, not a valid ready-to-solve project on its own. The actual collector preserves source identifiers and additional footprint, lock, orientation and metadata fields. Jumper records use `{"id": "W1", "from": {"row": 0, "col": 1}, "to": {"row": 4, "col": 1}}`. Between-hole cut records use `{"row": 2, "col": 4, "kind": "between"}`. Logical holes are integer `(row, col)` coordinates, zero-based. Pitch is 2.54 mm in the physical conversion layer. An on-board `locked` component must not move. Off-board/edge policies are more nuanced; use the engine's policy functions.

Typical result objects have `status`, `project`, `errors`, plus operation-specific verification/metrics/history keys. **Always check `status` before using `result['project']`**, and never treat `ROUTED` / electrical `PASS` as measured physical `BUILD_READY`.

## 2. Source module inventory: import, contracts and preparation

| Module | Reuse purpose / main entry points | Relevant test files |
|---|---|---|
| `collect.py` | CLI collector. Validates/normalises Karl project JSON, parses KiCad footprint definitions, merges `.pretty` footprints, compares `.net` node count, produces campaign project/index/manifest. Functions: `validate_project`, `merge_footprints`, `normalise_like_gui`, `estimate_board`, `main`. | `test_project_import_adapter.py`, `test_collector_geometry_assumptions.py`, `test_electrical_sanity.py`, `test_pipeline_adapters.py` (related contracts, not all direct collector tests) |
| `collector_geometry.py` | Builds deterministic **assumed** local package geometry for exploratory quality warnings; `build_assumed_geometry`. Assumed ≠ measured physical dimensions. | `test_collector_geometry_assumptions.py`, `test_capacitor_render_contract.py`, `test_assumed_25d_provenance.py` |
| `geometry_sidecar.py` | Persists/loads assumed geometry tied to a project snapshot; evaluates nominal package contact/edge warnings. `load_or_create`, `make_document`, `inspect_assumed_contacts`, `assess_saved_board`. | `test_geometry_sidecar_integration.py`, `test_assumed_25d_provenance.py`, `test_saved_audio_geometry_baseline.py`, `test_saved_moto_geometry_baseline.py` |
| `capacitor_contract.py` | Normalises capacitance and maps it to nominal capacitor artwork/package contract; `capacitance_farads`, `resolved_capacitor_package`, `capacitor_body_spec`. | `test_capacitor_render_contract.py` |
| `prepare/sanity/electrical.py` | Input preflight: checks JSON connectivity and optionally compares with KiCad `.net` connectivity; `run_electrical_sanity`. Not an actual routed-board connectivity proof. | `test_electrical_sanity.py`, `test_pipeline_adapters.py` |
| `prepare/presolve.py` | Read-only footprint topology/orientation/board-sizing intelligence and jumper-lane/cut lower-bound hints; `analyse_project`. Advisory, not a legal route. | `test_presolve.py`, `test_presolve_pipeline.py`, `test_quick_fit_geometry.py` |
| `pipeline/contracts.py` | UI-independent serialisable pipeline records: `Finding`, `StageResult`, `PipelineContext`, `project_sha256`, `make_finding_id`. | `test_pipeline_contracts.py` |
| `pipeline/adapters.py` | Wrap existing IN/PREPARE/SOLVE/verify outputs as common stage records without changing engine logic. Entries include `collector_stage_result`, `presolve_stage_result`, `quick_fit_stage_result`, `route_stage_result`, `verification_stage_result`. | `test_pipeline_adapters.py`, `test_project_import_adapter.py`, `test_solve_pipeline_adapters.py`, `test_pipeline_test_adapter.py` |
| `pipeline/orchestrator.py` | `PipelineRun.create/load/handoff/record_stage/save` manages lifecycle, immutable-by-convention project handoffs, hash provenance and a `.routemate-state.json` sidecar. | `test_pipeline_orchestrator.py`, `test_presolve_pipeline.py` |
| `pipeline/__init__.py`, `prepare/sanity/__init__.py` | Package markers / exports. | Covered by importing the relevant packages in tests. |

## 3. Shared logical and physical geometry

| Module | Reuse purpose / public interface | Relevant tests |
|---|---|---|
| `board_geometry.py` | Core logical footprint/grid model, `BoardGrid`, `BUILTIN_DEFS`, `resolve_definition`, `component_geometry`, `rotate_offset`. Body cells are **logical grid occupancy**, not measured can/package envelopes. | `test_board_geometry.py`, `test_quick_fit_geometry.py`, `test_physical_geometry.py` |
| `physical_geometry.py` | Converts grid-hole positions, between-hole cuts and jumper segments to exact physical coordinates; geometric intersection and cut-access helper functions, `project_geometry_confidence`. These helpers alone do not certify full 2.5D construction access. | `test_physical_geometry.py`, `test_nominal_pad_access.py`, `test_assumed_25d_provenance.py` |
| `adjacency.py` | Detects same-hole / continuous-strip adjacency conflicts for different-net pads: `hole_index`, `adjacency_conflicts`, `candidate_conflicts`. | `test_adjacency.py` |
| `placement_policy.py` | Shared off-board mounting determination via `is_off_board_component` (including an explicit Moto fixture exception). | `test_quick_fit.py`, `test_quick_place.py`, `test_default_body_spacing.py` (cross-module coverage) |
| `solve/wire_keepout.py` | Conservative logical/artwork-derived jumper restrictions: `component_keepouts`, `vertical_gap_keepouts`, `wire_keepout_errors`. Not measured clearance. | `test_wire_keepout.py`, `test_keepout_broadphase.py`, `test_nominal_pad_access.py` |
| `solve/clearance_25d.py` | Explicit 2.5D clearance evaluator from **supplied** physical dimensions, `classify_jumper`. Does not invent standoffs. | `test_clearance_25d.py`, `test_clearance_25d_integration.py` |
| `solve/clearance_25d_verify.py` | Separately implemented physical-clearance verdict for identical normative cases, `verify_jumper_25d`. This is not a whole-board physical certification. | `test_clearance_25d.py`, `test_clearance_25d_integration.py` |

## 4. Quick Solve and production solver modules

| Module | Reuse purpose / main entry points | Relevant tests |
|---|---|---|
| `solve/quick_fit.py` | Production net-aware deterministic placement with real board bounds, locked components, soft congestion/spacing preferences; `quick_fit(project, clearance=1, ...)`. | `test_quick_fit.py`, `test_quick_fit_geometry.py`, `test_default_body_spacing.py`, `test_gui_edge_slide_search.py` |
| `solve/quick_place.py` | Simpler deterministic first-fit placement; `quick_place(project)`. Useful baseline / fallback, not primary feedback portfolio. | `test_quick_place.py` |
| `solve/slide_fit.py` | Enumerates hard edge-slide anchor placements and executes placement retries; `edge_slide_positions`, `slide_fit`. | `test_slide_fit.py`, `test_gui_edge_slide_search.py` |
| `solve/placement_feedback.py` | Main routing-aware placement feedback engine. `solve_with_feedback(project, attempts=24, clearance=1, body_spacing_holes=1, progress=..., cancelled=..., ...)`; attempts placed+rerouted candidates, checks before keeping a result. | `test_placement_feedback.py`, `test_default_body_spacing.py`, `test_gui_141_controls.py`, `test_solve_cancellation.py` |
| `solve/hole_router.py` | Negotiated-congestion hole-graph router, `route_holes(project, iterations=24, expansion_budget=600000, cancelled=...)`. **Only for projects with empty cuts/wires**. Derives routing and cuts from owned holes; internally assesses grid legality. | `test_hole_router.py`, `test_multihop_synthetic.py`, `test_keepout_broadphase.py` |
| `solve/route.py` | Legacy/incremental copper router, `route_copper(project, vertical_only=False, quick_mode=False, ...)`. Preserves existing manual cuts and jumpers; verifies connectivity. | `test_route.py`, `test_multihop_synthetic.py`, `test_transactional_route.py` |
| `solve/transactional_route.py` | Bounded speculative cut search around strict copper routing; `route_transactionally`. | `test_transactional_route.py` |
| `solve/island_graph.py` | Read-only copper-island / possible vertical-jumper graph; `find_vertical_chain`, `route_with_island_graph`. A search/diagnostic primitive. | `test_island_graph.py` |
| `solve/skeleton.py` | Experimental deterministic sequence-pair rectangular placement decoder; `decode_sequence_pair`. **Not** the integrated production solver or a full Karl V5 port. | `test_skeleton.py` |
| `solve/quick_rules.py` | Quick Mode grid-level jumper/body/pin audit; `quick_wire_error`, `quick_audit`. Nominal, not measured 2.5D certification. | `test_route.py`, `test_wire_keepout.py`, `test_hole_router.py` (integrated coverage) |
| `solve/verify.py` | **Independent electrical** copper connectivity verifier, `verify_project(project)`; checks cuts, jumper connections, opens/shorts without using routing heuristics. | `test_verify.py`, `test_route.py`, `test_hole_router.py`, `test_solved_export_import.py` |
| `solve/quality_audit.py` | Measurement-only report of wire length, cuts, geometry and related costs; `audit_project`. | `test_quality_audit.py` |
| `solve/render_quality.py` | Provisional UI-friendly routing quality number / reasons; `score_render`. Never a physical-pass certificate. | `test_render_quality.py` |
| `solve/solution_quality.py` | De-duplicate and rank independently verified candidates, `solution_signature`, `candidate_quality`. | `test_parallel_quick.py`, `test_placement_feedback.py` (integration) |
| `solve/desktop_integration.py` | **Preferred toolkit-neutral Quick Solve call**: `solve_for_display(project, attempts=24, body_spacing_holes=..., progress=..., cancelled=...)`. Adapts shared solver result to GUI consumption while preserving locks. | `test_desktop_integration.py`, `test_gui_solve.py`, `test_gui_edge_slide_search.py`, `test_solve_pipeline_adapters.py` |
| `solve/parallel_quick.py` | **Preferred CPU-parallel Quick Solve call**: `solve_parallel_for_display(project, workers=3, attempts=24, body_spacing_holes=1, progress=..., cancelled=...)`; partitions one fixed attempt budget across worker processes; finds up to two distinct routes. | `test_parallel_quick.py`, `test_gui_141_controls.py`, `test_solve_cancellation.py` |
| `solve/__init__.py` | Package marker / exports. | Imports throughout solve tests. |

**Important nuance:** README's phrase “verified route” currently means independent electrical/grid checks in code, **not** the fully specified measured wire/body, cut access and assembly-ready standard. The new GUI must expose this distinction.

## 5. Hell Mode experimental modules (separate from production Quick Solve)

| Module | Purpose / public interface | Relevant tests |
|---|---|---|
| `hellmode/pad_geometry.py` | Independently reconstructs footprint pin holes and assigned net ownership from raw project, `collect_pad_holes`. | `test_hellmode_electrical_model.py`, `test_hellmode_strict_occupancy.py` |
| `hellmode/copper_model.py` | Independent strip-segment graph and wire-to-net ownership, `reconstruct_electrical`. | `test_hellmode_electrical_model.py`, `test_hellmode_net_ripup.py` |
| `hellmode/strict_occupancy.py` | Independent STRICT **2D** gap/landing/pin interference audit, `audit_strict_occupancy`; it is not 2.5D certification. | `test_hellmode_strict_occupancy.py`, `test_hellmode_diagnostic.py` |
| `hellmode/verify_layout.py` | Conservative combined independent electrical + strict 2D facade, `verify_layout`. Currently withholds `record_eligible=True` and physical PASS. | `test_hellmode_electrical_model.py`, `test_hellmode_strict_occupancy.py` |
| `hellmode/incremental_state.py` | Transactional reversible occupancy state: `TransactionalState`, `Transaction`, `move_wire`, `move_component`, rollback/commit, shadow-checkable counters. **Search state, not verifier.** | `test_hellmode_incremental_state.py` |
| `hellmode/topology_moves.py` | Cut-frozen strip-segment proposals, jumper endpoint-row changes, 1/2-wire detours: `StripSegments`, `topology_proposal`, `apply_topology_proposal`. | `test_hellmode_topology.py` |
| `hellmode/cut_moves.py` | Exploratory between-hole cut removal/shift and safely verified redundant-cut cleanup; `propose_cut_change`, `remove_redundant_cuts`. | `test_hellmode_cut_moves.py` |
| `hellmode/conflict_repair.py` | Targets illegal jumper gaps using 2D surrogate and independently rechecks committed 1/2-wire rebridges; `repair_conflicts`. | `test_hellmode_conflict_repair.py` |
| `hellmode/net_ripup.py` | Rips up and rebuilds an entire net's jumper tree through available strip islands; `rebuild_one_net`, `ripup_repair`. | `test_hellmode_net_ripup.py` |
| `hellmode/placement_search.py` | Transactionally moves unlocked components and rebuilds affected electrical nets, `move_and_rebuild`, `search_component_moves`. | `test_hellmode_placement_search.py` |
| `hellmode/diagnostic.py` | Classifies stacking clusters and calculates exact fixed-span column matching / Hall infeasibility witnesses, `diagnose`, CLI `python -m hellmode.diagnostic`. | `test_hellmode_diagnostic.py` |
| `hellmode/search_state.py` | Explicit tier barrier: graded union-find `InfeasibilityPenalty`, `SearchState`, `CertifiedRecord`; derived-cut proposals via `derive_required_cuts`, `grade_search_state`. Not itself a solved-board certification. | `test_hellmode_search_state.py` |
| `hellmode/hall_guided_repair.py` | Attempts clustered, two-jumper topology repair with penalised intermediate evaluation; `repair_hall_clusters`. | `test_hellmode_hall_guided_repair.py` |
| `hellmode/cluster_net_rebuild.py` | Compound transaction: rip up conflicting nets, derive affected cuts, rebuild complete net trees, then verify; `rebuild_conflicting_nets`. | `test_hellmode_cluster_net_rebuild.py` |
| `hellmode/demo.py` | **Current Hell Mode CLI search**: `optimize`, `optimize_portfolio`, `run_files`, `report_metrics`. Produces exploratory electrical output, not build-ready output. | `test_hellmode_demo.py`, `test_hellmode_portfolio.py`, `test_hellmode_hall_guided_repair.py`, `test_hellmode_cluster_net_rebuild.py` |
| `hellmode/__init__.py` | Package marker / exports. | Imported by Hell Mode tests. |

**Current confirmed benchmark context (three seeds × 150 moves, MOTOMIX):** the safety-gated run returns **44 jumpers, 57 cuts, 18 excess occupied gaps and 12 illegal hole findings**; status remains exploratory/electrical-only. A transient lower-gap result was deliberately rejected because it introduced additional illegal hole findings. No full physical RECORD is available.

### Hell Mode saved outputs

```bash
python3 -m hellmode.demo --input benchmarks/moto/motomix-autorouted.json \
  --moves 150 --seeds 3 --seed 1 --out /tmp/route-mate-hellmode-alpha

python3 -m hellmode.diagnostic \
  --input /tmp/route-mate-hellmode-alpha/best_electrical.json \
  --out /tmp/route-mate-hellmode-alpha/diagnostic.json
```

- `baseline_solved.json`: untouched starting project.
- `best_electrical.json`: best **electrically checked exploratory** board, not certified for construction.
- `run.json`: metrics, run provenance, seeds, move history, explicit `record_eligible: false`, physical status.
- `history.csv`: improving-record history within the exploratory tier.
- `diagnostic.json`: spatial clusters, per-gap matching bounds, Hall witnesses, exact-status proof limits.

## 6. Rendering and GUI modules

| Module | Purpose / how reusable | Relevant tests |
|---|---|---|
| `render/standalone_bridge.py` | **Production renderer bridge** to modified Karl stripboard-optimiser fork (Node/standalone renderer, initial fetch/build as needed). `render_project_data(project)` returns `(top_svg, copper_svg, log)`. It uses a temp JSON copy, adds coordinate labels and Route-Mate annotations. | `test_standalone_bridge.py`, `test_standalone_bundle.py`, `test_capacitor_render_contract.py`, `test_render_quality.py` |
| `render/render.py` | Public component-side API `render_front`, `render_front_svg`, `write_front_svg`; delegates to production renderer. | `test_front_renderer.py`, `test_standalone_bridge.py` |
| `render/_front.py` | **Legacy lightweight SVG test renderer only**; do not wire into production UI. | `test_front_renderer.py` |
| `render/_geometry.py` | Compatibility re-exports of `board_geometry.py`. | `test_board_geometry.py`, `test_front_renderer.py` |
| `render/__init__.py` | Package marker. | Rendering test imports. |
| `gui/main.py` | Monolithic **PySide6 frontend**: dialogs, board viewer, activity, progress, loading, saving, worker threads, source/solved views. Main UI classes: `BoardSizeDialog`, `SpacingDialog`, `LockDialog`, `BoardView`, `WorkflowChecklist`, `SolveWorker`, `RouteMateWindow`. Reuse as behaviour reference, **not necessary to copy**. | `test_gui_solve.py`, `test_gui_141_controls.py`, `test_gui_edge_slide_search.py`, `test_desktop_integration.py`, `test_solved_export_import.py` |
| `run_gui.py` | Desktop startup entry point. Calls `multiprocessing.freeze_support()` and launches `gui.main`. | `test_gui_solve.py` / GUI smoke CI |

**Renderer dependency warning:** The production bridge is not just `pip install PySide6`; it expects its Node-based standalone renderer runtime or a built bundle. If another GUI cannot package that runtime, the next-best integration is to keep Route-Mate's Python backend + renderer in a local service and pass back SVG strings. Keep the attribution and distribution licence of the renderer fork.

## 7. Benchmark, profiling and tooling modules

| File(s) | Purpose | Test/usage relationship |
|---|---|---|
| `benchmark_moto_strict.py`, `benchmark_audio_strict.py` | MOTO/AUDIO board benchmarks under named strict routing/profile settings; do not confuse a benchmark's particular legality profile with full measured physical certification. | `benchmarks/moto/`, `benchmarks/audio/`; CI/CLI benchmarks |
| `benchmark_moto_feedback.py`, `benchmark_audio_feedback.py` | Tests Quick Fit + routing feedback on the two primary projects, with reproducible metrics. | `test_placement_feedback.py`, `test_hole_router.py` plus end-to-end CI |
| `benchmark_route_order.py` | Explores routing-order strategies. | CLI benchmark, `test_route.py` |
| `profile_solve.py`, `speed_probe.py`, `time_tests.py` | Runtime profiling, CPU/solver startup probing and timing; **not engine APIs**. | Development/CI performance diagnostics |
| `debug_slide.py` | Edge-slide diagnostic script. | `test_slide_fit.py` |
| `tools/audit_capacitor_renderer.py` | Capacitor artwork/assumption audit tool. | `test_capacitor_render_contract.py` |
| `tools/benchmark_quick_workers.py`, `tools/smoke_process_pool.py` | Multiworker Quick Solve capacity/startup/performance probes. | `test_parallel_quick.py` |
| `tools/hellmode_m1_spike.py` | Original Hell Mode strict occupancy development/diagnostic spike. **Prefer current `hellmode/` modules.** | `test_hellmode_m1_spike.py` |

## 8. Complete test file catalogue (64 files)

All test filenames below were present in the audited `main` tree. Grouping is by the most directly relevant feature; **groups do not claim exclusive coverage of only those modules**.

**Input, data contracts, pipeline (10):**
`test_electrical_sanity.py`, `test_collector_geometry_assumptions.py`, `test_project_import_adapter.py`, `test_pipeline_contracts.py`, `test_pipeline_adapters.py`, `test_pipeline_orchestrator.py`, `test_pipeline_test_adapter.py`, `test_presolve.py`, `test_presolve_pipeline.py`, `test_capacitor_render_contract.py`.

**Geometry, clearance and board (10):**
`test_adjacency.py`, `test_board_geometry.py`, `test_physical_geometry.py`, `test_assumed_25d_provenance.py`, `test_clearance_25d.py`, `test_clearance_25d_integration.py`, `test_geometry_sidecar_integration.py`, `test_keepout_broadphase.py`, `test_nominal_pad_access.py`, `test_wire_keepout.py`.

**Quick placement, routing and verification (14):**
`test_quick_fit.py`, `test_quick_fit_geometry.py`, `test_quick_place.py`, `test_default_body_spacing.py`, `test_slide_fit.py`, `test_placement_feedback.py`, `test_hole_router.py`, `test_route.py`, `test_transactional_route.py`, `test_island_graph.py`, `test_multihop_synthetic.py`, `test_skeleton.py`, `test_verify.py`, `test_quality_audit.py`.

**GUI, rendering, export, parallelism and integration (13):**
`test_desktop_integration.py`, `test_gui_141_controls.py`, `test_gui_edge_slide_search.py`, `test_gui_solve.py`, `test_parallel_quick.py`, `test_solve_cancellation.py`, `test_solve_pipeline_adapters.py`, `test_solved_export_import.py`, `test_front_renderer.py`, `test_standalone_bridge.py`, `test_standalone_bundle.py`, `test_render_quality.py`, `test_saved_audio_geometry_baseline.py`.

**Additional saved-board geometry baseline (1):**
`test_saved_moto_geometry_baseline.py`.

**Hell Mode (16):**
`test_hellmode_cluster_net_rebuild.py`, `test_hellmode_conflict_repair.py`, `test_hellmode_cut_moves.py`, `test_hellmode_demo.py`, `test_hellmode_diagnostic.py`, `test_hellmode_electrical_model.py`, `test_hellmode_gate_predicate_contract.py`, `test_hellmode_hall_guided_repair.py`, `test_hellmode_incremental_state.py`, `test_hellmode_m1_spike.py`, `test_hellmode_net_ripup.py`, `test_hellmode_placement_search.py`, `test_hellmode_portfolio.py`, `test_hellmode_search_state.py`, `test_hellmode_strict_occupancy.py`, `test_hellmode_topology.py`.

The last recorded CI run after the compound-net modules showed **129 passing Hell Mode tests**; the full repository suite has more tests and must be run to establish its current total on your checkout. CI workflows in `.github/workflows/` include routing regression, MOTO automatic routing, desktop GUI smoke and benchmark checks.

### Commands to verify a new GUI integration

From the repository root (with Python dependencies installed):

```bash
python3 -m pip install -r requirements-gui.txt
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 -m unittest discover -s tests -p 'test_hellmode_*.py' -v
python3 run_gui.py
```

**Warnings:** `python3 -m unittest discover` *without* `-s tests` has historically collected no tests. Installing GUI requirements installs PySide6; rendering may also require a separate Node production-renderer bundle. Route-Mate's official GUI currently does not give you a finished integrated Hell Mode button, even though Hell Mode has a CLI.

## 9. Minimal alternative-GUI integration

For a **new Python GUI**, launch a worker/process around the toolkit-neutral adapter, never solve synchronously on the UI event loop:

```python
from solve.desktop_integration import solve_for_display
from solve.verify import verify_project
from render.standalone_bridge import render_project_data

# project is a validated, prepared Route-Mate project dict.
result = solve_for_display(project, attempts=24, body_spacing_holes=1)
if result.get("status") == "ROUTED" and result.get("project"):
    solved = result["project"]
    electrical = verify_project(solved)
    if electrical.get("status") == "PASS":
        top_svg, copper_svg, render_log = render_project_data(solved)
        # Give SVG strings and separate electrical/physical status to your GUI.
else:
    # Display result.get("status") and result.get("errors", []).
    pass
```

For native multicore operation, use `solve.parallel_quick.solve_parallel_for_display(project, workers=3, attempts=24, body_spacing_holes=1)`, with a proper `if __name__ == '__main__'` multiprocessing entrypoint for spawned processes. The progress and cancellation callbacks supported by the adapters let the new GUI show activity and a Stop button. Always retain/copy the input snapshot so failed searches don't destroy the imported project.

For an Electron/web/Swift/C#/Flutter GUI, a **thin Python backend service** can read/write the same project JSON, receive solve requests, run the above functions in a Python worker, and return status/metrics/SVG strings. **The repository does not currently ship a general HTTP/REST API**, so such a bridge is a small additional adapter—not a ready-made server. Never expose untrusted file paths or shell commands directly to remote clients.

The current Hell Mode callable `hellmode.demo.optimize_portfolio(project, moves=150, seed=1, seeds=3)` returns `(best_electrical_project, manifest)` without a GUI dependency, but its output must be labelled **EXPERIMENTAL / ELECTRICAL ONLY**. For viewing a previous Hell Mode file, render `best_electrical.json` with the same production renderer and overlay warnings from `hellmode.verify_layout.verify_layout`.

## 10. What's portable and what's not

**Highly reusable:** canonical project JSON, `pipeline/`, `prepare/`, `board_geometry.py`, `physical_geometry.py`, `solve/` (non-Qt), `hellmode/` (non-Qt), `render/standalone_bridge.py`, audit/verification functions and almost all tests.

**UI-specific:** `gui/main.py`, Qt signals/threads/dialogs, `run_gui.py` and PyInstaller/macOS bundling scripts. You can replace them while keeping Python engine files unchanged. The custom renderer and Node runtime can be retained as a service or replaced only after establishing parity for footprints and artwork.

**Not safe to borrow as a 'finished verified board' engine:** Hell Mode's best electrical candidate, nominal assumed geometry from collectors, 2D-only occupancy checks, placeholder record gates. Full 2.5D clearance, measured body geometry, cut tool access and final assembly verification are not implemented end-to-end.

## 11. Source, docs, licence and handover checklist

- Repository: https://github.com/bigbadevilaussie-hue/Route-Mate
- Source specification: `docs/PHYSICAL_MODEL_SPEC.md` (locked).
- Geometry amendments: `docs/PHYSICAL_MODEL_25D_AMENDMENT.md`, `docs/PHYSICAL_ASSUMED_SOURCE_AMENDMENT_V1_2.md`.
- Architecture: `docs/SOLVER_ARCHITECTURE_DECISION.md`.
- GUI design and status: `docs/GUI.md`.
- Data handoff: `docs/MODULE_IO_AND_HANDOFF_AUDIT.md`.
- Current blockers: `docs/GATE1_HANDOFF.md`, `docs/HELLMODE_ACCEPTANCE_PREDICATES.md`.
- Dependencies: `requirements-gui.txt` (`PySide6>=6.7,<7`).
- Golden/project fixtures: `benchmarks/moto/`, `benchmarks/audio/`, `tests/fixtures/`.
- Renderer copyright: Karl/Karlo Funke original stripboard editor and user's modified `stripboard-optimiser` fork. Renderer licence text at `licenses/GPL-3.0.txt` and README; if copying, linking or distributing reused GPL-covered code, comply with its actual licence obligations. **Do not assume the entire Route-Mate repository's licence solely from the renderer's GPL text; check each source's applicable licence and contributor ownership before redistribution.**

**New GUI developer's shortest safe sequence:** clone the pinned repository, inspect canonical JSON and lock semantics, run the complete test suite, call `solve_for_display`/`solve_parallel_for_display` from a background worker, call independent electrical verification, use production SVG renderer, display physical-state warnings separately, add Hell Mode CLI as explicitly experimental, then add adapter-level end-to-end tests with saved MOTO/AUDIO projects. No second copy of the routing logic is needed.

---

*Inventory and code signatures were inspected from the current GitHub repository tree and source files. Test-to-module relationships include direct tests and cross-module integration tests, not a measured per-function coverage analysis. A handover guide does not substitute for the source code or licence review.*
