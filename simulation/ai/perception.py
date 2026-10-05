"""Creatures only know what they can perceive: radius-limited, blocked by rocks (line of sight)."""
from __future__ import annotations
import math
from ..creatures.species import THREATS


class Percepts:
    __slots__ = ("food", "threats", "prey", "friends", "shelters", "neighbors", "threat_level", "nearest_threat")

    def __init__(self):
        self.food, self.threats, self.prey, self.friends = [], [], [], []
        self.shelters, self.neighbors = [], []
        self.threat_level = 0.0
        self.nearest_threat = None


def threat_distance(c) -> float:
    """Distance at which a threat starts to matter. Fearful/shy fish react earlier."""
    return c.vision * (0.45 + 0.55 * c.fear) * c.mods.get("flee_dist", 1.0)


def perceive(w, c) -> Percepts:
    p = Percepts()
    r, r2 = c.vision, c.vision * c.vision
    threats = THREATS[c.species.key]
    prey_keys = c.species.diet_creatures
    close = c.size * 3.0
    los = w.line_of_sight

    for o in w.creature_grid.query(c.x, c.y, r):
        if o is c or not o.alive:
            continue
        dx, dy = o.x - c.x, o.y - c.y
        d2 = dx * dx + dy * dy
        if d2 > r2:
            continue
        d = math.sqrt(d2)
        k = o.species.key
        if k in threats:
            if los(c.x, c.y, o.x, o.y):
                p.threats.append((d, o))
        elif k in prey_keys:
            if los(c.x, c.y, o.x, o.y):
                p.prey.append((d, o))
        elif k == c.species.key and los(c.x, c.y, o.x, o.y):
            p.friends.append((d, o))
        if d < close:
            p.neighbors.append((d, o))

    if c.species.diet_food:
        for f in w.food_grid.query(c.x, c.y, r):
            if not f.alive or f.kind not in c.species.diet_food:
                continue
            d2 = (f.x - c.x) ** 2 + (f.y - c.y) ** 2
            if d2 <= r2 and los(c.x, c.y, f.x, f.y):
                p.food.append((math.sqrt(d2), f))

    for s in w.shelters:
        d = math.hypot(s.x - c.x, s.y - c.y)
        if d <= r + s.r:
            p.shelters.append((d, s))

    p.food.sort(key=lambda t: t[0])
    p.threats.sort(key=lambda t: t[0])
    p.prey.sort(key=lambda t: t[0])
    p.friends.sort(key=lambda t: t[0])
    p.shelters.sort(key=lambda t: t[0])

    if p.threats:
        td = threat_distance(c)
        p.nearest_threat = p.threats[0][1]
        p.threat_level = max(0.0, min(1.0, 1.0 - p.threats[0][0] / td))
    return p
