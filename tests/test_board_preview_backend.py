"""Board preview backend isolation: identical SVG bytes, cache and fallback."""
import os
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from render.schematic_bridge import rasterize_board_svg

try:
    from PySide6.QtWidgets import QApplication
    from gui.main import BoardView
except ImportError:
    QApplication = None
    BoardView = None

SVG = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 30 30"><line x1="1" y1="2" x2="20" y2="25" stroke="#00cc88"/><text fill="#525252" paint-order="stroke" x="2" y="10">P1</text></svg>'


class BoardRasterTests(unittest.TestCase):
    def test_same_unmodified_svg_and_schematic_converter_options(self):
        png = b"\x89PNG\r\n\x1a\nfixture"
        def convert(args, **kwargs):
            self.assertEqual(args[:6], ["rsvg-convert", "-w", "2400", "-b", "white", "-o"])
            self.assertEqual(Path(args[-1]).read_text(), SVG)
            Path(args[-2]).write_bytes(png)
            return subprocess.CompletedProcess(args, 0, "", "")
        with patch("render.schematic_bridge.tool_path", return_value="rsvg-convert"), \
             patch("render.schematic_bridge.subprocess.run", side_effect=convert):
            self.assertEqual(rasterize_board_svg(SVG), png)


@unittest.skipIf(QApplication is None, "PySide6 unavailable")
class BoardPreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_board_uses_raster_and_caches_by_source(self):
        view = BoardView()
        try:
            with patch("render.schematic_bridge.rasterize_board_svg", return_value=b"png") as raster, \
                 patch.object(view, "show_png") as display, \
                 patch.object(view, "_show_qt_svg") as fallback:
                view.show_svg(SVG)
                view.show_svg(SVG)
                raster.assert_called_once_with(SVG)
                self.assertEqual(display.call_count, 2)
                fallback.assert_not_called()
                for i in range(4):
                    view.show_svg(SVG.replace("P1", str(i)))
                self.assertEqual(len(view._board_png_cache), 3)
        finally:
            view.close()

    def test_conversion_failure_warns_and_preserves_fallback_input(self):
        view = BoardView()
        warnings = []
        view.render_warning.connect(warnings.append)
        try:
            with patch("render.schematic_bridge.rasterize_board_svg", side_effect=RuntimeError("missing converter")), \
                 patch.object(view, "_show_qt_svg") as fallback:
                view.show_svg(SVG)
                fallback.assert_called_once_with(SVG, schematic=False)
                self.assertIn("QtSvg fallback", warnings[0])
                self.assertEqual(view._board_png_cache, {})
        finally:
            view.close()
