"""Frozen runtime paths are explicit and never use the developer checkout."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from gui import runtime_paths

class RuntimePathsTests(unittest.TestCase):
    def test_source_paths(self):
        with patch.object(runtime_paths.sys, "frozen", False, create=True):
            self.assertEqual(runtime_paths.node_command(), "node")
            self.assertEqual(runtime_paths.work_root(), Path(__file__).resolve().parents[1] / "Work")

    def test_packaged_tools_and_writable_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tools = root / "renderer-runtime"
            tools.mkdir()
            for name in ("node", "rsvg-convert"):
                (tools / name).touch()
            with patch.object(runtime_paths.sys, "frozen", True, create=True), \
                 patch.object(runtime_paths.sys, "_MEIPASS", str(root), create=True):
                self.assertEqual(runtime_paths.node_command(), str(tools / "node"))
                self.assertEqual(runtime_paths.tool_path("rsvg-convert"), str(tools / "rsvg-convert"))
                self.assertEqual(runtime_paths.work_root(), Path.home() / "Library" / "Application Support" / "StripSolve" / "Work")
                (tools / "node").unlink()
                with self.assertRaisesRegex(RuntimeError, "missing bundled tool"):
                    runtime_paths.node_command()
