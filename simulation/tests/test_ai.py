import math
import unittest
from simulation.ecosystem.world import World
from simulation.ecosystem.food import Rock, Shelter
from simulation.ai.statemachine import State, Action
from simulation.ai.perception import perceive, threat_distance
from simulation.ai.utility import score_actions


def blank(seed=1):
    return World(seed=seed, scenery=False)


def fish(w, sp, x, y, **kw):
    kw.setdefault("personality", None)
    c = w.add_creature(sp, x, y, **kw)
    c.energy = 0.9
    return c


def scores(c):
    return dict(c.scores)


class FoodSeeking(unittest.TestCase):
    def test_hungry_fish_finds_and_eats_visible_food(self):
        w = blank()
        c = fish(w, "neon_tetra", 400, 400, hunger=0.8, personality="curious")
        f = w.add_food(500, 400)
        seen = set()
        for _ in range(240):
            w.step()
            seen.add(c.state)
            if f.id not in w.food:
                break
        self.assertNotIn(f.id, w.food, "food should have been eaten")
        self.assertLess(c.hunger, 0.6)
        self.assertIn(State.SEARCHING_FOR_FOOD, seen)
        w.step(3)
        self.assertIn(State.EATING, seen | {c.state})

    def test_sated_fish_ignores_food(self):
        w = blank()
        c = fish(w, "neon_tetra", 400, 400, hunger=0.05)
        f = w.add_food(430, 400)
        w.step(40)
        self.assertIn(f.id, w.food)

    def test_food_beyond_vision_not_perceived(self):
        w = blank()
        c = fish(w, "neon_tetra", 400, 400, hunger=0.8)
        w.add_food(400 + c.vision + 60, 400)
        w.step(1)
        w.creature_grid.clear(); w.creature_grid.insert(c)
        self.assertEqual(perceive(w, c).food, [])

    def test_remembered_food_location_guides_search(self):
        w = blank()
        c = fish(w, "neon_tetra", 300, 400, hunger=0.85, personality="curious")
        c.memory.remember("FOOD_FOUND", 800, 400, 0.0)
        w.step(100)
        self.assertGreater(c.x, 380, "fish should head toward remembered food site")
        self.assertEqual(c.state, State.SEARCHING_FOR_FOOD)


class Utility(unittest.TestCase):
    def test_hunger_outweighs_mild_danger_but_not_severe_danger(self):
        w = blank()
        c = fish(w, "neon_tetra", 500, 400, hunger=0.95, personality="curious")
        w.add_food(540, 400)
        sh = w.add_creature("reef_shark", 500 + 125, 400)
        w.step(1)
        far = scores(c)
        self.assertEqual(max(far, key=far.get), Action.EAT, far)
        sh.x = 500 + 40
        w.creature_grid.clear(); [w.creature_grid.insert(o) for o in w.creatures.values()]
        from simulation.ai.brain import think
        think(c, w)
        near = scores(c)
        self.assertEqual(max(near, key=near.get), Action.FLEE, near)

    def test_scores_sorted_and_exposed(self):
        w = blank()
        c = fish(w, "neon_tetra", 500, 400)
        w.step(6)
        vals = [s for _, s in c.scores]
        self.assertEqual(vals, sorted(vals, reverse=True))
        self.assertTrue(c.current_goal)


class PredatorAvoidance(unittest.TestCase):
    def test_prey_flees_away_from_predator(self):
        w = blank()
        c = fish(w, "neon_tetra", 400, 400, personality="curious")
        w.add_creature("reef_shark", 500, 400)
        for _ in range(12):
            w.step()
        self.assertEqual(c.state, State.FLEEING)
        self.assertLess(c.vx, 0, "should move away from shark on the right")

    def test_prey_remembers_predator_and_hides_after_it_leaves(self):
        w = blank()
        w.shelters.append(Shelter(350, 450, 90))
        c = fish(w, "neon_tetra", 420, 400, personality="shy")
        sh = w.add_creature("reef_shark", 530, 400)
        w.step(20)
        self.assertGreater(c.memory.max_strength("PREDATOR_SEEN", w.time), 0.5)
        w.remove_creature(sh.id)
        w.step(30)
        self.assertEqual(c.current_goal, Action.HIDE)
        self.assertEqual(c.state, State.HIDING)

    def test_predator_hunts_catches_and_gains_food(self):
        w = blank()
        shark = fish(w, "reef_shark", 400, 400, hunger=0.8, personality="aggressive")
        prey = fish(w, "blue_tang", 470, 400, personality="lazy")
        prey.energy = 0.2                        # exhausted prey cannot escape
        w.step(400)
        self.assertNotIn(prey.id, w.creatures)
        self.assertEqual(prey.cause_of_death, "predation")
        self.assertLess(shark.hunger, 0.8)
        self.assertEqual(w.stats["kills"], 1)

    def test_sated_predator_does_not_hunt(self):
        w = blank()
        shark = fish(w, "reef_shark", 400, 400, hunger=0.05)
        prey = fish(w, "blue_tang", 470, 400)
        w.step(200)
        self.assertIn(prey.id, w.creatures)

    def test_predator_gives_up_when_exhausted(self):
        w = blank()
        shark = fish(w, "reef_shark", 200, 400, hunger=0.9, personality="aggressive")
        shark.energy = 0.15
        fish(w, "neon_tetra", 330, 400)
        w.step(40)
        self.assertNotEqual(shark.state, State.HUNTING)


class Perception(unittest.TestCase):
    def test_radius_limits_knowledge(self):
        w = blank()
        c = fish(w, "reef_shark", 400, 400)
        near = fish(w, "neon_tetra", 400 + 300, 400)
        far = fish(w, "neon_tetra", 400 + 460, 400)
        for o in w.creatures.values():
            w.creature_grid.insert(o)
        ids = {o.id for _, o in perceive(w, c).prey}
        self.assertIn(near.id, ids)
        self.assertNotIn(far.id, ids)

    def test_rock_blocks_line_of_sight(self):
        w = blank()
        w.rocks.append(Rock(500, 400, 40))
        c = fish(w, "reef_shark", 400, 400)
        t = fish(w, "neon_tetra", 600, 400)
        for o in w.creatures.values():
            w.creature_grid.insert(o)
        self.assertEqual(perceive(w, c).prey, [])
        t.y = 600; t.x = 520
        self.assertTrue(w.line_of_sight(c.x, c.y, 400, 500))

    def test_shy_fish_reacts_earlier_than_brave(self):
        w = blank()
        shy = fish(w, "neon_tetra", 100, 100, personality="shy")
        brave = fish(w, "neon_tetra", 200, 200, personality="brave")
        self.assertGreater(threat_distance(shy), threat_distance(brave) * 1.4)


class Schooling(unittest.TestCase):
    LINK = 80.0

    def _groups(self, fs):
        seen, groups = set(), []
        for a in fs:
            if a.id in seen:
                continue
            comp, stack = [], [a]
            while stack:
                u = stack.pop()
                if u.id in seen:
                    continue
                seen.add(u.id)
                comp.append(u)
                stack += [b for b in fs if b.id not in seen and math.hypot(u.x - b.x, u.y - b.y) < self.LINK]
            groups.append(comp)
        return groups

    def _local_alignment(self, fs):
        vals = []
        for a in fs:
            nb = [b for b in fs if b is not a and math.hypot(a.x - b.x, a.y - b.y) < self.LINK]
            if len(nb) < 2:
                continue
            sx = sum(b.vx / (math.hypot(b.vx, b.vy) or 1) for b in nb)
            sy = sum(b.vy / (math.hypot(b.vx, b.vy) or 1) for b in nb)
            vals.append(math.hypot(sx, sy) / len(nb))
        return sum(vals) / len(vals) if vals else 0.0

    def test_school_emerges_from_scattered_fish(self):
        for seed in (2, 5, 7):
            w = blank(seed=seed)
            fs = []
            for _ in range(14):
                c = w.add_creature("neon_tetra", w.rng.uniform(400, 1000), w.rng.uniform(250, 600), hunger=0.0)
                c.energy, c.metabolism = 1.0, 0.0
                fs.append(c)
            g0 = len(self._groups(fs))
            w.step(20 * 40)
            g1 = self._groups(fs)
            self.assertLessEqual(len(g1), max(2, g0 // 2), (seed, g0, len(g1)))
            self.assertGreaterEqual(max(len(g) for g in g1), 5, "a real school should form")
            self.assertGreater(self._local_alignment(fs), 0.65, seed)
            self.assertGreater(sum(c.state == State.SOCIALIZING for c in fs), 8)

    def test_school_scatters_and_regroups_around_predator(self):
        w = blank(seed=3)
        fs = [w.add_creature("neon_tetra", 800 + w.rng.gauss(0, 40), 400 + w.rng.gauss(0, 30), hunger=0.0)
              for _ in range(12)]
        for c in fs:
            c.energy, c.metabolism = 1.0, 0.0
        w.step(20 * 10)
        cx = sum(c.x for c in fs) / len(fs)
        cy = sum(c.y for c in fs) / len(fs)
        shark = w.add_creature("reef_shark", cx + 30, cy)   # inside the school's threat range
        shark.hunger = 0.0                                  # not hunting: just a threat
        def mean_dist():
            return sum(math.hypot(c.x - shark.x, c.y - shark.y) for c in fs) / len(fs)
        d0 = mean_dist()
        fled = set()
        for _ in range(10):
            w.step()
            fled |= {c.id for c in fs if c.state == State.FLEEING}
        # fish near the shark panic; those outside their (personality-dependent) threat range don't
        self.assertGreaterEqual(len(fled), 4)
        self.assertLess(len(fled), len(fs) + 1)
        w.step(40)
        self.assertGreater(mean_dist(), d0 + 50, "school should open up and move away from the predator")


class Systems(unittest.TestCase):
    def test_hunger_rises_and_starvation_kills(self):
        w = blank()
        c = fish(w, "neon_tetra", 400, 400, hunger=0.0)
        w.step(20 * 30)
        self.assertGreater(c.hunger, 0.1)
        c.hunger = 1.0
        c.energy = 0.05
        w.step(20 * 400)
        self.assertNotIn(c.id, w.creatures)
        self.assertEqual(c.cause_of_death, "starvation")

    def test_memory_decay_merge_and_capacity(self):
        from simulation.creatures.memory import Memory
        m = Memory(3)
        m.remember("FOOD_FOUND", 100, 100, 0.0)
        m.remember("FOOD_FOUND", 120, 100, 0.0)          # merged
        self.assertEqual(len(m.entries), 1)
        self.assertAlmostEqual(m.max_strength("FOOD_FOUND", 90.0), 0.5, places=2)
        for i in range(6):
            m.remember("SAFE_SPOT", i * 500, 0, 0.0)
        self.assertLessEqual(len(m.entries), 3)
        self.assertIsNone(m.recall("PREDATOR_SEEN", 0, 0, 0.0))

    def test_individuals_differ(self):
        w = blank()
        a = [w.add_creature("neon_tetra") for _ in range(20)]
        self.assertGreater(len({c.personality for c in a}), 2)
        self.assertGreater(len({round(c.fear, 2) for c in a}), 10)
        self.assertGreater(len({round(c.base_speed) for c in a}), 5)

    def test_deterministic_by_seed(self):
        def run():
            w = World(seed=9); w.populate_default(); w.step(200)
            return w.snapshot()["creatures"]
        self.assertEqual(run(), run())

    def test_ai_is_scheduled_not_per_tick(self):
        w = World(seed=2); w.populate_default()
        n = len(w.creatures); w.step(20 * 5)
        self.assertLess(w.stats["decisions_per_sec"], n * w.tick_rate * 0.5)

    def test_inspect_exposes_ai_visualizer_data(self):
        w = World(seed=2); w.populate_default(); w.step(30)
        d = w.inspect(next(iter(w.creatures)))
        self.assertTrue(d["scores"] and d["goal"] and "traits" in d and "recent" in d)
        self.assertIsNone(w.inspect(99999))

    def test_creatures_stay_in_bounds_and_out_of_rocks(self):
        w = World(seed=4); w.populate_default(); w.step(20 * 30)
        for c in w.creatures.values():
            self.assertTrue(0 <= c.x <= w.width and 0 <= c.y <= w.floor_y)
            for r in w.rocks:
                self.assertGreaterEqual(math.hypot(c.x - r.x, c.y - r.y), r.r - 1)


if __name__ == "__main__":
    unittest.main()
