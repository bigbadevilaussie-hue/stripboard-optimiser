"""Renderer revision provenance must be log-only: no Qt popup or status override."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
try:
    from PySide6.QtWidgets import QApplication
    from gui.main import RouteMateWindow
except ImportError:
    QApplication = None
    RouteMateWindow = None


@unittest.skipIf(QApplication is None, "PySide6 unavailable")
class RendererSplashSignatureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_renderer_revisions_are_log_only(self):
        window = RouteMateWindow()
        try:
            window.statusBar().showMessage("Existing status")
            before = set(QApplication.topLevelWidgets())
            for tool in ("RENDER", "SCHEMATIC"):
                stamp = f"[TOOL-REVISION] tool={tool} test"
                window._show_tool_revision(stamp, tool)
                window._show_tool_revision(stamp, tool)
                self.assertEqual(window.log.toPlainText().count(stamp), 1)
            QApplication.processEvents()
            self.assertEqual(set(QApplication.topLevelWidgets()), before)
            self.assertEqual(window.statusBar().currentMessage(), "Existing status")
            self.assertFalse(hasattr(window, "_display_tool_splash"))
            self.assertFalse(hasattr(window, "_active_tool_splash"))
        finally:
            window.close()


if __name__ == "__main__":
    unittest.main()
