"""Protect the new V1.40 input and its intentional unlocked TO-92 placements."""
import json
from pathlib import Path
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1] / "test-fixtures" / "masters" / "moto" / "V1.40"


class MotoV140FixtureTests(unittest.TestCase):
    def test_snapshot(self):
        project = json.loads((ROOT / "Moto-Mate_V_1_40.json").read_text(encoding="utf-8"))
        board = project["board"]
        self.assertEqual((board["rows"], board["cols"]), (24, 56))
        self.assertEqual((len(project["components"]), len(project["nets"]),
                          len(project["netAssignments"])), (44, 34, 125))
        self.assertEqual(board["wires"], [])
        self.assertEqual(board["cuts"], [])
        placed = {p["label"]: p for p in project["components"] if p.get("boardPos")}
        self.assertEqual(set(placed), {"Q1", "Q2"})
        for name, row, rotation in (("Q1", 9, 180), ("Q2", 14, 0)):
            part = placed[name]
            self.assertEqual(part["boardPos"], {"row": row, "col": 11})
            self.assertEqual(part["rotation"], rotation)
            self.assertFalse(part.get("locked", False))
            self.assertEqual([(p["id"], p["name"], p["offsetRow"])
                              for p in part["footprintOverride"]["pins"]],
                             [("3", "E", 0), ("1", "B", 1), ("2", "C", 2)])
        self.assertFalse(any(p.get("locked") for p in project["components"]))

    def test_footprint_archive(self):
        with zipfile.ZipFile(ROOT / "StripboardEditor.pretty.zip") as archive:
            self.assertIsNone(archive.testzip())
            self.assertTrue(any(n.endswith(".kicad_mod") for n in archive.namelist()))
