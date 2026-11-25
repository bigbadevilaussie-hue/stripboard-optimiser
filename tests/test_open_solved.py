"""Open Solved is a read-only renderer diagnostic, not a new campaign."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QDialog, QPushButton
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
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "solved.json"
                payload = {"board": {"rows": 24, "cols": 56, "wires": [], "cuts": []}}
                path.write_text(json.dumps(payload))
                before = path.read_bytes()

                def inspect(dialog):
                    buttons = {button.text(): button for button in dialog.findChildren(QPushButton)}
                    buttons["Copper side (mirrored)"].click()
                    buttons["Component side"].click()
                    return QDialog.DialogCode.Accepted

                with patch("gui.main.QFileDialog.getOpenFileName", return_value=(str(path), "")), \
                     patch("render.standalone_bridge.render_project_data", return_value=("top", "copper", "")) as render, \
                     patch.object(BoardView, "show_svg") as display, \
                     patch.object(QDialog, "exec", new=inspect), \
                     patch.object(window, "load_json") as load, \
                     patch.object(window, "start_pass_one") as solve:
                    window.render_action.trigger()
                    render.assert_called_once_with(payload)
                    self.assertEqual([call.args[0] for call in display.call_args_list],
                                     ["top", "copper", "top"])
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
