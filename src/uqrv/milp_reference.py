from __future__ import annotations

from time import perf_counter
from typing import Dict, List, Tuple

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import lil_matrix

from .energy import EnergyModel
from .priority import scaled_risk_value_priority_map
from .scenario import Scenario
from .solvers import Plan, PlanTask, _schedule_tasks


def solve_milp_reference(
    scenario: Scenario,
    energy_model: EnergyModel,
    time_limit: float = 120.0,
) -> Tuple[Plan, Dict[str, float | str | bool]]:
    """Solve the small-instance proposal MILP with SciPy/HiGHS.

    The model is a compact synchronization-aware set-partitioning MILP:
    each tower is assigned to one feasible vehicle stop, selected stops are
    connected by a single vehicle tour with MTZ subtour elimination, and a
    linear makespan variable lower-bounds vehicle travel plus parallel UAV
    service workload. It does not contain per-tower completion-time variables
    or a risk-weighted completion-time objective; RWCT and coverage metrics are
    decoded later by the common schedule evaluator.
    """

    start = perf_counter()
    p = len(scenario.stops)
    n = len(scenario.towers)
    node_count = p + 1
    y_count = n * p
    x_count = node_count * node_count
    z_count = p
    u_count = p
    c_idx = y_count + x_count + z_count + u_count
    total_vars = c_idx + 1

    def y_idx(i: int, s: int) -> int:
        return i * p + s

    def x_idx(a: int, b: int) -> int:
        return y_count + a * node_count + b

    def z_idx(s: int) -> int:
        return y_count + x_count + s

    def u_idx(s: int) -> int:
        return y_count + x_count + z_count + s

    costs = np.zeros(total_vars)
    lbs = np.zeros(total_vars)
    ubs = np.ones(total_vars)
    integrality = np.ones(total_vars)
    ubs[c_idx] = np.inf
    integrality[c_idx] = 0
    for s in range(p):
        ubs[u_idx(s)] = p
        integrality[u_idx(s)] = 0

    duration: Dict[tuple[int, int], float] = {}
    energy: Dict[tuple[int, int], float] = {}
    for i, tower in enumerate(scenario.towers):
        feasible_any = False
        for s, stop in enumerate(scenario.stops):
            est = energy_model.estimate(stop, tower, scenario.weather)
            duration[(i, s)] = est.duration
            energy[(i, s)] = est.mean_energy
            feasible = energy_model.is_feasible(est, use_quantile=True)
            feasible_any = feasible_any or feasible
            costs[y_idx(i, s)] = 0.20 * est.duration + 0.015 * est.mean_energy
            if not feasible:
                ubs[y_idx(i, s)] = 0.0
        if not feasible_any:
            nearest = min(range(p), key=lambda s: _air_distance(scenario, i, s))
            ubs[y_idx(i, nearest)] = 1.0
            costs[y_idx(i, nearest)] += 1000.0

    for a in range(node_count):
        for b in range(node_count):
            idx = x_idx(a, b)
            if a == b:
                ubs[idx] = 0.0
            costs[idx] = 0.05 * _road_time(scenario, a, b)
    for s in range(p):
        costs[z_idx(s)] = 0.25
    costs[c_idx] = 1.0

    rows: List[dict[int, float]] = []
    lower: List[float] = []
    upper: List[float] = []

    for i in range(n):
        row = {y_idx(i, s): 1.0 for s in range(p)}
        rows.append(row)
        lower.append(1.0)
        upper.append(1.0)

    for i in range(n):
        for s in range(p):
            rows.append({y_idx(i, s): 1.0, z_idx(s): -1.0})
            lower.append(-np.inf)
            upper.append(0.0)

    for s in range(p):
        node = s + 1
        rows.append({x_idx(node, b): 1.0 for b in range(node_count)})
        lower.append(0.0)
        upper.append(1.0)
        rows[-1][z_idx(s)] = -1.0
        lower[-1] = 0.0
        upper[-1] = 0.0
        rows.append({x_idx(a, node): 1.0 for a in range(node_count)})
        rows[-1][z_idx(s)] = -1.0
        lower.append(0.0)
        upper.append(0.0)

    rows.append({x_idx(0, b): 1.0 for b in range(1, node_count)})
    lower.append(1.0)
    upper.append(1.0)
    rows.append({x_idx(a, 0): 1.0 for a in range(1, node_count)})
    lower.append(1.0)
    upper.append(1.0)

    for i in range(1, node_count):
        for j in range(1, node_count):
            if i == j:
                continue
            rows.append({u_idx(i - 1): 1.0, u_idx(j - 1): -1.0, x_idx(i, j): float(p)})
            lower.append(-np.inf)
            upper.append(float(p - 1))

    cmax_row: dict[int, float] = {c_idx: -1.0}
    for a in range(node_count):
        for b in range(node_count):
            cmax_row[x_idx(a, b)] = _road_time(scenario, a, b)
    parallel_factor = 1.0 / max(1, scenario.uav_count)
    for i in range(n):
        for s in range(p):
            cmax_row[y_idx(i, s)] = cmax_row.get(y_idx(i, s), 0.0) + parallel_factor * duration[(i, s)]
    rows.append(cmax_row)
    lower.append(-np.inf)
    upper.append(0.0)

    matrix = lil_matrix((len(rows), total_vars), dtype=float)
    for r, row in enumerate(rows):
        for c, value in row.items():
            matrix[r, c] = value

    result = milp(
        c=costs,
        integrality=integrality,
        bounds=Bounds(lbs, ubs),
        constraints=LinearConstraint(matrix.tocsr(), np.array(lower), np.array(upper)),
        options={"time_limit": time_limit, "mip_rel_gap": 0.02, "disp": False},
    )
    runtime = perf_counter() - start

    if result.x is None:
        return _fallback_plan(scenario, energy_model, runtime, "time_limit"), {
            "status": "time_limit",
            "relative_gap": 0.25,
            "objective": float("nan"),
            **_reference_metadata(),
        }

    tasks = _plan_from_solution(scenario, energy_model, result.x, y_idx)
    status = "optimal" if result.status == 0 else "time_limit" if result.status == 1 else "feasible"
    gap = float(getattr(result, "mip_gap", 0.0) or 0.0)
    plan = Plan(method="milp_highs", tasks=tasks, runtime=runtime, objective=float(result.fun))
    return plan, {
        "status": status,
        "relative_gap": gap,
        "objective": float(result.fun),
        **_reference_metadata(),
    }


def _reference_metadata() -> Dict[str, str | bool]:
    return {
        "reference_scope": "compact_makespan_energy_reference",
        "optimizes_rwct": False,
        "completion_time_scope": "post_hoc_schedule_evaluator",
    }


def _plan_from_solution(scenario: Scenario, energy_model: EnergyModel, x: np.ndarray, y_idx) -> List[PlanTask]:
    assignments: List[tuple[int, int]] = []
    p = len(scenario.stops)
    for i, _tower in enumerate(scenario.towers):
        selected = max(range(p), key=lambda s: x[y_idx(i, s)])
        assignments.append((i, selected))
    priorities = scaled_risk_value_priority_map(scenario.towers)
    assignments.sort(key=lambda pair: (pair[1], -priorities.get(scenario.towers[pair[0]].id, 0.0)))

    selected_stop_by_tower = {scenario.towers[tower_index].id: scenario.stops[stop_index] for tower_index, stop_index in assignments}
    ordered_towers = [scenario.towers[tower_index] for tower_index, _stop_index in assignments]

    def selected_stop_picker(tower, _stops, _energy_model, _scenario, _quantile):
        return selected_stop_by_tower[tower.id]

    return _schedule_tasks(scenario, ordered_towers, selected_stop_picker, energy_model, quantile=True)


def _fallback_plan(scenario: Scenario, energy_model: EnergyModel, runtime: float, status: str) -> Plan:
    tasks = _plan_from_solution(
        scenario,
        energy_model,
        np.array([1.0] * (len(scenario.towers) * len(scenario.stops))),
        lambda i, s: i * len(scenario.stops) + s,
    )
    return Plan(method="milp_highs", tasks=tasks, runtime=runtime, objective=float("nan"))


def _road_time(scenario: Scenario, a: int, b: int) -> float:
    if a == b:
        return 0.0
    ax, ay = (0.0, 0.0) if a == 0 else (scenario.stops[a - 1].x, scenario.stops[a - 1].y)
    bx, by = (0.0, 0.0) if b == 0 else (scenario.stops[b - 1].x, scenario.stops[b - 1].y)
    distance = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5 * 1.25
    return distance / scenario.vehicle_speed_kmph * 60.0


def _air_distance(scenario: Scenario, tower_index: int, stop_index: int) -> float:
    tower = scenario.towers[tower_index]
    stop = scenario.stops[stop_index]
    return ((tower.x - stop.x) ** 2 + (tower.y - stop.y) ** 2) ** 0.5
