"""Executable provenance regressions: splash must not corrupt solver JSON stdout."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ToolRevisionSplashTests(unittest.TestCase):
    def test_solver_splash_is_stderr_only(self):
        helper = ROOT / "src/frontend/tests/solver/toolIdentity.js"
        script = (
            "require(" + repr(str(helper)).replace("'", '"') + ").printSolverSplash(" +
            repr(str(ROOT / "src/frontend/tests/solver/v5Solve.js")).replace("'", '"') + ")"
        )
        run = subprocess.run(["node", "-e", script],
                             capture_output=True, text=True, check=False)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, "")
        self.assertIn("STRIPBOARD · SOLVER", run.stderr)
        self.assertIn("[TOOL-REVISION] tool=SOLVER", run.stderr)
        self.assertIn("program_sha256=", run.stderr)

    def test_both_renderers_call_shared_splash(self):
        source = ROOT / "src/frontend/standalone-renderer"
        self.assertIn('printRendererSplash("RENDER")', (source / "cli.ts").read_text())
        self.assertIn('printRendererSplash("SCHEMATIC")', (source / "schematic/cli.ts").read_text())
        shared = (source / "toolSplash.ts").read_text()
        self.assertIn("buildSha(dist)", shared)
        self.assertIn("process.stderr.write(", shared)

    def test_gui_reports_cli_revisions(self):
        code = (ROOT / "gui/main.py").read_text()
        self.assertIn('self._show_tool_revision(_renderer_log, "RENDER")', code)
        self.assertIn('self._show_tool_revision(diagnostic, "SCHEMATIC")', code)
        self.assertIn('GUI_GIT_REVISION', code)
        self.assertIn("QSplashScreen", code)
        self.assertIn("self._display_tool_splash(tool, revision)", code)
        self.assertEqual((ROOT / "gui/VERSION").read_text().strip(), "2.04")


if __name__ == "__main__":
    unittest.main()
