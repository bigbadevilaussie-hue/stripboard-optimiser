# Frontend — Stripboard Optimiser

The inherited web editor frontend is a Next.js application. The repository also contains the standalone stripboard and schematic renderers under `standalone-renderer/`.

For the repository-wide overview and web application setup, see the root [README](../../README.md). For the optimiser requirements and acceptance criteria, see [project.md](../../project.md).

## Development setup

From this directory:

```bash
npm install
cp .env.local.example .env.local
npm run dev
```

Open `http://localhost:3000`.

The example environment file is a template. Configure it for the local environment and do not commit secrets or local environment files.

## Available scripts

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
| `npm run build:native` | Build native solver libraries and the Node addon |
| `npm run check:agent-docs` | Check repository agent-documentation consistency |
| `npm run gen:symbol-pins` | Generate symbol pin data using the schematic test TypeScript configuration |

The standalone renderer does not currently have its own npm script. Its build and CLI commands are documented in [standalone-renderer/README.md](standalone-renderer/README.md).

## Standalone renderers

The source directory `standalone-renderer/` contains two independent command-line renderers:

- `standalone-renderer/cli.ts` — renders the component side and copper side of a stripboard to `board-top.svg` and `board-copper.svg`.
- `standalone-renderer/schematic/cli.ts` — renders the schematic data in a project JSON file to `schematic.svg`.

Build both from this directory:

```bash
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.json
```

The compiled output is `standalone-renderer/dist/`. The desktop prototype bundles a runtime copy under `../../desktop/src/stripboard_optimizer/resources/standalone-renderer/` relative to the repository root (that path is shown from the repository root, not from this directory).

See the standalone renderer README for CLI arguments, input fields, architecture, parity-test commands and recorded results.

## Backend and deployment

The Django backend is in `../backend/`. The repository's Docker and Nginx deployment configuration is at the repository root and under `../nginx/`. These deploy the inherited web application; they are not desktop packaging instructions.
