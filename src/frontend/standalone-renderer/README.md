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

## Route-Mate GUI 2.01 display contract

The SVG sources and compiled Node CLIs in this directory remain the
authoritative generators for board and schematic imagery. Route-Mate displays
board top/copper SVG through QtSvg, but for **schematic text fidelity** it
uses the **original old-Tk** raster display path: convert the generated
`schematic.svg` into a 2400-pixel white-background PNG with `rsvg-convert`.

On a MacPorts Mac: `sudo port install librsvg`, then check
`/opt/local/bin/rsvg-convert --version`. This raster conversion occurs in
`render/schematic_bridge.py`; it does not alter the SVG renderer or project
JSON. The GUI's rendering is separate from CLI optimisation.
