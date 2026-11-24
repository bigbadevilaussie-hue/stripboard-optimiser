"""Renderer revision splash must use a valid PySide6 constructor."""
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

    def test_revision_splash_constructor(self):
        window = RouteMateWindow()
        try:
            window._display_tool_splash("RENDER", "[TOOL-REVISION] tool=RENDER test")
            self.assertIsNotNone(window._active_tool_splash)
        finally:
            if window._active_tool_splash is not None:
                window._active_tool_splash.close()
            window.close()


if __name__ == "__main__":
    unittest.main()
