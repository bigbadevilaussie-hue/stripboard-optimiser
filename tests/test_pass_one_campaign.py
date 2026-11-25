"""Pass One campaign persistence, strict resume and per-budget isolation."""
import csv
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.pass_one import inspect_pass_one_campaign, run_pass_one
from gui.work_directory import (
    CAMPAIGN_FIELDS, CAMPAIGN_MANIFEST, PASS_ONE, PASS_TWO,
    pass_one_budget_dir, winner_budget_dir, ensure_work,
    clear_pass_one_budget, read_pass_one, prepare_pass_two,
)


class CampaignStorageTests(unittest.TestCase):
    def test_deleting_10k_never_touches_20k_or_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_work(Path(tmp) / "Work" / "moto")
            ten = pass_one_budget_dir(workspace, 10000, create=True)
            twenty = pass_one_budget_dir(workspace, 20000, create=True)
            top10 = winner_budget_dir(workspace, 10000, create=True)
            top20 = winner_budget_dir(workspace, 20000, create=True)
            (workspace / PASS_ONE / "results.csv").write_text("legacy!")
            (workspace / PASS_TWO / "keep.csv").write_text("pass2!")
            (ten / "results.csv").write_text("delete this")
            (twenty / "results.csv").write_text("keep this")
            (top10 / "champion.svg").write_text("delete this")
            (top20 / "champion.svg").write_text("keep this")
            clear_pass_one_budget(workspace, 10000)
            self.assertFalse((ten / "results.csv").exists())
            self.assertFalse((top10 / "champion.svg").exists())
            self.assertEqual((twenty / "results.csv").read_text(), "keep this")
            self.assertEqual((top20 / "champion.svg").read_text(), "keep this")
            self.assertEqual((workspace / PASS_ONE / "results.csv").read_text(),
                             "legacy!")
            self.assertEqual((workspace / PASS_TWO / "keep.csv").read_text(),
                             "pass2!")

    def test_every_seed_saved_and_error_retried_without_repeating_pass_fail(self):
        project = {"board": {"rows": 24, "cols": 56}, "components": []}
        seen = []
        recovered = False

        def fake_seed(project, moves, seed, drilled_only, stacking_allowed,
                      cancelled, *, retained_candidate=None):
            seen.append(seed)
            if retained_candidate is not None:
                path = Path(retained_candidate)
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({
                    "board": {"rows": 24, "cols": 56}, "components": []
                }))
            if seed in (1, 4):
                return {"seed": seed, "valid": True, "cut": 35 if seed == 4 else 44,
                        "w": 24 if seed == 4 else 29, "q": 83.5 if seed == 4 else 72.2,
                        "time_taken": 1.25}
            if seed == 3 and not recovered:
                raise RuntimeError("transient native failure")
            return {"seed": seed, "valid": False, "seconds": 1.4,
                    "reason": "strict-invalid"}

        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_work(Path(tmp) / "Work" / "moto")
            folder = pass_one_budget_dir(workspace, 10000, create=True)
            events = []
            with patch("gui.pass_one.prerequisites"), \
                 patch("gui.pass_one.AUDITOR", Path(__file__)), \
                 patch("gui.pass_one._run_seed", side_effect=fake_seed):
                result = run_pass_one(
                    project, 10000, 3, False, True, folder,
                    events.append, lambda _: None, lambda: False,
                    seeds=5,
                )
                self.assertFalse(result["completed"])
                self.assertEqual(result["qualified"], 2)
                self.assertEqual(result["failed"], 2)
                self.assertEqual(result["errors"], 1)
                self.assertEqual(result["checked"], 4)
                with (folder / "results.csv").open(newline="") as file:
                    rows = list(csv.DictReader(file))
                self.assertEqual(len(rows), 5)
                self.assertEqual(tuple(rows[0]), CAMPAIGN_FIELDS)
                self.assertEqual({int(r["seed"]): r["status"] for r in rows}, {
                    1: "PASS", 2: "FAIL", 3: "ERROR", 4: "PASS", 5: "FAIL"
                })
                self.assertEqual(
                    json.loads((folder / CAMPAIGN_MANIFEST).read_text())["state"],
                    "INCOMPLETE"
                )
                snapshot = inspect_pass_one_campaign(
                    project, 10000, 3, False, True, folder, seeds=5
                )
                self.assertEqual(snapshot["done"], 4)
                self.assertEqual(snapshot["remaining"], 1)
                self.assertEqual(snapshot["errors"], 1)
                self.assertTrue(events)
                with self.assertRaisesRegex(ValueError, "INCOMPLETE"):
                    read_pass_one(workspace, csv_path=folder / "results.csv")

                seen.clear()
                recovered = True
                result2 = run_pass_one(
                    project, 10000, 3, False, True, folder,
                    events.append, lambda _: None, lambda: False,
                    seeds=5, resume=True,
                )
                self.assertTrue(result2["completed"])
                self.assertEqual(result2["checked"], 5)
                self.assertEqual(result2["qualified"], 2)
                self.assertEqual(result2["errors"], 0)
                self.assertEqual(sorted(seen), [3, 4])  # Only seed 3 rerun; 4 is winner replay.
                self.assertEqual(Path(result2["winner_json"]).name,
                                 "winner_seed_0004.json")
                self.assertTrue(Path(result2["winner_json"]).is_file())
                qualified = read_pass_one(workspace, csv_path=folder / "results.csv")
                self.assertEqual({row["seed"] for row in qualified}, {1, 4})
                candidates, count = prepare_pass_two(
                    workspace, source_csv=folder / "results.csv"
                )
                self.assertEqual(count, 2)
                self.assertEqual(
                    candidates.read_text().count("\n"), 3
                )
                self.assertTrue((folder / "results.csv").is_file())

    def test_debug_200_rows_isolated_from_full_campaign(self):
        from gui.pass_one import DEBUG_SEEDS, DEFAULT_SEEDS
        from gui.work_directory import pass_one_campaign_sources
        self.assertEqual((DEBUG_SEEDS, DEFAULT_SEEDS), (200, 2000))
        project = {"board": {"rows": 24, "cols": 56}, "components": []}
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_work(Path(tmp) / "Work" / "moto")
            full = pass_one_budget_dir(workspace, 10000, create=True)
            debug = pass_one_budget_dir(workspace, 10000, create=True, debug=True)
            (full / "results.csv").write_text("PRESERVE FULL 2000")
            full_winner = winner_budget_dir(workspace, 10000, create=True)
            (full_winner / "champion.svg").write_text("PRESERVE FULL WINNER")
            def reject_seed(project, moves, seed, drilled, stacking, cancelled):
                return {"seed": seed, "valid": False,
                        "seconds": 0.002, "reason": "strict invalid"}
            completed = []
            with patch("gui.pass_one.prerequisites"), \
                 patch("gui.pass_one.AUDITOR", Path(__file__)), \
                 patch("gui.pass_one._run_seed", side_effect=reject_seed):
                result = run_pass_one(
                    project, 10000, 3, False, True, debug,
                    completed.append, lambda _: None, lambda: False,
                    seeds=200, debug=True
                )
            self.assertTrue(result["completed"])
            self.assertEqual(result["checked"], 200)
            self.assertEqual(result["qualified"], 0)
            self.assertEqual(completed[-1]["total"], 200)
            with (debug / "results.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 200)
            self.assertEqual(rows[0]["seed"], "0001")
            self.assertEqual({r["seed"] for r in rows},
                             {f"{n:04d}" for n in range(1, 201)})
            state = json.loads((debug / "campaign.json").read_text())
            self.assertEqual(state["state"], "COMPLETED")
            self.assertTrue(state["debug"])
            self.assertEqual(state["seeds"], 200)
            self.assertEqual((full / "results.csv").read_text(), "PRESERVE FULL 2000")
            self.assertEqual((full_winner / "champion.svg").read_text(),
                             "PRESERVE FULL WINNER")
            labels = [label for label, _ in pass_one_campaign_sources(workspace)]
            self.assertIn("10k moves", labels)
            self.assertIn("10k moves (DEBUG 200)", labels)
            clear_pass_one_budget(workspace, 10000)
            self.assertFalse((full / "results.csv").exists())
            self.assertTrue((debug / "results.csv").exists())
            self.assertEqual(json.loads((debug / "campaign.json").read_text())["seeds"],
                             200)

    def test_resume_rejects_changed_input_or_rules(self):
        project = {"board": {"rows": 24, "cols": 56}, "components": []}
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ensure_work(Path(tmp) / "Work" / "moto")
            folder = pass_one_budget_dir(workspace, 20000, create=True)
            with patch("gui.pass_one.prerequisites"), \
                 patch("gui.pass_one.AUDITOR", Path(__file__)), \
                 patch("gui.pass_one._run_seed", return_value={
                     "seed": 1, "valid": False, "seconds": 1.1, "reason": "strict"
                 }):
                run_pass_one(
                    project, 20000, 4, False, True, folder,
                    lambda _: None, lambda _: None, lambda: False, seeds=1,
                )
            modified = {"board": {"rows": 24, "cols": 55}, "components": []}
            with self.assertRaisesRegex(ValueError, "input_sha256"):
                inspect_pass_one_campaign(
                    modified, 20000, 4, False, True, folder, seeds=1
                )
            with self.assertRaisesRegex(ValueError, "drilled_only"):
                inspect_pass_one_campaign(
                    project, 20000, 4, True, True, folder, seeds=1
                )


if __name__ == "__main__":
    unittest.main()
