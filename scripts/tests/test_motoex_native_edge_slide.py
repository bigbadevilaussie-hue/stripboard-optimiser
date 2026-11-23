"""Pure fixture tests for the native MOTOEX Edge+Slide controller.

These do not claim the native solver passed; a real run must do that.
"""
import copy
import json
import unittest

import run_motoex_native_edge_slide as edge
import test_motoex_usb_lock as contract


class EdgeSlideTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = contract.MASTER.read_bytes()
        cls.project = json.loads(cls.raw)
        cls.usb, cls.definition, cls.overhang = contract.usb_source(cls.project)

    def test_boolean_options(self):
        for s in ("yes", "true", "1", "on"):
            self.assertTrue(edge.bool_option(s))
        for s in ("no", "false", "0", "off"):
            self.assertFalse(edge.bool_option(s))
        with self.assertRaises(Exception):
            edge.bool_option("maybe")

    def test_51_legal_columns_nearest_first_and_full_coverage(self):
        positions = edge.slide_positions(self.usb, self.definition, 24, 56, True)
        self.assertEqual(len(positions), 51)
        self.assertEqual(set(positions), set(range(51)))
        self.assertEqual(positions[:8], [47, 46, 48, 45, 49, 44, 50, 43])
        self.assertEqual(positions[-1], 0)
        self.assertEqual(edge.slide_positions(self.usb, self.definition, 24, 56, False), [47])

    def test_edge_fixed_preserves_usb_and_clears_others(self):
        before = copy.deepcopy(self.project)
        trial = edge.prepare_trial(self.project, True, False, 47)
        usb = next(c for c in trial["components"] if c["label"] == "USB")
        self.assertEqual((trial["board"]["rows"], trial["board"]["cols"]), (24, 56))
        self.assertEqual((trial["board"]["lockedRows"], trial["board"]["lockedCols"]), (True, True))
        self.assertEqual(usb["boardPos"], {"row": 13, "col": 47})
        self.assertTrue(usb["locked"])
        self.assertTrue(usb["edge"])
        self.assertFalse(usb["slide"])
        self.assertEqual(trial["nets"], self.project["nets"])
        self.assertEqual(trial["netAssignments"], self.project["netAssignments"])
        self.assertEqual(trial["componentDefs"], self.project["componentDefs"])
        self.assertTrue(all(c.get("boardPos") is None for c in trial["components"]
                            if c["id"] != usb["id"]))
        self.assertEqual(self.project, before)
        self.assertEqual(contract.MASTER.read_bytes(), self.raw)

    def test_slider_keeps_same_row_and_rotation_across_all_51(self):
        for col in edge.slide_positions(self.usb, self.definition, 24, 56, True):
            trial = edge.prepare_trial(self.project, True, True, col)
            usb = next(c for c in trial["components"] if c["label"] == "USB")
            self.assertEqual(usb["boardPos"], {"row": 13, "col": col})
            self.assertEqual(usb["rotation"], 0)
            self.assertTrue(usb["edge"] and usb["slide"] and usb["locked"])
            self.assertEqual(len([c for c in trial["components"] if c.get("locked")]), 1)

    def test_slide_without_edge_rejected(self):
        with self.assertRaises(ValueError):
            edge.prepare_trial(self.project, False, True, 47)
        with self.assertRaises(ValueError):
            edge.prepare_trial(self.project, True, True, 51)
        with self.assertRaises(ValueError):
            edge.prepare_trial(self.project, True, True, -1)

    def test_validator_never_exempts_physical_constraints(self):
        trial = edge.prepare_trial(self.project, True, True, 40)
        result = {"strictValid": True, "rows": 24, "cols": 56}
        self.assertEqual(edge.check_trial(self.project, trial, trial, result, 0), [])
        bad = copy.deepcopy(trial)
        bad["board"]["rows"] = 26
        self.assertIn("BOARD_NOT_24x56", " ".join(edge.check_trial(self.project, trial, bad, result, 0)))
        bad = copy.deepcopy(trial)
        bad["board"]["cuts"] = [{"row": 25, "col": 8, "kind": "hole"}]
        self.assertIn("OUTSIDE_CUT", edge.check_trial(self.project, trial, bad, result, 0))
        bad = copy.deepcopy(trial)
        bad["board"]["wires"] = [{"from": {"row": 23, "col": 2},
                                  "to": {"row": 24, "col": 2}}]
        self.assertIn("OUTSIDE_WIRE", edge.check_trial(self.project, trial, bad, result, 0))
        bad = copy.deepcopy(trial)
        usb = next(c for c in bad["components"] if c["label"] == "USB")
        usb["boardPos"]["col"] = 41
        self.assertIn("USB_MOVED", " ".join(edge.check_trial(self.project, trial, bad, result, 0)))
        bad = copy.deepcopy(trial)
        usb = next(c for c in bad["components"] if c["label"] == "USB")
        usb["slide"] = False
        self.assertIn("EDGE_SLIDE_FLAGS_CHANGED", edge.check_trial(self.project, trial, bad, result, 0))
        self.assertIn("STRICT_EXIT_2", edge.check_trial(self.project, trial, trial, result, 2))


if __name__ == "__main__":
    unittest.main()
