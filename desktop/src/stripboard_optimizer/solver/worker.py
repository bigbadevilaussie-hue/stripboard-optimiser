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
        try:
            summary, path = solve_one(
                self.project_json,
                seed,
                work,
                effort=effort,
                native=self.native,
                drilled=self.drilled,
                no_wire_stacking=self.no_wire_stacking,
                routing_preference=self.routing_preference,
                on_log=lambda message: self.q.put(("log", message)),
                on_progress=lambda current_seed, fraction: self.q.put(
                    ("progress", current_seed, fraction)
                ),
                register_process=self._register_process,
                unregister_process=self._unregister_process,
            )
            ok = is_valid(summary)
            self.q.put(
                ("candidate", stage, seed, effort, summary, str(path), ok, contestant_name)
            )
            return (summary, str(path), seed, contestant_name) if ok else None
        except Exception as exc:
            if not self._cancel_event.is_set():
                label = contestant_name or f"seed {seed}"
                self.q.put(("log", f"[ERROR] {label}: {exc}"))
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

            final_stage_good = []
            for stage, (count, effort) in enumerate(plan, 1):
                if self._cancel_event.is_set():
                    break

                self.q.put(("log", f"🏁 Round {stage}: {len(seeds)} contestants"))
                with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                    results = executor.map(
                        lambda seed: self._one(
                            seed, effort, stage, work, contestant_names.get(seed)
                        ),
                        seeds,
                    )
                    stage_good = [result for result in results if result]

                ranked = sorted(
                    stage_good,
                    key=lambda result: rank_key(result[0]),
                )
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

                final_stage_good = ranked
                if stage < len(plan):
                    finalists = ranked[:plan[stage][0]]
                    seeds = [result[2] for result in finalists]
                    if not seeds:
                        break

            if final_stage_good and not self._cancel_event.is_set():
                best = min(
                    final_stage_good,
                    key=lambda result: rank_key(result[0], self.routing_preference),
                )
        except Exception as exc:
            self.q.put(("log", f"[SOLVE] Worker failed: {exc}"))
        finally:
            self.cancelled = self._cancel_event.is_set()
            self.q.put(("done", best, self.cancelled))
