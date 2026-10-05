"""Need dynamics: hunger, energy, health, safety, social."""
from __future__ import annotations
from .statemachine import State


def tick_needs(c, dt: float, speed: float):
    c.age += dt
    ratio = speed / max(1.0, c.species.base_speed)
    c.hunger = min(1.0, c.hunger + c.metabolism * dt)

    resting = c.state in (State.RESTING, State.EATING) or (c.state == State.HIDING and ratio < 0.15)
    burn = 0.002 + 0.012 * ratio * ratio * c.effort
    c.energy += (0.03 if resting else 0.0) * dt - burn * dt
    if c.hunger >= 1.0:
        c.energy -= 0.01 * dt
        c.health -= 0.01 * dt
    c.energy = max(0.0, min(1.0, c.energy))
    if c.energy <= 0.0:
        c.health -= 0.02 * dt
    elif c.hunger < 0.7 and c.energy > 0.3:
        c.health = min(1.0, c.health + 0.003 * dt)
    if c.health <= 0.0:
        c.alive = False
        c.cause_of_death = "starvation"
