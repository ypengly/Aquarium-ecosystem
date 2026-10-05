"""Utility AI: every candidate action gets a 0..~1.3 score from needs, personality and percepts."""
from __future__ import annotations
from .statemachine import Action
from ..creatures.species import THREATS


def alarm_level(c, p, now) -> float:
    """Immediate threat plus lingering fear remembered from a recent predator sighting."""
    if not THREATS[c.species.key]:
        return 0.0
    return max(p.threat_level * 0.9, c.memory.max_strength("PREDATOR_SEEN", now) * 0.6)


def score_actions(c, p, now):
    m, h, e = c.mods, c.hunger, c.energy
    alarm = alarm_level(c, p, now)
    s = {}

    if p.threat_level > 0:
        s[Action.FLEE] = min(1.3, 0.45 + 0.9 * p.threat_level) * (0.7 + 0.6 * c.fear)

    if alarm > 0.08 and (p.shelters or c.memory.max_strength("SAFE_SPOT", now) > 0.15):
        s[Action.HIDE] = min(1.0, alarm * 0.8 * m.get("hide", 1.0) * (0.6 + 0.8 * c.fear))

    if c.species.diet_food and h > 0.12:
        if p.food:
            s[Action.EAT] = min(1.0, (h ** 1.5) * 1.1 + 0.05) * (1 - 0.6 * alarm)
        else:
            s[Action.SEARCH_FOOD] = (h ** 1.3) * 0.85 * (1 - 0.5 * alarm)

    if c.species.diet_creatures and p.prey and h > 0.25 and e > 0.2 and now >= c.cooldown_until:
        s[Action.HUNT] = (0.35 + 0.6 * h) * (0.6 + 0.4 * c.aggression) * m.get("hunt", 1.0)

    s[Action.EXPLORE] = (0.12 + 0.4 * c.curiosity * (0.5 + 0.5 * e)) * m.get("explore", 1.0) * (1 - 0.5 * alarm)
    s[Action.REST] = ((1 - e) ** 2) * m.get("rest", 1.0)

    if c.species.schooling:
        base = 0.26 + 0.5 * c.social_need + (0.16 if len(p.friends) >= 2 else 0.1 if p.friends else 0.0)
        s[Action.JOIN_SCHOOL] = min(0.85, base * m.get("school", 1.0))

    # hysteresis: stick with the current goal unless something clearly beats it
    if c.current_goal in s and c.current_goal != Action.FLEE:
        s[c.current_goal] += 0.08

    return sorted(s.items(), key=lambda kv: kv[1], reverse=True)
