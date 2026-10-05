"""The simulated aquarium. Pure Python, no networking: Go drives it through the gRPC layer."""
from __future__ import annotations
import math
import random
import time as _time
from collections import deque

from ..creatures.creature import Creature
from ..creatures.species import SPECIES
from ..ai.brain import think
from ..ai.behaviors import act
from .food import Food, FOOD_KINDS, Rock, Shelter
from .spatial import SpatialHash


class World:
    def __init__(self, width=1600.0, height=900.0, seed=1, tick_rate=20, scenery=True):
        self.width, self.height = float(width), float(height)
        self.floor_y = self.height - 70.0
        self.tick_rate = tick_rate
        self.dt = 1.0 / tick_rate
        self.seed = seed
        self.rng = random.Random(seed)
        self.tick = 0
        self.time = 0.0
        self.creatures: dict = {}
        self.food: dict = {}
        self.rocks: list = []
        self.shelters: list = []
        self._next_id = 1
        self.creature_grid = SpatialHash(120.0)
        self.food_grid = SpatialHash(120.0)
        self.events: deque = deque(maxlen=200)
        self._outbox: list = []
        self.decisions = 0
        self.stats = {"step_ms": 0.0, "decisions_per_sec": 0, "meals": 0, "kills": 0, "deaths": 0}
        if scenery:
            f = self.floor_y
            self.rocks = [Rock(360, f - 40, 55), Rock(960, f - 30, 70), Rock(1380, f - 35, 50)]
            self.shelters = [Shelter(200, f - 70, 90), Shelter(640, f - 80, 100),
                             Shelter(1180, f - 75, 95), Shelter(1500, f - 80, 80)]

    # ---------- population ----------
    def add_creature(self, species_key, x=None, y=None, personality=None, hunger=None, sex=None):
        sp = SPECIES[species_key]
        if x is None:
            x = self.rng.uniform(100, self.width - 100)
        if y is None:
            y = self.rng.uniform(self.height * 0.15, self.floor_y - 80)
        c = Creature(self._next_id, sp, float(x), float(y), self.rng, personality, sex, hunger)
        c.next_think = self.tick + c.id % 5
        self.creatures[c.id] = c
        self._next_id += 1
        return c

    def remove_creature(self, cid) -> bool:
        c = self.creatures.pop(cid, None)
        if c:
            c.alive = False
        return c is not None

    def add_food(self, x, y=30.0, kind="fish_food"):
        nut, vy, ttl = FOOD_KINDS[kind]
        f = Food(self._next_id, kind, float(x), float(y), vy, nut, ttl)
        self._next_id += 1
        self.food[f.id] = f
        return f

    def feed(self, x, count=4):
        return [self.add_food(x + self.rng.uniform(-40, 40), 30 + self.rng.uniform(0, 25)) for _ in range(count)]

    def populate_default(self):
        cx, cy = self.rng.uniform(500, 1100), self.rng.uniform(250, 500)
        for _ in range(18):
            self.add_creature("neon_tetra", cx + self.rng.gauss(0, 80), cy + self.rng.gauss(0, 60))
        for _ in range(5):
            self.add_creature("blue_tang")
        for _ in range(2):
            self.add_creature("oscar")
        for _ in range(3):
            self.feed(self.rng.uniform(300, 1300), 2)

    # ---------- geometry ----------
    def line_of_sight(self, x1, y1, x2, y2) -> bool:
        for r in self.rocks:
            dx, dy = x2 - x1, y2 - y1
            l2 = dx * dx + dy * dy
            t = 0.0 if l2 == 0 else max(0.0, min(1.0, ((r.x - x1) * dx + (r.y - y1) * dy) / l2))
            px, py = x1 + t * dx - r.x, y1 + t * dy - r.y
            if px * px + py * py < r.r * r.r:
                return False
        return True

    # ---------- simulation ----------
    def log_event(self, kind, text, creature_id=0):
        ev = {"tick": self.tick, "time": round(self.time, 1), "kind": kind, "text": text, "creature_id": creature_id}
        self.events.append(ev)
        self._outbox.append(ev)

    def drain_events(self):
        out, self._outbox = self._outbox, []
        return out

    def _update_food(self):
        for f in list(self.food.values()):
            f.ttl -= self.dt
            if f.y < self.floor_y - 4:
                f.y = min(self.floor_y - 4, f.y + f.vy * self.dt)
            if f.ttl <= 0:
                f.alive = False
                del self.food[f.id]

    def step(self, n=1):
        for _ in range(n):
            self._step()

    def _step(self):
        t0 = _time.perf_counter()
        self.tick += 1
        self.time += self.dt
        self.creature_grid.clear()
        self.food_grid.clear()
        for c in self.creatures.values():
            self.creature_grid.insert(c)
        self._update_food()
        for f in self.food.values():
            self.food_grid.insert(f)

        for c in list(self.creatures.values()):
            if not c.alive:
                continue
            if self.tick >= c.next_think:
                think(c, self)
            act(c, self, self.dt)

        for c in [c for c in self.creatures.values() if not c.alive]:
            del self.creatures[c.id]
            self.stats["deaths"] += 1
            self.log_event("death", f"{c.name} died ({c.cause_of_death})", c.id)

        ms = (_time.perf_counter() - t0) * 1000.0
        self.stats["step_ms"] = ms if self.stats["step_ms"] == 0 else self.stats["step_ms"] * 0.9 + ms * 0.1
        if self.tick % self.tick_rate == 0:
            self.stats["decisions_per_sec"], self.decisions = self.decisions, 0

    # ---------- views ----------
    def world_info(self):
        return {
            "width": self.width, "height": self.height, "floor_y": self.floor_y, "tick_rate": self.tick_rate,
            "rocks": [{"x": r.x, "y": r.y, "r": r.r} for r in self.rocks],
            "shelters": [{"x": s.x, "y": s.y, "r": s.r} for s in self.shelters],
            "species": [{"key": s.key, "name": s.name, "size": s.base_size, "vision": s.vision,
                         "color": s.color, "stripe": s.stripe, "trophic": s.trophic} for s in SPECIES.values()],
        }

    def snapshot(self):
        return {
            "tick": self.tick, "time": round(self.time, 2),
            "creatures": [{"id": c.id, "sp": c.species.key, "x": round(c.x, 1), "y": round(c.y, 1),
                           "vx": round(c.vx, 1), "vy": round(c.vy, 1), "h": round(c.heading, 2),
                           "st": c.state.value, "e": round(c.energy, 2), "hu": round(c.hunger, 2),
                           "hp": round(c.health, 2), "sz": round(c.size, 1)} for c in self.creatures.values()],
            "food": [{"id": f.id, "k": f.kind, "x": round(f.x, 1), "y": round(f.y, 1)} for f in self.food.values()],
            "stats": {"step_ms": round(self.stats["step_ms"], 2), "decisions": self.stats["decisions_per_sec"],
                      "creatures": len(self.creatures), "food": len(self.food)},
        }

    def inspect(self, cid):
        c = self.creatures.get(cid)
        if c is None:
            return None
        now = self.time
        tgt = None
        if c.state.value == "HUNTING" and c.target_prey in self.creatures:
            o = self.creatures[c.target_prey]; tgt = (o.x, o.y)
        elif c.target_food in self.food:
            o = self.food[c.target_food]; tgt = (o.x, o.y)
        elif c.target:
            tgt = c.target
        return {
            "id": c.id, "name": c.name, "species": c.species.key, "age": round(c.age, 1),
            "health": c.health, "energy": c.energy, "hunger": c.hunger, "safety": c.safety, "social": c.social_need,
            "personality": c.personality, "mood": c.mood, "state": c.state.value,
            "goal": c.current_goal.value if c.current_goal else "",
            "genes": {k: round(v, 3) for k, v in c.genes.items()},
            "traits": {k: round(getattr(c, k), 3) for k in ("aggression", "curiosity", "fear", "intelligence",
                                                           "sociality", "territoriality")},
            "scores": [{"action": a.value, "score": round(s, 3)} for a, s in c.scores],
            "memories": [{"kind": e.kind, "x": e.x, "y": e.y, "strength": round(e.now_strength(now), 3)}
                         for e in c.memory.entries if e.now_strength(now) >= 0.05],
            "recent": [t for _, t in reversed(c.memory.events)][:6],
            "target": tgt, "vision": c.vision,
        }
