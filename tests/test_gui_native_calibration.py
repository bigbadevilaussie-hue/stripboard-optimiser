"""Genuine 100-point decoder probe: no full solver attempts, no save."""
import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch
import speed_probe
from gui import native_calibration as probe


class NativeMoveProbeTests(unittest.TestCase):
    def test_donor_speed_probe_remains(self):
        self.assertEqual(speed_probe.TASKS, 24)

    def test_probe_policy_and_no_solve(self):
        project = {"board": {"rows": 24, "cols": 56, "lockedRows": False,
                             "lockedCols": False, "wantedRows": 23,
                             "wantedCols": 54, "wantedRowsMode": "fixed",
                             "wantedColsMode": "fixed"},
                   "components": [], "nets": [], "netAssignments": []}
        original = copy.deepcopy(project)
        commands, events, logs = [], [], []
        def fake_run(command, env, cancelled):
            commands.append(command)
            sent = json.loads(
                (Path(command[command.index("--data") + 1]) / "projects/1.json")
                .read_text(encoding="utf-8"))
            self.assertEqual((sent["board"]["rows"], sent["board"]["cols"]), (24, 56))
            self.assertTrue(sent["board"]["lockedRows"])
            self.assertTrue(sent["board"]["lockedCols"])
            self.assertEqual((sent["board"]["wantedRows"], sent["board"]["wantedCols"]),
                             (23, 54))
            return (0, '{"wires":0,"cuts":0}', 'probeMs 0.250\n')
        with patch.object(probe, "prerequisites"), patch.object(
                probe, "run_process", side_effect=fake_run):
            report = probe.calibrate(project, 4, True, False,
                                     events.append, logs.append, lambda: False)
        self.assertEqual(project, original)
        self.assertEqual(report["points"], 100)
        self.assertAlmostEqual(report["decodes_per_second"], 4000)
        self.assertEqual(len(commands), 1)
        cmd = commands[0]
        self.assertEqual(cmd[cmd.index("--speedprobe") + 1], "100")
        self.assertEqual(cmd[cmd.index("--drilled") + 1], "1")
        self.assertEqual(cmd[cmd.index("--drill-domain") + 1], "1")
        self.assertEqual(cmd[cmd.index("--nostack") + 1], "1")
        self.assertNotIn("--moves", cmd)
        self.assertNotIn("--save", cmd)
        self.assertEqual([event["phase"] for event in events], ["running", "done"])
        self.assertTrue(any("[MOVE100][POLICY]" in line for line in logs))

    def test_no_timing_is_an_error(self):
        with patch.object(probe, "prerequisites"), patch.object(
                probe, "run_process", return_value=(0, "{}", "no probe\n")):
            with self.assertRaisesRegex(RuntimeError, "probeMs"):
                probe.calibrate({"board": {"rows": 24, "cols": 56}},
                                3, False, True, lambda _: None, lambda _: None,
                                lambda: False)

    def test_invalid_workers_fail(self):
        with self.assertRaises(ValueError):
            probe.calibrate({}, 2, False, True, lambda _: None,
                            lambda _: None, lambda: False)


    def test_native_error_reason_is_exposed(self):
        messages = []
        with patch.object(probe, "prerequisites"), patch.object(
                probe, "run_process", return_value=(
                    1, '{"id":1,"error":"Edge mount does not touch board edge"}',
                    "timing {\"error\":\"Edge mount\"}\n")):
            with self.assertRaisesRegex(RuntimeError, "Edge mount does not touch"):
                probe.calibrate(
                    {"board":{"rows":24,"cols":56}, "components":[],
                     "nets":[],"netAssignments":[]},
                    3, False, True, lambda x: None, messages.append,
                    lambda: False
                )
        self.assertTrue(any("[MOVE100][REJECTED INPUT]" in x for x in messages))
