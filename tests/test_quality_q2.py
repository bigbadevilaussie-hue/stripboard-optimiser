"""Q2 scoring regressions and physical stack semantics."""
import unittest
from unittest.mock import patch
from gui.quality import construction_metrics, max_stack_depth, cpu_allocation, QUALITY_VERSION

def wire(lo, hi, col=0):
    return {"from": {"row": lo, "col": col}, "to": {"row": hi, "col": col}}

class Q2Tests(unittest.TestCase):
    def test_endpoint_touch_does_not_stack(self):
        self.assertEqual(max_stack_depth([wire(1, 5), wire(5, 9)]), 1)
        self.assertEqual(max_stack_depth([wire(1, 5), wire(5, 9), wire(1, 9)]), 2)
        self.assertEqual(max_stack_depth([wire(1, 9), wire(3, 7), wire(4, 6)]), 3)
        self.assertEqual(max_stack_depth([]), 0)
        self.assertEqual(max_stack_depth([wire(1, 9), wire(1, 9, 1)]), 1)

    def test_quadratic_and_length(self):
        board = {"wires": [wire(1, 5)] * 3, "cuts": []}
        m = construction_metrics({"board": board}, quality_version="Q2")
        self.assertEqual(m["s"], 3)
        self.assertEqual(m["wire_length_mm"], 30.48)
        self.assertEqual(m["q"], 93.59)
        self.assertEqual(construction_metrics({"board": {"wires": [], "cuts": []}})["q"], 100)

    def test_q3_default_and_scaled_penalties(self):
        self.assertEqual(QUALITY_VERSION, "Q3")
        board = {"wires": [wire(1, 5)] * 3, "cuts": []}
        m = construction_metrics({"board": board})
        self.assertEqual(m["s"], 3)
        self.assertEqual(m["wire_length_mm"], 30.48)
        self.assertEqual(m["q"], 97.44)
        self.assertEqual(construction_metrics({"board": {"wires": [], "cuts": []}})["q"], 100)
        # A nonvertical jumper and unplaced component both retain their penalties.
        bad = {"board": {"wires": [{"from": {"row": 0, "col": 0},
                                     "to": {"row": 0, "col": 1}}], "cuts": []},
               "components": [{"id": "U1"}, {"id": "OFF", "offBoard": True}]}
        self.assertEqual(construction_metrics(bad)["q"], 89.74)
        with self.assertRaises(ValueError):
            construction_metrics(bad, quality_version="unknown")

    def test_q3_scales_unclamped_penalty_not_rounded_q2(self):
        bad = {"board": {"wires": [], "cuts": []},
               "components": [{"id": str(i)} for i in range(10)]}
        self.assertEqual(construction_metrics(bad, quality_version="Q2")["q"], 0)
        self.assertEqual(construction_metrics(bad)["q"], 40)

    def test_cpu_allocation(self):
        import os
        name = "process_cpu_count" if hasattr(os, "process_cpu_count") else "cpu_count"
        for cpus, workers in [(1, 1), (2, 1), (4, 3), (8, 7), (None, 1)]:
            with patch("gui.quality.os." + name, return_value=cpus):
                self.assertEqual(cpu_allocation(), (cpus or 1, workers))

if __name__ == "__main__":
    unittest.main()
