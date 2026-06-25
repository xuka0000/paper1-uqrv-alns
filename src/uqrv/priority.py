from __future__ import annotations

from typing import Dict, Sequence

from .scenario import Tower


def risk_value_priority_map(
    towers: Sequence[Tower],
    alpha_risk: float = 0.0,
    alpha_value: float = 1.0,
    alpha_interaction: float = 2.0,
    eps_risk: float = 1e-9,
    eps_value: float = 1e-9,
    eps_priority: float = 1e-9,
) -> Dict[int, float]:
    """Return normalized inspection-priority weights matching Section 3."""

    tower_list = list(towers)
    if not tower_list:
        return {}

    min_risk = min(tower.risk for tower in tower_list)
    max_risk = max(tower.risk for tower in tower_list)
    min_value = min(tower.value for tower in tower_list)
    max_value = max(tower.value for tower in tower_list)

    raw: Dict[int, float] = {}
    for tower in tower_list:
        risk = (tower.risk - min_risk) / (max_risk - min_risk + eps_risk)
        value = (tower.value - min_value) / (max_value - min_value + eps_value)
        raw[tower.id] = max(0.0, alpha_risk * risk + alpha_value * value + alpha_interaction * risk * value)

    total = sum(raw.values())
    if total <= eps_priority:
        uniform = 1.0 / len(tower_list)
        return {tower.id: uniform for tower in tower_list}
    return {tower_id: weight / (total + eps_priority) for tower_id, weight in raw.items()}


def scaled_risk_value_priority_map(towers: Sequence[Tower]) -> Dict[int, float]:
    priorities = risk_value_priority_map(towers)
    scale = sum(max(0.0, tower.value) for tower in towers)
    if scale <= 0.0:
        scale = float(max(1, len(towers)))
    return {tower_id: priority * scale for tower_id, priority in priorities.items()}
