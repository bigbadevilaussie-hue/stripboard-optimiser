"""Pass One tracks PASS/FAIL/ERROR and saves winner JSON outside CSV folder."""
import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from gui import pass_one
from gui.work_directory import ensure_work, pass_one_budget_dir


class PassOneContract(unittest.TestCase):
    def test_score_100_existing_formula(self):
        saved = {"board": {"cuts": [{"row": 1, "col": 1}],
                           "wires": [{"from":{"row":1,"col":1},
                                      "to":{"row":2,"col":1}}]},
                 "components": [{"boardPos": {"row":1,"col":1}}]}
        self.assertAlmostEqual(pass_one.quality100(saved), 99.58)

    def test_pass_one_csv_records_pass_and_fail_seeds(self):
        with tempfile.TemporaryDirectory() as td:
            root = ensure_work(Path(td) / "Work")
            out = pass_one_budget_dir(root, 10000, create=True)
            events, logs = [], []
            def fake_seed(project, moves, seed, drilled, stacking, cancel,
                          *, retained_candidate=None):
                if retained_candidate is not None:
                    Path(retained_candidate).write_text(json.dumps({
                        "board": {"rows": 24, "cols": 56, "wires": [], "cuts": []},
                        "components": []
                    }), encoding="utf-8")
                self.assertEqual(moves, 10000)
                if seed == 1:
                    return {"seed": 1, "valid": True,
                            "cut": 44, "w": 29, "q": 78.24, "s": 2, "wire_length_mm": 284.48, "time_taken": 3.2}
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
            self.assertEqual(len(rows), 2)
            by_seed = {row["seed"]: row for row in rows}
            self.assertEqual(by_seed["0001"], {
                "seed": "0001", "cut": "44", "w": "29", "q": "78.24",
                "time_taken": "3.200", "s": "2", "wire_length_mm": "284.48",
                "quality_version": "Q3", "status": "PASS", "reason": "",
            })
            self.assertEqual(by_seed["0002"]["status"], "FAIL")
            self.assertIn("short circuit", by_seed["0002"]["reason"])
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             ["activity.log", "campaign.json", "results.csv"])
            self.assertEqual(json.loads((out / "campaign.json").read_text())["state"],
                             "COMPLETED")
            self.assertTrue(any("[PASS1][FAIL]" in line for line in logs))
            self.assertEqual(len(events), 3)  # Restored initial progress plus both seeds.
            self.assertTrue(Path(result["winner_json"]).is_file())
            self.assertEqual(Path(result["winner_json"]).name, "winner_seed_0001.json")

    def test_unsupported_move_budget_rejected(self):
        with self.assertRaises(ValueError):
            pass_one.run_pass_one({}, 25000, 4, False, True, Path("/dev/null"),
                                  lambda _:None,lambda _:None,lambda:False)


if __name__ == "__main__":
    unittest.main()
