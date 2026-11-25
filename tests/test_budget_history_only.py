"""History lookup must never start a qualification search."""
import unittest
from unittest.mock import patch
from gui.budget_probe import history_budget


class HistoryOnlyTests(unittest.TestCase):
    def test_missing_history_defaults_without_solving(self):
        with patch("gui.budget_probe._prepared_input", return_value=({}, "test")), \
             patch("gui.budget_probe._history", return_value=None), \
             patch("gui.budget_probe._sample") as sample, \
             patch("gui.budget_probe._run_seed") as seed:
            result = history_budget({}, 3, False, True)
            self.assertEqual(result["recommended_moves"], 10000)
            sample.assert_not_called()
            seed.assert_not_called()
