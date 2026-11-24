"""Route-Mate desktop GUI: collect, sanity-check, render, then gather PRE-SOLVE locks."""
from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import traceback
from time import perf_counter
from pathlib import Path
from typing import Any

# Allow `python3 gui/main.py` to import the repository's root-level packages.
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# The GUI has its own release counter; the top-level VERSION stays at 2.00
# for the two-repository consolidation milestone.
_GUI_VERSION_FILE = REPO_ROOT / "gui" / "VERSION"
_ROOT_VERSION_FILE = REPO_ROOT / "VERSION"
GUI_VERSION = (_GUI_VERSION_FILE.read_text(encoding="utf-8").strip()
               if _GUI_VERSION_FILE.is_file()
               else _ROOT_VERSION_FILE.read_text(encoding="utf-8").strip())
CODE_VERSION = GUI_VERSION


def _git_revision() -> str:
    """Report the checked-out repository revision; no solver or renderer runs."""
    try:
        result = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short=12", "HEAD"],
            capture_output=True, text=True, timeout=2, check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return "unavailable"


GUI_GIT_REVISION = _git_revision()

from PySide6.QtCore import Qt, QByteArray, QPoint, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QBrush, QColor, QFontDatabase, QPainter, QPixmap, QIcon
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QComboBox,
    QSpinBox, QSplitter, QToolBar, QVBoxLayout, QWidget, QProgressBar, QTabWidget, QFrame, QSplashScreen,
)



def default_project_directory() -> Path:
    """Start native file pickers in user files, never PyInstaller internals."""
    desktop = Path.home() / "Desktop"
    project_folder = desktop / "Route-Mate"
    if project_folder.is_dir():
        return project_folder
    if desktop.is_dir():
        return desktop
    return Path.home()


# No old Python saved-board verifier: native CLI audit is authoritative.

class BoardSizeDialog(QDialog):
    """Collect physical and preferred dimensions without changing the source file."""
    def __init__(self, board: dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Board dimensions")
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.actual_rows = self._spin(board.get("actualRows", board.get("rows", 24)))
        self.actual_cols = self._spin(board.get("actualCols", board.get("cols", 56)))
        self.preferred_rows = self._spin(board.get("wantedRows", board.get("rows", 24)))
        self.preferred_cols = self._spin(board.get("wantedCols", board.get("cols", 56)))
        self.rows_mode = self._mode(board.get("wantedRowsMode", "fixed"))
        self.cols_mode = self._mode(board.get("wantedColsMode", "fixed"))
        form.addRow("Actual physical rows:", self.actual_rows)
        form.addRow("Actual physical columns:", self.actual_cols)
        rows_box = QWidget()
        rows_layout = QHBoxLayout(rows_box)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.addWidget(self.preferred_rows)
        rows_layout.addWidget(self.rows_mode)
        cols_box = QWidget()
        cols_layout = QHBoxLayout(cols_box)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.addWidget(self.preferred_cols)
        cols_layout.addWidget(self.cols_mode)
        form.addRow("Preferred rows:", rows_box)
        form.addRow("Preferred columns:", cols_box)
        layout.addLayout(form)
        layout.addWidget(QLabel("Preferred dimensions are separate from the physical board limits."))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @staticmethod
    def _spin(value):
        widget = QSpinBox()
        widget.setRange(1, 500)
        try:
            widget.setValue(int(value))
        except (TypeError, ValueError):
            widget.setValue(24)
        return widget

    @staticmethod
    def _mode(value):
        widget = QComboBox()
        widget.addItem("Fixed", "fixed")
        widget.addItem("Max", "max")
        index = widget.findData(value if value in ("fixed", "max") else "fixed")
        widget.setCurrentIndex(max(0, index))
        return widget

    def values(self):
        return {
            "actualRows": self.actual_rows.value(),
            "actualCols": self.actual_cols.value(),
            "wantedRows": self.preferred_rows.value(),
            "wantedCols": self.preferred_cols.value(),
            "wantedRowsMode": self.rows_mode.currentData(),
            "wantedColsMode": self.cols_mode.currentData(),
        }



class SpacingDialog(QDialog):
    """Select an advisory body-gap preference without changing circuit data."""

    def __init__(self, parent=None, selected: int = 1):
        super().__init__(parent)
        self.setWindowTitle("Quick Solve — component spacing")
        self.setMinimumWidth(420)
        layout = QVBoxLayout(self)
        heading = QLabel("How much space should Quick Solve leave between parts?")
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size: 14px; font-weight: 700;")
        layout.addWidget(heading)
        self.choice = QComboBox()
        self.choice.addItem("Off — compact placement (0 free holes)", 0)
        self.choice.addItem("Normal — 1 free hole (2.54 mm nominal)", 1)
        self.choice.addItem("Wider — 2 free holes (5.08 mm nominal)", 2)
        self.choice.setCurrentIndex(max(0, min(2, int(selected))))
        layout.addWidget(self.choice)
        note = QLabel(
            "This is a preference, not guaranteed physical clearance. "
            "Exact component locks and the purchased board size remain hard "
            "constraints. A reported compact fallback can be used if the "
            "preferred spacing cannot be routed."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def value(self) -> int:
        return int(self.choice.currentData())


class LockDialog(QDialog):
    """Collect PRE-SOLVE constraints for one already-placed component."""
    def __init__(self, component: dict[str, Any], index: int, total: int, parent=None):
        super().__init__(parent)
        label = str(component.get("label") or component.get("name") or component.get("id"))
        self.setWindowTitle(f"PRE-SOLVE constraints ({index}/{total})")
        self.setMinimumWidth(340)
        if parent is not None:
            # Keep the prompt over the left log pane so the highlighted board
            # remains visible while the user makes the decision.
            self.move(parent.mapToGlobal(QPoint(24, 90)))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Component: {label}"))
        self.locked = QRadioButton("Fixed — keep exact position")
        self.unlocked = QRadioButton("Movable — return to Quick Solve")
        self.edge = QCheckBox("Board-edge constraint")
        self.slide = QCheckBox("May slide along this edge (keep rotation)")
        # Unlocked parts lose their old placement and return to Quick Fit.
        is_locked = bool(component.get("locked", False))
        self.locked.setChecked(is_locked)
        self.unlocked.setChecked(not is_locked)
        self.edge.setChecked(bool(component.get("edge", False)))
        self.slide.setChecked(bool(component.get("slide", False)))
        self.locked.toggled.connect(self._update_constraint_controls)
        self.unlocked.toggled.connect(self._update_constraint_controls)
        self.edge.toggled.connect(self._update_constraint_controls)
        self.slide.toggled.connect(self._update_constraint_controls)
        layout.addWidget(self.locked)
        layout.addWidget(self.unlocked)
        layout.addWidget(self.edge)
        layout.addWidget(self.slide)
        hint = QLabel("Fixed = exact position. Edge + Slide = may move only along the same edge.\nMovable = auto-place while keeping all electrical connections.")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.search_notice = QLabel(
            "Edge+Slide can take much longer: up to 24 Quick Solve "
            "attempts at each legal position, stopping at the first verified route."
        )
        self.search_notice.setWordWrap(True)
        self.search_notice.setStyleSheet(
            "color: #92400e; font-size: 12px; font-weight: 600;"
        )
        layout.addWidget(self.search_notice)
        self._update_constraint_controls()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _update_constraint_controls(self):
        keep = self.locked.isChecked()
        self.edge.setEnabled(keep)
        self.slide.setEnabled(keep and self.edge.isChecked())
        self.search_notice.setVisible(
            keep and self.edge.isChecked() and self.slide.isChecked()
        )
        if not (keep and self.edge.isChecked()):
            self.slide.setChecked(False)

    def values(self):
        return {"locked": self.locked.isChecked(),
                "edge": self.edge.isChecked() if self.locked.isChecked() else False,
                "slide": self.slide.isChecked() if self.locked.isChecked() else False,
                "reposition": self.unlocked.isChecked()}


class BoardView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.setRenderHints(QPainter.RenderHint.Antialiasing |
                            QPainter.RenderHint.TextAntialiasing |
                            QPainter.RenderHint.SmoothPixmapTransform)
        self.setBackgroundBrush(QBrush(QColor("#fafbfd")))
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._renderer = None
        self._renderer_cache = {}
        self._svg_key = None
        self._user_zoomed = False

    def fit_board(self):
        if self.scene().sceneRect().isEmpty():
            return
        self.resetTransform()
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self._user_zoomed = False

    def zoom(self, factor: float):
        if self.scene().sceneRect().isEmpty():
            return
        current = self.transform().m11()
        # Bound zoom to avoid vanishing boards or enormous rasterisation.
        if 0.02 <= current * factor <= 12.0:
            self.scale(factor, factor)
            self._user_zoomed = True

    def wheelEvent(self, event):
        # The wheel scrolls; it no longer magnifies the SVG unexpectedly.
        super().wheelEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.scene() and not self.scene().sceneRect().isEmpty() and not self._user_zoomed:
            self.fit_board()

    def show_png(self, png: bytes):
        """Display the original Tk renderer's PNG using the existing Qt scene."""
        key = "png:" + hashlib.sha256(png).hexdigest()
        if self._svg_key == key:
            return
        pixmap = QPixmap()
        if not pixmap.loadFromData(png, "PNG"):
            raise ValueError("Tk-compatible schematic preview produced an unreadable PNG.")
        scene = self.scene()
        scene.clear()
        item = scene.addPixmap(pixmap)
        scene.setSceneRect(item.boundingRect())
        self._renderer = None
        self._svg_key = key
        self.fit_board()

    def show_svg(self, svg: str, *, schematic: bool = False):
        import re
        # Resolve generic SVG font aliases before Qt parses the image.
        # macOS Qt otherwise spends time constructing missing-font aliases.
        system_family = QFontDatabase.systemFont(
            QFontDatabase.SystemFont.GeneralFont
        ).family()
        for alias in ("sans-serif", "Sans-serif"):
            svg = svg.replace(
                f'font-family="{alias}"', f'font-family="{system_family}"'
            )
            svg = svg.replace(
                f"font-family: {alias}", f"font-family: {system_family}"
            )
        if schematic:
            # QtSvg draws the standalone renderer's white text halo over dark
            # glyphs (it does not reliably honour paint-order="stroke").
            # Adapt only this in-memory schematic preview; never edit the SVG
            # generated by the renderer or change the board/copper styling.
            from render.qt_schematic_svg import schematic_svg_for_qt
            svg = schematic_svg_for_qt(svg)
        else:
            svg = re.sub(
                r"(<svg\b[^>]*>)",
                r"\1<style>text{fill:#000000!important;stroke:#fff8ed!important;"
                r"stroke-width:0.32px!important;paint-order:stroke fill!important;"
                r"stroke-linejoin:round!important;font-weight:700!important;opacity:1!important;}"
                r"tspan{fill:#000000!important;stroke:#f3e5bf!important;"
                r"stroke-width:0.55px!important;font-weight:700!important;opacity:1!important;}</style>",
                svg, count=1,
            )
        key = hashlib.sha256(svg.encode("utf-8")).hexdigest()
        if key == self._svg_key:
            return
        renderer = self._renderer_cache.get(key)
        if renderer is None:
            renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
            if not renderer.isValid():
                raise ValueError("Component-side renderer produced invalid SVG.")
            if len(self._renderer_cache) >= 2:
                self._renderer_cache.pop(next(iter(self._renderer_cache)))
            self._renderer_cache[key] = renderer
        scene = self.scene()
        scene.clear()
        item = QGraphicsSvgItem()
        item.setSharedRenderer(renderer)
        scene.addItem(item)
        self._renderer = renderer
        self._svg_key = key
        scene.setSceneRect(item.boundingRect())
        self.fit_board()


class WorkflowChecklist(QWidget):
    """Visual summary of recorded pipeline stages, not a physical sign-off."""

    STAGES = (
        ("COLLECT", "Project imported"),
        ("SANITY", "Electrical input checked"),
        ("PRE-SOLVE", "Footprints analysed"),
        ("CONSTRAINTS", "Placement locks"),
        ("QUICK FIT", "Components placed"),
        ("ROUTING", "Copper routed"),
        ("VERIFY", "Electrical PASS"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workflowChecklist")
        self.setStyleSheet("""
            QWidget#workflowChecklist { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 12px; }
            QLabel#workflowTitle { color: #203047; font-size: 15px; font-weight: 700; }
            QLabel#workflowPercent { color: #233e6b; font-size: 14px; font-weight: 700; }
            QProgressBar { background: #e9eef5; border: 0; border-radius: 5px; height: 8px; }
            QProgressBar::chunk { background: #19866f; border-radius: 5px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 12)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        title = QLabel("JSON import/preflight")
        title.setObjectName("workflowTitle")
        self.percent = QLabel("0%")
        self.percent.setObjectName("workflowPercent")
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.percent)
        layout.addLayout(heading)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, len(self.STAGES))
        layout.addWidget(self.bar)
        self.rows = {}
        for key, caption in self.STAGES:
            row = QHBoxLayout()
            mark = QLabel("○")
            mark.setFixedWidth(22)
            mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mark.setStyleSheet("font-size: 23px; color: #b8bec7;")
            label = QLabel(caption)
            label.setStyleSheet("font-size: 12px; color: #475569;")
            row.addWidget(mark)
            row.addWidget(label, 1)
            layout.addLayout(row)
            self.rows[key] = mark
        self.lock_summary = QLabel("Fixed locked: 0   |   Edge locked: 0   |   Edge+Slide: 0")
        self.lock_summary.setWordWrap(True)
        self.lock_summary.setStyleSheet(
            "font-size: 11px; font-weight: 600; color: #24476b;"
        )
        layout.addWidget(self.lock_summary)
        self.lock_warning = QLabel("")
        self.lock_warning.setWordWrap(True)
        self.lock_warning.setStyleSheet(
            "font-size: 11px; font-weight: 700; color: #92400e;"
        )
        self.lock_warning.hide()
        layout.addWidget(self.lock_warning)
        note = QLabel("Input sanity only · routing and physical verification NOT run")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 10px; color: #697586;")
        layout.addWidget(note)
        self.reset()

    def reset(self):
        self.update_states({})
        self.set_lock_summary(0, 0, 0)

    def set_lock_summary(self, fixed: int, edge: int, slide: int,
                         positions: int | None = None, attempts: int = 24):
        self.lock_summary.setText(
            f"Fixed locked: {fixed}   |   Edge locked: {edge}   |   Edge+Slide: {slide}"
        )
        if slide:
            detail = (
                f"{positions} positions × {attempts} attempts = "
                f"up to {positions * attempts:,} solves"
                if positions is not None else
                f"up to {attempts} solves per legal edge position"
            )
            self.lock_warning.setText(
                f"Edge+Slide detected — Quick Solve will take much longer. "
                f"{detail}. Stops at first verified route."
            )
            self.lock_warning.show()
        elif edge:
            self.lock_warning.setText(
                "Edge lock detected — Quick Solve may take longer because "
                "placement is constrained to the board edge."
            )
            self.lock_warning.show()
        else:
            self.lock_warning.hide()

    def update_states(self, states):
        complete = 0
        for key, _ in self.STAGES:
            state = states.get(key, "pending")
            mark = self.rows[key]
            if state == "done":
                mark.setText("✓")
                mark.setStyleSheet("font-size: 19px; font-weight: bold; color: #2ebd64;")
                complete += 1
            elif state == "running":
                mark.setText("●")
                mark.setStyleSheet("font-size: 17px; color: #2673bf;")
            elif state == "failed":
                mark.setText("✕")
                mark.setStyleSheet("font-size: 19px; font-weight: bold; color: #d64545;")
            else:
                mark.setText("○")
                mark.setStyleSheet("font-size: 23px; color: #b8bec7;")
        self.bar.setValue(complete)
        self.percent.setText(f"{round(100 * complete / len(self.STAGES))}%")


# The old Python Quick Solve worker and startup solver probe are removed.

class RouteMateWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Route-Mate {GUI_VERSION} · rev {GUI_GIT_REVISION} — JSON Preflight")
        self.resize(1560, 900)
        self.setMinimumSize(950, 600)
        self.project: dict[str, Any] | None = None
        self.project_path: Path | None = None
        self.presolve_constraints: dict[str, dict[str, bool]] = {}
        self.pipeline_run = None
        self._top_svg = None
        self._copper_svg = None
        self._schematic_svg = None
        self._schematic_png = None  # Old Tk GUI’s rsvg-convert preview bytes
        self._board_side = "top"
        self._tool_revisions_seen: set[str] = set()
        self._active_tool_splash = None
        self._solver_worker = None
        self._speed_probe_worker = None
        self._stop_requested = False
        self._close_when_idle = False
        self._recommended_workers = 1  # Native CLI not connected; no worker probe
        self._body_spacing_holes = 1
        self._solve_attempt_seconds = []
        self._solve_started = None
        self._solve_done = 0
        self._solve_budget = 24
        self._solve_found = 0
        self._worker_time_stats = {}
        self._solve_clock = QTimer(self)
        self._solve_clock.setInterval(500)
        self._solve_clock.timeout.connect(self._update_solve_clock)
        self._solve_input = None
        self._solved_verified = False
        self._quick_source = None  # Locked pre-route project; never a previously solved layout.
        self._assumed_geometry = None  # Collector's advisory package profile; not 2.5D PASS.

        logo_path = REPO_ROOT / "icon" / "icon_128x128.png"
        if logo_path.is_file():
            self.setWindowIcon(QIcon(str(logo_path)))
        toolbar = QToolBar("Main")
        toolbar.setObjectName("routeMateToolbar")
        toolbar.setStyleSheet("""
            QToolBar#routeMateToolbar { background: #17273b; border: none; padding: 9px; spacing: 8px; min-height: 54px; }
            QToolBar#routeMateToolbar QToolButton { background: #2a405a; color: white; border: 1px solid #3e5976; border-radius: 9px; padding: 9px 14px; font-weight: 600; }
            QToolBar#routeMateToolbar QToolButton:hover { background: #3a5b7c; }
            QToolBar#routeMateToolbar QToolButton:checked { background: #23966c; border-color: #35c18b; }
        """)
        brand = QWidget()
        brand_row = QHBoxLayout(brand)
        brand_row.setContentsMargins(2, 0, 18, 0)
        brand_row.setSpacing(10)
        brand_logo = QLabel()
        if logo_path.is_file():
            logo = QPixmap(str(logo_path))
            if not logo.isNull():
                brand_logo.setPixmap(logo.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio,
                                                Qt.TransformationMode.SmoothTransformation))
        brand_row.addWidget(brand_logo)
        brand_title = QLabel("ROUTE-MATE")
        brand_title.setStyleSheet("color: white; font-size: 16px; font-weight: 800;")
        brand_row.addWidget(brand_title)
        toolbar.addWidget(brand)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.load_action = QAction("Load JSON", self)
        self.load_action.triggered.connect(self.load_json)
        toolbar.addAction(self.load_action)
        self.solve_action = QAction("Pass 1 (disabled)", self)
        self.solve_action.setToolTip("Native CLI not connected. This version stops after input checks.")
        self.solve_action.setEnabled(False)
        self.solve_action.triggered.connect(self.solve_board)
        toolbar.addAction(self.solve_action)
        self.stop_action = QAction("Stop Solve", self)
        self.stop_action.setToolTip("Cancel the running solve safely; keep the original board")
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self.stop_solve)
        toolbar.addAction(self.stop_action)
        self.review_locks_action = QAction("Review Locks", self)
        self.review_locks_action.setEnabled(False)
        self.review_locks_action.setToolTip("Choose fixed and edge constraints for positioned parts")
        self.review_locks_action.triggered.connect(self.review_locks)
        toolbar.addAction(self.review_locks_action)
        self.save_solved_action = QAction("Save Solved JSON", self)
        self.save_solved_action.setEnabled(False)
        self.save_solved_action.triggered.connect(self.save_solved_json)
        toolbar.addAction(self.save_solved_action)
        pipeline_action = QAction("Pipeline State", self)
        pipeline_action.triggered.connect(self.show_pipeline_state)
        toolbar.addAction(pipeline_action)
        toolbar.addSeparator()
        self.top_action = QAction("Component side", self)
        self.top_action.setCheckable(True)
        self.top_action.setChecked(True)
        self.top_action.triggered.connect(lambda: self._switch_board_side("top"))
        toolbar.addAction(self.top_action)
        self.copper_action = QAction("Copper side (mirrored)", self)
        self.copper_action.setCheckable(True)
        self.copper_action.triggered.connect(lambda: self._switch_board_side("copper"))
        toolbar.addAction(self.copper_action)
        self.schematic_action = QAction("Schematic", self)
        self.schematic_action.setCheckable(True)
        self.schematic_action.setEnabled(False)
        self.schematic_action.setToolTip("View the original schematic, rendered when JSON loads")
        self.schematic_action.triggered.connect(lambda: self._switch_board_side("schematic"))
        toolbar.addAction(self.schematic_action)
        self.render_action = QAction("Open Solved", self)
        self.render_action.setToolTip("Preview an existing routed JSON without re-solving")
        self.render_action.triggered.connect(self.render_json)
        self.render_action.setEnabled(False)
        toolbar.addAction(self.render_action)
        toolbar.addSeparator()
        self.exit_action = QAction("Exit", self)
        self.exit_action.setToolTip("Stop any active solve, then close Route-Mate")
        self.exit_action.triggered.connect(self._exit_requested)
        toolbar.addAction(self.exit_action)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(5000)
        self.log.setPlaceholderText("Checks, solve attempts and diagnostics appear here.")
        self.log.setStyleSheet(
            "QPlainTextEdit { background: #0f1c2b; color: #dbe7f5;"
            "border: 0; padding: 12px; font-size: 11px; }"
        )
        self.top_view = BoardView()
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.setHandleWidth(5)

        # Left: meaningful overview without a wall of test output.
        self.checklist = WorkflowChecklist()
        self.project_summary = QLabel("Open a circuit to begin")
        self.project_summary.setWordWrap(True)
        self.project_summary.setObjectName("projectSummary")
        self.solve_summary = QLabel("No board solved")
        self.solve_summary.setWordWrap(True)
        self.solve_summary.setObjectName("solveSummary")
        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.setContentsMargins(8, 12, 8, 8)
        overview_layout.setSpacing(11)
        overview_layout.addWidget(self.project_summary)
        overview_layout.addWidget(self.checklist)
        overview_layout.addWidget(self.solve_summary)
        self.solve_activity = QLabel("JSON sniff · STOP before Pass 1")
        self.solve_activity.setWordWrap(True)
        self.solve_activity.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #173c66; padding: 4px;"
        )
        overview_layout.addWidget(self.solve_activity)
        self.solve_progress = QProgressBar()
        self.solve_progress.setRange(0, 24)
        self.solve_progress.setValue(0)
        self.solve_progress.setFormat("Pass 1 not started")
        overview_layout.addWidget(self.solve_progress)
        self.solve_worker_status = QLabel("Native CLI not connected")
        self.solve_worker_status.setWordWrap(True)
        overview_layout.addWidget(self.solve_worker_status)
        self.solve_eta = QLabel("Elapsed: —   Estimated remaining: —")
        self.solve_eta.setWordWrap(True)
        overview_layout.addWidget(self.solve_eta)
        overview_layout.addStretch()
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setObjectName("sidebarTabs")
        self.sidebar_tabs.addTab(overview, "Overview")
        self.sidebar_tabs.addTab(self.log, "Activity")
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(6, 8, 2, 8)
        left_layout.addWidget(self.sidebar_tabs)
        left_panel.setMinimumWidth(245)
        left_panel.setMaximumWidth(375)
        split.addWidget(left_panel)

        # Right: stable board canvas. Scroll/pan and Fit; wheel zoom is disabled.
        board_panel = QWidget()
        board_layout = QVBoxLayout(board_panel)
        board_layout.setContentsMargins(8, 8, 8, 8)
        board_layout.setSpacing(7)
        board_heading = QFrame()
        board_heading.setObjectName("boardHeader")
        heading_row = QHBoxLayout(board_heading)
        heading_row.setContentsMargins(13, 8, 10, 8)
        heading_row.setSpacing(9)
        heading_text = QVBoxLayout()
        heading_text.setSpacing(2)
        self.board_project_label = QLabel("BOARD PREVIEW")
        self.board_project_label.setObjectName("boardProjectLabel")
        self.board_result_label = QLabel("Open a project to show its component layout")
        self.board_result_label.setObjectName("boardResultLabel")
        heading_text.addWidget(self.board_project_label)
        heading_text.addWidget(self.board_result_label)
        heading_row.addLayout(heading_text, 1)
        for caption, callback, tip in (
            ("Fit", self.fit_board, "Fit the complete board"),
        ):
            button = QPushButton(caption)
            button.setObjectName("boardZoomButton")
            button.setToolTip(tip)
            button.clicked.connect(callback)
            heading_row.addWidget(button)
        board_layout.addWidget(board_heading)
        board_layout.addWidget(self.top_view, 1)
        split.addWidget(board_panel)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([295, 1265])
        self.setCentralWidget(split)
        self.setStyleSheet("""
            QMainWindow { background: #eef2f7; }
            QWidget#sidebarTabs { background: #f7f9fc; }
            QTabWidget::pane { border: 1px solid #e0e7ef; border-radius: 9px;
                                background: #f7f9fc; }
            QTabBar::tab { color: #5b6c82; background: #e8eef5; padding: 9px 22px;
                           margin-right: 3px; border-radius: 7px; font-weight: 600; }
            QTabBar::tab:selected { background: white; color: #173c66; }
            QLabel#projectSummary { background: #e8f0fa; color: #1c4268;
                                    border-radius: 8px; padding: 12px;
                                    font-size: 12px; font-weight: 600; }
            QLabel#solveSummary { background: #edf3fa; color: #2e5274;
                                  border-radius: 8px; padding: 12px;
                                  font-size: 12px; }
            QFrame#boardHeader { background: white; border: 1px solid #e0e7ef;
                                  border-radius: 10px; }
            QLabel#boardProjectLabel { color: #17324f; font-size: 15px; font-weight: 800; }
            QLabel#boardResultLabel { color: #60738a; font-size: 11px; }
            QPushButton#boardZoomButton { background: #eff4fa; color: #183956;
                                         padding: 7px 11px; border: 1px solid #dbe5ef;
                                         border-radius: 6px; font-weight: 700; }
            QPushButton#boardZoomButton:hover { background: #dbe9f7; }
            QStatusBar { background: #e7eef5; color: #3f5873; font-size: 11px; }
        """)
        self.statusBar().showMessage("Ready. Load a project JSON to begin.")
        self.log_line(f"Route-Mate {GUI_VERSION} — JSON import preflight only")
        self.log_line(f"[GUI][REVISION] git={GUI_GIT_REVISION}")
        self.log_line("Workflow: JSON sniff → geometry/footprint inventory → electrical input sanity → STOP.")
        self.log_line("[SOLVER] DISCONNECTED. No Quick Solve, Hell Mode, native CLI or speed probe.")
        self.statusBar().showMessage("Ready. Load JSON to check; Pass 1 remains disabled.")

    def _set_board_summary(self, message: str, *, project: dict | None = None,
                           level: str = "neutral"):
        active = project if project is not None else self.project
        board = active.get("board", {}) if isinstance(active, dict) else {}
        name = self.project_path.stem if self.project_path is not None else "Untitled"
        rows, cols = board.get("rows"), board.get("cols")
        dims = f"  ·  {rows} × {cols} holes" if rows and cols else ""
        self.board_project_label.setText(f"{name.upper()}{dims}")
        self.board_result_label.setText(message)
        self.solve_summary.setText(message)
        backgrounds = {
            "neutral": ("#edf3fa", "#2e5274"),
            "working": ("#e7f1ff", "#155aa0"),
            "pass": ("#e2f4ed", "#176c51"),
            "failed": ("#fdeaea", "#ac2f3c"),
        }
        bg, fg = backgrounds.get(level, backgrounds["neutral"])
        self.solve_summary.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 8px; "
            "padding: 12px; font-size: 12px; font-weight: 600;"
        )

    def log_line(self, message: str):
        self.log.appendPlainText(message)

    def _show_tool_revision(self, diagnostic: str, tool: str):
        """Show each actual renderer CLI build in the Activity log once."""
        prefix = f"[TOOL-REVISION] tool={tool} "
        revision = next((line.strip() for line in diagnostic.splitlines()
                         if line.startswith(prefix)), None)
        if revision is None:
            revision = (f"[{tool}][REVISION NOT STAMPED] Compiled renderer lacks "
                        "revision splash; rebuild with cd src/frontend && npm run build:renderers")
        if revision in self._tool_revisions_seen:
            return
        self._tool_revisions_seen.add(revision)
        self.log_line(f"━━━━━━ {tool} · EXECUTABLE REVISION ━━━━━━")
        self.log_line(revision)
        self.log_line("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        self.statusBar().showMessage(revision, 8000)
        self._display_tool_splash(tool, revision)

    def _display_tool_splash(self, tool: str, revision: str):
        """Brief visible Qt splash; not a blocking dialog or a fake solver run."""
        pix = QPixmap(690, 156)
        pix.fill(QColor("#17273b"))
        painter = QPainter(pix)
        painter.setPen(QColor("#ffffff"))
        font = painter.font()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(24, 48, f"STRIPBOARD · {tool}")
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#b8d7ef"))
        painter.drawText(24, 88, revision)
        painter.drawText(24, 123, f"GUI {GUI_VERSION}  ·  checked-out {GUI_GIT_REVISION}")
        painter.end()
        if self._active_tool_splash is not None:
            self._active_tool_splash.close()
        splash = QSplashScreen(self, pix, Qt.WindowType.WindowStaysOnTopHint)
        self._active_tool_splash = splash
        splash.show()
        splash.repaint()
        QTimer.singleShot(1800, splash.close)

    def _log_handoff(self, handoff: dict[str, Any]):
        self.log_line(
            f"[HANDOFF] {handoff.get('from_stage') or 'project start'} -> "
            f"{handoff['to_module']} | project={handoff['project_sha256'][:12]} | "
            f"outstanding findings={len(handoff['findings'])}"
        )
        for finding in handoff["findings"]:
            self.log_line(
                f"[HANDOFF][{finding['severity'].upper()}] "
                f"{finding['code']}: {finding['message']}"
            )

    def show_pipeline_state(self):
        if self.pipeline_run is None:
            QMessageBox.information(self, "Pipeline State", "Load a project to start a pipeline run.")
            return
        context = self.pipeline_run.context
        lines = [
            f"Run ID: {context.run_id}",
            f"Project: {context.project_path}",
            f"Current stage: {context.current_stage or 'not started'}",
            f"Current project SHA-256: {context.project_sha256}",
            "",
            "WORKFLOW HANDOFFS",
        ]
        order = ("COLLECT", "TEST", "QUICKSOLVE", "SOLVE")
        grouped = {name: [] for name in order}
        for result in context.stages.values():
            group = result.extra.get("workflow_stage", "OTHER")
            grouped.setdefault(group, []).append(result)
        for group in order:
            lines.append(f"{group}:")
            records = grouped.get(group, [])
            if not records:
                lines.append("  NOT RUN")
            for result in records:
                lines.append(f"  {result.stage} — {result.status} — {result.module}")
                lines.append(f"    input:  {(result.input_project_sha256 or 'n/a')[:16]}")
                lines.append(f"    output: {(result.output_project_sha256 or 'n/a')[:16]}")
                if result.options.get("from_stage"):
                    lines.append(f"    received after: {result.options['from_stage']}")
                if result.options.get("upstream_finding_ids"):
                    lines.append(
                        f"    received findings: {result.options['upstream_finding_ids']}"
                    )
                if result.metrics:
                    lines.append(f"    metrics: {result.metrics}")
                if result.summary:
                    lines.append(f"    result: {result.summary}")
        lines.extend(["", f"FINDINGS ({len(context.findings)} total)"])
        if not context.findings:
            lines.append("  None")
        for finding in context.findings:
            lines.append(
                f"  [{finding.severity.upper()} / {finding.status}] "
                f"{finding.code}: {finding.message}"
            )
        dialog = QDialog(self)
        dialog.setWindowTitle("Pipeline State — Handoff Proof")
        dialog.resize(900, 650)
        layout = QVBoxLayout(dialog)
        view = QPlainTextEdit(dialog)
        view.setReadOnly(True)
        view.setPlainText("\\n".join(lines))
        layout.addWidget(view)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.reject)
        buttons.accepted.connect(dialog.accept)
        layout.addWidget(buttons)
        dialog.exec()

    def fit_board(self):
        self.top_view.fit_board()

    def _render_component_side(
        self, project: dict[str, Any], *, highlight_component_id: str | None = None
    ) -> tuple[str, str]:
        """Render the component side, optionally highlighting the part under review."""
        from render.standalone_bridge import render_project_data

        # Both views come from the same production render pass and solved project.
        top_svg, copper_svg, _renderer_log = render_project_data(
            project, highlight_component_id=highlight_component_id
        )
        self._copper_svg = copper_svg
        self._show_tool_revision(_renderer_log, "RENDER")
        # Surface render-only moved-label diagnostics (the source JSON and
        # solder pads are untouched); avoid dumping raw Node CLI messages.
        label_notes = [
            line for line in _renderer_log.splitlines()
            if line.startswith("[CAPACITOR][LABEL]")
        ]
        label_report = ("\n" + "\n".join(label_notes)) if label_notes else ""
        return top_svg, "production standalone renderer (both board sides)" + label_report

    def _cache_schematic_preview(self, project: dict[str, Any]):
        """Render imported schematic once; keep the board/lock workflow unchanged."""
        from render.schematic_bridge import render_schematic_data, rasterize_schematic_svg

        self._schematic_svg = None
        self._schematic_png = None
        self.schematic_action.setEnabled(False)
        # A new project always starts on its component-side board view, so the
        # original per-component lock highlighting is still visible.
        self._board_side = "top"
        try:
            svg, diagnostic = render_schematic_data(project)
            if not QSvgRenderer(QByteArray(svg.encode("utf-8"))).isValid():
                raise ValueError("Standalone schematic SVG is invalid for Qt.")
        except (OSError, RuntimeError, ValueError, TypeError, subprocess.SubprocessError) as exc:
            self.log_line(f"[SCHEMATIC][WARN] Preview unavailable: {exc}")
            # A renderer failure must never prevent the donor import/lock review.
            return
        self._schematic_svg = svg
        self._show_tool_revision(diagnostic, "SCHEMATIC")
        try:
            # Exactly the renderer path used by the old Tk GUI: the existing
            # standalone schematic SVG converted to PNG by librsvg at 2400px.
            self._schematic_png = rasterize_schematic_svg(svg)
            self.log_line(
                "[SCHEMATIC] Original Tk-compatible librsvg PNG (2400 px) ready."
            )
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
            # Preserve the SVG fallback if librsvg is not installed, but make
            # the reason explicit instead of silently claiming visual parity.
            self.log_line(f"[SCHEMATIC][WARN] Tk PNG preview unavailable: {exc}")
            self.log_line("[SCHEMATIC][WARN] Using direct QtSvg fallback; text may be faint.")
        self.schematic_action.setEnabled(True)
        self.log_line("[SCHEMATIC] Original JSON schematic ready. Solver not started.")
        for line in diagnostic.splitlines():
            if line.startswith("Saved "):
                self.log_line("[SCHEMATIC] " + line)

    def _record_assumed_geometry(self, project: dict[str, Any], *, stage=None):
        """Use the SAME versioned geometry generator as collect.py.

        Store the advisory data in the existing pipeline state when a stage is
        supplied. Do not add physicalClearance to the solver input: its
        absolute-coordinate contract requires measured/locked shapes.
        """
        from geometry_sidecar import load_or_create
        # Exact project snapshot + preset are checksum-bound in a persistent
        # sidecar. The collector's generator remains the only profile owner.
        path = self.project_path
        if path is None:
            from collector_geometry import build_assumed_geometry
            model = build_assumed_geometry(project)
            document = None
        else:
            document = load_or_create(project, path)
            model = document["geometry"]
        self._assumed_geometry = document if document is not None else model
        if stage is not None:
            # The pipeline stores a checksum-bound reference, not another
            # mutable copy of the geometry sidecar. Unit-level in-memory
            # callers without a source path retain an inline fallback.
            if document is not None:
                from geometry_sidecar import sidecar_path
                stage.report["assumed_geometry_sidecar"] = str(sidecar_path(path))
                stage.report["assumed_geometry_project_sha256"] = document["project_sha256"]
                stage.report["assumed_geometry_sha256"] = document["geometry_sha256"]
                stage.report["assumed_geometry_component_count"] = model["component_count"]
            else:
                stage.report["assumed_geometry"] = copy.deepcopy(model)
            stage.options["geometry_preset"] = model["preset"]
            stage.options["geometry_status"] = "ASSUMED_UNVERIFIED"
        assumed = sum(x["status"] == "ASSUMED_UNVERIFIED" for x in model["components"])
        unknown = sum(x["status"] == "UNVERIFIED" for x in model["components"])
        self.log_line(
            f"[GEOMETRY][ASSUMED] {model['preset']} | "
            f"{assumed} assumed package(s), {unknown} unknown body/bodies | "
            "collector profile active for reporting; solver still enforces "
            "legacy artwork and occupied-pad keepouts."
        )
        # Renderer receives the identical resolved package ID, making a
        # mis-selected ceramic/electrolytic traceable at import and solve.
        for entry in model["components"]:
            package = entry.get("render_package")
            if package:
                self.log_line(
                    f"[CAPACITOR][PACKAGE] {entry['label']}: "
                    f"renderer={package} collector={entry['profile']} "
                    f"source={entry.get('package_hint') or 'default'}"
                )
                for note in entry.get("notes", []):
                    if "symbol_with_" in note or "unrecognised_capacitor" in note:
                        self.log_line(
                            f"[CAPACITOR][WARNING] {entry['label']}: {note}"
                        )
        return model

    def _log_assumed_contacts(self, report: dict, *, stage: str):
        """Nominal proximity warnings, not measured collision verdicts."""
        contacts = report.get("contact_findings", [])
        if not contacts:
            self.log_line(f"[CONTACT][{stage}][ASSUMED_CLEAR] "
                          "No nominal body/body or foreign-pad contact flagged.")
            return 0
        self.log_line(
            f"[CONTACT][{stage}][ASSUMED_RISK] {len(contacts)} "
            "nominal body/pad contact(s) marked RED on both board sides. "
            "Dimensions are ASSUMED, not certified physical collisions."
        )
        for issue in contacts[:100]:
            position = issue.get("pad")
            detail = (f" pad=({position['row']},{position['col']})"
                      if position is not None else "")
            self.log_line(
                f"[CONTACT][ASSUMED_RISK] {issue['kind']}: "
                + " / ".join(issue["components"])
                + f" gap={issue['gap_mm']} mm{detail}"
            )
        if len(contacts) > 100:
            self.log_line(f"[CONTACT] {len(contacts)-100} additional findings "
                          "remain in sidecar report.")
        return len(contacts)

    def render_json(self):
        """All JSON imports use one validated path in this milestone."""
        self.load_json()

    def export_board_svgs(self):
        """Refresh the current board and save both production SVG views."""
        if self.project is None:
            QMessageBox.information(self, "Render SVG", "Load a project first.")
            return
        directory = self.project_path.parent if self.project_path else default_project_directory()
        suggested = directory / "route-mate-board.svg"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Export component-side SVG", str(suggested),
            "SVG image (*.svg)",
        )
        if not filename:
            return
        output = Path(filename)
        if output.suffix.lower() != ".svg":
            output = output.with_suffix(".svg")
        copper_output = output.with_name(output.stem + "-copper.svg")
        try:
            top_svg, renderer_log = self._render_component_side(self.project)
            self._show_board(top_svg)
            output.write_text(top_svg, encoding="utf-8")
            copper_output.write_text(self._copper_svg, encoding="utf-8")
        except (OSError, ValueError, TypeError) as exc:
            self.log_line(f"[RENDER][ERROR] {exc}")
            QMessageBox.warning(self, "SVG export failed", str(exc))
            return
        self.log_line(f"[RENDER] Component side: {output}")
        self.log_line(f"[RENDER] Copper side: {copper_output}")
        if renderer_log:
            self.log_line("[RENDER] " + renderer_log)
        self.statusBar().showMessage(f"Exported both SVG board views to {output.parent}")

    def _switch_board_side(self, side: str):
        """Switch cached SVG views without rerouting or changing component locks."""
        if side == "schematic" and not self._schematic_svg:
            return
        self._board_side = side
        self.top_action.setChecked(side == "top")
        self.copper_action.setChecked(side == "copper")
        self.schematic_action.setChecked(side == "schematic")
        svg = (self._schematic_svg if side == "schematic" else
               self._copper_svg if side == "copper" else self._top_svg)
        if side == "schematic" and self._schematic_png:
            self.top_view.show_png(self._schematic_png)
        elif svg:
            self.top_view.show_svg(svg, schematic=(side == "schematic"))
        self.statusBar().showMessage(
            "Schematic — original JSON circuit, rendered without solving."
            if side == "schematic" else
            "Copper side — mirrored underside; red X marks physical cuts."
            if side == "copper" else
            "Component side — transparent top view; cuts aligned to board holes."
        )

    def _show_board(self, top_svg: str):
        """Display renderer output without importing another optimiser."""
        self._top_svg = top_svg
        self._switch_board_side(self._board_side)
        if self.project is not None:
            board = self.project.get("board", {})
            self.log_line(f"[PREVIEW] Source only: {len(board.get('cuts', []))} cuts "
                          f"and {len(board.get('wires', []))} wires; no solver invoked.")

    def _run_tests(self):
        if getattr(sys, "frozen", False):
            self.log_line("[TEST] Skipped: running standalone application.")
            if self.pipeline_run is not None and self.project is not None:
                from pipeline import test_suite_stage_result
                handoff = self.pipeline_run.handoff(self.project, "tests.unittest")
                self._log_handoff(handoff)
                stage_result, findings = test_suite_stage_result(
                    handoff["project"], returncode=None, skipped=True
                )
                stage_result.options.update({
                    "from_stage": handoff["from_stage"],
                    "upstream_finding_ids": handoff["finding_ids"],
                })
                self._record_pipeline_result(stage_result, findings)
            return True

        self.log_line("[TEST] Running repository unittest suite...")
        result = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            cwd=Path(__file__).resolve().parent.parent,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        for line in result.stdout.splitlines():
            self.log_line("[TEST] " + line)
        self.log_line(f"[TEST] Exit code: {result.returncode}")
        if self.pipeline_run is not None and self.project is not None:
            from pipeline import test_suite_stage_result
            handoff = self.pipeline_run.handoff(self.project, "tests.unittest")
            self._log_handoff(handoff)
            stage_result, findings = test_suite_stage_result(
                handoff["project"], returncode=result.returncode, output=result.stdout
            )
            stage_result.options.update({
                "from_stage": handoff["from_stage"],
                "upstream_finding_ids": handoff["finding_ids"],
            })
            self._record_pipeline_result(stage_result, findings)
        return result.returncode == 0

    def _update_lock_summary(self, project: dict | None = None):
        """Show real fixed/edge/slide counts in the on-screen checklist."""
        from placement_policy import is_off_board_component

        source = project if project is not None else self.project
        parts = [
            p for p in (source or {}).get("components", [])
            if isinstance(p, dict) and not is_off_board_component(p)
        ]
        fixed = sum(p.get("locked") is True and not p.get("edge", False)
                    for p in parts)
        edge = sum(p.get("locked") is True and p.get("edge") is True
                   for p in parts)
        slide = sum(p.get("locked") is True and p.get("edge") is True
                    and p.get("slide") is True for p in parts)
        positions = None
        if slide:
            try:
                from math import prod
                from solve.slide_fit import edge_slide_positions
                positions = prod(len(item["positions"])
                                 for item in edge_slide_positions(source))
            except (ValueError, KeyError, TypeError, ImportError) as exc:
                self.log_line(f"[EDGE+SLIDE][WARNING] Cannot count positions: {exc}")
        self.checklist.set_lock_summary(fixed, edge, slide, positions=positions)
        return fixed, edge, slide, positions

    def _ask_lock_settings(self, placed: list[dict[str, Any]]):
        """Review positioned components one at a time with board highlighting."""
        self.presolve_constraints = {}
        if not placed:
            self.log_line("[LOCKS] No positioned parts to review. New parts will be auto-placed.")
        else:
            self.log_line(f"[LOCKS] Asking Fixed / Edge / Slide for {len(placed)} positioned parts.")
            for index, component in enumerate(placed, 1):
                component_id = str(component.get("id"))
                label = str(component.get("label") or component_id)
                highlighted_svg, renderer_log = self._render_component_side(
                    self.project, highlight_component_id=component_id
                )
                self._show_board(highlighted_svg)
                self.statusBar().showMessage(
                    f"Reviewing component {index}/{len(placed)}: {label}"
                )
                self.log_line(f"[LOCKS] Highlighting {label} on the board ({index}/{len(placed)}).")
                if renderer_log:
                    self.log_line("[RENDER] " + renderer_log)
                dialog = LockDialog(component, index, len(placed), self)
                if dialog.exec() != QDialog.DialogCode.Accepted:
                    preview, _ = self._render_component_side(self.project)
                    self._show_board(preview)
                    self.log_line("[LOCKS] Review cancelled; Quick Solve not started.")
                    return

                values = dialog.values()
                self.presolve_constraints[component_id] = values
                self.log_line(
                    f"[LOCKS] {label}: Locked={values['locked']} "
                    f"Edge={values['edge']} Slide={values['slide']} "
                    f"Reposition={values['reposition']}"
                )
                if values["reposition"]:
                    component.pop("boardPos", None)
                    component.pop("flexibleEndPos", None)
                    component["locked"] = False
                    component["edge"] = False
                    component["slide"] = False
                    self.log_line(f"[PLACEMENT] {label} returned to Quick Solve placement pool.")
                else:
                    component["locked"] = True
                    component["edge"] = bool(values["edge"])
                    component["slide"] = bool(values["slide"])

                self._update_lock_summary(self.project)
                preview, renderer_log = self._render_component_side(self.project)
                self._show_board(preview)
                if renderer_log:
                    self.log_line("[RENDER] " + renderer_log)

        fixed, edge, slide, positions = self._update_lock_summary(self.project)
        if slide:
            self.log_line(
                f"[EDGE+SLIDE][WARNING] Quick Solve will take much longer: "
                f"{positions} positions × 24 attempts = "
                f"up to {positions * 24:,} solves. "
                "Stops at first independently verified route."
                if positions is not None else
                "[EDGE+SLIDE][WARNING] Quick Solve will take much longer: "
                "up to 24 attempts per legal position."
            )
        self.log_line(
            f"[LOCKS] {sum(v['locked'] for v in self.presolve_constraints.values())} fixed/edge anchors; "
            f"{sum(v['reposition'] for v in self.presolve_constraints.values())} movable parts."
        )
        self._record_project_stage(
            "PREPARE.constraints", "gui.lock_dialog",
            {"constraints": copy.deepcopy(self.presolve_constraints)},
        )
        self._quick_source = copy.deepcopy(self.project)
        preview, _ = self._render_component_side(self.project)
        self._show_board(preview)
        self.review_locks_action.setEnabled(True)
        self.solve_board()

    def review_locks(self):
        """Review the *input* placement, not the last solved output."""
        from placement_policy import is_off_board_component
        if self._solver_worker is not None and self._solver_worker.isRunning():
            return
        if self.project is None:
            return
        source = copy.deepcopy(
            self.project if self._solved_verified else (self._quick_source or self.project)
        )
        # A successfully solved board is a useful anchor template, not a
        # valid input to the incremental legacy router. Retain any original
        # manual routing, but discard the just-generated cuts and jumpers.
        if self._solved_verified and self._quick_source is not None:
            source["board"]["cuts"] = copy.deepcopy(
                self._quick_source.get("board", {}).get("cuts", [])
            )
            source["board"]["wires"] = copy.deepcopy(
                self._quick_source.get("board", {}).get("wires", [])
            )
        placed = [c for c in source.get("components", [])
                  if isinstance(c, dict) and isinstance(c.get("boardPos"), dict)
                  and not is_off_board_component(c)]
        if not placed:
            QMessageBox.information(
                self, "Review Locks",
                "No on-board parts have positions yet. Load a partially placed "
                "project to choose fixed anchors, or run Quick Solve first."
            )
            return
        self.project = source
        self._solved_verified = False
        self.save_solved_action.setEnabled(False)
        if self.project_path is not None:
            # Recompute input milestones for the newly reviewed source.
            self._restart_quick_pipeline(source, include_constraints=False)
        preview, _ = self._render_component_side(source)
        self._show_board(preview)
        self._ask_lock_settings(placed)

    def _restart_quick_pipeline(self, source: dict[str, Any], *, include_constraints=True):
        """Re-run lightweight input checks when repeating a Quick Solve."""
        if self.project_path is None:
            return
        from pipeline import (
            PipelineRun, electrical_sanity_stage_result,
            presolve_stage_result, project_import_stage_result,
        )
        from prepare.sanity.electrical import run_electrical_sanity
        self.pipeline_run = PipelineRun.create(self.project_path, source)
        result, findings = project_import_stage_result(source, source)
        self._record_assumed_geometry(source, stage=result)
        self._record_pipeline_result(result, findings)
        sanity = run_electrical_sanity(source)
        result, findings = electrical_sanity_stage_result(source, sanity)
        self._record_pipeline_result(result, findings)
        if sanity["status"] != "PASS":
            raise ValueError("Electrical sanity failed before Quick Solve: " +
                             "; ".join(sanity.get("errors", [])[:4]))
        result, findings = presolve_stage_result(source)
        self._record_pipeline_result(result, findings)
        if include_constraints:
            self._record_project_stage(
                "PREPARE.constraints", "gui.lock_dialog",
                {"constraints": copy.deepcopy(self.presolve_constraints)},
                snapshot=source,
            )

    def solve_board(self):
        """Hard stop even if invoked programmatically."""
        self.solve_action.setEnabled(False)
        self.stop_action.setEnabled(False)
        self.log_line("[SOLVER][DISABLED] Native CLI adapter pending; nothing was started.")
        self.statusBar().showMessage("STOPPED BEFORE PASS 1 — no optimiser started.")
        return

    def stop_solve(self):
        """Cooperatively stop the active worker; never force-kill a QThread."""
        worker = self._solver_worker
        if worker is None or not worker.isRunning() or self._stop_requested:
            return
        self._stop_requested = True
        self.stop_action.setEnabled(False)
        worker.requestInterruption()
        self.log_line("[SOLVE][STOP] Cancellation requested; discarding current trial.")
        self.statusBar().showMessage(
            "Stopping Quick Solve — current search is being interrupted safely."
        )

    def _exit_requested(self):
        self._close_when_idle = True
        self.close()

    @staticmethod
    def _clock_text(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        return f"{total // 60}m {total % 60:02d}s"

    def _update_solve_clock(self):
        if self._solve_started is None:
            return
        elapsed = max(0.0, perf_counter() - self._solve_started)
        if self._worker_time_stats:
            # Parallel jobs do not finish in total-attempt order. The
            # slowest worker's unfinished share determines wall-clock ETA;
            # dividing global elapsed by global completed is misleading.
            rates = [s["seconds"] / s["done"] for s in self._worker_time_stats.values()
                     if s["done"] > 0]
            fallback_rate = max(rates) if rates else None
            estimates = []
            for stats in self._worker_time_stats.values():
                if stats["finished"]:
                    continue
                remaining_slots = max(0, stats["budget"] - stats["done"])
                rate = (stats["seconds"] / stats["done"] if stats["done"]
                        else fallback_rate)
                if rate is not None:
                    estimates.append(remaining_slots * rate)
            if estimates:
                remaining = self._clock_text(max(estimates)) + " (approx., slowest worker)"
            elif fallback_rate is None and self._solve_done < self._solve_budget:
                remaining = "calibrating from each worker"
            else:
                remaining = "0m 00s (workers finished)"
        elif self._solve_done:
            estimate = elapsed / self._solve_done * max(0, self._solve_budget - self._solve_done)
            remaining = self._clock_text(estimate) + " (approx., full budget)"
        else:
            remaining = "calibrating from first completed attempt"
        self.solve_eta.setText(
            f"Elapsed: {self._clock_text(elapsed)}   Estimated remaining: {remaining}"
        )

    def _solve_attempted(self, attempt: dict[str, Any]):
        if self._stop_requested:
            return
        if attempt.get("mode") == "parallel":
            completed = int(attempt.get("completed", 0))
            budget = max(1, int(attempt.get("budget", 24)))
            self._solve_done = max(self._solve_done, completed)
            self._solve_budget = max(self._solve_budget, budget)
            self._solve_found = max(
                self._solve_found, int(attempt.get("solutions_found", 0))
            )
            self.solve_progress.setRange(0, self._solve_budget)
            self.solve_progress.setValue(self._solve_done)
            worker = int(attempt.get("worker", 1))
            workers = int(attempt.get("workers", self._recommended_workers))
            stats = self._worker_time_stats.setdefault(worker, {
                "done": 0, "budget": max(1, (self._solve_budget + workers - 1) // workers),
                "seconds": 0.0, "finished": False,
            })
            if attempt.get("worker_budget") is not None:
                stats["budget"] = int(attempt["worker_budget"])
            if attempt.get("worker_completed") is not None:
                stats["done"] = max(stats["done"], int(attempt["worker_completed"]))
            elif not attempt.get("worker_finished"):
                stats["done"] += 1
            if attempt.get("worker_finished"):
                stats["finished"] = True
            else:
                stats["seconds"] += max(0.0, float(attempt.get("seconds", 0.0)))
            last = attempt.get("last") or {}
            repair_target = last.get("repair_target")
            if repair_target:
                self.solve_activity.setText(
                    f"Worker {worker}/{workers}: clearance repair for "
                    f"{repair_target} → {last.get('routing', 'routing')} · "
                    f"{self._solve_found} verified candidates"
                )
            else:
                self.solve_activity.setText(
                    f"Worker {worker}/{workers}: {last.get('placement', 'placing')} "
                    f"→ {last.get('routing', 'routing')} · "
                    f"{self._solve_found} verified candidates"
                )
            self._update_solve_clock()
            if attempt.get("worker_finished"):
                self.log_line(f"[WORKER {worker}/{workers}] Finished its assigned budget.")
            else:
                self.log_line(
                    f"[WORKER {worker}/{workers}][ATTEMPTS] "
                    f"{self._solve_done}/{self._solve_budget} · "
                    f"route={last.get('routing')} · "
                    + (f"targeted-repair={repair_target} · " if repair_target else "")
                    + f"{float(attempt.get('seconds', 0)):.2f}s"
                )
            self.statusBar().showMessage(
                f"Quick Solve: {workers} CPU processes · "
                f"{self._solve_done}/{self._solve_budget} attempts · "
                f"{self._solve_found}/2 candidates; see Overview for ETA."
            )
            return
        if attempt.get("mode") == "edge_slide_variant":
            completed = int(attempt["completed"])
            budget = int(attempt["budget"])
            slot = int(attempt["position_index"])
            total = int(attempt["positions_total"])
            variant = int(attempt["variant_index"])
            per_position = int(attempt["variants_per_position"])
            last = attempt.get("last", {})
            self.statusBar().showMessage(
                f"Edge+Slide position {slot}/{total}, "
                f"Quick Solve attempt {variant}/{per_position}; "
                f"up to {budget:,} total attempts, stops on verified success."
            )
            self.log_line(
                f"[EDGE+SLIDE][POSITION {slot}/{total}][ATTEMPT "
                f"{variant}/{per_position}] "
                f"placement={last.get('placement')} "
                f"routing={last.get('routing')} "
                f"time={float(attempt['seconds']):.2f}s"
            )
            return
        completed = int(attempt["completed"])
        budget = int(attempt["budget"])
        seconds = float(attempt["seconds"])
        self._solve_attempt_seconds.append(seconds)
        average = sum(self._solve_attempt_seconds) / len(self._solve_attempt_seconds)
        remaining = max(0, budget - completed)
        maximum_seconds = round(average * remaining)
        self.statusBar().showMessage(
            f"Quick Solve {completed}/{budget} attempts · last {seconds:.1f}s · "
            f"up to ~{maximum_seconds}s if all remaining attempts run "
            "(estimate, single worker)."
        )
        last = attempt.get("last", {})
        if attempt.get("mode") == "edge_slide":
            self.log_line(
                f"[EDGE+SLIDE][POSITION {completed}/{budget}] "
                f"{last.get('slide_positions')} | "
                f"placement={last.get('placement')} routing={last.get('routing')} "
                f"time={seconds:.2f}s"
                f" | variants={attempt.get('last', {}).get('variants_checked')}/24"
            )
            self.statusBar().showMessage(
                f"Edge+Slide {completed}/{budget} positions checked · "
                f"stops on first verified route."
            )
        else:
            self.log_line(
                f"[SOLVE][ATTEMPT {completed}/{budget}] "
                f"placement={last.get('placement')} routing={last.get('routing')} "
                f"time={seconds:.2f}s · remaining-budget estimate ~{maximum_seconds}s"
            )

    def _solve_completed(self, outcome: dict[str, Any]):
        """On the GUI thread, accept only a verified board and redraw it."""
        status = outcome.get("status", "FAILED")
        portfolio = outcome.get("portfolio") or {}
        if portfolio:
            found = int(portfolio.get("solutions_found", 0))
            self._solve_found = found
            self.solve_activity.setText(
                f"Search finished · {found} / 2 distinct verified layouts; "
                + ("best provisional quality selected" if found else "no verified route")
            )
            self.solve_worker_status.setText(
                f"{portfolio.get('workers', 1)} CPU processes · "
                f"{portfolio.get('attempts_used', 0)}/"
                f"{portfolio.get('attempts_budget', 24)} possible attempts"
            )
            self.log_line(
                f"[PORTFOLIO] {found} distinct verified layout(s) compared "
                f"across {portfolio.get('workers')} processes; "
                f"fixed budget {portfolio.get('attempts_budget')}. "
                "Provisional quality is not physical sign-off."
            )
            for index, candidate in enumerate(portfolio.get("candidate_summaries", []), 1):
                score = candidate.get("provisional_score")
                self.log_line(
                    f"[QUALITY][CANDIDATE {index}] "
                    f"variant={candidate.get('placement_variant')} · "
                    f"score={float(score):.1f}/100 · "
                    f"contacts={candidate.get('nominal_contacts')} · "
                    f"overhangs={candidate.get('nominal_board_overhangs')} · "
                    f"cuts={candidate.get('cuts')} · wires={candidate.get('wires')}"
                    if score is not None else
                    f"[QUALITY][CANDIDATE {index}] score unavailable"
                )
            if portfolio.get("worker_pids"):
                self.log_line(
                    f"[MULTICORE] Real solver process IDs: {portfolio['worker_pids']}"
                )
            if portfolio.get("worker_strategies"):
                self.log_line(
                    f"[MULTICORE] Worker strategies: {portfolio['worker_strategies']}"
                )
        if self._stop_requested:
            # Even if a verification result raced with the Stop click, never
            # publish a board after the user requested cancellation.
            status = "CANCELLED"
        if status == "CANCELLED":
            self._solved_verified = False
            self.save_solved_action.setEnabled(False)
            self._set_board_summary(
                "Quick Solve stopped · original board retained", level="neutral",
            )
            self.log_line("[SOLVE][CANCELLED] Stopped by user; no partial "
                          "layout or routes were accepted.")
            self.statusBar().showMessage(
                "Quick Solve stopped — original board retained."
            )
            return
        slide_search = outcome.get("slide_search")
        if slide_search:
            self.log_line(
                f"[EDGE+SLIDE] {slide_search['components']} | "
                f"checked {slide_search['positions_checked']}/"
                f"{slide_search['positions_total']} position(s)"
                + (f" | placement attempts={slide_search['variants_checked']}/"
                   f"{slide_search['variants_budget']}"
                   if 'variants_budget' in slide_search else "")
                + (f" | selected={slide_search['selected']}"
                   if slide_search.get("selected") else "")
            )
        else:
            self.log_line(f"[SOLVE] {status} — {outcome.get('attempts_used', 0)} placement attempt(s).")
        if status != "ROUTED":
            self._set_board_summary(
                (f"{status} · checked all {slide_search['positions_total']} "
                 "Edge+Slide positions; see Activity"
                 if slide_search else
                 f"{status} · no verified board found in the search budget"),
                level="failed",
            )
            self.sidebar_tabs.setCurrentIndex(1)
            for error in outcome.get("errors", []):
                self.log_line("[SOLVE][ERROR] " + str(error))
            failure = outcome.get("best_failure")
            if failure:
                self.log_line(f"[SOLVE] Best failed trial: {failure}")
            if self.pipeline_run is not None and self._solve_input is not None:
                from pipeline import route_stage_result
                handoff = self.pipeline_run.handoff(self._solve_input, "solve.placement_feedback")
                rejected = {
                    "status": status, "project": handoff["project"],
                    "errors": list(outcome.get("errors", [])), "warnings": [],
                    "cuts_added": 0, "wires_added": 0, "verification": None,
                }
                stage, findings = route_stage_result(handoff["project"], rejected)
                stage.status = "failed"
                stage.options["router"] = "hole_graph"
                self._record_pipeline_result(stage, findings)
            self.statusBar().showMessage(
                (str((outcome.get("errors") or ["No Edge+Slide solution"])[0])[:350]
                 if slide_search else "No verified route found; original preview retained.")
            )
            return

        solved = outcome["project"]
        # Compute sidecar-backed advisory geometry for the ACTUAL solved
        # placement. Do not overwrite the source project's collector sidecar.
        from geometry_sidecar import make_document, assess_saved_board
        geometry_document = make_document(solved)
        geometry_assessment = assess_saved_board(solved, geometry_document)
        self._assumed_geometry = geometry_document
        contact_count = self._log_assumed_contacts(
            geometry_assessment, stage="SOLVED"
        )
        selected_quality = outcome.get("quality_selection") or {}
        overhangs = selected_quality.get("nominal_board_overhangs") or []
        if overhangs:
            self.log_line(
                "[BOARD EDGE][ASSUMED OVERHANG] The following package outline(s) "
                "extend beyond the nominal stripboard perimeter: "
                + ", ".join(str(label) for label in overhangs)
                + ". Do not treat electrical PASS as physical buildability."
            )
        provisional = selected_quality.get("provisional_score")
        if provisional is not None:
            found = int((outcome.get("portfolio") or {}).get("solutions_found", 1))
            self.solve_activity.setText(
                f"Best of {found} verified layout(s): {float(provisional):.1f}/100 "
                f"provisional quality · {contact_count} nominal contact warnings · "
                f"{len(overhangs)} nominal board-edge overhang(s)"
            )
            self.log_line(
                f"[QUALITY][SELECTED] {float(provisional):.1f}/100 provisional · "
                f"{contact_count} nominal contacts · "
                f"assumed geometry {geometry_assessment['status']}."
            )
        self.log_line(
            f"[2.5D][SOLVED][{geometry_assessment['status']}] "
            f"{geometry_assessment['profile']} | "
            f"{len(geometry_assessment['wire_results'])} jumpers checked | "
            "conditional assumption, not physical sign-off."
        )
        if geometry_assessment["status"] == "HARD_CONFLICT":
            self.log_line(
                f"[2.5D][HARD_CONFLICT] "
                f"{geometry_assessment['counts']['FAIL_PROVEN']} jumper(s) "
                "have independently reproduced exact-grid conflicts."
            )
            for finding in geometry_assessment["findings"]:
                if finding["verdict"] == "FAIL_PROVEN":
                    self.log_line(
                        f"[2.5D][HARD_CONFLICT] wire={finding['wire']} "
                        f"reason={finding['reason']} "
                        f"obstacle={finding.get('obstacle', '')}"
                    )
        placement = outcome["placement"]
        spacing = placement.get("report", {})
        used_spacing = spacing.get("body_spacing_used")
        requested_spacing = spacing.get("body_spacing_requested", self._body_spacing_holes)
        unmet_spacing = (used_spacing is not None
                         and int(used_spacing) < int(requested_spacing))
        if used_spacing is not None:
            level = "PREFERRED" if used_spacing == requested_spacing else "COMPACT_FALLBACK"
            self.log_line(
                f"[PLACEMENT][SPACING][{level}] requested={requested_spacing} "
                f"free hole(s), used={used_spacing} | "
                f"nominal contacts={contact_count} | "
                "assumed package geometry, not measured clearance."
            )
        if unmet_spacing:
            self.log_line(
                f"[SPACING][NOT_MET] Requested {requested_spacing} free hole(s), "
                f"achieved {used_spacing}; a verified compact route was selected. "
                "This is NOT evidence of the requested physical clearance."
            )
            self.solve_activity.setText(
                f"SPACING NOT MET: requested {requested_spacing} hole(s), "
                f"achieved {used_spacing}; {contact_count} nominal contacts. "
                "Electrical PASS only."
            )
        routing = outcome["routing"]
        verification = outcome["verification"]
        if self.pipeline_run is not None and self._solve_input is not None:
            from pipeline import (
                quick_fit_stage_result, route_stage_result, verification_stage_result,
            )
            place_handoff = self.pipeline_run.handoff(
                self._solve_input, "solve.placement_feedback",
            )
            self._log_handoff(place_handoff)
            place_result, findings = quick_fit_stage_result(
                place_handoff["project"], placement,
            )
            place_result.module = "solve.placement_feedback"
            place_result.options.update({
                "from_stage": place_handoff["from_stage"],
                "upstream_finding_ids": place_handoff["finding_ids"],
                "router": "hole_graph",
                "attempts_used": outcome["attempts_used"],
            })
            self._record_pipeline_result(place_result, findings)

            route_handoff = self.pipeline_run.handoff(placement["project"], "solve.hole_router")
            self._log_handoff(route_handoff)
            route_result, findings = route_stage_result(
                route_handoff["project"], routing,
            )
            route_result.module = "solve.hole_router"
            route_result.report["assumed_25d_clearance"] = copy.deepcopy(geometry_assessment)
            route_result.report["assumed_geometry_preset"] = geometry_document["geometry"]["preset"]
            route_result.options.update({
                "from_stage": route_handoff["from_stage"],
                "upstream_finding_ids": route_handoff["finding_ids"],
                "measured_clearance_certified": False,
            })
            self._record_pipeline_result(route_result, findings)
            verify_handoff = self.pipeline_run.handoff(solved, "solve.verify")
            self._log_handoff(verify_handoff)
            verify_result, findings = verification_stage_result(
                verify_handoff["project"], verification,
            )
            verify_result.options.update({
                "from_stage": verify_handoff["from_stage"],
                "upstream_finding_ids": verify_handoff["finding_ids"],
            })
            self._record_pipeline_result(verify_result, findings)

        self.project = solved
        counts = verification["counts"]
        hard_conflict = geometry_assessment["status"] == "HARD_CONFLICT"
        advisory_risk = bool(contact_count or overhangs or unmet_spacing)
        self._set_board_summary(
            (f"Electrical PASS · 2.5D HARD CONFLICT — inspect Activity. "
             f"{len(solved['board']['cuts'])} cuts, "
             f"{len(solved['board']['wires'])} jumpers."
             if hard_conflict else
             f"Electrical PASS · requested spacing NOT MET ({requested_spacing} → "
             f"{used_spacing} holes) · physical fit UNVERIFIED"
             if unmet_spacing else
             f"Electrical PASS · {len(overhangs)} nominal board overhang(s) · "
             "physical fit UNVERIFIED"
             if overhangs else
             f"Electrical PASS · {contact_count} nominal contacts marked RED · "
             "physical fit UNVERIFIED"
             if contact_count else
             f"Electrical PASS · {len(solved['board']['cuts'])} cuts · "
             f"{len(solved['board']['wires'])} jumpers · "
             f"{outcome['attempts_used']} placement attempt(s) · physical sign-off pending"),
            level="failed" if hard_conflict else
                  "neutral" if advisory_risk else "pass",
        )
        self.sidebar_tabs.setCurrentIndex(0)
        self.log_line(
            f"[ROUTING] ROUTED: {len(solved['board']['cuts'])} cuts, "
            f"{len(solved['board']['wires'])} jumpers; "
            f"{counts['nets_checked']} nets, 0 shorts and 0 opens."
        )
        self.log_line(
            f"[VERIFY] Electrical PASS | grid jumper audit "
            f"{outcome['grid_audit']['status']} | grid physical audit "
            f"{outcome['physical_audit']['status']}."
        )
        for warning in outcome.get("warnings", []):
            self.log_line("[PHYSICAL][UNCERTIFIED] " + warning)
        self.log_line("[PHYSICAL] Measured package clearance and cut-tool access are NOT certified.")
        if contact_count:
            affected = sorted({
                str(label)
                for finding in geometry_assessment.get("contact_findings", [])
                for label in finding.get("components", [])
            })
            self.log_line(
                f"[DIAGNOSTIC][RECOMMENDATION][EXTRA_ROOM] "
                f"{contact_count} assumed component-body/pad proximity finding(s)"
                + (f" involving {', '.join(affected)}." if affected else ".")
                + " Consider trying another layout with extra room between parts. "
                "The current electrical PASS remains valid and the solved board "
                "is retained; nominal body sizes may be exaggerated. "
                "The bounded portfolio has searched the requested spacing "
                "and compact fallbacks; no contact-free verified alternative "
                "was selected in this run. Verify actual package sizes before assembly."
            )
        try:
            top_svg, renderer_log = self._render_component_side(solved)
            self._show_board(top_svg)
            self._solved_verified = True
            self.save_solved_action.setEnabled(True)
            if renderer_log:
                self.log_line("[RENDER] " + renderer_log)
            self.log_line("[RENDER] Solved component and mirrored copper sides are ready.")
            self.statusBar().showMessage(
                ("Electrical PASS but 2.5D HARD CONFLICT: inspect Activity before building."
                 if hard_conflict else
                 f"Electrical PASS, but {contact_count} nominal contacts are RED; "
                 "inspect Activity and verify actual package dimensions."
                 if contact_count else
                 f"Electrical PASS — {len(solved['board']['cuts'])} cuts, "
                 f"{len(solved['board']['wires'])} jumpers. Physical cut access unverified.")
            )
        except Exception as exc:
            self.log_line(f"[RENDER][ERROR] Could not show solved board: {exc}")
            self.statusBar().showMessage("Solved and verified, but board rendering failed.")
            QMessageBox.warning(self, "Solved board rendering failed", str(exc))

    def _solve_crashed(self, message: str):
        if self._stop_requested:
            self.log_line("[SOLVE][CANCELLED] Worker stopped; previous board retained.")
            return
        self.log_line("[SOLVE][ERROR] " + message)
        self._set_board_summary("Quick Solve error — see Activity", level="failed")
        self.sidebar_tabs.setCurrentIndex(1)
        self.statusBar().showMessage("Solve error; previous preview retained.")
        QMessageBox.warning(self, "Solve failed", message.splitlines()[-1])

    def _solve_finished(self):
        self._solve_clock.stop()
        self._update_solve_clock()
        self._solve_started = None
        self._solver_worker = None
        self._solve_input = None
        self._stop_requested = False
        self.stop_action.setEnabled(False)
        self.load_action.setEnabled(True)
        self.render_action.setEnabled(False)  # Import-only milestone
        self.solve_action.setEnabled(False)  # Import-only milestone; never arm solver
        self.review_locks_action.setEnabled(False)
        if self._close_when_idle:
            self.close()

    def save_solved_json(self):
        """Save the exact verified routed project; never overwrite source."""
        if not self._solved_verified or self.project is None:
            QMessageBox.information(self, "Save Solved JSON", "Solve a board first.")
            return
        folder = self.project_path.parent if self.project_path else default_project_directory()
        stem = self.project_path.stem if self.project_path else "board"
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save verified routed board",
            str(folder / f"{stem}-autorouted.json"),
            "Project JSON (*.json)",
        )
        if not filename:
            return
        path = Path(filename)
        if path.suffix.lower() != ".json":
            path = path.with_suffix(".json")
        if self.project_path is not None and path.resolve() == self.project_path.resolve():
            QMessageBox.warning(self, "Source protected", "Choose a new file; the source JSON will not be overwritten.")
            return
        try:
            payload = json.dumps(self.project, indent=2, ensure_ascii=False) + "\n"
            temp = path.with_name(path.name + ".tmp")
            temp.write_text(payload, encoding="utf-8")
            temp.replace(path)
            # Match saved routing to an integrity-bound physical assumption
            # sidecar, without rewriting or replacing the input source JSON.
            from geometry_sidecar import load_or_create
            load_or_create(self.project, path, persist=True)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self, "Save failed", str(exc))
            return
        self.log_line(f"[SAVE] Verified routed board: {path}")
        self.statusBar().showMessage(f"Saved solved board: {path}")

    def _refresh_checklist(self):
        """Map actual pipeline stage names to visible milestones."""
        if self.pipeline_run is None:
            self.checklist.reset()
            return
        stage_keys = {
            "IN.project_import": "COLLECT",
            "IN.collect": "COLLECT",
            "PREPARE.electrical": "SANITY",
            "PREPARE.presolve": "PRE-SOLVE",
            "PREPARE.constraints": "CONSTRAINTS",
            "SOLVE.quick_fit": "QUICK FIT",
            "SOLVE.route": "ROUTING",
            "VERIFY.independent": "VERIFY",
        }
        states = {}
        for result in self.pipeline_run.context.stages.values():
            key = stage_keys.get(result.stage)
            if key is None:
                continue
            status = str(result.status).lower()
            if status in ("failed", "blocked", "stale", "error"):
                states[key] = "failed"
            elif status == "completed":
                report = result.report
                if result.stage in ("PREPARE.electrical", "VERIFY.independent"):
                    states[key] = "done" if report.get("status") == "PASS" else "failed"
                else:
                    states[key] = "done"
        self.checklist.update_states(states)

    def _record_pipeline_result(self, result, findings):
        if self.pipeline_run is None:
            return
        self.pipeline_run.record_stage(result, findings)
        self._refresh_checklist()
        group = result.extra.get("workflow_stage", result.stage)
        self.log_line(
            f"[PIPELINE][{group}] {result.stage}: {result.summary or result.status}; "
            f"input={str(result.input_project_sha256 or 'n/a')[:12]} "
            f"output={str(result.output_project_sha256 or 'n/a')[:12]}; "
            f"state saved to {self.pipeline_run.state_path.name}"
        )

    def _record_project_stage(self, stage: str, module: str, report: dict[str, Any],
                              *, snapshot: dict[str, Any] | None = None):
        project = self.project if snapshot is None else snapshot
        if self.pipeline_run is None or project is None:
            return
        from pipeline import StageResult, project_sha256
        current_hash = project_sha256(project)
        result = StageResult(
            stage=stage, status="completed", module=module,
            input_project_sha256=self.pipeline_run.context.project_sha256,
            output_project_sha256=current_hash,
            report=copy.deepcopy(report),
            summary=f"{stage}: recorded {len(report.get('constraints', {}))} component constraint(s).",
        )
        self._record_pipeline_result(result, [])

    def load_json(self):
        start_dir = self.project_path.parent if self.project_path else default_project_directory()
        filename, _ = QFileDialog.getOpenFileName(
            self, "Load Route-Mate project", str(start_dir),
            "Project JSON (*.json);;All files (*)",
        )
        if not filename:
            return
        path = Path(filename)
        self.log_line("")
        self.log_line(f"--- LOAD PROJECT: {path.name} ---")
        try:
            source = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(source, dict):
                raise ValueError("Project JSON root must be an object.")

            # Collector validation and explicit board-size collection.
            from collect import validate_project
            project = validate_project(copy.deepcopy(source))
            collect_warnings = list(project.pop("_collectWarnings", []))
            for warning in collect_warnings:
                self.log_line("[COLLECT][WARN] " + warning)
            board_dialog = BoardSizeDialog(project.get("board", {}), self)
            if board_dialog.exec() != QDialog.DialogCode.Accepted:
                self.log_line("[COLLECT] Board dimensions cancelled; project not advanced.")
                return
            dimensions = board_dialog.values()
            spacing_dialog = SpacingDialog(self, selected=self._body_spacing_holes)
            if spacing_dialog.exec() != QDialog.DialogCode.Accepted:
                self.log_line("[SPACING] Cancelled; project not advanced.")
                return
            self._body_spacing_holes = spacing_dialog.value()
            self.log_line(
                f"[SPACING] Selected {('Off', 'Normal', 'Wider')[self._body_spacing_holes]} "
                f"({self._body_spacing_holes} free hole(s))."
            )
            if dimensions["wantedRowsMode"] == "fixed" and dimensions["wantedRows"] > dimensions["actualRows"]:
                raise ValueError("Fixed preferred rows cannot exceed actual physical rows.")
            if dimensions["wantedColsMode"] == "fixed" and dimensions["wantedCols"] > dimensions["actualCols"]:
                raise ValueError("Fixed preferred columns cannot exceed actual physical columns.")
            project["board"].update(dimensions)
            project["board"]["rows"] = dimensions["actualRows"]
            project["board"]["cols"] = dimensions["actualCols"]
            self.project_path = path
            from pipeline import PipelineRun, project_import_stage_result
            self.checklist.reset()
            self.pipeline_run = PipelineRun.create(
                path, source,
                sources=[{"kind": "project_json", "path": str(path.resolve())}],
            )
            import_result, import_findings = project_import_stage_result(
                source, project,
                warnings=collect_warnings,
                options={**dimensions, "body_spacing_holes": self._body_spacing_holes},
            )
            self._record_assumed_geometry(project, stage=import_result)
            self._record_pipeline_result(import_result, import_findings)
            self.log_line(
                f"[COLLECT] Actual board {dimensions['actualRows']} x {dimensions['actualCols']}; "
                f"preferred rows {dimensions['wantedRows']} ({dimensions['wantedRowsMode']}), "
                f"columns {dimensions['wantedCols']} ({dimensions['wantedColsMode']})."
            )
            self.log_line(
                f"[COLLECT] Components={len(project['components'])}, Nets={len(project['nets'])}, "
                f"Assignments={len(project['netAssignments'])}"
            )

            from prepare.sanity.electrical import run_electrical_sanity
            sanity_handoff = self.pipeline_run.handoff(project, "prepare.sanity.electrical")
            self._log_handoff(sanity_handoff)
            sanity_input = sanity_handoff["project"]
            sanity = run_electrical_sanity(sanity_input)
            from pipeline import electrical_sanity_stage_result
            sanity_result, sanity_findings = electrical_sanity_stage_result(sanity_input, sanity)
            sanity_result.options.update({
                "from_stage": sanity_handoff["from_stage"],
                "upstream_finding_ids": sanity_handoff["finding_ids"],
            })
            self._record_pipeline_result(sanity_result, sanity_findings)
            self.log_line(f"[SANITY] Electrical integrity: {sanity['status']}")
            for error in sanity["errors"]:
                self.log_line("[SANITY][ERROR] " + error)
            for warning in sanity["warnings"]:
                self.log_line("[SANITY][WARN] " + warning)
            if sanity["status"] != "PASS":
                QMessageBox.warning(self, "Collector sanity checks failed",
                                    "The project failed electrical sanity checks. See the log.")
                return

            # PRE-SOLVE is a read-only PREPARE report, persisted in the existing sidecar.
            from pipeline import presolve_stage_result
            presolve_handoff = self.pipeline_run.handoff(project, "prepare.presolve")
            self._log_handoff(presolve_handoff)
            presolve_result, presolve_findings = presolve_stage_result(presolve_handoff["project"])
            presolve_result.options.update({
                "from_stage": presolve_handoff["from_stage"],
                "upstream_finding_ids": presolve_handoff["finding_ids"],
            })
            self._record_pipeline_result(presolve_result, presolve_findings)
            candidate = presolve_result.report["board"]
            self.log_line(
                f"[PRE-SOLVE] {len(presolve_result.report['components'])} components; "
                f"placement candidate={candidate['placement_candidate_rows']} x "
                f"{candidate['placement_candidate_cols']} "
                f"({candidate['placement_candidate_status']}); "
                "physical fit NOT verified."
            )

            from placement_policy import is_off_board_component

            # Preserve and display the positions already present in the imported project.
            # Quick Fit works on a copy and must not overwrite the imported source JSON.
            components = project["components"]
            placed = [component for component in components
                      if isinstance(component.get("boardPos"), dict)
                      and not is_off_board_component(component)]
            on_board = [component for component in components
                        if not is_off_board_component(component)]
            self.log_line(
                f"[PLACEMENT] Existing layout: {len(placed)} positioned; "
                f"{len(on_board)} on-board; "
                f"{len(components) - len(on_board)} off-board/excluded."
            )
            for component in placed:
                self.log_line(
                    f"[PLACEMENT] {component.get('label') or component.get('id')}: "
                    f"boardPos={component.get('boardPos')} rotation={component.get('rotation', 0)}"
                )

            self.project = project
            self.project_path = path
            self._solved_verified = False
            self._quick_source = None
            self.solve_action.setEnabled(False)
            self._cache_schematic_preview(project)
            self.save_solved_action.setEnabled(False)
            self.project_summary.setText(
                f"{path.name}\n{len(project['components'])} components · "
                f"{len(project['nets'])} nets"
            )
            self._set_board_summary("Imported · reviewing placement constraints", project=project)
            top_svg, renderer_log = self._render_component_side(project)
            self._show_board(top_svg)
            self.log_line("[RENDER] Existing component-side layout rendered with alternating row bands.")
            if renderer_log:
                self.log_line("[RENDER] " + renderer_log)

            # Unit tests belong in CI, not on every user project import.
            self._ask_lock_settings(placed)
        except Exception as exc:
            self.log_line(f"[ERROR] {type(exc).__name__}: {exc}")
            self.log_line(traceback.format_exc())
            QMessageBox.critical(self, "Could not load project", str(exc))

    def closeEvent(self, event):
        if self._solver_worker is not None and self._solver_worker.isRunning():
            self._close_when_idle = True
            self.stop_solve()
            event.ignore()
            self.statusBar().showMessage(
                "Exit requested — stopping active solve safely before closing."
            )
            return
        if self._speed_probe_worker is not None and self._speed_probe_worker.isRunning():
            # Do not destroy a live QThread; retry close when calibration ends.
            self._close_when_idle = True
            event.ignore()
            self.statusBar().showMessage(
                "Exit requested — startup speed calibration is finishing."
            )
            return
        event.accept()


def main():
    app = QApplication(sys.argv)
    # Use the platform-selected concrete font instead of Qt’s unresolved generic Sans-serif alias.
    app.setFont(QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont))
    app.setApplicationName("Route-Mate")
    window = RouteMateWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())