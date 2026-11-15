"""Background worker for running isolated v5 solver seeds."""

import os
import random
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

from stripboard_optimizer.solver.solver_adapter import solve_one, is_valid, rank_key


PLANS = {
    "full_auto": [(8, 1.0)],
    "2pass": [(100, 0.1), (5, 3.0)],  # GUI selections override these defaults.
    "manual": [(4, 1.0)],
}

CONTESTANT_NAMES = [
    "Ada",
    "Ben",
    "Cleo",
    "Dan",
    "Eva",
    "Finn",
    "Gala",
    "Hank",
    "Iris",
    "Jack",
    "Kip",
    "Luna",
    "Max",
    "Nora",
    "Oto",
    "Pax",
    "Quinn",
    "Rex",
    "Sage",
    "Tess",
    "Uma",
    "Vance",
    "Wren",
    "Xander",
    "Yara",
    "Zoe",
    "Abe",
    "Bess",
    "Caleb",
    "Drew",
    "Elke",
    "Fritz",
    "Gideon",
    "Hazel",
    "Isla",
    "Jonas",
    "Kira",
    "Liam",
    "Milo",
    "Neve",
    "Onyx",
    "Piper",
    "Rico",
    "Selma",
    "Toby",
    "Vera",
    "Wyatt",
    "Zack",
    "Alma",
    "Brock",
    "Cora",
    "Dante",
    "Elsa",
    "Felix",
    "Gemma",
    "Hugo",
    "Ivy",
    "Jude",
    "Kofi",
    "Leo",
    "Maeve",
    "Nash",
    "Orla",
    "Phoebe",
    "Remi",
    "Soren",
    "Thea",
    "Val",
    "Winn",
    "Zion",
    "Ari",
    "Blaze",
    "Clem",
    "Delia",
    "Ember",
    "Fox",
    "Gage",
    "Hollis",
    "Ida",
    "Jinx",
    "Kobe",
    "Lane",
    "Mika",
    "Nico",
    "Opal",
    "Pike",
    "Reed",
    "Sloane",
    "Tate",
    "Veda",
    "West",
    "Zane",
    "Amber",
    "Brooke",
    "Chase",
    "Dawn",
    "Echo",
    "Finn II",
    "Grey",
    "Hope"
]


class SolveWorker(threading.Thread):
    """Run the desktop GUI's seed plan without touching Tkinter from this thread."""

    def __init__(
        self,
        project_json,
        mode,
        q,
        parallel=None,
        native=False,
        drilled=False,
        no_wire_stacking=False,
        routing_preference="wires",
        manual_seeds=None,
        manual_seed_base=0,
        manual_effort=None,
        tournament_candidates=100,
        tournament_finalists=5,
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

    def _one(self, seed, effort, stage, work, contestant_name=None):
        if self._cancel_event.is_set():
            return None
        label = contestant_name or f"Seed {seed}"
        try:
            self.q.put(("log", f"[ROUND {stage}] START {label} | seed={seed} | effort={effort:g} | input=original project"))
            summary, path = solve_one(
                self.project_json,
                seed,
                work,
                effort=effort,
                native=self.native,
                drilled=self.drilled,
                no_wire_stacking=self.no_wire_stacking,
                routing_preference=self.routing_preference,
                on_log=(lambda message: self.q.put(("log", message))) if contestant_name is None else None,
                on_progress=lambda current_seed, fraction: self.q.put(
                    ("progress", current_seed, fraction)
                ),
                register_process=self._register_process,
                unregister_process=self._unregister_process,
            )
            ok = is_valid(summary)
            status = "VALID" if ok else "INVALID"
            self.q.put(("log", f"[ROUND {stage}] DONE {label} | {status} | runtime={summary.get('ms', '?')}ms | {summary.get('wires', '?')}W/{summary.get('cuts', '?')}C | conflicts={summary.get('conflicts', '?')} | incomplete={summary.get('incomplete', '?')} | geo={summary.get('geo', '?')} | issues={summary.get('issues', [])} | saved={path}"))
            self.q.put(
                ("candidate", stage, seed, effort, summary, str(path), ok, contestant_name)
            )
            return (summary, str(path), seed, contestant_name, ok)
        except Exception as exc:
            if not self._cancel_event.is_set():
                self.q.put(("log", f"[ROUND {stage}] ERROR {label} | seed={seed} | effort={effort:g} | {type(exc).__name__}: {exc}"))
            return None

    def run(self):
        best = None
        work = tempfile.mkdtemp(prefix="sbsolve_")
        try:
            if self.mode == "manual":
                count = self.manual_seeds or PLANS["manual"][0][0]
                effort = self.manual_effort if self.manual_effort is not None else PLANS["manual"][0][1]
                plan = [(count, effort)]
                seeds = list(range(self.manual_seed_base, self.manual_seed_base + count))
            elif self.mode == "2pass":
                plan = [(self.tournament_candidates, 0.1), (self.tournament_finalists, 3.0)]
                seeds = list(range(1, self.tournament_candidates + 1))
            else:
                plan = PLANS.get(self.mode, PLANS["full_auto"])
                seeds = list(range(plan[0][0]))

            contestant_names = {}
            if self.mode == "2pass":
                shuffled_names = CONTESTANT_NAMES[:]
                random.SystemRandom().shuffle(shuffled_names)
                contestant_names = dict(zip(seeds, shuffled_names))

            all_valid = []
            finalists = []
            for stage, (count, effort) in enumerate(plan, 1):
                if self._cancel_event.is_set():
                    break

                self.q.put(("log", f"========== ROUND {stage} START | contestants={len(seeds)} | effort={effort:g} =========="))
                if stage == 2:
                    self.q.put(("log", "[ROUND 2] IMPORTANT: this is currently a fresh solve from the original project using finalist seeds; it is not a continuation from the saved Round 1 layout."))

                with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                    results = list(executor.map(
                        lambda seed: self._one(
                            seed, effort, stage, work, contestant_names.get(seed)
                        ),
                        seeds,
                    ))

                completed = [result for result in results if result is not None]
                stage_good = [result for result in completed if result[4]]
                stage_invalid = len(completed) - len(stage_good)
                stage_errors = len(results) - len(completed)
                ranked = sorted(
                    stage_good,
                    key=lambda result: rank_key(result[0], self.routing_preference),
                )
                all_valid.extend(stage_good)

                valid_rate = (100.0 * len(stage_good) / len(seeds)) if seeds else 0.0
                self.q.put(("log", f"========== ROUND {stage} SUMMARY =========="))
                self.q.put(("log", f"[ROUND {stage}] contestants={len(seeds)} | completed={len(completed)} | valid={len(stage_good)} | invalid={stage_invalid} | errors={stage_errors} | valid_rate={valid_rate:.1f}%"))
                if ranked:
                    best_round = ranked[0]
                    worst_round = ranked[-1]
                    self.q.put(("log", f"[ROUND {stage}] BEST: {best_round[3]} | seed={best_round[2]} | {best_round[0].get('wires', '?')}W/{best_round[0].get('cuts', '?')}C"))
                    self.q.put(("log", f"[ROUND {stage}] WORST VALID: {worst_round[3]} | seed={worst_round[2]} | {worst_round[0].get('wires', '?')}W/{worst_round[0].get('cuts', '?')}C"))
                else:
                    self.q.put(("log", f"[ROUND {stage}] No valid boards in this round."))

                standings = [
                    {
                        "name": result[3] or f"Seed {result[2]}",
                        "seed": result[2],
                        "rank": position + 1,
                        "points": max(0, 100 - position),
                        "wires": result[0].get("wires", "?"),
                        "cuts": result[0].get("cuts", "?"),
                    }
                    for position, result in enumerate(ranked)
                ]
                if not self._cancel_event.is_set():
                    self.q.put(("round_results", stage, len(seeds), len(stage_good), standings))

                if stage == 1 and stage < len(plan):
                    finalists = ranked[:plan[stage][0]]
                    self.q.put(("log", f"[ROUND 1] Advancing {len(finalists)} finalists."))
                    for finalist in finalists:
                        self.q.put(("log", f"[FINALIST] {finalist[3]} | seed={finalist[2]} | {finalist[0].get('wires', '?')}W/{finalist[0].get('cuts', '?')}C | saved={finalist[1]}"))
                    seeds = [result[2] for result in finalists]
                    if not seeds:
                        self.q.put(("log", "[TOURNAMENT] No valid qualifiers; stopping before Round 2."))
                        break

            if all_valid and not self._cancel_event.is_set():
                best = min(
                    all_valid,
                    key=lambda result: rank_key(result[0], self.routing_preference),
                )
                self.q.put(("log", f"[TOURNAMENT] CHAMPION: {best[3]} | seed={best[2]} | {best[0].get('wires', '?')}W/{best[0].get('cuts', '?')}C"))
                if len(plan) > 1 and best in finalists and len(all_valid) > len(finalists):
                    self.q.put(("log", "[TOURNAMENT] Champion is a Round 1 finalist fallback; Round 2 did not produce a better valid board."))
            elif not self._cancel_event.is_set():
                self.q.put(("log", "[TOURNAMENT] No valid board found in any round."))
        except Exception as exc:
            self.q.put(("log", f"[SOLVE] Worker failed: {exc}"))
        finally:
            self.cancelled = self._cancel_event.is_set()
            self.q.put(("done", best, self.cancelled))
