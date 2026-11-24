# Headless solver and standalone renderers — Version 2.00

Package version: `2.0.0` (repository release designation `v2.00`).

Despite this directory's historical name (`src/frontend/`), **there is no
frontend, web application or GUI here**. These are reusable headless modules
and command-line tools. Existing benchmark scripts rely on this path.

## Build

```sh
npm install
npm run build:solver
npm run build:native
npm run build:native:edge
npm run build:renderers
```

The native builds compile C decoding/routing code and the Node addon.
The solver CLI is `tests/solver/v5Solve.js`. Use strict validation
and `--save` to preserve each candidate. The independent saved-board
checker is `tests/solver/auditSavedStrict.js`.

## Default research policy

- Knife/between-hole cuts **allowed**: `--drilled 0`
- Insulated stacked wire paths **allowed**: `--nostack 0`
- Locked board rows and columns: set `board.lockedRows=true` and
  `board.lockedCols=true` in the project JSON
- Real component geometry and electrical validity must still pass
- The existing speed probe is available via `--speedprobe` in the solver CLI

## SVGs (no browser)

```sh
node standalone-renderer/dist/standalone-renderer/cli.js project.json --output /tmp/render
node standalone-renderer/dist/standalone-renderer/schematic/cli.js project.json --output /tmp/render
```

The corresponding TypeScript sources and compiled standalone renderers remain
under `standalone-renderer/`. Build them with `npm run build:renderers`.
