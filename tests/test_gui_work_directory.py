"""Work directory isolation, Pass Two direct startup, CSV contract."""
import csv
import tempfile
import unittest
from pathlib import Path
from gui.work_directory import (
    ensure_work, clear_started_pass, read_pass_one,
    prepare_pass_two, CSV_FIELDS, PASS_ONE, PASS_TWO,
)


class WorkContract(unittest.TestCase):
    def test_folders_are_stable_and_not_erased_on_load(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "Work"
            ensure_work(root)
            for part in ("pass 1", "pass 2", "jsons", "logs"):
                self.assertTrue((root / part).is_dir())
                (root / part / "keep.txt").write_text("preserve")
            ensure_work(root)
            self.assertTrue(all((root / part / "keep.txt").read_text() == "preserve"
                                for part in ("pass 1", "pass 2", "jsons", "logs")))

    def test_clear_exactly_selected_pass(self):
        with tempfile.TemporaryDirectory() as td:
            root = ensure_work(Path(td) / "Work")
            for part in ("pass 1", "pass 2", "jsons", "logs"):
                (root / part / "keep.txt").write_text(part)
            clear_started_pass(PASS_TWO, root)
            self.assertFalse((root / "pass 2" / "keep.txt").exists())
            for part in ("pass 1", "jsons", "logs"):
                self.assertTrue((root / part / "keep.txt").exists())
            with self.assertRaises(ValueError):
                clear_started_pass("jsons", root)

    def test_pass_two_reads_csv_without_project_or_clearing_pass_one(self):
        with tempfile.TemporaryDirectory() as td:
            root = ensure_work(Path(td) / "Work")
            source = root / PASS_ONE / "results.csv"
            with source.open("w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                w.writeheader()
                w.writerow({"seed":"0002","cut":44,"w":29,
                            "q":"78.24","time_taken":"3.200"})
                w.writerow({"seed":"0100","cut":33,"w":22,
                            "q":"88.40","time_taken":"2.450"})
            (root / PASS_TWO / "old.txt").write_text("old")
            rows = read_pass_one(root)
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[0]["seed"], 2)
            with self.assertRaisesRegex(ValueError, 'Q1'):
                prepare_pass_two(root)
            self.assertEqual(len(read_pass_one(root)), 2)
            self.assertTrue((root / PASS_TWO / "old.txt").exists())
            self.assertEqual(source.read_text().count("\n"), 3)

    def test_no_pass_one_does_not_clear_pass_two(self):
        with tempfile.TemporaryDirectory() as td:
            root = ensure_work(Path(td) / "Work")
            flag = root / PASS_TWO / "preserve.txt"
            flag.write_text("stay")
            with self.assertRaises(FileNotFoundError):
                prepare_pass_two(root)
            self.assertEqual(flag.read_text(), "stay")

    def test_malformed_csv_does_not_clear_pass_two(self):
        with tempfile.TemporaryDirectory() as td:
            root = ensure_work(Path(td) / "Work")
            (root / PASS_ONE / "results.csv").write_text("bad,header\n1,2\n")
            flag = root / PASS_TWO / "preserve.txt"
            flag.write_text("stay")
            with self.assertRaises(ValueError):
                prepare_pass_two(root)
            self.assertEqual(flag.read_text(), "stay")

    def test_work_stage_cannot_be_symlink(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            target = base / "other"
            target.mkdir()
            root = base / "Work"
            root.mkdir()
            (root / PASS_ONE).symlink_to(target, target_is_directory=True)
            with self.assertRaises(ValueError):
                ensure_work(root)
            self.assertTrue(target.is_dir())


if __name__ == "__main__":
    unittest.main()
