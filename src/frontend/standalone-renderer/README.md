# Standalone Stripboard Renderer

A Node.js command-line renderer that converts a saved Stripboard Optimiser project JSON file into two SVG files:

- `board-top.svg` — component side.
- `board-copper.svg` — copper side.

The renderer is extracted from the existing frontend and runs in Node.js without React, Zustand, Next.js or a browser DOM in its production rendering path.

## Requirements

- Node.js
- Dependencies installed in `src/frontend/node_modules`
- TypeScript compiler
- `tsc-alias`

Run commands from:

```bash
cd ~/Documents/stripboard-optimiser/src/frontend
```

## Build

Compile the production renderer:

```bash
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.json
```

Run `tsc-alias` immediately after TypeScript compilation. It rewrites the `@/` path aliases in the emitted JavaScript.

Compiled output:

```text
standalone-renderer/dist/
```

CLI entry point:

```text
standalone-renderer/dist/standalone-renderer/cli.js
```

There is currently no dedicated standalone-renderer build script in `package.json`.

## Usage

```bash
node standalone-renderer/dist/standalone-renderer/cli.js <project.json> [--output <dir>]
```

Example using the included example project:

```bash
node standalone-renderer/dist/standalone-renderer/cli.js standalone-renderer/example-project.json --output /tmp/render-test
```

### Arguments

| Argument | Description |
|---|---|
| `project.json` | Input project JSON file. Required. |
| `--output <dir>` | Output directory. |
| `-o <dir>` | Short form of `--output`. |
| `--output=<dir>` | Equals-sign form of the output option. |

If `--output` is omitted, the current working directory (`.`) is used. The output directory is created automatically when necessary.

### Generated files

```text
<output-directory>/
├── board-top.svg
└── board-copper.svg
```

The CLI reports board dimensions, component count, wire count, cut count and the paths of both generated files.

## Input JSON

The CLI accepts a saved project JSON file directly; no conversion or preprocessing is required.

The CLI checks for these top-level properties:

- `board` — an object.
- `components` — an array.

The renderer consumes the project's board and component data to generate the SVG output. The CLI reports `board.rows`, `board.cols`, `board.wires` and `board.cuts`. If `board.wires` or `board.cuts` is absent or is not an array, its reported count is zero.

### Example project

The included example is:

```text
standalone-renderer/example-project.json
```

It is accepted directly by the CLI. The verified invocation:

```bash
node standalone-renderer/dist/standalone-renderer/cli.js standalone-renderer/example-project.json --output /tmp/render-test
```

reported:

```text
Board:     69 rows x 69 cols
Components: 2
Wires:     0
Cuts:      0
Wrote:     /tmp/render-test/board-top.svg
Wrote:     /tmp/render-test/board-copper.svg
```

## Error handling

The CLI exits with status 1 and reports an error for:

- Missing input file.
- Invalid JSON.
- JSON that is not an object.
- Missing or invalid `board` object.
- Missing or invalid `components` array.
- Unknown command-line options.
- Missing output directory argument.
- Rendering failures.

Only one input project JSON file is accepted.

## Rendering options

The CLI currently enables all three options:

| Option | Value |
|---|---|
| Colour rendering | Enabled |
| Component labels | Enabled |
| Pin labels | Enabled |

Both board views are generated in one invocation:

- **Top (`place`)** — component side of the board.
- **Copper (`cut`)** — copper side of the board.

## Architecture

| File | Responsibility |
|---|---|
| `render.ts` | Full-board SVG rendering and public rendering entry point |
| `part_body.ts` | Component body SVG generation |
| `part_drawing.ts` | Standalone copy of the component geometry calculation |
| `static_part.ts` | Static component rendering, including pins and labels |
| `cli.ts` | Node.js command-line interface |
| `example-project.json` | Example input project |
| `tsconfig.json` | Production TypeScript configuration |
| `tsconfig.test.json` | Test TypeScript configuration |

The geometry function in `part_drawing.ts` is copied from the original application rather than imported from its TSX module. This avoids loading the React JSX runtime in the production renderer.

The original application rendering implementation remains separate.

## Tests and parity verification

The parity tests compare standalone SVG output and geometry with the original React implementation.

### Test files

```text
standalone-renderer/test_compare.tsx
standalone-renderer/test_static_part_parity.tsx
standalone-renderer/test_static_part_colours.tsx
standalone-renderer/test_board_parity.tsx
standalone-renderer/test_part_drawing_parity.tsx
```

### Compile the test suite

Run once after source changes:

```bash
cd ~/Documents/stripboard-optimiser/src/frontend
rm -rf standalone-renderer/dist-test
./node_modules/.bin/tsc -p standalone-renderer/tsconfig.test.json
./node_modules/.bin/tsc-alias -p standalone-renderer/tsconfig.test.json
```

### Run all five tests

```bash
node standalone-renderer/dist-test/standalone-renderer/test_compare.js
node standalone-renderer/dist-test/standalone-renderer/test_static_part_parity.js
node standalone-renderer/dist-test/standalone-renderer/test_static_part_colours.js
node standalone-renderer/dist-test/standalone-renderer/test_board_parity.js
node standalone-renderer/dist-test/standalone-renderer/test_part_drawing_parity.js
```

### Test fixtures

The parity tests were run using these external fixtures:

```text
/Users/nick/Desktop/repo/motomix.json
/Users/nick/Desktop/repo/moto14wires30cuts.json
```

These files are outside the clean repository clone. The tests therefore depend on their availability at those paths unless the fixture paths are changed.

The clean clone also contains:

```text
test-fixtures/masters/moto/moto.json
test-fixtures/masters/audio/audio.json
```

Those are separate repository fixtures; they are not the two external files used by the reported parity runs.

### Verified parity results

Reported test results:

| Comparison | Fixture | Result |
|---|---|---|
| Component body parity | `motomix.json` | Match |
| Static part parity | `motomix.json` | Match |
| Static part real pin colours | `motomix.json` | Match |
| Copied geometry parity | `moto14wires30cuts.json` | 32 of 32 match |
| Full-board top SVG | `moto14wires30cuts.json` | Match |
| Full-board copper SVG | `moto14wires30cuts.json` | Match |

The expanded full-board fixture contained:

- Board: 24 × 56
- Components: 44
- Placed components in geometry parity: 32
- Distinct component definition IDs: 13
- Flexible components: 24
- Wires: 14
- Cuts: 30

Full-board SVG comparison:

| Output | React reference | Standalone | Result |
|---|---:|---:|---|
| Top | 212,721 characters | 212,721 characters | Match |
| Copper | 183,726 characters | 183,726 characters | Match |

The smaller component-level tests use F1 and the 12V MOSFET and cover colour, monochrome and mirrored body rendering where applicable.

## Dependencies

### Production runtime

The inspected compiled production files use Node.js:

- `fs`
- `path`

No React, `react/jsx-runtime`, Zustand or Next.js imports were found in the inspected compiled production path (`cli.js`, `render.js` and `part_drawing.js`).

### Development and test dependencies

The frontend package configuration includes:

- `jsdom` — client-side React test rendering.
- `@types/jsdom` — TypeScript definitions for jsdom.
- `tsc-alias` — rewrites TypeScript path aliases in compiled output.

The original React components are used by parity tests as reference implementations. They are not production rendering dependencies.

## Maintenance

The copied geometry implementation in `part_drawing.ts` must remain consistent with the original application geometry function.

If the original geometry changes, update the standalone copy and run the geometry parity test against the original implementation.

Retain the parity tests as regression protection.

Generated SVGs are output artefacts and should not be committed unless specifically required.
