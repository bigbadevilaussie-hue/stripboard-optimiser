# StripSolve — macOS standalone application (GUI 2.26)

## Provenance and status

Reuse the existing Mac-tested Route-Mate windowed, onedir PyInstaller build:
[donor build script](https://github.com/bigbadevilaussie-hue/Route-Mate/blob/main/build_mac_app.sh)
and [donor macOS handover](https://github.com/bigbadevilaussie-hue/Route-Mate/blob/main/docs/STANDALONE_MACOS.md).
The donor was tested on the Intel iMac14,2 running Sonoma, Python 3.13.16,
PyInstaller 6.22.3 and PySide6. StripSolve's new native solver packaging has
not yet been built or executed on that Mac.

## Build on the iMac

Close StripSolve and move any existing Desktop StripSolve.app aside. From
the current checkout:

```bash
cd ~/Documents/stripboard-optimiser
git pull --ff-only
export PATH="/opt/local/bin:$PATH"
bash build_mac_app.sh
```

Prerequisites (already present on the development Mac unless removed):
Python 3 with requirements-gui.txt and PyInstaller installed, Node/npm,
Clang, Git, macOS sips/iconutil/ditto/codesign and MacPorts librsvg.
If missing: `python3 -m pip install -r requirements-gui.txt pyinstaller`
(using the existing Python environment) and `sudo port install librsvg`.

The script compiles the existing solver, standard/Edge native decoders and
renderers; exports the existing toolbar artwork; converts the approved
1024px StripSolve PNG into a multi-resolution ICNS; runs all source Python
tests; then builds the app with Python, Qt6, Node, rsvg-convert and its
collected Mach-O dependencies, the complete compiled renderer tree, native
addon and libraries, WASM resources, independent saved-board auditor and
version metadata. No historical research boards or Work files are included.
The script retains build and smoke-test logs under a unique
`/tmp/stripsolve-build.*` path and does not overwrite an existing Desktop app.

The packaged command-line smoke tests exercise the bundled Node, both SVG
renderers, librsvg rasterization, both native decoder speed probes and a
saved-board audit with a restricted shell PATH. A code-signature check
must also pass before the bundle is copied to the Desktop.

## Launch

```bash
open ~/Desktop/StripSolve.app
```

Or double-click the app icon. No source checkout or installed Python/Node
should be required at launch; this is a design target until tested on the
Mac. The bundled tool paths are explicit rather than relying on Finder's
PATH. The GUI title reads the captured build revision. The JS tools may
report Git unavailable when there is no checkout; their executable hashes
remain available.

The app's writable data directory is
`~/Library/Application Support/StripSolve/Work/`. Development runs still use
the existing repository Work directory. There is no automatic migration or
deletion of existing campaigns. Import sidecars still follow the normal
project-file policy. No writes into the signed application bundle are needed
for icons or workspaces.

## Acceptance checklist

- Source regression suite passes before packaging.
- Bundled CLI smoke tests and local ad-hoc signature verification pass.
- Finder launch shows approved Dock/Finder icon, splash and toolbar icons.
- Import Audio, view both board sides and schematic, confirm file picker.
- Complete a 200-seed Audio DEBUG campaign; check actual verified results,
  saved JSON and both SVGs, completion popup and writable Work location.
- Close/reopen and confirm saved campaign import works.
- Test without source checkout/developer PATH, then on a separate clean Mac
  before claiming portable distribution. MacPorts-linked library/plugin
  portability, architecture compatibility and notarisation remain unverified.
- GUI 2.26 automatically selects the bundled Edge decoder for locked Edge mounts. See [budget probe](BUDGET_PROBE.md). This must still be verified on MOTOEX. No native solver, scoring or audit rule is changed.

This package is for the target Mac architecture; it is not a universal,
notarised distribution or an installer. Pass Two remains import-only.


GUI 2.26 uses the bundled librsvg for both board previews as well as schematic. See [diagnostic](BOARD_PREVIEW_BACKEND.md). Visual verification outstanding.
