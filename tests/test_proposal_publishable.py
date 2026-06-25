import unittest
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.milp_reference import _plan_from_solution, solve_milp_reference
from uqrv.proposal_design import (
    PROPOSAL_SIZE_CONFIGS,
    build_proposal_experiment_matrix,
    generate_proposal_scenario,
)
from uqrv.energy import EnergyModel
from uqrv.scenario import Scenario, Stop, Tower, Weather


class ProposalPublishableTests(unittest.TestCase):
    def test_proposal_size_grid_matches_original_plan(self):
        self.assertEqual([c.tower_count for c in PROPOSAL_SIZE_CONFIGS["S"]], [10, 15, 20])
        self.assertEqual([c.stop_count for c in PROPOSAL_SIZE_CONFIGS["S"]], [5, 8, 10])
        self.assertEqual([c.tower_count for c in PROPOSAL_SIZE_CONFIGS["M"]], [30, 50, 75, 100])
        self.assertEqual([c.tower_count for c in PROPOSAL_SIZE_CONFIGS["L"]], [150, 200, 300, 500])

    def test_generate_proposal_scenario_uses_explicit_counts(self):
        scenario = generate_proposal_scenario("M", variant_index=2, seed=7, uncertainty="high")
        self.assertEqual(len(scenario.towers), 75)
        self.assertEqual(len(scenario.stops), 35)
        self.assertEqual(scenario.vehicle_count, 3)
        self.assertEqual(scenario.uav_count, 9)
        self.assertGreater(scenario.weather.uncertainty, 0.2)

    def test_experiment_matrix_contains_original_five_experiment_blocks(self):
        matrix = build_proposal_experiment_matrix(seeds=range(2), quick=True)
        self.assertIn("P1_milp_exact_small", matrix)
        self.assertIn("P2_algorithm_comparison", matrix)
        self.assertIn("P3_pinn_prediction_accuracy", matrix)
        self.assertIn("P4_ablation", matrix)
        self.assertIn("P5_case_study", matrix)
        self.assertIn("P6_candidate_stop_screening", matrix)
        self.assertIn("P8_sensitivity", matrix)
        self.assertTrue(any(row["method"] == "milp_highs" for row in matrix["P1_milp_exact_small"]))
        self.assertTrue(any(row["tower_count"] == 500 for row in matrix["P2_algorithm_comparison"]))
        p2_methods = {row["method"] for row in matrix["P2_algorithm_comparison"]}
        self.assertTrue(
            {
                "greedy_nearest",
                "ga",
                "aco",
                "simulated_annealing",
                "tabu_search",
                "variable_neighborhood_search",
                "hybrid_genetic_search",
                "alns_pinn_full",
            }.issubset(p2_methods)
        )
        self.assertFalse({"alns_fixed", "alns_pinn", "alns_pinn_uq"}.intersection(p2_methods))
        p4_methods = {row["method"] for row in matrix["P4_ablation"]}
        self.assertIn("alns_fixed", p4_methods)
        self.assertIn("alns_pinn", p4_methods)
        self.assertIn("alns_pinn_uq", p4_methods)
        self.assertIn("no_energy_repair", p4_methods)
        self.assertIn("no_sync_repair", p4_methods)
        p6_modes = {row["candidate_mode"] for row in matrix["P6_candidate_stop_screening"]}
        self.assertEqual(p6_modes, {"direct", "kmeans", "dbscan"})
        p8_factors = {row["sensitivity_factor"] for row in matrix["P8_sensitivity"]}
        self.assertEqual(
            p8_factors,
            {"quantile_z", "reserve_ratio", "iteration_budget", "uav_count", "candidate_mode"},
        )

    def test_milp_reference_solves_small_dynamic_pinn_instance(self):
        scenario = generate_proposal_scenario("S", variant_index=0, seed=3, uncertainty="medium")
        plan, info = solve_milp_reference(scenario, EnergyModel(scenario.battery_capacity), time_limit=20)
        covered = {task.tower_id for task in plan.tasks}
        self.assertEqual(len(covered), len(scenario.towers))
        self.assertEqual(plan.method, "milp_highs")
        self.assertIn(info["status"], {"optimal", "time_limit", "feasible"})
        self.assertLessEqual(info["relative_gap"], 0.25)
        self.assertEqual(info["reference_scope"], "compact_makespan_energy_reference")
        self.assertFalse(info["optimizes_rwct"])
        self.assertEqual(info["completion_time_scope"], "post_hoc_schedule_evaluator")

    def test_milp_reference_decode_uses_stop_batch_vehicle_timing(self):
        scenario = Scenario(
            id="milp_decode_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 0.0, 0.0, risk=0.2, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 60.0, 0.0, risk=0.2, value=10.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0), Stop(1, 60.0, 0.0)],
            vehicle_count=1,
            uav_count=2,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        x = np.zeros(len(scenario.towers) * len(scenario.stops))
        x[0] = 1.0
        x[3] = 1.0

        tasks = _plan_from_solution(
            scenario,
            EnergyModel(battery_capacity=10000.0, reserve_ratio=0.0, drone_speed_kmph=120.0),
            x,
            lambda i, s: i * len(scenario.stops) + s,
        )
        task_by_id = {task.tower_id: task for task in tasks}

        self.assertGreaterEqual(task_by_id[1].start, task_by_id[0].finish + 60.0 - 1e-6)


if __name__ == "__main__":
    unittest.main()
