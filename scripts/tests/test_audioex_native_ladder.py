"""AUDIOEX BMS-fixed ladder regression; no native solve executed."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import run_audioex_native_ladder as ladder


class AudioexBmsLadderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads(ladder.SOURCE.read_text(encoding="utf8"))

    def test_exact_ladder_270_trials(self):
        self.assertEqual(ladder.BUDGETS[:10], tuple(range(5000, 50001, 5000)))
        self.assertEqual(ladder.BUDGETS[10:], tuple(range(100000, 500001, 25000)))
        self.assertEqual(len(ladder.BUDGETS), 27)

    def test_prepare_fixed_bms_case_position_and_preserve_master(self):
        original = json.dumps(self.original, sort_keys=True)
        data = ladder.prepare_audioex(self.original)
        bms, definition = ladder.bms_info(data)
        self.assertEqual(bms["boardPos"], {"row": -2, "col": 24})
        self.assertTrue(bms["locked"])
        self.assertIs(bms["edge"], True)
        self.assertIs(bms["slide"], False)
        self.assertEqual((definition["height"], definition["width"]), (12, 7))
        self.assertEqual((data["board"]["rows"], data["board"]["cols"]), (24, 56))
        self.assertTrue(data["board"]["lockedRows"] and data["board"]["lockedCols"])
        self.assertEqual(data["board"]["cuts"], [])
        self.assertEqual(data["board"]["wires"], [])
        self.assertEqual(len(self.original["board"]["cuts"]), 4)
        self.assertNotIn("edge", ladder.bms_info(self.original)[0])
        self.assertEqual(json.dumps(self.original, sort_keys=True), original)
        self.assertEqual(len(data["netAssignments"]), 85)
        for pin in definition["pins"]:
            self.assertGreaterEqual(-2 + pin["offsetRow"], 0)
            self.assertLess(-2 + pin["offsetRow"], 24)
            self.assertGreaterEqual(24 + pin["offsetCol"], 0)
            self.assertLess(24 + pin["offsetCol"], 56)

    def test_fail_closed_on_bms_slide_or_moved_position(self):
        changed = json.loads(json.dumps(self.original))
        ladder.bms_info(changed)[0]["slide"] = True
        with self.assertRaisesRegex(ValueError, "Slide"):
            ladder.prepare_audioex(changed)
        changed = json.loads(json.dumps(self.original))
        ladder.bms_info(changed)[0]["boardPos"]["col"] = 25
        with self.assertRaisesRegex(ValueError, "row -2"):
            ladder.prepare_audioex(changed)

    def test_rank_qualified_only_and_distinct(self):
        rows = [
            {"moves": 5000, "seed": 1, "strictPass": True, "wires": 15,
             "cuts": 40, "wireLength": 20, "layoutSig": "same"},
            {"moves": 10000, "seed": 2, "strictPass": True, "wires": 15,
             "cuts": 40, "wireLength": 20, "layoutSig": "same"},
            {"moves": 100000, "seed": 3, "strictPass": False, "wires": 1,
             "cuts": 1, "layoutSig": "invalid"},
            {"moves": 20000, "seed": 4, "strictPass": True, "wires": 14,
             "cuts": 45, "wireLength": 30, "layoutSig": "better"},
        ]
        qualified = ladder.rank_passes(rows)
        self.assertEqual([r["seed"] for r in qualified], [4, 1])

    def test_invalid_source_pin_must_reject_before_solving(self):
        changed = json.loads(json.dumps(self.original))
        definition = ladder.bms_info(changed)[1]
        definition["pins"][0]["offsetRow"] = 0
        with self.assertRaisesRegex(ValueError, "pin off physical board"):
            ladder.prepare_audioex(changed)

    def test_first_fit_diagnostics_are_archived(self):
        self.assertIn("firstFeasibleMove", ladder.FIELDS)
        self.assertIn("firstFeasibleMs", ladder.FIELDS)
        import inspect
        source = inspect.getsource(ladder.run_one)
        self.assertIn('result.get("firstFeasibleMove")', source)
        self.assertIn('result.get("firstFeasibleMs")', source)

    def test_checkpoint_rejects_duplicate_or_mismatched_archive(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            folder = Path(tmp)
            file = folder / "results.jsonl"
            row = {"moves": 5000, "seed": 1, "strictPass": False}
            file.write_text(json.dumps(row) + "\n" + json.dumps(row) + "\n")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                ladder.read_checkpoint(folder, (5000,), (1,))


if __name__ == "__main__":
    unittest.main()
