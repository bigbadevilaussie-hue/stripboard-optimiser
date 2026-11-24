# Headless solver and standalone renderers — Version 2.00

Package version: `2.0.0` (repository consolidation designation `2.00`; no Git tag published). GUI is tracked separately at `../../gui/VERSION` (currently `2.01`).

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

## Tests and audit

From the repository root: `python3 scripts/audit_repo_integrity.py` and
`python3 -m unittest discover -s tests -p 'test_*.py' -v`.

From this directory after the native/TypeScript builds: `npm run test:headless`,
then explicitly run `node tests/solver/testAuditSavedStrict.js`,
`node tests/solver/testNativeBodyBoardBounds.js`,
`node tests/solver/testPackageBodyBoardBounds.js` and
`node tests/solver/testWireColumnPolish.js`.

Those `test*.js` scripts are **not** automatically discovered by the
`*.test.js` harness. The repository currently has no committed
`package-lock.json`, so `npm install` is not a frozen dependency resolution.
See [full audit](../../docs/REPOSITORY_AUDIT_2026-11-24.md).

`--strict 1` is opt-in, `--wire-polish 1` is opt-in, and
`auditSavedStrict.js` requires a both-locked original **prepared** input.
For MOTOEX, the original raw 99×500 input is not that prepared snapshot.
