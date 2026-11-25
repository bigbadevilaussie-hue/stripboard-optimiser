"""Resolve shipped tools and writable paths without Finder's shell PATH."""
from pathlib import Path
import sys
import shutil


def bundled_root():
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return None


def tool_path(name):
    root = bundled_root()
    if root is not None:
        path = root / "renderer-runtime" / name
        if not path.is_file():
            raise RuntimeError(f"Standalone app is missing bundled tool: {path}")
        return str(path)
    return shutil.which(name)


def node_command():
    # Preserve the source-mode CLI spelling and subprocess test contracts.
    if bundled_root() is None:
        return "node"
    return tool_path("node")


def work_root():
    if bundled_root() is not None:
        return Path.home() / "Library" / "Application Support" / "StripSolve" / "Work"
    return Path(__file__).resolve().parents[1] / "Work"
