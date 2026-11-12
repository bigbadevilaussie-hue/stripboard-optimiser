# Standalone renderers

This directory contains two Node.js command-line renderers extracted from the frontend rendering implementation:

1. The **stripboard renderer** creates component-side and copper-side SVGs.
2. The **schematic renderer** creates a schematic SVG from the schematic data in a saved project JSON.

The production rendering paths use Node.js filesystem APIs and SVG generation; they do not require React, Zustand, Next.js or a browser DOM.

## Location and outputs

Source of truth:

`src/frontend/standalone-renderer/`

Compiled JavaScript:

`src/frontend/standalone-renderer/dist/`

The desktop application's bundled runtime copy:

`desktop/src/stripboard_optimizer/resources/standalone-renderer/`

The desktop copy is a runtime bundle. Make renderer source changes in this directory, rebuild `dist/`, then keep the desktop runtime copy synchronised. There is currently no automated sync script documented for that copy.

| Renderer | TypeScript entry point | Compiled entry point | Output |
|---|---|---|---|
| Stripboard | `cli.ts` | `dist/standalone-renderer/cli.js` | `board-top.svg`, `board-copper.svg` |
| Schematic | `schematic/cli.ts` | `dist/standalone-renderer/schematic/cli.js` | `schematic.svg` |

## Requirements

- Node.js.
- Frontend dependencies installed in `src/frontend/node_modules`.
- TypeScript compiler.
- `tsc-alias`.

Run commands from the frontend directory:

```bash
cd ~/Documents/stripboard-optimiser/src/frontend
```

## Build

Compile the production renderer:

```bash
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.json
```

Run `tsc-alias` immediately after TypeScript compilation to rewrite the `@/` aliases in emitted JavaScript.

The production TypeScript configuration includes all `.ts` files under this directory, including the schematic renderer. It excludes `dist/` and `node_modules/`.

There is no dedicated standalone-renderer npm script in `src/frontend/package.json`.

## Stripboard CLI

Run:

```bash
node standalone-renderer/dist/standalone-renderer/cli.js <project.json> [--output <dir>]
```

Example:

```bash
node standalone-renderer/dist/standalone-renderer/cli.js standalone-renderer/example-project.json --output /tmp/board-render
```

Options:

| Argument | Description |
|---|---|
| `project.json` | One saved project JSON file; required. |
| `--output <dir>` | Output directory. |
| `-o <dir>` | Short form of `--output`. |
| `--output=<dir>` | Equals-sign form. |

If no output directory is supplied, the current working directory is used. The output directory is created automatically.

The input must be a JSON object containing a `board` object and a `components` array. The renderer produces:

- `board-top.svg` — component side.
- `board-copper.svg` — copper side.

The CLI reports board dimensions, component count, wire count and cut count. Missing or non-array `board.wires` and `board.cuts` are reported as zero.

## Schematic CLI

Run:

```bash
node standalone-renderer/dist/standalone-renderer/schematic/cli.js <project.json> [--output <dir>]
```

Example:

```bash
node standalone-renderer/dist/standalone-renderer/schematic/cli.js path/to/project.json --output /tmp/schematic-render
```

The schematic CLI accepts `--output <dir>` or `-o <dir>`. It writes `schematic.svg` into the selected directory (or the current directory if no output directory is supplied).

The schematic renderer reads these project fields:

- `components`
- `componentDefs`
- `nets`
- `netAssignments`
- `schematicWires`
- `netLabels`

It resolves component symbol definitions, applies schematic rotation and mirroring, draws component symbols and wires, and uses net colours where the project data provides them. This is a renderer, not a schematic editor, electrical rule checker or netlist validator.

## Architecture

### Stripboard renderer

| File | Responsibility |
|---|---|
| `cli.ts` | Node.js CLI for board SVG output |
| `render.ts` | Full-board SVG rendering entry point |
| `part_body.ts` | Component body SVG generation |
| `part_drawing.ts` | Standalone component geometry calculations |
| `static_part.ts` | Static component rendering, pins and labels |
| `example-project.json` | Example board input |
| `tsconfig.json` | Production TypeScript configuration |
| `tsconfig.test.json` | Test TypeScript configuration |

### Schematic renderer

| File | Responsibility |
|---|---|
| `schematic/cli.ts` | Node.js CLI for schematic SVG output |
| `schematic/render.ts` | Schematic SVG composition and bounds |
| `schematic/resolve_symbol.ts` | Component-definition and symbol resolution |
| `schematic/component_block.ts` | Component symbol block rendering |
| `schematic/draw_symbol.ts` | Symbol geometry and pin rendering |
| `schematic/net_label.ts` | Net-label glyph rendering |
| `schematic/symbol_geometry.ts` | Rotation, mirroring, transforms and bounds |
| `schematic/wire_line.ts` | Schematic wire rendering |
| `schematic/builtin_defs.ts` | Built-in schematic definition support |

Shared renderer dependencies are imported from the existing frontend component, data, type and utility modules. The compiled output under `dist/` contains those runtime dependencies.

The desktop UI bundles the compiled runtime separately under `desktop/src/stripboard_optimizer/resources/standalone-renderer/`. The desktop's `Render JSON...` action runs the board and schematic CLIs separately, converts their SVGs to PNG with `rsvg-convert`, and loads the available images in the three-view viewer.

## Parity tests

The five parity test source files are:

```text
test_compare.tsx
test_static_part_parity.tsx
test_static_part_colours.tsx
test_board_parity.tsx
test_part_drawing_parity.tsx
```

They compare the standalone renderer with the original React implementation. Compile from `src/frontend`:

```bash
rm -rf standalone-renderer/dist-test
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.test.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.test.json
```

Run:

```bash
node standalone-renderer/dist-test/standalone-renderer/test_compare.js
node standalone-renderer/dist-test/standalone-renderer/test_static_part_parity.js
node standalone-renderer/dist-test/standalone-renderer/test_static_part_colours.js
node standalone-renderer/dist-test/standalone-renderer/test_board_parity.js
node standalone-renderer/dist-test/standalone-renderer/test_part_drawing_parity.js
```

The recorded parity runs used these external fixture paths:

```text
~/Desktop/repo/motomix.json
~/Desktop/repo/moto14wires30cuts.json
```

Those files are outside the repository and must exist at those paths for the corresponding recorded runs. The repository also contains separate master fixtures under `test-fixtures/masters/`; those are not the external files listed above.

### Recorded parity results

The previously recorded results are:

| Comparison | Fixture | Result |
|---|---|---|
| Component body parity | `motomix.json` | Match |
| Static part parity | `motomix.json` | Match |
| Static part real pin colours | `motomix.json` | Match |
| Copied geometry parity | `moto14wires30cuts.json` | 32 of 32 match |
| Full-board top SVG | `moto14wires30cuts.json` | Match |
| Full-board copper SVG | `moto14wires30cuts.json` | Match |

Recorded full-board fixture details:

- Board: 24 × 56.
- Components: 44.
- Geometry parity placements: 32.
- Distinct component definition IDs: 13.
- Flexible components: 24.
- Wires: 14.
- Cuts: 30.

Recorded SVG lengths:

| Output | React reference | Standalone | Result |
|---|---:|---:|---|
| Top | 212,721 characters | 212,721 characters | Match |
| Copper | 183,726 characters | 183,726 characters | Match |

These are historical recorded results, not a claim that the tests were rerun during the current documentation update.

## Runtime dependencies

The inspected compiled production entry points use Node.js filesystem/path APIs. The renderer is designed to run without React, Zustand, Next.js or a browser DOM.

The desktop GUI adds separate image-conversion and display requirements: `rsvg-convert` and Python Pillow. Those are desktop integration dependencies, not dependencies of the SVG renderer CLI itself.

## Maintenance

- Keep the TypeScript source under this directory as the authoritative renderer implementation.
- Rebuild `dist/` after source changes.
- Synchronise the desktop runtime copy after rebuilding.
- Keep the five parity tests as regression protection.
- If `part_drawing.ts` changes, compare it with the original frontend geometry implementation.
- Do not commit generated SVG output unless it is explicitly required.
