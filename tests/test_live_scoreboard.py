"""Pass One live leaderboard and consent-gated winner preview regression tests."""
from __future__ import annotations

import os
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.pass_one import top_five_audited


class TopFiveAuditedTests(unittest.TestCase):
    def test_only_strict_pass_ranked_by_q_then_wires_cuts_seed(self):
        rows = [
            dict(seed="0007", status="FAIL", q="", w="", cut="", time_taken="0.2"),
            dict(seed="0006", status="ERROR", q="", w="", cut="", time_taken="0.2"),
            dict(seed="0011", status="PASS", q="80.00", w="9", cut="20", time_taken="1"),
            dict(seed="0005", status="PASS", q="82.00", w="13", cut="21", time_taken="1"),
            dict(seed="0003", status="PASS", q="82.00", w="13", cut="20", time_taken="1"),
            dict(seed="0002", status="PASS", q="82.00", w="12", cut="25", time_taken="1"),
            dict(seed="0009", status="PASS", q="82.00", w="13", cut="20", time_taken="1"),
            dict(seed="0001", status="PASS", q="79.00", w="8", cut="16", time_taken="1"),
        ]
        leaders = top_five_audited(rows)
        self.assertEqual([x["seed"] for x in leaders], [2, 3, 9, 5, 11])
        self.assertTrue(all(isinstance(x["q"], float) for x in leaders))
        self.assertEqual(top_five_audited(rows[:2]), [])

    def test_incremental_and_resumed_candidates_agree(self):
        rows = [
            dict(seed=f"{i:04d}", status="PASS", q=f"{60+i/10:.2f}",
                 w=str(30-i % 3), cut=str(40+i % 4), time_taken="0.5")
            for i in range(1, 40)
        ]
        leaders = []
        for row in rows:
            leaders = top_five_audited([*leaders, row])
        self.assertEqual(leaders, top_five_audited(rows))


os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication, QMessageBox, QScrollArea
    from gui.main import RouteMateWindow
    from gui.live_scoreboard import LiveScoreboard
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 unavailable")
class LiveScoreboardGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _progress():
        return {
            "done": 125, "total": 200, "qualified": 2, "failed": 123,
            "errors": 0,
            "leaders": [
                dict(seed=50, q=78.24, w=29, cut=44, time_taken=0.7),
                dict(seed=18, q=77.00, w=30, cut=45, time_taken=0.5),
            ],
            "last": {"seed": 125, "valid": False, "seconds": 1.4},
        }

    def test_live_updates_counters_ranking_and_latest_status(self):
        view = LiveScoreboard()
        try:
            view.start("AUDIO", 10000, 200, debug=True)
            view.update_progress(self._progress())
            self.assertIn("AUDIO", view.mode.text())
            self.assertEqual(view.progress.value(), 125)
            self.assertEqual(view.stat_values["done"].text(), "125")
            self.assertEqual(view.stat_values["qualified"].text(), "2")
            self.assertEqual(view.stat_values["errors"].text(), "0")
            self.assertEqual(view.leader_rows[0][0].text(), "0050")
            self.assertEqual(view.leader_rows[0][1].text(), "Q 78.24")
            self.assertEqual(view.leader_rows[0][2].text(), "29W/44C")
            self.assertEqual(view.leader_rows[1][0].text(), "0018")
            self.assertIn("0125 · FAIL", view.recent.text())
            view.finish(completed=True, qualified=2)
            self.assertIn("COMPLETE", view.state.text())
        finally:
            view.close()

    def test_scoreboard_is_own_scrollable_tab_not_clipped_overview(self):
        window = RouteMateWindow()
        try:
            self.assertIsInstance(window.scoreboard_scroll, QScrollArea)
            self.assertIs(window.scoreboard_scroll.widget(), window.scoreboard)
            self.assertEqual(window.sidebar_tabs.indexOf(window.scoreboard_scroll), 2)
            self.assertEqual(window.sidebar_tabs.widget(0).objectName(), "overviewPage")
        finally:
            window.close()

    def test_loading_another_project_clears_stale_scoreboard_values(self):
        window = RouteMateWindow()
        try:
            board = window.scoreboard
            board.start("AUDIO", 10000, 200, debug=True)
            board.update_progress(self._progress())
            self.assertEqual(board.leader_rows[0][0].text(), "0050")
            board.set_winner_available(True)
            board.reset_for_project("MOTO")
            self.assertIn("MOTO", board.mode.text())
            self.assertIn("No Pass One campaign", board.mode.text())
            self.assertEqual(board.leader_rows[0][0].text(), "—")
            self.assertFalse(board.view_winner_button.isEnabled())
            self.assertEqual(board.stat_values["qualified"].text(), "0")
        finally:
            window.close()

    def test_declining_winner_preview_preserves_board_and_keeps_saved_svgs(self):
        valid_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
            '<rect width="20" height="20"/></svg>'
        )
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "winner_seed_0050.json"
            path.write_text(json.dumps({
                "board": {"rows": 24, "cols": 56}, "components": []
            }), encoding="utf-8")
            window = RouteMateWindow()
            try:
                window._top_svg = "original top"
                window._copper_svg = "original copper"

                def fake_render(project):
                    window._copper_svg = valid_svg
                    return valid_svg, "test renderer"

                result = {
                    "winner_json": str(path), "winner_seed": 50, "moves": 10000,
                    "checked": 200, "qualified": 17, "errors": 0,
                    "completed": True, "csv": str(Path(temp) / "results.csv"),
                    "log": str(Path(temp) / "activity.log"),
                }
                with patch.object(window, "_render_component_side",
                                  side_effect=fake_render), \
                     patch.object(window, "_ask_to_view_pass_one_winner",
                                  return_value=False) as ask:
                    window._pass_one_completed(result)
                ask.assert_called_once_with(50)
                self.assertEqual(window._top_svg, "original top")
                self.assertEqual(window._copper_svg, "original copper")
                self.assertIn("preview unchanged", window.board_result_label.text())
                self.assertTrue(window.scoreboard.view_winner_button.isEnabled())
                self.assertTrue(
                    (Path(temp) / "winner_seed_0050-components.svg").is_file()
                )
                self.assertTrue(
                    (Path(temp) / "winner_seed_0050-copper.svg").is_file()
                )
                # The user can open the saved winner later with no re-solve.
                window.scoreboard.view_winner_button.click()
                self.assertEqual(window._top_svg, valid_svg)
                self.assertEqual(window._copper_svg, valid_svg)
                self.assertIn("champion", window.board_result_label.text().lower())
            finally:
                window.close()


    def test_accepting_winner_prompt_displays_saved_svg_immediately(self):
        valid_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
            '<rect width="20" height="20"/></svg>'
        )
        with tempfile.TemporaryDirectory() as temp:
            winner = Path(temp) / "winner_seed_0007.json"
            winner.write_text(json.dumps({
                "board": {"rows": 24, "cols": 56}, "components": []
            }), encoding="utf-8")
            window = RouteMateWindow()
            try:
                window._top_svg = "old board"

                def render(_project):
                    window._copper_svg = valid_svg
                    return valid_svg, "verified renderer"

                result = {
                    "winner_json": str(winner), "winner_seed": 7,
                    "moves": 20000, "checked": 200, "qualified": 1,
                    "errors": 0, "completed": True,
                    "csv": str(Path(temp) / "results.csv"),
                    "log": str(Path(temp) / "activity.log"),
                }
                with patch.object(window, "_render_component_side",
                                  side_effect=render), \
                     patch.object(window, "_ask_to_view_pass_one_winner",
                                  return_value=True) as ask:
                    window._pass_one_completed(result)
                ask.assert_called_once()
                self.assertEqual(window._top_svg, valid_svg)
                self.assertEqual(window._copper_svg, valid_svg)
                self.assertTrue(window.scoreboard.view_winner_button.isEnabled())
            finally:
                window.close()


if __name__ == "__main__":
    unittest.main()
