"""Regression: board-size and lock dialogs; no Quick Solve spacing prompt.

This test uses the real GUI import pipeline and the repository MOTOEX fixture.
Only user clicks and the external SVG renderer are mocked. No solver runs.
"""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QDialog, QMessageBox
    from gui.main import (
        BoardSizeDialog, LockDialog, RouteMateWindow,
    )
except ImportError:
    QApplication = None
    QDialog = None
    QMessageBox = None
    BoardSizeDialog = None
    LockDialog = None
    RouteMateWindow = None


@unittest.skipIf(QApplication is None, "PySide6 is not installed")
class GuiShellSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_motoex_dialogs_highlight_locks_then_stop_before_pass1(self):
        source_path = (
            Path(__file__).resolve().parents[1] /
            "test-fixtures" / "masters" / "moto" / "motoex.json"
        )
        source_bytes = source_path.read_bytes()
        sizes = {
            "actualRows": 24, "actualCols": 56,
            "wantedRows": 24, "wantedCols": 56,
            "wantedRowsMode": "fixed", "wantedColsMode": "fixed",
        }
        lock = {"locked": True, "edge": False, "slide": False, "reposition": False}
        svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><rect width="100" height="100"/></svg>'

        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "motoex.json"
            project_path.write_bytes(source_bytes)
            window = RouteMateWindow()
            try:
                with (
                    patch("gui.main.QFileDialog.getOpenFileName",
                          return_value=(str(project_path), "")),
                    patch.object(BoardSizeDialog, "exec",
                                 return_value=QDialog.DialogCode.Accepted) as size_exec,
                    patch.object(BoardSizeDialog, "values", return_value=sizes),
                    patch.object(LockDialog, "exec",
                                 return_value=QDialog.DialogCode.Accepted) as lock_exec,
                    patch.object(LockDialog, "values", return_value=lock),
                    patch.object(RouteMateWindow, "_render_component_side",
                                 return_value=(svg, "")) as render,
                    patch.object(RouteMateWindow, "_start_speed_probe") as probe,
                    patch("render.schematic_bridge.render_schematic_data",
                          return_value=(svg, "Saved schematic.svg")) as schematic_render,
                    patch("render.schematic_bridge.rasterize_schematic_svg",
                          return_value=b"test schematic PNG") as raster_render,
                    patch.object(QMessageBox, "critical",
                                 side_effect=AssertionError("Original import failed")),
                    patch.object(QMessageBox, "warning",
                                 side_effect=AssertionError("Unexpected warning dialog")),
                ):
                    window.load_json()

                size_exec.assert_called_once()
                # MOTOEX fixture has four existing on-board placements.
                self.assertEqual(lock_exec.call_count, 4)
                highlighted = [
                    call.kwargs.get("highlight_component_id")
                    for call in render.call_args_list
                    if call.kwargs.get("highlight_component_id") is not None
                ]
                self.assertEqual(len(highlighted), 4)
                # Schematic is rendered exactly once on import, before locks.
                schematic_render.assert_called_once()
                schematic_input = schematic_render.call_args.args[0]
                self.assertEqual(len(schematic_input["components"]), 45)
                self.assertEqual(len(schematic_input["schematicWires"]),
                                 len(__import__("json").loads(source_bytes)["schematicWires"]))
                self.assertEqual(schematic_input["board"]["rows"], 24)
                self.assertEqual(schematic_input["board"]["cols"], 56)
                self.assertTrue(window.schematic_action.isEnabled())
                self.assertEqual(window._schematic_svg, svg)
                self.assertEqual(window._schematic_png, b"test schematic PNG")
                raster_render.assert_called_once_with(svg)
                # The import hard stop is the current status UNTIL a view is selected.
                self.assertIn("STOPPED BEFORE PASS 1", window.statusBar().currentMessage())
                probe.assert_called_once()
                self.assertIs(window.checklist.cuts_choice.currentData(), True)
                self.assertIs(window.checklist.stacking_choice.currentData(), True)
                self.assertEqual(window.checklist.STAGES[-1], ("VERIFY", "Electrical PASS"))
                # Keep the PNG mock active while clicking the Qt action. The
                # fixture bytes intentionally are not a valid PNG payload.
                with patch.object(window.top_view, "show_png") as png_view:
                    window.schematic_action.trigger()
                    png_view.assert_called_once_with(b"test schematic PNG")
                self.assertEqual(window._board_side, "schematic")
                self.assertTrue(window.schematic_action.isChecked())
                self.assertFalse(window.top_action.isChecked())
                window.top_action.trigger()
                self.assertEqual(window._board_side, "top")
                self.assertTrue(window.top_action.isChecked())
                self.assertIn("Component side", window.statusBar().currentMessage())
                self.assertEqual(window.project["board"]["rows"], 24)
                self.assertEqual(window.project["board"]["cols"], 56)
                self.assertFalse(hasattr(window, 'solve_action'))
                self.assertFalse(window.stop_action.isEnabled())
                self.assertIsNone(window._solver_worker)
                self.assertIsNone(window._speed_probe_worker)
                self.assertEqual(project_path.read_bytes(), source_bytes)
                # Legacy Route-Mate persists state/geometry next to the source;
                # it never rewrites the original JSON.
                self.assertTrue(window.presolve_constraints)
            finally:
                window.close()

    def test_board_size_cancel_does_not_start_locks_or_solve(self):
        source_path = (
            Path(__file__).resolve().parents[1] /
            "test-fixtures" / "masters" / "moto" / "motoex.json"
        )
        with tempfile.TemporaryDirectory() as tmp:
            project_path = Path(tmp) / "motoex.json"
            project_path.write_bytes(source_path.read_bytes())
            window = RouteMateWindow()
            try:
                with (
                    patch("gui.main.QFileDialog.getOpenFileName",
                          return_value=(str(project_path), "")),
                    patch.object(BoardSizeDialog, "exec",
                                 return_value=QDialog.DialogCode.Rejected),
                    patch("render.schematic_bridge.render_schematic_data") as schematic_render,
                    patch("render.schematic_bridge.rasterize_schematic_svg") as raster_render,
                    patch.object(LockDialog, "exec") as locks,
                ):
                    window.load_json()
                locks.assert_not_called()
                schematic_render.assert_not_called()
                raster_render.assert_not_called()
                self.assertFalse(window.schematic_action.isEnabled())
                self.assertFalse(hasattr(window, 'solve_action'))
                self.assertIsNone(window._solver_worker)
                self.assertEqual(project_path.read_bytes(), source_path.read_bytes())
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
