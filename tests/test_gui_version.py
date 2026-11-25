"""GUI release metadata is independent of the headless repo milestone."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GuiVersionTests(unittest.TestCase):
    def test_gui_version_is_independent_and_well_formed(self):
        gui_version = (ROOT / "gui" / "VERSION").read_text(encoding="utf-8").strip()
        root_version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
        self.assertRegex(gui_version, r"^2\.\d{2}$")
        self.assertNotEqual(gui_version, root_version)

    def test_window_reads_gui_version_file(self):
        source = (ROOT / "gui" / "main.py").read_text(encoding="utf-8")
        self.assertIn('REPO_ROOT / "gui" / "VERSION"', source)
        self.assertIn('self.setWindowTitle("StripSolve")', source)
        self.assertIn('QLabel(f"Rev {GUI_VERSION}")', source)
        self.assertIn('addPermanentWidget(self.revision_label)', source)
        self.assertIn('self.log_line(f"StripSolve {GUI_VERSION}', source)


if __name__ == "__main__":
    unittest.main()
