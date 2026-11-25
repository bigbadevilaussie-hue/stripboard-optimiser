# Web-style board rendering — GUI 2.28

Ported from KarloFunke/stripboard-editor revision 21e2373f6e1da44ce017be234b2df04f42d3af30 (GPL-3.0). Source: StripboardCanvas.tsx, PlacedComponent.tsx, WireLine.tsx, CutMark.tsx, globals.css. Reuses existing package/geometry/net modules. No web server or browser.

Source checkout: cd src/frontend && npm run build:renderers. Then run the root run_gui.py. The standalone build already compiles and bundles the renderer.

GUI board previews use --web-preview, optionally --highlight ID, for import, locking, Open Solved and champion. Mirrored copper stays print style. Explicit SVG export uses the prior print pipeline. Winner SVGs represent the preview. Existing old winner SVGs are not retroactively regenerated. Existing Python assumed-contact warning overlays remain. No solver changes.

Not yet visually verified. Font fallback, original web lock icon, browser text rasterization and advisory overlays may differ. Compare the identical solved JSON to Karl's web editor before claiming parity.
