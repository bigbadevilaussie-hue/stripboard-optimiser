"""StripSolve: full-canvas native Qt6 live Pass One performance dashboard.

Custom antialiased Qt painting, not HTML or an embedded browser. All plots are
fed by verified worker progress; no demonstration/fake figures at runtime.
No additional pip dependencies beyond the project's PySide6 requirement.
"""
from __future__ import annotations

from collections import deque
from math import ceil, isfinite

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QBrush, QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen,
)
from PySide6.QtWidgets import (
    QFrame, QGraphicsDropShadowEffect, QGridLayout, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

# Original StripSolve Arctic Ice + Colourburst (not a replacement dark theme).
INK = '#19334d'
MUTED = '#536f88'
LINE = '#d1e4f1'
BLUE = '#257ac2'
CYAN = '#13a9d2'
TEAL = '#168d95'
GREEN = '#159d6b'
COPPER = '#c87d4b'
AMBER = '#c77916'
CORAL = '#ce5265'
WHITE = '#ffffff'
BG = '#edf6fd'


def _shadow(widget):
    effect = QGraphicsDropShadowEffect(widget)
    effect.setBlurRadius(23)
    effect.setXOffset(0)
    effect.setYOffset(4)
    effect.setColor(QColor(27, 70, 110, 22))
    widget.setGraphicsEffect(effect)


def _card(*, minheight=90, shadow=True):
    card = QFrame()
    card.setObjectName('liveDashboardCard')
    card.setMinimumHeight(minheight)
    card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    if shadow:
        _shadow(card)
    return card


def _label(value, name, size=12, color=INK, weight=500):
    item = QLabel(value)
    item.setObjectName(name)
    item.setStyleSheet(f'color: {color}; font-size: {size}px; font-weight: {weight};')
    return item


def _title_row(title, subtitle=None, legend=None):
    row = QHBoxLayout()
    row.setSpacing(7)
    title_label = _label(title, 'chartTitle', 13, INK, 800)
    row.addWidget(title_label)
    row.addStretch()
    if legend:
        for color, caption in legend:
            key = _label('● ' + caption, 'chartLegend', 10, color, 750)
            row.addWidget(key)
    if subtitle:
        text = _label(subtitle, 'chartSubtitle', 10, MUTED, 500)
        row.addWidget(text)
    return row


def _nice_number(number: float):
    if abs(number) >= 100:
        return f'{number:,.0f}'
    if abs(number) >= 10:
        return f'{number:.1f}'
    return f'{number:.2f}'


class MetricCard(QFrame):
    """Large data metric with gradient accent and miniature antialiased trace."""

    def __init__(self, caption, color, symbol, parent=None, *, nested=False):
        super().__init__(parent)
        self.setObjectName('metricCard')
        self.setMinimumHeight(105 if nested else 113)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.color = QColor(color)
        self._trace = []
        self._color = color
        self.setStyleSheet('QFrame#metricCard {background: white; border: 1px solid #cbddec; border-radius: 16px;}')
        if not nested:
            _shadow(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(17, 12, 15, 12)
        layout.setSpacing(5)
        capline = QHBoxLayout()
        capline.setSpacing(7)
        capline.addWidget(_label(symbol, 'metricSymbol', 17, color, 800))
        capline.addWidget(_label(caption.upper(), 'metricCaption', 11, MUTED, 800))
        capline.addStretch()
        layout.addLayout(capline)
        self.value = _label('—', 'metricValue', 28, INK, 800)
        self.value.setMinimumHeight(34)
        layout.addWidget(self.value)
        self.detail = _label('Waiting for audited results', 'metricDetail', 11, MUTED, 600)
        self.detail.setWordWrap(True)
        layout.addWidget(self.detail)
        # Small sparkline strip at the card's base, drawn behind text.
        if not nested:
            layout.addSpacing(12)

    def set_metric(self, value, detail, trace=None):
        self.value.setText(str(value))
        self.detail.setText(str(detail))
        self._trace = [float(x) for x in (trace or []) if isfinite(float(x))][-45:]
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.width() < 65:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self.color)
        painter.drawRoundedRect(QRectF(16, 0, max(22, self.width()-32), 3), 2, 2)
        if len(self._trace) > 1:
            base = self.height() - 10
            top = base - 14
            lo = min(self._trace)
            hi = max(self._trace)
            width = max(hi-lo, 1.0)
            points = [QPointF(17 + (self.width()-34)*i/(len(self._trace)-1),
                              base-(x-lo)/width*(base-top))
                      for i, x in enumerate(self._trace)]
            path = QPainterPath(points[0])
            for p in points[1:]:
                path.lineTo(p)
            painter.setPen(QPen(self.color, 2.2))
            painter.drawPath(path)
        painter.end()


class SmoothPlot(QWidget):
    """QPainter plots with antialiasing, area gradients, grids and real axes."""

    def __init__(self, mode='quality', parent=None):
        super().__init__(parent)
        if mode not in ('quality', 'wc', 'runtime'):
            raise ValueError('Unknown plot type')
        self.mode = mode
        self.points = []
        self.setMinimumHeight(145)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_points(self, points):
        self.points = list(points)
        self.update()

    @staticmethod
    def _trim(points, max_items=450):
        if len(points) <= max_items:
            return points
        step = ceil(len(points)/max_items)
        result = points[::step]
        if result[-1] != points[-1]:
            result.append(points[-1])
        return result

    def _polyline(self, painter, rect, values, lower, upper, color, area=False):
        if not values:
            return
        if len(values) == 1:
            coords = [QPointF(rect.center().x(), rect.bottom() -
                              (values[0]-lower)/(upper-lower)*rect.height())]
        else:
            coords = [QPointF(rect.left()+i*rect.width()/(len(values)-1),
                              rect.bottom()-(v-lower)/(upper-lower)*rect.height())
                      for i,v in enumerate(values)]
        path = QPainterPath(coords[0])
        for pt in coords[1:]:
            path.lineTo(pt)
        if area and len(coords) > 1:
            shadow = QPainterPath(path)
            shadow.lineTo(coords[-1].x(), rect.bottom())
            shadow.lineTo(coords[0].x(), rect.bottom())
            shadow.closeSubpath()
            gradient = QLinearGradient(0, rect.top(), 0, rect.bottom())
            transparent = QColor(color)
            transparent.setAlpha(64)
            gradient.setColorAt(0, transparent)
            transparent.setAlpha(1)
            gradient.setColorAt(1, transparent)
            painter.fillPath(shadow, QBrush(gradient))
        painter.setPen(QPen(QColor(color), 2.6, Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        painter.drawPath(path)
        painter.setPen(QPen(QColor(WHITE), 2))
        painter.setBrush(QColor(color))
        painter.drawEllipse(coords[-1], 4, 4)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.TextAntialiasing)
        bounds = QRectF(40, 12, max(10, self.width()-54), max(10, self.height()-38))
        painter.setFont(QFont('Helvetica Neue', 9))
        if not self.points:
            painter.setPen(QColor(MUTED))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                             'Awaiting independently audited seeds…'
                             if self.mode != 'runtime' else
                             'Awaiting completed seed timings…')
            painter.end()
            return

        if self.mode == 'runtime':
            samples = self.points[-35:]
            top = max(0.25, max(float(x[0]) for x in samples)*1.18)
            lo, hi = 0.0, top
        else:
            # Each tuple holds Q or (wires, cuts), in verified PASS completion order.
            samples = self._trim(self.points)
            flat = [v for group in samples for v in
                    (group if isinstance(group, (tuple, list)) else (group,))]
            lo = min(flat)
            hi = max(flat)
            padding = max((hi-lo)*0.25, 1.0 if self.mode=='wc' else 2.5)
            lo = max(0.0, lo-padding)
            hi += padding
            if hi <= lo:
                hi = lo + 1.0

        painter.setPen(QPen(QColor('#dfebf4'), 1, Qt.PenStyle.DashLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for i in range(5):
            y = bounds.bottom() - i*bounds.height()/4
            painter.drawLine(QPointF(bounds.left(), y), QPointF(bounds.right(), y))
            painter.setPen(QColor('#617a92'))
            painter.drawText(QRectF(0, y-7, 35, 15), Qt.AlignmentFlag.AlignRight,
                             _nice_number(lo+(hi-lo)*i/4))
            painter.setPen(QPen(QColor('#dfebf4'), 1, Qt.PenStyle.DashLine))
        painter.setPen(QColor('#69829a'))
        painter.drawText(QRectF(bounds.left(), bounds.bottom()+5, bounds.width(), 18),
                         Qt.AlignmentFlag.AlignCenter,
                         'Verified PASS sequence' if self.mode!='runtime'
                         else 'Recent completed seeds →')
        if self.mode == 'runtime':
            count = len(samples)
            slot = bounds.width()/max(count,1)
            for i,(duration,status) in enumerate(samples):
                height = max(2.0, float(duration)/hi*bounds.height())
                color = TEAL if status=='PASS' else CORAL if status=='ERROR' else BLUE
                grad = QLinearGradient(0, bounds.bottom()-height, 0, bounds.bottom())
                grad.setColorAt(0,QColor(color))
                faint = QColor(color); faint.setAlpha(100)
                grad.setColorAt(1,faint)
                painter.setBrush(QBrush(grad))
                painter.setPen(Qt.PenStyle.NoPen)
                painter.drawRoundedRect(QRectF(bounds.left()+i*slot+slot*0.12,
                                                bounds.bottom()-height,
                                                max(2,slot*0.76),height),2,2)
        elif self.mode == 'wc':
            self._polyline(painter,bounds,[float(x[0]) for x in samples],lo,hi,BLUE)
            self._polyline(painter,bounds,[float(x[1]) for x in samples],lo,hi,COPPER)
        else:
            self._polyline(painter,bounds,[float(x) for x in samples],lo,hi,CYAN,area=True)
        painter.end()


class OutcomeRing(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.counts = (0,0,0,0)
        self.setMinimumHeight(190)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_counts(self, passed, failed, errors, remaining):
        self.counts = tuple(max(0,int(v)) for v in (passed,failed,errors,remaining))
        self.update()

    def pass_rate_text(self):
        passed, failed, _, _ = self.counts
        audited = passed + failed
        return f"{100 * passed / audited:.1f}%" if audited else "—"

    def completion_text(self):
        passed, failed, errors, remaining = self.counts
        total = passed + failed + errors + remaining
        if not total:
            return "—"
        # Errors are retried on resume, so they are not completed seeds.
        completed = passed + failed
        if completed == total:
            return "100%"
        percentage = min(99.99, 100 * completed / total)
        return f"{percentage:.2f}".rstrip("0").rstrip(".") + "%"

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        passed, failed, errors, remaining = self.counts
        total = max(1, sum(self.counts))
        diameter = min(self.width()*0.53,self.height()-16,180)
        diameter = max(45,diameter)
        left = max(12,(self.width()*0.55-diameter)/2)
        ring = QRectF(left,(self.height()-diameter)/2,diameter,diameter)
        painter.setPen(QPen(QColor('#e2edf6'),19,Qt.PenStyle.SolidLine,
                            Qt.PenCapStyle.RoundCap))
        painter.drawArc(ring,0,5760)
        current = 90*16
        # Every scheduled seed occupies a share of the campaign ring.
        for value,color in ((passed,TEAL),(failed,BLUE),(errors,CORAL),(remaining,'#dbe7ef')):
            if value:
                sweep = -int(value/total*5760)
                painter.setPen(QPen(QColor(color),19,Qt.PenStyle.SolidLine,
                                    Qt.PenCapStyle.FlatCap))
                painter.drawArc(ring,current,sweep)
                current += sweep
        painter.setPen(QColor(INK))
        font = QFont('Helvetica Neue',24)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(ring.adjusted(8,4,-8,-12),Qt.AlignmentFlag.AlignCenter,
                         self.completion_text())
        font = QFont('Helvetica Neue',9)
        painter.setFont(font)
        painter.setPen(QColor(MUTED))
        painter.drawText(ring.adjusted(3,diameter*0.40,-3,0),
                         Qt.AlignmentFlag.AlignCenter,'Seeds completed')
        leg_x = max(ring.right()+20,self.width()*0.56)
        y = max(14,(self.height()-92)/2)
        for title,value,color in (('Verified',passed,TEAL),('Not qualified',failed,BLUE),
                                  ('Errors',errors,CORAL),('Pending',remaining,'#a3baca')):
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(color))
            painter.drawRoundedRect(QRectF(leg_x,y+4,8,8),3,3)
            painter.setPen(QColor(INK))
            font = QFont('Helvetica Neue',10)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(QRectF(leg_x+15,y, max(10,self.width()-leg_x-21),18),
                             Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter,
                             f'{title}  {value:,}')
            y += 24
        painter.end()


class LiveDashboard(QWidget):
    """The large board-preview canvas becomes a responsive live performance UI.

    No top-five list. The *best individual strict verified seed* is shown in the
    quality card, without turning the interface into a leaderboard.
    """
    view_winner_requested = Signal()
    view_board_requested = Signal()

    def __init__(self,parent=None):
        super().__init__(parent)
        self.setObjectName('stripSolveLiveDashboard')
        self.setStyleSheet('''
          QWidget#stripSolveLiveDashboard {background: #edf6fd;}
          QWidget#liveDashboardSurface {background: #edf6fd;}
          QFrame#liveDashboardCard {background: #ffffff; border: 1px solid #cbddec; border-radius: 16px;}
          QPushButton#dashboardAction {background: #257ac2; color: white;
              border: none; border-radius: 10px; padding: 10px 16px; font-weight: 750;}
          QPushButton#dashboardAction:hover {background: #1664aa;}
          QPushButton#dashboardAction:disabled {background: #cadfea; color: #638299;}
          QPushButton#dashboardSecondary {background: #ffffff; color: #215d88;
              border: 1px solid #a5c9e1; border-radius: 10px; padding: 10px 16px; font-weight: 750;}
          QPushButton#dashboardSecondary:hover {background: #e6f5fd;}
          QProgressBar#dashboardProgress {height: 13px; background: #d9eaf5;
              border: none; border-radius: 6px; text-align: center; color: #0f3c5e;
              font-size: 10px; font-weight: 800;}
          QProgressBar#dashboardProgress::chunk {background: #13a9d2; border-radius: 6px;}
        ''')
        self._total = 0
        self._done = 0
        self._qualified = 0
        self._failed = 0
        self._errors = 0
        self._best = None
        self._runtime = deque(maxlen=60)

        base = QVBoxLayout(self)
        base.setContentsMargins(0,0,0,0)
        self.scroller = QScrollArea()
        self.scroller.setObjectName('liveDashboardScroller')
        self.scroller.setFrameShape(QFrame.Shape.NoFrame)
        self.scroller.setWidgetResizable(True)
        self.scroller.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroller.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        base.addWidget(self.scroller)
        surface = QWidget()
        surface.setObjectName('liveDashboardSurface')
        surface.setMinimumWidth(745)
        self.scroller.setWidget(surface)
        content = QVBoxLayout(surface)
        content.setContentsMargins(20,17,20,17)
        content.setSpacing(15)

        header = QHBoxLayout()
        labels = QVBoxLayout(); labels.setSpacing(3)
        self.heading = _label('PASS ONE  /  LIVE RESULTS', 'liveHeading', 22, INK, 850)
        self.subtitle = _label('STRIPSOLVE · Awaiting native solver', 'liveSubtitle', 12, MUTED, 600)
        labels.addWidget(self.heading); labels.addWidget(self.subtitle)
        header.addLayout(labels); header.addStretch()
        self.state = _label('● READY', 'liveBadge', 12, TEAL, 850)
        self.state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.state.setMinimumWidth(125)
        self.state.setStyleSheet('color:#117b83; background:#d7f2f1; border-radius:11px; padding:8px 12px; font-weight:850;')
        header.addWidget(self.state)
        content.addLayout(header)

        middle = QHBoxLayout(); middle.setSpacing(13)
        quality_card = _card(minheight=285)
        qlayout = QVBoxLayout(quality_card)
        qlayout.setContentsMargins(16,14,16,16); qlayout.setSpacing(14)
        qlayout.addLayout(_title_row('BEST VERIFIED BOARD'))
        self.bestq = MetricCard('Quality score',CYAN,'✦', nested=True)
        self.bestq.value.setStyleSheet(f'color:{TEAL}; font-size:36px; font-weight:850;')
        self.bestq.setToolTip('Construction quality out of 100. Higher is better. '
                             'Fewer wires, cuts, shorter jumpers and less stacking improve the score.')
        qlayout.addWidget(self.bestq)
        score_grid = QGridLayout()
        score_grid.setHorizontalSpacing(12)
        self.w_card = MetricCard('Jumper wires',BLUE,'⌁', nested=True)
        self.c_card = MetricCard('Track cuts',COPPER,'✂', nested=True)
        self.s_card = MetricCard('Max wire stack',CORAL,'≡', nested=True)
        for i, widget in enumerate((self.w_card, self.c_card, self.s_card)):
            score_grid.addWidget(widget,0,i)
            score_grid.setColumnStretch(i,1)
        qlayout.addLayout(score_grid)
        middle.addWidget(quality_card,7)

        outcome_card = _card(minheight=247)
        olayout = QVBoxLayout(outcome_card)
        olayout.setContentsMargins(15,14,15,10); olayout.setSpacing(5)
        olayout.addLayout(_title_row('RUN OUTCOMES'))
        self.ring = OutcomeRing()
        olayout.addWidget(self.ring,1)
        self.qualification_rate = _label('Qualification rate: —', 'qualificationRate', 14, TEAL, 750)
        self.qualification_rate.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.qualification_rate.setToolTip('Verified seeds divided by all definitively audited seeds. Errors and pending seeds are excluded.')
        olayout.addWidget(self.qualification_rate)
        middle.addWidget(outcome_card,4)
        content.addLayout(middle,2)

        bottom = QHBoxLayout(); bottom.setSpacing(13)
        wc_card = _card(minheight=212)
        wl = QVBoxLayout(wc_card); wl.setContentsMargins(14,13,14,12); wl.setSpacing(5)
        wl.addLayout(_title_row('TOTAL JUMPER WIRE LENGTH'))
        self.length_mm = _label('—', 'wireLengthMm', 30, CYAN, 850)
        self.length_inches = _label('—', 'wireLengthInches', 18, MUTED, 700)
        self.average_length = _label('—', 'wireLengthAverage', 12, MUTED, 600)
        wl.addStretch(1)
        wl.addWidget(self.length_mm); wl.addWidget(self.length_inches)
        wl.addSpacing(12)
        wl.addWidget(self.average_length); wl.addStretch(1)
        bottom.addWidget(wc_card,6)

        runtime_card = _card(minheight=212)
        rl = QVBoxLayout(runtime_card); rl.setContentsMargins(14,13,14,12); rl.setSpacing(5)
        rl.addLayout(_title_row('SEED RUNTIMES',subtitle='seconds'))
        self.runtime_plot = SmoothPlot('runtime')
        rl.addWidget(self.runtime_plot,1)
        bottom.addWidget(runtime_card,5)

        pace_card = _card(minheight=212)
        pace = QVBoxLayout(pace_card); pace.setContentsMargins(15,14,15,14); pace.setSpacing(10)
        pace.addLayout(_title_row('RUN CONTROL'))
        self.processed = _label('0 / 0 seeds', 'liveProgressCount', 19, INK, 850)
        pace.addWidget(self.processed)
        self.progress = QProgressBar(); self.progress.setObjectName('dashboardProgress')
        self.progress.setRange(0,1); self.progress.setValue(0)
        self.progress.setTextVisible(False)
        pace.addWidget(self.progress)
        timing = QGridLayout(); timing.setHorizontalSpacing(12); timing.setVerticalSpacing(3)
        timing.addWidget(_label('Elapsed time','elapsedCaption',11,MUTED,700),0,0)
        timing.addWidget(_label('Time remaining','remainingCaption',11,MUTED,700),0,1)
        self.elapsed = _label('—','elapsedValue',20,INK,800)
        self.remaining = _label('—','remainingValue',20,TEAL,800)
        self.remaining.setWordWrap(True)
        timing.addWidget(self.elapsed,1,0)
        timing.addWidget(self.remaining,1,1)
        pace.addLayout(timing)
        self.eta = _label('','liveEta',10,MUTED,550)
        self.eta.setWordWrap(True)
        pace.addWidget(self.eta)
        self.run_note = _label("", "runNote", 11, MUTED, 600)
        self.run_note.setWordWrap(True)
        pace.addWidget(self.run_note)
        pace.addStretch()
        bottom.addWidget(pace_card,4)
        content.addLayout(bottom,2)

        actions = QHBoxLayout()
        self.disclaimer = _label('Only independently verified boards qualify.',
                                 'liveFootnote',11,MUTED,550)
        self.disclaimer.setWordWrap(True)
        actions.addWidget(self.disclaimer,1)
        self.board_button = QPushButton('Board preview')
        self.board_button.setObjectName('dashboardSecondary')
        self.board_button.clicked.connect(lambda _checked=False: self.view_board_requested.emit())
        actions.addWidget(self.board_button)
        self.winner_button = QPushButton('View saved winner')
        self.winner_button.setObjectName('dashboardAction')
        self.winner_button.setEnabled(False)
        self.winner_button.clicked.connect(lambda _checked=False: self.view_winner_requested.emit())
        actions.addWidget(self.winner_button)
        content.addLayout(actions)
        self.reset_for_project('')

    def _redraw_plots(self):
        self.runtime_plot.set_points(list(self._runtime))

    def reset_for_project(self, project):
        self._total=0; self._done=0; self._qualified=0; self._failed=0; self._errors=0
        self._best=None
        self._runtime.clear()
        self.subtitle.setText(f'{project.upper()} · No Pass One campaign started' if project else
                              'STRIPSOLVE · Awaiting native solver')
        self.state.setText('● READY')
        self._set_state_style(TEAL,'#d7f2f1')
        self.set_run_times('—', '—')
        self.run_note.clear()
        self.winner_button.setEnabled(False)
        self._update_view()

    def start(self,project,moves,seeds,*,debug,workers=None,resumed=False):
        self.reset_for_project(project)
        self._total=max(0,int(seeds))
        self.subtitle.setText(f'{project.upper()}  ·  {int(moves)//1000}k moves  ·  '
                              f'{"Debug run" if debug else "Full run"}')
        self.state.setText('● RESUMING' if resumed else '● LIVE RUNNING')
        self._set_state_style(TEAL,'#d7f2f1')
        self._update_view()

    def set_run_times(self, elapsed, remaining, detail=''):
        self.elapsed.setText(elapsed)
        self.remaining.setText(remaining)
        self.eta.setText(detail)

    def _set_state_style(self,foreground,background):
        self.state.setStyleSheet(f'color:{foreground};background:{background};'
                                  'border-radius:11px;padding:8px 12px;font-weight:850;')

    def update_progress(self,snapshot):
        if snapshot.get('history') is not None:
            for item in snapshot['history']:
                self._append_item(item)
        self._done=max(0,int(snapshot.get('done',self._done)))
        self._total=max(self._done,int(snapshot.get('total',self._total)))
        self._qualified=max(0,int(snapshot.get('qualified',self._qualified)))
        self._failed=max(0,int(snapshot.get('failed',self._failed)))
        self._errors=max(0,int(snapshot.get('errors',self._errors)))
        best=snapshot.get('best')
        if best:
            self._best=best
        latest=snapshot.get('last')
        if latest:
            self._append_item(latest)
        self._update_view()

    def _append_item(self,item):
        status=item.get('status')
        if status is None:
            status='PASS' if item.get('valid') is True else 'FAIL' if item.get('valid') is False else 'ERROR'
        duration=item.get('time_taken',item.get('seconds'))
        try:
            seconds=float(duration)
        except (TypeError,ValueError):
            return
        if isfinite(seconds) and seconds>=0:
            self._runtime.append((seconds,status))

    def _update_view(self):
        best=self._best
        if best:
            self.bestq.set_metric(f'{float(best["q"]):.2f} / 100',
                                  f'Seed {int(best["seed"]):04d} · verified')
            self.w_card.set_metric(str(best["w"]), 'On the board')
            self.c_card.set_metric(str(best["cut"]), 'In the copper tracks')
            stack = int(best["s"])
            self.s_card.set_metric(str(stack), 'No stacking' if stack <= 1 else 'Wires overlapping')
            length = float(best["wire_length_mm"])
            self.length_mm.setText(f'{length:,.2f} mm')
            self.length_inches.setText(f'{length/25.4:,.2f} in')
            avg = length / int(best["w"]) if int(best["w"]) else 0
            self.average_length.setText(f'Average jumper: {avg:.2f} mm')
        else:
            self.bestq.set_metric('—','Awaiting verified seed')
            for card in (self.w_card, self.c_card, self.s_card):
                card.set_metric('—', 'Awaiting champion')
            self.length_mm.setText('—')
            self.length_inches.setText('—')
            self.average_length.setText('Awaiting champion')
        self.progress.setRange(0,max(1,self._total))
        self.progress.setValue(min(self._done,self.progress.maximum()))
        self.processed.setText(f'{self._done:,} / {self._total:,} seeds')
        self.ring.set_counts(self._qualified,self._failed,self._errors,
                             max(0,self._total-self._qualified-self._failed-self._errors))
        self.qualification_rate.setText(f'Qualification rate: {self.ring.pass_rate_text()}')
        self._redraw_plots()

    def finish(self,*,completed,qualified):
        self._qualified=int(qualified)
        if completed and not self._qualified:
            self.state.setText('✕ FAILED — NO QUALIFIERS')
            self._set_state_style(CORAL, '#ffe3e9')
            self.run_note.setText('All seeds tested · no qualifying boards')
        else:
            self.state.setText('✓ COMPLETE' if completed else '● INCOMPLETE')
            self._set_state_style(GREEN if completed else AMBER,
                                  '#d7f3e7' if completed else '#fff2dc')
        self._update_view()

    def interrupted(self,message):
        self.state.setText('● STOPPED')
        self._set_state_style(AMBER,'#fff2dc')
        self.run_note.setText(message)

    def set_winner_available(self,available):
        self.winner_button.setEnabled(bool(available))