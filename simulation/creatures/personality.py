"""Personalities shift trait values and add behaviour modifiers used by the utility AI."""
from __future__ import annotations
from dataclasses import dataclass, field


def clamp01(v: float) -> float:
    return 0.0 if v < 0 else 1.0 if v > 1 else v


@dataclass(frozen=True)
class Personality:
    name: str
    deltas: dict = field(default_factory=dict)   # additive trait shifts
    mods: dict = field(default_factory=dict)     # behaviour multipliers


PERSONALITIES = {p.name: p for p in (
    Personality("curious", {"curiosity": .25, "fear": -.10}, {"explore": 1.2}),
    Personality("shy", {"fear": .20, "curiosity": -.15, "aggression": -.10, "sociality": .10},
                {"flee_dist": 1.25, "hide": 1.4, "shelter_bias": .85, "explore": .8}),
    Personality("aggressive", {"aggression": .30, "fear": -.20, "territoriality": .20},
                {"hunt": 1.3, "flee_dist": .8}),
    Personality("lazy", {"curiosity": -.20}, {"rest": 1.6, "explore": .6, "speed": .9}),
    Personality("social", {"sociality": .20}, {"school": 1.3}),
    Personality("territorial", {"territoriality": .30, "aggression": .15}, {}),
    Personality("brave", {"fear": -.30, "aggression": .10}, {"flee_dist": .7, "hide": .5}),
    Personality("nervous", {"fear": .25}, {"flee_dist": 1.4, "hide": 1.1, "shelter_bias": .5}),
    Personality("explorative", {"curiosity": .30}, {"explore": 1.4}),
    Personality("intelligent", {"intelligence": .25}, {}),
)}
