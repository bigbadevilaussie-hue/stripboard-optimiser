"""Optional Qt offscreen GUI startup and hard stop smoke tests."""
import os
import tempfile
import unittest
from pathlib import Path
import json

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from gui.main import RouteMateWindow
except ImportError:
    QApplication = None
    RouteMateWindow = None


@unittest.skipIf(QApplication is None, "PySide6 not installed")
class GuiShellSmoke(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_gui_import_load_stops_before_pass_1(self):
        data = {
            "board": {"rows": 24, "cols": 56, "wires": [], "cuts": []},
            "components": [{"id": "R1", "defId": "r",
                            "boardPos": {"row": 0, "col": 0}}],
            "componentDefs": [{"id": "r", "width": 2, "height": 1,
                               "pins": [{"id": "1", "offsetRow": 0, "offsetCol": 0}]}],
            "nets": [{"id": "N1"}],
            "netAssignments": [{"componentId": "R1", "pinId": "1", "netId": "N1"}],
            "lockedRows": True, "lockedCols": True,
        }
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "input.json"
            payload = json.dumps(data).encode()
            p.write_bytes(payload)
            window = RouteMateWindow()
            result = window.load_project_path(p)
            self.assertEqual(result["status"], "PASS")
            self.assertEqual(result["execution"], "STOPPED_BEFORE_PASS_1")
            self.assertFalse(window.solve_action.isEnabled())
            self.assertFalse(window.stop_action.isEnabled())
            self.assertFalse(window.review_locks_action.isEnabled())
            self.assertIsNone(window._solver_worker)
            self.assertIsNone(window._speed_probe_worker)
            window.solve_board()
            self.assertFalse(window.solve_action.isEnabled())
            self.assertEqual(p.read_bytes(), payload)
            self.assertEqual({x.name for x in Path(tmp).iterdir()}, {"input.json"})
            window.close()


if __name__ == "__main__":
    unittest.main()
