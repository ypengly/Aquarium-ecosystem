# Aquarium Ecosystem

A living-ecosystem simulation, not an animation: every fish perceives, remembers, decides and acts on its own.
**This drop covers Phases 1-5** (rendering, movement, creature entities, needs, AI) as one vertical slice across all
three services, plus the parts of food, predation and schooling that the AI needs to be demonstrable.

```
Phaser/WebGL client (TS)  <--WebSocket, JSON deltas-->  Go world server  <--gRPC-->  Python simulation  (PostgreSQL: provisioned, used from Phase 18)
```

## Run

```bash
docker compose up          # http://localhost:3000   (builds run the Python tests; Go build runs go vet + go test)
```

Without Docker (three terminals): `make dev-sim`, `make dev-server`, `make dev-client` (client on :5173, proxies `/ws`).

In the tank: click open water to drop food, click a fish to inspect it, add species from the toolbar
(try adding a **Reef Shark**), and use the debug toggles (AI state labels, vision radius, selected target).

## What exists

| Phase | Where | Notes |
|---|---|---|
| 1 Rendering | `client/src/{scenes,aquarium,rendering}` | Procedural textures, light shafts, sway, bubbles, motes. Visual only. |
| 2 Movement | `simulation/ai/steering.py`, `client/src/networking/WorldState.ts` | Sim 20 Hz, render 60 FPS with interpolation 2 ticks behind. |
| 3 Entities | `simulation/creatures/` | Per-individual genes, personality, traits, memory. 4 species. |
| 4 Needs | `simulation/ai/needs.py` | Hunger, energy, health, safety, social. Starvation is real. |
| 5 AI | `simulation/ai/` | Perceive -> remember -> score (utility) -> FSM -> steer. |

Deliberately **not** built yet (they need their own phases, and are not faked): water chemistry, plants as living
things, breeding/genetics inheritance, disease, life cycle, building, auth, persistence, multiplayer, trading,
achievements, analytics, audio, interest management. Food, predation and schooling exist in basic form because the
AI cannot be shown without them; Phases 6-8 deepen them.

## How a fish decides

Runs on a schedule (every 5 ticks, every 2 while fleeing/hunting/eating), never per frame. Steering runs every tick.

1. **Perceive** (`ai/perception.py`): only things inside the creature's own vision radius, and rocks block line of sight.
2. **Remember** (`creatures/memory.py`): food spots, predator sightings, safe hiding spots, school locations; decaying,
   merged, capacity-limited by intelligence. Remembered food guides search; a visited-but-empty spot is forgotten.
3. **Score** (`ai/utility.py`): Eat, Search, Hunt, Flee, Hide, Explore, Rest, Join School each get a 0-1.3 score
   from needs x personality x percepts, with hysteresis. Hunger can outrank mild danger; severe danger always wins.
4. **Act** (`ai/statemachine.py`, `ai/behaviors.py`): the goal maps to a state (IDLE, SEARCHING_FOR_FOOD, EATING,
   RESTING, EXPLORING, FLEEING, HIDING, SOCIALIZING, HUNTING) with locks and minimum dwell times; FLEEING overrides.
5. **Steer** (`ai/steering.py`): seek/arrive, boids (separation, alignment, cohesion), wall and rock avoidance, limited acceleration.

Personality changes behaviour, not just numbers: shy fish flee earlier, hide more and wander near plants; brave fish
tolerate predators; aggressive ones hunt harder; lazy ones rest more. The inspector's **AI decision** panel shows the live
score of every action for the selected fish.

## Protocol (Go <-> client)

`WELCOME` (static world + species) -> `SNAPSHOT` (full) -> `DELTA` every tick. A delta carries only creatures whose
quantised state changed (0.5 px, ~3 deg, state, energy/hunger %), explicit removals, food changes, events and stats.
Client messages: `FEED {x}`, `ADD_CREATURE {species,x,y}`, `INSPECT {id}`. All are validated and rate-limited in Go and
validated again in Python. Slow clients are dropped and resync on reconnect. Rooms with no viewers do not tick.

## Tests and verification

| Suite | Count | Status in the environment this was built in |
|---|---|---|
| Python (`make test-sim`): food seeking, predator avoidance, hiding, hunting, schooling, perception, memory, needs, determinism, service validation | 29 | **Run, all passing** |
| Go (`delta`, `world` rooms with a fake simulator) | 8 | **Written, not run**: no Go toolchain in the build sandbox |
| TypeScript client | 0 | **Not compiled or run**: no npm/network; all 9 files only passed a syntax parse |
| gRPC adapter, Dockerfiles, compose | - | **Not run** (no grpcio, Docker or network). The service logic beneath the adapter is tested. |

So: expect to fix some compile or type errors in the Go and TypeScript on first build; the Docker builds will tell you
immediately (`go vet`, `go test` and `tsc --noEmit` are build steps). Please report what they print.

## Performance (single thread, this sandbox, 20 Hz budget = 50 ms/tick)

| Creatures | ms/tick | Budget used | AI decisions/s |
|---|---|---|---|
| 100 | 2.6 | 5% | 564 |
| 500 | 28.7 | 57% | 2,868 |
| 1,000 | 55.8 | **112%** | 5,826 |

The 1,000-creature target is **not yet met** in pure Python. Phase 24 plans: vectorised steering, wider AI scheduling
intervals by LOD, and sharding worlds across processes. Reproduce with `make bench`.

## Known limitations

- Inspector "Genetics" values are display-scaled gene multipliers; real inheritance arrives in Phase 12.
- Predators are balanced loosely (tetras mostly escape healthy oscars; exhausted fish get caught). Tuning comes with Phase 7.
- JSON deltas are ~60 bytes per moving creature; binary encoding and interest management are Phases 19-24.
- No offline simulation: empty rooms simply pause. The `Step(n)` RPC already supports catch-up for Phase 18.
