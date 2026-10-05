"""State executors: each returns (desired_vx, desired_vy, speed_multiplier, effort)."""
from __future__ import annotations
import math
from .statemachine import State, Action, request_state
from . import steering as st
from . import needs


def _pick_target(c, w):
    rng = w.rng
    if w.shelters and rng.random() < c.mods.get("shelter_bias", 0.1):
        s = rng.choice(w.shelters)
        a, rad = rng.uniform(0, math.tau), s.r + rng.uniform(20, 140)
        tx, ty = s.x + math.cos(a) * rad, s.y + math.sin(a) * rad * 0.6
    else:
        tx, ty = rng.uniform(80, w.width - 80), rng.uniform(w.height * 0.12, w.floor_y - 40)
    return min(max(tx, 60), w.width - 60), min(max(ty, 60), w.floor_y - 30)


def _wander(c, w, now, mult):
    if c.target is None or now > c.target_until or math.hypot(c.target[0] - c.x, c.target[1] - c.y) < 30:
        c.target = _pick_target(c, w)
        c.target_until = now + w.rng.uniform(4, 9)
    vx, vy = st.seek(c, c.target[0], c.target[1], c.max_speed() * mult, 60)
    return vx, vy, mult, 0.8


def _explore(c, w, now):
    return _wander(c, w, now, 0.55)


def _consume(c, w, f, now):
    f.alive = False
    w.food.pop(f.id, None)
    c.hunger = max(0.0, c.hunger - f.nutrition)
    c.energy = min(1.0, c.energy + f.nutrition * 0.5)
    c.memory.remember("FOOD_FOUND", f.x, f.y, now)
    c.memory.log(now, "Found food")
    c.target_food = None
    w.stats["meals"] += 1
    request_state(c, State.EATING, now, force=True, lock=0.35)
    c.next_think = w.tick + 1


def _approach_food(c, w, now):
    f = w.food.get(c.target_food) if c.target_food is not None else None
    if f is None or not f.alive or math.hypot(f.x - c.x, f.y - c.y) > c.vision * 1.2:
        f, c.target_food = None, None
        if c.percepts:
            for _, cand in c.percepts.food:
                if cand.alive:
                    f, c.target_food = cand, cand.id
                    break
    if f is None:
        return None
    if math.hypot(f.x - c.x, f.y - c.y) < c.size * 0.5 + 6:
        _consume(c, w, f, now)
        return 0.0, 0.0, 0.3, 0.5
    vx, vy = st.seek(c, f.x, f.y, c.max_speed() * 0.85)
    return vx, vy, 0.85, 1.0


def _search(c, w, now):
    if c.current_goal == Action.EAT:
        r = _approach_food(c, w, now)
        if r:
            return r
    m = c.memory.recall("FOOD_FOUND", c.x, c.y, now)
    if m:
        if math.hypot(m.x - c.x, m.y - c.y) < 30:
            c.memory.forget_near("FOOD_FOUND", m.x, m.y, 60)   # went there, nothing left
        else:
            vx, vy = st.seek(c, m.x, m.y, c.max_speed() * 0.75)
            return vx, vy, 0.75, 1.0
    return _wander(c, w, now, 0.7)


def _eating(c, w, now):
    return 0.0, 0.0, 0.2, 0.5


def _flee(c, w, now):
    p = c.percepts
    t = next((o for _, o in p.threats if o.alive), None) if p else None
    if t is None:
        return c.vx, c.vy, 1.0, 1.0                      # keep momentum until the next think
    dx, dy = c.x - t.x, c.y - t.y
    d = math.hypot(dx, dy) or 1.0
    ux, uy = dx / d, dy / d
    side = 1.0 if c.id % 2 else -1.0                      # break symmetry: veer sideways a little
    ux, uy = ux - uy * 0.35 * side, uy + ux * 0.35 * side
    if p.shelters:
        sd, s = p.shelters[0]
        if 1.0 < sd < 350:
            ux += 0.5 * (s.x - c.x) / sd
            uy += 0.5 * (s.y - c.y) / sd
    m = math.hypot(ux, uy) or 1.0
    sp = c.max_speed() * 1.5
    return ux / m * sp, uy / m * sp, 1.5, 2.0


def _hide(c, w, now):
    p = c.percepts
    tx = ty = None
    rad = 40.0
    if p and p.shelters:
        _, s = p.shelters[0]
        tx, ty, rad = s.x, s.y, s.r
    else:
        m = c.memory.recall("SAFE_SPOT", c.x, c.y, now)
        if m:
            tx, ty, rad = m.x, m.y, 60.0
    if tx is None:
        return _wander(c, w, now, 0.5)
    tx += ((c.id * 37) % 100 - 50) / 50.0 * rad * 0.4
    ty += ((c.id * 53) % 100 - 50) / 50.0 * rad * 0.3
    if math.hypot(tx - c.x, ty - c.y) < 30:
        if c.hide_since is None:
            c.hide_since = now
        elif now - c.hide_since > 1.5 and (not p or p.threat_level == 0):
            c.memory.remember("SAFE_SPOT", c.x, c.y, now, 0.9)
        return 0.0, 0.0, 0.1, 0.3
    vx, vy = st.seek(c, tx, ty, c.max_speed() * 0.9, 40)
    return vx, vy, 0.9, 1.0


def _rest(c, w, now):
    return 0.0, 4.0, 0.1, 0.2


def _social(c, w, now):
    p = c.percepts
    speed = c.max_speed() * 0.7
    if p and p.friends:
        r = st.flock(c, p.friends, speed, c.size * 1.9)
        if r:
            return r[0], r[1], 0.8, 1.0
    m = c.memory.recall("SCHOOL_SEEN", c.x, c.y, now)
    if m and math.hypot(m.x - c.x, m.y - c.y) > 40:
        vx, vy = st.seek(c, m.x, m.y, speed)
        return vx, vy, 0.8, 1.0
    return _wander(c, w, now, 0.6)


def _hunt(c, w, now):
    p = c.percepts
    prey = w.creatures.get(c.target_prey) if c.target_prey is not None else None
    if prey is None or not prey.alive or math.hypot(prey.x - c.x, prey.y - c.y) > c.vision * 1.3:
        prey, c.target_prey = None, None
        if p:
            for _, o in p.prey:
                if o.alive:
                    prey, c.target_prey, c.chase_started = o, o.id, now
                    break
    if prey is None:
        if c.lost_prey_since is None:
            c.lost_prey_since = now
        elif now - c.lost_prey_since > 2.0:
            c.cooldown_until, c.lost_prey_since = now + 5.0, None
            c.next_think = w.tick
        return _wander(c, w, now, 0.6)
    c.lost_prey_since = None
    d = math.hypot(prey.x - c.x, prey.y - c.y)
    if d < c.size * 0.5 + prey.size * 0.5:
        prey.alive, prey.cause_of_death = False, "predation"
        c.hunger = max(0.0, c.hunger - min(0.6, 0.25 + 0.5 * prey.size / c.size))
        c.energy = min(1.0, c.energy + 0.2)
        c.cooldown_until, c.target_prey = now + 6.0, None
        c.memory.log(now, f"Caught a {prey.species.name}")
        w.stats["kills"] += 1
        w.log_event("predation", f"{c.name} caught {prey.name}", c.id)
        request_state(c, State.EATING, now, force=True, lock=0.8)
        c.next_think = w.tick + 1
        return 0.0, 0.0, 0.2, 0.5
    if now - c.chase_started > 8.0 or c.energy < 0.2:
        c.cooldown_until, c.target_prey = now + 6.0, None
        c.memory.log(now, "Gave up the chase")
        c.next_think = w.tick
        return _wander(c, w, now, 0.6)
    sp = c.max_speed() * 1.25
    t = min(1.0, d / (sp + 1.0))
    vx, vy = st.seek(c, prey.x + prey.vx * t, prey.y + prey.vy * t, sp)
    return vx, vy, 1.25, 2.0


_DISPATCH = {
    State.SEARCHING_FOR_FOOD: _search, State.EATING: _eating, State.FLEEING: _flee,
    State.HIDING: _hide, State.RESTING: _rest, State.SOCIALIZING: _social,
    State.HUNTING: _hunt, State.EXPLORING: _explore, State.IDLE: _explore,
}


def act(c, w, dt):
    now = w.time
    dvx, dvy, mult, c.effort = _DISPATCH[c.state](c, w, now)
    p = c.percepts
    ax, ay = st.avoid_walls(c, w)
    rx, ry = st.avoid_rocks(c, w)
    sx = sy = 0.0
    if p and c.state != State.SOCIALIZING:
        sx, sy = st.separation(c, p.neighbors, c.size * 2.0)
    speed = st.integrate(c, w, dvx + ax + rx + sx, dvy + ay + ry + sy, c.max_speed() * mult, dt)
    needs.tick_needs(c, dt, speed)
