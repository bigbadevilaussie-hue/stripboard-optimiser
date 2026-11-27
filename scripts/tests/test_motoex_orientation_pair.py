"""Static generation and saved-rotation contract; no native solver execution."""
import unittest
from build_motoex_orientation_pair import SOURCE, MASKS, patched, saved_errors

class OrientationPairTests(unittest.TestCase):
    def test_patch_anchors(self):
        original = SOURCE.read_text()
        changed = patched(original)
        self.assertIn("gRot[daveGps] = 1;",changed)
        self.assertIn("if (!daveAllowed(k,gRot[k])) return 0;",changed)
        self.assertIn("DAVE_PAIR_READY",changed)
        with self.assertRaises(ValueError):
            patched(changed)

    def test_saved_masks(self):
        saved = {"components":[{"id":i,"rotation":angles[0],"boardPos":{"row":0,"col":0}}
                               for i,angles in MASKS.items()]}
        self.assertEqual(saved_errors(saved),[])
        saved["components"][0]["rotation"]=0
        self.assertEqual(len(saved_errors(saved)),1)
        saved["components"][1]["rotation"]=90
        self.assertEqual(len(saved_errors(saved)),2)
        self.assertEqual(len(saved_errors({"components":[]})),2)

if __name__=="__main__":
    unittest.main()
