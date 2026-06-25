from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Mapping

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.io_utils import write_markdown, write_rows_csv


DEFAULT_SUMMARIES = [
    PROJECT_ROOT
    / "results" / "experiments"
    / "P9_real_gis_case"
    / "analysis_data"
    / "P9_real_gis_case_public_bay_area_full_20260526_summary.csv",
    PROJECT_ROOT
    / "results" / "experiments"
    / "P9_real_gis_case"
    / "analysis_data"
    / "P9_real_gis_case_public_dallas_fort_worth_full_20260526_summary.csv",
    PROJECT_ROOT
    / "results" / "experiments"
    / "P9_real_gis_case"
    / "analysis_data"
    / "P9_real_gis_case_public_los_angeles_inland_full_20260526_summary.csv",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit RWCT and TopCov alignment in public GIS proxy cases.")
    parser.add_argument("--run-id", default="metric_alignment_20260531")
    parser.add_argument("--summary-csv", action="append", type=Path, default=[])
    args = parser.parse_args()

    summary_paths = args.summary_csv or DEFAULT_SUMMARIES
    rows = []
    for path in summary_paths:
        rows.extend(_read_csv(path))

    audit_rows = build_metric_alignment_rows(rows)
    out_root = PROJECT_ROOT / "results" / "experiments" / "P9_real_gis_case" / "analysis_data"
    csv_path = out_root / f"P9_real_gis_case_{args.run_id}_audit.csv"
    md_path = out_root / f"P9_real_gis_case_{args.run_id}_audit.md"
    write_rows_csv(csv_path, audit_rows)
    write_markdown(md_path, "P9 GIS Metric Alignment Audit", audit_rows)
    print(f"P9 GIS metric audit: wrote {len(audit_rows)} rows to {csv_path}")
    return 0


def build_metric_alignment_rows(rows: Iterable[Mapping[str, object]]) -> list[dict]:
    grouped: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["case_id"])].append(row)

    audit_rows: list[dict] = []
    for case_id, case_rows in sorted(grouped.items()):
        rwct_rank = _dense_ranks(case_rows, "risk_weighted_completion_time_mean", lower_is_better=True)
        top_rank = _dense_ranks(case_rows, "top_risk_coverage_mean", lower_is_better=False)
        best_rwct_methods = sorted(row["method"] for row in case_rows if rwct_rank[str(row["method"])] == 1)
        best_top_methods = sorted(row["method"] for row in case_rows if top_rank[str(row["method"])] == 1)
        best_metric_conflict = not bool(set(best_rwct_methods) & set(best_top_methods))
        for row in sorted(case_rows, key=lambda item: (rwct_rank[str(item["method"])], str(item["method"]))):
            method = str(row["method"])
            gap = abs(rwct_rank[method] - top_rank[method])
            audit_rows.append(
                {
                    "case_id": case_id,
                    "method": method,
                    "rwct": round(float(row["risk_weighted_completion_time_mean"]), 6),
                    "top_risk_coverage": round(float(row["top_risk_coverage_mean"]), 6),
                    "infeasible_sortie_rate": round(float(row.get("infeasible_sortie_rate_mean", 0.0)), 6),
                    "rwct_rank": rwct_rank[method],
                    "top_cov_rank": top_rank[method],
                    "rank_gap_abs": gap,
                    "case_best_rwct_methods": ";".join(best_rwct_methods),
                    "case_best_top_cov_methods": ";".join(best_top_methods),
                    "case_has_best_metric_conflict": best_metric_conflict,
                    "interpretation_flag": "rwct_topcov_conflict" if best_metric_conflict or gap >= 2 else "aligned_or_minor_gap",
                }
            )
    return audit_rows


def _dense_ranks(rows: Iterable[Mapping[str, object]], metric: str, lower_is_better: bool) -> dict[str, int]:
    values = sorted(
        {round(float(row[metric]), 9) for row in rows},
        reverse=not lower_is_better,
    )
    value_rank = {value: idx + 1 for idx, value in enumerate(values)}
    return {str(row["method"]): value_rank[round(float(row[metric]), 9)] for row in rows}


def _read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


if __name__ == "__main__":
    raise SystemExit(main())
