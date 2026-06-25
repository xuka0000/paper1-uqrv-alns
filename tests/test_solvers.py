import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.energy import EnergyModel
from uqrv.metrics import evaluate_plan
from uqrv.scenario import Scenario, Stop, Tower, Weather, generate_scenario
import uqrv.solvers as solvers
from uqrv.solvers import Plan, PlanSortie, PlanTask, _schedule_tasks_and_sorties, _weighted_permutation, solve


class SolverTests(unittest.TestCase):
    def test_solver_returns_all_towers_once(self):
        scenario = generate_scenario(size="S", seed=4)
        plan = solve(scenario, method="uq_rv_alns", energy_model=EnergyModel(), iterations=20)
        visited = sorted(task.tower_id for task in plan.tasks)
        self.assertEqual(visited, sorted(t.id for t in scenario.towers))

    def test_metric_aware_portfolio_selects_lower_reported_rwct_candidate(self):
        scenario = Scenario(
            id="metric_portfolio_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 1.0, 0.0, risk=0.1, value=5.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 1.1, 0.0, risk=1.0, value=100.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        _order, tasks, sorties, diagnostics = solvers._select_metric_aware_schedule(
            scenario=scenario,
            candidate_orders=[
                ("cache_best", [scenario.towers[0], scenario.towers[1]]),
                ("risk_first", [scenario.towers[1], scenario.towers[0]]),
            ],
            stop_picker=solvers._pick_value_aware,
            energy_model=energy,
            quantile=True,
            allow_multi_tower_sorties=True,
        )

        self.assertEqual(diagnostics["selected_portfolio_candidate"], "risk_first")
        self.assertEqual(len(sorties), 1)
        self.assertEqual([task.tower_id for task in tasks], [1, 0])

    def test_operator_portfolio_uses_deterministic_component_seed(self):
        scenario = generate_scenario(size="S", seed=7)
        disturbed_rng = solvers.Random(99)
        for _ in range(20):
            disturbed_rng.random()
        expected_point = solvers._local_improvement_order(
            scenario.towers,
            scenario.stops,
            solvers.Random(3),
            iterations=12,
            value_weight=0.2,
        )

        portfolio = solvers._operator_portfolio_orders(
            scenario=scenario,
            search_order=list(reversed(scenario.towers)),
            schedule_stop_picker=solvers._pick_value_aware,
            use_quantile=True,
            iterations=12,
            selection_seed=3,
            priority_scores=solvers.scaled_risk_value_priority_map(scenario.towers),
        )

        point_order = next(order for label, order, *_ in portfolio if label == "point_local")
        self.assertEqual(
            [tower.id for tower in point_order],
            [tower.id for tower in expected_point],
        )

    def test_quantile_solver_groups_nearby_towers_into_multi_tower_sorties(self):
        scenario = Scenario(
            id="multi_tower_sortie_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 1.0, 0.0, risk=0.3, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 1.2, 0.0, risk=0.4, value=12.0, service_time=1.0, payload=0.1, segment=0),
                Tower(2, 1.4, 0.0, risk=0.5, value=14.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        plan = solve(scenario, method="alns_full", energy_model=energy, iterations=1, seed=0)

        self.assertEqual(sorted(task.tower_id for task in plan.tasks), [0, 1, 2])
        self.assertLess(len(plan.sorties), len(plan.tasks))
        self.assertEqual(plan.sorties[0].tower_ids, [2, 1, 0])
        self.assertEqual(plan.sorties[0].stop_id, 0)
        self.assertEqual(plan.sorties[0].uav_id, 0)
        self.assertGreater(plan.sorties[0].return_time, plan.tasks[-1].finish)

    def test_scheduler_groups_same_stop_towers_separated_by_priority_order(self):
        scenario = Scenario(
            id="nonadjacent_same_stop_sortie_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 1.0, 0.0, risk=0.3, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 60.0, 0.0, risk=0.0, value=1.0, service_time=1.0, payload=0.1, segment=1),
                Tower(2, 1.2, 0.0, risk=0.5, value=20.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0), Stop(1, 60.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        def nearest_stop(tower, stops, _energy_model, _scenario, _quantile):
            return min(stops, key=lambda stop: abs(stop.x - tower.x))

        tasks, sorties = _schedule_tasks_and_sorties(
            scenario,
            scenario.towers,
            nearest_stop,
            energy,
            quantile=True,
            allow_multi_tower_sorties=True,
        )

        self.assertEqual(sorted(task.tower_id for task in tasks), [0, 1, 2])
        self.assertEqual(len(sorties), 2)
        self.assertIn([0, 2], [sortie.tower_ids for sortie in sorties])

    def test_scheduler_groups_corridor_towers_when_combined_path_saves_distance(self):
        scenario = Scenario(
            id="corridor_spacing_sortie_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 1.0, 0.0, risk=0.3, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 3.5, 0.0, risk=0.2, value=10.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        plan = solve(scenario, method="alns_full", energy_model=energy, iterations=1, seed=0)

        self.assertEqual(len(plan.sorties), 1)
        self.assertEqual(plan.sorties[0].tower_ids, [0, 1])

    def test_schedule_completion_includes_vehicle_travel_between_stops(self):
        scenario = Scenario(
            id="vehicle_travel_counterexample",
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
        energy = EnergyModel(
            battery_capacity=scenario.battery_capacity,
            reserve_ratio=0.0,
            drone_speed_kmph=scenario.drone_speed_kmph,
        )

        plan = solve(scenario, method="greedy_nearest", energy_model=energy, iterations=1)
        task_by_id = {task.tower_id: task for task in plan.tasks}

        self.assertGreaterEqual(task_by_id[1].start, task_by_id[0].finish + 60.0 - 1e-6)
        self.assertEqual(task_by_id[1].vehicle_id, 0)

    def test_metrics_include_required_keys(self):
        scenario = generate_scenario(size="S", seed=5)
        plan = solve(scenario, method="greedy_nearest", energy_model=EnergyModel(), iterations=5)
        metrics = evaluate_plan(scenario, plan, EnergyModel())
        for key in [
            "makespan",
            "expected_energy",
            "infeasible_sortie_rate",
            "risk_weighted_completion_time",
            "feasible_top_risk_coverage",
        ]:
            self.assertIn(key, metrics)

    def test_feasible_top_risk_coverage_excludes_energy_infeasible_early_tasks(self):
        scenario = Scenario(
            id="metric_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 0.0, 0.0, risk=1.0, value=100.0, service_time=1.0, payload=1.0, segment=0),
                Tower(1, 1.0, 0.0, risk=0.1, value=10.0, service_time=1.0, payload=1.0, segment=0),
                Tower(2, 2.0, 0.0, risk=0.1, value=10.0, service_time=1.0, payload=1.0, segment=0),
                Tower(3, 3.0, 0.0, risk=0.1, value=10.0, service_time=1.0, payload=1.0, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=40.0,
            battery_capacity=100.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        plan = Plan(
            method="manual",
            tasks=[
                PlanTask(0, 0, 0, 0.0, 1.0, 10.0, 95.0, False, 100.0, 1.0),
                PlanTask(1, 0, 0, 1.0, 2.0, 10.0, 10.0, True, 10.0, 0.1),
                PlanTask(2, 0, 0, 2.0, 3.0, 10.0, 10.0, True, 10.0, 0.1),
                PlanTask(3, 0, 0, 3.0, 4.0, 10.0, 10.0, True, 10.0, 0.1),
            ],
            runtime=0.0,
            objective=0.0,
        )
        metrics = evaluate_plan(scenario, plan, EnergyModel(battery_capacity=100.0, reserve_ratio=0.1))
        self.assertEqual(metrics["top_risk_coverage"], 1.0)
        self.assertEqual(metrics["feasible_top_risk_coverage"], 0.0)

    def test_metrics_use_sortie_energy_when_sortie_records_exist(self):
        scenario = Scenario(
            id="sortie_metric_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 1.0, 0.0, risk=0.2, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 1.2, 0.0, risk=0.3, value=10.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=100.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        plan = Plan(
            method="manual",
            tasks=[
                PlanTask(0, 0, 0, 0.5, 1.5, 20.0, 40.0, True, 10.0, 0.2, sortie_id=0),
                PlanTask(1, 0, 0, 2.0, 3.0, 20.0, 40.0, True, 10.0, 0.3, sortie_id=0),
            ],
            runtime=0.0,
            objective=0.0,
            sorties=[
                PlanSortie(
                    sortie_id=0,
                    tower_ids=[0, 1],
                    stop_id=0,
                    uav_id=0,
                    vehicle_id=0,
                    start=0.0,
                    return_time=4.0,
                    energy_mean=30.0,
                    energy_q95=80.0,
                    feasible=True,
                    vehicle_departure=4.0,
                )
            ],
        )

        metrics = evaluate_plan(scenario, plan, EnergyModel(battery_capacity=100.0, reserve_ratio=0.1))

        self.assertEqual(metrics["expected_energy"], 30.0)
        self.assertEqual(metrics["infeasible_sortie_rate"], 0.0)
        self.assertEqual(metrics["sortie_count"], 1)
        self.assertEqual(metrics["avg_towers_per_sortie"], 2.0)

    def test_metrics_use_vehicle_route_with_return_to_depot(self):
        scenario = Scenario(
            id="metric_vehicle_route_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 0.0, 0.0, risk=0.1, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 60.0, 0.0, risk=0.1, value=10.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0), Stop(1, 60.0, 0.0)],
            vehicle_count=1,
            uav_count=2,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        plan = Plan(
            method="manual",
            tasks=[
                PlanTask(0, 0, 0, 0.0, 1.0, 10.0, 10.0, True, 10.0, 0.1, vehicle_id=0, vehicle_departure=1.0),
                PlanTask(
                    1,
                    1,
                    1,
                    61.0,
                    62.0,
                    10.0,
                    10.0,
                    True,
                    10.0,
                    0.1,
                    vehicle_id=0,
                    vehicle_arrival=61.0,
                    vehicle_departure=62.0,
                    road_travel=60.0,
                ),
            ],
            runtime=0.0,
            objective=0.0,
        )

        metrics = evaluate_plan(scenario, plan, EnergyModel(battery_capacity=10000.0, reserve_ratio=0.0))
        self.assertEqual(metrics["total_vehicle_distance"], 120.0)
        self.assertEqual(metrics["makespan"], 122.0)

    def test_metrics_use_unified_normalized_risk_value_priority(self):
        scenario = Scenario(
            id="metric_priority_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 0.0, 0.0, risk=1.0, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 1.0, 0.0, risk=0.0, value=20.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        plan = Plan(
            method="manual",
            tasks=[
                PlanTask(0, 0, 0, 0.0, 10.0, 10.0, 10.0, True, 10.0, 1.0),
                PlanTask(1, 0, 0, 10.0, 20.0, 10.0, 10.0, True, 20.0, 0.0),
            ],
            runtime=0.0,
            objective=0.0,
        )

        metrics = evaluate_plan(scenario, plan, EnergyModel(battery_capacity=10000.0, reserve_ratio=0.0))
        self.assertEqual(metrics["risk_weighted_completion_time"], 20.0)
        self.assertEqual(metrics["top_risk_coverage"], 0.0)

    def test_proposed_solver_orders_by_unified_normalized_priority(self):
        scenario = Scenario(
            id="solver_priority_counterexample",
            size="S",
            seed=0,
            towers=[
                Tower(0, 0.0, 0.0, risk=1.0, value=10.0, service_time=1.0, payload=0.1, segment=0),
                Tower(1, 0.1, 0.0, risk=0.0, value=20.0, service_time=1.0, payload=0.1, segment=0),
            ],
            stops=[Stop(0, 0.0, 0.0)],
            vehicle_count=1,
            uav_count=1,
            vehicle_speed_kmph=60.0,
            drone_speed_kmph=120.0,
            battery_capacity=10000.0,
            weather=Weather(0.0, 0.0, 22.0, 0.0),
        )
        plan = solve(
            scenario,
            method="uq_rv_alns",
            energy_model=EnergyModel(battery_capacity=10000.0, reserve_ratio=0.0),
            iterations=1,
            seed=0,
        )
        task_by_id = {task.tower_id: task for task in plan.tasks}

        self.assertLess(task_by_id[1].finish, task_by_id[0].finish)

    def test_uq_rv_prioritizes_risk_value_better_than_point_alns(self):
        scenario = generate_scenario(size="S", seed=0)
        energy = EnergyModel()
        point = solve(scenario, method="alns_point", energy_model=energy, iterations=50, seed=0)
        value = solve(scenario, method="greedy_value", energy_model=energy, iterations=50, seed=0)
        proposed = solve(scenario, method="uq_rv_alns", energy_model=energy, iterations=50, seed=0)
        point_metrics = evaluate_plan(scenario, point, energy)
        value_metrics = evaluate_plan(scenario, value, energy)
        proposed_metrics = evaluate_plan(scenario, proposed, energy)
        self.assertLessEqual(
            proposed_metrics["risk_weighted_completion_time"],
            point_metrics["risk_weighted_completion_time"],
        )
        self.assertLessEqual(
            proposed_metrics["risk_weighted_completion_time"],
            value_metrics["risk_weighted_completion_time"],
        )

    def test_uq_rv_reduces_high_uncertainty_violations(self):
        scenario = generate_scenario(size="M", seed=0, uncertainty="high")
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)
        point = solve(scenario, method="alns_point", energy_model=energy, iterations=40, seed=0)
        proposed = solve(scenario, method="uq_rv_alns", energy_model=energy, iterations=40, seed=0)
        point_metrics = evaluate_plan(scenario, point, energy)
        proposed_metrics = evaluate_plan(scenario, proposed, energy)
        self.assertLess(
            proposed_metrics["infeasible_sortie_rate"],
            point_metrics["infeasible_sortie_rate"],
        )

    def test_full_alns_returns_all_towers_and_operator_diagnostics(self):
        scenario = generate_scenario(size="S", seed=8, uncertainty="high")
        plan = solve(scenario, method="alns_full", energy_model=EnergyModel(), iterations=25, seed=13)
        visited = sorted(task.tower_id for task in plan.tasks)
        self.assertEqual(visited, sorted(t.id for t in scenario.towers))
        self.assertIsNotNone(plan.diagnostics)
        diagnostics = plan.diagnostics or {}
        self.assertEqual(diagnostics["iterations"], 25)
        self.assertGreater(diagnostics["accepted_moves"], 0)
        self.assertIn("random_removal", diagnostics["destroy_uses"])
        self.assertIn("greedy_insert_repair", diagnostics["repair_uses"])
        self.assertIn("energy_minimum_insert_repair", diagnostics["repair_uses"])
        self.assertIn("synchronization_aware_insert_repair", diagnostics["repair_uses"])
        self.assertEqual(plan.method, "alns_full")

    def test_full_alns_is_reproducible_with_same_seed(self):
        scenario = generate_scenario(size="S", seed=9)
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)
        first = solve(scenario, method="alns_full", energy_model=energy, iterations=20, seed=21)
        second = solve(scenario, method="alns_full", energy_model=energy, iterations=20, seed=21)
        self.assertEqual([task.tower_id for task in first.tasks], [task.tower_id for task in second.tasks])
        self.assertEqual(first.diagnostics["destroy_uses"], second.diagnostics["destroy_uses"])
        self.assertEqual(first.diagnostics["repair_uses"], second.diagnostics["repair_uses"])

    def test_full_alns_records_cached_score_evaluations(self):
        scenario = generate_scenario(size="M", seed=10)
        plan = solve(scenario, method="alns_full", energy_model=EnergyModel(), iterations=5, seed=2)
        diagnostics = plan.diagnostics or {}
        self.assertEqual(diagnostics["score_cache_size"], len(scenario.towers))
        self.assertEqual(diagnostics["objective_evaluations"], 6)
        self.assertLessEqual(diagnostics["repair_position_evaluations"], 5 * len(scenario.towers))

    def test_full_alns_repair_ablation_aliases_disable_named_repair_operator(self):
        scenario = generate_scenario(size="S", seed=11, uncertainty="high")
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)

        no_energy = solve(
            scenario,
            method="alns_full_no_energy_repair",
            energy_model=energy,
            iterations=18,
            seed=3,
        )
        no_sync = solve(
            scenario,
            method="alns_full_no_sync_repair",
            energy_model=energy,
            iterations=18,
            seed=3,
        )

        no_energy_uses = no_energy.diagnostics["repair_uses"]
        no_sync_uses = no_sync.diagnostics["repair_uses"]
        self.assertEqual(no_energy_uses["energy_minimum_insert_repair"], 0)
        self.assertEqual(no_sync_uses["synchronization_aware_insert_repair"], 0)
        self.assertIn("energy_minimum_insert_repair", no_energy.diagnostics["disabled_repair_operators"])
        self.assertIn("synchronization_aware_insert_repair", no_sync.diagnostics["disabled_repair_operators"])
        self.assertEqual(sorted(task.tower_id for task in no_energy.tasks), sorted(t.id for t in scenario.towers))
        self.assertEqual(sorted(task.tower_id for task in no_sync.tasks), sorted(t.id for t in scenario.towers))

    def test_full_alns_controlled_ablation_aliases_keep_operator_search(self):
        scenario = generate_scenario(size="S", seed=12, uncertainty="high")
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)

        no_uq = solve(scenario, method="alns_full_no_uq", energy_model=energy, iterations=12, seed=4)
        no_risk = solve(scenario, method="alns_full_no_risk_value", energy_model=energy, iterations=12, seed=4)
        no_adaptive = solve(scenario, method="alns_full_no_adaptive", energy_model=energy, iterations=12, seed=4)

        self.assertFalse(no_uq.diagnostics["use_quantile"])
        self.assertEqual(no_uq.diagnostics["iterations"], 12)
        self.assertEqual(no_uq.diagnostics["objective_evaluations"], 13)

        self.assertTrue(no_risk.diagnostics["use_quantile"])
        self.assertEqual(no_risk.diagnostics["risk_value_weight"], 0.0)
        self.assertEqual(no_risk.diagnostics["objective_evaluations"], 13)

        self.assertFalse(no_adaptive.diagnostics["adaptive_enabled"])
        self.assertEqual(no_adaptive.diagnostics["objective_evaluations"], 13)

    def test_value_aware_stop_score_has_no_tower_constant_term(self):
        from uqrv.solvers import _value_aware_stop_score

        low_value_score = _value_aware_stop_score(bound=20.0, duration=5.0, feasible=True)
        high_value_score = _value_aware_stop_score(bound=20.0, duration=5.0, feasible=True)
        self.assertEqual(low_value_score, high_value_score)

    def test_ga_and_aco_record_population_search_diagnostics(self):
        scenario = generate_scenario(size="S", seed=14, uncertainty="medium")
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)

        ga = solve(scenario, method="ga", energy_model=energy, iterations=12, seed=5)
        aco = solve(scenario, method="aco", energy_model=energy, iterations=12, seed=5)

        self.assertEqual(sorted(task.tower_id for task in ga.tasks), sorted(t.id for t in scenario.towers))
        self.assertEqual(sorted(task.tower_id for task in aco.tasks), sorted(t.id for t in scenario.towers))
        self.assertEqual(ga.diagnostics["baseline_family"], "genetic_order_search")
        self.assertEqual(aco.diagnostics["baseline_family"], "ant_colony_order_search")
        self.assertGreater(ga.diagnostics["candidate_evaluations"], 12)
        self.assertGreater(aco.diagnostics["candidate_evaluations"], 12)

    def test_external_public_baselines_are_not_alns_variants(self):
        scenario = generate_scenario(size="S", seed=17, uncertainty="medium")
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)
        expected_families = {
            "simulated_annealing": "simulated_annealing_order_search",
            "tabu_search": "tabu_swap_insert_search",
            "variable_neighborhood_search": "variable_neighborhood_search",
            "hybrid_genetic_search": "hybrid_genetic_vns_search",
        }

        for method, family in expected_families.items():
            plan = solve(scenario, method=method, energy_model=energy, iterations=8, seed=5)
            self.assertEqual(sorted(task.tower_id for task in plan.tasks), sorted(t.id for t in scenario.towers))
            self.assertEqual(plan.diagnostics["baseline_family"], family)
            self.assertNotIn("implementation_family", plan.diagnostics)
            self.assertGreater(plan.diagnostics["candidate_evaluations"], 0)

    def test_fixed_alns_uses_operator_pool_without_uq_or_risk_value(self):
        scenario = generate_scenario(size="S", seed=15, uncertainty="medium")
        energy = EnergyModel(battery_capacity=scenario.battery_capacity)

        plan = solve(scenario, method="alns_fixed", energy_model=energy, iterations=10, seed=4)

        self.assertEqual(sorted(task.tower_id for task in plan.tasks), sorted(t.id for t in scenario.towers))
        self.assertEqual(plan.method, "alns_fixed")
        self.assertFalse(plan.diagnostics["use_quantile"])
        self.assertEqual(plan.diagnostics["risk_value_weight"], 0.0)
        self.assertGreater(plan.diagnostics["accepted_moves"], 0)

    def test_weighted_permutation_returns_each_tower_once(self):
        scenario = generate_scenario(size="S", seed=16, uncertainty="medium")
        order = _weighted_permutation(
            scenario.towers,
            [1.0 + tower.risk for tower in scenario.towers],
            seed=17,
        )

        self.assertEqual(sorted(tower.id for tower in order), sorted(tower.id for tower in scenario.towers))


if __name__ == "__main__":
    unittest.main()
