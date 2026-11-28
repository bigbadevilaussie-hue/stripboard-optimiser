"""Strict budget probe: actual JSON, sample selection, history and safety."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from gui import budget_probe as bp
from gui import native_calibration as nc

PROJECT = {"board": {"rows": 24, "cols": 56}, "components": []}

def stats(moves, count, total=100):
    return bp.summary(moves, [
        {"status": "PASS" if k < count else "FAIL", "q": 60, "time_taken": 1.2}
        for k in range(total)], "probe", 3)

class BudgetProbeTests(unittest.TestCase):
    def test_threshold_and_inconclusive_cases(self):
        self.assertEqual(bp.choose(stats(10000, 5))[0], 10000)
        self.assertEqual(bp.choose(stats(10000, 1), stats(20000, 3))[0], 20000)
        self.assertEqual(bp.choose(stats(10000, 4), stats(20000, 2))[0], 10000)
        chosen, reason = bp.choose(stats(10000, 0), stats(20000, 0))
        self.assertEqual(chosen, 20000)
        self.assertIn("not a proven recommendation", reason)

    def test_actual_probe_uses_same_seed_subset_and_strict_results(self):
        calls = []
        def seed(project, moves, seed, drilled, stacking, cancelled):
            self.assertTrue(project["board"]["lockedRows"])
            self.assertTrue(project["board"]["lockedCols"])
            self.assertTrue(drilled)
            self.assertFalse(stacking)
            calls.append((moves, seed))
            valid = seed in (10, 30, 50) if moves == 20000 else seed == 10
            return {"seed": seed, "valid": valid, "seconds": 1.0, "q": 65}
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(bp, "prerequisites"), patch.object(bp, "_run_seed", side_effect=seed):
            workspace = Path(tmp)
            keeper = workspace / "pass 1"
            keeper.mkdir()
            (keeper / "keep").write_text("untouched")
            report = bp.probe_budget(PROJECT, 3, True, False, lambda _: None,
                                     lambda _: None, lambda: False, workspace=workspace)
            self.assertEqual(report["recommended_moves"], 20000)
            self.assertEqual(report["ten"]["qualified"], 1)
            self.assertEqual(report["twenty"]["qualified"], 3)
            self.assertEqual(len(calls), 200)
            for moves in (10000, 20000):
                self.assertEqual(sorted(s for m,s in calls if m == moves), list(bp.SAMPLE_SEEDS))
            self.assertTrue((workspace / "logs" / "budget_probe.json").is_file())
            self.assertEqual((keeper / "keep").read_text(), "untouched")
            self.assertNotIn("lockedRows", PROJECT["board"])

    def test_matching_full_history_wins_without_sampling(self):
        with patch.object(bp, "prerequisites"), \
             patch.object(bp, "_history", side_effect=[stats(10000, 252, 2000), None]), \
             patch.object(bp, "_sample") as sample:
            report = bp.probe_budget(PROJECT, 3, False, True, lambda _: None,
                                     lambda _: None, lambda: False)
            self.assertEqual(report["recommended_moves"], 10000)
            sample.assert_not_called()

    def test_good_10k_sample_skips_20k(self):
        with patch.object(bp, "prerequisites"), \
             patch.object(bp, "_sample", return_value=(stats(10000, 9), [])) as sample:
            report = bp.probe_budget(PROJECT, 3, False, True, lambda _: None,
                                     lambda _: None, lambda: False)
            self.assertEqual(report["recommended_moves"], 10000)
            sample.assert_called_once()

    def test_decoder_selection(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(nc, "NATIVE", Path(tmp)):
            locked = {"components": [{"locked": True, "edge": True, "boardPos": {"row": 13, "col": 47}}]}
            self.assertEqual(nc.decoder_directory(PROJECT), Path(tmp))
            self.assertEqual(nc.decoder_directory(locked), Path(tmp))
            edge = Path(tmp) / "edge"
            edge.mkdir()
            (edge / "libv5decode.so").touch()
            self.assertEqual(nc.decoder_directory(locked), Path(tmp))
            locked["components"][0]["locked"] = False
            self.assertEqual(nc.decoder_directory(locked), Path(tmp))

    def test_native_failure_is_not_a_zero_survivor(self):
        with patch.object(bp, "prerequisites"), \
             patch.object(bp, "_run_seed", side_effect=RuntimeError("native error")):
            with self.assertRaisesRegex(RuntimeError, "native error"):
                bp.probe_budget(PROJECT, 3, False, True, lambda _: None,
                                lambda _: None, lambda: False)
