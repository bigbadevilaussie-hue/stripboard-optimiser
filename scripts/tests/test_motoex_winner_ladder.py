"""Fast, synthetic winner-ladder tests; do not run the native solver."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "run_motoex_winner_ladder.py"
SPEC = importlib.util.spec_from_file_location("motoex_winner_ladder", SOURCE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class WinnerLadderTests(unittest.TestCase):
    def test_complete_5k_ladder(self):
        self.assertEqual(len(module.MOVES), 43)
        self.assertEqual(module.MOVES[:2], (5000, 10000))
        self.assertEqual(module.MOVES[39], 200000)
        self.assertEqual(module.MOVES[-3:], (300000, 400000, 500000))
        self.assertEqual(sum(module.MOVES), 5_300_000)

    def test_bad_schedules(self):
        for schedule in ("", "0", "5000,5000", "10000,5000", "x"):
            with self.subTest(schedule=schedule), self.assertRaises(Exception):
                module.parse_moves(schedule)

    def test_ranking_only_strict_and_unique(self):
        def row(w, c, key, good=True, moves=5000):
            return dict(wires=w, cuts=c, wireLength=100, price=0,
                        seed=37, column=23, moves=moves,
                        layoutSig=key, strictPass=good)
        rows = [row(44,60,"baseline"),row(43,99,"a"),row(40,10,"rejected",False),
                row(43,99,"a",True,10000),row(43,60,"b")]
        picked = module.rank_candidates(rows)
        self.assertEqual([(r["wires"],r["cuts"]) for r in picked],
                         [(43,60),(43,99),(44,60)])

    def test_baseline_contract(self):
        valid = {"board":{"rows":24,"cols":56,"wires":[{}]*44,"cuts":[{}]*60},
                 "components":[{"label":"USB","boardPos":{"row":13,"col":23}}]}
        module.validate_baseline(valid)
        valid["components"][0]["boardPos"]["col"]=24
        with self.assertRaises(ValueError):
            module.validate_baseline(valid)


if __name__ == "__main__":
    unittest.main()
