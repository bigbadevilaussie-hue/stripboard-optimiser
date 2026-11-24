"""Stack-only gating, original rejection preservation, audit-only contract."""
import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("requalify_motoex", ROOT / "requalify_motoex_winner_ladder.py")
module=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class RequalificationTests(unittest.TestCase):
    def test_only_allowed_stacks_can_requalify(self):
        row={"strictFailures":["SOLVER_ISSUES"],
             "diagnostics":{"issues":["6 wires still run on top of another wire"]}}
        self.assertEqual(module.stack_only_reason(row),6)
        row["diagnostics"]["issues"].append("1 strip conflict remains")
        self.assertIsNone(module.stack_only_reason(row))
        row["diagnostics"]["issues"]= ["5 wires still run on top of another wire"]
        row["strictFailures"].append("GEOMETRY_1")
        self.assertIsNone(module.stack_only_reason(row))
        row["strictFailures"]=["SOLVER_ISSUES"]
        row["diagnostics"]["issues"]= ["5 wires could not be made straight and crossing-free"]
        self.assertIsNone(module.stack_only_reason(row))

    def test_never_reclassify_arbitrary_solver_issue(self):
        for issue in ("unplaced component", "3 wire violations remain after fixed-board polish",
                      "UNSOLVED: NO_PHYSICAL_FINISH", "5 wire overlap unexplained"):
            with self.subTest(issue=issue):
                self.assertIsNone(module.stack_only_reason({
                    "strictFailures":["SOLVER_ISSUES"],"diagnostics":{"issues":[issue]}}))

if __name__=="__main__":
    unittest.main()
