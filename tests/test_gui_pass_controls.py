"""Pass launch confirmations, pass-specific cleanup and cold-start Pass Two."""
import csv
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QDialog, QDialogButtonBox, QLabel
    from gui.main import (
        RouteMateWindow, PassOneDialog, PassOneExistingDialog, PassTwoDialog,
        PassOneWorker, RoutingRulesDialog, WorkflowChecklist,
    )
except ImportError:
    QApplication = None


@unittest.skipUnless(QApplication is not None, "PySide6 unavailable")
class PassControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_successful_calibration_prompts_once_after_worker_finishes(self):
        window = RouteMateWindow()
        try:
            window.project = {"board": {"rows": 24, "cols": 56}}
            window._probe_cut_drilled_only = False
            window._probe_stacking_allowed = True
            window._recommended_workers = 3
            window._calibration_worker = object()
            result = {"ms_per_decode": 0.17, "decodes_per_second": 5882.0}
            with patch("gui.main.QTimer.singleShot") as queue, \
                 patch.object(window, "start_pass_one") as launch:
                window._calibration_completed(result)
                self.assertTrue(window._pass_one_prompt_pending)
                queue.assert_not_called()  # Worker must exit before any popup.
                window._calibration_finished()
                queue.assert_called_once_with(0, launch)
                self.assertFalse(window._pass_one_prompt_pending)
                self.assertIsNone(window._calibration_worker)
                self.assertEqual(window._calibration_stages["CALIBRATION"], "done")
                window._calibration_finished()
                queue.assert_called_once()  # No duplicate popup.
        finally:
            window.close()

    def test_failed_cancelled_or_closing_calibration_never_prompts(self):
        window = RouteMateWindow()
        try:
            window.project = {"board": {"rows": 24, "cols": 56}}
            with patch("gui.main.QTimer.singleShot") as queue:
                window._pass_one_prompt_pending = True
                window._calibration_failed("probe failed")
                window._calibration_finished()
                queue.assert_not_called()
                window._pass_one_prompt_pending = True
                window._calibration_cancelled()
                window._calibration_finished()
                queue.assert_not_called()
                window._calibration_stages["CALIBRATION"] = "done"
                window._pass_one_prompt_pending = True
                window._close_when_idle = True
                with patch.object(window, "close") as close:
                    window._calibration_finished()
                    close.assert_called_once()
                queue.assert_not_called()
        finally:
            window._close_when_idle = False
            window.close()

    def test_routing_rules_popup_needs_explicit_confirmation(self):
        dialog = RoutingRulesDialog()
        try:
            go = dialog.findChild(QDialogButtonBox).button(
                QDialogButtonBox.StandardButton.Ok)
            self.assertFalse(go.isEnabled())
            self.assertEqual(dialog.values(), {
                "drilled_only": False, "stacking_allowed": True})
            dialog.cut_drilled.setChecked(True)
            dialog.stack_no.setChecked(True)
            self.assertEqual(dialog.values(), {
                "drilled_only": True, "stacking_allowed": False})
            self.assertFalse(go.isEnabled())
            dialog.confirm.setChecked(True)
            self.assertTrue(go.isEnabled())
            dialog.confirm.setChecked(False)
            self.assertFalse(go.isEnabled())
        finally:
            dialog.close()

    def test_pass_one_launch_displays_confirmed_routing_policy(self):
        dialog = PassOneDialog(
            {"ms_per_decode": 3.0},
            drilled_only=True, stacking_allowed=False)
        try:
            text = "\n".join(label.text()
                             for label in dialog.findChildren(QLabel))
            self.assertIn("Cuts: Drilled only", text)
            self.assertIn("Wire stacking: Off", text)
        finally:
            dialog.close()

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

    def test_overwrite_requires_distinct_checkbox_and_explicit_action(self):
        d = PassOneExistingDialog(
            "moto.json", 10000, [Path("results.csv")], resume_error="no manifest"
        )
        try:
            self.assertFalse(d.restart_button.isEnabled())
            self.assertFalse(d.resume_button.isEnabled())
            d.confirm.setChecked(True)
            self.assertTrue(d.restart_button.isEnabled())
            self.assertIsNone(d.action)
            d._choose("restart")
            self.assertEqual(d.action, "restart")
        finally:
            d.close()

    def test_sidebar_preparation_progress_not_diluted_by_passes(self):
        panel = WorkflowChecklist()
        try:
            panel.update_states(
                {key: "done" for key in panel.PREPARATION_STAGES}
            )
            self.assertEqual(panel.percent.text(), "100%")
            self.assertEqual(panel.bar.value(), len(panel.PREPARATION_STAGES))
            panel.update_states({})
            self.assertEqual(panel.percent.text(), "0%")
        finally:
            panel.close()

    def test_champion_svg_files_and_preview(self):
        import json
        with tempfile.TemporaryDirectory() as td:
            champion_file = Path(td) / "winner_seed_0017.json"
            champion_file.write_text(json.dumps({
                "board": {"rows": 24, "cols": 56}, "components": []
            }))
            valid_svg = ('<svg xmlns="http://www.w3.org/2000/svg" '
                         'width="20" height="20"><rect width="20" height="20"/></svg>')
            w = RouteMateWindow()
            try:
                w._copper_svg = valid_svg
                with patch.object(w, "_render_component_side",
                                  return_value=(valid_svg, "verified renderer")):
                    w._display_pass_one_champion({
                        "winner_json": str(champion_file),
                        "winner_seed": 17, "moves": 10000,
                    })
                self.assertTrue((Path(td) / "winner_seed_0017-components.svg").is_file())
                self.assertTrue((Path(td) / "winner_seed_0017-copper.svg").is_file())
                self.assertIn("champion", w.solve_summary.text().lower())
            finally:
                w.close()

    def test_pass_one_explicit_go_only_clears_pass_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Work"
            from gui.work_directory import project_workspace
            source = Path(td) / "audio.json"
            source.write_text('{"board": {"rows":24,"cols":56}}')
            workspace = project_workspace(source, root, create=True)
            (workspace / "pass 1" / "old.csv").write_text("legacy preserved")
            (workspace / "pass 1" / "10k").mkdir()
            (workspace / "pass 1" / "10k" / "old.csv").write_text("old 10k")
            (workspace / "pass 1" / "20k").mkdir()
            (workspace / "pass 1" / "20k" / "keep.csv").write_text("preserve 20k")
            (workspace / "pass 2" / "keep.csv").write_text("preserve")
            (workspace / "jsons" / "10k").mkdir()
            (workspace / "jsons" / "10k" / "old.svg").write_text("old champion")
            (workspace / "jsons" / "20k").mkdir()
            (workspace / "jsons" / "20k" / "keep.svg").write_text("preserve champion")
            (workspace / "jsons" / "keep.json").write_text("preserve")
            window = RouteMateWindow()
            try:
                window.work_root = root
                window.project = {"board": {"rows":24,"cols":56}}
                window.project_path = source
                window.active_workspace = workspace
                window._calibration_stages["CALIBRATION"] = "done"
                window._probe_cut_drilled_only = False
                window._probe_stacking_allowed = True
                window._recommended_workers = 3
                with patch.object(PassOneDialog, "exec",
                                  return_value=QDialog.DialogCode.Accepted), \
                     patch.object(PassOneDialog, "moves", return_value=10000), \
                     patch("gui.native_calibration.prerequisites"), \
                     patch("gui.pass_one.AUDITOR", Path(__file__)), \
                     patch("gui.main.PassOneExistingDialog") as confirm_existing, \
                     patch.object(PassOneWorker, "start") as starter:
                    confirm_existing.return_value.exec.return_value = QDialog.DialogCode.Accepted
                    confirm_existing.return_value.action = "restart"
                    window.start_pass_one()
                    starter.assert_called_once()
                    confirm_existing.assert_called_once()
                self.assertTrue((workspace / "pass 1" / "old.csv").exists())
                self.assertFalse((workspace / "pass 1" / "10k" / "old.csv").exists())
                self.assertTrue((workspace / "pass 1" / "20k" / "keep.csv").exists())
                self.assertTrue((workspace / "pass 2" / "keep.csv").exists())
                self.assertFalse((workspace / "jsons" / "10k" / "old.svg").exists())
                self.assertTrue((workspace / "jsons" / "20k" / "keep.svg").exists())
                self.assertTrue((workspace / "jsons" / "keep.json").exists())
            finally:
                window._solve_clock.stop()
                window._pass_one_worker = None
                window.close()

    def test_pass_two_from_cold_gui_without_project(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Work"
            from gui.work_directory import project_workspace, CSV_FIELDS
            source_file = Path(td) / "audio.json"
            source_file.write_text("{}")
            workspace = project_workspace(source_file, root, create=True)
            with (workspace / "pass 1" / "results.csv").open(
                    "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerow({"seed":"0002","cut":44,"w":29,
                                 "q":"78.24","time_taken":"3.200"})
            (workspace / "pass 2" / "old.txt").write_text("old")
            window = RouteMateWindow()
            try:
                window.work_root = root
                self.assertIsNone(window.project)
                with patch.object(PassTwoDialog, "exec",
                                  return_value=QDialog.DialogCode.Accepted):
                    window.start_pass_two()
                self.assertTrue((workspace / "pass 1" / "results.csv").exists())
                self.assertFalse((workspace / "pass 2" / "old.txt").exists())
                self.assertTrue((workspace / "pass 2" / "candidates.csv").exists())
                self.assertIn("search not started", window.solve_activity.text())
                self.assertNotEqual(
                    window._calibration_stages.get("PASS2"), "done")
            finally:
                window.close()


    def test_cold_pass_two_selects_exact_project_when_multiple_exist(self):
        with tempfile.TemporaryDirectory() as td:
            from gui.work_directory import project_workspace, CSV_FIELDS
            root = Path(td) / "Work"
            for name, seed in (("audio.json", "1171"), ("moto.json", "0009")):
                source = Path(td) / name
                source.write_text("{}")
                ws = project_workspace(source, root, create=True)
                with (ws / "pass 1" / "results.csv").open(
                    "w", newline="", encoding="utf-8"
                ) as file:
                    writer = csv.DictWriter(file, fieldnames=CSV_FIELDS)
                    writer.writeheader()
                    writer.writerow({"seed": seed, "cut": 39, "w": 11,
                                     "q": "74.14", "time_taken": "1.030"})
            audio_ws = project_workspace(Path(td) / "audio.json", root)
            moto_ws = project_workspace(Path(td) / "moto.json", root)
            window = RouteMateWindow()
            try:
                window.work_root = root
                with patch("gui.main.QInputDialog.getItem",
                           return_value=(f"moto.json  ·  {moto_ws.name}", True)) as select, \
                     patch.object(PassTwoDialog, "exec",
                                  return_value=QDialog.DialogCode.Accepted):
                    window.start_pass_two()
                select.assert_called_once()
                self.assertTrue((moto_ws / "pass 2" / "candidates.csv").is_file())
                self.assertFalse((audio_ws / "pass 2" / "candidates.csv").exists())
                self.assertEqual(
                    (moto_ws / "pass 2" / "candidates.csv").read_text().count("0009"), 1
                )
                self.assertEqual(
                    (audio_ws / "pass 1" / "results.csv").read_text().count("1171"), 1
                )
            finally:
                window.close()


    def test_live_pass_one_eta_uses_all_completed_seeds(self):
        from time import perf_counter
        w = RouteMateWindow()
        try:
            # Simulate the screenshot's actual counts, without a solver run.
            w._pass_one_worker = object()
            w._solve_budget = 2000
            w._solve_done = 1259
            w._solve_started = perf_counter() - 516.0
            w._update_solve_clock()
            display = w.solve_eta.text()
            self.assertIn("1,259/2,000 seeds", display)
            self.assertIn("ETA: ~5m 04s", display)
            self.assertNotIn("remaining unknown", display)

            w._solve_done = 0
            w._update_solve_clock()
            self.assertIn("measuring first completed seed", w.solve_eta.text())

            w._solve_done = 2000
            w._update_solve_clock()
            self.assertIn("ETA: ~0m 00s", w.solve_eta.text())
        finally:
            w._pass_one_worker = None
            w.close()


    def test_cancel_pass_one_keeps_old_results(self):
        with tempfile.TemporaryDirectory() as td:
            from gui.work_directory import project_workspace
            root = Path(td) / "Work"
            source = Path(td) / "audio.json"
            source.write_text("{}")
            workspace = project_workspace(source, root, create=True)
            previous = workspace / "pass 1" / "results.csv"
            previous.write_text("DO NOT ERASE")
            w = RouteMateWindow()
            try:
                w.work_root = root
                w.project = {"board": {"rows": 24, "cols": 56}}
                w.project_path = source
                w.active_workspace = workspace
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
            from gui.work_directory import project_workspace, CSV_FIELDS
            root = Path(td) / "Work"
            source = Path(td) / "moto.json"
            source.write_text("{}")
            workspace = project_workspace(source, root, create=True)
            with (workspace / "pass 1" / "results.csv").open(
                    "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerow({"seed": "0010", "cut": 4, "w": 3,
                                 "q": "91.20", "time_taken": "1.100"})
            previous = workspace / "pass 2" / "keep.txt"
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
