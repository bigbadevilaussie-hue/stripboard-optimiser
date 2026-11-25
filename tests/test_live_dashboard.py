"""StripSolve full-preview live Qt6 dashboard and winner-consent tests.

Use the real PySide6 widgets offscreen. No native solver is run by these tests.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from gui.pass_one import best_audited


class AuditedChampionTests(unittest.TestCase):
    def test_best_only_strict_pass_and_deterministic_tie_breaking(self):
        data = [
            dict(seed='0001',status='FAIL',q='',w='',cut='',time_taken='0.2'),
            dict(seed='0002',status='ERROR',q='',w='',cut='',time_taken='0.2'),
            dict(seed='0003',status='PASS',s=2,wire_length_mm=284.48,q='79.40',w='31',cut='45',time_taken='1.0'),
            dict(seed='0004',status='PASS',s=2,wire_length_mm=284.48,q='82.10',w='32',cut='44',time_taken='1.0'),
            dict(seed='0005',status='PASS',s=2,wire_length_mm=284.48,q='82.10',w='29',cut='50',time_taken='1.0'),
            dict(seed='0006',status='PASS',s=2,wire_length_mm=284.48,q='82.10',w='29',cut='40',time_taken='1.0'),
            dict(seed='0007',status='PASS',s=2,wire_length_mm=284.48,q='82.10',w='29',cut='40',time_taken='1.0'),
        ]
        best = best_audited(data)
        self.assertEqual(best['seed'],6)
        self.assertEqual(best['q'],82.10)
        self.assertEqual(best['status'],'PASS')
        self.assertIsNone(best_audited(data[:2]))

    def test_single_new_pass_competes_against_retained_champion(self):
        old = dict(seed=50,status='PASS',s=2,wire_length_mm=284.48,q=78.24,w=29,cut=44,time_taken=2.2)
        worse = dict(seed='0120',status='PASS',s=2,wire_length_mm=284.48,q='77.00',w='25',cut='37',time_taken='1.4')
        better = dict(seed='0122',status='PASS',s=2,wire_length_mm=284.48,q='78.24',w='27',cut='40',time_taken='1.4')
        self.assertEqual(best_audited([old,worse])['seed'],50)
        self.assertEqual(best_audited([old,better])['seed'],122)


os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
try:
    from PySide6.QtWidgets import QApplication, QStackedWidget
    from gui.live_dashboard import LiveDashboard, SmoothPlot, OutcomeRing
    from gui.main import RouteMateWindow
except ImportError:
    QApplication = None


@unittest.skipIf(QApplication is None,'PySide6 unavailable')
class LiveDashboardGuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    @staticmethod
    def _sample():
        return {
            'done':125,'total':200,'qualified':2,'failed':123,'errors':0,
            'best':dict(seed=50,status='PASS',s=2,wire_length_mm=284.48,q=78.24,w=29,cut=44,time_taken=2.2),
            'history':[
                dict(seed='0050',status='PASS',s=2,wire_length_mm=284.48,q='78.24',w='29',cut='44',time_taken='2.2'),
                dict(seed='0084',status='PASS',s=2,wire_length_mm=284.48,q='76.21',w='31',cut='46',time_taken='1.9'),
                dict(seed='0011',status='FAIL',q='',w='',cut='',time_taken='2.3'),
            ],
            'last':{'seed':125,'valid':False,'seconds':1.4},
        }

    def test_large_rounded_dashboard_tracks_real_worker_data(self):
        board = LiveDashboard()
        try:
            board.start('AUDIO',10000,200,debug=True,workers=3,resumed=True)
            board.update_progress(self._sample())
            self.assertIn('AUDIO',board.subtitle.text())
            self.assertIn('10k moves',board.subtitle.text())
            self.assertEqual(board.processed.text(),'125 / 200 seeds')
            self.assertEqual(board.ring.counts[0],2)
            self.assertEqual(board.bestq.value.text(),'78.24 / 100')
            self.assertEqual(board.w_card.value.text(),'29')
            self.assertEqual(board.c_card.value.text(),'44')
            self.assertEqual(board.s_card.value.text(),'2')
            self.assertEqual(board.length_mm.text(),'284.48 mm')
            self.assertEqual(board.progress.value(),125)
            self.assertEqual(board.ring.counts,(2,123,0,75))
            self.assertFalse(hasattr(board,'quality_plot'))
            self.assertFalse(hasattr(board,'wc_plot'))
            self.assertEqual(len(board.runtime_plot.points),4)
            self.assertFalse(hasattr(board,'last'))
            self.assertFalse(hasattr(board,'workers'))
            self.assertFalse(board.winner_button.isEnabled())
            self.assertFalse(hasattr(board,'leader_rows'))
            self.assertIsInstance(board.runtime_plot,SmoothPlot)
            self.assertIsInstance(board.ring,OutcomeRing)
        finally:
            board.close()

    def test_dashboard_is_main_preview_not_sidebar(self):
        window = RouteMateWindow()
        try:
            self.assertIsInstance(window.preview_stack,QStackedWidget)
            self.assertEqual(window.preview_stack.count(),2)
            self.assertEqual(window.sidebar_tabs.count(),2) # Overview + Activity only
            self.assertIs(window.preview_stack.widget(0),window.top_view)
            self.assertIs(window.preview_stack.widget(1),window.dashboard)
            window.dashboard.start('AUDIO',10000,200,debug=True,workers=3)
            window._show_live_dashboard()
            self.assertIs(window.preview_stack.currentWidget(),window.dashboard)
            self.assertTrue(window.board_fit_button.isHidden())
            window._return_to_board_preview()
            self.assertIs(window.preview_stack.currentWidget(),window.top_view)
        finally:
            window.close()

    def test_new_project_resets_dashboard_and_chart_history(self):
        dashboard = LiveDashboard()
        try:
            dashboard.start('AUDIO',10000,200,debug=True)
            dashboard.update_progress(self._sample())
            dashboard.set_winner_available(True)
            dashboard.reset_for_project('MOTO')
            self.assertEqual(dashboard.ring.counts[0],0)
            self.assertEqual(dashboard.length_mm.text(),'—')
            self.assertFalse(dashboard.winner_button.isEnabled())
            self.assertIn('MOTO',dashboard.subtitle.text())
        finally:
            dashboard.close()

    def _champion(self, temp, seed=50):
        path = Path(temp) / f'winner_seed_{seed:04d}.json'
        path.write_text(json.dumps({'board':{'rows':24,'cols':56},'components':[]}),encoding='utf-8')
        result = {
            'winner_json':str(path),'winner_seed':seed,'moves':10000,
            'checked':200,'qualified':17,'errors':0,'completed':True,
            'csv':str(Path(temp)/'results.csv'),
            'log':str(Path(temp)/'activity.log'),
        }
        svg = '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20"><rect width="20" height="20"/></svg>'
        return path,result,svg

    def test_decline_keeps_big_dashboard_visible_and_saves_both_svgs(self):
        with tempfile.TemporaryDirectory() as temp:
            path,result,svg = self._champion(temp)
            window = RouteMateWindow()
            try:
                window._top_svg = 'pre-run board'
                window._copper_svg = 'pre-run copper'
                window.dashboard.start('AUDIO',10000,200,debug=True)
                window._show_live_dashboard()
                def render(_project):
                    window._copper_svg = svg
                    return svg,'native renderer'
                with patch.object(window,'_render_component_side',side_effect=render), \
                     patch.object(window,'_ask_to_view_pass_one_winner',return_value=False) as ask:
                    window._pass_one_completed(result)
                ask.assert_called_once_with(50)
                self.assertIs(window.preview_stack.currentWidget(),window.dashboard)
                self.assertEqual(window._top_svg,'pre-run board')
                self.assertEqual(window._copper_svg,'pre-run copper')
                self.assertTrue(window.dashboard.winner_button.isEnabled())
                self.assertTrue(path.with_name(path.stem+'-components.svg').is_file())
                self.assertTrue(path.with_name(path.stem+'-copper.svg').is_file())
                window.dashboard.winner_button.click()
                self.assertIs(window.preview_stack.currentWidget(),window.top_view)
                self.assertEqual(window._top_svg,svg)
            finally:
                window.close()

    def test_yes_opens_saved_winner_in_board_preview(self):
        with tempfile.TemporaryDirectory() as temp:
            path,result,svg = self._champion(temp,seed=17)
            window = RouteMateWindow()
            try:
                window.dashboard.start('AUDIO',10000,200,debug=True)
                window._show_live_dashboard()
                def render(_project):
                    window._copper_svg=svg
                    return svg,'native renderer'
                with patch.object(window,'_render_component_side',side_effect=render), \
                     patch.object(window,'_ask_to_view_pass_one_winner',return_value=True) as ask:
                    window._pass_one_completed(result)
                ask.assert_called_once_with(17)
                self.assertIs(window.preview_stack.currentWidget(),window.top_view)
                self.assertEqual(window._top_svg,svg)
                self.assertEqual(window._copper_svg,svg)
            finally:
                window.close()


if __name__ == '__main__':
    unittest.main()