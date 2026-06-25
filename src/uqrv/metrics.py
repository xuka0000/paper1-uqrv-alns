from __future__ import annotations

from math import hypot
from typing import Dict, List, Tuple

from .energy import EnergyModel
from .priority import risk_value_priority_map
from .scenario import Scenario, Stop
from .solvers import Plan


def evaluate_plan(scenario: Scenario, plan: Plan, energy_model: EnergyModel) -> Dict[str, float]:
    if not plan.tasks:
        return {
            "makespan": 0.0,
            "total_vehicle_distance": 0.0,
            "expected_energy": 0.0,
            "energy_violation_rate": 0.0,
            "infeasible_sortie_rate": 0.0,
            "risk_weighted_completion_time": 0.0,
            "top_risk_coverage": 0.0,
            "feasible_top_risk_coverage": 0.0,
            "sortie_count": 0,
            "avg_towers_per_sortie": 0.0,
            "missed_value": 0.0,
            "solver_runtime": plan.runtime,
        }

    tower_by_id = {tower.id: tower for tower in scenario.towers}
    total_vehicle_distance, vehicle_return_completion = _vehicle_route_summary(scenario, plan)
    makespan = max(max(task.finish for task in plan.tasks), vehicle_return_completion)
    q95_limit = energy_model.battery_capacity * (1.0 - energy_model.reserve_ratio)
    if plan.sorties:
        expected_energy = sum(sortie.energy_mean for sortie in plan.sorties)
        infeasible = sum(1 for sortie in plan.sorties if sortie.energy_q95 > q95_limit)
        energy_denominator = len(plan.sorties)
        sortie_count = len(plan.sorties)
        avg_towers_per_sortie = sum(len(sortie.tower_ids) for sortie in plan.sorties) / len(plan.sorties)
    else:
        expected_energy = sum(task.energy_mean for task in plan.tasks)
        infeasible = sum(1 for task in plan.tasks if task.energy_q95 > q95_limit)
        energy_denominator = len(plan.tasks)
        sortie_count = len(plan.tasks)
        avg_towers_per_sortie = 1.0
    priority = risk_value_priority_map(scenario.towers)
    risk_weighted_completion = sum(
        priority.get(task.tower_id, 0.0) * task.finish
        for task in plan.tasks
    )
    top_count = max(1, int(len(scenario.towers) * 0.25))
    top_risk_ids = {
        tower.id
        for tower in sorted(
            scenario.towers,
            key=lambda t: (priority.get(t.id, 0.0), t.risk, t.value, -t.id),
            reverse=True,
        )[:top_count]
    }
    early_cutoff = sorted(task.finish for task in plan.tasks)[top_count - 1]
    early_top = sum(1 for task in plan.tasks if task.tower_id in top_risk_ids and task.finish <= early_cutoff)
    feasible_early_top = sum(
        1
        for task in plan.tasks
        if task.tower_id in top_risk_ids and task.finish <= early_cutoff and task.energy_q95 <= q95_limit
    )
    missed_value = sum(tower_by_id[task.tower_id].value for task in plan.tasks if not task.feasible)
    return {
        "makespan": round(makespan, 6),
        "total_vehicle_distance": round(total_vehicle_distance, 6),
        "expected_energy": round(expected_energy, 6),
        "energy_violation_rate": round(infeasible / energy_denominator, 6),
        "infeasible_sortie_rate": round(infeasible / energy_denominator, 6),
        "risk_weighted_completion_time": round(risk_weighted_completion, 6),
        "top_risk_coverage": round(early_top / top_count, 6),
        "feasible_top_risk_coverage": round(feasible_early_top / top_count, 6),
        "sortie_count": sortie_count,
        "avg_towers_per_sortie": round(avg_towers_per_sortie, 6),
        "missed_value": round(missed_value, 6),
        "solver_runtime": round(plan.runtime, 6),
    }


def _vehicle_route_summary(scenario: Scenario, plan: Plan) -> Tuple[float, float]:
    stop_by_id = {stop.id: stop for stop in scenario.stops}
    depot = _depot_stop(scenario)
    distance = 0.0
    return_completion = 0.0
    tasks_by_vehicle: Dict[int, List] = {}
    for task in plan.tasks:
        tasks_by_vehicle.setdefault(task.vehicle_id, []).append(task)

    for vehicle_tasks in tasks_by_vehicle.values():
        last = depot
        last_departure = 0.0
        for task in vehicle_tasks:
            stop = stop_by_id[task.stop_id]
            leg = _stop_distance(last, stop)
            distance += leg
            last = stop
            last_departure = max(last_departure, task.vehicle_departure, task.finish)
        return_distance = _stop_distance(last, depot)
        distance += return_distance
        return_completion = max(return_completion, last_departure + _travel_time(scenario, return_distance))
    return distance, return_completion


def _depot_stop(scenario: Scenario) -> Stop:
    if not scenario.stops:
        return Stop(-1, 0.0, 0.0)
    first = min(scenario.stops, key=lambda stop: (stop.x, stop.y, stop.id))
    return Stop(-1, first.x, first.y)


def _stop_distance(left: Stop, right: Stop) -> float:
    return hypot(left.x - right.x, left.y - right.y)


def _travel_time(scenario: Scenario, distance: float) -> float:
    return distance / max(1.0, scenario.vehicle_speed_kmph) * 60.0


def _vehicle_distance_proxy(scenario: Scenario, plan: Plan) -> float:
    return _vehicle_route_summary(scenario, plan)[0]
