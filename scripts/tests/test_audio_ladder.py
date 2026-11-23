"""v1.63 native audio ladder: isolated unit tests, no GUI/native binary needed."""
import unittest

import ladder_native_audio as ladder


class AudioLadderTests(unittest.TestCase):
    def test_budgets_are_5k_to_50k(self):
        self.assertEqual(ladder.BUDGETS, tuple(range(5000, 50001, 5000)))
        self.assertEqual(len(ladder.BUDGETS), 10)

    def test_strict_and_historical_are_distinct(self):
        rows = [
            {
                "budget": 5000, "seed": 1, "failed": 0, "strictValid": False,
                "historicalClean": True, "wires": 20, "cuts": 40,
                "solveMs": 500, "annealMs": 390, "routeMs": 30,
                "price": 200, "sig": "aaa",
            },
            {
                "budget": 5000, "seed": 2, "failed": 0, "strictValid": True,
                "historicalClean": True, "wires": 19, "cuts": 39,
                "solveMs": 520, "annealMs": 400, "routeMs": 40,
                "price": 180, "sig": "bbb",
            }
        ]
        summary = ladder.summarize(rows, [5000], [1, 2])
        self.assertEqual(summary[0]["strictClean"], 1)
        self.assertEqual(summary[0]["historicalClean"], 2)
        self.assertEqual(summary[0]["bestStrictSeed"], 2)
        self.assertEqual(summary[0]["bestStrictWires"], 19)

    def test_missing_seed_fails_rung(self):
        with self.assertRaises(RuntimeError):
            ladder.summarize([{"budget": 5000, "seed": 1}], [5000], [1, 2])

    def test_historical_and_strict_can_be_zero(self):
        rows = [{"budget": 5000, "seed": 1, "failed": 0,
                 "strictValid": False, "historicalClean": False,
                 "solveMs": 100}]
        summary = ladder.summarize(rows, [5000], [1])
        self.assertEqual(summary[0]["strictClean"], 0)
        self.assertEqual(summary[0]["bestStrictSeed"], "")


if __name__ == "__main__":
    unittest.main()
