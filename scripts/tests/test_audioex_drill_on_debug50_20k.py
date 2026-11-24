"""20k drill forensic experiment invariants; no solves executed."""
import unittest
from scripts import run_audioex_drill_on_debug50_20k as s

class Drill20kDebugTests(unittest.TestCase):
    def test_budget_seeds(self):
        self.assertEqual(s.MOVES, 20000)
        self.assertEqual(s.SEEDS, tuple(range(1,51)))
        self.assertEqual(len(s.SEEDS),50)
        self.assertIn("debug50",str(s.OUT))
    def test_reason_aggregation(self):
        rows=[
          {"strictPass":False,"strictFailures":["KNIFE_2"]},
          {"strictPass":False,"strictFailures":["KNIFE_2"]},
          {"strictPass":False,"unsolvedReason":"NO_PHYSICAL_FINISH"},
          {"strictPass":True},
        ]
        self.assertEqual(s.failure_counts(rows),{"KNIFE_2":2,"NO_PHYSICAL_FINISH":1})
if __name__=="__main__":
    unittest.main()
