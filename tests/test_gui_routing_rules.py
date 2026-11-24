"""Routing popup is optional, explained and defaults to human-friendly knife cuts."""
import os
import unittest
from unittest.mock import patch
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QDialog, QLabel
    from gui.main import RouteMateWindow, RoutingRulesDialog, LockDialog
except ImportError:
    QApplication = None
    QDialog = None


@unittest.skipUnless(QApplication is not None, "PySide6 unavailable")
class RoutingRulesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_default_drilled_off_and_stacking_on(self):
        d = RoutingRulesDialog()
        try:
            self.assertEqual(d.values(), {"drilled_only": False, "stacking_allowed": True})
            self.assertTrue(any("knife cuts" in label.text().lower()
                                for label in d.findChildren(QLabel)))
        finally:
            d.close()

    def test_accepted_rules_summary_before_probe(self):
        w = RouteMateWindow()
        try:
            w.project = {"board": {"rows": 24, "cols": 56}, "components": []}
            with patch.object(RoutingRulesDialog, "exec",
                              return_value=QDialog.DialogCode.Accepted), \
                 patch.object(RoutingRulesDialog, "values",
                              return_value={"drilled_only": False,
                                            "stacking_allowed": False}), \
                 patch.object(w, "_start_speed_probe") as speed:
                w._choose_routing_rules()
            speed.assert_called_once()
            self.assertEqual(w.checklist.cuts_value.text(), "Knife allowed")
            self.assertEqual(w.checklist.stacking_value.text(), "Off")
        finally:
            w.close()

    def test_slide_experimental_bright_red(self):
        d = LockDialog({"id": "F1", "boardPos": {"row": 1, "col": 1},
                        "locked": True}, 1, 1)
        try:
            self.assertIn("EXPERIMENTAL", d.slide.text())
            self.assertIn("#ff1744", d.slide.styleSheet())
            self.assertIn("EXPERIMENTAL", d.search_notice.text())
            self.assertNotIn("Quick Solve", d.search_notice.text())
        finally:
            d.close()

    def test_cancel_rules_does_not_start_probes(self):
        w = RouteMateWindow()
        try:
            w.project = {"board": {"rows": 24, "cols": 56}, "components": []}
            with patch.object(RoutingRulesDialog, "exec",
                              return_value=QDialog.DialogCode.Rejected), \
                 patch.object(w, "_start_speed_probe") as speed:
                w._choose_routing_rules()
            speed.assert_not_called()
            self.assertIsNone(w._probe_cut_drilled_only)
            self.assertEqual(w.checklist.cuts_value.text(), "Not selected")
        finally:
            w.close()


if __name__ == "__main__":
    unittest.main()
