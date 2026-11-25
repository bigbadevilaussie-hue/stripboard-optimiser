#!/usr/bin/env python3
"""Build StripSolve artwork with PySide6, entirely offline.

    python3 tools/build_icons.py              # keep existing custom artwork
    python3 tools/build_icons.py --png        # export 48x48 toolbar PNGs
    python3 tools/build_icons.py --force      # refresh SVGs; keep approved PNG

Produces gui/assets/app_icon.svg, gui/assets/app_icon.png (1024x1024),
and 10 gui/icons/*.svg masters (48x48 rendered at 24x24 in the GUI).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtWidgets import QApplication
from gui.assets_ui import ASSETS_DIR, ICONS_DIR, BUTTON_ICON_FILES, export_assets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--png", action="store_true",
                        help="also export 48x48 toolbar PNG copies")
    parser.add_argument("--force", action="store_true",
                        help="refresh existing toolbar artwork; preserve approved app PNG")
    args = parser.parse_args()
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    made = export_assets(force=args.force, toolbar_png=args.png)
    print(f"StripSolve icons: {len(BUTTON_ICON_FILES)} toolbar SVGs + 1024px app PNG")
    print(f"  {ICONS_DIR}")
    print(f"  {ASSETS_DIR}")
    print(f"  Created/updated: {len(made)} file(s)")
    for path in made:
        print("   ✓", path.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
