import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from run_publishable_experiments import _solver_mapping, run_prediction_experiment, run_solver_experiment


class PublishableRunnerTests(unittest.TestCase):
    def test_full_method_maps_to_operator_alns(self):
        method, iterations = _solver_mapping("alns_pinn_full", "M")
        self.assertEqual(method, "alns_full")
        self.assertGreater(iterations, 0)

    def test_main_experiment_external_baselines_map_to_non_alns_solvers(self):
        expected = {
            "simulated_annealing": "simulated_annealing",
            "tabu_search": "tabu_search",
            "variable_neighborhood_search": "variable_neighborhood_search",
            "hybrid_genetic_search": "hybrid_genetic_search",
        }
        for public_method, solver_method in expected.items():
            method, iterations = _solver_mapping(public_method, "M")
            self.assertEqual(method, solver_method)
            self.assertGreater(iterations, 0)

    def test_repair_ablation_methods_map_to_operator_alns_aliases(self):
        method, iterations = _solver_mapping("no_energy_repair", "M")
        self.assertEqual(method, "alns_full_no_energy_repair")
        self.assertGreater(iterations, 0)

        method, iterations = _solver_mapping("no_sync_repair", "M")
        self.assertEqual(method, "alns_full_no_sync_repair")
        self.assertGreater(iterations, 0)

        method, iterations = _solver_mapping("no_uq", "M")
        self.assertEqual(method, "alns_full_no_uq")
        self.assertGreater(iterations, 0)

        method, iterations = _solver_mapping("no_risk_value", "M")
        self.assertEqual(method, "alns_full_no_risk_value")
        self.assertGreater(iterations, 0)

        method, iterations = _solver_mapping("no_adaptive", "M")
        self.assertEqual(method, "alns_full_no_adaptive")
        self.assertGreater(iterations, 0)

    def test_solver_experiment_records_candidate_stop_screening_metrics(self):
        row = {
            "size": "M",
            "variant_index": 0,
            "tower_count": 30,
            "stop_count": 15,
            "vehicle_count": 2,
            "uavs_per_vehicle": 2,
            "seed": 2,
            "uncertainty": "medium",
            "method": "greedy_nearest",
            "candidate_mode": "kmeans",
            "nearest_per_tower": 2,
        }
        result = run_solver_experiment([row])[0]
        self.assertEqual(result["candidate_mode"], "kmeans")
        self.assertGreater(result["candidate_pair_reduction"], 0.0)
        self.assertLess(result["screened_pair_count"], result["total_candidate_pairs"])
        self.assertIn("kmeans15", result["scenario_id"])

    def test_solver_experiment_counts_direct_feasible_pairs_by_q95(self):
        row = {
            "size": "M",
            "variant_index": 0,
            "tower_count": 30,
            "stop_count": 15,
            "vehicle_count": 2,
            "uavs_per_vehicle": 2,
            "seed": 2,
            "uncertainty": "high",
            "method": "greedy_nearest",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]
        self.assertEqual(result["screened_pair_count"], result["total_candidate_pairs"])
        self.assertLess(result["feasible_candidate_pairs"], result["total_candidate_pairs"])

    def test_solver_experiment_records_milp_reference_scope(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 3,
            "uncertainty": "medium",
            "method": "milp_highs",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]
        self.assertEqual(result["milp_reference_scope"], "compact_makespan_energy_reference")
        self.assertFalse(result["milp_optimizes_rwct"])
        self.assertEqual(result["milp_completion_time_scope"], "post_hoc_schedule_evaluator")

    def test_solver_experiment_records_alns_operator_diagnostics(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 1,
            "uncertainty": "medium",
            "method": "alns_pinn_full",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]
        self.assertGreater(result["alns_accepted_moves"], 0)
        self.assertEqual(result["alns_score_cache_size"], 10)
        self.assertGreater(result["destroy_random_removal_uses"], 0)
        self.assertGreater(result["repair_greedy_insert_repair_uses"], 0)
        self.assertIn("repair_energy_minimum_insert_repair_uses", result)
        self.assertIn("repair_synchronization_aware_insert_repair_uses", result)

    def test_solver_experiment_records_portfolio_selection_diagnostics(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 1,
            "uncertainty": "medium",
            "method": "alns_pinn_full",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]

        self.assertGreaterEqual(result["alns_portfolio_candidate_count"], 1.0)
        self.assertIn(
            result["alns_selected_portfolio_candidate"],
            {
                "alns_search",
                "point_local",
                "uq_local",
                "risk_value_order",
                "risk_bucket_stop_4",
                "risk_bucket_stop_5",
                "risk_bucket_stop_8",
            },
        )
        self.assertGreater(result["alns_selected_portfolio_rwct"], 0.0)

    def test_solver_experiment_records_stop_batch_model_evidence(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 1,
            "uncertainty": "medium",
            "method": "alns_pinn_full",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]

        self.assertEqual(result["implementation_family"], "stop_batch_schedule_state_alns")
        self.assertGreater(result["service_graph_pattern_count"], result["tower_count"])
        self.assertGreater(result["service_graph_feasible_count"], 0)
        self.assertEqual(result["missed_service_count"], 0)
        self.assertGreater(result["objective_rwct"], 0.0)
        self.assertGreater(result["objective_q95_energy"], 0.0)

    def test_solver_experiment_records_strengthened_baseline_diagnostics(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 3,
            "uncertainty": "medium",
            "method": "ga",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]
        self.assertEqual(result["baseline_family"], "genetic_order_search")
        self.assertGreater(result["baseline_candidate_evaluations"], 0)
        self.assertGreater(result["baseline_population_size"], 0)

    def test_solver_experiment_records_public_sota_baseline_diagnostics(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 3,
            "uncertainty": "medium",
            "method": "hybrid_genetic_search",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]
        self.assertEqual(result["baseline_family"], "hybrid_genetic_vns_search")
        self.assertGreater(result["baseline_candidate_evaluations"], 0)
        self.assertGreater(result["baseline_population_size"], 0)

    def test_solver_experiment_records_repair_ablation_operator_zero_use(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 1,
            "uncertainty": "medium",
            "method": "no_energy_repair",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
        }
        result = run_solver_experiment([row])[0]
        self.assertEqual(result["repair_energy_minimum_insert_repair_uses"], 0.0)
        self.assertGreater(result["repair_greedy_insert_repair_uses"], 0.0)

    def test_solver_experiment_honors_sensitivity_iteration_override(self):
        row = {
            "size": "S",
            "variant_index": 0,
            "tower_count": 10,
            "stop_count": 5,
            "vehicle_count": 1,
            "uavs_per_vehicle": 1,
            "seed": 2,
            "uncertainty": "medium",
            "method": "alns_pinn_full",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
            "sensitivity_factor": "iteration_budget",
            "sensitivity_level": "7",
            "iteration_budget": 7,
        }
        result = run_solver_experiment([row])[0]
        self.assertEqual(result["sensitivity_factor"], "iteration_budget")
        self.assertEqual(result["alns_objective_evaluations"], 8.0)

    def test_prediction_experiment_records_simulation_trained_surrogate_status(self):
        row = {
            "size": "M",
            "variant_index": 1,
            "tower_count": 50,
            "stop_count": 25,
            "vehicle_count": 2,
            "uavs_per_vehicle": 2,
            "seed": 4,
            "uncertainty": "high",
            "method": "probabilistic_pinn",
            "candidate_mode": "direct",
            "nearest_per_tower": 3,
            "prediction_model": "probabilistic_pinn",
        }

        result = run_prediction_experiment([row])[0]

        self.assertEqual(result["prediction_evidence_level"], "simulation_trained")
        self.assertEqual(result["prediction_training_status"], "simulation_trained_not_field_validated")
        self.assertGreater(result["training_sample_count"], 0)


if __name__ == "__main__":
    unittest.main()
