"""Rounded frameless chrome and wheel-free validated dimensions regression tests."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLineEdit, QSpinBox
    from gui.arctic_theme import apply_arctic_theme
    from gui.main import BoardSizeDialog, RoutingRulesDialog, PassOneDialog, RouteMateWindow
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None, "PySide6 not installed")
class CurvedDimensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        apply_arctic_theme(cls.app)

    def test_all_dimensions_use_text_boxes_not_spin_wheels(self):
        dialog = BoardSizeDialog({"rows": 24, "cols": 56})
        try:
            self.assertFalse(dialog.findChildren(QSpinBox))
            for field in (dialog.actual_rows, dialog.actual_cols,
                          dialog.preferred_rows, dialog.preferred_cols):
                self.assertIsInstance(field.entry, QLineEdit)
                self.assertTrue(field.entry.hasAcceptableInput())
                self.assertEqual(field.check.text(), "✓")
            self.assertEqual(dialog.values()["actualRows"], 24)
            self.assertEqual(dialog.values()["wantedCols"], 56)
        finally:
            dialog.close()

    def test_bad_values_have_red_checker_and_cannot_be_submitted(self):
        dialog = BoardSizeDialog({"rows": 24, "cols": 56})
        try:
            ok = dialog.findChild(QDialogButtonBox).button(
                QDialogButtonBox.StandardButton.Ok
            )
            self.assertTrue(ok.isEnabled())
            dialog.actual_rows.entry.setText("")
            self.assertFalse(ok.isEnabled())
            self.assertEqual(dialog.actual_rows.check.text(), "✕")
            with self.assertRaises(ValueError):
                dialog.values()
            dialog.actual_rows.entry.setText("0")
            self.assertFalse(ok.isEnabled())
            dialog.actual_rows.entry.setText("24")
            self.assertTrue(ok.isEnabled())
            dialog.preferred_cols.entry.setText("57")
            self.assertFalse(ok.isEnabled())
            self.assertEqual(dialog.preferred_cols.check.text(), "✕")
            dialog.cols_mode.setCurrentIndex(dialog.cols_mode.findData("max"))
            self.assertTrue(ok.isEnabled())
            self.assertEqual(dialog.values()["wantedCols"], 57)
        finally:
            dialog.close()

    def test_dialog_and_main_window_have_frameless_flags(self):
        widgets = [
            BoardSizeDialog({"rows": 24, "cols": 56}),
            RoutingRulesDialog(),
            PassOneDialog({"ms_per_decode": 0.2}),
            RouteMateWindow(),
        ]
        try:
            for widget in widgets:
                self.assertTrue(
                    bool(widget.windowFlags() & Qt.WindowType.FramelessWindowHint)
                )
        finally:
            for widget in widgets:
                widget.close()

    def test_shared_title_bar_is_added_on_show(self):
        dialog = BoardSizeDialog({"rows": 24, "cols": 56})
        try:
            dialog.show()
            self.app.processEvents()
            self.assertIsNotNone(getattr(dialog, "_arctic_titlebar", None))
            self.assertEqual(dialog._arctic_titlebar.heading.text(), "Board dimensions")
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
