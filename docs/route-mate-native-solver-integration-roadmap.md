# Integration roadmap: Route-Mate GUI + Stripboard Optimiser native solver

> **Historical architecture decision (24 Nov 2026).** The import-only
> Route-Mate GUI **has since been transplanted** as GUI 2.01; original board
> sizing, spacing/lock review and schematic SVG/PNG rendering work, but
> **Pass 1/Pass 2 native CLI adapter remains disconnected**.
> The “transplant later” phase descriptions below record the original plan,
> not the current repository status. Read
> [the current audit](REPOSITORY_AUDIT_2026-11-24.md) first.

**Decision date:** 24 November 2026  
**Status:** architecture and sequencing decision, **not** authorization to migrate the GUI yet  
**Primary repository:** `bigbadevilaussie-hue/stripboard-optimiser`  
**Donor repository:** [Route-Mate](https://github.com/bigbadevilaussie-hue/Route-Mate), audited handover commit `bb764a0b61cbf813d4abc687ef6c596243abc929`  
**Destination:** Route-Mate's much richer PySide6 experience driving **this repository's native C/TypeScript solver**, with selected Route-Mate import, orchestration, render, audit, and sidecar capabilities.

## Executive decision — solver first, GUI later

1. **Native solver is authoritative.** Continue native CLI development and benchmarks in this repository. Do not port or invoke Route-Mate Quick Solve, hole router, placement feedback, or Hell Mode as replacement production optimisation paths.
2. **The current Stripboard Optimiser Tk/web GUI is not the target GUI.** It can remain stale during native development. Avoid spending effort rebuilding a second elaborate UI here. Route-Mate's PySide6 GUI v1.44 becomes the target front end **after quality and reproducibility gates**.
3. **Bring forward only independent, read-only diagnostic/validation ideas that demonstrably help solve quality now.** Preserve source attribution and review licences. Initially build an *optional sidecar/probe*, not a new fitness function. Never silently modify native C annealing, RNG, candidate selection, or historical strict benchmarks.
4. **Quality outranks raw speed.** Strict electrical completeness, physical constraints, locked board and components, drill/no-stack settings when requested, actual width/rows, and no illegal crossings or noncompliant wires must be met before a candidate wins. Do not confuse `Q0`, `ROUTED`, electrical PASS, strict 2D pass, and measured build-ready certification.
5. **No backwards benchmark changes.** Keep 20k baseline and original 80-run/36-run MOTO snapshots, and 100-run AUDIO 5k–50k results, untouched. MOTO C1's corrected value affects geometry: compare old and corrected input only with explicit fixture provenance.

## Audited systems and specific boundaries

| Subsystem | Donor Route-Mate code | Intended disposition |
|---|---|---|
| GUI and human workflow | `gui/main.py` (2,367 lines at audited commit), `run_gui.py`, PySide6, board viewers, top/copper views, dialogs, activity, Stop, source/solved comparison | **Transplant later** as primary application, after native solver passes gates |
| Native optimiser | This repo's `src/frontend/components/stripboard/v5wasm/`, `autoLayout5.ts`, `layout2/finish.ts`, and `src/frontend/tests/solver/v5Solve.js` | **Keep and improve here**; do not replace with Route-Mate search |
| Quick Solve | Route-Mate `solve/parallel_quick.py`, `solve/desktop_integration.py`, `solve/placement_feedback.py`, `solve/hole_router.py` | **Bypass** optimisation. Replace GUI worker invocation with adapter to this repo's native solver |
| Experimental Hell Mode | Route-Mate `hellmode/demo.py`, search / topology / rip-up modules | **Do not use as main engine**. Mine individual diagnostics only with parity tests |
| Import | `collect.py` and `prepare/sanity/electrical.py` | Reuse later, subject to nonmutating source/UUID/netlist/footprint provenance checks |
| Pre-solve | `prepare/presolve.py` | **High-value read-only diagnostic candidate now**; report constrained footprint topology, jumper feasibility, size warnings and possible starting budget, never a guaranteed solver setting |
| Congestion explanation | `hellmode/diagnostic.py` | **High-value optional diagnostic candidate now**, Hall-deficient gap/column witness and bounded exact fixed-span search; tightly scoped and not a full solver feasibility proof |
| Electrical verification | `solve/verify.py` + `adjacency.py`, `board_geometry.py`, `placement_policy.py` | **High-value independent oracle** in separate process/test harness; compare with native verifier, investigate disagreements, never accept worse validation |
| Geometry and nominal clearance | `physical_geometry.py`, `geometry_sidecar.py`, `solve/clearance_25d*.py` | Reuse as advisory/independent audits; assumed dimensions cannot certify physical board |
| Sidecar/provenance | `pipeline/contracts.py`, `pipeline/orchestrator.py`, `pipeline/adapters.py` | **Transplant later**, keep immutable input hashes, stage findings, saved run state, and versioned solver run metadata |
| Renderer | `render/standalone_bridge.py` and existing Node renderer | **Transplant later**, maintain front and copper SVG parity and GPL/licence obligations |

### Concrete code evidence

At audited commit, Route-Mate's `gui/main.py:SolveWorker.run()` calls `solve.parallel_quick.solve_parallel_for_display(project, workers=..., attempts=24, body_spacing_holes=..., progress=..., cancelled=...)`. `RouteMateWindow.solve_board()` creates the worker and assumes a 24-attempt progress range. **That is the first adapter seam**, not an invitation to make native moves look like Route-Mate placement attempts. Native CLI `v5Solve.js` consumes `--data <dir>/projects/1.json --id 1 --seed <n> --moves <n> --native 1`, with `--routing-preference wires|cuts`, optional `--drilled 1`, `--nostack 1`, `--strict 1`, and `--save`. It emits one JSON result plus timing diagnostics and exit code 2 for a strict-invalid result. The GUI worker must treat exit 2 as **completed but nonqualifying**, not a process crash.

Route-Mate's `hellmode/diagnostic.py` can produce a rigorous Hall witness only for its **fixed-placement, fixed-cuts, fixed endpoint-rows / copper-memberships, column-reassignment model**. It cannot prove that moving components, rerouting entire nets or changing cuts is impossible. When search exceeds its node budget, it must report **UNKNOWN**, not UNSAT. Read-only `prepare/presolve.py` similarly offers advisory topology/packing estimates, not a physical proof.

## Phase 0 — immediately: preserve engine and establish a trustworthy baseline

**Do now, before any GUI work.**

- Freeze reproducible input snapshots and SHA256, source commit, native/WASM build fingerprints, board size, locks, cut policy, stacking policy, rotation, diagonal policy, routing preference, seeds, move count, run IDs, selected winner, failure reasons, and run timing. Saved JSON layouts and intermediate diagnostics must be traceable to inputs.
- Retain native `--strict 1` checking and an explicitly configured independent checker; never infer physical build readiness solely from `quality:0`.
- Keep **MOTO and AUDIO separate** when estimating Pass 1 budgets. AUDIO: 19 components, 85 assigned pins, 29 nets, large custom bodies; MOTO: 44 components, 123 assigned pins, 35 nets, both locked 24×56. A pin-ratio estimate is only a hypothesis; calibrate with measured strict survivors and quality per CPU-second.
- Preserve the v1.63 AUDIO test: 100 native solves, 5k–50k in 5k increments, 10 seeds per rung; six strictly clean in the user-provided transcript; best 13 wires/41 cuts (20k seed 6 and 45k seed 6); 50k 0/10. Default knife/stack allowances apply, so **these are not drilled-only/no-stack results**.
- Collect per-seed `ladder_results.csv` failure criteria to classify column shifts, true slants, crossings, geometry, electrical and issues. Do not extrapolate optimum from ten seeds per budget.

**Exit gate:** exact fixture and seed reproducibility; strict invalid layouts never qualify; unchanged native CLI signatures against frozen controls.

## Phase 1 — optional donor diagnostic pilot (ahead of GUI migration)

**Read and isolate donor code only when a concrete paired experiment exists.** Priorities, in order:

1. **Independent electrical oracle**: run Route-Mate `solve/verify.py` as an offline check on saved native layouts (dependencies: `adjacency.py`, `board_geometry.py`, `placement_policy.py`, etc.). Compare net opens, shorts, strip semantics, drilled-hole versus between-hole cuts, off-board parts, rotations and lock preservation. Generate mismatch reports, not automatic repairs. Add golden tests before trusting it.
2. **Congestion feasibility diagnostics**: run `hellmode/diagnostic.py` offline for failing native layouts with column-changing jumpers/stacking or crossover problems. Its dependencies include copper model, strict occupancy and strip-segment construction. Distinguish proven *fixed-span infeasible*, bounded UNKNOWN, and heuristically repairable. Correlate with existing CLI failure matrix and routing hotspots.
3. **Read-only presolve metrics**: extract `prepare/presolve.py` outputs or reproduce the measures in a pure reporting tool to examine footprint packing, net-degree distribution, lock pressure and cut/jumper lower bounds. Test whether they **predict** Pass 1 sweet spots on held-out projects. Do not add speculative unverified heuristics to C annealing.

**Initial decision at this commit:** no donor Python source copied into the native solver yet. The diagnostic functions are useful but **not standalone drop-ins**, have dependencies and distinct semantics, and could corrupt scoring or misclassify legality if inserted directly. This is a deliberate risk boundary, not a claim that the capabilities were already integrated.

**Exit gate:** isolated diagnostic runs on AUDIO/MOTO, differences recorded, zero changed solver fingerprints, measured improvement in diagnosis or verified survivor selection. Port only proven semantics and the necessary tests with attribution/licence review.

## Phase 2 — solve quality and tournament gates, still CLI-only

- Correct native objective/physical penalty mismatches through **option-gated, paired-seed experiments**. Especially investigate native anneal not directly penalising no-wire-stacking, and repeated column shifts/crossings in finishes. Do not patch finish selection based only on unsupported theory.
- Evaluate performance experiments separately: early rejection of failing mutations while preserving RNG sequence, and bounded routing repair. For speed claims use serial `--jobs 1` and consistent input/budget/environment; for quality throughput use representative multi-process tests.
- Define qualification precisely for each configuration: Q0, zero opens/shorts, all assigned pins represented, zero geometry faults, required cut type, stacking and wire-direction rules, no crossings, locked board and component preservation, verifiable saved solution.
- Pass 1 maximises **high-quality, diverse valid survivors per CPU-second**; Pass 2 spends deeper budgets on *all qualified survivors* and maintains a fair winner selection. Design ranking so a physically invalid lower-wire solution cannot defeat a valid one.
- Run paired budget tests on MOTO, corrected C1 MOTO/MOTOMIX, AUDIO, and additional representative projects. Test budget recommendation predictions rather than assuming AUDIO and MOTO share a fixed 20k optimum.

**Exit gate for GUI migration:** chosen representative configurations reliably produce valid candidates at a useful rate; Pass 1/Pass 2 accounting, selection, cancellation, serial/parallel determinism and saved JSON round-trip are exercised in automated CLI regressions. Success rates should be measured and agreed, not invented here.

## Phase 3 — build a thin native solver adapter, still without transplanting GUI

Expose a stable toolkit-independent job contract, preferably in Python subprocess orchestration over the existing Node/native CLI (so no rewrite of the native engine).

**Proposed request** (schema to be finalized by integration tests): `input_snapshot`, `seed_base`, `seed_count`, `moves`, `pass`, `board_lock`, `drilled_cuts_only`, `no_stacking`, `allow_rotation`, `wire_direction_policy`, `routing_preference`, `threads`, `output_root`.

**Proposed events:** `job_started`, `seed_started`, `seed_progress` (only when actually available), `seed_finished` (metrics, fingerprint, strict failures, duration), `survivor_qualified`, `pass_started`, `pass_finished`, `candidate_saved`, `cancel_ack`, `job_finished`.

**Proposed outputs:** immutable input and configuration SHA256, solver and native module versions, all seed results/validity, qualified survivors, best candidate and saved project JSON, independent verification report, original stdout/stderr, stage provenance. Never rewrite a failed solution as successful. Preserve UUIDs/positions and original source separately.

Constrain option mapping to what the native solver **actually supports**. If a GUI control (e.g. certain diagonal/rotation policy) has no implemented enforcement in native CLI, disable it or display unsupported status rather than pretending it works. Use a dedicated process group for reliable cancellation and permit retained per-seed audit logs.

**Exit gate:** automated adapter tests demonstrate same fingerprints and strict flags as direct CLI for fixed inputs, seeds and options, including exit-2 invalids, crashes, cancellation and resumption.

## Phase 4 — transplant Route-Mate GUI + sidecar after solver/adapter gates

- Port the inspected PySide6 GUI, import/preparation workflows, sidecar stage management and renderer; remove calls to Route-Mate `solve_parallel_for_display` and current 24-attempt Quick Solve assumption. Call the native adapter in a background worker.
- Preserve superior lock, edge/slide and board-dimension dialogues, but gate each option behind correct native semantics. Reconcile component rotation, flexible footprints, offboard connectors and physical constraints.
- Replace `Quick Solve` solver terminology with **Pass 1 / Pass 2 native tournament** state: seeds attempted, strict-qualified, shortlisted, timing/ETA from observations, stop/resume, no retroactive invalid promotions, and per-candidate forensic record.
- Keep Route-Mate independent electrical audit, physical-assumption warnings and rendered front/copper boards, but make category/status distinctions prominent. Do not show nominal 2.5D models as measured certification.
- Store sidecar and all provenance next to source/saved layout; ensure re-opening a result cannot silently overwrite its original input or invalidate a previously approved locked component.
- Keep current Stripboard Optimiser GUI untouched/deprecated unless required for an explicit emergency fallback.

**Exit gate:** Route-Mate GUI input → native adapter → same saved strict-checked layout as CLI → independent Route-Mate verifier → both SVG views → user-visible pass/tournament dashboard. Smoke tests on corrected MOTO/MOTOMIX and AUDIO.

## Phase 5 — packaging and licensing

- Compare licences for individual donor modules, the Karl/Funke renderer fork, SVG/Node standalone runtime and any third-party bundled dependencies. Route-Mate's handover notes `licenses/GPL-3.0.txt` for renderer but **does not establish a blanket licence for every Python file**.
- Before copying or redistributing code, preserve required notices and applicable GPL source obligations. Confirm attribution and dependencies. Keep tests and golden files when transplanting audited code.
- Ship macOS desktop packaging only after native runtime/WASM/Node, Python/PySide6, renderer and assets can be packaged and tested together.

## Immediate decisions and non-goals

**Do now:** improve the native solver's strict yield, preserve the AUDIO/MOTO benchmark data, and run optional independent diagnostics under frozen inputs. Keep the Route-Mate code and handover as reference.

**Do not do now:** merge GUI trees, reimplement the Qt screens in Tk/web, replace native annealing with Quick Solve/Hell Mode, treat a new UI as a solver-quality fix, or claim Hall fixed-span infeasibility is global physical impossibility.

**Next implementation proposal:** after obtaining the 100-row AUDIO CSV and saved-board samples, build a standalone *read-only native-result diagnostic pilot* reporting strict failure types and Route-Mate-style constrained routing congestion, with tests that guarantee the solver's results remain bit-for-bit unchanged.

### Links and evidence

- [Route-Mate source and audited GUI](https://github.com/bigbadevilaussie-hue/Route-Mate/tree/bb764a0b61cbf813d4abc687ef6c596243abc929)
- [Route-Mate locked physical model](https://github.com/bigbadevilaussie-hue/Route-Mate/blob/bb764a0b61cbf813d4abc687ef6c596243abc929/docs/PHYSICAL_MODEL_SPEC.md)
- [Route-Mate GUI design](https://github.com/bigbadevilaussie-hue/Route-Mate/blob/bb764a0b61cbf813d4abc687ef6c596243abc929/docs/GUI.md)
- [Route-Mate experimental diagnostics](https://github.com/bigbadevilaussie-hue/Route-Mate/blob/bb764a0b61cbf813d4abc687ef6c596243abc929/hellmode/diagnostic.py)
- [Local native budget and failure matrix](native-cli-budget-sweep-v161.md)
- [Completed AUDIO 5k–50k ladder](native-audio-ladder-v163.md)
- [MOTO C1 correction and historical record](moto-c1-correction-v162.md)
