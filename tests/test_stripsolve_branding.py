"""StripSolve brand/artwork contracts; real solver behaviour is untouched."""
from __future__ import annotations

import os
import unittest
from xml.etree import ElementTree

from gui.icon_art import ICON_KEYS, app_icon_svg, icon_svg


class StripSolveArtTests(unittest.TestCase):
    def test_every_toolbar_button_has_one_valid_standalone_48px_svg(self):
        self.assertEqual(len(ICON_KEYS), 10)
        self.assertEqual(len(set(ICON_KEYS)), 10)
        for key in ICON_KEYS:
            with self.subTest(key=key):
                root = ElementTree.fromstring(icon_svg(key))
                self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
                self.assertEqual(root.attrib["viewBox"], "0 0 48 48")
                self.assertGreater(len(list(root.iter())), 2)

    def test_1024px_app_master_has_copper_and_routed_s(self):
        svg = app_icon_svg()
        root = ElementTree.fromstring(svg)
        self.assertEqual(root.attrib["width"], "1024")
        self.assertEqual(root.attrib["height"], "1024")
        self.assertIn("#c87d4b", svg)
        self.assertIn('id="route"', svg)

    def test_unknown_icon_key_is_rejected(self):
        with self.assertRaises(KeyError):
            icon_svg("unapproved_toolbar_button")


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtCore import QSize
    from PySide6.QtWidgets import QApplication
    from gui.assets_ui import (
        StripSolveSplash, _rasterize, load_app_icon, load_button_icon,
    )
    from gui.main import RouteMateWindow
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 unavailable")
class StripSolveGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_app_icon_renders_as_real_1024px_image(self):
        image = _rasterize(app_icon_svg(), 1024)
        self.assertEqual(image.width(), 1024)
        self.assertEqual(image.height(), 1024)
        self.assertFalse(load_app_icon().isNull())

    def test_ten_icons_render_in_memory_without_installed_files(self):
        for key in ICON_KEYS:
            with self.subTest(key=key):
                icon = load_button_icon(key)
                self.assertFalse(icon.isNull())
                self.assertFalse(icon.pixmap(QSize(24, 24)).isNull())

    def test_asset_generator_writes_1024_png_and_ten_svg_masters(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from PySide6.QtGui import QImage
        from gui.assets_ui import export_assets
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with patch("gui.assets_ui.ASSETS_DIR", root / "assets"), \
                 patch("gui.assets_ui.ICONS_DIR", root / "icons"):
                made = export_assets(toolbar_png=True)
                self.assertEqual(len(made), 22)  # app svg/png + 10 svg + 10 png
                png = QImage(str(root / "assets" / "app_icon.png"))
                self.assertFalse(png.isNull())
                self.assertEqual((png.width(), png.height()), (1024, 1024))
                self.assertEqual(len(list((root / "icons").glob("*.svg"))), 10)
                self.assertEqual(len(list((root / "icons").glob("*.png"))), 10)
                self.assertEqual(export_assets(toolbar_png=True), [])

    def test_existing_toolbar_actions_use_icons_and_stripsolve_name(self):
        window = RouteMateWindow()
        try:
            self.assertIn("StripSolve", window.windowTitle())
            for action in (
                window.load_action, window.stop_action,
                window.pass_one_action, window.pass_two_action,
                window.top_action, window.copper_action,
                window.schematic_action, window.render_action,
                window.exit_action,
            ):
                self.assertFalse(action.icon().isNull(), action.text())
        finally:
            window.close()

    def test_splash_can_skip_without_launching_solver(self):
        splash = StripSolveSplash()
        seen = []
        splash.finished.connect(lambda: seen.append(True))
        try:
            self.assertEqual(splash.progress.maximum(), 100)
            self.assertIn("no solver running", splash.status_label.text())
            splash._finish()
            splash._finish()
            self.assertEqual(seen, [True])
        finally:
            splash.close()


if __name__ == "__main__":
    unittest.main()
