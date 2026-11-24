"""Pass launch confirmations, pass-specific cleanup and cold-start Pass Two."""
import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox
    from gui.main import (
        RouteMateWindow, PassOneDialog, PassTwoDialog, PassOneWorker,
    )
except ImportError:
    QApplication = None


@unittest.skipUnless(QApplication is not None, "PySide6 unavailable")
class PassControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_pass_one_radio_checkbox_and_go(self):
        dialog = PassOneDialog({"ms_per_decode": 3.0})
        try:
            go = dialog.findChild(QDialogButtonBox).button(
                QDialogButtonBox.StandardButton.Ok)
            self.assertFalse(go.isEnabled())
            self.assertIn(dialog.moves(), (10000, 20000))
            dialog.twenty_k.setChecked(True)
            self.assertEqual(dialog.moves(), 20000)
            dialog.confirm.setChecked(True)
            self.assertTrue(go.isEnabled())
        finally:
            dialog.close()

    def test_pass_one_explicit_go_only_clears_pass_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Work"
            from gui.work_directory import ensure_work
            ensure_work(root)
            (root / "pass 1" / "old.csv").write_text("old")
            (root / "pass 2" / "keep.csv").write_text("preserve")
            (root / "jsons" / "keep.json").write_text("preserve")
            window = RouteMateWindow()
            try:
                window.work_root = root
                window.project = {"board": {"rows":24,"cols":56}}
                window._calibration_stages["CALIBRATION"] = "done"
                window._probe_cut_drilled_only = False
                window._probe_stacking_allowed = True
                window._recommended_workers = 3
                with patch.object(PassOneDialog, "exec",
                                  return_value=QDialog.DialogCode.Accepted), \
                     patch.object(PassOneDialog, "moves", return_value=10000), \
                     patch("gui.native_calibration.prerequisites"), \
                     patch("gui.pass_one.AUDITOR", Path(__file__)), \
                     patch.object(PassOneWorker, "start") as starter:
                    window.start_pass_one()
                    starter.assert_called_once()
                self.assertFalse((root / "pass 1" / "old.csv").exists())
                self.assertTrue((root / "pass 2" / "keep.csv").exists())
                self.assertTrue((root / "jsons" / "keep.json").exists())
            finally:
                window._solve_clock.stop()
                window._pass_one_worker = None
                window.close()

    def test_pass_two_from_cold_gui_without_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Work"
            from gui.work_directory import ensure_work, CSV_FIELDS
            ensure_work(root)
            with (root / "pass 1" / "results.csv").open(
                    "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerow({"seed":"0002","cut":44,"w":29,
                                 "q":"78.24","time_taken":"3.200"})
            (root / "pass 2" / "old.txt").write_text("old")
            window = RouteMateWindow()
            try:
                window.work_root = root
                self.assertIsNone(window.project)
                with patch.object(PassTwoDialog, "exec",
                                  return_value=QDialog.DialogCode.Accepted):
                    window.start_pass_two()
                self.assertTrue((root / "pass 1" / "results.csv").exists())
                self.assertFalse((root / "pass 2" / "old.txt").exists())
                self.assertTrue((root / "pass 2" / "candidates.csv").exists())
                self.assertIn("search not started", window.solve_activity.text())
                self.assertNotEqual(
                    window._calibration_stages.get("PASS2"), "done")
            finally:
                window.close()


    def test_cancel_pass_one_keeps_old_results(self):
        with tempfile.TemporaryDirectory() as td:
            from gui.work_directory import ensure_work
            root = ensure_work(Path(td) / "Work")
            previous = root / "pass 1" / "results.csv"
            previous.write_text("DO NOT ERASE")
            w = RouteMateWindow()
            try:
                w.work_root = root
                w.project = {"board": {"rows": 24, "cols": 56}}
                w._calibration_stages["CALIBRATION"] = "done"
                w._probe_cut_drilled_only = False
                w._probe_stacking_allowed = True
                w._recommended_workers = 3
                with patch.object(PassOneDialog, "exec",
                                  return_value=QDialog.DialogCode.Rejected):
                    w.start_pass_one()
                self.assertEqual(previous.read_text(), "DO NOT ERASE")
            finally:
                w.close()

    def test_cancel_pass_two_keeps_old_results(self):
        with tempfile.TemporaryDirectory() as td:
            from gui.work_directory import ensure_work, CSV_FIELDS
            root = ensure_work(Path(td) / "Work")
            with (root / "pass 1" / "results.csv").open(
                    "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerow({"seed": "0010", "cut": 4, "w": 3,
                                 "q": "91.20", "time_taken": "1.100"})
            previous = root / "pass 2" / "keep.txt"
            previous.write_text("PRESERVE")
            w = RouteMateWindow()
            try:
                w.work_root = root
                with patch.object(PassTwoDialog, "exec",
                                  return_value=QDialog.DialogCode.Rejected):
                    w.start_pass_two()
                self.assertEqual(previous.read_text(), "PRESERVE")
            finally:
                w.close()



if __name__ == "__main__":
    unittest.main()
