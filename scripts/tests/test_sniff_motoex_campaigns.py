"""Standalone sniffer unit tests; synthetic boards, no solver."""
import unittest
from sniff_motoex_campaigns import quality, signatures, wire_details, invariants

class SniffTests(unittest.TestCase):
    def board(self):
        return {"board":{"rows":24,"cols":56,"lockedRows":True,"lockedCols":True,
                         "cuts":[],"wires":[
                             {"from":{"row":0,"col":3},"to":{"row":3,"col":3}},
                             {"from":{"row":2,"col":3},"to":{"row":4,"col":3}},
                             {"from":{"row":4,"col":3},"to":{"row":5,"col":4}}]},
                "components":[],"nets":[],"netAssignments":[],"componentDefs":[]}

    def test_stack_and_nonvertical(self):
        b=self.board(); q=quality(b)
        self.assertEqual(q["stack"],2)
        self.assertEqual(q["nonvertical"],1)
        self.assertEqual(q["wires"],3)
        self.assertAlmostEqual(q["length_mm"],(5+2**.5)*2.54,places=5)

    def test_wire_union(self):
        b=self.board(); w=b["board"]["wires"][2]
        rec={"wire":3,**w,"violations":["NONVERTICAL","CROSSINGS"],
             "crossingComponents":["GPS","MPU"]}
        e={"crossings":2,"diagnostics":{"wireViolations":[rec]}}
        self.assertEqual(wire_details(e,b),([3],[3],[("GPS",1),("MPU",1)],True))
        e["crossings"]=3
        self.assertFalse(wire_details(e,b)[3])

    def test_signature_and_locks(self):
        b=self.board()
        self.assertEqual(invariants(b,b),[])
        p,l=signatures(b)
        b["board"]["wires"][0]["to"]["row"]=4
        self.assertEqual(signatures(b)[0],p)
        self.assertNotEqual(signatures(b)[1],l)
        b["board"]["lockedRows"]=False
        self.assertIn("BOARD_LOCK",invariants(b,b))

if __name__=="__main__":
    unittest.main()
