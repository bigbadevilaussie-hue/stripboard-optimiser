"""Static generation and saved-rotation contract; no native solver execution."""
import unittest
from build_motoex_orientation_pair import SOURCE, MASKS, build, saved_errors

class OrientationPairTests(unittest.TestCase):
    def test_canonical_pair(self):
        source = SOURCE.read_text()
        self.assertIn("EXPORT(v5_setDavePair)", source)
        self.assertIn("if (daveGps >= 0) gRot[daveGps] = 1;", source)
        self.assertIn("if (!daveAllowed(k,gRot[k])) return 0;", source)
        with self.assertRaisesRegex(ValueError, "retired"):
            build(SOURCE)

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
