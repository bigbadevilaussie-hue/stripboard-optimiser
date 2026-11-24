"""Unified Arctic Ice + Colourburst visual theme for every Route-O-Matic Qt window.

Only presentation: no solver, board, workflow, file or routing behaviour lives here.
Fonts inherit from QApplication so dialogs, tooltips, buttons and the main window agree.
"""
from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtWidgets import QApplication
from gui.curved_windows import install_curved_windows


COLORS = {
    "ice": "#edf6fd",
    "snow": "#ffffff",
    "panel": "#f7fbff",
    "mist": "#e9f3fc",
    "line": "#cbddec",
    "ink": "#19334d",
    "muted": "#536f88",
    "blue": "#257ac2",
    "cyan": "#13a9d2",
    "teal": "#168d95",
    "lime": "#9acb33",
    "green": "#159d6b",
    "amber": "#c77916",
    "coral": "#ce5265",
    "gold": "#cf9c30",
}

# Single source of truth for widgets shown by the main window and modal dialogs.
# Semantic green is reserved for affirmative GO / next-action buttons; normal
# selection (tabs, toolbar view modes, text selection) remains blue.
STYLESHEET = """
QWidget {
    color: #19334d;
}
QMainWindow, QDialog, QMessageBox, QFileDialog {
    background-color: #edf6fd;
    border-radius: 18px;
}
QWidget#arcticTitleBar {
    background-color: #e1f0fb;
    border-bottom: 1px solid #bbd8ec;
    border-radius: 8px;
}
QLabel#arcticWindowCaption {
    color: #245476;
    font-size: 12px;
    font-weight: 700;
    padding-left: 4px;
}
QToolButton#arcticClose, QToolButton#arcticMinimize,
QToolButton#arcticMaximize {
    background: transparent;
    color: #3b6682;
    border: 0;
    border-radius: 7px;
    padding: 2px;
    font-size: 18px;
    min-height: 0;
}
QToolButton#arcticClose:hover {
    background: #ffe5e9;
    color: #b43352;
}
QToolButton#arcticMinimize:hover,
QToolButton#arcticMaximize:hover {
    background: #cbe7fa;
    color: #215e8e;
}
QLineEdit#dimensionEntry {
    background: white;
    border: 1px solid #bcd4e8;
    border-radius: 8px;
    padding: 7px 9px;
    font-weight: 650;
}
QLabel#dimensionCheck {
    color: #168d95;
    font-weight: 800;
    font-size: 16px;
}
QLabel {
    background: transparent;
}
QGroupBox {
    background-color: #ffffff;
    border: 1px solid #cbddec;
    border-radius: 11px;
    margin-top: 15px;
    padding: 11px 10px 10px 10px;
    font-weight: 650;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
    color: #255778;
}
QPushButton, QToolButton {
    background-color: #ffffff;
    border: 1px solid #bcd4e8;
    border-radius: 9px;
    padding: 8px 13px;
    color: #1f5279;
    font-weight: 650;
    min-height: 20px;
}
QPushButton:hover, QToolButton:hover {
    background-color: #e8f7ff;
    border-color: #50b5dc;
    color: #14446c;
}
QPushButton:pressed, QToolButton:pressed {
    background-color: #cfeafb;
    border-color: #257ac2;
}
QPushButton:focus, QToolButton:focus {
    border: 2px solid #257ac2;
}
QPushButton:disabled, QToolButton:disabled {
    background-color: #eef3f8;
    border-color: #d9e5ee;
    color: #90a4b5;
}
QPushButton:checked, QToolButton:checked {
    background-color: #dceffc;
    border-color: #6aaddc;
    color: #1a5b92;
}
QPushButton#nextActionButton {
    background-color: #159d6b;
    border-color: #0e895c;
    color: white;
    font-weight: 750;
}
QPushButton#nextActionButton:hover {
    background-color: #12ad73;
    border-color: #0b885a;
}
QPushButton#nextActionButton:pressed {
    background-color: #117c56;
}
QPushButton#nextActionButton:disabled {
    background-color: #e9f3ed;
    border-color: #cbded4;
    color: #8da89b;
}
QToolBar {
    background-color: #f7fbff;
    border: 0;
    border-bottom: 1px solid #cbddec;
    padding: 9px;
    spacing: 8px;
    min-height: 52px;
}
QToolBar QToolButton {
    background-color: #ffffff;
    border: 1px solid #bfd7e9;
    border-radius: 9px;
    padding: 9px 12px;
}
QToolBar QToolButton:checked {
    background-color: #dceffc;
    border-color: #6aaddc;
    color: #1a5b92;
}
QToolBar::separator {
    background-color: #cfdfec;
    width: 1px;
    margin: 6px 5px;
}
QTabWidget::pane {
    background-color: #f7fbff;
    border: 1px solid #cfdfec;
    border-radius: 10px;
}
QTabBar::tab {
    background-color: #e6f0f9;
    border: 1px solid #d5e4ef;
    border-bottom: 0;
    color: #57738b;
    padding: 10px 18px;
    margin-right: 3px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    font-weight: 650;
}
QTabBar::tab:selected {
    background-color: #ffffff;
    border-color: #9cc6e6;
    color: #2366a1;
}
QTabBar::tab:hover:!selected {
    background-color: #eff9ff;
    color: #1e699e;
}
QLineEdit, QPlainTextEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox,
QListView, QTreeView, QTableView {
    background-color: #ffffff;
    color: #19334d;
    border: 1px solid #c4d8e9;
    border-radius: 8px;
    padding: 6px 9px;
    selection-background-color: #257ac2;
    selection-color: #ffffff;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus,
QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #3e9ed2;
}
QComboBox::drop-down {
    border: 0;
    width: 24px;
}
QComboBox QAbstractItemView {
    background-color: #ffffff;
    color: #19334d;
    border: 1px solid #a9cfe7;
    selection-background-color: #dceffc;
    selection-color: #164f7f;
    padding: 5px;
}
QCheckBox, QRadioButton {
    spacing: 9px;
    padding: 4px 2px;
    color: #213d57;
}
QCheckBox:disabled, QRadioButton:disabled {
    color: #94a7b8;
}
QProgressBar {
    background-color: #e2edf7;
    color: #234a69;
    border: 1px solid #d1e1ee;
    border-radius: 7px;
    text-align: center;
    min-height: 13px;
}
QProgressBar::chunk {
    background-color: #17a6c8;
    border-radius: 6px;
}
QStatusBar {
    background-color: #e4f0fa;
    color: #365c7a;
    border-top: 1px solid #cbddec;
}
QStatusBar::item {
    border: none;
}
QSplitter::handle {
    background-color: #dceaf5;
}
QScrollBar:vertical {
    background-color: #f1f7fd;
    width: 11px;
    margin: 1px;
}
QScrollBar::handle:vertical {
    background-color: #b4cedf;
    border-radius: 5px;
    min-height: 28px;
}
QScrollBar:horizontal {
    background-color: #f1f7fd;
    height: 11px;
    margin: 1px;
}
QScrollBar::handle:horizontal {
    background-color: #b4cedf;
    border-radius: 5px;
    min-width: 28px;
}
QScrollBar::add-line, QScrollBar::sub-line {
    width: 0;
    height: 0;
}
QMenu, QToolTip {
    background-color: #ffffff;
    color: #19334d;
    border: 1px solid #bed6e8;
    padding: 5px;
}
QMenu::item {
    padding: 6px 20px;
}
QMenu::item:selected {
    background-color: #dceffc;
    color: #1a5b92;
}
"""


def apply_arctic_theme(app: QApplication) -> str:
    """Apply one font and a light palette to ALL Qt windows and modal dialogs."""
    app.setStyle("Fusion")

    available = set(QFontDatabase.families())
    family = next(
        (name for name in ("Avenir Next", "Inter", "Helvetica Neue", "Arial")
         if name in available),
        app.font().family(),
    )
    font = QFont(family, 11)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["ice"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["ink"]))
    palette.setColor(QPalette.ColorRole.Base, QColor(COLORS["snow"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS["panel"]))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["ink"]))
    palette.setColor(QPalette.ColorRole.Button, QColor(COLORS["snow"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["ink"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["blue"]))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORS["snow"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLORS["snow"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(COLORS["ink"]))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLORS["muted"]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor("#91a5b7"))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
    install_curved_windows(app)
    return family
