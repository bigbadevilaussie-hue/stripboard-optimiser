# Board preview backend diagnostic — GUI 2.26

## Historical fix

Commit [302d35d](https://github.com/bigbadevilaussie-hue/stripboard-optimiser/commit/302d35d7d275b993086f7acc0dd95ec9b73c14ee)
restored the original Tk schematic preview using librsvg rather than direct QtSvg.
The earlier [fcfab4c](https://github.com/bigbadevilaussie-hue/stripboard-optimiser/commit/fcfab4cdf16cda983c52f6012d24683e39c32570)
suppressed white text halos in the Qt schematic fallback.
The commits document missing/faint labels, not a demonstrated wire-colour loss.

## Controlled change

Both board sides now use the same 2400px librsvg conversion and QPixmap display as
schematic. The generated SVG is passed unchanged, with no injected font/colour CSS.
Up to three board PNGs are cached by SVG SHA256. Lock highlights produce new cache
keys. A conversion failure logs an explicit Activity warning and falls back to
QtSvg without the removed text overrides. Schematic behavior is unchanged.
Saved SVGs, Python overlays, native geometry, scoring and solver are untouched.

## Compare on the Mac

Use the exact same solved JSON for Karl's web editor, the existing print view,
and StripSolve. Compare the raw saved SVG in Safari with the new GUI preview.
To rasterize the same file manually:

```bash
PATH="/opt/local/bin:$PATH" rsvg-convert -w 2400 -b white -o /tmp/board-preview.png "/path/to/board-components.svg"
open /tmp/board-preview.png
```

A successful GUI raster should match the librsvg image, apart from view scaling.
Look for Activity fallback warnings if it does not. At very high zoom the PNG
will not retain vector sharpness; exported SVG remains vector artwork.

Karl's interactive canvas and print renderer have distinct drawing rules (upstream
revision 21e2373f6e1da44ce017be234b2df04f42d3af30). This diagnostic does NOT port
the interactive style, remove existing overlays, or claim web editor parity.
Inspect the result before deciding whether to port those rules.

## Status

Source tests and target-Mac visual verification outstanding. The converter is
already included in the standalone build script. Rebuild after source checks
if the diagnostic is accepted.
