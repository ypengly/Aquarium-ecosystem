"""A single living creature: individual genes, personality, needs, memory and AI state."""
from __future__ import annotations
import math
from .species import Species
from .personality import PERSONALITIES, clamp01
from .memory import Memory
from ..ai.statemachine import State

TRAITS = ("aggression", "curiosity", "fear", "intelligence", "sociality", "territoriality")


class Creature:
    def __init__(self, cid, species: Species, x, y, rng, personality=None, sex=None, hunger=None):
        self.id = cid
        self.species = species
        self.alive = True
        self.cause_of_death = None
        self.age = 0.0
        self.sex = sex or rng.choice("MF")
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.heading = rng.uniform(-math.pi, math.pi)

        # genes: multipliers around 1.0 (inheritance/mutation arrive in Phase 12)
        self.genes = {k: min(1.3, max(0.7, rng.gauss(1.0, 0.08)))
                      for k in ("size", "speed", "metabolism", "vision", "vitality")}

        self.personality = personality or rng.choice(species.personalities)
        p = PERSONALITIES[self.personality]
        self.mods = dict(p.mods)
        for k in TRAITS:
            setattr(self, k, clamp01(species.traits[k] + rng.gauss(0, 0.07) + p.deltas.get(k, 0.0)))
        self.traits = [self.personality]

        self.size = species.base_size * self.genes["size"]
        self.base_speed = species.base_speed * self.genes["speed"] * self.mods.get("speed", 1.0)
        self.vision = species.vision * self.genes["vision"]
        self.metabolism = species.metabolism * self.genes["metabolism"]
        self.lifespan = species.lifespan * rng.uniform(0.85, 1.15)

        # needs
        self.health = 1.0
        self.energy = rng.uniform(0.6, 1.0)
        self.hunger = rng.uniform(0.15, 0.55) if hunger is None else hunger
        self.safety = 1.0
        self.social_need = rng.uniform(0.0, 0.3)

        self.memory = Memory(int(6 + 10 * self.intelligence))
        self.relationships = {}          # populated from Phase 11 (mates, friends, rivals)

        # AI state
        self.state = State.IDLE
        self.prev_state = State.IDLE
        self.state_since = 0.0
        self.lock_until = 0.0
        self.current_goal = None
        self.scores = []
        self.percepts = None
        self.next_think = 0
        self.last_think_time = 0.0
        self.target = None               # (x, y) wander / search destination
        self.target_until = 0.0
        self.target_food = None
        self.target_prey = None
        self.cooldown_until = 0.0
        self.hide_since = None
        self.chase_started = 0.0
        self.lost_prey_since = None
        self.effort = 1.0

    @property
    def name(self):
        return f"{self.species.name} #{self.id}"

    def max_speed(self):
        stamina = 0.55 + 0.45 * min(1.0, self.energy * 2.0)
        return self.base_speed * stamina * (0.5 + 0.5 * self.health)

    @property
    def mood(self):
        if self.state == State.FLEEING:
            return "Panicked"
        if self.state == State.HIDING or self.safety < 0.6:
            return "Anxious"
        if self.hunger > 0.7:
            return "Hungry"
        if self.energy < 0.25:
            return "Tired"
        return "Content" if self.hunger < 0.3 and self.energy > 0.6 else "Calm"
