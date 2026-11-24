"""Pass One CSV keeps verified W/C/Q/time and never writes solved JSON to Work."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from gui import pass_one
from gui.work_directory import ensure_work


class PassOneContract(unittest.TestCase):
    def test_score_100_existing_formula(self):
        saved = {"board": {"cuts": [{"row": 1, "col": 1}],
                           "wires": [{"from":{"row":1,"col":1},
                                      "to":{"row":2,"col":1}}]},
                 "components": [{"boardPos": {"row":1,"col":1}}]}
        self.assertAlmostEqual(pass_one.quality100(saved), 98.95)

    def test_pass_one_csv_only_verified_rows(self):
        with tempfile.TemporaryDirectory() as td:
            root = ensure_work(Path(td) / "Work")
            out = root / "pass 1"
            events, logs = [], []
            def fake_seed(project, moves, seed, drilled, stacking, cancel):
                self.assertEqual(moves, 10000)
                if seed == 1:
                    return {"seed": 1, "valid": True,
                            "cut": 44, "w": 29, "q": 78.24, "time_taken": 3.2}
                return {"seed": seed, "valid": False, "seconds": 2.1,
                        "reason": "short circuit"}
            project = {"board": {"rows":24,"cols":56,"lockedRows":False,
                                 "lockedCols":False}}
            with patch.object(pass_one, "prerequisites"), \
                 patch.object(pass_one, "AUDITOR", Path(__file__)), \
                 patch.object(pass_one, "_run_seed", side_effect=fake_seed):
                result = pass_one.run_pass_one(
                    project, 10000, 3, False, True, out,
                    events.append, logs.append, lambda: False, seeds=2
                )
            self.assertEqual(result["qualified"], 1)
            self.assertEqual(project["board"]["lockedRows"], False)
            with (out / "results.csv").open(newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0], {
                "seed":"0001", "cut":"44", "w":"29",
                "q":"78.24", "time_taken":"3.200"})
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             ["activity.log", "results.csv"])
            self.assertTrue(any("[PASS1][REJECT]" in line for line in logs))
            self.assertEqual(len(events), 2)

    def test_unsupported_move_budget_rejected(self):
        with self.assertRaises(ValueError):
            pass_one.run_pass_one({}, 25000, 4, False, True, Path("/dev/null"),
                                  lambda _:None,lambda _:None,lambda:False)


if __name__ == "__main__":
    unittest.main()
