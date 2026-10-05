"""Steering behaviours return desired-velocity vectors; integrate() applies limited acceleration."""
from __future__ import annotations
import math


def seek(c, tx, ty, speed, slow_radius=0.0):
    dx, dy = tx - c.x, ty - c.y
    d = math.hypot(dx, dy)
    if d < 1e-6:
        return 0.0, 0.0
    if slow_radius:
        speed *= min(1.0, d / slow_radius)
    return dx / d * speed, dy / d * speed


def avoid_walls(c, w, margin=70.0):
    sp = c.base_speed * 1.6
    fx = fy = 0.0
    if c.x < margin:
        fx += (1 - c.x / margin) * sp
    elif c.x > w.width - margin:
        fx -= (1 - (w.width - c.x) / margin) * sp
    if c.y < margin:
        fy += (1 - c.y / margin) * sp
    bottom = w.floor_y - 10
    if c.y > bottom - margin:
        fy -= min(1.0, 1 - (bottom - c.y) / margin) * sp
    return fx, fy


def avoid_rocks(c, w):
    sp = c.base_speed * 2.0
    fx = fy = 0.0
    for r in w.rocks:
        dx, dy = c.x - r.x, c.y - r.y
        d = math.hypot(dx, dy)
        lim = r.r + c.size + 30
        if 1e-3 < d < lim:
            k = (1 - d / lim) * sp
            fx += dx / d * k
            fy += dy / d * k
    return fx, fy


def separation(c, neighbors, personal):
    fx = fy = 0.0
    sp = c.base_speed
    for d, o in neighbors:
        if not o.alive or d >= personal or d < 1e-3:
            continue
        k = (1 - d / personal) * sp
        fx += (c.x - o.x) / d * k
        fy += (c.y - o.y) / d * k
    return fx, fy


def flock(c, friends, speed, personal):
    """Boids: separation + alignment + cohesion over perceived schoolmates (max 8 nearest)."""
    fr = [(d, o) for d, o in friends[:8] if o.alive]
    if not fr:
        return None
    n = len(fr)
    cx = sum(o.x for _, o in fr) / n
    cy = sum(o.y for _, o in fr) / n
    ax = sum(o.vx for _, o in fr) / n
    ay = sum(o.vy for _, o in fr) / n
    cohx, cohy = seek(c, cx, cy, speed)
    am = math.hypot(ax, ay)
    alx, aly = (ax / am * speed, ay / am * speed) if am > 1e-3 else (0.0, 0.0)
    sx, sy = separation(c, fr, personal)
    vx = 1.2 * cohx + 1.6 * alx + 1.6 * sx
    vy = 1.2 * cohy + 1.6 * aly + 1.6 * sy
    m = math.hypot(vx, vy)
    if m < speed * 0.35:                       # keep schooling fish moving
        hx, hy = math.cos(c.heading), math.sin(c.heading)
        vx, vy, m = vx + hx * speed * 0.4, vy + hy * speed * 0.4, math.hypot(vx + hx * speed * 0.4, vy + hy * speed * 0.4)
    if m > speed:
        vx, vy = vx / m * speed, vy / m * speed
    return vx, vy


def integrate(c, w, dvx, dvy, vmax, dt):
    m = math.hypot(dvx, dvy)
    if m > vmax:
        dvx, dvy = dvx / m * vmax, dvy / m * vmax
    ax, ay = dvx - c.vx, dvy - c.vy
    a = math.hypot(ax, ay)
    max_a = max(vmax, c.base_speed * 0.5) * 3.5 * dt
    if a > max_a:
        ax, ay = ax / a * max_a, ay / a * max_a
    c.vx += ax
    c.vy += ay
    s = math.hypot(c.vx, c.vy)
    cap = max(vmax * 1.05, 1.0)
    if s > cap:
        c.vx, c.vy, s = c.vx / s * cap, c.vy / s * cap, cap
    c.x += c.vx * dt
    c.y += c.vy * dt
    # hard bounds
    if c.x < 5: c.x, c.vx = 5.0, abs(c.vx)
    elif c.x > w.width - 5: c.x, c.vx = w.width - 5.0, -abs(c.vx)
    if c.y < 5: c.y, c.vy = 5.0, abs(c.vy)
    elif c.y > w.floor_y - 5: c.y, c.vy = w.floor_y - 5.0, -abs(c.vy)
    for r in w.rocks:                           # rocks are solid
        dx, dy = c.x - r.x, c.y - r.y
        d = math.hypot(dx, dy)
        lim = r.r + c.size * 0.3
        if d < lim:
            if d < 1e-3:
                dx, dy, d = 0.0, -1.0, 1.0
            c.x, c.y = r.x + dx / d * lim, r.y + dy / d * lim
    if s > 4.0:
        target = math.atan2(c.vy, c.vx)
        diff = (target - c.heading + math.pi) % (2 * math.pi) - math.pi
        c.heading += diff * min(1.0, 10.0 * dt)
    return s
