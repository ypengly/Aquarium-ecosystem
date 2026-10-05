from __future__ import annotations
from dataclasses import dataclass

# kind -> (nutrition, sink speed px/s, time-to-live s)
FOOD_KINDS = {"fish_food": (0.28, 16.0, 70.0)}


@dataclass
class Food:
    id: int
    kind: str
    x: float
    y: float
    vy: float
    nutrition: float
    ttl: float
    alive: bool = True

    @property
    def vx(self):
        return 0.0


@dataclass
class Rock:
    x: float
    y: float
    r: float


@dataclass
class Shelter:
    """Plant clump / cave: creatures hide here. Does not block sight."""
    x: float
    y: float
    r: float
