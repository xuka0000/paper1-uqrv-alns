import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.online import generate_events, simulate_online_policy
from uqrv.scenario import generate_scenario


class OnlineTests(unittest.TestCase):
    def test_event_generation_is_seeded(self):
        scenario = generate_scenario(size="S", seed=9)
        self.assertEqual(generate_events(scenario, seed=1), generate_events(scenario, seed=1))

    def test_event_triggered_policy_reports_response_time(self):
        scenario = generate_scenario(size="S", seed=10)
        result = simulate_online_policy(scenario, policy="event_triggered", seed=2)
        self.assertIn("online_response_time", result.metrics)
        self.assertGreaterEqual(result.metrics["online_response_time"], 0)


if __name__ == "__main__":
    unittest.main()

