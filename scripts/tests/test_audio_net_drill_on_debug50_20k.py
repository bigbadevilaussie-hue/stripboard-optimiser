import unittest
import json
from scripts import run_audio_net_drill_on_debug50_20k as d

class AudioNetDrillTests(unittest.TestCase):
    def test_fixture_matches_netlist(self):
        data=json.loads(d.SOURCE_JSON.read_text(encoding="utf8"))
        result=d.verify_netlist(data,d.SOURCE_NET.read_text(encoding="utf8"))
        self.assertEqual(result,{"nets":29,"assignedPins":85})
        self.assertFalse(any(c.get("locked") and c.get("boardPos") for c in data["components"]))
    def test_contract(self):
        self.assertEqual(d.MOVES,20000)
        self.assertEqual(d.SEEDS,tuple(range(1,51)))
        self.assertIn("audio_net",str(d.OUT))
    def test_mismatch_fails(self):
        with self.assertRaises(ValueError):
            d.verify_netlist({"nets":[],"components":[],"netAssignments":[]},"")

if __name__ == "__main__":
    unittest.main()
