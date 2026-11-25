"""Static JSON complexity assessment and historical recommendation fixtures."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from gui.json_sniff import assess, save_report

ROOT = Path(__file__).resolve().parents[1]


def fixture(name):
    return json.loads((ROOT / "test-fixtures" / "masters" / name /
                       (name + ".json")).read_text(encoding="utf-8"))


class SniffTests(unittest.TestCase):
    def test_historical_inputs(self):
        for name, score, moves in (("audio", 51.58, 10000), ("moto", 78.03, 20000)):
            project = fixture(name)
            original = copy.deepcopy(project)
            result = assess(project)
            self.assertEqual(project, original)
            self.assertEqual(result["complexity_score"], score)
            self.assertEqual(result["recommended_moves"], moves)
            self.assertEqual(result["features"]["unknown_footprints"], [])

    def test_board_pressure_and_constraints(self):
        project = fixture("audio")
        easy = assess(project)
        project["board"].update(wantedRows=20, wantedCols=30)
        project["components"][0].update(locked=True, edge=True, slide=True)
        hard = assess(project, drilled_only=True, stacking_allowed=False)
        self.assertGreater(hard["complexity_score"], easy["complexity_score"])
        self.assertEqual(hard["recommended_moves"], 20000)
        self.assertEqual(hard["factors"]["constraints"], 10)

    def test_unknown_definition_and_report(self):
        project = fixture("audio")
        project["components"][0]["defId"] = "unknown"
        project["components"][0].pop("footprintOverride", None)
        result = assess(project)
        self.assertTrue(result["features"]["unknown_footprints"])
        self.assertEqual(result["recommended_moves"], 20000)
        with tempfile.TemporaryDirectory() as tmp:
            save_report(Path(tmp), result)
            saved = json.loads((Path(tmp) / "logs" / "json_sniff.json").read_text())
            self.assertEqual(saved, result)

    def test_score_bounds(self):
        project = fixture("moto")
        project["board"].update(rows=1, cols=1)
        result = assess(project, drilled_only=True, stacking_allowed=False)
        self.assertLessEqual(result["complexity_score"], 100)
        self.assertGreaterEqual(result["complexity_score"], 0)
