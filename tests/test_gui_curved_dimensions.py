"""Rounded frameless chrome and wheel-free validated dimensions regression tests."""
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication, QDialogButtonBox, QLineEdit, QSpinBox, QMessageBox
    from gui.arctic_theme import apply_arctic_theme
    from gui.main import BoardSizeDialog, RoutingRulesDialog, PassOneDialog, PassTwoDialog, LockDialog, RouteMateWindow
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

    def test_dimensions_are_compact_and_accept_999(self):
        dialog = BoardSizeDialog({"rows": 24, "cols": 56})
        try:
            field = dialog.actual_rows.entry
            self.assertEqual(field.validator().top(), 999)
            self.assertEqual(field.maximumWidth(), 64)
            field.setText("999")
            self.assertTrue(field.hasAcceptableInput())
            self.assertEqual(dialog.values()["actualRows"], 999)
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
            PassTwoDialog(__import__("pathlib").Path("/tmp/results.csv"), 170),
            LockDialog({"id": "U1", "label": "Test"}, 1, 1),
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

    def test_standard_message_box_uses_the_same_rounded_chrome(self):
        dialog = QMessageBox()
        dialog.setWindowTitle("Test warning")
        dialog.setText("This is only a presentation test.")
        try:
            dialog.show()
            self.app.processEvents()
            self.assertTrue(
                bool(dialog.windowFlags() & Qt.WindowType.FramelessWindowHint)
            )
            self.assertIsNotNone(getattr(dialog, "_arctic_titlebar", None))
        finally:
            dialog.close()

    def test_shared_title_bar_is_added_on_show(self):
        dialog = BoardSizeDialog({"rows": 24, "cols": 56})
        try:
            dialog.show()
            self.app.processEvents()
            self.assertIsNotNone(getattr(dialog, "_arctic_titlebar", None))
            self.assertEqual(dialog._arctic_titlebar.heading.text(), "Board dimensions")
            from PySide6.QtWidgets import QLabel
            icon = dialog._arctic_titlebar.findChild(QLabel, "arcticPopupIcon")
            self.assertIsNotNone(icon)
            self.assertFalse(icon.pixmap().isNull())
        finally:
            dialog.close()


if __name__ == "__main__":
    unittest.main()
