"""Pure config, scheduling and ranking regression tests; runs NO annealer."""
import json
import unittest
from types import SimpleNamespace

import run_motoex_native_sweep as sweep
from run_motoex_native_edge_slide import contract


class NativeSweepTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(contract.MASTER.read_bytes())
        cls.usb, cls.definition, _ = contract.usb_source(cls.source)

    def settings(self, **changes):
        base = {"slide": False, "column": None, "columns": "all"}
        base.update(changes)
        return SimpleNamespace(**base)

    def test_fixed_default_is_one_original_anchor(self):
        columns = sweep.select_usb_columns(self.settings(), self.usb, self.definition)
        self.assertEqual(columns, [47])
        schedule = sweep.seed_schedule(1, 200, columns)
        self.assertEqual(len(schedule), 200)
        self.assertEqual(len(set(s for s, _ in schedule)), 200)
        self.assertTrue(all(col == 47 for _, col in schedule))
        self.assertEqual(schedule[0], (1, 47))
        self.assertEqual(schedule[-1], (200, 47))
        fixed = sweep.prepare_trial(self.source, True, False, 47)
        usb = next(c for c in fixed["components"] if c["label"] == "USB")
        self.assertFalse(usb["slide"])
        self.assertTrue(usb["edge"] and usb["locked"])
        self.assertEqual(usb["boardPos"], {"row": 13, "col": 47})
        self.assertEqual((fixed["board"]["rows"], fixed["board"]["cols"]), (24, 56))

    def test_slide_requires_explicit_opt_in(self):
        with self.assertRaisesRegex(ValueError, "slide yes"):
            sweep.select_usb_columns(
                self.settings(columns="25,41"), self.usb, self.definition)
        with self.assertRaisesRegex(ValueError, "fixed-only"):
            sweep.select_usb_columns(
                self.settings(slide=True, column=25), self.usb, self.definition)
        all_cols = sweep.select_usb_columns(
            self.settings(slide=True), self.usb, self.definition)
        self.assertEqual(len(all_cols), 51)
        self.assertEqual(set(all_cols), set(range(51)))
        # Even when enabled, Slide never multiplies the number of solves.
        schedule = sweep.seed_schedule(1, 200, all_cols)
        self.assertEqual(len(schedule), 200)
        self.assertGreater(len(set(col for _, col in schedule)), 1)

    def test_explicit_fixed_column_and_validation(self):
        self.assertEqual(sweep.select_usb_columns(
            self.settings(column=25), self.usb, self.definition), [25])
        for illegal in (-1, 51):
            with self.assertRaisesRegex(ValueError, "0..50"):
                sweep.select_usb_columns(
                    self.settings(column=illegal), self.usb, self.definition)
        selected = sweep.select_usb_columns(
            self.settings(slide=True, columns="25,41"), self.usb, self.definition)
        self.assertEqual(selected, [25, 41])
        self.assertEqual(sweep.seed_schedule(3, 4, selected),
                         [(3, 25), (4, 41), (5, 25), (6, 41)])

    def test_rank_prioritises_wires_then_cuts_and_dedup_only_top5(self):
        items = [
            {"wires": 14, "cuts": 30, "wireLength": 99, "price": 1, "seed": 1, "column": 47},
            {"wires": 14, "cuts": 28, "wireLength": 110, "price": 2, "seed": 2, "column": 47},
            {"wires": 13, "cuts": 42, "wireLength": 140, "price": 3, "seed": 3, "column": 47},
        ]
        self.assertEqual([x["seed"] for x in sorted(items, key=lambda x: sweep.key_of(x, "wires"))],
                         [3, 2, 1])
        self.assertEqual([x["seed"] for x in sorted(items, key=lambda x: sweep.key_of(x, "cuts"))],
                         [2, 1, 3])

    def test_timing_and_missing_timing(self):
        sample = 'progress 1\ntiming {"solveMs":12.5,"totalMs":16.2,"cpuMs":15,"rssMb":42}\n'
        self.assertEqual(sweep.timing_from_stderr(sample)["solveMs"], 12.5)
        self.assertEqual(sweep.timing_from_stderr("no timing available"), {})
        self.assertEqual(sweep.stats_of([3, 5, 10])["median"], 5)


if __name__ == "__main__":
    unittest.main()
