"""StripSolve branded Qt icons and start-up splash.

SVG masters come from gui.icon_art and can be exported with:
    python3 tools/build_icons.py

Existing artwork is never overwritten by normal GUI launch. The renderer has
an in-memory fallback if its installation directory is read-only.
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray, Qt, QTimer, Signal, QSize
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from gui.icon_art import ICON_KEYS, app_icon_svg, icon_svg

ASSETS_DIR = Path(__file__).resolve().parent / "assets"
ICONS_DIR = Path(__file__).resolve().parent / "icons"
BUTTON_ICON_FILES = {key: f"{key}.svg" for key in ICON_KEYS}


def _rasterize(svg: str, size: int) -> QImage:
    if size < 1 or size > 2048:
        raise ValueError("Icon size outside supported range")
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    if not renderer.isValid():
        raise ValueError("Invalid StripSolve SVG")
    image = QImage(size, size, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        renderer.render(painter)
    finally:
        painter.end()
    return image


def export_assets(*, force: bool = False, toolbar_png: bool = False) -> list[Path]:
    """Write all icon masters and the 1024px app PNG; never overwrite by default."""
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    created = []
    app_svg = ASSETS_DIR / "app_icon.svg"
    if force or not app_svg.is_file():
        app_svg.write_text(app_icon_svg(), encoding="utf-8")
        created.append(app_svg)
    app_png = ASSETS_DIR / "app_icon.png"
    if force or not app_png.is_file():
        if not _rasterize(app_svg.read_text(encoding="utf-8"), 1024).save(
            str(app_png), "PNG"
        ):
            raise OSError(f"Unable to save application icon: {app_png}")
        created.append(app_png)
    for key in ICON_KEYS:
        target = ICONS_DIR / BUTTON_ICON_FILES[key]
        if force or not target.is_file():
            target.write_text(icon_svg(key), encoding="utf-8")
            created.append(target)
        if toolbar_png:
            png = target.with_suffix(".png")
            if force or not png.is_file():
                if not _rasterize(target.read_text(encoding="utf-8"), 48).save(
                    str(png), "PNG"
                ):
                    raise OSError(f"Unable to save toolbar icon: {png}")
                created.append(png)
    return created


def load_app_icon() -> QIcon:
    icon_path = ASSETS_DIR / "app_icon.png"
    if icon_path.is_file():
        icon = QIcon(str(icon_path))
        if not icon.isNull():
            return icon
    svg_path = ASSETS_DIR / "app_icon.svg"
    if svg_path.is_file():
        svg = svg_path.read_text(encoding="utf-8")
    else:
        svg = app_icon_svg()
    return QIcon(QPixmap.fromImage(_rasterize(svg, 1024)))


def load_button_icon(key: str) -> QIcon:
    filename = BUTTON_ICON_FILES.get(key)
    if filename is None:
        return QIcon()
    file = ICONS_DIR / filename
    if file.is_file():
        icon = QIcon(str(file))
        if not icon.isNull():
            return icon
    # Works in read-only packaged apps as well as fresh source checkouts.
    return QIcon(QPixmap.fromImage(_rasterize(icon_svg(key), 96)))


class StripSolveSplash(QWidget):
    """Short, skippable application splash; does NOT simulate a solver run."""

    finished = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(
            parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(540, 340)
        self._complete = False
        outer = QVBoxLayout(self)
        outer.setContentsMargins(8, 8, 8, 8)
        card = QFrame()
        card.setObjectName("StripSolveSplashCard")
        card.setStyleSheet("""
            QFrame#StripSolveSplashCard {
                background: #f4f9fc;
                border: 2px solid #4e9bc3;
                border-radius: 18px;
            }
            QLabel#StripSolveSplashTitle {
                color: #0f2537;
                font-size: 28px;
                font-weight: 800;
            }
            QLabel#StripSolveSplashSubtitle {
                color: #284b67;
                font-size: 13px;
                font-weight: 650;
            }
            QLabel#StripSolveSplashStatus {
                color: #234561;
                font-size: 12px;
                font-weight: 600;
            }
            QProgressBar {
                color: #0f2537;
                background: #dbeefa;
                border: 1px solid #7faeca;
                border-radius: 7px;
                min-height: 17px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #19a8c6;
                border-radius: 6px;
            }
        """)
        outer.addWidget(card)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(11)
        top_row = QHBoxLayout()
        icon = QLabel()
        icon.setPixmap(load_app_icon().pixmap(QSize(88, 88)))
        top_row.addWidget(icon)
        headings = QVBoxLayout()
        title = QLabel("STRIPSOLVE")
        title.setObjectName("StripSolveSplashTitle")
        subtitle = QLabel("Stripboard Layout & Routing Optimizer")
        subtitle.setObjectName("StripSolveSplashSubtitle")
        subtitle.setWordWrap(True)
        headings.addWidget(title)
        headings.addWidget(subtitle)
        top_row.addLayout(headings, 1)
        layout.addLayout(top_row)
        layout.addStretch(1)
        self.status_label = QLabel("Starting the desktop interface · no solver running")
        self.status_label.setObjectName("StripSolveSplashStatus")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        layout.addWidget(self.progress)
        bottom = QHBoxLayout()
        note = QLabel("Arctic Ice + Colourburst")
        note.setStyleSheet("color: #536f88; font-size: 11px;")
        bottom.addWidget(note)
        bottom.addStretch()
        skip = QPushButton("Skip")
        skip.setObjectName("splashSkipButton")
        skip.clicked.connect(self._finish)
        bottom.addWidget(skip)
        layout.addLayout(bottom)
        self._steps = (
            (35, "Loading StripSolve interface..."),
            (70, "Preparing board preview controls..."),
            (100, "Ready · project not yet loaded"),
        )
        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    def start_demo(self, interval_ms: int = 300):
        self.show()
        self._timer.start(interval_ms)

    def set_progress(self, value: int, message: str | None = None):
        self.progress.setValue(max(0, min(100, value)))
        if message:
            self.status_label.setText(message)
        if value >= 100:
            QTimer.singleShot(150, self._finish)

    def _advance(self):
        if self._complete:
            return
        if self._step >= len(self._steps):
            self._finish()
            return
        value, message = self._steps[self._step]
        self._step += 1
        self.set_progress(value, message)

    def _finish(self):
        if self._complete:
            return
        self._complete = True
        self._timer.stop()
        self.finished.emit()
        self.close()
