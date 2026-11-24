"""Pure controller unit tests: no anneal or native binary required."""
import json
from pathlib import Path
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import run_motoex_native_full_slide_sweep as slide


class FullSlideSweepTests(unittest.TestCase):
    def test_every_seed_starts_at_first_column(self):
        cols = [47, 46, 48] + list(range(45, -1, -1)) + [49, 50]
        self.assertEqual(len(cols), 51)
        for seed in range(1, 201):
            self.assertEqual(slide.seed_positions(cols, []), cols)

    def test_failure_does_not_stop_and_first_strict_pass_does(self):
        cols = [47, 46, 48, 45]
        prev = [{"seed": 1, "column": 47, "strictPass": False}]
        self.assertEqual(slide.seed_positions(cols, prev), [46, 48, 45])
        prev += [{"seed": 1, "column": 46, "strictPass": True}]
        self.assertEqual(slide.seed_positions(cols, prev), [])

    def test_archive_summary_only_strict_winners_ranked(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)
            (out / "solved").mkdir()
            cols = [47, 46, 48]
            records = []
            for seed, col, valid, wires, cuts in (
                (1, 47, False, 22, 30),
                (1, 46, True, 33, 52),
                (2, 47, False, 24, 40),
                (2, 46, False, 23, 42),
                (2, 48, True, 30, 47),
            ):
                record = {"seed": seed, "column": col, "strictPass": valid,
                          "wires": wires, "cuts": cuts, "knife": 2, "stacked": 3,
                          "elapsedWallMs": 400, "time": {"solveMs": 375},
                          "strictFailures": [] if valid else ["CROSSINGS_1"],
                          "layoutSig": "{}:{}".format(seed, col)}
                if valid:
                    name = "solved/seed_{}_col_{}.json".format(seed, col)
                    (out / name).write_text(json.dumps({"seed": seed}), encoding="utf8")
                    record["savedJson"] = name
                records.append(record)
            report = slide.analyse(records, [1, 2], cols, 25000, 0, out)
            self.assertEqual(report["strictSolvedSeeds"], 2)
            self.assertEqual(report["totalPositionsAttempted"], 5)
            self.assertEqual(report["maximumPossiblePositions"], 6)
            self.assertEqual([e["seed"] for e in report["top5"]], [2, 1])
            self.assertEqual([e["winnerColumn"] for e in report["seedOutcomes"]], [46, 48])
            self.assertEqual(len(list((out / "top5").glob("*.json"))), 2)
            self.assertTrue((out / "summary.json").is_file())
            self.assertTrue((out / "results.csv").is_file())

    def test_unsolved_seed_requires_all_columns(self):
        with tempfile.TemporaryDirectory() as root:
            out = Path(root)
            entries = [{"seed": 1, "column": 47, "strictPass": False, "time": {},
                        "elapsedWallMs": 100, "strictFailures": ["CROSSINGS_1"]}]
            report = slide.analyse(entries, [1], [47, 46], 25000, 0, out)
            self.assertEqual(report["seedsFinished"], 0)
            self.assertFalse(report["seedOutcomes"][0]["fullyExhausted"])


if __name__ == "__main__":
    unittest.main()
