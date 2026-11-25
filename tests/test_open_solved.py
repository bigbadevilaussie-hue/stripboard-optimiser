"""Open Solved is a read-only renderer diagnostic, not a new campaign."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QDialog
    from gui.main import RouteMateWindow, BoardView
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 unavailable")
class OpenSolvedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_open_solved_renders_both_sides_without_changing_project(self):
        window = RouteMateWindow()
        try:
            self.assertTrue(window.render_action.isEnabled())
            window.load_action.setEnabled(False)
            self.assertFalse(window.render_action.isEnabled())
            window.load_action.setEnabled(True)
            self.assertTrue(window.render_action.isEnabled())
            original = {"board": {"rows": 5, "cols": 5}}
            window.project = original
            window._top_svg = "old top"
            window._copper_svg = "old copper"
            window._schematic_svg = "old schematic"
            window._schematic_png = b"old png"
            window.schematic_action.setEnabled(True)
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "solved.json"
                payload = {"board": {"rows": 24, "cols": 56, "wires": [], "cuts": []}}
                path.write_text(json.dumps(payload))
                before = path.read_bytes()

                with patch("gui.main.QFileDialog.getOpenFileName", return_value=(str(path), "")), \
                     patch("render.standalone_bridge.render_project_data", return_value=("top", "copper", "")) as render, \
                     patch.object(BoardView, "show_svg") as display, \
                     patch.object(BoardView, "show_png") as display_png, \
                     patch.object(window, "_build_schematic_preview", return_value=("solved schematic", b"solved png")) as schematic, \
                     patch.object(QDialog, "exec", side_effect=AssertionError("Unexpected preview dialog")), \
                     patch.object(window, "load_json") as load, \
                     patch.object(window, "start_pass_one") as solve:
                    window.render_action.trigger()
                    render.assert_called_once_with(payload, web_preview=True)
                    self.assertIs(window.preview_stack.currentWidget(), window.top_view)
                    self.assertIn("solved.json", window.board_project_label.text())
                    self.assertTrue(window.checklist.isHidden())
                    self.assertFalse(window.open_solved_summary.isHidden())
                    self.assertIn("solved.json", window.open_solved_summary.text())
                    schematic.assert_called_once_with(payload)
                    self.assertTrue(window.schematic_action.isEnabled())
                    window.copper_action.trigger()
                    window.schematic_action.trigger()
                    self.assertTrue(window.schematic_action.isChecked())
                    display_png.assert_called_once_with(b"solved png")
                    window.top_action.trigger()
                    self.assertEqual([call.args[0] for call in display.call_args_list],
                                     ["top", "top", "copper", "top"])
                    window.return_project_button.click()
                    self.assertIsNone(window._opened_solved)
                    self.assertFalse(window.checklist.isHidden())
                    self.assertTrue(window.open_solved_summary.isHidden())
                    self.assertEqual(display.call_args.args[0], "old top")
                    self.assertTrue(window.schematic_action.isEnabled())
                    window.schematic_action.trigger()
                    self.assertEqual(display_png.call_args.args[0], b"old png")
                    load.assert_not_called()
                    solve.assert_not_called()
                self.assertEqual(path.read_bytes(), before)
            self.assertIs(window.project, original)
            self.assertEqual(window._top_svg, "old top")
            self.assertEqual(window._copper_svg, "old copper")
        finally:
            window.close()

    def test_cancel_does_not_render(self):
        window = RouteMateWindow()
        try:
            with patch("gui.main.QFileDialog.getOpenFileName", return_value=("", "")), \
                 patch("render.standalone_bridge.render_project_data") as render:
                window.render_json()
                render.assert_not_called()
        finally:
            window.close()
