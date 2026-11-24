"""Exactly 100 audits and original speed-probe code are available."""
import unittest
from unittest.mock import patch
import speed_probe
from gui import native_calibration as audit

class AuditContract(unittest.TestCase):
    def test_original_worker_probe(self):
        self.assertEqual(speed_probe.TASKS,24)
        self.assertTrue(callable(speed_probe.probe_worker_scaling))
    def test_exactly_100(self):
        self.assertEqual(audit.TOTAL,100)
        self.assertEqual(len(audit.SEEDS),50)
        self.assertEqual(audit.PAIR_BUDGETS,(10000,20000))
    def test_100_checks(self):
        def fake(project,moves,seed,folder,cancelled):
            return {"moves":moves,"seed":seed,"seconds":0.01,
                    "valid":seed%2==0,"wires":10,"cuts":38,"wireLength":200}
        seen=[]
        with patch.object(audit,"prereqs"),patch.object(audit,"trial",side_effect=fake):
            result=audit.calibrate({"board":{}},3,seen.append,lambda:False)
        self.assertEqual(len(seen),100)
        self.assertEqual(result["reports"][10000]["passed"],25)
        self.assertEqual(result["reports"][20000]["passed"],25)
