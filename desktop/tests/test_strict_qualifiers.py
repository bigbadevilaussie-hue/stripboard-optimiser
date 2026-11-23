"""v1.61 regression tests: only strict-valid boards advance; distinct routes survive."""
import json
from pathlib import Path
import tempfile
import unittest

from stripboard_optimizer.solver.solver_adapter import is_valid
from stripboard_optimizer.solver.worker import _layout_signature


class StrictQualificationTests(unittest.TestCase):
    def test_missing_strict_verdict_is_never_accepted(self):
        self.assertFalse(is_valid({"quality": 0, "offAxis": 0, "conflicts": 0, "geo": 0}))

    def test_strict_failure_cannot_be_a_finalist(self):
        self.assertFalse(is_valid({
            "quality": 0, "offAxis": 0, "strictValid": False,
            "strictFailures": ["KNIFE_3", "STACKED_1"],
        }))

    def test_strict_success_can_qualify(self):
        self.assertTrue(is_valid({"strictValid": True, "strictFailures": []}))
        self.assertFalse(is_valid({"strictValid": True, "strictFailures": ["CROSSINGS_1"]}))

    def test_same_placement_different_routes_are_distinct(self):
        original = {
            "board": {"rows": 24, "cols": 56, "cuts": [], "wires": []},
            "components": [{"id": "U1", "boardPos": {"row": 3, "col": 4}, "rotation": 0}],
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "layout.json"
            path.write_text(json.dumps(original), encoding="utf-8")
            baseline = _layout_signature(path)
            original["board"]["wires"] = [{
                "id": "w1", "from": {"row": 3, "col": 4},
                "to": {"row": 8, "col": 4},
            }]
            path.write_text(json.dumps(original), encoding="utf-8")
            routed = _layout_signature(path)
            self.assertNotEqual(baseline, routed)
            original["board"]["wires"][0]["id"] = "arbitrary-other-id"
            path.write_text(json.dumps(original), encoding="utf-8")
            self.assertEqual(routed, _layout_signature(path))
            original["board"]["cuts"] = [{"row": 3, "col": 5, "kind": "hole"}]
            path.write_text(json.dumps(original), encoding="utf-8")
            self.assertNotEqual(routed, _layout_signature(path))


if __name__ == "__main__":
    unittest.main()
