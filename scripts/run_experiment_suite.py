from __future__ import annotations

import argparse
import sys
from pathlib import Path
from time import perf_counter
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.io_utils import ensure_experiment_dirs, summarize_rows, write_json, write_markdown, write_rows_csv
from uqrv.metrics import evaluate_plan
from uqrv.online import simulate_online_policy
from uqrv.scenario import generate_scenario
from uqrv.solvers import solve


METRIC_KEYS = [
    "makespan",
    "total_vehicle_distance",
    "expected_energy",
    "energy_violation_rate",
    "infeasible_sortie_rate",
    "risk_weighted_completion_time",
    "top_risk_coverage",
    "missed_value",
    "solver_runtime",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--only", required=True, help="Experiment ID or ALL")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    selected = _selected_experiments(args.only)
    for experiment_id in selected:
        start = perf_counter()
        rows = run_experiment(experiment_id, args.run_id, quick=args.quick)
        elapsed = perf_counter() - start
        print(f"{experiment_id}: wrote {len(rows)} rows in {elapsed:.3f}s")
    return 0


def _selected_experiments(only: str) -> List[str]:
    all_ids = [
        "E0_smoke",
        "E1_exact_small",
        "E2_core_comparison",
        "E3_uncertainty_robustness",
        "E4_value_ablation",
        "E5_online_replanning",
        "E6_scalability",
        "E7_parameter_sensitivity",
    ]
    if only.upper() == "ALL":
        return all_ids[:-1]
    if only not in all_ids:
        raise ValueError(f"unknown experiment {only!r}; expected one of {all_ids} or ALL")
    return [only]


def run_experiment(experiment_id: str, run_id: str, quick: bool = False) -> List[Dict[str, object]]:
    exp_root = ensure_experiment_dirs(PROJECT_ROOT / "results" / "experiments", experiment_id, run_id)
    if experiment_id == "E5_online_replanning":
        rows = _online_rows(experiment_id, quick)
        group_keys = ["policy", "size"]
        metrics = METRIC_KEYS + ["online_response_time", "event_count", "disturbance_intensity"]
    else:
        rows = _solver_rows(experiment_id, quick)
        group_keys = ["method", "size", "uncertainty"]
        metrics = METRIC_KEYS

    raw_path = exp_root / "raw_data" / f"{experiment_id}_{run_id}_raw.csv"
    summary = summarize_rows(rows, group_keys, metrics)
    summary_path = exp_root / "analysis_data" / f"{experiment_id}_{run_id}_summary.csv"
    report_path = exp_root / "analysis_data" / f"{experiment_id}_{run_id}_summary.md"
    json_path = exp_root / "analysis_data" / f"{experiment_id}_{run_id}_run_summary.json"
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
    write_markdown(exp_root / "runs" / run_id / "README.md", f"{experiment_id} {run_id}", summary)
    return rows


def _solver_rows(experiment_id: str, quick: bool) -> List[Dict[str, object]]:
    configs = _solver_configs(experiment_id, quick)
    rows: List[Dict[str, object]] = []
    for cfg in configs:
        scenario = generate_scenario(size=cfg["size"], seed=cfg["seed"], uncertainty=cfg["uncertainty"])
        energy_model = EnergyModel(battery_capacity=scenario.battery_capacity)
        plan = solve(
            scenario,
            method=cfg["method"],
            energy_model=energy_model,
            iterations=cfg["iterations"],
            seed=cfg["seed"],
        )
        metrics = evaluate_plan(scenario, plan, energy_model)
        rows.append(
            {
                "experiment": experiment_id,
                "size": cfg["size"],
                "seed": cfg["seed"],
                "uncertainty": cfg["uncertainty"],
                "method": cfg["method"],
                **metrics,
            }
        )
    return rows


def _online_rows(experiment_id: str, quick: bool) -> List[Dict[str, object]]:
    seeds = range(3 if quick else 30)
    policies = ["static", "periodic", "event_triggered"]
    rows: List[Dict[str, object]] = []
    for seed in seeds:
        scenario = generate_scenario(size="M", seed=seed, uncertainty="high")
        for policy in policies:
            result = simulate_online_policy(scenario, policy=policy, seed=seed)
            rows.append(
                {
                    "experiment": experiment_id,
                    "size": scenario.size,
                    "seed": seed,
                    "policy": policy,
                    **result.metrics,
                }
            )
    return rows


def _solver_configs(experiment_id: str, quick: bool) -> List[Dict[str, object]]:
    if experiment_id == "E0_smoke":
        return _grid(["S"], range(2), ["medium"], ["greedy_nearest", "alns_point", "uq_rv_alns"], 30)
    if experiment_id == "E1_exact_small":
        return _grid(["S"], range(3 if quick else 12), ["medium"], ["greedy_nearest", "alns_fixed", "alns_point", "uq_rv_alns"], 80)
    if experiment_id == "E2_core_comparison":
        methods = ["greedy_nearest", "greedy_value", "random_feasible", "ga", "aco", "alns_fixed", "alns_point", "uq_alns", "rv_alns", "uq_rv_alns"]
        return _grid(["M"], range(3 if quick else 30), ["medium"], methods, 90)
    if experiment_id == "E3_uncertainty_robustness":
        return _grid(["M"], range(3 if quick else 24), ["low", "medium", "high"], ["alns_point", "uq_alns", "uq_rv_alns"], 90)
    if experiment_id == "E4_value_ablation":
        return _grid(["M"], range(3 if quick else 24), ["medium"], ["alns_point", "uq_alns", "rv_alns", "uq_rv_alns"], 90)
    if experiment_id == "E6_scalability":
        return _grid(["S", "M", "L"], range(2 if quick else 10), ["medium"], ["alns_point", "uq_rv_alns"], 120)
    if experiment_id == "E7_parameter_sensitivity":
        return _grid(["M"], range(3 if quick else 12), ["low", "medium", "high"], ["uq_rv_alns"], 160)
    raise ValueError(f"solver config not defined for {experiment_id}")


def _grid(sizes, seeds, uncertainties, methods, iterations) -> List[Dict[str, object]]:
    return [
        {
            "size": size,
            "seed": seed,
            "uncertainty": uncertainty,
            "method": method,
            "iterations": iterations,
        }
        for size in sizes
        for seed in seeds
        for uncertainty in uncertainties
        for method in methods
    ]


if __name__ == "__main__":
    raise SystemExit(main())

