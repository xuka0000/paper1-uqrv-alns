from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.io_utils import ensure_experiment_dirs, write_json, write_markdown, write_rows_csv
from uqrv.stat_tests import compare_paired_methods, holm_adjust


BASELINES = ["greedy_nearest", "ga", "aco", "alns_fixed", "alns_pinn", "alns_pinn_uq"]
METRICS = [
    ("makespan", True),
    ("risk_weighted_completion_time", True),
    ("top_risk_coverage", False),
    ("infeasible_sortie_rate", True),
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default="stop_batch_model_20260606")
    args = parser.parse_args()
    rows = build_statistical_rows(args.run_id)
    write_outputs(args.run_id, rows)
    print(f"P7_statistical_tests: wrote {len(rows)} rows")
    return 0


def build_statistical_rows(run_id: str) -> List[dict]:
    p2_path = (
        PROJECT_ROOT
        / "results" / "experiments"
        / "P2_algorithm_comparison"
        / "raw_data"
        / f"P2_algorithm_comparison_{run_id}_raw.csv"
    )
    raw_rows = _read_csv(p2_path)
    out: List[dict] = []
    tower_counts = sorted({int(row["tower_count"]) for row in raw_rows})
    for tower_count in tower_counts:
        count_rows = [row for row in raw_rows if int(row["tower_count"]) == tower_count]
        for metric, lower_is_better in METRICS:
            metric_rows: List[dict] = []
            for baseline in BASELINES:
                result = compare_paired_methods(
                    count_rows,
                    baseline_method=baseline,
                    proposed_method="alns_pinn_full",
                    metric=metric,
                    pair_keys=["seed", "tower_count", "stop_count", "uncertainty"],
                    lower_is_better=lower_is_better,
                )
                result["tower_count"] = tower_count
                result["lower_is_better"] = lower_is_better
                metric_rows.append(result)
            adjusted = holm_adjust([row["p_value"] for row in metric_rows])
            for row, p_holm in zip(metric_rows, adjusted):
                row["p_holm"] = round(p_holm, 8)
                out.append(row)
    return out


def write_outputs(run_id: str, rows: List[dict]) -> None:
    root = ensure_experiment_dirs(PROJECT_ROOT / "results" / "experiments", "P7_statistical_tests", run_id)
    raw_path = root / "raw_data" / f"P7_statistical_tests_{run_id}_raw.csv"
    summary_path = root / "analysis_data" / f"P7_statistical_tests_{run_id}_summary.csv"
    report_path = root / "analysis_data" / f"P7_statistical_tests_{run_id}_summary.md"
    json_path = root / "analysis_data" / f"P7_statistical_tests_{run_id}_run_summary.json"
    write_rows_csv(raw_path, rows)
    write_rows_csv(summary_path, rows)
    write_markdown(report_path, "P7 Statistical Tests Summary", rows)
    write_json(
        json_path,
        {
            "experiment_id": "P7_statistical_tests",
            "run_id": run_id,
            "row_count": len(rows),
            "raw_data": str(raw_path),
            "summary_csv": str(summary_path),
            "summary_md": str(report_path),
        },
    )
    write_markdown(root / "runs" / run_id / "README.md", f"P7_statistical_tests {run_id}", rows)


def _read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
