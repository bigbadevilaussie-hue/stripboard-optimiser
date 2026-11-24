# START HERE — Native stripboard solver handover (24 November 2026)

> **This is the current engineering handover for the next chat or developer.** Read this file, [README.md](../README.md), [project.md](../project.md), and [native Edge/Slide technical notes](native-edge-slide-motoex.md) **before changing code**. Do not infer that a command or test has passed merely because it is committed. All commands and findings below are tied to the existing GitHub feature branch, not a new branch.
>
> **As-of:** 24 November 2026, Australia/Brisbane. **Repository:** `bigbadevilaussie-hue/stripboard-optimiser`. **Active work branch:** `feature/native-edge-slide-motoex`. Source-code tip immediately before this documentation update: `240ed008228f5f6c26b3ef3248df1e1503b9ff39`; documentation commits advance the branch afterwards. Run `git status -sb` / `git log -5 --oneline` to establish actual tip.

## 1. Mission, user priorities and boundaries

Build a **general-purpose** stripboard/Veroboard optimiser, based on the inherited Karl v5 C/TypeScript engine, capable of producing **human-buildable** layouts from arbitrary valid projects. **Never hard-code GPS, USB, MOTOEX, pin names, preferred rotation values, net6, a column, a particular footprint, or a benchmark result in solver logic.** MOTOEX is an adversarial fixture, not product behaviour. Rules may depend on the actual board copper pattern, footprint geometry, net assignments, user-selected constraints and legal component mount types. The filter created here applies to all qualifying rigid footprints. Preserve normal, unrestricted behaviour when experimental features are disabled.

**Quality first, speed second.** A completed strict board must simultaneously satisfy:
- Complete intended electrical connections, **zero** unintended shorts and **zero** disconnected nets.
- Legal component placement, collisions, clearances, locked positions and optional component-body overhang constraints.
- Exact locked physical board dimensions; all **pins, cuts and jumper endpoints on-board**.
- When strict vertical mode is requested: every jumper has equal endpoint column (slants **and horizontal wires fail**), no body crossings, no overlapping/stacked wires.
- When drilled-only is requested: **zero** knife/between-hole cuts.
- Retain and rank actual validated alternatives. A pretty or low-wire-count result with any hard failure is **not** a solved board. `Q0`, an anneal price, fitting in the board, and a strict physical PASS are different things.

Developer workflow preferences: direct code changes and Git commits in the **current branch**, no needless branch proliferation, no endless seed runs without new diagnostic value, compact copy/paste commands, emoji `🧷 🔬 🛡️ ✅ ❌ 🛠️ 🔪` progress. All relevant sources live in Git so rollback is available; avoid needless clarification loops. The user's own iMac/desktop files are not accessible from this chat environment, so local runtime evidence must come from pasted terminal output or uploaded files. Do not promise asynchronous work.

**Reference layout caveat:** A prior Moto-Mate reference/WR-style result was made possible by moving **both GPS and USB off-board**, changing the physical problem. The older **W14/C30** 24×56 reference is valuable history but **not a verified strict same-problem benchmark** for GPS+USB physically present on-board. The broader historical 80-run/36-run MOTO results also used a mistaken **1000mF C1** component label/footprint; the corrected C1 fixture must not be compared silently to those input snapshots. See `docs/moto-c1-correction-v162.md`.

## 2. Architecture: what exists today

- `src/frontend/components/stripboard/v5wasm/decode.c`: authoritative native/WASM v5 anneal + placement/rotation genome, scoring and C search. Its `-DV5_EXPERIMENT_EDGE_MOUNT=1` feature is **opt-in**; regular native/WASM builds stay distinct.
- `src/frontend/components/stripboard/v5wasm/v5Wasm.ts`: model serialization and native decoder wrapper. Native experimental setter and read-only first-fit telemetry.
- `src/frontend/components/stripboard/autoLayout5.ts`: normal v5 search portfolio, physical-fit gating, finisher selection, optional rotation-domain switch and **optional** final wire polish.
- `src/frontend/components/stripboard/layout2/finish.ts`: router and repair finisher; the locked-board case disables or limits normal width/channel-insertion moves.
- `src/frontend/components/stripboard/autoFinish.ts`, `cutPlanning.ts`, `wireRouting.ts`, `boardPins.ts`, `stripSegments.ts`, `connectivity.ts`, `netCompleteness.ts`, `flexGeometry.ts`, `partGeometry.ts`: physical/electrical build and checker logic. **Read these before changing attachment semantics.**
- `src/frontend/components/stripboard/wireColumnPolish.ts`: **new**, generic post-finish local column reassignment + knife-to-drill improvement, opt-in.
- `src/frontend/tests/solver/v5Solve.js`: independent strict CLI gate, input project, `--native 1`, `--drilled 1`, `--nostack 1`, `--strict 1`, explicit `--drill-domain 0|1`, `--wire-polish 0|1`, `--save <path>`, result signature and JSON diagnostics. Exit **0** strict PASS, **2** completed but strict invalid, **64** bad CLI arguments.
- `src/frontend/tests/solver/native/addon.c`, `native/buildAddon.js`, `nativeInstance.js`: native Node bridge for tests/CLI; the addon builder now locates Node API headers on macOS/Linux.
- `scripts/run_motoex_native_edge_slide.py`: **fixture-specific benchmark controller only**, creates per-attempt project copies, seeds, output reports and checks, calls the **same general native solver**. USB column slide is **currently a controller/racing search**, **not** a mutation in the native anneal.
- `test-fixtures/masters/moto/motoex.json`: master fixture. **Never modify the master to “make it pass.”**
- `desktop/src/stripboard_optimizer/`: older Tk GUI/tournament. **Current experimental native Edge/Slide, drill-domain and wire-polish path is CLI-first; GUI integration is not established.** Route-Mate PySide6 GUI migration is deliberately deferred until solver quality gates. See `docs/route-mate-native-solver-integration-roadmap.md`.

## 3. Exact MOTOEX physical fixture

- Test board: **24 rows × 56 columns = 1,344 holes**. Both `lockedRows` and `lockedCols` true; copper is ordinary horizontal stripboard.
- Reported prepared case: **45 components**, **123 pin/net assignments**. GPS and USB are **physically on-board**. Other legitimate off-board items remain represented via pad expansion; do **not** convert GPS/USB to off-board to get a passing benchmark.
- USB rigid charger footprint **6 columns × 13 rows**, rotation **0**, anchored **row 13**. Source column **47**; experimental Slide explores legal columns **0..50**. Body reaches row **25**, so rows **24–25 overhang the *bottom* of the purchased board by two**, while both USB pins and all electrical copper remain in rows **0–23**. For Edge=yes/Slide=yes, current benchmark controller locks USB to each tested column in a fresh input. All **other placement locks are discarded by this fixture's setup**, not by the general solver.
- GPS footprint **9×13**, five adjacent pins in one bottom pin row at offsets `(12,2)..(12,6)`; assigned VCC/net27, GND/GND, TXD/net25, RXD/net29, and an unassigned PPS. At rotation **0°** adjacent different-net pins share a strip with no empty hole between them. At **270°** their pin row becomes a column, removing that specific forced-cut problem. **These orientations are diagnostics, not a GPS name-based solver whitelist.**
- On-board means electrical pins are soldered into valid board holes. Body overhang is an **explicit mechanical permission**, not a blanket exemption for every component. Future automatic GPS edge-mounting is a separate general feature; do not silently allow it as though implemented.

## 4. Engineering chronology and hard evidence (distinguish measurements from interpretation)

### A. Original Edge/Slide and hard physical lock

An early 51-column sweep at 20k moves found **four overflow outputs** at USB columns **25, 18, 12 and 8** (e.g. column 25 returned 30×56). Overflow was a soft objective penalty, not a guaranteed hard physical cap. The experimental C ratchet now allows a search to reach its **first fitting placement**; once fitting, out-of-cap proposals cannot be accepted as the incumbent. The TypeScript finalizer validates dimensions, every part/pin/cut/wire endpoint and returns an explicit empty **`UNSOLVED: NO_FEASIBLE_PLACEMENT`** or **`UNSOLVED: NO_PHYSICAL_FINISH`** if it cannot return a fitting result. Empty 0W/0C/35-incomplete placeholders are **not** treated as routed failures.

User-verified runs, physical 24×56:
- USB col **25**, 20k **before rotation domain**: `UNSOLVED`, **0 W / 0 C**, all 35 nets apparently incomplete only because the fallback is empty. No first fit.
- USB col **25**, 500k before rotation filter: **29 W / 48 C**, **3 incomplete GPS-related nets** (GND, TXD, RXD), **7 knife**, **11 crossings**, **2 stacks**; GPS **0°**.
- USB col **41**, 500k before filter: **30 W / 46 C**, electrically complete, **0 knife**, **8 crossings**, **1 stack**, **2 nonvertical wires**; GPS **270°**. Still no strict physical PASS.
- USB col **41**, 20k before filter: **47 W / 63 C**, no incomplete nets reported, **3 nonvertical**, **6 crossings**, **6 knife**, **3 stacks**. First physical fit at **move 7,796 / 479 ms**; GPS **270°**.

First-fit telemetry from the C decoder uses existing shared-memory slots, reported as `firstFeasibleMove` and `firstFeasibleMs`. The metric measures **first accepted in-cap placement, not fully routed PASS**.

### B. Generic drill-only rotation-domain discovery, implementation and A/B

For ordinary horizontal-strip copper, a rigid footprint rotation with two **adjacent holes on the same row carrying different assigned nets** necessarily requires a knife cut to separate them; an unassigned pin is a private floating net. Compute allowed rotations from **actual rotated pin geometry + net assignments** for **every rigid footprint**, including same-net adjacency exceptions, locked rotations and `halfTurnOnly` mechanical constraints. This is a **necessary condition**, not a guarantee of a complete route. Patterned/non-horizontal boards are excluded from this inference.

Native-only experimental implementation: `decode.c` `v5_setDrilledRotations`, rotation masking, `initGenome`, `mutate` and decode rejection; wrapper `v5Wasm.ts`; `autoLayout5.ts` only activates under drilled cuts and explicit `drilledRotationDomain !== false`. **Production WASM and ordinary native mode unchanged.** `v5Solve.js --drill-domain 0` disables only this domain for same-binary A/B.

**Mac-verified:**
- `npm run build:native` succeeded with header `/usr/local/include/node`; `npm run build:native:edge` succeeded. Build flags for edge = `V5_EXPERIMENT_EDGE_MOUNT`, `FAST_GRID_CLEAR`, `FAST_IDENTICAL_GENOME`; ordinary native is separate. `testDrilledRotationDomain.js` (synthetic) passed; `testKnifeCutAudit.js` (synthetic) passed.
- **Col 25, 20k, domain ON**: fitting placement at **move 1,194 / 77 ms**, **56 W / 72 C**, **0 reported incomplete nets**, **9 nonvertical**, **8 slanted**, **17 crossings**, **9 stacks**, **1 knife**. This *solved the initial placement/rotation pathology*, not strict routing.
- **Col 25, same seed and 20k budget, domain OFF**: empty **`UNSOLVED: NO_FEASIBLE_PLACEMENT`**, no first fit; output **signature `e69806eb68fc`**, **identical** to the preserved pre-domain hard-lock run (`e69806eb68fc`). One verified opt-out signature equality; the broad 80-signature parity suite **has not been rerun**.
- This on/off comparison uses the **same native edge build and fast flags**. The domain switch changes search trajectory; isolated one-seed differences are not a population estimate.

**User-provided 500k one-seed comparisons** (comparative summary supplied from Claude, not raw full pasted CLI stdout; do not overclaim):

| Metric | Col 25 BEFORE domain | Col 25 AFTER domain | Col 41 BEFORE | Col 41 AFTER |
|---|---:|---:|---:|---:|
| Wires / cuts | 29 / 48 | **40 / 56** | 30 / 46 | **23 / 44** |
| Electrically complete | No (3 GPS nets) | **Yes** | Yes | **No (net6)** |
| Knife cuts | 7 | **2** | 0 | **2** |
| Crossings | 11 | **8** | 8 | **0** |
| Stacks | 2 | **4** | 1 | **2** |

The 500k after-domain results reached first in-cap placement very early (reported first-fit move values **668 and 1,847**, without per-column mapping in the summary). **Neither is a verified strict PASS.** At col 25, 3V3 **wire 24** was reported slanted from **(6,54) to (2,15)** and crosses five named bodies (ESP32, R6, Switched Buck, GPS, R12). At col 41, **net6** has disconnected pin groups **ESP32.GPIO5**, **R3.2 + R4.1**, **R10.1**, and needs a placement/copper corridor analysis. Do not turn these into hard-coded routing behaviour.

### C. Knife 20k drill diagnosis, user-verified

The read-only generic `knifeCutAudit.js` on the *20k* col25-domain-ON saved board returned exactly one knife:
- **row 0, copper gap between columns 49 and 50**;
- nearest left pin **R11.2 [net19] @49**; nearest right pin **30 mm FAN 2.1 [GND] @51**;
- hole **49 blocked by the pin** and hole **50 blocked by endpoint of wire #56**;
- **not** forced by two directly adjacent different-net pins. If a wire endpoint can legally move, hole 50 may become drillable, subject to independent final verification.
This is evidence that a **fixed-component, column-reassignment** local wire move can address some violations without more placement moves.

### D. Experimental fixed-board wire polish — **committed, NOT YET TESTED ON THE MAC**

New module `wireColumnPolish.ts`, wired into `autoLayout5.ts` and CLI behind `--wire-polish 1`; benchmark controller flag `--wire-polish yes` default **no**. It:
1. Preserves components, nets, original board frame, wire count and copper segment memberships for an existing jumper.
2. Searches free candidate columns common to its endpoint strip segments (including possible slant→vertical repair), reassigns **both endpoints together**.
3. Prevents occupied pin/body/cut/other-endpoint placements; measures crossing/stack/vertical compliance.
4. Attempts between-cut→drilled-hole conversion where flank holes become free.
5. Recomputes independent strip segments, connected copper, incomplete nets, shorts, crossings, stacking and knife counts; accepts a candidate only if no strict defect count regresses and the scoring vector improves. A final check rejects changes that regress.
6. Returns the original result if disabled or no improvement; records before/after `wirePolish` counts.

**Do not claim the polisher passes yet.** The latest code and synthetic test `testWireColumnPolish.js` were committed on GitHub but **not yet compiled or executed on the iMac**. The saved-layout replay script `polishSavedLayout.js` and generic `inspectNetCorridors.js` are likewise unexecuted. The next task is to run, fix any compile or runtime errors directly, and measure **both** 500k saved layouts. Important: `--wire-polish` is optional; old signatures and GUI unchanged by default. This pass does **not** solve net6 if its disconnected groups have no legal shared attachment column; that likely needs component placement or multiwire rerouting.

**Additional implementation limitations / audit items to check in code and tests:**
- A fully verified strict result must use the same independent checker as `v5Solve.js`, including board pattern/hole availability, no-overlap, electrical shorts and geometry; quality improvements alone cannot certify an output.
- The polisher's current candidate search skips same-row horizontal wires, so it cannot individually straighten a pure horizontal link by preserving both endpoint rows; this is a genuine scope boundary, not a regression.
- The new quality metric is a local strict-defect ordering, **not** a replacement for final independent strict validation or Pareto ranking.
- The maximum local search is presently **6 passes / 6,000 full evaluations** per invocation; tune based on measured quality/CPU, not on MOTOEX-specific exceptions.
- The original fast 20k or 500k run outputs are kept on the user's desktop, **not automatically committed**. Git tracks code and fixture master, not those individual experiment outputs.

## 5. Files to read before implementing anything else

| Area | Paths |
|---|---|
| Architecture and controls | `src/frontend/components/stripboard/autoLayout5.ts`; `v5wasm/decode.c`; `v5wasm/v5Wasm.ts`; `layout2/finish.ts` |
| Physical wire/cut local polish | `src/frontend/components/stripboard/wireColumnPolish.ts`; `autoFinish.ts`; `cutPlanning.ts`; `boardPins.ts` |
| Independent net/copper checker | `stripSegments.ts`; `connectivity.ts`; `netCompleteness.ts`; `flexGeometry.ts`; `partGeometry.ts` |
| Strict CLI | `src/frontend/tests/solver/v5Solve.js`; `tests/solver/helpers.js`; `tests/solver/metricsLib.js` |
| Native build | `src/frontend/package.json`; `src/frontend/tests/solver/native/addon.c`; `native/buildAddon.js`; `nativeInstance.js` |
| Benchmark | `scripts/run_motoex_native_edge_slide.py`; `scripts/tests/test_motoex_native_edge_slide.py`; `test-fixtures/masters/moto/motoex.json` |
| Diagnosis | `src/frontend/tests/solver/knifeCutAudit.js`; `inspectSavedCuts.js`; `inspectNetCorridors.js`; `polishSavedLayout.js` |
| Synthetic tests | `testDrilledRotationDomain.js`; `testKnifeCutAudit.js`; **new** `testWireColumnPolish.js` |
| Longer history | `docs/native-edge-slide-motoex.md`; `docs/motoex-locked-usb-24x56-regression.md`; `docs/cli-audit-2026-11-23.md`; `docs/native-speed-lab-v165-results-and-followup.md`; `docs/moto-c1-correction-v162.md` |
| GUI future | `desktop/README.md`; `docs/route-mate-native-solver-integration-roadmap.md` |

## 6. Quick startup commands — iMac

Repository root: `~/Documents/stripboard-optimiser`; local terminal typically uses `zsh`. Use the current branch and pull only fast-forward; never wipe local work. Run each line from the root unless a `cd` is shown. The root README has additional build and GUI instructions.

```sh
cd ~/Documents/stripboard-optimiser
git status -sb
git pull --ff-only
cd src/frontend
npx tsc -p tests/solver/tsconfig.json
npm run build:native
npm run build:native:edge
node tests/solver/testDrilledRotationDomain.js
node tests/solver/testKnifeCutAudit.js
node tests/solver/testWireColumnPolish.js
```

Last two synthetic tests previously passed on user's Mac only **before** the local-polish addition; the new wire-polish test is still pending. `build:native` finds `node_api.h` automatically; on the iMac it previously resolved `/usr/local/include/node`. `build:native:edge` rebuilds the special native decoder only, not the Node addon. If any command fails, fix that concrete failure in the existing feature branch before spending more time on anneals.

### Zero additional annealing: inspect and polish saved 500k boards

```sh
cd ~/Documents/stripboard-optimiser/src/frontend
node tests/solver/inspectSavedCuts.js ~/Desktop/motoex_col25_rotation_domain_500k/motoex_seed1_usb_col25.json ~/Desktop/motoex_col41_rotation_domain_500k/motoex_seed1_usb_col41.json
node tests/solver/inspectNetCorridors.js ~/Desktop/motoex_col41_rotation_domain_500k/motoex_seed1_usb_col41.json --net net6
node tests/solver/polishSavedLayout.js ~/Desktop/motoex_col25_rotation_domain_500k/motoex_seed1_usb_col25.json --out ~/Desktop/motoex_col25_rotation_domain_500k_polished.json
node tests/solver/polishSavedLayout.js ~/Desktop/motoex_col41_rotation_domain_500k/motoex_seed1_usb_col41.json --out ~/Desktop/motoex_col41_rotation_domain_500k_polished.json
```

**Check the folder names:** some earlier pre-domain saved baselines are instead `~/Desktop/motoex_col25_500k/` and `~/Desktop/motoex_col41_500k/`. `*_rotation_domain_500k` are the proposed *after*-domain output names from an earlier test command, not independently re-listed from the Mac. If those paths are absent, inspect `~/Desktop` and supply the actual existing paths. The output path must differ from the input; the polisher should never overwrite the source.

### Native fixture trial with integrated optional polish (only after quick replay)

```sh
cd ~/Documents/stripboard-optimiser
python3 scripts/run_motoex_native_edge_slide.py --edge yes --slide yes --column 25 --seeds 1 --moves 20000 --drill-domain yes --wire-polish yes --out ~/Desktop/motoex_col25_polish_trial_v1
```

The fixture controller exits **2** for a fully completed but non-strict result; do not interpret that as a compiler failure. Every fresh `--out` must be empty/nonexistent. Stop on verified strict PASS; do not launch a 51-position brute-force sweep until diagnostic quality warrants it.

### Same-build domain-off parity regression

```sh
python3 scripts/run_motoex_native_edge_slide.py --edge yes --slide yes --column 25 --seeds 1 --moves 20000 --drill-domain no --wire-polish no --out ~/Desktop/motoex_col25_domain_off_new
```

Expected preserved signature `e69806eb68fc` for that exact input/seed/moves/build family. **One signature equality has already been independently reported.** Longer 80-run parity comparison is outstanding, and must reference the correct historical fixture and corrected/uncorrected C1 distinctions.

## 7. Immediate next work, in priority order

1. **Compile and execute the new polish synthetic tests and saved-layout replay.** Fix actual failures; do not hide problems by weakening checker assertions or hard-coding the fixture.
2. On both after-domain 500k boards, run `inspectSavedCuts.js` (two knives each reported), `polishSavedLayout.js`, compare strict gate metrics **before/after**, inspect moved wire endpoints and recovered knives. Ensure outputs still 24×56, complete nets not regressed, no new crossings/stacks.
3. **Net6:** inspect its four pins and disconnected copper groups with `inspectNetCorridors.js`. Report shared free columns and geometry-clean candidates; if none exist, choose a general placement/rip-up/re-route remedy.
4. Expand local polish beyond its current limitations **generically**: candidate prioritisation, more than one wire move, column reallocation to unblock drilled cuts, and only as proven useful a fixed-board placement improvement. Keep independently verifiable result quality as the gate.
5. At least several independent 500k seeds at columns 25 and 41 only after polish has demonstrated value; preserve **all** physically fitting candidate evidence, not just one scalar winner.
6. Separate parallel work: generic **USB edge slide as a mutation inside anneal**, not only 51 independent fixed-column races; fixed-board feasibility moves; future UI/Route-Mate integration only after native solver is reliable.
7. Run broader 80-signature domain-off regression and legacy AUDIO/MOTO parity **on correctly matched fixture revisions**. The new feature must not silently alter disabled behavior.

## 8. Engineering traps / things NOT to do

- **Do not** treat `UNSOLVED` empty fallback as a 0-wire layout or a physical impossibility proof.
- **Do not** let the purchased 24×56 board grow to 26×56/30×56. USB plastic can overhang only in its explicitly permitted edge setup.
- **Do not** call an electrically complete candidate strictly build-ready while it has horizontal/slanted jumpers, stack, knife or body crossing.
- **Do not** hard-code “GPS only 90/270” or “ESP32 only 0/180”; infer allowed geometry and nets, honour user settings and mechanical rotation capability.
- **Do not** assume the output `--drilled 1` / `--nostack 1` *causes* compliance: final independent CLI checks remain authoritative.
- **Do not** confuse wheel-spinning anneal time with finish time; first-fit move is a **placement** milestone only.
- **Do not** use old off-board GPS/USB WR data to claim an on-board strict benchmark was solved.
- **Do not** silently compare signatures across changed inputs, different compilers, different flags, WASM/native, or corrected/uncorrected C1.
- **Do not** overwrite canonical master, input saved results, original SVG renderer outputs or historical logs.
- **Do not** pivot to an unrelated solver, add another feature branch, reimplement routing in the GUI or force a GUI migration now.

## 9. Starting a new ChatGPT chat

Suggested initial instruction: **“Read `docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md`, root `README.md`, `project.md` and `docs/native-edge-slide-motoex.md` from branch `feature/native-edge-slide-motoex` in `bigbadevilaussie-hue/stripboard-optimiser`. Continue the general-purpose native optimiser where we left off. The immediate job is to compile/test/replay `wireColumnPolish.ts` on existing 500k saved layouts and fix it, then tackle net6 and integrate edge-slide into native anneal. Do not hard-code for MOTOEX. Quality/strict verification first; use existing branch; make code and commits, not just plans.”**

**This handover is a documentation snapshot. Git code and actual new test output supersede an outdated statement.** When code or measured results change, update the status and the exact commands here and at the top-level README in the same commit.
