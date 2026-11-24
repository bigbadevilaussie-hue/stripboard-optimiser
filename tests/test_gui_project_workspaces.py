"""One Work directory per JSON; no accidental cross-circuit data mixing."""
import copy
import csv
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from gui.work_directory import (
    WORKSPACE_MANIFEST, PASS_ONE, PASS_TWO, CSV_FIELDS,
    project_workspace, project_workspace_name,
    list_project_workspaces, clear_started_pass,
    adopt_matching_legacy_pass_one, ensure_work, read_pass_one,
)


def write_csv(folder, seed="0001"):
    with (folder / "results.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerow({"seed": seed, "cut": 39, "w": 11,
                         "q": "74.14", "time_taken": "1.03"})


class NamedWorkspaceContract(unittest.TestCase):
    def test_one_isolated_folder_per_source_json(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            root = base / "Work"
            a = base / "A" / "audio.json"
            b = base / "B" / "audio.json"
            a.parent.mkdir()
            b.parent.mkdir()
            a.write_text('{"v":1}')
            b.write_text('{"v":1}')
            wa = project_workspace(a, root, create=True)
            wb = project_workspace(b, root, create=True)
            self.assertNotEqual(wa, wb)
            self.assertTrue(wa.name.startswith("audio--"))
            self.assertTrue(wb.name.startswith("audio--"))
            self.assertEqual(len(wa.name.split("--")[-1]), 12)
            self.assertEqual(len(wb.name.split("--")[-1]), 12)
            self.assertEqual(project_workspace_name(a), wa.name)
            self.assertEqual(len(list_project_workspaces(root)), 2)
            for folder in (wa, wb):
                for name in (PASS_ONE, PASS_TWO, "jsons", "logs"):
                    self.assertTrue((folder / name).is_dir())
                self.assertTrue((folder / WORKSPACE_MANIFEST).is_file())

            (wa / PASS_ONE / "results.csv").write_text("A")
            (wa / PASS_TWO / "candidates.csv").write_text("A2")
            (wb / PASS_ONE / "results.csv").write_text("B")
            (root / "keep.txt").write_text("legacy root")
            clear_started_pass(PASS_ONE, wa)
            self.assertFalse((wa / PASS_ONE / "results.csv").exists())
            self.assertEqual((wa / PASS_TWO / "candidates.csv").read_text(), "A2")
            self.assertEqual((wb / PASS_ONE / "results.csv").read_text(), "B")
            self.assertEqual((root / "keep.txt").read_text(), "legacy root")

    def test_editing_contents_does_not_rename_or_clear_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "moto.json"
            p.write_text('{"rev":1}')
            root = Path(td) / "Work"
            folder = project_workspace(p, root, create=True)
            keeper = folder / PASS_TWO / "keep.txt"
            keeper.write_text("previous results")
            p.write_text('{"rev":2}')
            self.assertEqual(project_workspace(p, root, create=True), folder)
            self.assertEqual(keeper.read_text(), "previous results")
            self.assertFalse((root / PASS_ONE).exists())
            self.assertFalse((root / PASS_TWO).exists())

    def test_workspace_rejects_symlinked_project_folder(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            p = base / "moto.json"
            p.write_text("{}")
            root = base / "Work"
            root.mkdir()
            elsewhere = base / "other"
            elsewhere.mkdir()
            (root / project_workspace_name(p)).symlink_to(elsewhere, target_is_directory=True)
            with self.assertRaises(ValueError):
                project_workspace(p, root, create=True)
            self.assertEqual(list(elsewhere.iterdir()), [])

    def test_legacy_results_only_copy_on_identical_solver_input(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = base / "audio.json"
            source.write_text("{}")
            root = ensure_work(base / "Work")  # Legacy folder still present.
            project = {"board": {"rows":24, "cols":56, "lockedRows":False,
                                 "lockedCols":False},
                       "components": [], "nets": [], "netAssignments": []}
            prepared = copy.deepcopy(project)
            prepared["board"]["lockedRows"] = True
            prepared["board"]["lockedCols"] = True
            signature = hashlib.sha256(
                json.dumps(prepared, sort_keys=True).encode("utf-8")
            ).hexdigest()
            write_csv(root / PASS_ONE, "1171")
            original_csv = (root / PASS_ONE / "results.csv").read_bytes()
            log = root / PASS_ONE / "activity.log"
            log.write_text(
                f"[PASS1][START] seeds=1..2000 moves=10000 workers=4 "
                f"drilled_only=False stacking_allowed=True input_sha256={signature}\n"
            )
            folder = project_workspace(source, root, create=True)
            self.assertTrue(adopt_matching_legacy_pass_one(project, folder, root))
            self.assertEqual((folder / PASS_ONE / "results.csv").read_bytes(), original_csv)
            self.assertEqual((root / PASS_ONE / "results.csv").read_bytes(), original_csv)
            self.assertEqual(read_pass_one(folder)[0]["seed"], 1171)
            self.assertFalse(adopt_matching_legacy_pass_one(project, folder, root))

            other = base / "moto.json"
            other.write_text("{}")
            bad_workspace = project_workspace(other, root, create=True)
            altered = copy.deepcopy(project)
            altered["board"]["cols"] = 55
            self.assertFalse(adopt_matching_legacy_pass_one(altered, bad_workspace, root))
            self.assertFalse((bad_workspace / PASS_ONE / "results.csv").exists())

    def test_invalid_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = Path(td) / "test.json"
            source.write_text("{}")
            root = Path(td) / "Work"
            folder = project_workspace(source, root, create=True)
            (folder / WORKSPACE_MANIFEST).write_text('{"schema":999}')
            with self.assertRaises(ValueError):
                project_workspace(source, root, create=False)


if __name__ == "__main__":
    unittest.main()
