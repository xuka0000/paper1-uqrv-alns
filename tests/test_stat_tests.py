import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.stat_tests import compare_paired_methods, holm_adjust


class StatTestTests(unittest.TestCase):
    def test_holm_adjust_returns_monotone_bounded_values(self):
        adjusted = holm_adjust([0.01, 0.03, 0.2])
        self.assertEqual(len(adjusted), 3)
        self.assertTrue(all(0.0 <= value <= 1.0 for value in adjusted))
        self.assertLessEqual(adjusted[0], adjusted[1])
        self.assertLessEqual(adjusted[1], adjusted[2])

    def test_compare_paired_methods_reports_effect_and_p_value(self):
        rows = []
        for seed in range(6):
            rows.append(
                {
                    "method": "baseline",
                    "seed": seed,
                    "tower_count": 50,
                    "risk_weighted_completion_time": 100.0 + seed,
                }
            )
            rows.append(
                {
                    "method": "proposed",
                    "seed": seed,
                    "tower_count": 50,
                    "risk_weighted_completion_time": 90.0 + seed,
                }
            )
        result = compare_paired_methods(
            rows,
            baseline_method="baseline",
            proposed_method="proposed",
            metric="risk_weighted_completion_time",
            pair_keys=["seed", "tower_count"],
            lower_is_better=True,
        )
        self.assertEqual(result["n"], 6)
        self.assertEqual(result["baseline_mean"], 102.5)
        self.assertEqual(result["proposed_mean"], 92.5)
        self.assertGreater(result["effect_pct"], 0.0)
        self.assertLessEqual(result["p_value"], 1.0)
        self.assertEqual(result["median_effect_abs"], 10.0)
        self.assertEqual(result["improvement_count"], 6)
        self.assertEqual(result["worsening_count"], 0)
        self.assertGreater(result["rank_biserial_effect"], 0.0)
        self.assertLessEqual(result["paired_diff_ci95_low"], result["median_effect_abs"])
        self.assertGreaterEqual(result["paired_diff_ci95_high"], result["median_effect_abs"])


if __name__ == "__main__":
    unittest.main()
