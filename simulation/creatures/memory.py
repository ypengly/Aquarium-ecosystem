"""Spatial episodic memory with exponential decay, merging and capacity limits."""
from __future__ import annotations
from collections import deque

HALF_LIFE = {"FOOD_FOUND": 90.0, "PREDATOR_SEEN": 25.0, "SAFE_SPOT": 300.0,
             "ATTACKED": 120.0, "SCHOOL_SEEN": 40.0}
MERGE_RADIUS = {"PREDATOR_SEEN": 250.0}


class MemoryEntry:
    __slots__ = ("kind", "x", "y", "time", "strength")

    def __init__(self, kind, x, y, time, strength):
        self.kind, self.x, self.y, self.time, self.strength = kind, x, y, time, strength

    def now_strength(self, now: float) -> float:
        return self.strength * 0.5 ** ((now - self.time) / HALF_LIFE[self.kind])


class Memory:
    def __init__(self, capacity: int):
        self.capacity = max(3, capacity)
        self.entries: list = []
        self.events: deque = deque(maxlen=10)      # human-readable recent events

    def remember(self, kind, x, y, now, strength=1.0):
        r2 = MERGE_RADIUS.get(kind, 70.0) ** 2
        for e in self.entries:
            if e.kind == kind and (e.x - x) ** 2 + (e.y - y) ** 2 <= r2:
                e.strength = max(e.now_strength(now), strength)
                e.x, e.y, e.time = x, y, now
                return e
        e = MemoryEntry(kind, x, y, now, strength)
        self.entries.append(e)
        if len(self.entries) > self.capacity:
            self.entries.remove(min(self.entries, key=lambda m: m.now_strength(now)))
        return e

    def recall(self, kind, x, y, now, min_strength=0.15):
        """Best remembered location of `kind`: strong and close beats weak and far."""
        best, best_score = None, 0.0
        for e in self.entries:
            if e.kind != kind:
                continue
            s = e.now_strength(now)
            if s < min_strength:
                continue
            score = s / (1.0 + (((e.x - x) ** 2 + (e.y - y) ** 2) ** 0.5) / 300.0)
            if score > best_score:
                best, best_score = e, score
        return best

    def max_strength(self, kind, now) -> float:
        return max((e.now_strength(now) for e in self.entries if e.kind == kind), default=0.0)

    def forget_near(self, kind, x, y, radius):
        self.entries = [e for e in self.entries
                        if not (e.kind == kind and (e.x - x) ** 2 + (e.y - y) ** 2 <= radius * radius)]

    def prune(self, now):
        self.entries = [e for e in self.entries if e.now_strength(now) >= 0.05]

    def log(self, now, text):
        if not self.events or self.events[-1][1] != text:
            self.events.append((round(now, 1), text))
