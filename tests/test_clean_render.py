"""Normal and lock-review rendering must not paint physical-warning boxes."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from render.standalone_bridge import render_project

WEB = '<svg xmlns="http://www.w3.org/2000/svg" data-render-style="web" viewBox="0 0 180 180"><g data-web-cut="1"/>{selected}</svg>'
PRINT = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 180 180"></svg>'


class CleanRenderTests(unittest.TestCase):
    def test_no_warning_overlays_and_lock_selection_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "project.json"
            output = root / "output"
            project = {"board": {"rows": 3, "cols": 3, "cuts": [], "wires": []},
                       "components": [], "componentDefs": [], "nets": [], "netAssignments": []}
            source.write_text(json.dumps(project))

            def run(args):
                selected = '<g data-web-selected="1"/>' if "--highlight" in args else ""
                top = WEB.format(selected=selected) if "--web-preview" in args else PRINT
                (output / "board-top.svg").write_text(top)
                (output / "board-copper.svg").write_text(PRINT)
                return subprocess.CompletedProcess(args, 0, "")

            with patch("render.standalone_bridge.ensure_renderer", return_value=root / "cli.js"), \
                 patch("render.standalone_bridge._bundled_runtime", return_value=None), \
                 patch("render.standalone_bridge._renderer_input", return_value=project), \
                 patch("render.standalone_bridge._run", side_effect=run), \
                 patch("render.standalone_bridge.add_assumed_contact_highlights") as warnings:
                top, copper, _ = render_project(source, output, web_preview=True)
                self.assertNotIn("data-web-selected", top)
                self.assertIn("data-web-cut", top)
                top, copper, _ = render_project(source, output, web_preview=True,
                                               highlight_component_id="part")
                self.assertIn('data-web-selected="1"', top)
                render_project(source, output)
                warnings.assert_not_called()
