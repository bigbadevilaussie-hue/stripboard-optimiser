"""Standalone schematic bridge: no solver and no writes beside original JSON."""
import copy
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from render.schematic_bridge import render_schematic_data


class SchematicBridgeTests(unittest.TestCase):
    def test_uses_existing_compiled_cli_with_unchanged_project(self):
        project = {
            "name": "MOTOEX", "components": [{"id": "C1", "schematicPos": {"x": 42, "y": 16}}],
            "nets": [{"id": "n1"}], "netAssignments": [],
            "schematicWires": [{"start": {"x": 0, "y": 0}, "end": {"x": 42, "y": 16}}],
            "board": {"rows": 24, "cols": 56},
        }
        before = copy.deepcopy(project)
        schematic = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 50 50"></svg>'
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            compiled = root / "dist" / "standalone-renderer"
            (compiled / "schematic").mkdir(parents=True)
            (compiled / "cli.js").write_text("board stub", encoding="utf-8")
            (compiled / "schematic" / "cli.js").write_text("schematic stub", encoding="utf-8")

            def fake_run(args):
                self.assertEqual(args[0], "node")
                self.assertEqual(args[1], str(compiled / "schematic" / "cli.js"))
                self.assertEqual(args[3], "--output")
                self.assertEqual(json.loads(Path(args[2]).read_text(encoding="utf-8")), before)
                (Path(args[4]) / "schematic.svg").write_text(schematic, encoding="utf-8")
                return subprocess.CompletedProcess(args, 0, "Saved schematic.svg")

            with patch("render.schematic_bridge.ensure_renderer", return_value=compiled / "cli.js"), \
                 patch("render.schematic_bridge._run", side_effect=fake_run) as run:
                svg, log = render_schematic_data(project)
            self.assertEqual(svg, schematic)
            self.assertEqual(log, "Saved schematic.svg")
            self.assertEqual(run.call_count, 1)
            self.assertEqual(project, before)
            self.assertEqual(
                sorted(p.name for p in root.iterdir()), ["dist"]
            )

    def test_reports_unbuilt_cli_without_calling_runner(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("render.schematic_bridge.ensure_renderer",
                       return_value=Path(directory) / "standalone-renderer" / "cli.js"), \
                 patch("render.schematic_bridge._run") as run:
                with self.assertRaisesRegex(RuntimeError, "schematic renderer is missing"):
                    render_schematic_data({"components": []})
                run.assert_not_called()

    def test_failure_does_not_return_a_fake_schematic(self):
        with tempfile.TemporaryDirectory() as directory:
            compiled = Path(directory) / "standalone-renderer"
            (compiled / "schematic").mkdir(parents=True)
            (compiled / "schematic" / "cli.js").write_text("stub", encoding="utf-8")
            with patch("render.schematic_bridge.ensure_renderer",
                       return_value=compiled / "cli.js"), \
                 patch("render.schematic_bridge._run",
                       return_value=subprocess.CompletedProcess([], 1, "bad render")):
                with self.assertRaisesRegex(RuntimeError, "bad render"):
                    render_schematic_data({"components": []})


if __name__ == "__main__":
    unittest.main()
