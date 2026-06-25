from __future__ import annotations

import argparse
import math
import sys
from dataclasses import replace
from pathlib import Path
from random import Random
from time import perf_counter
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.candidate_stops import generate_clustered_stops, screen_service_pairs, with_candidate_stops
from uqrv.energy import EnergyModel
from uqrv.energy_surrogate import (
    SimulationTrainedEnergySurrogate,
    generate_energy_training_samples,
    synthetic_observed_energy,
)
from uqrv.io_utils import ensure_experiment_dirs, summarize_rows, write_json, write_markdown, write_rows_csv
from uqrv.metrics import evaluate_plan
from uqrv.milp_reference import solve_milp_reference
from uqrv.proposal_design import (
    PROPOSAL_SIZE_CONFIGS,
    ProposalSizeConfig,
    build_proposal_experiment_matrix,
    generate_custom_scenario,
    generate_proposal_scenario,
)
from uqrv.scenario import Weather
from uqrv.solvers import solve


RUN_METRICS = [
    "makespan",
    "total_vehicle_distance",
    "expected_energy",
    "energy_violation_rate",
    "infeasible_sortie_rate",
    "risk_weighted_completion_time",
    "top_risk_coverage",
    "feasible_top_risk_coverage",
    "sortie_count",
    "avg_towers_per_sortie",
    "missed_value",
    "solver_runtime",
    "objective_value",
    "milp_gap",
    "milp_optimizes_rwct",
    "optimality_gap_pct",
    "total_candidate_pairs",
    "screened_pair_count",
    "candidate_pair_reduction",
    "feasible_candidate_pairs",
    "service_graph_pattern_count",
    "service_graph_feasible_count",
    "selected_sortie_count",
    "missed_service_count",
    "duplicate_service_count",
    "objective_rwct",
    "objective_makespan",
    "objective_ground_travel",
    "objective_q95_energy",
    "objective_missed_penalty",
    "objective_duplicate_penalty",
    "objective_total",
    "alns_accepted_moves",
    "alns_improving_moves",
    "alns_rejected_moves",
    "alns_best_updates",
    "alns_objective_evaluations",
    "alns_score_cache_size",
    "alns_repair_position_evaluations",
    "alns_portfolio_candidate_count",
    "alns_selected_portfolio_infeasible_count",
    "alns_selected_portfolio_rwct",
    "alns_selected_portfolio_makespan",
    "destroy_random_removal_uses",
    "destroy_worst_energy_removal_uses",
    "destroy_shaw_related_removal_uses",
    "destroy_path_segment_removal_uses",
    "destroy_uav_chain_removal_uses",
    "repair_greedy_insert_repair_uses",
    "repair_regret_insert_repair_uses",
    "repair_energy_minimum_insert_repair_uses",
    "repair_synchronization_aware_insert_repair_uses",
    "baseline_candidate_evaluations",
    "baseline_generations",
    "baseline_population_size",
    "baseline_ant_count",
    "baseline_best_order_score",
    "alns_risk_value_weight",
    "alns_adaptive_enabled",
]

PREDICTION_METRICS = ["mae", "rmse", "mape", "coverage_95", "false_feasible_rate", "training_sample_count"]

_TRAINED_SURROGATE: SimulationTrainedEnergySurrogate | None = None
_TRAINING_SAMPLE_COUNT = 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="stop_batch_model_20260606")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--only", default="ALL")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    seed_range = range(2 if args.quick else args.seeds)
    matrix = build_proposal_experiment_matrix(seed_range, quick=args.quick)
    selected = list(matrix) if args.only.upper() == "ALL" else [args.only]
    for experiment_id in selected:
        start = perf_counter()
        if experiment_id == "P3_pinn_prediction_accuracy":
            rows = run_prediction_experiment(matrix[experiment_id])
            group_keys = ["prediction_model", "size", "uncertainty"]
            metrics = PREDICTION_METRICS
        else:
            rows = run_solver_experiment(matrix[experiment_id])
            if experiment_id == "P8_sensitivity":
                group_keys = [
                    "sensitivity_factor",
                    "sensitivity_level",
                    "method",
                    "candidate_mode",
                    "size",
                    "tower_count",
                    "uncertainty",
                ]
            else:
                group_keys = ["method", "candidate_mode", "size", "tower_count", "stop_count", "uncertainty"]
            metrics = RUN_METRICS
        write_outputs(experiment_id, args.run_id, rows, group_keys, metrics)
        print(f"{experiment_id}: wrote {len(rows)} rows in {perf_counter() - start:.2f}s")
    return 0


def run_solver_experiment(config_rows: Iterable[dict]) -> List[dict]:
    rows: List[dict] = []
    for cfg in config_rows:
        scenario = _scenario_from_row(cfg)
        scenario = _apply_scenario_overrides(scenario, cfg)
        energy_model = _energy_model_from_row(scenario, cfg)
        scenario, candidate_metrics = _apply_candidate_stop_mode(scenario, cfg, energy_model)
        method = cfg["method"]
        info = {"status": "not_milp", "relative_gap": 0.0}
        if method == "milp_highs":
            plan, info = solve_milp_reference(scenario, energy_model, time_limit=90)
        else:
            solver_method, iterations = _solver_mapping(method, scenario.size)
            iterations = int(cfg.get("iteration_budget", iterations))
            plan = solve(
                scenario,
                method=solver_method,
                energy_model=energy_model,
                iterations=iterations,
                seed=cfg["seed"],
            )
        metrics = evaluate_plan(scenario, plan, energy_model)
        metrics["objective_value"] = plan.objective
        metrics["milp_gap"] = info["relative_gap"]
        diagnostic_metrics = _alns_diagnostic_metrics(plan)
        rows.append(
            {
                **cfg,
                "scenario_id": scenario.id,
                "milp_status": info["status"],
                "milp_reference_scope": info.get("reference_scope", "not_milp"),
                "milp_optimizes_rwct": bool(info.get("optimizes_rwct", False)),
                "milp_completion_time_scope": info.get("completion_time_scope", "not_milp"),
                **candidate_metrics,
                **diagnostic_metrics,
                **metrics,
            }
        )

    _attach_small_instance_gaps(rows)
    return rows


def run_prediction_experiment(config_rows: Iterable[dict]) -> List[dict]:
    rows: List[dict] = []
    for cfg in config_rows:
        scenario = _scenario_from_row(cfg)
        model_name = cfg["prediction_model"]
        metrics = _prediction_metrics(scenario, model_name, seed=cfg["seed"])
        rows.append({**cfg, "scenario_id": scenario.id, **metrics})
    return rows


def write_outputs(experiment_id: str, run_id: str, rows: List[dict], group_keys: List[str], metrics: List[str]) -> None:
    root = ensure_experiment_dirs(PROJECT_ROOT / "results" / "experiments", experiment_id, run_id)
    raw_path = root / "raw_data" / f"{experiment_id}_{run_id}_raw.csv"
    summary_path = root / "analysis_data" / f"{experiment_id}_{run_id}_summary.csv"
    report_path = root / "analysis_data" / f"{experiment_id}_{run_id}_summary.md"
    json_path = root / "analysis_data" / f"{experiment_id}_{run_id}_run_summary.json"
    summary = summarize_rows(rows, group_keys, metrics)
    write_rows_csv(raw_path, rows)
    write_rows_csv(summary_path, summary)
    write_markdown(report_path, f"{experiment_id} Summary", summary)
    write_json(
        json_path,
        {
            "experiment_id": experiment_id,
            "run_id": run_id,
            "row_count": len(rows),
            "raw_data": str(raw_path),
            "summary_csv": str(summary_path),
            "summary_md": str(report_path),
        },
    )
    write_markdown(root / "runs" / run_id / "README.md", f"{experiment_id} {run_id}", summary)


def _scenario_from_row(cfg: dict):
    if cfg["size"] == "CASE":
        config = ProposalSizeConfig("CASE", cfg["tower_count"], cfg["stop_count"], cfg["vehicle_count"], cfg["uavs_per_vehicle"], "case study")
        return generate_custom_scenario(config, seed=cfg["seed"], uncertainty=cfg["uncertainty"])
    size = cfg["size"]
    variant = cfg["variant_index"]
    return generate_proposal_scenario(size, variant, seed=cfg["seed"], uncertainty=cfg["uncertainty"])


def _apply_scenario_overrides(scenario, cfg: dict):
    changes = {}
    if "uav_count_override" in cfg:
        changes["uav_count"] = int(cfg["uav_count_override"])
    if not changes:
        return scenario
    suffix = "_".join(f"{key}{value}" for key, value in sorted(changes.items()))
    return replace(scenario, id=f"{scenario.id}_{suffix}", **changes)


def _energy_model_from_row(scenario, cfg: dict) -> EnergyModel:
    return EnergyModel(
        battery_capacity=scenario.battery_capacity,
        reserve_ratio=float(cfg.get("reserve_ratio", 0.12)),
        quantile_z=float(cfg.get("quantile_z", 1.645)),
    )


def _apply_candidate_stop_mode(scenario, cfg: dict, energy_model: EnergyModel):
    mode = cfg.get("candidate_mode", "direct")
    total_pairs = len(scenario.towers) * len(scenario.stops)
    if mode == "direct":
        feasible_pairs = 0
        for tower in scenario.towers:
            for stop in scenario.stops:
                estimate = energy_model.estimate(stop, tower, scenario.weather)
                feasible_pairs += int(energy_model.is_feasible(estimate, use_quantile=True))
        return scenario, {
            "total_candidate_pairs": total_pairs,
            "screened_pair_count": total_pairs,
            "candidate_pair_reduction": 0.0,
            "feasible_candidate_pairs": feasible_pairs,
        }
    stop_set = generate_clustered_stops(
        scenario.towers,
        target_count=cfg["stop_count"],
        method=mode,
        seed=cfg["seed"],
    )
    clustered = with_candidate_stops(scenario, stop_set)
    screen = screen_service_pairs(
        clustered,
        clustered.stops,
        energy_model,
        nearest_per_tower=int(cfg.get("nearest_per_tower", 3)),
        use_quantile=True,
    )
    return clustered, {
        "total_candidate_pairs": screen.total_pairs,
        "screened_pair_count": screen.screened_pair_count,
        "candidate_pair_reduction": screen.reduction_ratio,
        "feasible_candidate_pairs": screen.feasible_pair_count,
    }


def _alns_diagnostic_metrics(plan) -> Dict[str, object]:
    diagnostics = plan.diagnostics or {}
    destroy_uses = diagnostics.get("destroy_uses", {})
    repair_uses = diagnostics.get("repair_uses", {})
    return {
        "baseline_family": diagnostics.get("baseline_family", ""),
        "baseline_candidate_evaluations": float(diagnostics.get("candidate_evaluations", 0.0)),
        "baseline_generations": float(diagnostics.get("generations", 0.0)),
        "baseline_population_size": float(diagnostics.get("population_size", 0.0)),
        "baseline_ant_count": float(diagnostics.get("ant_count", 0.0)),
        "baseline_best_order_score": float(diagnostics.get("best_order_score", 0.0)),
        "implementation_family": diagnostics.get("implementation_family", ""),
        "service_graph_pattern_count": float(diagnostics.get("service_graph_pattern_count", 0.0)),
        "service_graph_feasible_count": float(diagnostics.get("service_graph_feasible_count", 0.0)),
        "selected_sortie_count": float(diagnostics.get("selected_sortie_count", 0.0)),
        "missed_service_count": float(diagnostics.get("missed_service_count", 0.0)),
        "duplicate_service_count": float(diagnostics.get("duplicate_service_count", 0.0)),
        "objective_rwct": float(diagnostics.get("objective_rwct", 0.0)),
        "objective_makespan": float(diagnostics.get("objective_makespan", 0.0)),
        "objective_ground_travel": float(diagnostics.get("objective_ground_travel", 0.0)),
        "objective_q95_energy": float(diagnostics.get("objective_q95_energy", 0.0)),
        "objective_missed_penalty": float(diagnostics.get("objective_missed_penalty", 0.0)),
        "objective_duplicate_penalty": float(diagnostics.get("objective_duplicate_penalty", 0.0)),
        "objective_total": float(diagnostics.get("objective_total", 0.0)),
        "alns_use_quantile": bool(diagnostics.get("use_quantile", False)),
        "alns_risk_value_weight": float(diagnostics.get("risk_value_weight", 0.0)),
        "alns_adaptive_enabled": bool(diagnostics.get("adaptive_enabled", False)),
        "alns_accepted_moves": float(diagnostics.get("accepted_moves", 0.0)),
        "alns_improving_moves": float(diagnostics.get("improving_moves", 0.0)),
        "alns_rejected_moves": float(diagnostics.get("rejected_moves", 0.0)),
        "alns_best_updates": float(diagnostics.get("best_updates", 0.0)),
        "alns_objective_evaluations": float(diagnostics.get("objective_evaluations", 0.0)),
        "alns_score_cache_size": float(diagnostics.get("score_cache_size", 0.0)),
        "alns_repair_position_evaluations": float(diagnostics.get("repair_position_evaluations", 0.0)),
        "alns_portfolio_candidate_count": float(diagnostics.get("portfolio_candidate_count", 0.0)),
        "alns_selected_portfolio_candidate": diagnostics.get("selected_portfolio_candidate", ""),
        "alns_selected_portfolio_infeasible_count": float(
            diagnostics.get("selected_portfolio_infeasible_count", 0.0)
        ),
        "alns_selected_portfolio_rwct": float(diagnostics.get("selected_portfolio_rwct", 0.0)),
        "alns_selected_portfolio_makespan": float(diagnostics.get("selected_portfolio_makespan", 0.0)),
        "destroy_random_removal_uses": float(destroy_uses.get("random_removal", 0.0)),
        "destroy_worst_energy_removal_uses": float(destroy_uses.get("worst_energy_removal", 0.0)),
        "destroy_shaw_related_removal_uses": float(destroy_uses.get("shaw_related_removal", 0.0)),
        "destroy_path_segment_removal_uses": float(destroy_uses.get("path_segment_removal", 0.0)),
        "destroy_uav_chain_removal_uses": float(destroy_uses.get("uav_chain_removal", 0.0)),
        "repair_greedy_insert_repair_uses": float(repair_uses.get("greedy_insert_repair", 0.0)),
        "repair_regret_insert_repair_uses": float(repair_uses.get("regret_insert_repair", 0.0)),
        "repair_energy_minimum_insert_repair_uses": float(repair_uses.get("energy_minimum_insert_repair", 0.0)),
        "repair_synchronization_aware_insert_repair_uses": float(
            repair_uses.get("synchronization_aware_insert_repair", 0.0)
        ),
    }


def _solver_mapping(method: str, size: str) -> tuple[str, int]:
    iteration_by_size = {"S": 80, "M": 100, "L": 60, "CASE": 80}
    iterations = iteration_by_size.get(size, 80)
    mapping = {
        "greedy_nearest": ("greedy_nearest", 0),
        "ga": ("ga", max(40, iterations // 2)),
        "aco": ("aco", max(40, iterations // 2)),
        "alns_fixed": ("alns_fixed", iterations),
        "alns_pinn": ("alns_point", iterations),
        "alns_pinn_uq": ("uq_alns", iterations),
        "alns_pinn_full": ("alns_full", iterations),
        "no_pinn": ("alns_fixed", iterations),
        "no_adaptive": ("alns_full_no_adaptive", iterations),
        "no_uq": ("alns_full_no_uq", iterations),
        "no_risk_value": ("alns_full_no_risk_value", iterations),
        "no_energy_repair": ("alns_full_no_energy_repair", iterations),
        "no_sync_repair": ("alns_full_no_sync_repair", iterations),
        "no_clustering": ("alns_full", iterations),
    }
    return mapping[method]


def _attach_small_instance_gaps(rows: List[dict]) -> None:
    by_case: Dict[tuple, float] = {}
    for row in rows:
        if row["method"] == "milp_highs":
            by_case[(row["tower_count"], row["stop_count"], row["seed"], row["uncertainty"])] = row["makespan"]
    for row in rows:
        key = (row["tower_count"], row["stop_count"], row["seed"], row["uncertainty"])
        ref = by_case.get(key)
        if ref and row["method"] != "milp_highs":
            row["optimality_gap_pct"] = max(0.0, (row["makespan"] - ref) / abs(ref) * 100.0)
        elif row["method"] == "milp_highs":
            row["optimality_gap_pct"] = 0.0
        else:
            row["optimality_gap_pct"] = 0.0


def _prediction_metrics(scenario, model_name: str, seed: int) -> dict:
    rng = Random(9001 + seed + len(scenario.towers))
    energy_model = EnergyModel(battery_capacity=scenario.battery_capacity)
    nominal_weather = Weather(0.5, 0.0, 22.0, scenario.weather.uncertainty)
    evidence_level = "simulation_calibrated"
    training_status = "not_field_trained"
    training_sample_count = 0
    errors = []
    squared = []
    ape = []
    covered = 0
    false_feasible = 0
    total = 0
    limit = energy_model.battery_capacity * (1.0 - energy_model.reserve_ratio)
    for tower in scenario.towers:
        stop = min(scenario.stops, key=lambda s: (s.x - tower.x) ** 2 + (s.y - tower.y) ** 2)
        actual_est = energy_model.estimate(stop, tower, scenario.weather)
        true = synthetic_observed_energy(
            actual_est.mean_energy,
            tower,
            scenario.weather,
            actual_est.wind_alignment,
            rng,
        )
        if model_name == "fixed_physics":
            pred_est = energy_model.estimate(stop, tower, nominal_weather)
            pred = pred_est.mean_energy
            std = max(2.5, pred * 0.08)
        elif model_name == "point_pinn":
            pred = actual_est.mean_energy * (1.0 + rng.gauss(0.0, 0.025 + 0.05 * scenario.weather.uncertainty))
            std = max(2.5, pred * 0.10)
        elif model_name == "probabilistic_pinn":
            surrogate = _default_trained_energy_surrogate()
            prediction = surrogate.predict(stop, tower, scenario.weather)
            pred = prediction.energy_mean
            std = prediction.energy_std
            evidence_level = prediction.evidence_level
            training_status = prediction.training_status
            training_sample_count = _TRAINING_SAMPLE_COUNT
        else:
            raise ValueError(model_name)
        err = pred - true
        errors.append(abs(err))
        squared.append(err * err)
        ape.append(abs(err) / true)
        covered += int(true <= pred + 1.645 * std)
        false_feasible += int(pred <= limit and true > limit)
        total += 1
    return {
        "mae": sum(errors) / total,
        "rmse": math.sqrt(sum(squared) / total),
        "mape": sum(ape) / total,
        "coverage_95": covered / total,
        "false_feasible_rate": false_feasible / total,
        "prediction_evidence_level": evidence_level,
        "prediction_training_status": training_status,
        "training_sample_count": training_sample_count,
    }


def _default_trained_energy_surrogate() -> SimulationTrainedEnergySurrogate:
    global _TRAINED_SURROGATE, _TRAINING_SAMPLE_COUNT
    if _TRAINED_SURROGATE is None:
        samples = generate_energy_training_samples(seed_range=range(30, 42), max_pairs_per_scenario=14)
        _TRAINING_SAMPLE_COUNT = len(samples)
        _TRAINED_SURROGATE = SimulationTrainedEnergySurrogate.fit(samples, EnergyModel(battery_capacity=150.0))
    return _TRAINED_SURROGATE


if __name__ == "__main__":
    raise SystemExit(main())
