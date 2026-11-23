"""Tests for v1.61 native CLI-only failure and budget analysis (no native solver)."""
import unittest

import native_failure_matrix as fm
import sweep_native_move_budget as sw


def case(repair="QUALITY,COLUMN_SHIFT", router="COLUMN_SHIFT,CROSSINGS",
         selected="router", project="MOTOMIX", config="DRILL_ON_STACK_OFF"):
    return {
        "project": project, "configuration": config, "seed": "897",
        "selected": selected,
        "repair_failed": repair,
        "router_failed": router,
        "repair_verified_compliant": not bool(repair),
        "router_verified_compliant": not bool(router),
        "eitherCompliant": not bool(repair) or not bool(router),
        "selectedCompliant": not bool(repair if selected == "repair" else router),
        "error": "",
    }


class FailureMatrixTests(unittest.TestCase):
    def test_closest_is_electrical_first(self):
        row = case("QUALITY", "COLUMN_SHIFT,CROSSINGS")
        rec = fm.classify_row(row)
        self.assertEqual(rec["closest"], "router")
        self.assertEqual(rec["minimumFailures"], 1)
        self.assertFalse(rec["eitherCompliant"])

    def test_intersection_of_failures(self):
        rec = fm.classify_row(case("STACKED,COLUMN_SHIFT", "CROSSINGS,COLUMN_SHIFT"))
        self.assertEqual(rec["_common"], {"COLUMN_SHIFT"})
        self.assertEqual(rec["commonCount"], 1)
        self.assertEqual(rec["minimumFailures"], 2)

    def test_valid_alternative_lost_is_detectable(self):
        rec = fm.classify_row(case("", "STACKED", selected="router"))
        self.assertTrue(rec["eitherCompliant"])
        self.assertFalse(rec["selectedCompliant"])
        self.assertEqual(rec["closest"], "repair")

    def test_bad_verdict_is_rejected(self):
        row = case()
        row["router_verified_compliant"] = True
        with self.assertRaises(ValueError):
            fm.classify_row(row)

    def test_absent_required_field_is_rejected(self):
        row = case()
        del row["repair_failed"]
        with self.assertRaises(ValueError):
            fm.classify_row(row)


class BudgetSweepTests(unittest.TestCase):
    def test_budget_parser(self):
        self.assertEqual(sw.parse_positive_ints("20000,100000,500000", "--budgets"),
                         (20000, 100000, 500000))
        for raw in ("0,20000", "20000,20000", "ten", ""):
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    sw.parse_positive_ints(raw, "--budgets")

    def test_flatten_candidate_fields(self):
        checks = {
            "compliant": False, "failReasons": ["STACKED"],
            "geometry": 0, "conflicts": 0, "incomplete": 0,
        }
        trace = {"selected": "router", "anyCompliant": False, "selectedCompliant": False,
                 "routePhases": {"repairSlantWires": 103.5},
                 "repair": None,
                 "router": {"quality": 0, "score": 200,
                            "scoreTerms": {"qualityCost": 0, "messCost": 0, "price": 200},
                            "verification": checks,
                            "stacked": 3}}
        record = {
            "project": "MOTOMIX", "configuration": "DRILL_ON_STACK_OFF", "seed": 897,
            "finishTrace": [trace], "result": {"strictValid": False, "sig": "abc",
                                               "moveSummary": {"attempted": 20000}},
            "baselineSig": "abc", "signatureMatch": True, "strictMatch": True,
            "timing": {"routeMs": 103.5}}
        row = sw.flatten(record, 20000)
        self.assertEqual(row["repair_failed"], "UNAVAILABLE")
        self.assertIs(row["repair_verified_compliant"], False)
        self.assertIs(row["router_verified_compliant"], False)
        self.assertEqual(row["phase_repairSlantWires_ms"], 103.5)
        self.assertEqual(fm.classify_row(row)["closest"], "router")

    def test_budget_summary_counts_either_and_minimum(self):
        row = case("STACKED", "")
        row.update({"budget": 500000, "annealMs": 100, "routeMs": 20})
        summaries = sw.summarize_budget([row], 500000)
        self.assertEqual(summaries[0]["selected_clean"], 1)
        self.assertEqual(summaries[0]["either_clean"], 1)
        self.assertEqual(summaries[0]["minimal_zero"], 1)


if __name__ == "__main__":
    unittest.main()
