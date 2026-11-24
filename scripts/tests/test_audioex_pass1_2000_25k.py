"""Contract tests for the 25k / 2000-seed Pass 1 qualifier."""
import unittest
from scripts import run_audioex_pass1_2000_25k as run

class AudioexPass1Tests(unittest.TestCase):
    def test_exact_budget_and_seeds(self):
        self.assertEqual(run.MOVES, 25_000)
        self.assertEqual(len(run.SEEDS), 2000)
        self.assertEqual(run.SEEDS, tuple(range(1, 2001)))
    def test_retained_fields_for_strict_recheck(self):
        for name in ("strictPass", "wires", "cuts", "layoutSig", "wireLength",
                     "price", "strictFailures", "auditFailures"):
            self.assertIn(name, run.FIELDS)

if __name__ == "__main__":
    unittest.main()
