"""Arctic Ice appearance regression tests; no solver or project mutation."""
import os
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import (
        QApplication, QDialog, QDialogButtonBox, QLabel, QPushButton,
        QCheckBox, QRadioButton, QPlainTextEdit, QComboBox, QSpinBox,
        QFileDialog, QToolButton,
    )
    from gui.arctic_theme import COLORS, STYLESHEET, apply_arctic_theme
    from gui.main import RoutingRulesDialog, PassOneDialog, PassTwoDialog
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 unavailable")
class ArcticIceThemeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.family = apply_arctic_theme(cls.app)

    def test_one_font_family_in_main_widgets_and_popups(self):
        widgets = [
            QDialog(), QLabel("text"), QPushButton("Press"),
            QCheckBox("Agree"), QRadioButton("Choice"),
            QPlainTextEdit(), QComboBox(), QSpinBox(),
            RoutingRulesDialog(),
            PassOneDialog({"ms_per_decode": 0.2}),
            PassTwoDialog(Path("/tmp/results.csv"), 170),
        ]
        try:
            for widget in widgets:
                self.assertEqual(widget.font().family(), self.family)
        finally:
            for widget in widgets:
                widget.close()

    def test_light_palette_and_consistent_colours(self):
        p = self.app.palette()
        self.assertEqual(
            p.color(QPalette.ColorRole.Window).name(),
            QColor(COLORS["ice"]).name(),
        )
        self.assertEqual(
            p.color(QPalette.ColorRole.Highlight).name(),
            QColor(COLORS["blue"]).name(),
        )
        self.assertIn("QMessageBox", STYLESHEET)
        self.assertIn("QFileDialog", STYLESHEET)
        self.assertIn("QToolBar QToolButton:checked", STYLESHEET)
        self.assertIn("QPushButton#nextActionButton", STYLESHEET)

    def test_file_dialog_navigation_icons_have_room(self):
        for mode in (QFileDialog.AcceptMode.AcceptOpen, QFileDialog.AcceptMode.AcceptSave):
            with self.subTest(mode=mode):
                dialog = QFileDialog()
                try:
                    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
                    dialog.setAcceptMode(mode)
                    dialog.ensurePolished()
                    for name in ("backButton", "forwardButton", "toParentButton",
                                 "newFolderButton", "listModeButton", "detailModeButton"):
                        button = dialog.findChild(QToolButton, name)
                        self.assertIsNotNone(button, name)
                        button.ensurePolished()
                        self.assertFalse(button.icon().isNull(), name)
                        self.assertGreaterEqual(button.iconSize().width(), 22, name)
                        self.assertGreaterEqual(button.iconSize().height(), 22, name)
                        self.assertGreaterEqual(button.sizeHint().width(), button.iconSize().width() + 8, name)
                        self.assertGreaterEqual(button.sizeHint().height(), button.iconSize().height() + 8, name)
                finally:
                    dialog.close()

    def test_confirmation_buttons_are_only_semantic_green_actions(self):
        dialogs = [
            RoutingRulesDialog(),
            PassOneDialog({"ms_per_decode": 0.2}),
            PassTwoDialog(Path("/tmp/results.csv"), 170),
        ]
        try:
            for dialog in dialogs:
                button = dialog.findChild(QDialogButtonBox).button(
                    QDialogButtonBox.StandardButton.Ok
                )
                self.assertEqual(button.objectName(), "nextActionButton")
        finally:
            for dialog in dialogs:
                dialog.close()


if __name__ == "__main__":
    unittest.main()
