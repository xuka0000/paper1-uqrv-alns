from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path
from time import perf_counter
from typing import Dict, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.gis_case import load_gis_case
from uqrv.io_utils import ensure_experiment_dirs, summarize_rows, write_json, write_markdown, write_rows_csv
from uqrv.metrics import evaluate_plan
from uqrv.solvers import solve


METRICS = [
    "makespan",
    "total_vehicle_distance",
    "expected_energy",
    "energy_violation_rate",
    "infeasible_sortie_rate",
    "risk_weighted_completion_time",
    "top_risk_coverage",
    "sortie_count",
    "avg_towers_per_sortie",
    "missed_value",
    "solver_runtime",
    "objective_value",
]

METHOD_MAP = {
    "greedy_nearest": ("greedy_nearest", 0),
    "ga": ("ga", 50),
    "aco": ("aco", 50),
    "alns_fixed": ("alns_fixed", 80),
    "alns_pinn": ("alns_point", 80),
    "alns_pinn_uq": ("uq_alns", 80),
    "alns_pinn_full": ("alns_full", 80),
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a GIS-grounded public-data case through the solver suite.")
    parser.add_argument("--case-root", required=True)
    parser.add_argument("--case-id", default="public_gis_case")
    parser.add_argument("--run-id", default="public_gis_smoke_20260526")
    parser.add_argument("--seeds", type=int, default=2)
    parser.add_argument("--methods", default="greedy_nearest,ga,aco,alns_fixed,alns_pinn,alns_pinn_full")
    parser.add_argument("--iterations", type=int, default=0, help="0 uses method defaults")
    args = parser.parse_args()

    methods = [method.strip() for method in args.methods.split(",") if method.strip()]
    unknown = sorted(set(methods) - set(METHOD_MAP))
    if unknown:
        raise ValueError(f"unknown methods: {unknown}; expected one of {sorted(METHOD_MAP)}")

    rows = run_case(args.case_root, args.case_id, seeds=range(args.seeds), methods=methods, iterations=args.iterations)
    write_outputs(args.run_id, rows)
    print(f"P9_real_gis_case: wrote {len(rows)} rows for {args.case_root}")
    return 0


def run_case(case_root: str | Path, case_id: str, seeds, methods: List[str], iterations: int = 0) -> List[dict]:
    base = load_gis_case(case_root, case_id=case_id)
    rows = []
    for seed in seeds:
        scenario = replace(base, id=f"{case_id}_seed{seed}", seed=int(seed))
        energy_model = EnergyModel(battery_capacity=scenario.battery_capacity)
        for method in methods:
            solver_method, default_iterations = METHOD_MAP[method]
            start = perf_counter()
            plan = solve(
                scenario,
                method=solver_method,
                energy_model=energy_model,
                iterations=iterations or default_iterations,
                seed=int(seed),
            )
            metrics = evaluate_plan(scenario, plan, energy_model)
            rows.append(
                {
                    "case_id": case_id,
                    "seed": int(seed),
                    "method": method,
                    "solver_method": solver_method,
                    "tower_count": len(scenario.towers),
                    "stop_count": len(scenario.stops),
                    "vehicle_count": scenario.vehicle_count,
                    "uav_count": scenario.uav_count,
                    "iterations": iterations or default_iterations,
                    "scenario_id": scenario.id,
                    "objective_value": plan.objective,
                    "solver_runtime": perf_counter() - start,
                    **metrics,
                    **_diagnostics(plan.diagnostics or {}),
                }
            )
    return rows


def write_outputs(run_id: str, rows: List[dict]) -> Dict[str, Path]:
    root = ensure_experiment_dirs(PROJECT_ROOT / "results" / "experiments", "P9_real_gis_case", run_id)
    raw_path = root / "raw_data" / f"P9_real_gis_case_{run_id}_raw.csv"
    summary_path = root / "analysis_data" / f"P9_real_gis_case_{run_id}_summary.csv"
    report_path = root / "analysis_data" / f"P9_real_gis_case_{run_id}_summary.md"
    json_path = root / "analysis_data" / f"P9_real_gis_case_{run_id}_run_summary.json"
    summary = summarize_rows(
        rows,
        ["case_id", "method", "tower_count", "stop_count", "vehicle_count", "uav_count"],
        METRICS + ["alns_accepted_moves", "alns_improving_moves"],
    )
    write_rows_csv(raw_path, rows)
    write_rows_csv(summary_path, summary)
    write_markdown(report_path, "P9 Real GIS Case Summary", summary)
    write_json(
        json_path,
        {
            "experiment_id": "P9_real_gis_case",
            "run_id": run_id,
            "row_count": len(rows),
            "raw_data": str(raw_path),
            "summary_csv": str(summary_path),
            "summary_md": str(report_path),
            "evidence_boundary": "GIS-grounded coordinates and weather; risk/value/stop labels remain proxy-generated.",
        },
    )
    write_markdown(root / "runs" / run_id / "README.md", "P9 Real GIS Case", summary)
    return {
        "raw_csv": raw_path,
        "summary_csv": summary_path,
        "summary_md": report_path,
        "run_summary_json": json_path,
    }


def _diagnostics(diagnostics: dict) -> dict:
    return {
        "alns_accepted_moves": float(diagnostics.get("accepted_moves", 0.0)),
        "alns_improving_moves": float(diagnostics.get("improving_moves", 0.0)),
        "alns_rejected_moves": float(diagnostics.get("rejected_moves", 0.0)),
        "alns_best_updates": float(diagnostics.get("best_updates", 0.0)),
    }


if __name__ == "__main__":
    raise SystemExit(main())
