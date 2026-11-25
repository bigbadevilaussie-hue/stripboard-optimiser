"""Compact live Pass One leaderboard for StripSolve.

Presentation only. Scores come exclusively from the independent strict audit
reported by gui.pass_one; this widget does not score or rerun any seed.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QVBoxLayout, QWidget,
)


class LiveScoreboard(QWidget):
    """Five audited leaders in a dedicated tab, not the crowded Overview."""

    view_winner_requested = Signal()
    MEDALS = ("🥇", "🥈", "🥉", "4", "5")

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("passOneLiveScoreboard")
        self.setStyleSheet("""
            QWidget#passOneLiveScoreboard { background: #f4f9fe; }
            QLabel#scoreHeading { font-size: 15px; font-weight: 800; color: #163c57; }
            QLabel#scoreMode { font-size: 11px; color: #395d77; }
            QLabel#scoreState { font-size: 11px; font-weight: 700; color: #147c83; }
            QLabel#scoreNumber { font-size: 20px; font-weight: 800; color: #164f76; }
            QLabel#scoreLabel { font-size: 10px; font-weight: 650; color: #4a667c; }
            QLabel#scoreSubhead { font-size: 11px; font-weight: 800; color: #1a4d72; }
            QLabel#scoreSeed { font-size: 12px; font-weight: 750; color: #163c57; }
            QLabel#scoreQuality { font-size: 12px; font-weight: 800; color: #086f81; }
            QLabel#scoreCounts { font-size: 11px; color: #395d77; }
            QLabel#scoreRecent { font-size: 11px; color: #355874; }
            QLabel#scoreNote { font-size: 10px; color: #526c80; }
            QFrame#scoreRow { background: #ffffff; border: 1px solid #c9dfef;
                              border-radius: 7px; }
            QFrame#scoreLeader { background: #dff5f2; border: 1px solid #75c5bc;
                                 border-radius: 8px; }
            QFrame#scoreStat { background: #e7f3fc; border: 1px solid #c8e0ef;
                               border-radius: 8px; }
        """)
        self._total = 0
        outer = QVBoxLayout(self)
        outer.setContentsMargins(7, 9, 7, 9)
        outer.setSpacing(9)

        title = QLabel("🏆 PASS ONE · LIVE")
        title.setObjectName("scoreHeading")
        outer.addWidget(title)
        self.mode = QLabel("Waiting for Pass One")
        self.mode.setObjectName("scoreMode")
        self.mode.setWordWrap(True)
        outer.addWidget(self.mode)

        stats = QGridLayout()
        stats.setHorizontalSpacing(5)
        self.stat_values = {}
        for i, (key, label) in enumerate((
            ("done", "CHECKED"), ("qualified", "PASS"), ("errors", "ERRORS"),
        )):
            frame = QFrame()
            frame.setObjectName("scoreStat")
            cell = QVBoxLayout(frame)
            cell.setContentsMargins(4, 4, 4, 4)
            cell.setSpacing(1)
            value = QLabel("0")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value.setObjectName("scoreNumber")
            heading = QLabel(label)
            heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
            heading.setObjectName("scoreLabel")
            cell.addWidget(value)
            cell.addWidget(heading)
            stats.addWidget(frame, 0, i)
            self.stat_values[key] = value
        outer.addLayout(stats)

        self.progress = QProgressBar()
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("0 / 0 checked")
        outer.addWidget(self.progress)

        header = QLabel("TOP FIVE · STRICT AUDIT PASS")
        header.setObjectName("scoreSubhead")
        outer.addWidget(header)
        self.leader_rows = []
        for i in range(5):
            frame = QFrame()
            frame.setObjectName("scoreLeader" if i == 0 else "scoreRow")
            row = QHBoxLayout(frame)
            row.setContentsMargins(5, 7, 5, 7)
            row.setSpacing(5)
            rank = QLabel(self.MEDALS[i])
            rank.setFixedWidth(21)
            rank.setAlignment(Qt.AlignmentFlag.AlignCenter)
            seed = QLabel("—")
            seed.setObjectName("scoreSeed")
            quality = QLabel("Q —")
            quality.setObjectName("scoreQuality")
            counts = QLabel("—")
            counts.setObjectName("scoreCounts")
            row.addWidget(rank)
            row.addWidget(seed)
            row.addStretch(1)
            row.addWidget(quality)
            row.addWidget(counts)
            outer.addWidget(frame)
            self.leader_rows.append((seed, quality, counts))

        self.state = QLabel("No verified results yet")
        self.state.setObjectName("scoreState")
        self.state.setWordWrap(True)
        outer.addWidget(self.state)
        self.recent = QLabel("Last seed: —")
        self.recent.setObjectName("scoreRecent")
        self.recent.setWordWrap(True)
        outer.addWidget(self.recent)
        note = QLabel("Q: higher is better · ties: fewer W, then C, then seed")
        note.setObjectName("scoreNote")
        note.setWordWrap(True)
        outer.addWidget(note)
        self.view_winner_button = QPushButton("🏆 View saved winner")
        self.view_winner_button.setObjectName("scoreViewWinner")
        self.view_winner_button.setEnabled(False)
        self.view_winner_button.setToolTip(
            "Open previously saved component and copper SVGs; no rerun"
        )
        self.view_winner_button.clicked.connect(
            lambda _checked=False: self.view_winner_requested.emit()
        )
        outer.addWidget(self.view_winner_button)
        outer.addStretch(1)

    def start(self, project: str, moves: int, seeds: int, *, debug: bool,
              resumed: bool = False):
        self._total = seeds
        self.mode.setText(
            f"{project} · {moves // 1000}k moves · "
            f"{'DEBUG' if debug else 'FULL'} · {seeds:,} seeds"
        )
        self.state.setText("Resuming audited candidates…" if resumed else
                           "Running native seeds · checking strict PASS")
        self.progress.setRange(0, seeds)
        self.progress.setValue(0)
        self.progress.setFormat("%v / %m checked")
        for label in self.stat_values.values():
            label.setText("0")
        for seed, quality, counts in self.leader_rows:
            seed.setText("—")
            quality.setText("Q —")
            counts.setText("—")
        self.recent.setText("Last seed: —")
        self.view_winner_button.setEnabled(False)

    def reset_for_project(self, project: str):
        """A newly loaded project must not inherit another project's scores."""
        self.start(project, 0, 0, debug=False)
        self.mode.setText(f"{project} · No Pass One campaign started")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.progress.setFormat("No campaign")
        self.state.setText("Run Pass One to see strictly audited leaders")

    def update_progress(self, snapshot: dict):
        """Called on GUI thread for each confirmed worker result."""
        done = max(0, int(snapshot.get("done", 0)))
        total = max(1, int(snapshot.get("total", self._total or 1)))
        self._total = total
        self.progress.setRange(0, total)
        self.progress.setValue(min(done, total))
        for key, value in self.stat_values.items():
            value.setText(f"{int(snapshot.get(key, 0)):,}")
        leaders = snapshot.get("leaders", ())
        for i, (seed, quality, counts) in enumerate(self.leader_rows):
            if i < len(leaders):
                item = leaders[i]
                seed.setText(f"{int(item['seed']):04d}")
                quality.setText(f"Q {float(item['q']):.2f}")
                counts.setText(f"{int(item['w'])}W/{int(item['cut'])}C")
            else:
                seed.setText("—")
                quality.setText("Q —")
                counts.setText("—")
        self.state.setText(
            f"{int(snapshot.get('qualified', 0)):,} strictly verified · "
            f"{int(snapshot.get('failed', 0)):,} failed"
        )
        last = snapshot.get("last")
        if last:
            if last.get("valid") is True:
                status = "PASS"
            elif last.get("valid") is False:
                status = "FAIL"
            else:
                status = "ERROR"
            self.recent.setText(
                f"Last seed: {int(last['seed']):04d} · {status}"
            )

    def finish(self, *, completed: bool, qualified: int):
        self.state.setText(
            f"COMPLETE · {qualified:,} audited PASS"
            if completed else
            f"INCOMPLETE · {qualified:,} audited PASS · resume available"
        )

    def interrupted(self, message: str):
        self.state.setText(message)

    def set_winner_available(self, available: bool):
        self.view_winner_button.setEnabled(bool(available))
