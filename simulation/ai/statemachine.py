"""Finite state machine: utility AI picks an Action (goal); the FSM decides whether and when
the creature may actually enter the matching State (locks + minimum dwell times)."""
from __future__ import annotations
from enum import Enum


class State(str, Enum):
    IDLE = "IDLE"
    SEARCHING_FOR_FOOD = "SEARCHING_FOR_FOOD"
    EATING = "EATING"
    RESTING = "RESTING"
    EXPLORING = "EXPLORING"
    FLEEING = "FLEEING"
    HIDING = "HIDING"
    SOCIALIZING = "SOCIALIZING"
    HUNTING = "HUNTING"


class Action(str, Enum):
    EAT = "EAT"
    SEARCH_FOOD = "SEARCH_FOOD"
    HUNT = "HUNT"
    FLEE = "FLEE"
    HIDE = "HIDE"
    EXPLORE = "EXPLORE"
    REST = "REST"
    JOIN_SCHOOL = "JOIN_SCHOOL"


ACTION_STATE = {
    Action.EAT: State.SEARCHING_FOR_FOOD, Action.SEARCH_FOOD: State.SEARCHING_FOR_FOOD,
    Action.HUNT: State.HUNTING, Action.FLEE: State.FLEEING, Action.HIDE: State.HIDING,
    Action.EXPLORE: State.EXPLORING, Action.REST: State.RESTING, Action.JOIN_SCHOOL: State.SOCIALIZING,
}

# Leaving these states early is not allowed (seconds); FLEEING always overrides.
MIN_DWELL = {State.EXPLORING: 1.5, State.RESTING: 2.0, State.SOCIALIZING: 1.0, State.HIDING: 1.5}


def request_state(c, new, now, force=False, lock=0.0):
    if new == c.state:
        if lock:
            c.lock_until = now + lock
        return True
    if not force and new != State.FLEEING:
        if c.lock_until > now:
            return False
        if now - c.state_since < MIN_DWELL.get(c.state, 0.0):
            return False
    c.prev_state = c.state
    c.state, c.state_since = new, now
    c.lock_until = now + lock if lock else 0.0
    c.hide_since = None
    c.target = None
    return True
