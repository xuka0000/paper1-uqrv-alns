from __future__ import annotations

import unittest

from uqrv.energy import EnergyModel
from uqrv.scenario import Scenario, Stop, Tower, Weather
from uqrv.stop_batch_model import (
    ModelParameters,
    SortieAssignment,
    build_service_graph,
    evaluate_schedule_state,
    objective_breakdown,
)


class StopBatchModelTests(unittest.TestCase):
    def _scenario(self) -> Scenario:
        return Scenario(
            id="stop_batch_unit",
            size="UNIT",
            seed=7,
            towers=[
                Tower(0, 1.0, 0.0, risk=0.9, value=100.0, service_time=2.0, payload=0.5, segment=0),
                Tower(1, 1.6, 0.0, risk=0.7, value=80.0, service_time=2.0, payload=0.5, segment=0),
                Tower(2, 8.0, 0.0, risk=0.1, value=10.0, service_time=2.0, payload=0.5, segment=1),
            ],
            stops=[
                Stop(0, 0.0, 0.0),
                Stop(1, 7.5, 0.0),
            ],
            vehicle_count=1,
            uav_count=2,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=60.0,
            battery_capacity=500.0,
            weather=Weather(1.0, 0.0, 22.0, 0.05),
        )

    def test_service_graph_builds_q95_feasible_same_stop_patterns(self):
        scenario = self._scenario()
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        graph = build_service_graph(
            scenario,
            energy,
            ModelParameters(max_towers_per_sortie=2, nearest_stops_per_tower=2),
        )

        self.assertGreater(graph.pattern_count, len(scenario.towers))
        self.assertGreater(graph.feasible_service_count, 0)
        multi = [pattern for pattern in graph.patterns if pattern.stop_id == 0 and pattern.tower_ids == (0, 1)]
        self.assertEqual(len(multi), 1)
        self.assertTrue(multi[0].feasible)
        self.assertGreaterEqual(multi[0].energy_q95, multi[0].energy_mean)
        self.assertIn(multi[0].pattern_id, graph.patterns_by_tower[0])
        self.assertIn(multi[0].pattern_id, graph.patterns_by_tower[1])

    def test_schedule_state_enforces_stop_batch_vehicle_waiting_and_parallel_uavs(self):
        scenario = self._scenario()
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )
        graph = build_service_graph(
            scenario,
            energy,
            ModelParameters(max_towers_per_sortie=2, nearest_stops_per_tower=2),
        )
        pattern_01 = graph.require_pattern(stop_id=0, tower_ids=(0, 1))
        pattern_2 = graph.best_pattern_covering({2})

        state = evaluate_schedule_state(
            scenario,
            graph,
            [
                SortieAssignment(pattern_01.pattern_id, vehicle_id=0, uav_id=0),
                SortieAssignment(pattern_2.pattern_id, vehicle_id=0, uav_id=1),
            ],
            energy,
            ModelParameters(),
            method="unit_state",
        )

        self.assertEqual(len(state.tasks), 3)
        self.assertEqual(len(state.sorties), 2)
        first_sortie = state.sorties[0]
        self.assertEqual(first_sortie.tower_ids, [0, 1])
        self.assertGreater(first_sortie.return_time, state.tasks[0].finish)
        self.assertGreaterEqual(first_sortie.vehicle_departure, first_sortie.return_time)
        self.assertGreaterEqual(state.makespan, first_sortie.return_time)

    def test_objective_breakdown_matches_reported_metrics_terms(self):
        scenario = self._scenario()
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )
        params = ModelParameters(max_towers_per_sortie=2, nearest_stops_per_tower=2)
        graph = build_service_graph(scenario, energy, params)
        state = evaluate_schedule_state(
            scenario,
            graph,
            [SortieAssignment(graph.best_pattern_covering({tower.id}).pattern_id, 0, 0) for tower in scenario.towers],
            energy,
            params,
            method="objective_unit",
        )

        breakdown = objective_breakdown(scenario, state, params)

        self.assertAlmostEqual(breakdown.rwct, sum(task.priority * task.finish for task in state.tasks), places=6)
        self.assertEqual(breakdown.missed_service_count, 0)
        self.assertGreater(breakdown.q95_energy, 0.0)
        self.assertGreater(breakdown.total_objective, 0.0)


if __name__ == "__main__":
    unittest.main()
