import unittest
from simulation.grpc.service import SimService


class ServiceLayer(unittest.TestCase):
    def setUp(self):
        self.s = SimService()
        self.info = self.s.create_world("a1", seed=7)

    def test_create_is_idempotent_and_describes_world(self):
        again = self.s.create_world("a1", seed=99)
        self.assertEqual(self.info, again)
        self.assertEqual(self.info["tick_rate"], 20)
        self.assertGreaterEqual(len(self.info["species"]), 4)

    def test_step_advances_and_returns_snapshot(self):
        a = self.s.step("a1", 5)
        b = self.s.step("a1", 5)
        self.assertEqual((a["tick"], b["tick"]), (5, 10))
        self.assertTrue(b["creatures"])
        self.assertIsNone(self.s.step("nope", 1))

    def test_commands_are_validated_server_side(self):
        self.assertFalse(self.s.add_creature("a1", "kraken")[0])
        self.assertFalse(self.s.add_food("a1", 10, 10, 1, "gold")[0])
        ok, _, cid = self.s.add_creature("a1", "oscar", x=-5000, y=99999)       # clamped, not trusted
        self.assertTrue(ok)
        c = self.s._worlds["a1"].creatures[cid]
        self.assertTrue(0 <= c.x <= 1600 and 0 <= c.y <= 830)
        ok, _, _ = self.s.add_food("a1", 800, 30, count=10_000)
        self.assertTrue(ok)
        self.assertLess(len(self.s._worlds["a1"].food), 30)

    def test_step_is_bounded(self):
        snap = self.s.step("a1", 10**9)               # a hostile/huge request must be clamped
        self.assertEqual(snap["tick"], SimService.MAX_TICKS_PER_STEP)

    def test_events_drain_once(self):
        self.s.add_creature("a1", "reef_shark")
        first = self.s.step("a1", 1)["events"]
        self.assertTrue(any(e["kind"] == "spawn" for e in first))
        self.assertEqual(self.s.step("a1", 1)["events"], [])

    def test_inspect_and_remove(self):
        snap = self.s.step("a1", 20)
        cid = snap["creatures"][0]["id"]
        self.assertEqual(self.s.inspect("a1", cid)["id"], cid)
        self.assertTrue(self.s.remove_creature("a1", cid)[0])
        self.assertIsNone(self.s.inspect("a1", cid))


if __name__ == "__main__":
    unittest.main()
