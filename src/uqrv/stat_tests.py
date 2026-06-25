from __future__ import annotations

from statistics import mean, median
from typing import Iterable, List, Mapping, Sequence

import numpy as np
from scipy.stats import rankdata
from scipy.stats import wilcoxon


def holm_adjust(p_values: Sequence[float]) -> List[float]:
    indexed = sorted(enumerate(p_values), key=lambda item: item[1])
    m = len(indexed)
    adjusted_sorted: List[tuple[int, float]] = []
    running_max = 0.0
    for rank, (idx, p_value) in enumerate(indexed):
        adjusted = min(1.0, (m - rank) * float(p_value))
        running_max = max(running_max, adjusted)
        adjusted_sorted.append((idx, running_max))
    adjusted_original = [0.0 for _ in p_values]
    for idx, adjusted in adjusted_sorted:
        adjusted_original[idx] = adjusted
    return adjusted_original


def compare_paired_methods(
    rows: Iterable[Mapping[str, object]],
    baseline_method: str,
    proposed_method: str,
    metric: str,
    pair_keys: Sequence[str],
    lower_is_better: bool,
) -> dict:
    baseline = {}
    proposed = {}
    for row in rows:
        key = tuple(row[pair_key] for pair_key in pair_keys)
        if row["method"] == baseline_method:
            baseline[key] = float(row[metric])
        elif row["method"] == proposed_method:
            proposed[key] = float(row[metric])

    common_keys = sorted(set(baseline) & set(proposed))
    baseline_values = [baseline[key] for key in common_keys]
    proposed_values = [proposed[key] for key in common_keys]
    if not common_keys:
        return {
            "baseline_method": baseline_method,
            "proposed_method": proposed_method,
            "metric": metric,
            "n": 0,
            "baseline_mean": 0.0,
            "proposed_mean": 0.0,
            "effect_abs": 0.0,
            "effect_pct": 0.0,
            "median_effect_abs": 0.0,
            "median_effect_pct": 0.0,
            "paired_diff_ci95_low": 0.0,
            "paired_diff_ci95_high": 0.0,
            "improvement_count": 0,
            "worsening_count": 0,
            "tie_count": 0,
            "rank_biserial_effect": 0.0,
            "p_value": 1.0,
        }

    baseline_mean = mean(baseline_values)
    proposed_mean = mean(proposed_values)
    effect_abs = baseline_mean - proposed_mean if lower_is_better else proposed_mean - baseline_mean
    effect_pct = 0.0 if baseline_mean == 0 else effect_abs / abs(baseline_mean) * 100.0
    improvements = [
        (baseline - proposed) if lower_is_better else (proposed - baseline)
        for baseline, proposed in zip(baseline_values, proposed_values)
    ]
    median_effect_abs = median(improvements)
    median_effect_pct = 0.0 if baseline_mean == 0 else median_effect_abs / abs(baseline_mean) * 100.0
    ci_low, ci_high = _bootstrap_median_ci(improvements)
    p_value = _wilcoxon_p_value(baseline_values, proposed_values)
    return {
        "baseline_method": baseline_method,
        "proposed_method": proposed_method,
        "metric": metric,
        "n": len(common_keys),
        "baseline_mean": round(baseline_mean, 6),
        "proposed_mean": round(proposed_mean, 6),
        "effect_abs": round(effect_abs, 6),
        "effect_pct": round(effect_pct, 6),
        "median_effect_abs": round(median_effect_abs, 6),
        "median_effect_pct": round(median_effect_pct, 6),
        "paired_diff_ci95_low": round(ci_low, 6),
        "paired_diff_ci95_high": round(ci_high, 6),
        "improvement_count": sum(1 for value in improvements if value > 1e-12),
        "worsening_count": sum(1 for value in improvements if value < -1e-12),
        "tie_count": sum(1 for value in improvements if abs(value) <= 1e-12),
        "rank_biserial_effect": round(_rank_biserial_effect(improvements), 6),
        "p_value": round(p_value, 8),
    }


def _wilcoxon_p_value(baseline_values: Sequence[float], proposed_values: Sequence[float]) -> float:
    differences = [proposed - baseline for baseline, proposed in zip(baseline_values, proposed_values)]
    if all(abs(diff) <= 1e-12 for diff in differences):
        return 1.0
    try:
        result = wilcoxon(proposed_values, baseline_values, zero_method="wilcox", alternative="two-sided")
    except ValueError:
        return 1.0
    return float(result.pvalue)


def _rank_biserial_effect(improvements: Sequence[float]) -> float:
    non_zero = [value for value in improvements if abs(value) > 1e-12]
    if not non_zero:
        return 0.0
    ranks = rankdata([abs(value) for value in non_zero])
    positive = sum(rank for rank, value in zip(ranks, non_zero) if value > 0)
    negative = sum(rank for rank, value in zip(ranks, non_zero) if value < 0)
    total = sum(ranks)
    return float((positive - negative) / total) if total else 0.0


def _bootstrap_median_ci(values: Sequence[float]) -> tuple[float, float]:
    if not values:
        return 0.0, 0.0
    if all(abs(value - values[0]) <= 1e-12 for value in values):
        return float(values[0]), float(values[0])
    rng = np.random.default_rng(20260531)
    sample = np.array(values, dtype=float)
    indices = rng.integers(0, len(sample), size=(5000, len(sample)))
    medians = np.median(sample[indices], axis=1)
    return float(np.quantile(medians, 0.025)), float(np.quantile(medians, 0.975))
