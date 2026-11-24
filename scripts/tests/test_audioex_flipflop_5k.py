"""Tests for fresh 5k paired drill benchmark settings and quality calculation."""
import unittest
from scripts import run_audioex_flipflop_5k as f

class FlipFlop5kTests(unittest.TestCase):
    def test_settings(self):
        self.assertEqual(f.MOVES, 5000)
        self.assertEqual(len(f.SEEDS), 2000)
        self.assertEqual(f.MODES, (True,False))
        self.assertEqual(f.mode_name(True), "drill_on")
        self.assertEqual(f.mode_name(False), "drill_off")
        self.assertIn("5k", str(f.OUT))
    def test_score(self):
        board={"components":[{"boardPos":{"row":1,"col":1}}],
               "board":{"cuts":[{"row":1,"col":1}],
               "wires":[{"from":{"row":0,"col":1},"to":{"row":10,"col":1}}]}}
        score,length,pen=f.score_quality(board)
        self.assertEqual(length,25.4)
        self.assertEqual(score,98.49)
        self.assertEqual(pen["penaltyInvalid"],0.0)
if __name__=="__main__":
    unittest.main()
