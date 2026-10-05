"""Headless benchmark: python -m simulation.benchmark [counts...]
Reports per-tick cost against the 50 ms budget of a 20 Hz simulation tick."""
from __future__ import annotations
import resource
import sys
import time
from .ecosystem.world import World


def run(n: int, ticks: int = 100):
    w = World(width=1600 * max(1, n // 400), seed=1)          # keep density roughly constant
    for i in range(n):
        w.add_creature("neon_tetra" if i % 10 < 7 else "blue_tang" if i % 10 < 9 else "oscar")
    for _ in range(max(3, n // 20)):
        w.feed(w.rng.uniform(100, w.width - 100), 3)
    w.step(40)                                                # warm-up
    t = time.perf_counter()
    w.step(ticks)
    ms = (time.perf_counter() - t) * 1000 / ticks
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    return ms, w.stats["decisions_per_sec"], rss


if __name__ == "__main__":
    counts = [int(a) for a in sys.argv[1:]] or [100, 500, 1000]
    print(f"{'creatures':>10} {'ms/tick':>9} {'budget@20Hz':>12} {'AI decisions/s':>15} {'RSS MB':>8}")
    for n in counts:
        ms, dec, rss = run(n)
        print(f"{n:>10} {ms:>9.2f} {ms / 50 * 100:>11.0f}% {dec:>15} {rss:>8.0f}")
