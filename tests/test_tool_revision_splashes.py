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

    def test_compiled_renderers_print_revision_before_usage(self):
        base = ROOT / "src/frontend/standalone-renderer/dist/standalone-renderer"
        for tool, entry in (("RENDER", base / "cli.js"),
                            ("SCHEMATIC", base / "schematic/cli.js")):
            with self.subTest(tool=tool):
                if not entry.is_file():
                    self.skipTest("Compiled renderer dist not installed")
                run = subprocess.run(["node", str(entry)],
                                     capture_output=True, text=True, check=False)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(run.stdout, "")
                self.assertIn(f"[TOOL-REVISION] tool={tool}", run.stderr)
                self.assertIn("build_sha256=", run.stderr)

    def test_gui_reports_cli_revisions(self):
        code = (ROOT / "gui/main.py").read_text()
        self.assertIn('self._show_tool_revision(_renderer_log, "RENDER")', code)
        self.assertIn('self._show_tool_revision(diagnostic, "SCHEMATIC")', code)
        self.assertIn('GUI_GIT_REVISION', code)
        self.assertNotIn("QSplashScreen", code)
        self.assertNotIn("_display_tool_splash", code)
        handler = code.split("    def _show_tool_revision(", 1)[1].split("    def _log_handoff(", 1)[0]
        self.assertIn("self.log_line(revision)", handler)
        self.assertNotIn("statusBar()", handler)
        # GUI version advances independently of the repository release; 2.04
        # was a stale snapshot, not a renderer provenance requirement.
        gui_version = (ROOT / "gui/VERSION").read_text().strip()
        self.assertRegex(gui_version, r"^2\.\d{2}$")
        self.assertGreaterEqual(int(gui_version.split(".")[1]), 4)


if __name__ == "__main__":
    unittest.main()
