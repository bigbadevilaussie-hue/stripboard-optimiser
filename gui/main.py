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

from gui.work_directory import (
    WORK_ROOT, PASS_ONE, PASS_TWO, ensure_work,
    clear_started_pass, read_pass_one, prepare_pass_two,
    ensure_workspace_root, project_workspace, list_project_workspaces,
    adopt_matching_legacy_pass_one,
    pass_one_budget_dir, winner_budget_dir, campaign_existing_files,
    clear_pass_one_budget, pass_one_campaign_sources,
)

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
from PySide6.QtGui import QAction, QBrush, QColor, QFontDatabase, QPainter, QPixmap, QIcon, QIntValidator
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtSvgWidgets import QGraphicsSvgItem
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QDialog, QDialogButtonBox, QFileDialog,
    QFormLayout, QGraphicsScene, QGraphicsView, QGroupBox, QHBoxLayout,
    QLabel, QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QRadioButton, QComboBox, QInputDialog,
    QLineEdit, QSplitter, QToolBar, QVBoxLayout, QWidget, QProgressBar, QTabWidget, QFrame, QSplashScreen, QScrollArea,
)


from gui.arctic_theme import apply_arctic_theme


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

class DimensionBox(QWidget):
    """Plain numeric text field with live ✓/✕ indicator. No spin wheels."""

    def __init__(self, value, parent=None):
        super().__init__(parent)
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        self.entry = QLineEdit(self)
        self.entry.setObjectName("dimensionEntry")
        self.entry.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.entry.setValidator(QIntValidator(1, 500, self.entry))
        self.entry.setPlaceholderText("1–500")
        self.entry.setMinimumWidth(78)
        try:
            self.entry.setText(str(int(value)))
        except (TypeError, ValueError):
            self.entry.setText("")
        row.addWidget(self.entry, 1)
        self.check = QLabel("✓", self)
        self.check.setObjectName("dimensionCheck")
        self.check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.check.setFixedWidth(21)
        row.addWidget(self.check)

    def number(self):
        if not self.entry.hasAcceptableInput():
            return None
        return int(self.entry.text())

    def value(self):
        number = self.number()
        if number is None:
            raise ValueError("Board dimensions must be whole numbers from 1 to 500")
        return number

    def setValue(self, number):
        self.entry.setText(str(number))

    def set_valid(self, valid):
        self.check.setText("✓" if valid else "✕")
        self.check.setStyleSheet(
            "font-size: 17px; font-weight: 800; "
            + ("color: #168d95;" if valid else "color: #ce5265;")
        )
        self.entry.setStyleSheet(
            "border: 1px solid " + ("#bcd4e8" if valid else "#ce5265") + ";"
        )


class BoardSizeDialog(QDialog):
    """Validated text boxes replace wheel-based board-size spin controls."""

    def __init__(self, board: dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Board dimensions")
        self.setModal(True)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.actual_rows = DimensionBox(board.get("actualRows", board.get("rows", 24)))
        self.actual_cols = DimensionBox(board.get("actualCols", board.get("cols", 56)))
        self.preferred_rows = DimensionBox(board.get("wantedRows", board.get("rows", 24)))
        self.preferred_cols = DimensionBox(board.get("wantedCols", board.get("cols", 56)))
        self.rows_mode = self._mode(board.get("wantedRowsMode", "fixed"))
        self.cols_mode = self._mode(board.get("wantedColsMode", "fixed"))
        form.addRow("Actual physical rows:", self.actual_rows)
        form.addRow("Actual physical columns:", self.actual_cols)
        rows_box = QWidget()
        rows_layout = QHBoxLayout(rows_box)
        rows_layout.setContentsMargins(0, 0, 0, 0)
        rows_layout.setSpacing(8)
        rows_layout.addWidget(self.preferred_rows, 1)
        rows_layout.addWidget(self.rows_mode)
        cols_box = QWidget()
        cols_layout = QHBoxLayout(cols_box)
        cols_layout.setContentsMargins(0, 0, 0, 0)
        cols_layout.setSpacing(8)
        cols_layout.addWidget(self.preferred_cols, 1)
        cols_layout.addWidget(self.cols_mode)
        form.addRow("Preferred rows:", rows_box)
        form.addRow("Preferred columns:", cols_box)
        layout.addLayout(form)
        layout.addWidget(QLabel("Enter whole numbers from 1 to 500. ✓ means valid."))
        self.feedback = QLabel("")
        self.feedback.setWordWrap(True)
        self.feedback.setStyleSheet("color: #ac3553; font-size: 11px;")
        layout.addWidget(self.feedback)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self._ok = buttons.button(QDialogButtonBox.StandardButton.Ok)
        self._ok.setObjectName("nextActionButton")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for field in (self.actual_rows, self.actual_cols,
                      self.preferred_rows, self.preferred_cols):
            field.entry.textChanged.connect(self._update_validation)
        self.rows_mode.currentIndexChanged.connect(self._update_validation)
        self.cols_mode.currentIndexChanged.connect(self._update_validation)
        self._update_validation()

    @staticmethod
    def _mode(value):
        widget = QComboBox()
        widget.addItem("Fixed", "fixed")
        widget.addItem("Max", "max")
        index = widget.findData(value if value in ("fixed", "max") else "fixed")
        widget.setCurrentIndex(max(0, index))
        return widget

    def _update_validation(self, *_):
        fields = (self.actual_rows, self.actual_cols,
                  self.preferred_rows, self.preferred_cols)
        numbers = [field.number() for field in fields]
        valid = [number is not None for number in numbers]
        errors = []
        if not all(valid):
            errors.append("Every dimension must be a whole number from 1 to 500.")
        if (valid[0] and valid[2] and self.rows_mode.currentData() == "fixed"
                and numbers[2] > numbers[0]):
            valid[2] = False
            errors.append("Fixed preferred rows cannot exceed physical rows.")
        if (valid[1] and valid[3] and self.cols_mode.currentData() == "fixed"
                and numbers[3] > numbers[1]):
            valid[3] = False
            errors.append("Fixed preferred columns cannot exceed physical columns.")
        for field, ok in zip(fields, valid):
            field.set_valid(ok)
        self._ok.setEnabled(all(valid))
        self.feedback.setText(" ".join(errors))
        return all(valid)

    def accept(self):
        if self._update_validation():
            super().accept()

    def values(self):
        if not self._update_validation():
            raise ValueError("Correct the marked board dimensions before continuing")
        return {
            "actualRows": self.actual_rows.value(),
            "actualCols": self.actual_cols.value(),
            "wantedRows": self.preferred_rows.value(),
            "wantedCols": self.preferred_cols.value(),
            "wantedRowsMode": self.rows_mode.currentData(),
            "wantedColsMode": self.cols_mode.currentData(),
        }

class RoutingRulesDialog(QDialog):
    """Require a visible, explicit choice of both physical routing policies."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Routing rules — confirm cuts and wire stacking")
        self.setModal(True)
        self.setMinimumWidth(530)
        layout = QVBoxLayout(self)
        title = QLabel("ROUTING RULES — REVIEW BOTH SETTINGS")
        title.setStyleSheet("font-size: 16px; font-weight: 800;")
        layout.addWidget(title)
        intro = QLabel(
            "These settings control the native solver. Choose one option "
            "for cuts and one for jumper stacking before calibration."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        cuts_group = QGroupBox("1. CUTS")
        cuts_layout = QVBoxLayout(cuts_group)
        self.cut_knife = QRadioButton(
            "Knife cuts allowed (default) — drilled cuts also allowed"
        )
        self.cut_drilled = QRadioButton("Drilled holes only — no knife cuts")
        self.cut_knife.setChecked(True)
        cuts_layout.addWidget(self.cut_knife)
        cuts_layout.addWidget(self.cut_drilled)
        layout.addWidget(cuts_group)

        stack_group = QGroupBox("2. WIRE STACKING")
        stack_layout = QVBoxLayout(stack_group)
        self.stack_yes = QRadioButton("Allow stacked jumper wires (default)")
        self.stack_no = QRadioButton("Do not allow stacked jumper wires")
        self.stack_yes.setChecked(True)
        stack_layout.addWidget(self.stack_yes)
        stack_layout.addWidget(self.stack_no)
        layout.addWidget(stack_group)

        note = QLabel(
            "Drilled-only affects decoder constraints. Stacking affects "
            "routing/finishing, not the 100-decode timing measurement. "
            "This confirmation does not start Pass One."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        self.confirm = QCheckBox("I have checked both routing settings")
        layout.addWidget(self.confirm)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        go = buttons.button(QDialogButtonBox.StandardButton.Ok)
        go.setObjectName("nextActionButton")
        go.setText("CONFIRM RULES / CONTINUE")
        go.setEnabled(False)
        self.confirm.toggled.connect(go.setEnabled)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self):
        return {"drilled_only": self.cut_drilled.isChecked(),
                "stacking_allowed": self.stack_yes.isChecked()}


class PassOneDialog(QDialog):
    """Explicit move-budget selection and confirmation; no auto-start."""

    def __init__(self, probe_result=None, parent=None, *, drilled_only=None, stacking_allowed=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Pass One — Move Budget")
        self.setModal(True)
        self.setMinimumWidth(450)
        layout = QVBoxLayout(self)
        heading = QLabel("Pass One")
        heading.setStyleSheet("font-size: 17px; font-weight: 800;")
        layout.addWidget(heading)
        explanation = QLabel(
            "Run 200 seeds in DEBUG mode, or 2,000 in normal mode. "
            "Save PASS, FAIL and ERROR attempts with seed, cuts, wires, Q/100 "
            "and seconds to this project's "
            "selected 10k/20k directory. The verified winner is replayed "
            "and saved separately when the campaign completes."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        if isinstance(drilled_only, bool) and isinstance(stacking_allowed, bool):
            policies = QLabel(
                "Confirmed routing rules for Pass One:\n"
                f"Cuts: {'Drilled only' if drilled_only else 'Knife allowed'}\n"
                f"Wire stacking: {'Allowed' if stacking_allowed else 'Off'}"
            )
            policies.setWordWrap(True)
            policies.setStyleSheet("font-weight: 700;")
            layout.addWidget(policies)
        self.ten_k = QRadioButton("10,000 moves per seed")
        self.twenty_k = QRadioButton("20,000 moves per seed")
        ms = (probe_result or {}).get("ms_per_decode")
        if isinstance(ms, (int, float)) and ms > 0:
            ten_est = 10000 * ms / 1000
            twenty_est = 20000 * ms / 1000
            # Transparent runtime heuristic, NOT a quality prediction.
            self._recommended = 20000 if twenty_est <= 30 else 10000
            timing = QLabel(
                f"100-point decoder timing: {ms:.5f} ms/decode. "
                f"Approximate decoder work per seed: 10k ≈ {ten_est:.1f}s; "
                f"20k ≈ {twenty_est:.1f}s. "
                "Excludes routing/finishing and does not prove quality."
            )
        else:
            self._recommended = 10000
            timing = QLabel(
                "100-point timing unavailable. Default is 10k; "
                "this is not a verified quality recommendation."
            )
        timing.setWordWrap(True)
        layout.addWidget(timing)
        if self._recommended == 10000:
            self.ten_k.setText("10,000 moves — suggested for first-pass screening")
            self.ten_k.setChecked(True)
        else:
            self.twenty_k.setText("20,000 moves — suggested from decoder timing")
            self.twenty_k.setChecked(True)
        layout.addWidget(self.ten_k)
        layout.addWidget(self.twenty_k)
        self.debug_mode = QCheckBox("DEBUG MODE — ON: 200 seeds · OFF: 2,000 seeds")
        self.debug_mode.setObjectName("passOneDebugMode")
        self.debug_mode.setChecked(False)
        layout.addWidget(self.debug_mode)
        self.confirm = QCheckBox(
            "I confirm the selected Pass One budget and want to continue."
        )
        layout.addWidget(self.confirm)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        go = buttons.button(QDialogButtonBox.StandardButton.Ok)
        go.setObjectName("nextActionButton")
        go.setText("GO — PASS ONE")
        go.setEnabled(False)
        self.confirm.toggled.connect(go.setEnabled)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def moves(self):
        return 10000 if self.ten_k.isChecked() else 20000

    def debug(self):
        return self.debug_mode.isChecked()

    def seeds(self):
        return 200 if self.debug() else 2000


class PassOneExistingDialog(QDialog):
    """A separate, explicit gate before overwriting previous test results."""

    def __init__(self, source_name, moves, existing, resume_info=None,
                 resume_error=None, parent=None, *, seeds=2000, debug=False):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Pass One — Previous results found")
        self.setMinimumWidth(540)
        self.action = None
        layout = QVBoxLayout(self)
        heading = QLabel("⚠ PREVIOUS PASS ONE TEST RESULTS EXIST")
        heading.setStyleSheet("font-weight: 800; font-size: 15px; color: #842c32;")
        layout.addWidget(heading)
        warning = QLabel(
            f"Project: {source_name}\n"
            f"Move budget: {moves // 1000}k\n"
            f"Campaign: {'DEBUG · 200 seeds' if debug else 'FULL · 2,000 seeds'}\n"
            f"Existing files: {len(existing)}\n"
            "RESTART will overwrite ONLY this project's selected move-budget "
            "CSV/log and its winner JSON/SVG. Other budgets and projects remain untouched."
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        if resume_info is not None and resume_info["state"] != "COMPLETED":
            details = QLabel(
                f"Saved campaign: {resume_info['state']} · "
                f"{resume_info['done']:,}/{seeds:,} confirmed seeds · "
                f"{resume_info['qualified']} verified · "
                f"{resume_info['errors']} errors to retry."
            )
            details.setWordWrap(True)
            layout.addWidget(details)
        elif resume_error:
            caution = QLabel(f"Resume unavailable: {resume_error}")
            caution.setWordWrap(True)
            layout.addWidget(caution)
        else:
            layout.addWidget(QLabel("This campaign is already marked COMPLETED."))

        self.confirm = QCheckBox(
            "I understand these existing test results will be overwritten"
        )
        layout.addWidget(self.confirm)
        buttons = QHBoxLayout()
        self.resume_button = QPushButton("RESUME")
        self.resume_button.setEnabled(
            resume_info is not None and resume_info["state"] != "COMPLETED"
        )
        self.restart_button = QPushButton("OVERWRITE & START")
        self.restart_button.setEnabled(False)
        self.restart_button.setObjectName("nextActionButton")
        cancel_button = QPushButton("CANCEL")
        self.confirm.toggled.connect(self.restart_button.setEnabled)
        self.resume_button.clicked.connect(lambda: self._choose("resume"))
        self.restart_button.clicked.connect(lambda: self._choose("restart"))
        cancel_button.clicked.connect(self.reject)
        buttons.addWidget(self.resume_button)
        buttons.addWidget(self.restart_button)
        buttons.addWidget(cancel_button)
        layout.addLayout(buttons)

    def _choose(self, action):
        self.action = action
        self.accept()


class PassTwoDialog(QDialog):
    """Confirm import of existing Pass One CSV; no solver strategy assumed."""

    def __init__(self, csv_path: Path, candidate_count: int, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle("Pass Two — Load Pass One Results")
        self.setModal(True)
        self.setMinimumWidth(470)
        layout = QVBoxLayout(self)
        label = QLabel(
            f"Found {candidate_count:,} independently verified Pass One "
            f"seed record(s):\n{csv_path}\n\n"
            "GO copies all records into this project's pass 2/candidates.csv. "
            "No Pass Two solver search runs yet because its move-budget "
            "and survivor-processing strategy have not been specified."
        )
        label.setWordWrap(True)
        layout.addWidget(label)
        self.confirm = QCheckBox(
            "Are you sure? Clear only this project's Pass Two; keep Pass One and JSONs."
        )
        layout.addWidget(self.confirm)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel
        )
        go = buttons.button(QDialogButtonBox.StandardButton.Ok)
        go.setObjectName("nextActionButton")
        go.setText("GO — LOAD PASS TWO")
        go.setEnabled(False)
        self.confirm.toggled.connect(go.setEnabled)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class LockDialog(QDialog):
    """Collect PRE-SOLVE constraints for one already-placed component."""
    def __init__(self, component: dict[str, Any], index: int, total: int, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
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
        self.unlocked = QRadioButton("Movable — release for future placement")
        self.edge = QCheckBox("Board-edge constraint")
        self.slide = QCheckBox("May slide along this edge — EXPERIMENTAL")
        self.slide.setStyleSheet(
            "QCheckBox { color: #ff1744; font-weight: 800; font-size: 13px; }"
        )
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
        hint = QLabel(
            "Fixed = keep current position (unless experimental Slide is selected). "
            "Movable = return the part to placement. "
            "Edge anchors must already touch or overhang a physical board edge."
        )
        hint.setWordWrap(True)
        layout.addWidget(hint)
        self.search_notice = QLabel(
            "EXPERIMENTAL — Edge+Slide is not a guaranteed routing mode. "
            "The part must already touch or overhang the board edge; "
            "the native decoder rejects invalid edge anchors. "
            "The 100-point check does not search slide positions."
        )
        self.search_notice.setWordWrap(True)
        self.search_notice.setStyleSheet(
            "color: #ff1744; font-size: 12px; font-weight: 800;"
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
        self.setBackgroundBrush(QBrush(QColor("#f5faff")))
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
        ("BOARD", "Board dimensions"),
        ("CONSTRAINTS", "Placement locks"),
        ("CUTS", "Cuts"),
        ("STACK", "Wire stacking"),
        ("SPEED", "Speed probe (3 or 4 workers)"),
        ("CALIBRATION", "100-point move calibration"),
        ("PASS1", "1st Pass"),
        ("PASS2", "2nd Pass"),
        ("FINAL", "Final Pass"),
        ("VERIFY", "Electrical PASS"),
    )

    PREPARATION_STAGES = ("COLLECT", "SANITY", "PRE-SOLVE", "BOARD", "CONSTRAINTS",
                          "CUTS", "STACK", "SPEED", "CALIBRATION")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("workflowChecklist")
        self.setStyleSheet("""
            QWidget#workflowChecklist { background: #ffffff; border: 1px solid #cbddec; border-radius: 12px; }
            QLabel#workflowTitle { color: #1d425f; font-size: 15px; font-weight: 700; }
            QLabel#workflowPercent { color: #2674ae; font-size: 14px; font-weight: 700; }
            QProgressBar { background: #e2edf7; border: 0; border-radius: 6px; height: 8px; }
            QProgressBar::chunk { background: #17a6c8; border-radius: 6px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 12)
        layout.setSpacing(8)
        heading = QHBoxLayout()
        title = QLabel("PROJECT PREPARATION")
        title.setObjectName("workflowTitle")
        self.percent = QLabel("0%")
        self.percent.setObjectName("workflowPercent")
        heading.addWidget(title)
        heading.addStretch()
        heading.addWidget(self.percent)
        layout.addLayout(heading)
        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, len(self.PREPARATION_STAGES))
        layout.addWidget(self.bar)
        self.rows = {}
        for key, caption in self.STAGES:
            if key == "PASS1":
                separator = QLabel("OPTIMISATION PASSES")
                separator.setStyleSheet(
                    "font-size: 11px; font-weight: 800; color: #244d70; "
                    "padding-top: 9px; border-top: 1px solid #cbddec;"
                )
                layout.addWidget(separator)
            elif key == "VERIFY":
                separator = QLabel("FINAL VERIFICATION")
                separator.setStyleSheet(
                    "font-size: 11px; font-weight: 800; color: #244d70; "
                    "padding-top: 9px; border-top: 1px solid #cbddec;"
                )
                layout.addWidget(separator)
            row = QHBoxLayout()
            mark = QLabel("○")
            mark.setFixedWidth(22)
            mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
            mark.setStyleSheet("font-size: 23px; color: #b8bec7;")
            label = QLabel(caption)
            label.setStyleSheet("font-size: 12px; color: #475569;")
            row.addWidget(mark)
            row.addWidget(label, 1)
            if key == "CUTS":
                self.cuts_value = QLabel("Not selected")
                self.cuts_value.setStyleSheet(
                    "color: #526581; font-size: 11px; font-weight: 600;"
                )
                self.cuts_value.setWordWrap(True)
            elif key == "STACK":
                self.stacking_value = QLabel("Not selected")
                self.stacking_value.setStyleSheet(
                    "color: #526581; font-size: 11px; font-weight: 600;"
                )
                self.stacking_value.setWordWrap(True)
            layout.addLayout(row)
            if key == "CUTS":
                layout.addWidget(self.cuts_value)
            elif key == "STACK":
                layout.addWidget(self.stacking_value)
            self.rows[key] = mark
        self.lock_summary = QLabel("Fixed: 0  ·  Edge: 0\nEdge+Slide: 0")
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
        note = QLabel("Pass One and Pass Two launch only by button · final Electrical PASS pending")
        note.setWordWrap(True)
        note.setStyleSheet("font-size: 10px; color: #697586;")
        layout.addWidget(note)
        self.reset()

    def reset(self):
        self.update_states({})
        self.set_lock_summary(0, 0, 0)
        self.set_rules(None, None)

    def set_rules(self, drilled_only: bool | None, stacking_allowed: bool | None):
        self.cuts_value.setText(
            "Not selected" if drilled_only is None
            else ("Drilled only" if drilled_only else "Knife allowed")
        )
        self.stacking_value.setText(
            "Not selected" if stacking_allowed is None
            else ("Allowed" if stacking_allowed else "Off")
        )

    def set_lock_summary(self, fixed: int, edge: int, slide: int,
                         positions: int | None = None, attempts: int = 24):
        self.lock_summary.setText(
            f"Fixed locked: {fixed}  ·  Edge locked: {edge}\n"
            f"Edge+Slide: {slide}"
        )
        if slide:
            self.lock_warning.setText(
                "EXPERIMENTAL Edge+Slide — invalid edge anchors are rejected "
                "by the native decoder."
            )
            self.lock_warning.setStyleSheet(
                "font-size: 11px; font-weight: 800; color: #ff1744;"
            )
            self.lock_warning.show()
        elif edge:
            self.lock_warning.setText(
                "Edge lock requires a part to touch or overhang a physical board edge."
            )
            self.lock_warning.setStyleSheet(
                "font-size: 11px; font-weight: 700; color: #92400e;"
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
                mark.setStyleSheet("font-size: 19px; font-weight: bold; color: #168d95;")
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
        prepared = sum(
            states.get(key, "pending") == "done" for key in self.PREPARATION_STAGES
        )
        self.bar.setValue(prepared)
        self.percent.setText(f"{round(100 * prepared / len(self.PREPARATION_STAGES))}%")


class StartupSpeedProbe(QThread):
    """Original Route-Mate synthetic CPU scaling probe."""
    completed = Signal(object)
    crashed = Signal(str)

    def run(self):
        try:
            from speed_probe import probe_worker_scaling
            self.completed.emit(probe_worker_scaling(seconds=1.0))
        except Exception as exc:
            self.crashed.emit(str(exc))


class NativeCalibrationWorker(QThread):
    tick = Signal(dict)
    diagnostic = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, project, workers, drilled_only, stacking_allowed, parent=None):
        super().__init__(parent)
        self.project = copy.deepcopy(project)
        self.workers = workers
        self.drilled_only = drilled_only
        self.stacking_allowed = stacking_allowed

    def run(self):
        from gui.native_calibration import calibrate, Cancelled
        try:
            result = calibrate(
                self.project, self.workers,
                self.drilled_only, self.stacking_allowed,
                self.tick.emit, self.diagnostic.emit, self.isInterruptionRequested)
            self.completed.emit(result)
        except Cancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")

class PassOneWorker(QThread):
    tick = Signal(dict)
    diagnostic = Signal(str)
    completed = Signal(dict)
    failed = Signal(str)
    cancelled = Signal()

    def __init__(self, project, moves, workers, drilled, stacking, output,
                 parent=None, *, resume=False, seeds=2000, debug=False):
        super().__init__(parent)
        self.project = copy.deepcopy(project)
        self.moves = moves
        self.workers = workers
        self.drilled = drilled
        self.stacking = stacking
        self.output = output
        self.resume = resume
        self.seeds = seeds
        self.debug = debug

    def run(self):
        from gui.pass_one import run_pass_one
        from gui.native_calibration import Cancelled
        try:
            result = run_pass_one(
                self.project, self.moves, self.workers,
                self.drilled, self.stacking, self.output,
                self.tick.emit, self.diagnostic.emit, self.isInterruptionRequested,
                seeds=self.seeds, resume=self.resume, debug=self.debug,
            )
            self.completed.emit(result)
        except Cancelled:
            self.cancelled.emit()
        except Exception as exc:
            self.failed.emit(f"{type(exc).__name__}: {exc}")


class RouteMateWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
        self.setWindowTitle(f"Route-Mate {GUI_VERSION} · rev {GUI_GIT_REVISION} — Pass Control")
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
        self._calibration_worker = None
        self._pass_one_worker = None
        self._pass_one_resume_done = 0
        self._pass_one_previous_average = None
        self._move_probe_result = None
        self._pass_one_prompt_pending = False
        self.work_root = WORK_ROOT
        self.active_workspace: Path | None = None
        self._stop_requested = False
        self._close_when_idle = False
        self._recommended_workers = None  # Original CPU probe chooses 3 or 4
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
        self._calibration_stages = {}
        self._probe_cut_drilled_only = None
        self._probe_stacking_allowed = None
        self._assumed_geometry = None  # Collector's advisory package profile; not 2.5D PASS.

        logo_path = REPO_ROOT / "icon" / "icon_128x128.png"
        if logo_path.is_file():
            self.setWindowIcon(QIcon(str(logo_path)))
        toolbar = QToolBar("Main")
        toolbar.setObjectName("routeMateToolbar")
        toolbar.setStyleSheet("""
            QToolBar#routeMateToolbar { background: #f7fbff; border: none; border-bottom: 1px solid #cbddec; padding: 9px; spacing: 8px; min-height: 54px; }
            QToolBar#routeMateToolbar QToolButton { background: white; color: #245675; border: 1px solid #bfd7e9; border-radius: 9px; padding: 9px 14px; font-weight: 650; }
            QToolBar#routeMateToolbar QToolButton:hover { background: #e8f7ff; border-color: #50b5dc; }
            QToolBar#routeMateToolbar QToolButton:checked { background: #dceffc; border-color: #6aaddc; color: #1a5b92; }
            QToolBar#routeMateToolbar QToolButton:disabled { background: #eef3f8; border-color: #d9e5ee; color: #90a4b5; }
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
        brand_title.setStyleSheet("color: #19334d; font-size: 16px; font-weight: 800;")
        brand_row.addWidget(brand_title)
        toolbar.addWidget(brand)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        self.load_action = QAction("Load JSON", self)
        self.load_action.triggered.connect(self.load_json)
        toolbar.addAction(self.load_action)


        self.stop_action = QAction("Stop Solve", self)
        self.stop_action.setToolTip("Cancel the running solve safely; keep the original board")
        self.stop_action.setEnabled(False)
        self.stop_action.triggered.connect(self.stop_solve)
        toolbar.addAction(self.stop_action)

        self.pass_one_action = QAction("Pass One", self)
        self.pass_one_action.setToolTip(
            "Choose 10k/20k; record all seed statuses; replay and render the winner"
        )
        self.pass_one_action.triggered.connect(self.start_pass_one)
        toolbar.addAction(self.pass_one_action)
        self.pass_two_action = QAction("Pass Two", self)
        self.pass_two_action.setToolTip(
            "Choose a project's saved Pass One CSV without rerunning Pass One"
        )
        self.pass_two_action.triggered.connect(self.start_pass_two)
        toolbar.addAction(self.pass_two_action)

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
            "QPlainTextEdit { background: #ffffff; color: #23435e;"
            "border: 1px solid #cbddec; border-radius: 9px;"
            "padding: 12px; font-size: 11px; }"
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
        self.solve_activity = QLabel("100-point move check pending · STOP before Pass 1")
        self.solve_activity.setWordWrap(True)
        self.solve_activity.setStyleSheet(
            "font-size: 13px; font-weight: 700; color: #216896; padding: 4px;"
        )
        overview_layout.addWidget(self.solve_activity)
        self.solve_progress = QProgressBar()
        self.solve_progress.setRange(0, 100)
        self.solve_progress.setValue(0)
        self.solve_progress.setFormat("100-point move check: %v/%m")
        overview_layout.addWidget(self.solve_progress)
        self.solve_worker_status = QLabel("Original CPU speed probe pending")
        self.solve_worker_status.setWordWrap(True)
        overview_layout.addWidget(self.solve_worker_status)
        self.solve_eta = QLabel("Elapsed: —   Estimated remaining: —")
        self.solve_eta.setWordWrap(True)
        overview_layout.addWidget(self.solve_eta)
        overview_layout.addStretch()
        self.sidebar_tabs = QTabWidget()
        self.sidebar_tabs.setObjectName("sidebarTabs")
        overview_scroll = QScrollArea()
        overview_scroll.setWidgetResizable(True)
        overview_scroll.setFrameShape(QFrame.Shape.NoFrame)
        overview_scroll.setWidget(overview)
        self.sidebar_tabs.addTab(overview_scroll, "Overview")
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
            QMainWindow { background: #edf6fd; }
            QWidget#sidebarTabs { background: #f7fbff; }
            QTabWidget::pane { border: 1px solid #cbddec; border-radius: 10px;
                                background: #f7fbff; }
            QTabBar::tab { color: #59758c; background: #e6f0f9; padding: 9px 22px;
                           margin-right: 3px; border-radius: 7px; font-weight: 650; }
            QTabBar::tab:selected { background: white; color: #2366a1;
                                    border-bottom: 2px solid #257ac2; }
            QLabel#projectSummary { background: #e6f3fc; color: #1d527a;
                                    border-radius: 9px; padding: 12px;
                                    font-size: 12px; font-weight: 650; }
            QLabel#solveSummary { background: #eaf5fc; color: #285a7c;
                                  border-radius: 9px; padding: 12px;
                                  font-size: 12px; }
            QFrame#boardHeader { background: white; border: 1px solid #cbddec;
                                  border-radius: 11px; }
            QLabel#boardProjectLabel { color: #193d60; font-size: 15px; font-weight: 800; }
            QLabel#boardResultLabel { color: #55758d; font-size: 11px; }
            QPushButton#boardZoomButton { background: #ffffff; color: #215778;
                                         padding: 7px 11px; border: 1px solid #bcd4e8;
                                         border-radius: 8px; font-weight: 700; }
            QPushButton#boardZoomButton:hover { background: #e8f7ff; border-color: #50b5dc; }
            QStatusBar { background: #e4f0fa; color: #365c7a; font-size: 11px; }
        """)
        self.statusBar().setMinimumHeight(26)
        self.statusBar().showMessage("Ready. Load a project JSON to begin.")
        self.log_line(f"Route-Mate {GUI_VERSION} — 100-point native move calibration only")
        self.log_line(f"[GUI][REVISION] git={GUI_GIT_REVISION}")
        self.log_line("Workflow: import → input sanity → footprints → dimensions → locks → cuts → stacking → CPU probe → 100-point move check → STOP.")
        self.log_line("[SOLVER] CPU and 100-point probes remain separate from Pass One/Two.")
        try:
            ensure_workspace_root(self.work_root)  # Work root only; legacy remains untouched
            self.log_line(f"[WORK] Project workspaces root: {self.work_root}")
            self.log_line("[WORK] One directory per source JSON: pass 1 / pass 2 / jsons / logs.")
            self.log_line("[WORK] Old root-level pass folders are preserved; never reused for new jobs.")
        except (OSError, ValueError) as exc:
            self.log_line(f"[WORK][ERROR] {exc}")
        self.statusBar().showMessage("Ready. Pass Two can select a previous project without loading its JSON.")

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
            "neutral": ("#eaf5fc", "#285a7c"),
            "working": ("#e0f2ff", "#216896"),
            "pass": ("#e1f6f3", "#127c81"),
            "failed": ("#fff0f1", "#b33e55"),
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
        pix.fill(QColor("#edf6fd"))
        painter = QPainter(pix)
        painter.setPen(QColor("#19334d"))
        font = painter.font()
        font.setPointSize(20)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(24, 48, f"STRIPBOARD · {tool}")
        font.setPointSize(10)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#536f88"))
        painter.drawText(24, 88, revision)
        painter.drawText(24, 123, f"GUI {GUI_VERSION}  ·  checked-out {GUI_GIT_REVISION}")
        painter.end()
        if self._active_tool_splash is not None:
            self._active_tool_splash.close()
        # PySide6 QSplashScreen takes (pixmap, flags), not (parent, pixmap, flags).
        splash = QSplashScreen(pix, Qt.WindowType.WindowStaysOnTopHint)
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
        dialog.setWindowFlag(Qt.WindowType.FramelessWindowHint, True)
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
            options=QFileDialog.Option.DontUseNativeDialog,
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
        self.checklist.set_lock_summary(fixed, edge, slide)
        return fixed, edge, slide, None

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
                    self.log_line("[LOCKS] Review cancelled; calibration not started.")
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
                    self.log_line(f"[PLACEMENT] {label} released for future placement.")
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
                "[EDGE+SLIDE][EXPERIMENTAL] Slide selected. The native decoder "
                "requires the anchor already to touch/overhang an edge. "
                "An invalid edge is deliberately rejected; "
                "no slide-search optimisation pass is running."
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
        # Old Work/pass 1/ is NOT moved/deleted. Only copy when the exact
        # original Pass One input signature matches this reviewed project.
        if self.active_workspace is not None:
            try:
                if adopt_matching_legacy_pass_one(
                    self.project, self.active_workspace, self.work_root
                ):
                    self.log_line(
                        f"[WORK][LEGACY COPIED] Fingerprint-matched Pass One data copied to "
                        f"{self.active_workspace / PASS_ONE}; originals preserved."
                    )
            except (OSError, ValueError, KeyError) as exc:
                self.log_line(f"[WORK][LEGACY SKIPPED] {exc}")
        preview, _ = self._render_component_side(self.project)
        self._show_board(preview)

        self.statusBar().showMessage(
            "STOPPED BEFORE PASS 1 — choose cuts and stacking."
        )
        self._choose_routing_rules()

    def _choose_routing_rules(self):
        """Show cut/stack options after locks; only accepted choices start probes."""
        dialog = RoutingRulesDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.log_line("[RULES][CANCELLED] CPU and native probes were not started.")
            self.statusBar().showMessage("Routing rules cancelled; no probe started.")
            return
        rules = dialog.values()
        self._probe_cut_drilled_only = bool(rules["drilled_only"])
        self._probe_stacking_allowed = bool(rules["stacking_allowed"])
        self.checklist.set_rules(
            self._probe_cut_drilled_only, self._probe_stacking_allowed
        )
        self.log_line(
            f"[RULES][CONFIRMED] Drilled only={self._probe_cut_drilled_only}; "
            f"knife allowed={not self._probe_cut_drilled_only}; "
            f"stacked wires allowed={self._probe_stacking_allowed}."
        )
        self._start_speed_probe()

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


    def _start_speed_probe(self):
        """Run original donor CPU probe before the 100-point move check."""
        if self.project is None or self._speed_probe_worker is not None:
            return
        if (type(self._probe_cut_drilled_only) is not bool
                or type(self._probe_stacking_allowed) is not bool):
            self.log_line("[RULES][ERROR] No confirmed cut/stack policy. No probe started.")
            return
        self._calibration_stages = {"CUTS": "done", "STACK": "done", "SPEED": "running"}
        self._refresh_checklist()
        self.log_line(f"[RULES] Cuts={'DRILLED ONLY' if self._probe_cut_drilled_only else 'KNIFE ALLOWED'}; "
                      f"wire stacking={'ALLOWED' if self._probe_stacking_allowed else 'OFF'}.")
        self.solve_activity.setText("CPU speed probe · comparing 3 or 4 workers")
        self.log_line("[SPEED] Original Route-Mate CPU worker-scaling probe; "
                      "separate from the native 100-decoder measurement.")
        if QApplication.platformName() == "offscreen":
            self.log_line("[SPEED] Offscreen GUI test: automatic probe skipped.")
            return
        self.load_action.setEnabled(False)
        worker = StartupSpeedProbe(self)
        self._speed_probe_worker = worker
        worker.completed.connect(self._speed_probe_completed)
        worker.crashed.connect(self._speed_probe_failed)
        worker.finished.connect(self._speed_probe_finished)
        worker.start()

    def _speed_probe_completed(self, result):
        timings = {int(n): float(t) for n,t in result["timings"].items()}
        cpus = int(result.get("logical_cpus") or os.cpu_count() or 1)
        if cpus < 3 or 3 not in timings or timings[3] <= 0:
            self._speed_probe_failed("Three CPU workers unavailable.")
            return
        three, four = timings[3], timings.get(4)
        # Exact donor policy: choose 4 if its time is within 15% of 3.
        self._recommended_workers = (4 if cpus >= 4 and four is not None
                                     and four <= three * 1.15 else 3)
        self._calibration_stages["SPEED"] = "done"
        self._refresh_checklist()
        self.solve_worker_status.setText(f"{self._recommended_workers} CPU workers selected")
        self.log_line("[SPEED][TIMINGS] " + ", ".join(
            f"{n} workers={t:.3f}s" for n,t in sorted(timings.items())))
        self.log_line(f"[SPEED][POLICY] selected={self._recommended_workers}; "
                      "4 preferred if within 15% of 3.")
        self._start_calibration()

    def _speed_probe_failed(self, error):
        self._calibration_stages["SPEED"] = "failed"
        self._refresh_checklist()
        self.solve_activity.setText("Speed probe failed; see Activity")
        self.solve_worker_status.setText(str(error))
        self.log_line("[SPEED][FAILED] "+str(error))

    def _speed_probe_finished(self):
        self._speed_probe_worker = None
        if self._calibration_worker is None:
            self.load_action.setEnabled(True)
        if self._close_when_idle:
            self.close()

    def _start_calibration(self):
        """Exactly 100 native decoder samples, not a solver campaign."""
        if self.project is None or self._calibration_worker is not None:
            return
        workers = self._recommended_workers
        if workers not in (3, 4):
            self._speed_probe_failed("CPU probe did not select 3 or 4 workers.")
            return
        self.load_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self._pass_one_prompt_pending = False
        self._solve_started = perf_counter()
        self._solve_done = 0
        self._solve_budget = 100
        self._worker_time_stats = {}
        self.solve_progress.setRange(0, 0)  # no invented per-decode progress
        self.solve_activity.setText("100-point move check · measuring decoder speed")
        self._calibration_stages["CALIBRATION"] = "running"
        self._refresh_checklist()
        self._solve_clock.start()
        self.log_line("[MOVE100][START] ONE --speedprobe 100 native call; "
                      "100 random-genome decodes, ZERO full solver runs.")
        worker = NativeCalibrationWorker(
            self.project, workers,
            self._probe_cut_drilled_only, self._probe_stacking_allowed, self)
        self._calibration_worker = worker
        worker.tick.connect(self._calibration_tick)
        worker.diagnostic.connect(self.log_line)
        worker.completed.connect(self._calibration_completed)
        worker.failed.connect(self._calibration_failed)
        worker.cancelled.connect(self._calibration_cancelled)
        worker.finished.connect(self._calibration_finished)
        worker.start()

    def _calibration_tick(self, event):
        if event["phase"] == "running":
            self.solve_activity.setText("100-point move check · native measurement running")
            self.solve_worker_status.setText(
                "Native decoder measurement · no per-sample progress available")
        else:
            self._solve_done = int(event["completed"])
            self.solve_progress.setRange(0, 100)
            self.solve_progress.setValue(100)
        self._update_solve_clock()

    def _calibration_completed(self, result):
        self._calibration_stages["CALIBRATION"] = "done"
        self._move_probe_result = dict(result)
        self._pass_one_prompt_pending = True
        self._refresh_checklist()
        self._solve_done = 100
        self.solve_progress.setRange(0, 100)
        self.solve_progress.setValue(100)
        self.solve_activity.setText("MOVE CHECK COMPLETE · Pass One awaits GO")
        self.solve_worker_status.setText(
            f"100 decodes · {result['ms_per_decode']:.5f}ms/decode · "
            f"{result['decodes_per_second']:,.0f} decodes/s")
        self.log_line("[MOVE100][DONE] 100/100 random decoder points; "
                      "0 placement, routing, solve attempts or final electrical check.")
        self.log_line("[MOVE100][READY] Pass One confirmation opens after the native probe exits; no solver campaign starts without GO.")
        self.statusBar().showMessage("MOVE CALIBRATION COMPLETE — Pass One confirmation will open.")
        self._set_board_summary("Move calibration complete · no final routed board", level="neutral")

    def _calibration_failed(self, error):
        self._pass_one_prompt_pending = False
        self._calibration_stages["CALIBRATION"] = "failed"
        self._refresh_checklist()
        self.solve_progress.setRange(0, 100)
        self.solve_progress.setValue(0)
        self.solve_activity.setText("100-point move check FAILED · see Activity")
        self.solve_worker_status.setText(str(error))
        self.log_line("[MOVE100][ERROR] " + str(error))
        self.log_line("[MOVE100][STOP] No optimisation pass started.")

    def _calibration_cancelled(self):
        self._pass_one_prompt_pending = False
        self.solve_progress.setRange(0, 100)
        self.solve_progress.setValue(0)
        self.solve_activity.setText("100-point move check cancelled")
        self.log_line("[MOVE100][CANCELLED] No optimiser pass started.")

    def _calibration_finished(self):
        self._solve_clock.stop()
        if self._solve_started is not None:
            elapsed = self._clock_text(perf_counter() - self._solve_started)
            self.solve_eta.setText(f"Elapsed: {elapsed} · stopped before Pass 1")
        self._solve_started = None
        self._calibration_worker = None
        self.load_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        offer_pass_one = (self._pass_one_prompt_pending and
                          self._calibration_stages.get("CALIBRATION") == "done" and
                          self.project is not None and not self._close_when_idle)
        self._pass_one_prompt_pending = False
        if self._close_when_idle:
            self.close()
        elif offer_pass_one:
            # Wait for the calibration thread to finish and its references to be
            # released before showing the existing GO-gated launch dialog.
            self.log_line("[PASS1][PROMPT] Calibration complete; choose 10k/20k and confirm GO or Cancel.")
            QTimer.singleShot(0, self.start_pass_one)

    def start_pass_one(self):
        """Explicit GO; never clear a campaign without budget-specific consent."""
        if (self._pass_one_worker is not None
            or self._calibration_worker is not None
            or self._speed_probe_worker is not None):
            QMessageBox.information(self, "Pass One busy",
                                    "Finish or stop the active task first.")
            return
        if self.project is None or self.project_path is None or self.active_workspace is None:
            QMessageBox.information(self, "Pass One", "Load a project JSON first.")
            return
        if (self._calibration_stages.get("CALIBRATION") != "done"
            or not isinstance(self._probe_cut_drilled_only, bool)
            or not isinstance(self._probe_stacking_allowed, bool)
            or self._recommended_workers not in (3, 4)):
            QMessageBox.information(
                self, "Pass One", "Finish board/lock review, routing rules, "
                "worker probe and the 100-point move check before Pass One."
            )
            return
        dialog = PassOneDialog(
            self._move_probe_result, self,
            drilled_only=self._probe_cut_drilled_only,
            stacking_allowed=self._probe_stacking_allowed,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.log_line("[PASS1][CANCELLED] GO not pressed; results untouched.")
            return
        moves = dialog.moves()
        debug = dialog.debug()
        seeds = dialog.seeds()
        try:
            from gui.native_calibration import prerequisites
            from gui.pass_one import AUDITOR, inspect_pass_one_campaign
            prerequisites()
            if not AUDITOR.is_file():
                raise RuntimeError(f"Independent saved-board auditor is missing: {AUDITOR}")
            workspace = project_workspace(self.project_path, self.work_root, create=False)
            if workspace != self.active_workspace:
                raise ValueError("Loaded project and workspace disagree — no files cleared.")
            folder = pass_one_budget_dir(workspace, moves, debug=debug)
            existing = campaign_existing_files(workspace, moves, debug=debug)
            resume = False
            snapshot = None
            if existing:
                try:
                    snapshot = inspect_pass_one_campaign(
                        self.project, moves, self._recommended_workers,
                        self._probe_cut_drilled_only, self._probe_stacking_allowed,
                        folder, seeds=seeds, debug=debug,
                    )
                    error = None
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    error = str(exc)
                original = {
                    str(p): (p.stat().st_size, p.stat().st_mtime_ns)
                    for p in existing
                }
                choice = PassOneExistingDialog(
                    self.project_path.name, moves, existing, snapshot, error, self,
                    seeds=seeds, debug=debug,
                )
                if choice.exec() != QDialog.DialogCode.Accepted or choice.action is None:
                    self.log_line("[PASS1][CANCELLED] Existing results preserved.")
                    return
                # Re-check every saved file after the user reviews the warning.
                current = {
                    str(p): (p.stat().st_size, p.stat().st_mtime_ns)
                    for p in campaign_existing_files(workspace, moves, debug=debug)
                }
                if current != original:
                    raise ValueError("Results changed while confirming; nothing overwritten.")
                resume = choice.action == "resume"
                if resume:
                    if snapshot is None or snapshot["state"] == "COMPLETED":
                        raise ValueError("Resume is not available for this campaign")
                else:
                    folder = clear_pass_one_budget(workspace, moves, debug=debug)
            else:
                folder = pass_one_budget_dir(workspace, moves, create=True, debug=debug)
        except (OSError, ValueError, RuntimeError) as exc:
            QMessageBox.critical(self, "Pass One startup", str(exc))
            return

        self._calibration_stages["PASS1"] = "running"
        self._refresh_checklist()
        self._solve_done = snapshot["done"] if resume else 0
        self._pass_one_resume_done = self._solve_done
        self._pass_one_previous_average = (
            snapshot["seconds_per_seed"] if resume else None
        )
        self._solve_budget = seeds
        self.solve_progress.setRange(0, seeds)
        self.solve_progress.setValue(self._solve_done)
        self.solve_progress.setFormat("Pass One: %v/%m seeds")
        self.solve_activity.setText(
            f"Pass One {'DEBUG' if debug else 'FULL'} · "
            f"{moves:,} moves · {self._solve_done:,}/{seeds:,}"
        )
        self.solve_worker_status.setText(
            f"{self._recommended_workers} workers · "
            f"{snapshot['qualified'] if resume else 0} verified seeds"
        )
        self._set_board_summary(
            f"Pass One {'resuming' if resume else 'running'} · "
            f"{moves // 1000}k moves · {'DEBUG' if debug else 'FULL'} · "
            "not a final routed board",
            level="working",
        )
        self.load_action.setEnabled(False)
        self.pass_one_action.setEnabled(False)
        self.pass_two_action.setEnabled(False)
        self.stop_action.setEnabled(True)
        self._solve_started = perf_counter()
        self._solve_clock.start()
        self.log_line(
            f"[PASS1][{'RESUME' if resume else 'GO'}] "
            f"{seeds:,} native seeds × {moves:,} moves; {self._recommended_workers} "
            f"workers; folder={folder}; "
            f"{'existing PASS/FAIL rows preserved' if resume else 'selected budget only cleared'}."
        )
        worker = PassOneWorker(
            self.project, moves, self._recommended_workers,
            self._probe_cut_drilled_only, self._probe_stacking_allowed,
            folder, self, resume=resume, seeds=seeds, debug=debug
        )
        self._pass_one_worker = worker
        worker.tick.connect(self._pass_one_tick)
        worker.diagnostic.connect(self.log_line)
        worker.completed.connect(self._pass_one_completed)
        worker.failed.connect(self._pass_one_failed)
        worker.cancelled.connect(self._pass_one_cancelled)
        worker.finished.connect(self._pass_one_finished)
        worker.start()

    def _pass_one_tick(self, progress):
        self._solve_done = progress["done"]
        self.solve_progress.setValue(self._solve_done)
        passed = progress["qualified"]
        errors = progress.get("errors", 0)
        self.solve_activity.setText(
            f"Pass One · {self._solve_done:,}/{progress['total']:,} "
            f"confirmed · {passed:,} verified"
        )
        self.solve_worker_status.setText(
            f"{self._recommended_workers} workers · {passed} strict PASS · "
            f"{errors} errors"
        )
        self._update_solve_clock()

    def _display_pass_one_champion(self, result):
        """Render only independently audited, repeatably replayed winner JSON."""
        if not result.get("winner_json"):
            return
        path = Path(result["winner_json"])
        champion = json.loads(path.read_text(encoding="utf-8"))
        top_svg, details = self._render_component_side(champion)
        copper_svg = self._copper_svg
        if not copper_svg:
            raise ValueError("Production renderer returned no copper-side SVG")
        for kind, svg in (("component", top_svg), ("copper", copper_svg)):
            if not QSvgRenderer(QByteArray(svg.encode("utf-8"))).isValid():
                raise ValueError(f"Winner {kind}-side SVG failed SVG validation")
        top_file = path.with_name(path.stem + "-components.svg")
        copper_file = path.with_name(path.stem + "-copper.svg")
        top_file.write_text(top_svg, encoding="utf-8")
        copper_file.write_text(copper_svg, encoding="utf-8")
        self._top_svg = top_svg
        self._board_side = "top"
        self._switch_board_side("top")
        self._set_board_summary(
            f"🏆 Pass One champion · {result['moves'] // 1000}k · "
            f"seed {result['winner_seed']:04d} · strictly verified",
            project=champion, level="pass",
        )
        self.log_line(f"[PASS1][WINNER][JSON] {path}")
        self.log_line(f"[PASS1][WINNER][COMPONENTS] {top_file}")
        self.log_line(f"[PASS1][WINNER][COPPER] {copper_file}")
        if details:
            self.log_line("[PASS1][WINNER][RENDER] " + details)

    def _pass_one_completed(self, result):
        done = result.get("completed", True)
        self._calibration_stages["PASS1"] = "done" if done else "failed"
        self._refresh_checklist()
        self.solve_progress.setValue(result["checked"])
        label = "PASS ONE COMPLETE" if done else "PASS ONE INCOMPLETE — RESUME AVAILABLE"
        self.solve_activity.setText(
            f"{label} · {result['qualified']:,} verified CSV rows"
        )
        self.log_line(f"[PASS1][DELIVERED] {result['csv']}")
        self.log_line(f"[PASS1][LOG] {result['log']}")
        self.log_line("[PASS1][STOP] Pass Two not started.")
        if done:
            if result.get("winner_error"):
                self.log_line("[PASS1][WINNER][ERROR] " + result["winner_error"])
                self._set_board_summary(
                    "Pass One complete · winner replay failed (see Activity)",
                    level="failed",
                )
            elif result.get("winner_json"):
                try:
                    self._display_pass_one_champion(result)
                except Exception as exc:
                    self.log_line(f"[PASS1][WINNER][RENDER ERROR] {exc}")
                    self._set_board_summary(
                        "Pass One complete · winner JSON verified, SVG unavailable",
                        level="failed",
                    )
                    QMessageBox.warning(
                        self, "Pass One winner SVG failed",
                        f"Winner JSON is saved; renderer failed: {exc}",
                    )
            else:
                self._set_board_summary(
                    "Pass One complete · winner output missing"
                    if result["qualified"] else "Pass One complete · no strict survivors",
                    level="failed" if result["qualified"] else "neutral",
                )
        else:
            self._set_board_summary(
                "Pass One incomplete · resume to retry missing/error seeds",
                level="working",
            )
        self.statusBar().showMessage(
            f"Pass One {'complete' if done else 'incomplete'} · "
            f"{result['qualified']} verified · "
            f"{result.get('errors', 0)} errors"
        )

    def _pass_one_failed(self, error):
        self._calibration_stages["PASS1"] = "failed"
        self._refresh_checklist()
        self.solve_activity.setText("PASS ONE INCOMPLETE · see Activity; resume available")
        self._set_board_summary("Pass One interrupted · existing CSV preserved", level="failed")
        self.log_line("[PASS1][ERROR] " + str(error))

    def _pass_one_cancelled(self):
        self.solve_activity.setText("PASS ONE STOPPED · resume preserves PASS/FAIL rows")
        self._set_board_summary("Pass One stopped · resume available", level="working")
        self.log_line("[PASS1][CANCELLED] No Pass Two automatically started.")

    def _pass_one_finished(self):
        self._solve_clock.stop()
        if self._solve_started is not None:
            self.solve_eta.setText(
                f"Elapsed: {self._clock_text(perf_counter() - self._solve_started)}"
            )
        self._solve_started = None
        self._pass_one_worker = None
        self._pass_one_resume_done = 0
        self._pass_one_previous_average = None
        self.load_action.setEnabled(True)
        self.pass_one_action.setEnabled(True)
        self.pass_two_action.setEnabled(True)
        self.stop_action.setEnabled(False)
        if self._close_when_idle:
            self.close()

    def start_pass_two(self):
        """Import CSV from exactly one named project workspace, even cold-start.

        Pass Two still imports candidates only; it does not start an optimiser.
        """
        if (self._pass_one_worker is not None
            or self._calibration_worker is not None
            or self._speed_probe_worker is not None):
            QMessageBox.information(
                self, "Pass Two busy", "Stop the active task first."
            )
            return

        try:
            if self.project is not None and self.project_path is not None:
                workspace = project_workspace(
                    self.project_path, self.work_root, create=False
                )
                if workspace != self.active_workspace:
                    raise ValueError("Loaded project and workspace disagree.")
                chosen = self.project_path.name
            else:
                available = list_project_workspaces(self.work_root)
                if not available:
                    raise FileNotFoundError(
                        "No project workspaces found. Load a source JSON once "
                        "to create its own Work/<project-id>/ folders. "
                        "Old Work/pass 1/ data has been preserved."
                    )
                if len(available) == 1:
                    chosen, workspace = available[0]
                else:
                    selection, accepted = QInputDialog.getItem(
                        self, "Pass Two — Choose Project",
                        "Load Pass One results for which JSON?",
                        [label for label, _ in available],
                        0, False,
                    )
                    if not accepted:
                        self.log_line("[PASS2][CANCELLED] No project selected; all files untouched.")
                        return
                    workspace = dict(available)[selection]
                    chosen = selection
            sources = pass_one_campaign_sources(workspace)
            if not sources:
                raise FileNotFoundError(
                    f"No Pass One CSV found for project {chosen}. "
                    "No results were overwritten."
                )
            if len(sources) == 1:
                label, source = sources[0]
            else:
                label, accepted = QInputDialog.getItem(
                    self, "Pass Two — Choose Move Budget",
                    "Which saved Pass One test should Pass Two import?",
                    [name for name, _ in sources], 0, False,
                )
                if not accepted:
                    self.log_line("[PASS2][CANCELLED] Budget not selected.")
                    return
                source = dict(sources)[label]
            rows = read_pass_one(workspace, csv_path=source)
        except (OSError, ValueError, KeyError) as exc:
            self.log_line("[PASS2][INPUT ERROR] " + str(exc))
            QMessageBox.warning(self, "Pass Two needs project Pass One CSV", str(exc))
            return
        if not rows:
            QMessageBox.information(
                self, "Pass Two", "This project's results.csv contains no verified seeds."
            )
            return
        dialog = PassTwoDialog(source, len(rows), self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            self.log_line(f"[PASS2][CANCELLED] {workspace / PASS_TWO} unchanged.")
            return
        try:
            # A different project's directories can never be the clear target.
            path, count = prepare_pass_two(workspace, source_csv=source)
        except (OSError, ValueError) as exc:
            self.log_line("[PASS2][ERROR] " + str(exc))
            QMessageBox.critical(self, "Pass Two import failed", str(exc))
            return
        self.log_line(f"[PASS2][PROJECT] {chosen} · {workspace}")
        self.log_line(f"[PASS2][GO] Imported {count:,} prior strict+audited "
                      f"seed records from {source}.")
        self.log_line(f"[PASS2][FILES] {path}; this project's pass 1 and jsons untouched.")
        self.log_line("[PASS2][WAITING] Pass Two native search is NOT implemented; "
                      "no moves have been run.")
        self.solve_activity.setText(
            f"Pass Two · {count:,} seeds loaded · search not started"
        )
        self.statusBar().showMessage(
            f"Pass Two CSV ready for {chosen}: {path} — search not yet configured."
        )

    def solve_board(self):
        """Hard stop for legacy auto-start paths; passes use explicit buttons."""

        self.stop_action.setEnabled(False)
        self.log_line("[SOLVER][DISABLED] Native CLI adapter pending; nothing was started.")
        self.statusBar().showMessage("STOPPED BEFORE PASS 1 — no optimiser started.")
        return

    def stop_solve(self):
        """Cooperatively stop the active worker; never force-kill a QThread."""
        if self._pass_one_worker is not None and self._pass_one_worker.isRunning():
            self._pass_one_worker.requestInterruption()
            self.stop_action.setEnabled(False)
            self.log_line("[PASS1][STOP] Cancellation requested; partial CSV retained.")
            return
        if self._calibration_worker is not None and self._calibration_worker.isRunning():
            self._calibration_worker.requestInterruption()
            self.stop_action.setEnabled(False)
            self.log_line("[MOVE100][STOP] Cancellation requested.")
            return
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
        if self._pass_one_worker is not None:
            remaining_seeds = max(0, self._solve_budget - self._solve_done)
            measured_here = max(0, self._solve_done - self._pass_one_resume_done)
            if not remaining_seeds:
                remaining = "~0m 00s (finished)"
            elif measured_here > 0 and elapsed > 0:
                eta_seconds = elapsed * remaining_seeds / measured_here
                remaining = f"~{self._clock_text(eta_seconds)} (observed throughput)"
            elif self._pass_one_previous_average is not None:
                eta_seconds = (remaining_seeds * self._pass_one_previous_average /
                               max(1, self._recommended_workers or 1))
                remaining = f"~{self._clock_text(eta_seconds)} (previous seed timings)"
            else:
                remaining = "measuring first completed seed"
            self.solve_eta.setText(
                f"Elapsed: {self._clock_text(elapsed)} · "
                f"{self._solve_done:,}/{self._solve_budget:,} seeds · "
                f"ETA: {remaining}"
            )
            return
        if self._calibration_worker is not None:
            self.solve_eta.setText(
                f"Elapsed: {self._clock_text(elapsed)} · ETA unavailable (100 decoder samples)")
            return
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
            options=QFileDialog.Option.DontUseNativeDialog,
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
        states = dict(self._calibration_stages)
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
                if key == "COLLECT":
                    states["BOARD"] = "done"
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
            options=QFileDialog.Option.DontUseNativeDialog,
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
            self.log_line("[SPACING] Obsolete Quick Solve spacing dialog removed; "
                          "donor body-spacing metadata is not part of native move calibration.")
            if dimensions["wantedRowsMode"] == "fixed" and dimensions["wantedRows"] > dimensions["actualRows"]:
                raise ValueError("Fixed preferred rows cannot exceed actual physical rows.")
            if dimensions["wantedColsMode"] == "fixed" and dimensions["wantedCols"] > dimensions["actualCols"]:
                raise ValueError("Fixed preferred columns cannot exceed actual physical columns.")
            project["board"].update(dimensions)
            project["board"]["rows"] = dimensions["actualRows"]
            project["board"]["cols"] = dimensions["actualCols"]
            self.project_path = path
            from pipeline import PipelineRun, project_import_stage_result
            self._calibration_stages = {}
            self._move_probe_result = None
            self._pass_one_prompt_pending = False
            self._probe_cut_drilled_only = None
            self._probe_stacking_allowed = None
            self.checklist.reset()
            self.solve_progress.setRange(0, 100)
            self.solve_progress.setValue(0)
            self.solve_activity.setText("100-point move check pending")
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

            workspace = project_workspace(path, self.work_root, create=True)
            self.project = project
            self.project_path = path
            self.active_workspace = workspace
            self.log_line(f"[WORK][PROJECT] {path.name} → {workspace}")
            self._solved_verified = False
            self._quick_source = None

            self._cache_schematic_preview(project)

            self.project_summary.setText(
                f"PROJECT  ·  {path.name}\n"
                f"{len(project['components'])} components · {len(project['nets'])} nets\n"
                f"WORKSPACE  ·  {workspace.name}"
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
        if self._pass_one_worker is not None and self._pass_one_worker.isRunning():
            self._close_when_idle = True
            self._pass_one_worker.requestInterruption()
            event.ignore()
            self.statusBar().showMessage("Exit requested — cancelling Pass One.")
            return
        if self._solver_worker is not None and self._solver_worker.isRunning():
            self._close_when_idle = True
            self.stop_solve()
            event.ignore()
            self.statusBar().showMessage(
                "Exit requested — stopping active solve safely before closing."
            )
            return
        if self._calibration_worker is not None and self._calibration_worker.isRunning():
            self._close_when_idle = True
            self._calibration_worker.requestInterruption()
            event.ignore()
            self.statusBar().showMessage("Exit requested — cancelling solver audit.")
            return
        if self._speed_probe_worker is not None and self._speed_probe_worker.isRunning():
            self._close_when_idle = True
            event.ignore()
            self.statusBar().showMessage("Exit requested — original CPU probe finishing.")
            return
        event.accept()


def main():
    app = QApplication(sys.argv)
    apply_arctic_theme(app)
    app.setApplicationName("Route-Mate")
    window = RouteMateWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())