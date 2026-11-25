"""StripSolve branded Qt icons and start-up splash.

SVG masters come from gui.icon_art and can be exported with:
    python3 tools/build_icons.py

The 1024px approved app PNG is never overwritten automatically. Toolbar SVG
masters refresh once per visual-design revision, while subsequent local custom
SVG edits are preserved. Read-only installs fall back to in-memory vector art.
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
ARTWORK_REVISION = "copper-traces-v3"
ARTWORK_MARKER = ".stripsolve_artwork_revision"


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
    """Refresh shipped SVG artwork once; keep the approved app PNG untouched.

    Existing toolbar SVGs are refreshed when the shipped artwork revision
    changes, but not on every launch. Full regeneration can be requested
    explicitly with --force in tools/build_icons.py. The source-controlled
    hi-res app PNG is preserved even in force mode.
    """
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    created = []
    marker = ASSETS_DIR / ARTWORK_MARKER
    current_revision = (
        marker.read_text(encoding="utf-8").strip()
        if marker.is_file() else ""
    )
    refresh = force or current_revision != ARTWORK_REVISION

    app_svg = ASSETS_DIR / "app_icon.svg"
    if refresh or not app_svg.is_file():
        app_svg.write_text(app_icon_svg(), encoding="utf-8")
        created.append(app_svg)

    # The committed 1024px Gemini-reference artwork wins over generated SVG.
    # Do not replace it on launch OR when --force refreshes toolbar SVGs.
    app_png = ASSETS_DIR / "app_icon.png"
    if not app_png.is_file():
        if not _rasterize(app_svg.read_text(encoding="utf-8"), 1024).save(
            str(app_png), "PNG"
        ):
            raise OSError(f"Unable to save application icon: {app_png}")
        created.append(app_png)

    for key in ICON_KEYS:
        target = ICONS_DIR / BUTTON_ICON_FILES[key]
        if refresh or not target.is_file():
            target.write_text(icon_svg(key), encoding="utf-8")
            created.append(target)
        if toolbar_png:
            png = target.with_suffix(".png")
            if refresh or not png.is_file():
                if not _rasterize(target.read_text(encoding="utf-8"), 48).save(
                    str(png), "PNG"
                ):
                    raise OSError(f"Unable to save toolbar icon: {png}")
                created.append(png)

    if current_revision != ARTWORK_REVISION:
        marker.write_text(ARTWORK_REVISION + "\n", encoding="utf-8")
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
    """Polished Arctic Ice splash using the *installed* StripSolve app icon.

    The progress animation describes GUI startup only; it never launches or
    claims to run the native decoder, a seed campaign, or a routing audit.
    """

    finished = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(
            parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(690, 462)
        self._complete = False
        self._drag_offset = None

        shell = QVBoxLayout(self)
        shell.setContentsMargins(10, 10, 10, 10)
        card = QFrame(self)
        card.setObjectName("StripSolveSplashCard")
        card.setStyleSheet("""
            QFrame#StripSolveSplashCard {
                background-color: #f6fbff;
                border: 2px solid #74bbd4;
                border-radius: 18px;
            }
            QLabel#SplashBrandName {
                color: #123b57;
                font-size: 29px;
                font-weight: 850;
            }
            QLabel#SplashBrandTagline {
                color: #315a72;
                font-size: 11px;
                font-weight: 650;
            }
            QLabel#SplashKicker {
                color: #138c97;
                font-size: 12px;
                font-weight: 800;
            }
            QLabel#SplashHeroTitle {
                color: #17435c;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#SplashHeroDescription {
                color: #3a5c72;
                font-size: 12px;
                font-weight: 550;
            }
            QLabel#SplashStage {
                color: #234b65;
                font-size: 12px;
                font-weight: 750;
            }
            QProgressBar {
                background: #d9ecf8;
                color: #133c54;
                border: 1px solid #9cc7d9;
                border-radius: 8px;
                min-height: 18px;
                font-size: 11px;
                font-weight: 750;
                text-align: center;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2b7de9, stop:.5 #19b3d5, stop:1 #11a88b);
                border-radius: 7px;
            }
            QPushButton#SplashSkip {
                color: #176493;
                background-color: #ffffff;
                border: 1px solid #aad0e4;
                border-radius: 9px;
                padding: 6px 14px;
                font-weight: 700;
            }
            QPushButton#SplashSkip:hover {
                background-color: #def6ff;
                border-color: #33aacf;
            }
        """)
        shell.addWidget(card)

        body = QVBoxLayout(card)
        body.setContentsMargins(24, 20, 24, 20)
        body.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(12)
        emblem = QLabel()
        emblem.setObjectName("SplashSmallAppIcon")
        emblem.setPixmap(load_app_icon().pixmap(QSize(64, 64)))
        header.addWidget(emblem)

        heading = QVBoxLayout()
        heading.setSpacing(0)
        brand = QLabel("STRIPSOLVE")
        brand.setObjectName("SplashBrandName")
        tagline = QLabel("STRIPBOARD LAYOUT & ROUTING OPTIMIZER")
        tagline.setObjectName("SplashBrandTagline")
        heading.addWidget(brand)
        heading.addWidget(tagline)
        header.addLayout(heading, 1)

        skip = QPushButton("Skip")
        skip.setObjectName("SplashSkip")
        skip.setCursor(Qt.CursorShape.PointingHandCursor)
        skip.clicked.connect(self._finish)
        header.addWidget(skip, alignment=Qt.AlignmentFlag.AlignTop)
        body.addLayout(header)

        # Hero: the approved high-detail copper/blue S artwork, not a substitute
        # icon or a second painted approximation of the approved image.
        hero = QFrame()
        hero.setObjectName("SplashHeroPanel")
        hero.setStyleSheet("""
            QFrame#SplashHeroPanel {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #e1f2fb, stop:.55 #f2fbff, stop:1 #ffffff);
                border: 1px solid #c8e2ef;
                border-radius: 15px;
            }
        """)
        hero_layout = QHBoxLayout(hero)
        hero_layout.setContentsMargins(14, 10, 20, 10)
        hero_layout.setSpacing(20)
        art = QLabel()
        art.setObjectName("SplashBoardArtwork")
        art.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art.setFixedSize(223, 223)
        art.setPixmap(load_app_icon().pixmap(QSize(221, 221)))
        hero_layout.addWidget(art)

        copy = QVBoxLayout()
        copy.setSpacing(9)
        kicker = QLabel("COPPER  /  CIRCUITS  /  PRECISION")
        kicker.setObjectName("SplashKicker")
        copy.addWidget(kicker)
        motto = QLabel("ROUTE SMARTER.")
        motto.setObjectName("SplashHeroTitle")
        copy.addWidget(motto)
        description = QLabel(
            "An engineer's workspace for stripboard layout, "
            "electrical verification and native routing."
        )
        description.setWordWrap(True)
        description.setObjectName("SplashHeroDescription")
        copy.addWidget(description)

        for label_text, dot_color in (
            ("PASS ONE   /   NATIVE SEARCH", "#2b7de9"),
            ("STRICT AUDIT   /   VERIFIED", "#16a34a"),
            ("PASS TWO   /   CANDIDATE IMPORT", "#c87d4b"),
        ):
            label = QLabel("●   " + label_text)
            label.setStyleSheet(
                f"color: {dot_color}; font-weight: 800; font-size: 11px;"
            )
            label.setWordWrap(True)
            copy.addWidget(label)
        copy.addStretch(1)
        hero_layout.addLayout(copy, 1)
        body.addWidget(hero)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Starting desktop interface · no solver running")
        self.status_label.setObjectName("SplashStage")
        status_row.addWidget(self.status_label, 1)
        self.version_label = QLabel("ARCTIC ICE  +  COLOURBURST")
        self.version_label.setStyleSheet(
            "color: #52758d; font-size: 10px; font-weight: 750;"
        )
        status_row.addWidget(self.version_label)
        body.addLayout(status_row)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setFormat("%p%")
        body.addWidget(self.progress)

        # These are display-only loading captions; no fake 100-decode claims.
        self._steps = (
            (25, "Loading StripSolve appearance..."),
            (55, "Preparing component and copper views..."),
            (80, "Connecting desktop controls..."),
            (100, "Ready · choose a project JSON"),
        )
        self._step = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

    def start_demo(self, interval_ms: int = 240) -> None:
        self.show()
        self._timer.start(interval_ms)

    def set_progress(self, value: int, message: str | None = None) -> None:
        self.progress.setValue(max(0, min(100, int(value))))
        if message is not None:
            self.status_label.setText(message)
        if value >= 100:
            QTimer.singleShot(180, self._finish)

    def _advance(self) -> None:
        if self._complete:
            return
        if self._step >= len(self._steps):
            self._finish()
            return
        value, message = self._steps[self._step]
        self._step += 1
        self.set_progress(value, message)

    def _finish(self) -> None:
        if self._complete:
            return
        self._complete = True
        self._timer.stop()
        self.finished.emit()
        self.close()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if (self._drag_offset is not None and
                event.buttons() & Qt.MouseButton.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_offset)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_offset = None
        super().mouseReleaseEvent(event)
