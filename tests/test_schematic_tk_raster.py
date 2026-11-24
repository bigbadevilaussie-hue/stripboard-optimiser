"""Exact old Tk schematic raster conversion, with no solver or JSON mutation."""
import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from render.schematic_bridge import rasterize_schematic_svg


PNG_STUB = b"\x89PNG\r\n\x1a\n" + b"fixture raster payload"


class OriginalTkSchematicRasterTests(unittest.TestCase):
    def test_tk_rsvg_command_preserves_svg_and_returns_png(self):
        svg = '<svg xmlns="http://www.w3.org/2000/svg"><text>TVS USB F1</text></svg>'
        calls = []

        def fake_run(args, **kwargs):
            calls.append(list(args))
            self.assertEqual(args[:6], [
                "/opt/homebrew/bin/rsvg-convert",
                "-w", "2400", "-b", "white", "-o",
            ])
            self.assertEqual(kwargs["timeout"], 60)
            self.assertFalse(kwargs["check"])
            self.assertEqual(Path(args[-1]).read_text(encoding="utf-8"), svg)
            Path(args[-2]).write_bytes(PNG_STUB)
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch("render.schematic_bridge.shutil.which",
                   return_value="/opt/homebrew/bin/rsvg-convert"), \
             patch("render.schematic_bridge.subprocess.run",
                   side_effect=fake_run):
            png = rasterize_schematic_svg(svg)

        self.assertEqual(png, PNG_STUB)
        self.assertEqual(len(calls), 1)
        self.assertEqual(svg, '<svg xmlns="http://www.w3.org/2000/svg"><text>TVS USB F1</text></svg>')
        # The temp SVG/PNG files disappear when the method returns.
        self.assertFalse(Path(calls[0][-1]).exists())
        self.assertFalse(Path(calls[0][-2]).exists())

    def test_missing_librsvg_reports_explicit_requirements(self):
        with patch("render.schematic_bridge.shutil.which", return_value=None), \
             patch("render.schematic_bridge.subprocess.run") as run:
            with self.assertRaisesRegex(RuntimeError, "brew install librsvg"):
                rasterize_schematic_svg("<svg></svg>")
        run.assert_not_called()

    def test_converter_failure_is_not_misreported_as_success(self):
        with patch("render.schematic_bridge.shutil.which", return_value="rsvg-convert"), \
             patch("render.schematic_bridge.subprocess.run",
                   return_value=subprocess.CompletedProcess(
                       [], 1, "", "invalid SVG"
                   )):
            with self.assertRaisesRegex(RuntimeError, "invalid SVG"):
                rasterize_schematic_svg("<svg></svg>")

    def test_png_must_exist_and_have_png_signature(self):
        with patch("render.schematic_bridge.shutil.which", return_value="rsvg-convert"), \
             patch("render.schematic_bridge.subprocess.run",
                   return_value=subprocess.CompletedProcess([], 0, "", "")):
            with self.assertRaisesRegex(RuntimeError, "did not produce"):
                rasterize_schematic_svg("<svg></svg>")

        def fake_png(args, **kwargs):
            Path(args[-2]).write_bytes(b"not an image")
            return subprocess.CompletedProcess(args, 0, "", "")

        with patch("render.schematic_bridge.shutil.which", return_value="rsvg-convert"), \
             patch("render.schematic_bridge.subprocess.run", side_effect=fake_png):
            with self.assertRaisesRegex(ValueError, "invalid PNG"):
                rasterize_schematic_svg("<svg></svg>")


if __name__ == "__main__":
    unittest.main()
