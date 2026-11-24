# Stripboard Optimiser

> **Latest verified result (24 Nov, saved 500k replays):** All three synthetic tests passed on the user's iMac. Generic fixed-board wire-column polish reduced **col25 7→4 knife cuts** (384 attempts, 3 accepted, no shorts/opens/geometry regression) while col41 remained unchanged (119 attempts; no improving move). The remaining four col25 knives are **forced by GPS's 0° adjacent different-net pins** in that historical pre-domain board; they require a rotation/placement change, not more single-wire tweaks. On col41, 2 nonvertical wires, 8 crossings and 1 stack persist; a broader **multiwire or placement-aware repair** is next. See the [verified results and output paths](docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md#8a-user-verified-fixed-board-polish-replay--24-nov-2026-new). The 500k board files tested were the *pre-domain* `motoex_col25_500k` and `motoex_col41_500k`, not the newer domain-ON outputs.

> **LATEST verified ON-domain 500k replay:** col25 polished from **2→1 knife cut** (213 candidates, 1 accepted) while remaining electrically complete; col41 unchanged after 78 tries, with **three disconnected groups on net6** and no clean direct vertical path. Both 24×56, no independent checker regression; still **0 strict PASS**. See [handover §8C](docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md#8c-user-verified-rotation-domain-on-500k-replay--24-nov-2026-latest). **Next:** generic conflict-directed bounded part moves plus multiwire rerouting, not another round of single-column tweaking.

> **New pending sweep (NOT YET RUN):** [200 seeds × 25,000 moves — fixed USB, drilled-only OFF, stacking allowed](docs/native-fixed-usb-200x25k-sweep.md). **Slide is OFF for all 200 seeds**, USB stays at (13,47); `--slide yes` is a separate future sweep option. The tournament archives **every** strict solved JSON, every rejected JSON, per-seed timing, move-summary/finish diagnostics, and reports the top five **distinct physical layouts** by wires then cuts. Command and resume instructions are in that dedicated document.

> **200-seed fixed-USB sweep COMPLETE (24 Nov):** 200 × 25,000 moves, USB fixed (13,47), drilled-only OFF, stacking allowed, six workers; **0 strict passes** in **150.08 seconds**. **63 electrically complete routed boards** still failed physical wire requirements; one seed had no feasible placement. Closest two invalid layouts: seed 157 (43W/59C, 0 nonvertical, **1 crossing**), seed 129 (40W/56C, **1 nonvertical**, 0 crossings). Every JSON, timings and diagnostics are archived. A new post-analysis tool copies the five nearest invalid boards to a separate folder without pretending they are solved. [Exact results, next commands and analysis](docs/native-fixed-usb-200x25k-sweep.md#measured-result--mac-run-200--25k-usb-fixed-col47-no-slide).

## 🚀 Current work — START HERE (24 November 2026)

**If resuming in a new chat, read the [complete native optimiser handover](docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md) FIRST.** It contains the working branch, code map, verified build tests, exact MOTOEX on/off/500k results, remaining defects, saved result paths, reproducible commands and next engineering steps. Companion source-of-truth notes: [native Edge/Slide implementation](docs/native-edge-slide-motoex.md), [project specification](project.md), [Route-Mate GUI integration roadmap](docs/route-mate-native-solver-integration-roadmap.md).

| Item | As-of 24 Nov 2026 |
|---|---|
| Repository / work branch | `bigbadevilaussie-hue/stripboard-optimiser` · `feature/native-edge-slide-motoex` (keep working on it; no extra branch required) |
| Current focus | **General-purpose native solver quality**: strict 24×56 physical board; real on-board GPS+USB test; drilled cuts, vertical uncrossing/unstacked wires, electrical completeness |
| Confirmed on the user's Mac | Portable macOS native addon build; Edge decoder build; generic drill rotation and knife-cut synthetic tests; col25 **20k domain ON** first physical fit move **1,194 / 77 ms**, no incomplete nets; domain OFF original signature **`e69806eb68fc`** matches |
| Observed 500k comparison | Col25 domain ON: **40 wires / 56 cuts, electrically complete, 2 knives, 8 crossings, 4 stacks**; col41 domain ON: **23 wires / 44 cuts, net6 incomplete, 2 knives, 0 crossings, 2 stacks** — user-supplied one-seed results, neither strict PASS |
| Just committed, **not yet Mac-tested** | Generic fixed-board wire-column and knife→drill polish, CLI `--wire-polish 1`, fixture `--wire-polish yes`, synthetic `testWireColumnPolish.js`, saved-board replay `polishSavedLayout.js`, net-corridor audit |
| Most useful next work | Compile/run polish test, then polish **existing** 500k saved JSONs without annealing, diagnose net6; fix actual failures and use strict independent verification |
| Broader pending | 80-signature opt-out parity suite, multiple 500k seeds, native in-anneal USB slide, general finisher improvement, GUI migration **later** |

**Product rule:** MOTOEX is only a **stress-test fixture**. **Never hard-code a particular component (GPS/USB), footprint, column, rotation or net in the solver.** Infer constraints from geometry, net assignments, selected board pattern and build options. A valid result needs independent **zero opens, zero shorts, no illegal geometry, no slants/horizontal jumpers, no crossings, no stacks, drilled-only cuts and exact physical board fit** when these strict options are requested. Low wire count or a physically fitting arrangement is **not** a strict pass. The older **W14/C30 reference** had GPS and USB moved off-board and is **not** an apples-to-apples on-board MOTOEX benchmark.

### Quick developer restart (current native work)

From the repository root:

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

Build is now portable on macOS/Linux: `npm run build:native` discovers Node headers using `tests/solver/native/buildAddon.js`. There is **no need** to hard-code `-I/usr/include/node` or manually compile the addon on an iMac. The final test above is **pending validation**; if it fails, fix the code before launching an anneal. Check the [handover](docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md) for specific existing saved-file commands. Native Edge is still a CLI experiment: the current Tk and inherited web GUIs are **not** proven to use this experimental pipeline yet.

---

**A stripboard (Veroboard) layout optimiser built on the Stripboard Editor project.**

Stripboard Optimiser is a development fork of [KarloFunke's Stripboard Editor](https://github.com/KarloFunke/stripboard-editor). The aim is to retain the editor's useful stripboard design workflow while adding a headless optimisation engine, independent layout validation, candidate comparison and a dedicated desktop interface.

The repository contains the inherited web editor plus an operational Tkinter desktop optimiser. The desktop application runs the existing v5 solver through the Node.js harness, supports multi-seed optimisation, validates results, and provides board previews. It is a development tool, not yet a packaged end-user release.

## Project direction

The desktop optimiser now provides a working multi-seed tournament around the existing v5 solver. The broader goal remains to turn an existing circuit layout into a more practical, compact and buildable stripboard design.

Further development and release capabilities include:

- **Optimise layouts:** run repeatable optimisation attempts with configurable effort, random seeds and worker count.
- **Respect design constraints:** preserve fixed components, excluded components, board dimensions and placement restrictions.
- **Handle real components:** import project JSON and custom part definitions, validate footprints and pin locations, and report missing definitions.
- **Validate candidates:** check component placement, overlaps, electrical connectivity and unintended shorts independently of the optimiser.
- **Compare results:** assess candidates using board area, wire count and length, cuts, track continuity and other layout measures—not just the solver's internal score.
- **Review and export:** inspect candidate layouts and export a selected, validated result without overwriting the original project.

The detailed requirements and staged development plan are maintained in [project.md](project.md).

**Solver-first integration plan:** [Route-Mate GUI + sidecar with the native solver (GUI migration deferred until solver quality gates)](docs/route-mate-native-solver-integration-roadmap.md).

**Current native development handover:** [START HERE — 24 November 2026](docs/START_HERE_NATIVE_SOLVER_HANDOFF_2026-11-24.md). All older desktop tournament and 20k/500k records below should be read as **historical snapshots** unless corroborated against current source.

**MOTOEX edge-mount regression:** [24×56 locked USB overhang test](docs/motoex-locked-usb-24x56-regression.md) — one locked USB, other component positions discarded, exact output geometry and strict CLI gate.

**Native CLI development:** [v1.65 measured speed results and held-out verification](docs/native-speed-lab-v165-results-and-followup.md), [v1.64 native decoder/router speed laboratory](docs/native-speed-lab-v164.md), [v1.63 audio 5k–50k native ladder](docs/native-audio-ladder-v163.md), [v1.62 C1 capacitor correction and source migration](docs/moto-c1-correction-v162.md), [v1.61 budget sweep and failure matrix](docs/native-cli-budget-sweep-v161.md), and [native CLI validation/diagnostics](docs/cli-audit-2026-11-23.md). **Important:** the original 80-run/36-run results were generated with an incorrectly labelled 1000mF C1; they are historical and must not be treated as corrected-input baselines. Current work is CLI-only; GUI integration may remain stale.

## Development working agreement (v1)

These instructions govern AI-assisted development in this repository.

### User profile

- Nick is a smart-ass, sarcastic Australian male who gives no fucks.
- He may use blunt or insulting language such as "cunt", "clown" or "retard". Do not take it personally; it is not a reason to become defensive or derail the task.
- Be direct and blunt. Avoid corporate AI language and unnecessary explanations.
- If Nick asks a question, answer it. If he gives an instruction, carry it out.
- Do not ask whether he is ready or whether a process has finished unless that information is directly relevant.

### Strict rules

**Tone and communication**
- Do not lecture or explain basic Git or programming concepts unless asked.
- Give the answer or action, then stop. Do not bundle unrelated explanations or multiple steps into one response.
- Do not make unsolicited changes, rewrites, design decisions or automation.
- Ask before assuming permission to automate or make broader changes.

**Shell and patch workflow**
- The user's zsh environment has problems with multiline pastes. Do not provide multiline shell pastes or heredocs.
- Write patch scripts to `/tmp/*.py` and run them with `python3 /tmp/script.py` from the repository directory.
- Do not use `python3 -c`.
- Every patch script must check its expected anchors and exit non-zero if an anchor is missing.
- Never patch a file until its current contents have been read.
- Do not guess anchors, file contents or regular expressions.
- Make one focused change in one file at a time where practical.
- Include an application version bump with every code patch.
- After each patch, state the exact command or check that verifies it worked.

**Diagnosis**
- Confirm the current state before proposing a fix. Do not present assumptions as facts.
- Do not patch a theory. State the theory and the cheapest way to confirm it first.
- An intermittent failure is not automatically a broken implementation; retry where appropriate before changing code.
- Read all supplied output before responding.

**Session discipline**
- Nick may edit files himself. Do not assume permission to edit or commit.
- Do not nag for status updates or confirmation unless the next action genuinely depends on them.

## Existing application

The repository currently contains the inherited Stripboard Editor web application. It provides the existing schematic and stripboard design workflow, including component placement, copper-strip net colouring, cuts, link wires, layout conflict feedback and printable build templates.

The inherited web application is built with Next.js and Django. The separate Tkinter desktop optimiser is the active multi-seed optimisation interface; it is operational but not yet packaged as a standalone end-user release.

## Running the existing web editor locally

These instructions are for running the inherited web application, not for running a completed desktop optimiser.

### Requirements

- Node.js and npm
- Python 3
- The Python dependencies listed in `src/backend/requirements.txt`

The frontend also provides optional build scripts for WebAssembly and native solver components. Those scripts require a compatible Clang toolchain and, for the native Node addon, the relevant Node development headers.

### Backend

From the repository root:

```bash
cd src/backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

The Django API is served at `http://localhost:8000/api/`.

### Frontend

In a second terminal, from the repository root:

```bash
cd src/frontend
npm install
cp .env.local.example .env.local
npm run dev
```

The Next.js frontend is served at `http://localhost:3000`.

The example environment files are templates. Review and configure their values for your local setup before running the application. Do not commit real credentials, secrets or local environment files.

### Available frontend scripts

Run these from `src/frontend`:

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Next.js development server |
| `npm run build` | Build the frontend |
| `npm run start` | Start the built frontend |
| `npm run lint` | Run ESLint |
| `npm run test:solver` | Run the solver test suite |
| `npm run test:schematic` | Run schematic tests |
| `npm run test:board` | Run board tests |
| `npm run test:branches` | Run branch tests |
| `npm run build:wasm` | Compile the existing C solver sources to WebAssembly |
| `npm run build:native` | Build the existing native solver libraries and Node addon |

The solver build scripts compile existing code; they do not by themselves provide the new optimiser pipeline described in [project.md](project.md).

## Standalone stripboard renderer

The frontend also contains a standalone Node.js renderer that converts a saved project JSON file into two SVG views:

- `board-top.svg` — component side.
- `board-copper.svg` — copper side.

This renderer is separate from the planned desktop optimiser described in `project.md`. It is a command-line utility extracted from the existing frontend rendering implementation; it does not run the optimisation pipeline.

### Build

From `src/frontend`:

```bash
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.json
```

Run `tsc-alias` immediately after TypeScript compilation to rewrite the `@/` path aliases in the emitted JavaScript.

The compiled CLI is:

```text
standalone-renderer/dist/standalone-renderer/cli.js
```

There is no dedicated npm script for this build.

### Run

From `src/frontend`:

```bash
node standalone-renderer/dist/standalone-renderer/cli.js <project.json> [--output <dir>]
```

For example, using the included example project:

```bash
node standalone-renderer/dist/standalone-renderer/cli.js standalone-renderer/example-project.json --output /tmp/render-test
```

The CLI accepts `--output <dir>`, `-o <dir>` or `--output=<dir>`. If omitted, output is written to the current directory. The output directory is created automatically.

The input JSON must contain a top-level `board` object and a `components` array. The CLI generates `board-top.svg` and `board-copper.svg`, and reports board dimensions, component count, wire count and cut count.

### Parity tests

Compile the tests from `src/frontend`:

```bash
rm -rf standalone-renderer/dist-test
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.test.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.test.json
```

Then run the five parity tests:

```bash
node standalone-renderer/dist-test/standalone-renderer/test_compare.js
node standalone-renderer/dist-test/standalone-renderer/test_static_part_parity.js
node standalone-renderer/dist-test/standalone-renderer/test_static_part_colours.js
node standalone-renderer/dist-test/standalone-renderer/test_board_parity.js
node standalone-renderer/dist-test/standalone-renderer/test_part_drawing_parity.js
```

The reported parity runs used two local fixtures outside the repository clone:

- `~/Desktop/repo/motomix.json`
- `~/Desktop/repo/moto14wires30cuts.json`

Those fixture paths must exist for the corresponding parity tests to run as reported. The clean clone also contains `test-fixtures/masters/moto/moto.json` and `test-fixtures/masters/audio/audio.json`; these are not the external fixtures used in those parity runs.

For the renderer's file-by-file architecture, CLI validation behaviour and recorded parity results, see [the standalone renderer README](src/frontend/standalone-renderer/README.md).

## Deployment

The repository retains the inherited Docker deployment configuration:

- `docker-compose.yml` defines the Django, Next.js and Nginx services.
- `deploy.sh` pulls the current Git branch, rebuilds the Docker services and updates the running deployment.

These files belong to the existing web application deployment. They are not the packaging or release process for the planned macOS, Windows and Linux desktop applications.

## Tkinter desktop optimiser

The active desktop application is the Tkinter GUI in `desktop/`. It is the current optimisation interface; the inherited web GUI is not the tournament interface.

### Build and launch on macOS (legacy Tk GUI)

The Tk GUI is the older desktop optimiser; **it is not yet the target GUI for the experimental native Edge/Slide and wire-polish work**. Build the native harness with the **portable**, tested npm script, not manually hard-coded Node include paths.

Requirements: Node.js, Python 3 with Tkinter, Clang, compiled v5 JavaScript/WASM solver assets, and Node development headers for the installed Node version. The builder checks common macOS/Linux header locations and accepts `NODE_INCLUDE_DIR` as an override.

Build the native solver (from the repository root):

```bash
cd src/frontend
npx tsc -p tests/solver/tsconfig.json
npm run build:native
npm run build:native:edge
```

`build:native` builds the normal native libraries and addon; `build:native:edge` builds a **separate experimental C decoder** used by the Edge/Slide test controller. No GUI integration is implied by building the experimental decoder.

Launch the Tk GUI:

```bash
cd ../../desktop
PYTHONPATH=src python3 -m stripboard_optimizer.main
```

Or, from the repository root, launch it directly with:

```bash
cd desktop && PYTHONPATH=src python3 -m stripboard_optimizer.main
```

**Native mode is mandatory.** The desktop solver adapter forces `native=True`, passes `--native 1` to the Node harness, and checks that all three native build files exist before starting a solve. It does not fall back to WASM-only solving. The WASM files are still required by the harness for module setup, but the native addon replaces the decoder and router implementations during the solve.

At the start of a tournament, the GUI log must show:

```text
[SOLVER] Native=ON | drilled cuts=OFF | wire stacking=ALLOWED | routing priority=wires
```

If the native build is incomplete, the solver stops with a missing-native-files error rather than silently running in WASM mode. After building, the three files should exist in `src/frontend/tests/solver/native/build/`:

- `v5native.node`
- `libv5decode.so`
- `libv5route.so`

The tournament workflow currently supports:

- **Pass 1:** 1,000 independent seeds, each starting from the original project JSON, with 25,000 moves at effort 0.1.
- **Pass 1 retention:** only fully valid results qualify. Exact layout duplicates are excluded from the unique finalist pool. The top 10 unique valid layouts are selected using the configured ranking priority.
- **Pass 2:** each finalist is rerun from the original project JSON with the same seed at 40 independent move budgets: 5,000 through 200,000 in 5,000-step increments. The best valid result per finalist seed is retained.
- **Ranking:** default priority is fewer jumper wires, then fewer cuts, then lower price; cut-priority mode reverses the first two metrics.
- **Output:** retained finalist JSON files are saved to the configured tournament output directory, and the winning board is previewed.

The known Moto-Mate reference layout is **14 wires / 30 cuts (W14/C30)**. This is the current project benchmark to beat, not a claim of a verified world record. The current tournament log is an in-progress search and must not be presented as a completed benchmark result.

See [desktop/README.md](desktop/README.md) for the current desktop workflow and [project.md](project.md) for the full specification and implementation status.

## Credits and licensing

This project is derived from [Stripboard Editor by KarloFunke](https://github.com/KarloFunke/stripboard-editor). The original project's authorship, copyright notices and licence terms remain applicable to inherited code. This fork is distributed under the repository's GPL-3.0 licence; see [LICENSE](LICENSE).

The built-in IC pinout data is derived from the [KiCad symbol library](https://gitlab.com/kicad/libraries/kicad-symbols) by the KiCad Library Team and is licensed under [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The inherited import script is `src/frontend/scripts/importKicadIcs.js`, and the resulting data is in `src/frontend/data/icLibrary.ts`; the applicable attribution and share-alike terms continue to apply.

## Contributing and feedback

Bug reports, feature requests and development discussion can be raised through the [GitHub issues](https://github.com/bigbadevilaussie-hue/stripboard-optimiser/issues) for this fork.

When reporting an issue, include the project JSON or a minimal reproducible example where possible. Remove private or sensitive information before sharing project files.
