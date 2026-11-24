"""Contract tests for AUDIOEX 10k drill ON/OFF paired sweep."""
import unittest
from scripts import run_audioex_flipflop_10k as runner

class TestFlipFlop(unittest.TestCase):
    def test_pair_count_and_order(self):
        self.assertEqual(runner.MOVES, 10_000)
        self.assertEqual(len(runner.SEEDS), 2000)
        self.assertEqual(list(runner.MODES), [True, False])
        self.assertEqual(runner.mode_name(True), "drill_on")
        self.assertEqual(runner.mode_name(False), "drill_off")

    def test_historical_quality_formula(self):
        board={"components":[{"boardPos":{"row":0,"col":0}}],
               "board":{"cuts":[{} for _ in range(2)],
                        "wires":[{"from":{"row":0,"col":0},
                                  "to":{"row":10,"col":0}}]}}
        score,mm,p=runner.score_quality(board)
        self.assertEqual(mm,25.4)
        self.assertEqual(p["penaltyWires"],0.6)
        self.assertEqual(p["penaltyCuts"],0.8)
        self.assertEqual(p["penaltyWireLength"],0.508)
        self.assertEqual(p["penaltyDiagonals"],0)
        self.assertEqual(score,98.09)

    def test_quality_order(self):
        a={"quality100":72,"wires":20,"cuts":50,"wireLengthMm":100,
           "seed":1,"drillOn":False}
        b={"quality100":73,"wires":21,"cuts":51,"wireLengthMm":90,
           "seed":2,"drillOn":True}
        self.assertLess(runner.key(b),runner.key(a))

if __name__=="__main__":
    unittest.main()
