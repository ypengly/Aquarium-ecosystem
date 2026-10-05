"""Think step (runs on a schedule, not every tick): Perceive -> Remember -> Score -> Select goal."""
from __future__ import annotations
from .perception import perceive
from .utility import score_actions, alarm_level
from .statemachine import ACTION_STATE, State, request_state

FAST_STATES = (State.FLEEING, State.HUNTING, State.EATING)


def think(c, w):
    now = w.time
    p = perceive(w, c)
    c.percepts = p
    mem = c.memory
    dtk = max(0.05, now - c.last_think_time)
    c.last_think_time = now

    if p.threats:
        if mem.max_strength("PREDATOR_SEEN", now) < 0.3:
            mem.log(now, f"Spotted a {p.threats[0][1].species.name}")
        for _, o in p.threats[:3]:
            mem.remember("PREDATOR_SEEN", o.x, o.y, now)
    if p.food:
        f = p.food[0][1]
        mem.remember("FOOD_FOUND", f.x, f.y, now, 0.7)
    if len(p.friends) >= 2:
        n = len(p.friends)
        mem.remember("SCHOOL_SEEN", sum(o.x for _, o in p.friends) / n, sum(o.y for _, o in p.friends) / n, now, 0.8)
    mem.prune(now)

    if c.species.schooling:
        n = len(p.friends)
        if n >= 2:
            c.social_need = max(0.0, c.social_need - 0.4 * dtk)
        elif n == 0:
            c.social_need = min(1.0, c.social_need + 0.15 * c.sociality * dtk)
    c.safety += (1.0 - alarm_level(c, p, now) - c.safety) * min(1.0, 3.0 * dtk)

    c.scores = score_actions(c, p, now)
    goal = c.scores[0][0]
    c.current_goal = goal
    old = c.state
    if request_state(c, ACTION_STATE[goal], now) and c.state != old:
        if c.state == State.FLEEING and p.nearest_threat:
            mem.log(now, f"Fled from a {p.nearest_threat.species.name}")
        elif old == State.FLEEING and p.threat_level == 0:
            mem.log(now, "Avoided a predator")
        elif c.state == State.HIDING:
            mem.log(now, "Took shelter")
        elif c.state == State.SOCIALIZING and len(p.friends) >= 3:
            mem.log(now, "Joined a school")
    c.next_think = w.tick + (2 if c.state in FAST_STATES else 5)
    w.decisions += 1
