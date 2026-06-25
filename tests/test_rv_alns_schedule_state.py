from __future__ import annotations

import unittest

from uqrv.energy import EnergyModel
from uqrv.metrics import evaluate_plan
from uqrv.scenario import Scenario, Stop, Tower, Weather
from uqrv.solvers import solve


class ScheduleStateAlnsTests(unittest.TestCase):
    def _scenario(self) -> Scenario:
        return Scenario(
            id="rv_alns_state_unit",
            size="UNIT",
            seed=11,
            towers=[
                Tower(0, 1.0, 0.0, risk=0.9, value=100.0, service_time=2.0, payload=0.5, segment=0),
                Tower(1, 1.4, 0.0, risk=0.8, value=95.0, service_time=2.0, payload=0.5, segment=0),
                Tower(2, 1.8, 0.0, risk=0.7, value=90.0, service_time=2.0, payload=0.5, segment=0),
                Tower(3, 8.0, 0.0, risk=0.2, value=20.0, service_time=2.0, payload=0.5, segment=1),
                Tower(4, 8.4, 0.0, risk=0.1, value=15.0, service_time=2.0, payload=0.5, segment=1),
            ],
            stops=[Stop(0, 0.0, 0.0), Stop(1, 8.0, 0.0)],
            vehicle_count=1,
            uav_count=2,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=60.0,
            battery_capacity=500.0,
            weather=Weather(1.0, 0.0, 22.0, 0.05),
        )

    def test_full_alns_uses_schedule_state_service_graph(self):
        scenario = self._scenario()
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        plan = solve(scenario, "alns_full", energy_model=energy, iterations=8, seed=3)

        self.assertEqual(plan.diagnostics["implementation_family"], "stop_batch_schedule_state_alns")
        self.assertGreater(plan.diagnostics["service_graph_pattern_count"], len(scenario.towers))
        self.assertEqual(plan.diagnostics["missed_service_count"], 0)
        self.assertIn("objective_rwct", plan.diagnostics)
        self.assertEqual(sorted(task.tower_id for task in plan.tasks), [0, 1, 2, 3, 4])
        self.assertTrue(any(len(sortie.tower_ids) > 1 for sortie in plan.sorties))
        metrics = evaluate_plan(scenario, plan, energy)
        self.assertAlmostEqual(metrics["risk_weighted_completion_time"], plan.diagnostics["objective_rwct"], places=5)

    def test_ablation_flags_are_exported_from_schedule_state_solver(self):
        scenario = self._scenario()
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        no_uq = solve(scenario, "alns_full_no_uq", energy_model=energy, iterations=4, seed=5)
        no_risk = solve(scenario, "alns_full_no_risk_value", energy_model=energy, iterations=4, seed=5)

        self.assertEqual(no_uq.diagnostics["implementation_family"], "stop_batch_schedule_state_alns")
        self.assertFalse(no_uq.diagnostics["use_quantile"])
        self.assertTrue(no_risk.diagnostics["use_quantile"])
        self.assertEqual(no_risk.diagnostics["risk_value_weight"], 0.0)
        self.assertGreaterEqual(no_uq.diagnostics["alns_objective_evaluations"], 1)
        self.assertGreaterEqual(no_risk.diagnostics["repair_greedy_insert_repair_uses"], 0)


if __name__ == "__main__":
    unittest.main()
