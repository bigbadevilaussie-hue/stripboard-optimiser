"""Bounded 1/2/3/4-process scaling probe with routing-like synthetic workloads.

No Route-Mate project files are read or written. Standard-library Python only.
"""
from __future__ import annotations

import argparse
import heapq
import os
import platform
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from time import perf_counter

TASKS = 24  # divisible by 1, 2, 3, and 4: identical work across worker counts
MASK = (1 << 32) - 1


def geometry_work(seed: int, repeats: int) -> int:
    """Dense jumper/footprint intersection checks with bounding-box rejection."""
    answer = 0
    for rep in range(repeats):
        state = ((seed + 1) * 1664525 + rep) & MASK
        for _line in range(100):
            state = (state * 1664525 + 1013904223) & MASK
            x1, y1 = state % 56, (state >> 9) % 24
            state = (state * 1664525 + 1013904223) & MASK
            x2, y2 = state % 56, (state >> 9) % 24
            low_x, high_x = min(x1, x2), max(x1, x2)
            low_y, high_y = min(y1, y2), max(y1, y2)
            dx, dy = x2 - x1, y2 - y1
            for cell in range(90):
                cx = (cell * 17 + seed * 11) % 56
                cy = (cell * 7 + rep * 3) % 24
                if cx + 1 < low_x or cx - 1 > high_x or cy + 1 < low_y or cy - 1 > high_y:
                    continue
                if dx == 0 and abs(cx - x1) > 1:
                    continue
                if dy == 0 and abs(cy - y1) > 1:
                    continue
                cross = abs(dx * (cy - y1) - dy * (cx - x1))
                if cross <= abs(dx) + abs(dy):
                    answer += 1
    return answer


def path_work(seed: int, repeats: int) -> int:
    """Repeated shortest-path graph searches with obstacles and heap updates."""
    rows, cols = 24, 56
    result = 0
    for rep in range(repeats):
        start = (seed * 71 + rep * 19) % (rows * cols)
        target = (seed * 97 + rep * 151 + 503) % (rows * cols)
        queue = [(0, start)]
        dist = {start: 0}
        expanded = 0
        while queue and expanded < 800:
            cost, node = heapq.heappop(queue)
            if cost != dist[node]:
                continue
            if node == target:
                break
            expanded += 1
            r, c = divmod(node, cols)
            for rr, cc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                if not (0 <= rr < rows and 0 <= cc < cols):
                    continue
                if (rr * 13 + cc * 7 + seed) % 29 == 0:
                    continue
                neighbour = rr * cols + cc
                next_cost = cost + 1 + ((rr + cc + seed) % 4 == 0)
                if next_cost < dist.get(neighbour, 1 << 30):
                    dist[neighbour] = next_cost
                    heapq.heappush(queue, (next_cost, neighbour))
        result += expanded + dist.get(target, 0)
    return result


def mixed_work(seed: int, repeats: int) -> int:
    """Geometry checks plus graph searches, representing a mixed route attempt."""
    return geometry_work(seed, repeats) ^ path_work(seed, repeats)


WORK = {"geometry": geometry_work, "path": path_work, "mixed": mixed_work}


def task(payload: tuple[str, int, int]) -> int:
    name, seed, repeats = payload
    return WORK[name](seed, repeats)


def calibrated_repeats(name: str, seconds: float) -> int:
    started = perf_counter()
    task((name, 0, 1))
    per = max(perf_counter() - started, 0.00001)
    return max(1, min(2500, round(seconds / (TASKS * per))))



def probe_worker_scaling(seconds: float = 1.0) -> dict:
    """Short startup probe. Identical synthetic mixed work for 1..4 workers.

    Includes process startup overhead. This only *recommends* concurrency;
    it does not execute Route-Mate solves or predict their exact duration.
    """
    count = os.cpu_count() or 1
    workers_to_try = [w for w in (1, 2, 3, 4) if w <= count]
    repeats = calibrated_repeats("mixed", seconds)
    workload = [("mixed", seed, repeats) for seed in range(TASKS)]
    timings = {}
    checksums = set()
    for workers in workers_to_try:
        started = perf_counter()
        with ProcessPoolExecutor(
            max_workers=workers, mp_context=get_context("spawn")
        ) as pool:
            results = list(pool.map(task, workload, chunksize=1))
        timings[workers] = perf_counter() - started
        checksums.add(sum(results) & MASK)
    if len(checksums) != 1:
        raise RuntimeError("inconsistent worker-probe results")
    return {
        "recommended_workers": min(timings, key=timings.get),
        "timings": timings,
        "logical_cpus": count,
        "pattern": "synthetic mixed routing",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Longer routing-like CPU scaling probe: 1, 2, 3, 4 workers"
    )
    parser.add_argument(
        "--seconds", type=float, default=8.0,
        help="target single-process compute seconds per pattern (default 8, range 1..20)",
    )
    args = parser.parse_args()
    if not 1 <= args.seconds <= 20:
        parser.error("--seconds must be between 1 and 20")
    count = os.cpu_count() or 1
    worker_counts = [w for w in (1, 2, 3, 4) if w <= count]
    print(f"[MAC] {platform.platform()} | Python {platform.python_version()} | logical CPUs={count}", flush=True)
    print("[PROBE] 24 identical tasks per pattern, comparing 1/2/3/4 processes.", flush=True)
    overall = {}
    for name in WORK:
        repeats = calibrated_repeats(name, args.seconds)
        workload = [(name, seed, repeats) for seed in range(TASKS)]
        print(f"\n[{name.upper()}] tasks={TASKS} repeats/task={repeats}", flush=True)
        times = {}
        checksums = set()
        for workers in worker_counts:
            started = perf_counter()
            with ProcessPoolExecutor(
                max_workers=workers, mp_context=get_context("spawn")
            ) as pool:
                results = list(pool.map(task, workload, chunksize=1))
            elapsed = perf_counter() - started
            checksum = sum(results) & MASK
            checksums.add(checksum)
            times[workers] = elapsed
            print(
                f"  {workers} workers: {elapsed:7.3f}s  "
                f"speedup={times[1] / elapsed:.2f}x  checksum={checksum:08x}",
                flush=True,
            )
        print(f"  Consistent results: {'YES' if len(checksums) == 1 else 'NO'}", flush=True)
        overall[name] = times
    print("\n[SUMMARY] Best worker count for each pattern (including spawn overhead):", flush=True)
    for name, times in overall.items():
        best = min(times, key=times.get)
        print(f"  {name:9s} best={best} workers ({times[best]:.3f}s)", flush=True)
    print("[NOTE] Synthetic patterns, not a benchmark of the real Route-Mate solver.", flush=True)


if __name__ == "__main__":
    main()
