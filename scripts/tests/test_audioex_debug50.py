"""Regression checks for AUDIOEX forensic campaign metadata, no solver needed."""
import unittest
from scripts import run_audioex_debug50 as d

EXPECTED_HIGH_CUT = {722, 1208, 1377, 1384}

class AudioexDebug50Tests(unittest.TestCase):
    def test_exact_seed_portfolio(self):
        self.assertEqual(len(d.SEEDS), 50)
        self.assertEqual(len(set(d.SEEDS)), 50)
        self.assertEqual(tuple(sorted(d.SEEDS)), d.SEEDS)
        self.assertTrue(all(1 <= seed <= 2000 for seed in d.SEEDS))
        self.assertTrue(EXPECTED_HIGH_CUT.issubset(set(d.SEEDS)))

    def test_baseline_configuration(self):
        self.assertEqual(d.MOVES, 50000)
        flags = dict(zip(d.FLAGS[::2], d.FLAGS[1::2]))
        self.assertEqual(flags["--strict"], "1")
        self.assertEqual(flags["--native"], "1")
        self.assertEqual(flags["--drilled"], "0")
        self.assertEqual(flags["--nostack"], "0")
        self.assertEqual(flags["--drill-domain"], "0")
        self.assertEqual(flags["--wire-polish"], "0")
        self.assertEqual(flags["--finish-trace"], "1")
        self.assertEqual(flags["--move-summary"], "1")

    def test_requested_csv_columns(self):
        for key in ("seed","moves","firstFeasibleMove","selectedFinish",
                    "repairCompliant","repairFailures","routerCompliant",
                    "routerFailures","incompleteNets","wireViolations",
                    "rotations","cutsMinusWires","moveRejected",
                    "moveSameBoard","moveAccepted","moveNewBest",
                    "auditFailures","independentCopperOracle"):
            self.assertIn(key,d.FIELDS)

if __name__ == "__main__":
    unittest.main()
