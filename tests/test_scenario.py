import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.scenario import generate_scenario


class ScenarioTests(unittest.TestCase):
    def test_generate_scenario_is_seed_reproducible(self):
        a = generate_scenario(size="S", seed=7)
        b = generate_scenario(size="S", seed=7)
        self.assertEqual(a.towers[0].x, b.towers[0].x)
        self.assertEqual(a.stops[0].x, b.stops[0].x)
        self.assertEqual(a.uav_count, b.uav_count)

    def test_generate_scenario_has_positive_task_values(self):
        scenario = generate_scenario(size="S", seed=3)
        self.assertGreater(len(scenario.towers), 0)
        self.assertTrue(all(t.value > 0 for t in scenario.towers))
        self.assertTrue(all(t.risk >= 0 for t in scenario.towers))


if __name__ == "__main__":
    unittest.main()

