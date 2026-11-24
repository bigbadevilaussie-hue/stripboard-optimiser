"""Preflight contract: raw input unchanged and no optimiser/worker spawned."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.preflight import preflight_project, sniff_json


def fixture():
    return {
        "board": {"rows": 24, "cols": 56, "cuts": [], "wires": []},
        "components": [{"id": "R1", "label": "R1", "defId": "resistor",
                        "boardPos": {"row": 3, "col": 4}, "locked": True}],
        "componentDefs": [{"id": "resistor", "width": 2, "height": 1,
                           "pins": [{"id": "1", "offsetRow": 0, "offsetCol": 0},
                                    {"id": "2", "offsetRow": 0, "offsetCol": 1}]}],
        "nets": [{"id": "N1"}, {"id": "N2"}],
        "netAssignments": [
            {"componentId": "R1", "pinId": "1", "netId": "N1"},
            {"componentId": "R1", "pinId": "2", "netId": "N2"}
        ],
        "lockedRows": True, "lockedCols": True,
    }


class HeadlessPreflightTests(unittest.TestCase):
    def test_valid_input_ends_before_pass1_and_preserves_source(self):
        project = fixture()
        original = copy.deepcopy(project)
        with patch.object(subprocess, "Popen", side_effect=AssertionError("solver started")), \
             patch.object(subprocess, "run", side_effect=AssertionError("solver started")):
            report = preflight_project(project)
        self.assertEqual(project, original)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["execution"], "STOPPED_BEFORE_PASS_1")
        self.assertEqual(report["board"]["rows"], 24)
        self.assertEqual(report["board"]["cols"], 56)
        self.assertTrue(report["board"]["lockedRows"])
        self.assertTrue(report["board"]["lockedCols"])

    def test_unknown_net_fails_before_pass1(self):
        project = fixture()
        project["netAssignments"][0]["netId"] = "missing"
        report = preflight_project(project)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(report["execution"], "STOPPED_BEFORE_PASS_1")
        self.assertTrue(any("unknown net" in error for error in report["errors"]))

    def test_invalid_dimensions_fail(self):
        project = fixture()
        project["board"]["rows"] = 0
        report = preflight_project(project)
        self.assertEqual(report["status"], "FAIL")

    def test_sniff_does_not_write_sidecars_or_mutate_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "source.json"
            data = json.dumps(fixture(), sort_keys=True).encode()
            path.write_bytes(data)
            report = sniff_json(path)
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual({x.name for x in Path(tmp).iterdir()}, {"source.json"})
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(len(report["source_sha256"]), 64)

    def test_missing_footprint_warns_instead_of_replacing_geometry(self):
        project = fixture()
        project["components"][0]["defId"] = "not-known"
        report = preflight_project(project)
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(len(report["missing_footprints"]), 1)


if __name__ == "__main__":
    unittest.main()
