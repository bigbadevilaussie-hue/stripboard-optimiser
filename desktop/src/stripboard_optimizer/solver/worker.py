"""Background worker for running isolated v5 solver seeds."""

import os
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

from stripboard_optimizer.solver.solver_adapter import solve_one, is_valid, rank_key


PLANS = {
    "full_auto": [(8, 1.0)],
    "2pass": [(12, 0.3), (3, 3.0)],
    "manual": [(4, 1.0)],
}


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
    ):
        super().__init__(daemon=True)
        self.project_json = str(project_json)
        self.mode = mode
        self.q = q
        self.parallel = parallel or max(1, min(4, (os.cpu_count() or 2) - 1))
        self.native = native
        self.drilled = drilled
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

    def _one(self, seed, effort, stage, work):
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
                on_log=lambda message: self.q.put(("log", message)),
                on_progress=lambda current_seed, fraction: self.q.put(
                    ("progress", current_seed, fraction)
                ),
                register_process=self._register_process,
                unregister_process=self._unregister_process,
            )
            ok = is_valid(summary)
            self.q.put(
                ("candidate", stage, seed, effort, summary, str(path), ok)
            )
            return (summary, str(path), seed) if ok else None
        except Exception as exc:
            if not self._cancel_event.is_set():
                self.q.put(("log", f"[ERROR] seed {seed}: {exc}"))
            return None

    def run(self):
        best = None
        work = tempfile.mkdtemp(prefix="sbsolve_")
        try:
            plan = PLANS.get(self.mode, PLANS["full_auto"])
            seeds = list(range(plan[0][0]))
            good = []

            for stage, (count, effort) in enumerate(plan, 1):
                if self._cancel_event.is_set():
                    break

                self.q.put(
                    (
                        "log",
                        f"[SOLVE] Stage {stage}: {len(seeds)} seeds at effort {effort}",
                    )
                )
                with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                    results = executor.map(
                        lambda seed: self._one(seed, effort, stage, work),
                        seeds,
                    )
                    stage_good = [result for result in results if result]

                good.extend(stage_good)
                if stage < len(plan):
                    next_count = plan[stage][0]
                    seeds = [
                        result[2]
                        for result in sorted(
                            stage_good, key=lambda result: rank_key(result[0])
                        )[:next_count]
                    ]
                    if not seeds:
                        break

            if good and not self._cancel_event.is_set():
                best = min(good, key=lambda result: rank_key(result[0]))
        except Exception as exc:
            self.q.put(("log", f"[SOLVE] Worker failed: {exc}"))
        finally:
            self.cancelled = self._cancel_event.is_set()
            self.q.put(("done", best, self.cancelled))
