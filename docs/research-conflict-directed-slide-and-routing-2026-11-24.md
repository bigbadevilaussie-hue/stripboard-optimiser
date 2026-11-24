# Research: escaping failed USB Slide layouts through conflict-directed routing and placement

**Date:** 24 November 2026 (Australia/Brisbane). **Current branch:** `main` (original research drafted on the former feature branch). **Status:** research/engineering design, **not implemented or Mac-tested**. This document intentionally proposes **no production code changes during the in-progress exhaustive 200 seeds × 51 USB columns sweep**.

## Problem and empirical evidence

The current full Slide controller `scripts/run_motoex_native_full_slide_sweep.py` tries all **51 legal USB anchors independently for each seed**, stopping a seed only at its **first independently verified strict pass**. The user-provided terminal log shows seeds **1, 2, 3 and 4** each exhausting all 51 columns without a pass. At the time of the appended log, seeds 5–8 had begun and no strict pass had been shown. This is an **interim observation, not the final result of 200 seeds**. Some individual results are `NO_FEASIBLE_PLACEMENT` (empty 0W/0C) at this move budget; others are placed but fail electrical/physical checks. The 200-seed USB-fixed col47 reference was **0/200 strict passes** in 150.08s with the same 25k, knives-allowed, stacking-allowed settings; seed 157 was electrically complete with **one body crossing**, seed 129 electrically complete with **one nonvertical wire**. These are particularly good deterministic post-repair fixtures.

**Do not confuse**: failing a 25k anneal for one fixed USB column does not prove that column or the entire 24×56 board is infeasible.

## The core finding: relay routing is ALREADY implemented

The native `src/frontend/components/stripboard/v5wasm/route.c` is **not just a greedy direct jumper router**. It already has:

- A hard stripboard-specific separation between horizontal copper strips and vertical jumper wires.
- Two-vertical-hop relay routing through an empty strip or borrowable section of a donor copper strip: `findRelayBest()` around lines **678–730**.
- Comparison against the best direct wire: `search()` around lines **733–740**; relays are considered when a direct route is missing or has routing mess.
- A **nominal 32-candidate relay limit**: `MAX_RELAY_CANDS 32` around line **125**, with pruning around **946–966**. The implementation preserves **all pin-free relay groups** first, then selects the widest donor tails to fill remaining slots. Thus “32 total always” is not strictly true when free groups exceed 32; **the important limitation is that donor tails are selected mostly by width, not by ability to unblock the specific net**.
- Greedy net ordering by shortage of free holes, via `supply[]` around **875–885**. Net wiring uses nearest-cost direct/relay candidates and, on failure, records starved nets around **1027–1039**.
- Shared solder joints / stack-rescue fallback where allowed.
- `stripSegments.ts`, `connectivity.ts`, `netCompleteness.ts`, `cutPlanning.ts` and `flexGeometry.ts` provide reusable copper group, pin and geometry semantics.

**Consequent design decision:** Do **not** introduce “two-jumper relay routing” as a purported new feature. Introduce **route conflict repair, alternative relay search, and local backtracking**, reusing these existing functions. If the two-hop relay search cannot solve a net, investigate *which* exclusion or earlier choice makes it unavailable.

## Research sources and transfer to this stripboard geometry

1. **PathFinder negotiated congestion** (McMurchie and Ebeling, 1995): iterative use of conflict/history cost encourages routes to avoid shared scarce resources; especially valuable after greedy routing has failed. Source: https://janders.eecg.utoronto.ca/1387_2015/readings/pathfinder.pdf . **Adaptation:** resources are **copper segments, legal solder holes and vertical jumper corridors**, not FPGA switchboxes; no shared nets or shorts ever accepted as final.
2. **Freerouting autorouter/optimizer and RipupMemory:** routes unfinished connections, temporarily removes blocking routes, reroutes them and avoids repetitive A-rips-B/B-rips-A cycles. Source: https://github.com/freerouting/freerouting/blob/master/docs/architecture.md . **Adaptation:** keep a temporary blocked-resource/history table across repair attempts for the **same board**, never silently accept cross-net sharing.
3. **VPR placement and routing feedback:** simulated annealing of placement and targeted quench/repair; input quality can depend on routability, not merely wirelength/area. Source: https://docs.verilogtorouting.org/en/latest/vpr/command_line_usage/ . **Adaptation:** score legal vertical-corridor access and completed net groups before/alongside physical compactness.
4. **Large-neighborhood search**: freeze most of a candidate, alter a small causally connected subset, rebuild that region and compare. Source: https://acrogenesis.com/or-tools/documentation/user_manual/manual/metaheuristics/jobshop_lns.html . **Adaptation:** change 1–4 blocking parts/wires rather than restarting the entire circuit at every column.
5. **Google OR-Tools CP-SAT NoOverlap2D:** can represent bounded discrete component positions/rotations as a more powerful optional local placement repair; not a substitute for the native copper/net checker. Source: https://or-tools.github.io/docs/python/cp__model_8py_source.html (NoOverlap2D); https://developers.google.com/optimization/cp/cp_solver/ . **Adaptation:** optional targeted fallback later, **not** an initial requirement or a full-board solver replacement.
6. **Striprouter**, an existing stripboard-specific autorouter: demonstrates a constrained graph/Uniform Cost Search with separate horizontal copper and vertical jumper resources and route-order optimisation. Source: https://github.com/rogerdahl/striprouter . Repository front page notes this version is in development and points to `striprouter-cpp`; use for algorithm ideas, not as a drop-in replacement.

Research evidence supports the **techniques**, not a promise they will succeed on our fixture. Every proposal must be tested against our own independent netlist and geometry checker.

## Proposed implementation, smallest useful change first

### 0. Preserve and diagnose before changing the search

- **Do not pull, rebuild, overwrite binaries or change the running output** while the exhaustive Slide sweep is active. Git research/docs updates do not affect the already running local processes, but pulling the changes during a run could create non-reproducible mixed-binary output.
- Archive the existing fixed-USB near-misses `seed_0157_col_47.json` (one component crossing) and `seed_0129_col_47.json` (one nonvertical wire). Analyse independent `wireViolations`, pin/copper groups, available relay tails, other route allocations and `finishTrace`. Then pick near-miss candidates from the completed Slide run. Reuse snapshots, **no additional annealing needed** for initial diagnosis.
- Distinguish `SOLVER_ISSUES` / `quality` from independently recomputed electrical/geometry defects. Never hide or drop an issue to manufacture a pass; derive a **new consistent final result** and rerun the full independent strict gate.

### 1. Limited `rip-up-and-reroute` pass on the already finished board

For each candidate with zero electrical shorts (or other safely fixable defects):

1. Identify **the defect**: incomplete net's disconnected copper groups, a nonvertical wire, or a body-crossing wire. Also list other wires sharing its current attachment/corridor and the component bodies it intersects.
2. Build a **small, causally related repair neighborhood**, initially the offending wire(s), their net's wires, and at most **2–4 blockers**. Remove only those wires (and dependent relay cuts), **without** changing original pins, unrelated nets, locked placement or physical dimensions.
3. Use the current strip/cut topology as the starting graph: `computeStripSegments`, `computeConnectivity`, legal free hole availability and `flexGeometry` body/crossing checks. Generate **multiple** candidate direct links, two-hop relays and ordered local wire reconnections. **Don't select solely the geometrically widest relay tail**; rank by whether it actually joins the required groups, legal corridor cost and downstream free-hole scarcity.
4. For congested nets, keep a tiny **beam/priority queue of alternative partial routes** (start 4–16 alternatives, bounded). If net B cannot route after net A claims a hole, undo A and retry B first, with a temporary history penalty preventing infinite A↔B ping-pong.
5. Independently recompute the **entire** new board. It must not gain shorts, pin conflicts, off-board copper, component-body intersections or new illegal wires. If a new state reduces incomplete nets or strict wire violations, keep it even when it has **more total wires/cuts**. Preserve the original as fallback; never corrupt it.

On this 24×56 horizontal-strip board, a seemingly disconnected pair of netside copper groups with **zero shared vertical columns** may still connect through a **multi-hop path across an intermediate row** using two vertical jumpers plus existing copper. However, the current router **already tries certain one-relay paths**; the novelty is **richer candidate choice, multiple route orders, temporary displacement/backtracking and potentially more than one intermediate copper segment**, not merely adding one simple relay.

### 2. Escalation: bounded conflict-directed **component move**

If no legal reroute exists with fixed placements:

1. For a crossing, inspect the component(s) hit by the offending wire. For an incomplete net, inspect each disconnected pin group's attached parts and blocking parts in candidate direct/relay corridors. **No hard-coded net6, GPS, USB, column or footprint cases.**
2. Generate discrete adjacent shifts `±1/±2` rows/columns for **movable** components, small swaps where physically meaningful, and permitted rotations from the general geometry-derived domain. Respect half-turn-only and locked/edge/excluded constraints.
3. Rebuild affected cuts and complete wiring using existing `finishSkeleton` / `finishRepair` (not handcrafted copper); preserve 24×56 and exact USB anchor unless explicitly operating in a separate in-anneal Slide experiment.
4. Use a **lexicographic feasibility key** on independently recomputed metrics: `(shorts, unplaced/illegal geometry/offboard/lock, incomplete net groups, nonvertical, body-crossing, [stacks/knives only when forbidden], wires, cuts, wire length)`. This is the *experimental repair comparator*; it is not intended to change normal anneal weighting in the existing GUI. Penalties may allow a short bounded worse intermediate only in isolated scratch state, never in returned results.
5. Keep a beam of 8–16 candidates and cap by actual independent validation calls or elapsed CPU. Return the best only when all hard constraints are satisfied; otherwise retain and label non-strict near-misses for further repair.

### 3. Better Slide interaction (later, opt-in experiment)

Currently the `scripts/run_motoex_native_full_slide_sweep.py` controller runs a **fresh Node/native anneal** at each USB position, with otherwise movable components reset. This explores columns but does **not transfer a useful placement/copper arrangement from column 47 to column 46**.

After the local repair has produced consistent wins, test **explicit in-annealer Edge Slide mutations or warm-started nearby anchors**:

- Keep the USB physically edge-mounted; mutate its legal column by `±1`, `±2` or occasional larger jumps, and make a small set of local placement/routing repairs near its new body.
- Preserve non-USB component positions as an incumbent when moving to a neighboring column, rather than completely restarting; accept only independently checked candidates as strict winners.
- Keep this behind an **opt-in native experimental flag**, not default native/WASM/Tk behaviour. A/B on identical master, seeds, move budgets and consistent source/binary fingerprints.
- Compare **strict passes per CPU-second**, **time to first strict pass**, moves to first fitting placement, final wire/cut counts, and distribution of failure categories. Don't use merely “first physical fit” or “fewest wires” as evidence of actual solved quality.

## Engineering acceptance tests before full integration

- Synthetic net with two disconnected pin groups and no same-column endpoints, but a legal two-jumper relay through a pin-free row: should connect with **two vertical wires and valid cuts**, no slants/shorts/crossings.
- A layout that was already clean but has an alternate longer cheaper path: repair never makes it worse on the **feasibility-first comparator**.
- A two-net corridor conflict: fixed-order greedy fails; **bounded rip-up/reorder** finds a complete legal connection.
- A one-wire crossing: moving one unlocked blocking component and rebuilding route repairs the crossing with all unrelated nets preserved.
- A locked-part obstruction: no candidate may move or rotate the locked part or place copper outside bounds.
- Source, normal WASM, native CLI and historical signatures unchanged when new repair is **disabled**.
- Real fixed-USB seed 157 and 129: record strict reason codes and before/after independent metrics. **No presumption of success**.
- Real Slide seed/column archive: compare a small deterministic holdout to the unmodified binary, then measure strict qualification rate; no 10,200-trial rerun without evidence.

## Decision

**Build an opt-in bounded, conflict-directed post-finisher first**: existing graph/relay code + small route-order beam/rip-up, then placement-aware escapes. This is lower-risk, targeted at demonstrated near-misses, and more likely to improve strict solve rate than repeating a fresh complete anneal 51 times with no feedback. The full in-anneal USB slide mutation is worthwhile but should be implemented only after the repair gate is proven.

**Do not change or interrupt the in-progress full Slide sweep.** Its saved invalid layouts are the test corpus for this proposed next improvement.
