# Stripboard Optimiser

A development fork of [KarloFunke's Stripboard Editor](https://github.com/KarloFunke/stripboard-editor), focused on practical Veroboard/stripboard design, standalone rendering and a separate desktop optimisation workflow.

This is **not** a PCB design or fabrication application.

## Repository status

The repository currently contains three related parts:

1. **Inherited web editor** — the existing Next.js frontend and Django backend.
2. **Standalone renderers** — Node.js command-line tools for the stripboard's component side, copper side and schematic.
3. **Desktop prototype** — a Tkinter interface with project import/preflight UI and a three-view image viewer. The desktop optimiser is not yet runnable as a complete application: its UI imports `stripboard_optimizer.solver.worker.SolveWorker`, but that module is not present in the current repository. Packaging and a complete dependency/install workflow are also not present.

The optimisation engine, validation pipeline, candidate management and desktop distribution requirements remain defined in [project.md](project.md). That document is the specification; it must not be read as proof that every requirement has been implemented.

## Repository layout

```text
stripboard-optimiser/
├── README.md                         # Repository overview and entry points
├── project.md                        # Canonical project specification and status notes
├── desktop/
│   ├── README.md                     # Desktop prototype status and file map
│   └── src/stripboard_optimizer/     # Tkinter desktop application source
│       ├── ui/
│       └── resources/standalone-renderer/ # Bundled JavaScript renderer runtime
└── src/
    ├── backend/                      # Django backend
    ├── frontend/                     # Next.js application and renderer source
    │   └── standalone-renderer/
    │       ├── schematic/            # Schematic SVG renderer source
    │       ├── dist/                 # Compiled JavaScript renderer
    │       └── README.md             # Renderer build, CLI and parity documentation
    └── nginx/                        # Nginx deployment configuration
```

## Run the inherited web application

These instructions run the existing web editor. They do not launch the desktop prototype or a completed optimiser.

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

The example environment files are templates. Configure them for the local environment. Never commit real credentials, secrets or local environment files.

### Frontend scripts

Run these from `src/frontend`:

| Command | Purpose |
|---|---|
| `npm run dev` | Start the Next.js development server |
| `npm run build` | Build the frontend |
| `npm run start` | Start the built frontend |
| `npm run lint` | Run ESLint |
| `npm run test:solver` | Run solver tests |
| `npm run test:schematic` | Run schematic tests |
| `npm run test:board` | Run board tests |
| `npm run test:branches` | Run branch tests |
| `npm run build:wasm` | Compile the existing C solver sources to WebAssembly |
| `npm run build:native` | Build the existing native solver libraries and Node addon |
| `npm run check:agent-docs` | Run the repository's agent-documentation consistency check |

The solver build scripts compile existing solver code. They do not by themselves implement the complete optimiser pipeline described in [project.md](project.md).

## Standalone rendering

The standalone renderer is TypeScript source under `src/frontend/standalone-renderer/`. Its compiled JavaScript is under `src/frontend/standalone-renderer/dist/`.

It provides two separate command-line entry points:

| Renderer | Compiled entry point | Output |
|---|---|---|
| Stripboard | `dist/standalone-renderer/cli.js` | `board-top.svg`, `board-copper.svg` |
| Schematic | `dist/standalone-renderer/schematic/cli.js` | `schematic.svg` |

Build from `src/frontend`:

```bash
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.json
```

Run the board renderer:

```bash
node standalone-renderer/dist/standalone-renderer/cli.js <project.json> --output <dir>
```

Run the schematic renderer:

```bash
node standalone-renderer/dist/standalone-renderer/schematic/cli.js <project.json> --output <dir>
```

Both CLIs accept `--output <dir>` and `-o <dir>`. The schematic CLI writes `schematic.svg`; the board CLI writes the top and copper SVGs. Detailed input expectations, source layout, test compilation and recorded parity results are in [the renderer README](src/frontend/standalone-renderer/README.md).

## Desktop prototype

The desktop source is in `desktop/src/stripboard_optimizer/`. Its current UI includes project loading, netlist and KiCad ZIP selection, preflight display, optimisation-mode selection, solver controls and a board viewer with Front (Top), Back (Copper) and Schematic views.

The renderer runtime used by the desktop is bundled under:

`desktop/src/stripboard_optimizer/resources/standalone-renderer/`

The TypeScript source of truth remains under `src/frontend/standalone-renderer/`; `dist/` is its compiled output, and the desktop resources directory is the runtime copy consumed by the Python UI.

**Desktop status warning:** the current UI imports a missing `desktop/src/stripboard_optimizer/solver/worker.py`. Therefore the desktop entry point cannot currently be treated as launch-ready. The repository also has no desktop `pyproject.toml`, requirements file, installer or packaging workflow. See [desktop/README.md](desktop/README.md) for the verified file map and limitations.

## Deployment

The inherited web deployment files remain:

- `docker-compose.yml` — Django, Next.js and Nginx services.
- `deploy.sh` — existing deployment helper.

These are for the inherited web application. They are not a desktop packaging or release process.

## Development direction

The planned optimiser workflow is:

1. Import and normalise project data without changing circuit topology.
2. Run the existing headless solver reproducibly.
3. Preserve and independently validate candidate layouts.
4. Rank and compare valid candidates using physical and electrical measures.
5. Export a selected validated project without overwriting the original.
6. Package the desktop application for macOS, Windows and Linux.

Requirements and acceptance criteria are in [project.md](project.md). Implemented behaviour must be verified against source and tests before it is described as complete.

## Credits and licensing

This project is derived from [Stripboard Editor by KarloFunke](https://github.com/KarloFunke/stripboard-editor). Original authorship, copyright notices and licence terms continue to apply to inherited code. This fork is distributed under the repository's GPL-3.0 licence; see [LICENSE](LICENSE).

Built-in IC pinout data is derived from the [KiCad symbol library](https://gitlab.com/kicad/libraries/kicad-symbols) by the KiCad Library Team and is licensed under [CC-BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). The inherited import script is `src/frontend/scripts/importKicadIcs.js`, and the resulting data is in `src/frontend/data/icLibrary.ts`; applicable attribution and share-alike terms continue to apply.

## Contributing and feedback

Use the [GitHub issues](https://github.com/bigbadevilaussie-hue/stripboard-optimiser/issues) for bug reports and feature requests. Include a minimal reproducible project JSON where possible, with private or sensitive information removed.
