"""Synthetic tests for post-sweep analysis: preserve source and never fake solved."""
import json
from pathlib import Path
import tempfile
import unittest

import analyze_motoex_native_sweep as analyze


def candidate(seed, nonvertical, crossings, strict=False):
    return {
        "seed": seed, "column": 47, "strictPass": strict,
        "rows": 24, "cols": 56, "wires": 40 + seed, "cuts": 60,
        "quality": 0, "conflicts": 0, "incomplete": 0, "geometry": 0,
        "nonvertical": nonvertical, "crossings": crossings,
        "knife": 8, "stacked": 2, "elapsedWallMs": 4000 + seed,
        "strictFailures": [] if strict else ["NONVERTICAL_1", "SOLVER_ISSUES"],
        "savedJson": "solved/seed_{}.json".format(seed) if strict else "rejected/seed_{}.json".format(seed),
        "diagnostics": {
            "wireViolations": [{"wire": 7, "from": {"row": 0, "col": 1},
                                "to": {"row": 3, "col": 2},
                                "violations": ["NONVERTICAL"],
                                "crossingComponents": [], "stackedWith": []}],
            "wirePolish": {"tried": 13, "accepted": 1, "drillsRecovered": 0},
        },
        "time": {"solveMs": 3000},
    }


class AnalyzeNativeSweepTests(unittest.TestCase):
    def test_near_miss_filter_and_rank(self):
        a = candidate(1, 0, 1)
        b = candidate(2, 1, 0)
        c = candidate(3, 0, 0, strict=True)
        self.assertTrue(analyze.eligible(a))
        self.assertTrue(analyze.eligible(b))
        self.assertFalse(analyze.eligible(c))
        self.assertLess(analyze.rank(a), analyze.rank(b))
        b["incomplete"] = 1
        self.assertFalse(analyze.eligible(b))

    def test_archive_preserves_originals_and_distinguishes_solves(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            records = [candidate(1, 0, 1), candidate(2, 1, 0),
                       candidate(3, 0, 0, strict=True)]
            for r in records:
                board_path = root / r["savedJson"]
                board_path.parent.mkdir(exist_ok=True)
                board_path.write_text(json.dumps({"marker": r["seed"]}), encoding="utf8")
            (root / "results.jsonl").write_text(
                "".join(json.dumps(r) + "\n" for r in records), encoding="utf8")
            original = (root / "results.jsonl").read_bytes()
            summary, ranked = analyze.inspect(root, 5)
            self.assertEqual(summary["strictSolved"], 1)
            self.assertEqual(summary["electricallyCompleteRouted"], 3)
            self.assertEqual([r["seed"] for r in ranked], [1, 2])
            self.assertEqual(len(list((root / "analysis/near_misses").glob("*.json"))), 2)
            self.assertEqual((root / "results.jsonl").read_bytes(), original)
            self.assertIn("NOT SOLVED", (root / "analysis/near_miss_report.md").read_text())
            for r in records:
                self.assertTrue((root / r["savedJson"]).is_file())


if __name__ == "__main__":
    unittest.main()
