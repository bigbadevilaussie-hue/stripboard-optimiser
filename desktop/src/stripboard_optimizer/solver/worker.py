APP_VERSION = "v1.49"
"""Background worker for running isolated v5 solver seeds."""

import json
import os
import random
import shutil
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from stripboard_optimizer.solver.solver_adapter import solve_one, is_valid, rank_key


PLANS = {
    "full_auto": [(8, 1.0)],
    "2pass": [(1000, 0.1)],
    "manual": [(4, 1.0)],
}

PASS1_MOVES = 25_000
MAX_FINALISTS = 10000  # effectively unlimited


def _layout_signature(path):
    """Return a stable signature for a board arrangement, ignoring run metadata."""
    saved = json.loads(Path(path).read_text(encoding="utf-8"))
    board = saved.get("board", {})
    components = []
    for component in saved.get("components", []):
        if component.get("boardExcluded"):
            continue
        components.append((
            str(component.get("id", "")),
            component.get("boardPos"),
            component.get("rotation", 0),
        ))
    components.sort(key=lambda item: item[0])
    return json.dumps(
        {"rows": board.get("rows", saved.get("rows")),
         "cols": board.get("cols", saved.get("cols")),
         "components": components},
        sort_keys=True, separators=(",", ":"),
    )


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
        manual_seed_base=0, manual_effort=None, tournament_candidates=2000,
        tournament_finalists=10000, output_dir=None,
    ):
        super().__init__(daemon=True)
        self.project_json = str(project_json)
        self.mode = mode
        self.q = q
        self.parallel = parallel or max(1, min(4, (os.cpu_count() or 2) - 1))
        # Fixed benchmark configuration: native solver, knife cuts, stacking allowed.
        self.native = True
        self.drilled = drilled
        self.no_wire_stacking = False
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
        label = contestant_name or "Solver"
        try:
            summary, path = solve_one(
                self.project_json, seed, work,
                effort=effort,
                moves=moves, native=self.native, drilled=self.drilled,
                no_wire_stacking=self.no_wire_stacking,
                routing_preference=self.routing_preference,
                on_progress=lambda current_seed, fraction: self.q.put(
                    ("progress", current_seed, fraction)
                ),
                register_process=self._register_process,
                unregister_process=self._unregister_process,
            )
            ok = (summary.get("quality") == 0 and summary.get("offAxis", 0) <= 2)
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
            price = summary.get("price", summary.get("rate", "?"))
            try:
                price_text = f"${float(price):,.2f}"
            except (TypeError, ValueError):
                price_text = str(price)
            conflicts = summary.get("conflicts", "?")
            incomplete = summary.get("incomplete", "?")
            geo = summary.get("geo", "?")
            issues = summary.get("issues") or []
            issue_count = len(issues) if isinstance(issues, (list, tuple)) else "?"
            phase = (
                "🏁 P1"
                if stage == 1 else f"⚔️ P2·R{stage - 1:02d}"
            )
            status = "✅" if ok else "❌"
            line = (
                f"{phase} {label} #{seed:04d} {status} · "
                f"📐{summary.get('rows', '?')}×{summary.get('cols', '?')} · "
                f"🔌{summary.get('wires', '?')} · ✂️{summary.get('cuts', '?')} · "
                f"🎯Q{summary.get('quality', '?')} · ↘{summary.get('offAxis', '?')} · "
                f"⏱{elapsed}ms · 💰{price_text}"
            )
            if not ok:
                reasons = []
                if summary.get("quality") is not None:
                    reasons.append(f"Q={summary.get('quality')}")
                reasons.extend((f"CONFLICTS={conflicts}", f"INCOMPLETE={incomplete}",
                                f"GEO={geo}", f"ISSUES={issue_count}"))
                if issues and isinstance(issues, (list, tuple)):
                    reasons.append("DETAILS=" + "; ".join(str(issue) for issue in issues[:3]))
                line += " | " + " ".join(reasons)
            # Pass 1 reports valid qualifiers. Pass 2 reports only each round winner.
            if stage == 1 and ok:
                self.q.put(("log", line))
            self.q.put(("candidate", stage, seed, effort, summary, str(path), ok, contestant_name))
            return (summary, str(path), seed, contestant_name, ok)
        except Exception as exc:
            if self.mode == "2pass" and self._cancel_event.is_set():
                return None
            if self.mode != "2pass":
                self.q.put(("log", f"[{label}] ❌ ERROR: {exc}"))
            return (None, None, seed, contestant_name, False)

    def _run_two_pass(self, work):
        candidates = self.tournament_candidates
        finalist_count = min(MAX_FINALISTS, max(1, self.tournament_finalists))
        seeds = list(range(1, candidates + 1))
        names = CONTESTANT_NAMES[:]
        random.SystemRandom().shuffle(names)
        contestant_names = {seed: names[(seed - 1) % len(names)] for seed in seeds}

        self.q.put(("log", f"[SOLVER] Native=ON | drilled cuts=ON | wire stacking=ALLOWED | routing priority={self.routing_preference}"))
        self.q.put(("log", f"🏁 PASS 1: {candidates} seeds × {PASS1_MOVES:,} moves at effort 0.1"))
        try:
            _jd = json.loads(Path(self.project_json).read_text(encoding="utf-8"))
            _b = _jd.get("board", {})
            _er = _b.get("rows")
            _ec = _b.get("cols")
            _lk = bool(_b.get("lockedRows") or _b.get("lockedCols"))
        except Exception:
            _er = _ec = None
            _lk = False
        # Collect in completion order. executor.map() yields in seed order, so
        # one slow early seed can hide hundreds of later completed seeds from the GUI.
        results = [None] * candidates
        completed = 0
        valid_count = 0
        duplicate_count = 0
        seen_layouts = {}
        unique_valid = []
        with ThreadPoolExecutor(max_workers=self.parallel) as executor:
            futures = {
                executor.submit(
                    self._one, seed, 0.1, 1, work, contestant_names[seed],
                    moves=PASS1_MOVES,
                ): seed
                for seed in seeds
            }
            for future in as_completed(futures):
                seed = futures[future]
                result = future.result()
                results[seed - 1] = result
                if result is not None:
                    completed += 1
                    if (result[0] is not None
                            and result[0].get("quality") == 0
                            and result[0].get("offAxis", 0) <= 2
                            and (not _lk or (result[0].get("rows") == _er and result[0].get("cols") == _ec))):
                        try:
                            signature = _layout_signature(result[1])
                        except Exception as exc:
                            self.q.put(("log", f"[LAYOUT CHECK] Seed {seed:04d}: could not fingerprint board: {exc}"))
                            signature = f"unreadable-seed-{seed}"
                        original_seed = seen_layouts.get(signature)
                        if original_seed is None:
                            seen_layouts[signature] = seed
                            unique_valid.append(result)
                            valid_count += 1
                        else:
                            duplicate_count += 1
                            self.q.put(("log", f"🔁 DUPLICATE: {result[3]} (seed {seed:04d}) matches {contestant_names[original_seed]} (seed {original_seed:04d}); excluded from finalist ranking"))
        valid = unique_valid
        ranked = sorted(valid, key=lambda result: rank_key(result[0], self.routing_preference))
        if self._cancel_event.is_set():
            self.q.put(("log", f"⏹ PASS 1 INTERRUPTED: {completed}/{candidates} completed, {len(valid)} valid"))
            return None
        self.q.put(("log", f"🏁 PASS 1 COMPLETE: {completed}/{candidates} completed, {len(valid)} unique valid, {duplicate_count} duplicates"))
        if not ranked:
            return None

        finalists = ranked[:min(finalist_count, len(ranked))]
        finalist_seeds = [item[2] for item in finalists]
        self.q.put(("log", "➡️ PASS 1 FINALISTS: " + ", ".join(
            f"{contestant_names[s]} (seed {s})" for s in finalist_seeds
        )))
        # Match the CLI tournament: every move-budget run starts from the original
        # input JSON with the same seed; it does not continue from the prior JSON.
        best_by_seed = {}
        budgets = [25000]
        for round_number, moves in enumerate(budgets, 1):
            if self._cancel_event.is_set():
                break
            self.q.put(("log", f"⚔️ PASS 2: Auditing {len(finalist_seeds)} qualifiers at {moves:,} moves"))
            with ThreadPoolExecutor(max_workers=self.parallel) as executor:
                round_results = list(executor.map(
                    lambda seed: self._one(
                        seed, None, round_number + 1, work,
                        contestant_names[seed], moves=moves,
                    ),
                    finalist_seeds,
                ))
            if self._cancel_event.is_set():
                self.q.put(("log", f"⏹ PASS 2 — INTERRUPTED"))
                break
            def _p2v(i):
                if not i or i[0] is None: return False
                s = i[0]
                if s.get("quality") != 0: return False
                if s.get("offAxis", 0) != 0: return False
                if _lk:
                    if s.get("rows") != _er or s.get("cols") != _ec: return False
                return True
            
            good = [item for item in round_results if _p2v(item)]
            for item in good:
                best_by_seed[item[2]] = item

        if self._cancel_event.is_set() or not best_by_seed:
            return None

        final_ranked = sorted(
            best_by_seed.values(),
            key=lambda item: rank_key(item[0], self.routing_preference),
        )[:10]
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
        self.q.put(("log", f"🏆 OVERALL WINNER: {winner[3]} (seed {winner[2]:04d}) · "
                           f"{winner[0].get('rows')}×{winner[0].get('cols')} · "
                           f"{winner[0].get('wires')}W / {winner[0].get('cuts')}C · "
                           f"${float(winner[0].get('price', winner[0].get('rate', 0))):,.2f} · VALID"))
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
