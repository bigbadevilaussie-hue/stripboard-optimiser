#!/bin/bash
# Adapted from the tested Route-Mate macOS build. Run from any directory.
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$PWD"
export PATH="/opt/local/bin:$PATH"
PYTHON="$(command -v "${PYTHON:-python3}")"
NAME=StripSolve
DEST="$HOME/Desktop/$NAME.app"
[[ "$(uname -s)" == Darwin ]] || { echo "Build on the target Mac."; exit 1; }
[[ ! -e "$DEST" && ! -L "$DEST" ]] || { echo "Move the existing $DEST aside first; nothing overwritten."; exit 1; }
for tool in node npm clang git sips iconutil rsvg-convert ditto codesign; do
    command -v "$tool" >/dev/null || { echo "Missing $tool (rsvg-convert: sudo port install librsvg)."; exit 1; }
done
"$PYTHON" -m PyInstaller --version || { echo "Install: $PYTHON -m pip install pyinstaller"; exit 1; }
"$PYTHON" -c 'import PySide6'
BUILD="$(mktemp -d /tmp/stripsolve-build.XXXXXXXX)"
echo "Build and diagnostic files: $BUILD"
FRONT="$ROOT/src/frontend"
VERSION="$(tr -d '[:space:]' < "$ROOT/gui/VERSION")"
git -C "$ROOT" rev-parse --short=12 HEAD > "$BUILD/BUILD_REVISION"
echo "Building StripSolve $VERSION, revision $(cat "$BUILD/BUILD_REVISION")"

# Build all existing native and headless components from this checkout.
(
    cd "$FRONT"
    npm install
    npm run build:solver
    npm run build:native
    npm run build:native:edge
    npm run build:renderers
)

# Export approved artwork with the existing generator, not a new design.
QT_QPA_PLATFORM=offscreen "$PYTHON" -c 'from PySide6.QtWidgets import QApplication; from gui.assets_ui import export_assets; app=QApplication([]); export_assets()'
ICONSET="$BUILD/StripSolve.iconset"
mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
    sips -z "$size" "$size" "$ROOT/gui/assets/app_icon.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
    double=$((size * 2))
    sips -z "$double" "$double" "$ROOT/gui/assets/app_icon.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$BUILD/StripSolve.icns"

# Stage only runtime files, never research boards, Work or a Git checkout.
STAGE="$BUILD/stage"
SOLVER="$FRONT/tests/solver"
mkdir -p "$STAGE/solver" "$STAGE/wasm"
cp "$SOLVER/"*.js "$STAGE/solver/"
ditto "$SOLVER/out" "$STAGE/solver/out"
cp "$FRONT/components/stripboard/v5wasm/"*.wasm "$STAGE/wasm/"
NATIVE="$SOLVER/native/build"
for file in "$NATIVE/v5native.node" "$NATIVE/libv5decode.so" "$NATIVE/libv5route.so" "$NATIVE/edge/libv5decode.so"; do
    [[ -s "$file" ]] || { echo "Missing native artifact $file"; exit 1; }
done
NODE_BIN="$(command -v node)"
RSVG_BIN="$(command -v rsvg-convert)"
QT_QPA_PLATFORM=offscreen "$PYTHON" -B -m unittest discover -s tests -v

# PyInstaller collects the Python/Qt runtime and native Mach-O dependencies.
"$PYTHON" -m PyInstaller --clean --noconfirm --windowed --onedir \
    --name "$NAME" --icon "$BUILD/StripSolve.icns" \
    --osx-bundle-identifier org.stripsolve.desktop \
    --paths "$ROOT" \
    --distpath "$BUILD/dist" --workpath "$BUILD/work" --specpath "$BUILD" \
    --add-data "$ROOT/VERSION:." \
    --add-data "$ROOT/gui/VERSION:gui" \
    --add-data "$BUILD/BUILD_REVISION:." \
    --add-data "$ROOT/gui/assets/app_icon.png:gui/assets" \
    --add-data "$ROOT/gui/icons:gui/icons" \
    --add-data "$FRONT/standalone-renderer/dist:renderer-runtime/dist" \
    --add-binary "$NODE_BIN:renderer-runtime" \
    --add-binary "$RSVG_BIN:renderer-runtime" \
    --add-data "$STAGE/solver:src/frontend/tests/solver" \
    --add-data "$STAGE/wasm:src/frontend/components/stripboard/v5wasm" \
    --add-binary "$NATIVE/v5native.node:src/frontend/tests/solver/native/build" \
    --add-binary "$NATIVE/libv5decode.so:src/frontend/tests/solver/native/build" \
    --add-binary "$NATIVE/libv5route.so:src/frontend/tests/solver/native/build" \
    --add-binary "$NATIVE/edge/libv5decode.so:src/frontend/tests/solver/native/build/edge" \
    --collect-submodules pipeline --collect-submodules prepare --collect-submodules render \
    run_gui.py

APP="$BUILD/dist/$NAME.app"
RUNTIME="$APP/Contents/Frameworks"
[[ -x "$APP/Contents/MacOS/$NAME" && -d "$RUNTIME" ]]
# Exercise shipped tools with no MacPorts PATH and no development checkout cwd.
SMOKE="$BUILD/smoke"
mkdir -p "$SMOKE/projects" "$SMOKE/board" "$SMOKE/schematic"
FIXTURE="$ROOT/analysis/WR_Audio/20k/seed_0050.json"
cp "$FIXTURE" "$SMOKE/projects/1.json"
(
    cd "$SMOKE"
    export PATH="/usr/bin:/bin"
    unset V5_NATIVE_LIB_DIR V5_NATIVE_ROUTE_LIB_DIR
    NODE="$RUNTIME/renderer-runtime/node"
    CLI="$RUNTIME/src/frontend/tests/solver/v5Solve.js"
    "$NODE" --version
    "$NODE" "$RUNTIME/renderer-runtime/dist/standalone-renderer/cli.js" "$SMOKE/projects/1.json" --output "$SMOKE/board"
    "$NODE" "$RUNTIME/renderer-runtime/dist/standalone-renderer/schematic/cli.js" "$SMOKE/projects/1.json" --output "$SMOKE/schematic"
    "$RUNTIME/renderer-runtime/rsvg-convert" -w 2400 -b white -o "$SMOKE/schematic.png" "$SMOKE/schematic/schematic.svg"
    [[ -s "$SMOKE/board/board-top.svg" && -s "$SMOKE/board/board-copper.svg" && -s "$SMOKE/schematic.png" ]]
    "$NODE" "$CLI" --data "$SMOKE" --id 1 --native 1 --speedprobe 100 > "$SMOKE/probe.json"
    V5_NATIVE_LIB_DIR="$RUNTIME/src/frontend/tests/solver/native/build/edge" \
        "$NODE" "$CLI" --data "$SMOKE" --id 1 --native 1 --speedprobe 100 > "$SMOKE/probe-edge.json"
    "$NODE" "$RUNTIME/src/frontend/tests/solver/auditSavedStrict.js" "$SMOKE/projects/1.json" "$SMOKE/projects/1.json" > "$SMOKE/audit.json"
)
codesign --verify --deep --strict "$APP"
# Re-check immediately before copying. Never replace an existing Desktop app.
[[ ! -e "$DEST" && ! -L "$DEST" ]] || { echo "Destination now exists: $DEST"; exit 1; }
ditto "$APP" "$DEST"
echo "BUILT: $DEST"
echo "Double-click StripSolve.app on your Desktop, then test a complete Audio DEBUG run."
echo "Build files and smoke logs: $BUILD"
