"""Generic native edge slide retry controller: pure contract tests."""
import copy
import unittest

from native_edge_slide_positions import edge_slide_anchors
from run_native_edge_slide import prepare_variation, verify_candidate


def project():
    return {
        "board": {"rows": 24, "cols": 56, "lockedRows": True,
                  "lockedCols": True, "cuts": [], "wires": []},
        "components": [
            {"id": "usb", "label": "USB", "defId": "wide",
             "boardPos": {"row": 13, "col": 47},
             "rotation": 0, "locked": True, "edge": True, "slide": True},
            {"id": "fixed", "label": "P", "defId": "pin",
             "boardPos": {"row": 3, "col": 3},
             "rotation": 90, "locked": True},
        ],
        "componentDefs": [
            {"id": "wide", "width": 6, "height": 13,
             "pins": [{"id": "1", "offsetRow": 0, "offsetCol": 0},
                      {"id": "2", "offsetRow": 0, "offsetCol": 5}],
             "bodyCells": [{"row": r, "col": c} for r in range(13) for c in range(6)]},
            {"id": "pin", "width": 1, "height": 1,
             "pins": [{"id": "1", "offsetRow": 0, "offsetCol": 0}],
             "bodyCells": []},
        ],
        "nets": [], "netAssignments": [],
    }


class GenericNativeEdgeControllerTests(unittest.TestCase):
    def test_slide_changes_only_one_component_and_preserves_other_locks(self):
        p = project()
        before = copy.deepcopy(p)
        anchors = edge_slide_anchors(p)
        self.assertEqual(len(anchors[0].positions), 51)
        variant = prepare_variation(p, ["usb"], [(13, 40)])
        self.assertEqual(variant["components"][0]["boardPos"], {"row": 13, "col": 40})
        self.assertEqual(variant["components"][1], p["components"][1])
        self.assertEqual(p, before)

    def test_full_strict_required_and_no_copper_outside(self):
        p = project()
        v = prepare_variation(p, ["usb"], [(13, 40)])
        result = {"rows": 24, "cols": 56, "strictValid": True}
        self.assertEqual(verify_candidate(p, v, v, result, 0), [])
        self.assertIn("NOT_STRICT_VALID", verify_candidate(p, v, v, result, 2))
        bad = copy.deepcopy(v)
        bad["board"]["rows"] = 26
        self.assertIn("BOARD_DIMENSIONS_CHANGED", verify_candidate(p, v, bad, result, 0))
        bad = copy.deepcopy(v)
        bad["board"]["cuts"] = [{"row": 24, "col": 2, "kind": "hole"}]
        self.assertIn("CUT_OUTSIDE_BOARD", verify_candidate(p, v, bad, result, 0))
        bad = copy.deepcopy(v)
        bad["board"]["wires"] = [{
            "from": {"row": 23, "col": 2}, "to": {"row": 24, "col": 2}
        }]
        self.assertIn("WIRE_OUTSIDE_BOARD", verify_candidate(p, v, bad, result, 0))

    def test_slide_must_not_break_another_fixed_lock(self):
        p = project()
        v = prepare_variation(p, ["usb"], [(13, 40)])
        bad = copy.deepcopy(v)
        bad["components"][1]["boardPos"]["col"] = 5
        reasons = verify_candidate(p, v, bad, {"strictValid": True}, 0)
        self.assertIn("LOCKED_PART_MOVED_fixed", reasons)

    def test_cannot_slide_unlocked_part(self):
        p = project()
        with self.assertRaises(ValueError):
            prepare_variation(p, ["fixed"], [(2, 3)])


if __name__ == "__main__":
    unittest.main()
