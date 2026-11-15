"""Background worker for running isolated v5 solver seeds."""

import json
import os
import random
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from stripboard_optimizer.solver.solver_adapter import solve_one, is_valid, rank_key


PLANS = {
    "full_auto": [(8, 1.0)],
    "2pass": [(2000, 25000)],
    "manual": [(4, 1.0)],
}

CONTESTANT_NAMES = [
    "Ada", "Ben", "Cleo", "Dan", "Eva", "Finn", "Gala", "Hank", "Iris", "Jack",
    "Kip", "Luna", "Max", "Nora", "Oto", "Pax", "Quinn", "Rex", "Sage", "Tess",
    "Uma", "Vance", "Wren", "Xander", "Yara", "Zoe", "Abe", "Bess", "Caleb",
    "Drew", "Elke", "Fritz", "Gideon", "Hazel", "Isla", "Jonas", "Kira", "Liam",
    "Milo", "Neve", "Onyx", "Piper", "Rico", "Selma", "Toby", "Vera", "Wyatt",
    "Zack", "Alma", "Brock", "Cora", "Dante", "Elsa", "Felix", "Gemma", "Hugo",
    "Ivy", "Jude", "Kofi", "Leo", "Maeve", "Nash", "Orla", "Phoebe", "Remi",
    "Soren", "Thea", "Val", "Winn", "Zion", "Ari", "Blaze", "Clem", "Delia",
    "Ember", "Fox", "Gage", "Hollis", "Ida", "Jinx", "Kobe", "Lane", "Mika",
    "Nico", "Opal", "Pike", "Reed", "Sloane", "Tate", "Veda", "West", "Zane",
    "Amber", "Brooke", "Chase", "Dawn", "Echo", "Finn II", "Grey", "Hope"
]


class SolveWorker(threading.Thread):
    """Run the desktop GUI's seed plan without touching Tkinter from this thread."""

    def __init__(
        self, project_json, mode, q, parallel=None, native=False, drilled=False,
        no_wire_stacking=False, routing_preference="wires", manual_seeds=None,
        manual_seed_base=0, manual_effort=None, tournament_candidates=200,
        tournament_finalists=5, output_dir=None,
    ):
        super().__init__(daemon=True)
        self.project_json = str(project_json)
        self.mode = mode
        self.q = q
        self.parallel = parallel or max(1, min(4, (os.cpu_count() or 2) - 1))
        self.native = native
        self.drilled = drilled
        self.no_wire_stacking = no_wire_stacking
        self.routing_preference = routing_preference
        self.manual_seeds = manual_seeds
        self.manual_seed_base = manual_seed_base
        self.manual_effort = manual_effort
        self.tournament_candidates = tournament_candidates
        self.tournament_finalists = tournament_finalists
        self.output_dir = Path(output_dir).expanduser().resolve() if output_dir else None
        self.cancelled = False
        self._cancel_event = threading.Event()
        self._procs = []
        self._procs_lock = threading.Lock()

    def cancel(self):
        self.cancelled = True
        self._cancel_event.set()
        with self._procs_lock:
            procs = list(self._procs)
        for proc in procs:
            try:
                if proc.poll() is None:
                    proc.terminate()
            except Exception:
                pass

    def _register_process(self, proc):
        with self._procs_lock:
            if self._cancel_event.is_set():
                try:
                    proc.terminate()
                except Exception:
                    pass
            self._procs.append(proc)

    def _unregister_process(self, proc):
        with self._procs_lock:
            try:
                self._procs.remove(proc)
            except ValueError:
                pass

    def _one(self, seed, effort, stage, work, contestant_name=None, moves=None):
        if self._cancel_event.is_set():
            return None
        label = f"Seed {seed:04d}"
        try:
            summary, path = solve_one(
                self.project_json, seed, work,
                effort=effort if moves is None else 1.0,
                moves=moves, native=self.native, drilled=self.drilled,
                no_wire_stacking=self.no_wire_stacking,
                routing_preference=self.routing_preference,
                on_progress=lambda current_seed, fraction: self.q.put(
                    ("progress", current_seed, fraction)
                ),
                register_process=self._register_process,
                unregister_process=self._unregister_process,
            )
            ok = is_valid(summary)
            try:
                saved = json.loads(Path(path).read_text(encoding="utf-8"))
                parts = sum(
                    1 for component in saved.get("components", [])
                    if component.get("boardPos") and not component.get("boardExcluded")
                )
            except Exception:
                parts = "?"
            diagonals = summary.get("offAxis", "?")
            elapsed = summary.get("ms", "?")
            line = (
                f"[{label}] {'✅' if ok else '❌'} "
                f"📐 Rows: {summary.get('rows', '?')} | Cols: {summary.get('cols', '?')} | "
                f"🧩 Parts: {parts} | ↗️ Diag: {diagonals} | "
                f"🔌 Wires: {summary.get('wires', '?')} | ✂️ Cuts: {summary.get('cuts', '?')} | "
                f"⏱️ Moves: {elapsed}ms"
            )
            if not ok:
                reasons = []
                if summary.get("quality") is not None:
                    reasons.append(f"Q:{summary.get('quality')}")
                for key in ("conflicts", "incomplete", "geo"):
                    if summary.get(key):
                        reasons.append(f"{key.upper()}:{summary.get(key)}")
                if summary.get("issues"):
                    reasons.append(f"ISSUES:{len(summary['issues'])}")
                line += " | FAIL: " + (", ".join(reasons) if reasons else "validation")
            if self.mode != "2pass":
                self.q.put(("log", line))
            self.q.put(("candidate", stage, seed, effort, summary, str(path), ok, contestant_name))
            return (summary, str(path), seed, contestant_name, ok)
        except Exception as exc:
            self.q.put(("log", f"[{label}] ❌ ERROR: {exc}"))
            return None

    def _run_two_pass(self, work):
        candidates = self.tournament_candidates
        finalist_count = self.tournament_finalists
        seeds = list(range(1, candidates + 1))
        names = CONTESTANT_NAMES[:]
        random.SystemRandom().shuffle(names)
        contestant_names = {seed: names[(seed - 1) % len(names)] for seed in seeds}

        self.q.put(("log", f"🏁 PASS 1: {candidates} seeds × 25,000 moves"))
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            results = list(executor.map(
                lambda seed: self._one(
                    seed, None, 1, work, contestant_names[seed], moves=25000
                ),
                seeds,
            ))
        valid = [result for result in results if result and result[4]]
        ranked = sorted(valid, key=lambda result: rank_key(result[0], self.routing_preference))
        self.q.put(("log", f"🏁 PASS 1 COMPLETE: {len(valid)}/{candidates} valid"))
        if not ranked or self._cancel_event.is_set():
            return None

        finalists = ranked[:finalist_count]
        finalist_seeds = [item[2] for item in finalists]
        self.q.put(("log", "➡️ PASS 1 FINALISTS: " + ", ".join(
            f"{contestant_names[s]} (seed {s})" for s in finalist_seeds
        )))
        # Match the CLI tournament: every move-budget run starts from the original
        # input JSON with the same seed; it does not continue from the prior JSON.
        best_by_seed = {item[2]: item for item in finalists}
        budgets = range(5000, 200001, 5000)
        for round_number, moves in enumerate(budgets, 1):
            if self._cancel_event.is_set():
                break
            self.q.put(("log", f"⚔️ PASS 2 ROUND {round_number}/40: {moves:,} moves"))
            with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                round_results = list(executor.map(
                    lambda seed: self._one(
                        seed, None, round_number + 1, work,
                        contestant_names[seed], moves=moves,
                    ),
                    finalist_seeds,
                ))
            good = [item for item in round_results if item and item[4]]
            for item in good:
                previous = best_by_seed.get(item[2])
                if previous is None or rank_key(item[0], self.routing_preference) < rank_key(previous[0], self.routing_preference):
                    best_by_seed[item[2]] = item
            current_ranked = sorted(
                good, key=lambda item: rank_key(item[0], self.routing_preference)
            )
            if current_ranked:
                round_winner = current_ranked[0]
                self.q.put((
                    "log",
                    f"🏁 PASS 2 ROUND {round_number}/40 — WINNER: "
                    f"{round_winner[3]} · {round_winner[0].get('wires', '?')}W / "
                    f"{round_winner[0].get('cuts', '?')}C"
                ))
            else:
                self.q.put(("log", f"🏁 PASS 2 ROUND {round_number}/40 — NO WINNER"))

        if self._cancel_event.is_set() or not best_by_seed:
            return None

        final_ranked = sorted(
            best_by_seed.values(),
            key=lambda item: rank_key(item[0], self.routing_preference),
        )[:finalist_count]
        if self.output_dir is None:
            raise RuntimeError("No persistent output directory was supplied for tournament results.")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        for old_json in self.output_dir.glob("*.json"):
            old_json.unlink()
        saved_finalists = []
        for rank, item in enumerate(final_ranked, 1):
            seed = item[2]
            destination = self.output_dir / f"finalist_{rank:02d}_seed_{seed:04d}.json"
            shutil.copy2(item[1], destination)
            saved_finalists.append((item[0], str(destination), seed, item[3]))
        self.q.put(("log", f"📁 FINALISTS SAVED: {len(saved_finalists)} JSON files in {self.output_dir}"))
        winner = saved_finalists[0]
        self.q.put(("log", f"🏆 WINNER: {winner[3]} · {winner[0].get('rows')}x{winner[0].get('cols')} · "
                           f"{winner[0].get('wires')}W / {winner[0].get('cuts')}C"))
        return winner

    def run(self):
        best = None
        work = Path(tempfile.mkdtemp(prefix="sbsolve_"))
        try:
            if self.mode == "2pass":
                best = self._run_two_pass(work)
            else:
                if self.mode == "manual":
                    count = self.manual_seeds or PLANS["manual"][0][0]
                    effort = self.manual_effort if self.manual_effort is not None else PLANS["manual"][0][1]
                    seeds = list(range(self.manual_seed_base, self.manual_seed_base + count))
                else:
                    count, effort = PLANS.get(self.mode, PLANS["full_auto"])[0]
                    seeds = list(range(count))
                with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                    results = list(executor.map(
                        lambda seed: self._one(seed, effort, 1, work), seeds
                    ))
                valid = [item for item in results if item and item[4]]
                if valid and not self._cancel_event.is_set():
                    winner = min(valid, key=lambda item: rank_key(item[0], self.routing_preference))
                    best = winner[:4]
        except Exception as exc:
            self.q.put(("log", f"[SOLVE ERROR] {exc}"))
        finally:
            self.cancelled = self._cancel_event.is_set()
            shutil.rmtree(work, ignore_errors=True)
            self.q.put(("done", best, self.cancelled))
