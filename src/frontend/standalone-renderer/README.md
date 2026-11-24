# Standalone board and schematic SVG renderers

These are **headless Node.js** renderers. Both are deliberately retained
after removal of the old GUI and web editor.

Build from `src/frontend/`:

```sh
npm install
npm run build:renderers
```

Board render:

```sh
node standalone-renderer/dist/standalone-renderer/cli.js standalone-renderer/example-project.json --output /tmp/render
```

Writes `board-top.svg` and `board-copper.svg`.

Schematic render:

```sh
node standalone-renderer/dist/standalone-renderer/schematic/cli.js standalone-renderer/example-project.json --output /tmp/render
```

Writes `schematic.svg`.

Both accept the existing project JSON format and write their output only
to the requested directory. The former React-versus-renderer GUI parity
test sources were removed with the web application; keep future renderer
checks self-contained and headless.
