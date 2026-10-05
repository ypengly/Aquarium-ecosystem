"""Transport-independent service layer: owns the worlds and exposes plain-dict operations.
The gRPC servicer is a thin adapter over this class, so all logic is testable without grpcio."""
from __future__ import annotations
import threading
from ..ecosystem.world import World
from ..creatures.species import SPECIES


class SimService:
    MAX_TICKS_PER_STEP = 2000          # offline catch-up goes through Step(n); keep it bounded

    def __init__(self):
        self._worlds: dict = {}
        self._locks: dict = {}
        self._guard = threading.Lock()

    def _get(self, aid):
        with self._guard:
            w = self._worlds.get(aid)
            return w, self._locks.get(aid)

    def create_world(self, aid, seed=1, populate_default=True):
        with self._guard:
            if aid in self._worlds:
                return self._worlds[aid].world_info()
            w = World(seed=seed or 1)
            if populate_default:
                w.populate_default()
            self._worlds[aid], self._locks[aid] = w, threading.Lock()
            return w.world_info()

    def drop_world(self, aid):
        with self._guard:
            self._locks.pop(aid, None)
            return self._worlds.pop(aid, None) is not None

    def step(self, aid, ticks=1):
        w, lock = self._get(aid)
        if w is None:
            return None
        with lock:
            w.step(max(1, min(ticks, self.MAX_TICKS_PER_STEP)))
            snap = w.snapshot()
            snap["events"] = w.drain_events()
            return snap

    def snapshot(self, aid):
        w, lock = self._get(aid)
        if w is None:
            return None
        with lock:
            snap = w.snapshot()
            snap["events"] = []
            return snap

    def add_food(self, aid, x, y=30.0, count=1, kind="fish_food"):
        w, lock = self._get(aid)
        if w is None:
            return False, "unknown aquarium", 0
        with lock:
            if kind != "fish_food":
                return False, "unknown food kind", 0
            count = max(1, min(int(count or 1), 8))
            x = min(max(float(x), 20.0), w.width - 20.0)
            y = min(max(float(y), 10.0), w.floor_y - 10.0)
            first = None
            for i in range(count):
                f = w.add_food(x + (w.rng.uniform(-40, 40) if count > 1 else 0.0), y + w.rng.uniform(0, 20))
                first = first or f
            return True, "", first.id

    def add_creature(self, aid, species, x=None, y=None):
        w, lock = self._get(aid)
        if w is None:
            return False, "unknown aquarium", 0
        if species not in SPECIES:
            return False, "unknown species", 0
        with lock:
            if len(w.creatures) >= 1500:
                return False, "aquarium is full", 0
            if x is not None:
                x = min(max(float(x), 20.0), w.width - 20.0)
            if y is not None:
                y = min(max(float(y), 20.0), w.floor_y - 20.0)
            c = w.add_creature(species, x, y)
            w.log_event("spawn", f"{c.name} was added", c.id)
            return True, "", c.id

    def remove_creature(self, aid, cid):
        w, lock = self._get(aid)
        if w is None:
            return False, "unknown aquarium", 0
        with lock:
            ok = w.remove_creature(cid)
            return ok, "" if ok else "no such creature", cid

    def inspect(self, aid, cid):
        w, lock = self._get(aid)
        if w is None:
            return None
        with lock:
            return w.inspect(cid)
