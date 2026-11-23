"""Contract tests for native speed lab (no compiler / Node / OS jobs needed)."""
import pathlib
import unittest

import speed_lab_native as lab


class SpeedLabTests(unittest.TestCase):
    def test_output_parity_ignores_timing_but_not_results(self):
        a = {
            "exit": 2, "save_sha256": "aaa",
            "result": {"strictValid": False, "sig": "x",
                       "strictFailures": ["NONVERTICAL_2"],
                       "quality": 0, "wires": 12, "cuts": 40},
            "timing": {"annealMs": 1000, "totalMs": 1100},
        }
        b = {
            **a, "result": dict(a["result"]),
            "timing": {"annealMs": 500, "totalMs": 610},
        }
        self.assertEqual(lab.exact_verdict(a, b), "")
        b["result"]["strictFailures"] = ["CROSSINGS_1"]
        self.assertEqual(lab.exact_verdict(a, b), "cli_json_fields")
        b["result"] = dict(a["result"])
        b["save_sha256"] = "bbb"
        self.assertEqual(lab.exact_verdict(a, b), "saved_json_sha256")
        b["save_sha256"] = "aaa"
        b["exit"] = 0
        self.assertEqual(lab.exact_verdict(a, b), "exit_code")

    def test_compiler_variants_keep_o3_reference(self):
        self.assertIn("o3", lab.DEFAULT_VARIANTS)
        self.assertIn("o3", lab.ROUTER_VARIANTS)
        self.assertIn("-O3", lab.compile_flags("o3"))
        self.assertTrue(any("FAST_GRID_CLEAR" in s for s in lab.compile_flags("grid")))
        self.assertTrue(any("FAST_IDENTICAL_GENOME" in s for s in lab.compile_flags("identical")))
        self.assertNotIn("grid", lab.ROUTER_VARIANTS)
        self.assertNotIn("identical", lab.ROUTER_VARIANTS)
        self.assertNotIn("-ffast-math", " ".join(
            " ".join(lab.compile_flags(v)) for v in lab.DEFAULT_VARIANTS))

    def test_run_counts_with_bookends(self):
        self.assertEqual(lab.estimate_run_count(["o3", "grid"], ["AUDIO", "MOTO"],
                                                 ["loose"], 3, 2), 48)

    def test_speedup_formula(self):
        self.assertEqual(lab.format_pct(120, 100), 20.0)
        self.assertEqual(lab.format_pct(100, 120), -16.67)
        self.assertIsNone(lab.format_pct(0, 100))

    def test_parser_timing_not_reported_as_outcome(self):
        raw = 'noise\n{"seed":1,"ms":100}\n{"seed":1,"ms":200}\n'
        self.assertEqual(lab.parse_json_line(raw), {"seed": 1, "ms": 200})
        self.assertEqual(lab.parse_json_line("timing {\"annealMs\":31}\n",
                                             "timing "), {"annealMs": 31})

    def test_output_never_points_into_source(self):
        for unsafe in (lab.ROOT, lab.FRONTEND,
                       lab.ROOT / "test-fixtures" / "masters" / "moto"):
            with self.assertRaises(ValueError):
                lab.safe_dir(unsafe)
        self.assertEqual(lab.safe_dir(pathlib.Path("/tmp/v5-lab-safe")),
                         pathlib.Path("/tmp/v5-lab-safe").resolve())


if __name__ == "__main__":
    unittest.main()
