"""Species definitions (data only). Individual variation comes from genes + personality."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Species:
    key: str
    name: str
    trophic: str                    # prey | forager | predator
    diet_food: tuple                # food kinds it eats
    diet_creatures: tuple           # species keys it hunts
    base_size: float                # body length, px
    base_speed: float               # cruise ceiling, px/s
    vision: float                   # perception radius, px
    metabolism: float               # hunger gained per second
    lifespan: float                 # seconds (used from Phase 14)
    schooling: bool
    traits: dict                    # mean of aggression/curiosity/fear/intelligence/sociality/territoriality
    personalities: tuple
    color: int
    stripe: int


def _t(a, c, f, i, s, t):
    return dict(aggression=a, curiosity=c, fear=f, intelligence=i, sociality=s, territoriality=t)


SPECIES = {s.key: s for s in (
    Species("neon_tetra", "Neon Tetra", "prey", ("fish_food",), (), 14, 110, 160, 1 / 240, 20000, True,
            _t(.05, .45, .70, .30, .90, .05),
            ("social", "shy", "curious", "nervous", "brave", "explorative"), 0x3FA9FF, 0xFF4D5E),
    Species("blue_tang", "Blue Tang", "forager", ("fish_food",), (), 30, 95, 210, 1 / 300, 40000, False,
            _t(.20, .60, .45, .60, .50, .30),
            ("curious", "lazy", "social", "intelligent", "brave", "explorative"), 0x2D6BFF, 0xFFD23F),
    Species("oscar", "Oscar", "predator", ("fish_food",), ("neon_tetra",), 38, 105, 240, 1 / 280, 50000, False,
            _t(.65, .50, .30, .55, .20, .70),
            ("aggressive", "territorial", "lazy", "intelligent", "curious"), 0x7A5C3E, 0xE0702B),
    Species("reef_shark", "Reef Shark", "predator", (), ("neon_tetra", "blue_tang", "oscar"), 120, 130, 420,
            1 / 420, 90000, False,
            _t(.85, .40, .05, .50, .10, .60),
            ("aggressive", "territorial", "explorative", "lazy"), 0x7F8C99, 0xDDE4EA),
)}

# species key -> set of species keys that hunt it
THREATS = {k: frozenset(o.key for o in SPECIES.values() if k in o.diet_creatures) for k in SPECIES}
