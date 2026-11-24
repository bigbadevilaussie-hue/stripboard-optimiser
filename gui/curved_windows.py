"""Arcade-Mate-inspired frameless, rounded Arctic window chrome.

One presentation-only Qt event filter serves the main window, modal project
dialogs, message boxes and non-native file pickers. No routing logic is touched.
"""
from __future__ import annotations

from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QPainterPath, QRegion
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMainWindow,
    QToolButton, QWidget,
)


CORNER_RADIUS = 18
TITLE_HEIGHT = 36


class ArcticTitleBar(QWidget):
    """Compact replacement for the grey macOS title bar; keeps real controls."""

    def __init__(self, target):
        super().__init__(target)
        self.target = target
        self.setObjectName("arcticTitleBar")
        self.setFixedHeight(TITLE_HEIGHT)
        self._drag_offset = None
        self._system_drag = False

        row = QHBoxLayout(self)
        row.setContentsMargins(9, 2, 5, 2)
        row.setSpacing(6)
        self.heading = QLabel(target.windowTitle())
        self.heading.setObjectName("arcticWindowCaption")
        self.heading.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        row.addWidget(self.heading, 1)

        if isinstance(target, QMainWindow):
            minimize = self._button("—", "Minimise", "arcticMinimize")
            minimize.clicked.connect(target.showMinimized)
            row.addWidget(minimize)
            self.maximize = self._button("□", "Maximise / restore", "arcticMaximize")
            self.maximize.clicked.connect(self.toggle_maximize)
            row.addWidget(self.maximize)
        else:
            self.maximize = None

        close = self._button("×", "Close", "arcticClose")
        close.clicked.connect(target.close)
        row.addWidget(close)

    def _button(self, text, tooltip, name):
        button = QToolButton(self)
        button.setText(text)
        button.setToolTip(tooltip)
        button.setObjectName(name)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setFixedSize(29, 27)
        return button

    def toggle_maximize(self):
        if self.target.isMaximized():
            self.target.showNormal()
        else:
            self.target.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.target.frameGeometry().topLeft()
            self._system_drag = False
            handle = self.target.windowHandle()
            if handle is not None:
                try:
                    self._system_drag = bool(handle.startSystemMove())
                except (AttributeError, RuntimeError):
                    self._system_drag = False
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (self._drag_offset is not None and not self._system_drag
                and bool(event.buttons() & Qt.MouseButton.LeftButton)
                and not self.target.isMaximized()):
            self.target.move(event.globalPosition().toPoint() - self._drag_offset)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_offset = None
        self._system_drag = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if isinstance(self.target, QMainWindow) and event.button() == Qt.MouseButton.LeftButton:
            self.toggle_maximize()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)


class CurvedWindowManager(QObject):
    """Style newly shown top-level Qt windows, even standard message boxes."""

    def eventFilter(self, obj, event):
        if not isinstance(obj, (QMainWindow, QDialog)) or not obj.isWindow():
            return False

        kind = event.type()
        if kind in (QEvent.Type.Polish, QEvent.Type.Show):
            self.attach(obj)
        elif kind == QEvent.Type.Resize or kind == QEvent.Type.WindowStateChange:
            self.update_shape(obj)
        elif kind == QEvent.Type.WindowTitleChange:
            bar = getattr(obj, "_arctic_titlebar", None)
            if bar is not None:
                bar.heading.setText(obj.windowTitle())
        return False

    def attach(self, window):
        if getattr(window, "_arctic_titlebar", None) is not None:
            return

        if isinstance(window, QDialog) and window.layout() is None:
            # Qt's own QMessageBox/file dialog is sometimes polished before
            # its child layout exists; retry when the Show event arrives.
            return

        # Our own dialogs set this flag at construction. Standard QMessageBox
        # and non-native QFileDialog instances may reach Show before styling.
        # Re-show those once after changing flags so Qt cannot leave them hidden.
        if not (window.windowFlags() & Qt.WindowType.FramelessWindowHint):
            showing = window.isVisible()
            window.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
            if showing:
                QTimer.singleShot(0, window.show)

        bar = ArcticTitleBar(window)
        window._arctic_titlebar = bar

        if isinstance(window, QMainWindow):
            window.setMenuWidget(bar)
        else:
            content_layout = window.layout()
            left, top, right, bottom = content_layout.getContentsMargins()
            content_layout.setContentsMargins(left, top + TITLE_HEIGHT, right, bottom)
            bar.show()
            self.position_dialog_bar(window)

        self.update_shape(window)

    def position_dialog_bar(self, dialog):
        bar = getattr(dialog, "_arctic_titlebar", None)
        if bar is not None and isinstance(dialog, QDialog):
            bar.setGeometry(10, 4, max(80, dialog.width() - 20), TITLE_HEIGHT)
            bar.raise_()

    def update_shape(self, window):
        if window.isMaximized() or window.isFullScreen():
            window.clearMask()
            return
        width, height = window.width(), window.height()
        if width <= 1 or height <= 1:
            return
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, width, height),
                            CORNER_RADIUS, CORNER_RADIUS)
        window.setMask(QRegion(path.toFillPolygon().toPolygon()))
        if isinstance(window, QDialog):
            self.position_dialog_bar(window)


def install_curved_windows(app: QApplication):
    """Retain the manager on the QApplication to keep the event filter alive."""
    manager = getattr(app, "_arctic_window_manager", None)
    if manager is None:
        manager = CurvedWindowManager(app)
        app._arctic_window_manager = manager
        app.installEventFilter(manager)
    return manager
