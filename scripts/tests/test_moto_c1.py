"""v1.62 native MOTO source correction regression tests; no GUI dependencies."""
import json
from pathlib import Path
import tempfile
import unittest

import fix_moto_c1 as fixer


class MotoC1CorrectionTests(unittest.TestCase):
    def test_correct_only_c1_not_c4(self):
        data = {"components": [
            {"id": "c1", "label": "C1", "value": "1000mf"},
            {"id": "c4", "label": "C4", "value": "15pf"},
        ], "board": {"rows": 24, "cols": 56}}
        path = Path("motomix.json")
        state, new_text = fixer.corrected_text(path, json.dumps(data))
        self.assertEqual(state, "update")
        fixed = json.loads(new_text)
        self.assertEqual(fixed["components"][0]["value"], "1000µF")
        self.assertEqual(fixed["components"][1]["value"], "15pf")
        self.assertEqual(fixer.corrected_text(path, new_text)[0], "already-correct")

    def test_netlist_changes_only_c1(self):
        text = '(comp (ref "C1")\n  (value "1000mf")\n)\n(comp (ref "C2")\n  (value "1000mf")\n)\n'
        state, new_text = fixer.corrected_text(Path("moto.net"), text)
        self.assertEqual(state, "update")
        self.assertIn('(ref "C1")\n  (value "1000µF")', new_text)
        self.assertIn('(ref "C2")\n  (value "1000mf")', new_text)

    def test_ambiguous_json_stays_untouched(self):
        text = json.dumps({"components": [
            {"label": "C1", "value": "1000mf"},
            {"label": "C2", "value": "1000mf"},
        ]})
        self.assertEqual(fixer.corrected_text(Path("moto.json"), text)[0], "ambiguous-value")

    def test_archive_protection(self):
        self.assertTrue(fixer.is_archive(Path("/private/tmp/stripboard_drill_stack_80/MOTO/projects/1.json")))
        self.assertTrue(fixer.is_archive(Path.home() / "Desktop" / "stripboard_baseline_80_full" / "MOTO" / "projects" / "1.json"))
        self.assertFalse(fixer.is_archive(Path.home() / "Documents" / "stripboard-optimiser" / "test-fixtures" / "masters" / "moto" / "moto.json"))

    def test_backups_preserve_exact_original_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project = root / "moto.json"
            before = b'{"components":[{"label":"C1","value":"1000mf"}]}\n'
            project.write_bytes(before)
            state, new_text = fixer.corrected_text(project, before.decode("utf-8"))
            self.assertEqual(state, "update")
            entry = fixer.apply_one(project, new_text, root / "backup", root)
            self.assertEqual(Path(entry["backup"]).read_bytes(), before)
            self.assertIn("1000µF", project.read_text(encoding="utf-8"))
            self.assertEqual(project.read_bytes(), new_text.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
