import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from audit_gis_metric_alignment import build_metric_alignment_rows


class GisMetricAuditTests(unittest.TestCase):
    def test_build_metric_alignment_rows_flags_rank_conflict(self):
        rows = [
            _row("case_a", "nearest", 90.0, 0.0),
            _row("case_a", "point", 120.0, 0.9),
            _row("case_a", "proposed", 80.0, 0.8),
        ]

        audit = build_metric_alignment_rows(rows)
        proposed = next(row for row in audit if row["method"] == "proposed")
        nearest = next(row for row in audit if row["method"] == "nearest")

        self.assertTrue(proposed["case_has_best_metric_conflict"])
        self.assertEqual(proposed["rwct_rank"], 1)
        self.assertEqual(proposed["top_cov_rank"], 2)
        self.assertEqual(nearest["rwct_rank"], 2)
        self.assertEqual(nearest["top_cov_rank"], 3)
        self.assertGreater(nearest["rank_gap_abs"], 0)


def _row(case_id, method, rwct, top_cov):
    return {
        "case_id": case_id,
        "method": method,
        "risk_weighted_completion_time_mean": rwct,
        "top_risk_coverage_mean": top_cov,
        "infeasible_sortie_rate_mean": 0.0,
    }


if __name__ == "__main__":
    unittest.main()
