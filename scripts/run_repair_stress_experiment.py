from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from typing import Dict, Iterable, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.io_utils import ensure_experiment_dirs, summarize_rows, write_json, write_markdown, write_rows_csv
from uqrv.metrics import evaluate_plan
from uqrv.proposal_design import ProposalSizeConfig, generate_custom_scenario
from uqrv.scenario import Weather
from uqrv.solvers import solve


METHOD_MAP = {
    "alns_pinn_full": "alns_full",
    "no_energy_repair": "alns_full_no_energy_repair",
    "no_sync_repair": "alns_full_no_sync_repair",
    "no_uq": "alns_full_no_uq",
    "no_risk_value": "alns_full_no_risk_value",
    "alns_fixed": "alns_fixed",
}

STRESS_CASES = {
    "sparse_high_wind": {
        "tower_count": 75,
        "stop_count": 18,
        "vehicle_count": 3,
        "uavs_per_vehicle": 2,
        "battery_capacity": 125.0,
        "reserve_ratio": 0.20,
        "quantile_z": 1.96,
        "weather": Weather(12.0, 70.0, 34.0, 0.30),
    },
    "tight_battery": {
        "tower_count": 75,
        "stop_count": 24,
        "vehicle_count": 3,
        "uavs_per_vehicle": 2,
        "battery_capacity": 108.0,
        "reserve_ratio": 0.22,
        "quantile_z": 1.96,
        "weather": Weather(9.5, 140.0, 32.0, 0.30),
    },
    "very_sparse_corridor": {
        "tower_count": 100,
        "stop_count": 18,
        "vehicle_count": 3,
        "uavs_per_vehicle": 2,
        "battery_capacity": 132.0,
        "reserve_ratio": 0.18,
        "quantile_z": 1.96,
        "weather": Weather(10.5, 20.0, 35.0, 0.28),
    },
}

METRICS = [
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
    "alns_accepted_moves",
    "alns_improving_moves",
    "alns_rejected_moves",
    "alns_best_updates",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run repair-operator stress experiments.")
    parser.add_argument("--run-id", default="repair_stress_20260526")
    parser.add_argument("--seeds", type=int, default=10)
    parser.add_argument("--iterations", type=int, default=140)
    args = parser.parse_args()

    rows = run_stress(range(args.seeds), iterations=args.iterations)
    write_outputs(args.run_id, rows)
    print(f"P11_repair_stress: wrote {len(rows)} rows")
    return 0


def run_stress(seeds: Iterable[int], iterations: int) -> List[dict]:
    rows = []
    for case_id, case in STRESS_CASES.items():
        config = ProposalSizeConfig(
            "M",
            case["tower_count"],
            case["stop_count"],
            case["vehicle_count"],
            case["uavs_per_vehicle"],
            "repair stress",
        )
        for seed in seeds:
            base = generate_custom_scenario(config, seed=seed, uncertainty="high")
            scenario = replace(
                base,
                id=f"{case_id}_seed{seed}",
                battery_capacity=case["battery_capacity"],
                weather=case["weather"],
            )
            energy_model = EnergyModel(
                battery_capacity=scenario.battery_capacity,
                reserve_ratio=case["reserve_ratio"],
                quantile_z=case["quantile_z"],
            )
            for method, solver_method in METHOD_MAP.items():
                plan = solve(scenario, method=solver_method, energy_model=energy_model, iterations=iterations, seed=seed)
                metrics = evaluate_plan(scenario, plan, energy_model)
                rows.append(
                    {
                        "stress_case": case_id,
                        "seed": int(seed),
                        "method": method,
                        "solver_method": solver_method,
                        "tower_count": len(scenario.towers),
                        "stop_count": len(scenario.stops),
                        "vehicle_count": scenario.vehicle_count,
                        "uav_count": scenario.uav_count,
                        "battery_capacity": scenario.battery_capacity,
                        "reserve_ratio": case["reserve_ratio"],
                        "quantile_z": case["quantile_z"],
                        "wind_speed": scenario.weather.wind_speed,
                        "temperature": scenario.weather.temperature,
                        "objective_value": plan.objective,
                        **metrics,
                        **_diagnostics(plan.diagnostics or {}),
                    }
                )
    return rows


def write_outputs(run_id: str, rows: List[dict]) -> Dict[str, Path]:
    root = ensure_experiment_dirs(PROJECT_ROOT / "results" / "experiments", "P11_repair_stress", run_id)
    raw_path = root / "raw_data" / f"P11_repair_stress_{run_id}_raw.csv"
    summary_path = root / "analysis_data" / f"P11_repair_stress_{run_id}_summary.csv"
    summary_md = root / "analysis_data" / f"P11_repair_stress_{run_id}_summary.md"
    run_json = root / "analysis_data" / f"P11_repair_stress_{run_id}_run_summary.json"
    summary = summarize_rows(rows, ["stress_case", "method", "tower_count", "stop_count"], METRICS)
    write_rows_csv(raw_path, rows)
    write_rows_csv(summary_path, summary)
    write_markdown(summary_md, "P11 Repair Stress Summary", summary)
    write_json(
        run_json,
        {
            "experiment_id": "P11_repair_stress",
            "run_id": run_id,
            "row_count": len(rows),
            "raw_data": str(raw_path),
            "summary_csv": str(summary_path),
            "summary_md": str(summary_md),
            "evidence_boundary": "Synthetic stress scenarios designed to expose repair-operator behavior.",
        },
    )
    write_markdown(root / "runs" / run_id / "README.md", "P11 Repair Stress", summary)
    return {"raw_csv": raw_path, "summary_csv": summary_path, "summary_md": summary_md, "run_summary_json": run_json}


def _diagnostics(diagnostics: dict) -> dict:
    return {
        "alns_accepted_moves": float(diagnostics.get("accepted_moves", 0.0)),
        "alns_improving_moves": float(diagnostics.get("improving_moves", 0.0)),
        "alns_rejected_moves": float(diagnostics.get("rejected_moves", 0.0)),
        "alns_best_updates": float(diagnostics.get("best_updates", 0.0)),
    }


if __name__ == "__main__":
    raise SystemExit(main())
