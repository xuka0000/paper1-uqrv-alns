from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot
from random import Random
from time import perf_counter
from typing import Callable, Dict, List, Sequence

from .alns_operators import (
    AdaptiveOperatorWeights,
    DestroyMove,
    SimulatedAnnealingAcceptance,
    energy_minimum_insert_repair,
    greedy_insert_repair,
    path_segment_removal,
    random_removal,
    regret_insert_repair,
    shaw_related_removal,
    synchronization_aware_insert_repair,
    uav_chain_removal,
    worst_energy_removal,
)
from .energy import EnergyModel
from .priority import risk_value_priority_map, scaled_risk_value_priority_map
from .scenario import Scenario, Stop, Tower


@dataclass(frozen=True)
class PlanTask:
    tower_id: int
    stop_id: int
    uav_id: int
    start: float
    finish: float
    energy_mean: float
    energy_q95: float
    feasible: bool
    value: float
    risk: float
    vehicle_id: int = 0
    vehicle_arrival: float = 0.0
    vehicle_departure: float = 0.0
    road_travel: float = 0.0
    priority: float = 0.0
    sortie_id: int = -1


@dataclass(frozen=True)
class PlanSortie:
    sortie_id: int
    tower_ids: List[int]
    stop_id: int
    uav_id: int
    vehicle_id: int
    start: float
    return_time: float
    energy_mean: float
    energy_q95: float
    feasible: bool
    vehicle_arrival: float = 0.0
    vehicle_departure: float = 0.0
    road_travel: float = 0.0


@dataclass(frozen=True)
class Plan:
    method: str
    tasks: List[PlanTask]
    runtime: float
    objective: float
    diagnostics: Dict[str, object] | None = None
    sorties: List[PlanSortie] = field(default_factory=list)


def solve(
    scenario: Scenario,
    method: str,
    energy_model: EnergyModel | None = None,
    iterations: int = 100,
    seed: int | None = None,
) -> Plan:
    energy_model = energy_model or EnergyModel(battery_capacity=scenario.battery_capacity)
    start_time = perf_counter()
    rng = Random(scenario.seed if seed is None else seed)
    method_key = method.lower()
    diagnostics: Dict[str, object] | None = None
    priority_scores = scaled_risk_value_priority_map(scenario.towers)
    if method_key in {"greedy_nearest", "nearest"}:
        ordered = sorted(scenario.towers, key=lambda t: _nearest_distance(t, scenario.stops))
        stop_picker = _pick_nearest
        quantile = False
    elif method_key in {"greedy_value", "value_density"}:
        ordered = sorted(
            scenario.towers,
            key=lambda t: (priority_scores.get(t.id, 0.0), t.value, -_nearest_distance(t, scenario.stops)),
            reverse=True,
        )
        stop_picker = _pick_value_aware
        quantile = False
    elif method_key in {"random_feasible", "random"}:
        ordered = list(scenario.towers)
        rng.shuffle(ordered)
        stop_picker = _pick_nearest
        quantile = False
    elif method_key == "ga":
        ordered, diagnostics = _genetic_order_search(
            scenario.towers, scenario.stops, rng, iterations, value_weight=0.12
        )
        stop_picker = _pick_energy_aware
        quantile = False
    elif method_key == "aco":
        ordered, diagnostics = _ant_colony_order_search(
            scenario.towers, scenario.stops, rng, iterations, value_weight=0.10
        )
        stop_picker = _pick_energy_aware
        quantile = False
    elif method_key == "alns_fixed":
        return _solve_schedule_state_alns_plan(
            scenario=scenario,
            method=method_key,
            energy_model=energy_model,
            iterations=iterations,
            rng=rng,
            start_time=start_time,
            use_quantile=False,
            risk_value_weight=0.0,
        )
    elif method_key in {"alns_point", "point_pinn"}:
        return _solve_schedule_state_alns_plan(
            scenario=scenario,
            method=method_key,
            energy_model=energy_model,
            iterations=iterations,
            rng=rng,
            start_time=start_time,
            use_quantile=False,
            risk_value_weight=0.0,
        )
    elif method_key in {"uq_alns", "uq"}:
        return _solve_schedule_state_alns_plan(
            scenario=scenario,
            method=method_key,
            energy_model=energy_model,
            iterations=iterations,
            rng=rng,
            start_time=start_time,
            use_quantile=True,
            risk_value_weight=0.0,
        )
    elif method_key in {"rv_alns", "risk_value"}:
        return _solve_schedule_state_alns_plan(
            scenario=scenario,
            method=method_key,
            energy_model=energy_model,
            iterations=iterations,
            rng=rng,
            start_time=start_time,
            use_quantile=False,
            risk_value_weight=0.25,
        )
    elif method_key in {"uq_rv_alns", "proposed"}:
        return _solve_schedule_state_alns_plan(
            scenario=scenario,
            method=method_key,
            energy_model=energy_model,
            iterations=iterations,
            rng=rng,
            start_time=start_time,
            use_quantile=True,
            risk_value_weight=0.25,
        )
    elif method_key in {
        "alns_full",
        "alns_operator",
        "uq_rv_alns_full",
        "alns_full_no_energy_repair",
        "alns_full_no_sync_repair",
        "alns_full_no_uq",
        "alns_full_no_risk_value",
        "alns_full_no_adaptive",
    }:
        disabled_repair_operators: list[str] = []
        if method_key == "alns_full_no_energy_repair":
            disabled_repair_operators = ["energy_minimum_insert_repair"]
        elif method_key == "alns_full_no_sync_repair":
            disabled_repair_operators = ["synchronization_aware_insert_repair"]
        use_quantile = method_key != "alns_full_no_uq"
        risk_value_weight = 0.0 if method_key == "alns_full_no_risk_value" else 0.25
        adaptive_enabled = method_key != "alns_full_no_adaptive"
        return _solve_schedule_state_alns_plan(
            scenario=scenario,
            method=method_key,
            energy_model=energy_model,
            iterations=iterations,
            rng=rng,
            start_time=start_time,
            use_quantile=use_quantile,
            risk_value_weight=risk_value_weight,
            disabled_repair_operators=disabled_repair_operators,
            adaptive_enabled=adaptive_enabled,
        )
    else:
        raise ValueError(f"unknown solver method {method!r}")

    tasks, sorties = _schedule_tasks_and_sorties(
        scenario,
        ordered,
        stop_picker,
        energy_model,
        quantile,
        allow_multi_tower_sorties=quantile,
    )
    objective = _plan_objective(tasks)
    runtime = perf_counter() - start_time
    return Plan(
        method=method,
        tasks=tasks,
        runtime=runtime,
        objective=objective,
        diagnostics=diagnostics,
        sorties=sorties,
    )


def _solve_operator_alns(
    scenario: Scenario,
    method: str,
    energy_model: EnergyModel,
    iterations: int,
    rng: Random,
    start_time: float,
    use_quantile: bool,
    risk_value_weight: float,
    disabled_repair_operators: Sequence[str] | None = None,
    schedule_stop_picker: Callable[[Tower, Sequence[Stop], EnergyModel, Scenario, bool], Stop] | None = None,
    adaptive_enabled: bool = True,
    selection_seed: int | None = None,
) -> Plan:
    priority_scores = scaled_risk_value_priority_map(scenario.towers)
    current = sorted(
        scenario.towers,
        key=lambda tower: (
            priority_scores.get(tower.id, 0.0),
            -_nearest_distance(tower, scenario.stops),
        ),
        reverse=True,
    )
    score_cache = _build_operator_score_cache(
        scenario, energy_model, use_quantile, risk_value_weight
    )
    energy_cache = _build_operator_energy_cache(scenario, energy_model, use_quantile)
    workload_cache = _build_operator_workload_cache(scenario, energy_model, use_quantile)
    best = list(current)
    current_objective = _operator_alns_objective_from_cache(current, score_cache, energy_cache, workload_cache, scenario.uav_count)
    objective_evaluations = 1
    best_objective = current_objective
    temperature = max(1.0, abs(current_objective) * 0.03)
    acceptance = SimulatedAnnealingAcceptance(initial_temperature=temperature, cooling_rate=0.992)

    destroy_operator_names = [
        "random_removal",
        "worst_energy_removal",
        "shaw_related_removal",
        "path_segment_removal",
        "uav_chain_removal",
    ]
    repair_operator_names = [
        "greedy_insert_repair",
        "regret_insert_repair",
        "energy_minimum_insert_repair",
        "synchronization_aware_insert_repair",
    ]
    disabled_repair = set(disabled_repair_operators or [])
    active_repair_operator_names = [name for name in repair_operator_names if name not in disabled_repair]
    if not active_repair_operator_names:
        raise ValueError("at least one repair operator must remain active")

    destroy_weights = AdaptiveOperatorWeights(destroy_operator_names)
    repair_weights = AdaptiveOperatorWeights(active_repair_operator_names)
    accepted_moves = 0
    improving_moves = 0
    best_updates = 0
    rejected_moves = 0
    repair_position_evaluations = 0
    rounds = max(0, iterations)

    for _ in range(rounds):
        if len(current) < 2:
            break
        remove_count = max(1, min(len(current) - 1, round(len(current) * 0.18)))
        destroy_name = destroy_weights.select(rng)
        repair_name = repair_weights.select(rng)
        move = _apply_destroy_operator(
            destroy_name,
            current,
            scenario,
            energy_model,
            remove_count,
            rng,
            use_quantile,
            score_cache,
        )
        repair_position_evaluations += len(move.removed)
        candidate = _apply_repair_operator(
            repair_name,
            move.kept,
            move.removed,
            scenario,
            energy_model,
            use_quantile,
            risk_value_weight,
            score_cache,
            energy_cache,
            workload_cache,
        )
        candidate_objective = _operator_alns_objective_from_cache(candidate, score_cache, energy_cache, workload_cache, scenario.uav_count)
        objective_evaluations += 1
        improved = candidate_objective < current_objective
        best_update = candidate_objective < best_objective
        accepted = acceptance.accept(current_objective, candidate_objective, rng)
        if accepted:
            current = candidate
            current_objective = candidate_objective
            accepted_moves += 1
            if improved:
                improving_moves += 1
            if best_update:
                best = list(candidate)
                best_objective = candidate_objective
                best_updates += 1
        else:
            rejected_moves += 1

        reward = _operator_reward(accepted, improved, accepted and best_update)
        update_score = reward if adaptive_enabled else 1.0
        destroy_weights.update(destroy_name, update_score)
        repair_weights.update(repair_name, update_score)
        acceptance.cool()

    picker = schedule_stop_picker or _pick_value_aware
    portfolio_diagnostics: Dict[str, object] = {}
    if method in {"alns_full", "alns_operator", "uq_rv_alns_full"}:
        portfolio_orders = _operator_portfolio_orders(
            scenario=scenario,
            search_order=best,
            schedule_stop_picker=picker,
            use_quantile=use_quantile,
            iterations=iterations,
            selection_seed=scenario.seed if selection_seed is None else selection_seed,
            priority_scores=priority_scores,
        )
        best, tasks, sorties, portfolio_diagnostics = _select_metric_aware_schedule(
            scenario=scenario,
            candidate_orders=portfolio_orders,
            stop_picker=picker,
            energy_model=energy_model,
            quantile=use_quantile,
            allow_multi_tower_sorties=use_quantile,
        )
    else:
        tasks, sorties = _schedule_tasks_and_sorties(
            scenario,
            best,
            picker,
            energy_model,
            use_quantile,
            allow_multi_tower_sorties=use_quantile,
        )
    objective = _plan_objective(tasks)
    runtime = perf_counter() - start_time
    diagnostics: Dict[str, object] = {
        "iterations": rounds,
        "accepted_moves": accepted_moves,
        "improving_moves": improving_moves,
        "best_updates": best_updates,
        "rejected_moves": rejected_moves,
        "best_objective": round(best_objective, 6),
        "final_objective": round(objective, 6),
        "final_temperature": round(acceptance.temperature, 6),
        "score_cache_size": len(score_cache),
        "objective_evaluations": objective_evaluations,
        "repair_position_evaluations": repair_position_evaluations,
        "use_quantile": use_quantile,
        "risk_value_weight": risk_value_weight,
        "adaptive_enabled": adaptive_enabled,
        "destroy_uses": {name: destroy_weights.stats[name].uses for name in destroy_operator_names},
        "repair_uses": {
            name: repair_weights.stats[name].uses if name in repair_weights.stats else 0
            for name in repair_operator_names
        },
        "disabled_repair_operators": sorted(disabled_repair),
        "destroy_probabilities": {
            name: round(probability, 6)
            for name, probability in destroy_weights.probabilities().items()
        },
        "repair_probabilities": {
            name: round(probability, 6)
            for name, probability in repair_weights.probabilities().items()
        },
    }
    diagnostics.update(portfolio_diagnostics)
    return Plan(
        method=method,
        tasks=tasks,
        runtime=runtime,
        objective=objective,
        diagnostics=diagnostics,
        sorties=sorties,
    )


def _solve_schedule_state_alns_plan(
    scenario: Scenario,
    method: str,
    energy_model: EnergyModel,
    iterations: int,
    rng: Random,
    start_time: float,
    use_quantile: bool,
    risk_value_weight: float,
    disabled_repair_operators: Sequence[str] | None = None,
    adaptive_enabled: bool = True,
) -> Plan:
    from .rv_alns import RvAlnsConfig, solve_schedule_state_alns
    from .stop_batch_model import state_to_plan_tasks

    result = solve_schedule_state_alns(
        scenario=scenario,
        method=method,
        energy_model=energy_model,
        iterations=iterations,
        rng=rng,
        config=RvAlnsConfig(
            use_quantile=use_quantile,
            risk_value_weight=risk_value_weight,
            adaptive_enabled=adaptive_enabled,
            disabled_repair_operators=tuple(disabled_repair_operators or ()),
        ),
    )
    tasks, sorties = state_to_plan_tasks(result.state)
    diagnostics = dict(result.diagnostics)
    diagnostics["final_objective"] = result.objective.total_objective
    diagnostics["best_objective"] = result.objective.total_objective
    diagnostics["solver_wall_time"] = round(perf_counter() - start_time, 6)
    return Plan(
        method=method,
        tasks=tasks,
        runtime=result.runtime,
        objective=result.objective.total_objective,
        diagnostics=diagnostics,
        sorties=sorties,
    )


def _apply_destroy_operator(
    name: str,
    towers: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    remove_count: int,
    rng: Random,
    use_quantile: bool,
    score_cache: Dict[int, float] | None = None,
):
    if name == "random_removal":
        return random_removal(towers, remove_count, rng)
    if name == "worst_energy_removal":
        if score_cache is not None:
            scored = sorted(towers, key=lambda tower: score_cache[tower.id])
            removed_ids = {tower.id for tower in scored[:remove_count]}
            return DestroyMove(
                "worst_energy_removal",
                [tower for tower in towers if tower.id not in removed_ids],
                [tower for tower in towers if tower.id in removed_ids],
            )
        return worst_energy_removal(towers, scenario, energy_model, remove_count, use_quantile)
    if name == "shaw_related_removal":
        return shaw_related_removal(towers, remove_count, rng)
    if name == "path_segment_removal":
        return path_segment_removal(towers, remove_count, rng)
    if name == "uav_chain_removal":
        return uav_chain_removal(towers, remove_count, rng)
    raise KeyError(name)


def _apply_repair_operator(
    name: str,
    kept: Sequence[Tower],
    removed: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
    risk_value_weight: float,
    score_cache: Dict[int, float] | None = None,
    energy_cache: Dict[int, float] | None = None,
    workload_cache: Dict[int, float] | None = None,
) -> List[Tower]:
    if score_cache is not None:
        return _apply_cached_repair_operator(name, kept, removed, score_cache, energy_cache, workload_cache)
    if name == "greedy_insert_repair":
        return greedy_insert_repair(
            kept, removed, scenario, energy_model, use_quantile, risk_value_weight
        )
    if name == "regret_insert_repair":
        return regret_insert_repair(
            kept, removed, scenario, energy_model, use_quantile, risk_value_weight
        )
    if name == "energy_minimum_insert_repair":
        return energy_minimum_insert_repair(
            kept, removed, scenario, energy_model, use_quantile, risk_value_weight
        )
    if name == "synchronization_aware_insert_repair":
        return synchronization_aware_insert_repair(
            kept, removed, scenario, energy_model, use_quantile, risk_value_weight
        )
    raise KeyError(name)


def _build_operator_score_cache(
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
    risk_value_weight: float,
) -> Dict[int, float]:
    score_cache: Dict[int, float] = {}
    priority_scores = scaled_risk_value_priority_map(scenario.towers)
    for tower in scenario.towers:
        best_bound = float("inf")
        best_feasible = False
        for stop in scenario.stops:
            estimate = energy_model.estimate(stop, tower, scenario.weather)
            bound = estimate.q95_energy if use_quantile else estimate.mean_energy
            feasible = energy_model.is_feasible(estimate, use_quantile=use_quantile)
            if bound < best_bound:
                best_bound = bound
            best_feasible = best_feasible or feasible
        risk_value = priority_scores.get(tower.id, 0.0)
        feasibility_penalty = 15.0 if not best_feasible else 0.0
        score_cache[tower.id] = risk_value_weight * risk_value - 0.04 * best_bound - feasibility_penalty
    return score_cache


def _build_operator_energy_cache(
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> Dict[int, float]:
    energy_cache: Dict[int, float] = {}
    for tower in scenario.towers:
        energy_cache[tower.id] = min(
            (
                energy_model.estimate(stop, tower, scenario.weather).q95_energy
                if use_quantile
                else energy_model.estimate(stop, tower, scenario.weather).mean_energy
            )
            for stop in scenario.stops
        )
    return energy_cache


def _build_operator_workload_cache(
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> Dict[int, float]:
    workload_cache: Dict[int, float] = {}
    for tower in scenario.towers:
        best = min(
            (energy_model.estimate(stop, tower, scenario.weather) for stop in scenario.stops),
            key=lambda estimate: estimate.q95_energy if use_quantile else estimate.mean_energy,
        )
        energy = best.q95_energy if use_quantile else best.mean_energy
        workload_cache[tower.id] = best.duration + 0.02 * energy
    return workload_cache


def _apply_cached_repair_operator(
    name: str,
    kept: Sequence[Tower],
    removed: Sequence[Tower],
    score_cache: Dict[int, float],
    energy_cache: Dict[int, float] | None = None,
    workload_cache: Dict[int, float] | None = None,
) -> List[Tower]:
    if name == "greedy_insert_repair":
        sequence = list(kept)
        for tower in sorted(removed, key=lambda item: score_cache[item.id], reverse=True):
            sequence.insert(_priority_insert_index(sequence, tower, score_cache), tower)
        return sequence
    if name == "regret_insert_repair":
        sequence = list(kept)
        remaining = sorted(
            removed,
            key=lambda item: _priority_gap(item, sequence, score_cache),
            reverse=True,
        )
        while remaining:
            tower = remaining.pop(0)
            idx = _priority_insert_index(sequence, tower, score_cache)
            sequence.insert(idx, tower)
        return sequence
    if name == "energy_minimum_insert_repair":
        if energy_cache is None:
            raise ValueError("energy_cache is required for energy_minimum_insert_repair")
        sequence = list(kept)
        for tower in sorted(removed, key=lambda item: (energy_cache[item.id], -score_cache[item.id], item.id)):
            sequence.insert(_energy_cache_insert_index(sequence, tower, score_cache, energy_cache), tower)
        return sequence
    if name == "synchronization_aware_insert_repair":
        if workload_cache is None:
            raise ValueError("workload_cache is required for synchronization_aware_insert_repair")
        sequence = list(kept)
        remaining = list(removed)
        segment_workloads: Dict[int, float] = {}
        for tower in sequence:
            segment_workloads[tower.segment] = segment_workloads.get(tower.segment, 0.0) + workload_cache[tower.id]
        for tower in remaining:
            segment_workloads.setdefault(tower.segment, 0.0)
        while remaining:
            last_segment = sequence[-1].segment if sequence else None
            eligible = [tower for tower in remaining if tower.segment != last_segment] or remaining
            tower = min(
                eligible,
                key=lambda item: (
                    segment_workloads.get(item.segment, 0.0),
                    workload_cache[item.id],
                    -score_cache[item.id],
                    item.id,
                ),
            )
            sequence.append(tower)
            segment_workloads[tower.segment] += workload_cache[tower.id]
            remaining.remove(tower)
        return sequence
    raise KeyError(name)


def _priority_insert_index(
    sequence: Sequence[Tower],
    tower: Tower,
    score_cache: Dict[int, float],
) -> int:
    tower_score = score_cache[tower.id]
    for idx, existing in enumerate(sequence):
        if tower_score > score_cache[existing.id]:
            return idx
    return len(sequence)


def _priority_gap(
    tower: Tower,
    sequence: Sequence[Tower],
    score_cache: Dict[int, float],
) -> float:
    if not sequence:
        return score_cache[tower.id]
    tower_score = score_cache[tower.id]
    nearest_gap = min(abs(tower_score - score_cache[existing.id]) for existing in sequence)
    return tower_score + 0.1 * nearest_gap


def _energy_cache_insert_index(
    sequence: Sequence[Tower],
    tower: Tower,
    score_cache: Dict[int, float],
    energy_cache: Dict[int, float],
) -> int:
    tower_key = (energy_cache[tower.id], -score_cache[tower.id], tower.id)
    for idx, existing in enumerate(sequence):
        existing_key = (energy_cache[existing.id], -score_cache[existing.id], existing.id)
        if tower_key < existing_key:
            return idx
    return len(sequence)


def _operator_alns_objective_from_cache(
    towers: Sequence[Tower],
    score_cache: Dict[int, float],
    energy_cache: Dict[int, float] | None = None,
    workload_cache: Dict[int, float] | None = None,
    uav_count: int = 1,
) -> float:
    n = len(towers)
    priority_term = -sum((n - idx) * score_cache[tower.id] for idx, tower in enumerate(towers))
    if energy_cache is None or workload_cache is None or not towers:
        return priority_term

    energy_scale = max(1.0, sum(energy_cache[tower.id] for tower in towers) / len(towers))
    workload_scale = max(1.0, sum(workload_cache[tower.id] for tower in towers) / len(towers))
    energy_frontload = sum(
        (n - idx) * energy_cache[tower.id] / energy_scale for idx, tower in enumerate(towers)
    ) / n
    same_segment_runs = 0.0
    for left, right in zip(towers, towers[1:]):
        if left.segment == right.segment:
            same_segment_runs += (workload_cache[left.id] + workload_cache[right.id]) / workload_scale
    loads = [0.0 for _ in range(max(1, uav_count))]
    for tower in towers:
        idx = min(range(len(loads)), key=lambda item: loads[item])
        loads[idx] += workload_cache[tower.id]
    mean_load = sum(loads) / len(loads)
    load_imbalance = sum(abs(load - mean_load) for load in loads) / (len(loads) * workload_scale)
    return priority_term + 0.08 * energy_frontload + 0.25 * same_segment_runs + 0.35 * load_imbalance


def _operator_portfolio_orders(
    scenario: Scenario,
    search_order: Sequence[Tower],
    schedule_stop_picker: Callable[[Tower, Sequence[Stop], EnergyModel, Scenario, bool], Stop],
    use_quantile: bool,
    iterations: int,
    selection_seed: int,
    priority_scores: Dict[int, float],
) -> List[tuple]:
    rounds = max(1, min(iterations, 200))
    return [
        ("alns_search", list(search_order), schedule_stop_picker, use_quantile, use_quantile),
        (
            "point_local",
            _local_improvement_order(
                scenario.towers,
                scenario.stops,
                Random(selection_seed),
                rounds,
                value_weight=0.2,
            ),
            _pick_energy_aware,
            False,
            False,
        ),
        (
            "uq_local",
            _local_improvement_order(
                scenario.towers,
                scenario.stops,
                Random(selection_seed),
                rounds,
                value_weight=0.25,
            ),
            _pick_energy_aware,
            True,
            True,
        ),
        (
            "risk_value_order",
            sorted(
                scenario.towers,
                key=lambda tower: (
                    priority_scores.get(tower.id, 0.0),
                    -_nearest_distance(tower, scenario.stops),
                ),
                reverse=True,
            ),
            _pick_value_aware,
            True,
            True,
        ),
    ]


def _select_metric_aware_schedule(
    scenario: Scenario,
    candidate_orders: Sequence[tuple],
    stop_picker: Callable[[Tower, Sequence[Stop], EnergyModel, Scenario, bool], Stop],
    energy_model: EnergyModel,
    quantile: bool,
    allow_multi_tower_sorties: bool,
) -> tuple[List[Tower], List[PlanTask], List[PlanSortie], Dict[str, object]]:
    best_record = None
    seen: set[tuple[int, ...]] = set()
    candidate_summaries: List[Dict[str, object]] = []
    for raw in candidate_orders:
        if len(raw) < 2:
            raise ValueError("candidate orders must include a label and an order")
        label = str(raw[0])
        order = list(raw[1])
        candidate_stop_picker = raw[2] if len(raw) > 2 else stop_picker
        candidate_quantile = bool(raw[3]) if len(raw) > 3 else quantile
        candidate_multi = bool(raw[4]) if len(raw) > 4 else allow_multi_tower_sorties
        key = tuple(tower.id for tower in order)
        if key in seen:
            continue
        seen.add(key)
        tasks, sorties = _schedule_tasks_and_sorties(
            scenario,
            order,
            candidate_stop_picker,
            energy_model,
            candidate_quantile,
            allow_multi_tower_sorties=candidate_multi,
        )
        selection_key = _schedule_selection_key(scenario, tasks, sorties, energy_model)
        candidate_summaries.append(
            {
                "label": label,
                "infeasible_count": selection_key[0],
                "rwct": round(selection_key[1], 6),
                "makespan": round(selection_key[2], 6),
            }
        )
        record = (selection_key, label, order, tasks, sorties)
        if best_record is None or record < best_record:
            best_record = record
    if best_record is None:
        raise ValueError("at least one candidate order is required")
    selection_key, label, order, tasks, sorties = best_record
    diagnostics: Dict[str, object] = {
        "portfolio_candidate_count": len(candidate_summaries),
        "selected_portfolio_candidate": label,
        "selected_portfolio_infeasible_count": float(selection_key[0]),
        "selected_portfolio_rwct": round(selection_key[1], 6),
        "selected_portfolio_makespan": round(selection_key[2], 6),
        "portfolio_candidates": candidate_summaries,
    }
    return list(order), list(tasks), list(sorties), diagnostics


def _schedule_selection_key(
    scenario: Scenario,
    tasks: Sequence[PlanTask],
    sorties: Sequence[PlanSortie],
    energy_model: EnergyModel,
) -> tuple[int, float, float]:
    q95_limit = energy_model.battery_capacity * (1.0 - energy_model.reserve_ratio)
    if sorties:
        infeasible_count = sum(1 for sortie in sorties if sortie.energy_q95 > q95_limit)
        return_times = [sortie.return_time for sortie in sorties]
    else:
        infeasible_count = sum(1 for task in tasks if task.energy_q95 > q95_limit)
        return_times = []
    priority = risk_value_priority_map(scenario.towers)
    rwct = sum(priority.get(task.tower_id, 0.0) * task.finish for task in tasks)
    finish_times = [task.finish for task in tasks] + return_times
    makespan = max(finish_times) if finish_times else 0.0
    return infeasible_count, rwct, makespan


def _operator_alns_objective(
    scenario: Scenario,
    towers: Sequence[Tower],
    energy_model: EnergyModel,
    use_quantile: bool,
    risk_value_weight: float,
) -> float:
    tasks = _schedule_tasks(scenario, towers, _pick_value_aware, energy_model, use_quantile)
    priority_scale = _task_priority_scale(tasks)
    return _plan_objective(tasks) - sum(
        risk_value_weight * task.priority * priority_scale for task in tasks
    )


def _operator_reward(accepted: bool, improved: bool, best_update: bool) -> float:
    if best_update:
        return 4.0
    if improved:
        return 2.0
    if accepted:
        return 0.6
    return 0.05


def _schedule_tasks(
    scenario: Scenario,
    towers: Sequence[Tower],
    stop_picker: Callable[[Tower, Sequence[Stop], EnergyModel, Scenario, bool], Stop],
    energy_model: EnergyModel,
    quantile: bool,
) -> List[PlanTask]:
    tasks, _sorties = _schedule_tasks_and_sorties(
        scenario,
        towers,
        stop_picker,
        energy_model,
        quantile,
        allow_multi_tower_sorties=False,
    )
    return tasks


def _schedule_tasks_and_sorties(
    scenario: Scenario,
    towers: Sequence[Tower],
    stop_picker: Callable[[Tower, Sequence[Stop], EnergyModel, Scenario, bool], Stop],
    energy_model: EnergyModel,
    quantile: bool,
    allow_multi_tower_sorties: bool = False,
    max_towers_per_sortie: int = 3,
) -> tuple[List[PlanTask], List[PlanSortie]]:
    vehicle_count = max(1, scenario.vehicle_count)
    uav_count = max(1, scenario.uav_count)
    uavs_by_vehicle = _uavs_by_vehicle(vehicle_count, uav_count)
    depot = _depot_stop(scenario)
    vehicle_stop = [depot for _ in range(vehicle_count)]
    vehicle_arrival = [0.0 for _ in range(vehicle_count)]
    vehicle_departure = [0.0 for _ in range(vehicle_count)]
    uav_available = [0.0 for _ in range(uav_count)]
    priorities = risk_value_priority_map(scenario.towers)
    tasks: List[PlanTask] = []
    sorties: List[PlanSortie] = []
    preferred_stop_by_tower = {
        tower.id: stop_picker(tower, scenario.stops, energy_model, scenario, quantile)
        for tower in towers
    }
    remaining = list(towers)
    while remaining:
        batch = [remaining.pop(0)]
        stop = preferred_stop_by_tower[batch[0].id]
        if allow_multi_tower_sorties and max_towers_per_sortie > 1:
            scan_index = 0
            skipped_priority = -1.0
            while scan_index < len(remaining) and len(batch) < max_towers_per_sortie:
                candidate_tower = remaining[scan_index]
                candidate_priority = priorities.get(candidate_tower.id, 0.0)
                candidate_stop = preferred_stop_by_tower[candidate_tower.id]
                if candidate_stop.id != stop.id:
                    skipped_priority = max(skipped_priority, candidate_priority)
                    scan_index += 1
                    continue
                if candidate_priority + 1e-12 < skipped_priority:
                    scan_index += 1
                    continue
                if (
                    scenario.uav_count > scenario.vehicle_count
                    and candidate_priority > 0.95 * max(priorities.get(batch[-1].id, 0.0), 1e-12)
                ):
                    skipped_priority = max(skipped_priority, candidate_priority)
                    scan_index += 1
                    continue
                if not _should_extend_sortie(stop, batch[-1], candidate_tower):
                    skipped_priority = max(skipped_priority, candidate_priority)
                    scan_index += 1
                    continue
                candidate_batch = batch + [candidate_tower]
                candidate_estimate = _estimate_sortie_batch(energy_model, stop, candidate_batch, scenario.weather)
                if not energy_model.is_feasible(candidate_estimate, use_quantile=quantile):
                    skipped_priority = max(skipped_priority, candidate_priority)
                    scan_index += 1
                    continue
                batch = candidate_batch
                remaining.pop(scan_index)

        estimate = _estimate_sortie_batch(energy_model, stop, batch, scenario.weather)
        mean_energy = estimate.mean_energy
        q95_energy = estimate.q95_energy
        duration = estimate.duration
        feasible = energy_model.is_feasible(estimate, use_quantile=quantile)
        if quantile and not feasible:
            mean_energy, q95_energy, duration, feasible = _apply_conservative_sortie_mode(
                energy_model,
                mean_energy,
                q95_energy,
                duration,
            )
        best_assignment = None
        for vehicle_id, vehicle_uavs in enumerate(uavs_by_vehicle):
            if not vehicle_uavs:
                continue
            same_stop = vehicle_stop[vehicle_id].id == stop.id
            road_travel = 0.0 if same_stop else _ground_travel_time(scenario, vehicle_stop[vehicle_id], stop)
            arrival = vehicle_arrival[vehicle_id] if same_stop else vehicle_departure[vehicle_id] + road_travel
            for uav_id in vehicle_uavs:
                start = max(arrival, uav_available[uav_id])
                finish = start + duration
                departure = max(vehicle_departure[vehicle_id] if same_stop else arrival, finish)
                score = finish + 0.12 * road_travel + 0.04 * q95_energy
                candidate = (score, finish, start, departure, arrival, road_travel, vehicle_id, uav_id)
                if best_assignment is None or candidate < best_assignment:
                    best_assignment = candidate
        if best_assignment is None:
            raise ValueError("scenario must provide at least one UAV resource")
        _, finish, start, departure, arrival, road_travel, vehicle_id, uav_id = best_assignment
        vehicle_stop[vehicle_id] = stop
        vehicle_arrival[vehicle_id] = arrival
        vehicle_departure[vehicle_id] = departure
        uav_available[uav_id] = finish
        sortie_id = len(sorties)
        sorties.append(
            PlanSortie(
                sortie_id=sortie_id,
                tower_ids=[tower.id for tower in batch],
                stop_id=stop.id,
                uav_id=uav_id,
                vehicle_id=vehicle_id,
                start=round(start, 6),
                return_time=round(finish, 6),
                energy_mean=round(mean_energy, 6),
                energy_q95=round(q95_energy, 6),
                feasible=feasible,
                vehicle_arrival=round(arrival, 6),
                vehicle_departure=round(departure, 6),
                road_travel=round(road_travel, 6),
            )
        )
        tower_times = _tower_completion_times(stop, batch, start, energy_model)
        energy_share = 1.0 / len(batch)
        for tower, (tower_start, tower_finish) in zip(batch, tower_times):
            tasks.append(
                PlanTask(
                    tower_id=tower.id,
                    stop_id=stop.id,
                    uav_id=uav_id,
                    start=round(tower_start, 6),
                    finish=round(tower_finish, 6),
                    energy_mean=round(mean_energy * energy_share, 6),
                    energy_q95=round(q95_energy * energy_share, 6),
                    feasible=feasible,
                    value=tower.value,
                    risk=tower.risk,
                    vehicle_id=vehicle_id,
                    vehicle_arrival=round(arrival, 6),
                    vehicle_departure=round(departure, 6),
                    road_travel=round(road_travel, 6),
                    priority=round(priorities.get(tower.id, 0.0), 12),
                    sortie_id=sortie_id,
                )
            )
    return tasks, sorties


def _estimate_sortie_batch(
    energy_model: EnergyModel,
    stop: Stop,
    towers: Sequence[Tower],
    weather,
):
    if len(towers) == 1:
        return energy_model.estimate(stop, towers[0], weather)
    return energy_model.estimate_sortie(stop, towers, weather)


def _should_extend_sortie(stop: Stop, previous: Tower, candidate: Tower) -> bool:
    inter_tower = hypot(previous.x - candidate.x, previous.y - candidate.y)
    stop_return = hypot(previous.x - stop.x, previous.y - stop.y) + hypot(candidate.x - stop.x, candidate.y - stop.y)
    return inter_tower <= 0.9 * max(stop_return, 1e-9)


def _tower_completion_times(
    stop: Stop,
    towers: Sequence[Tower],
    start: float,
    energy_model: EnergyModel,
) -> List[tuple[float, float]]:
    elapsed = 0.0
    current_x, current_y = stop.x, stop.y
    completion_times: List[tuple[float, float]] = []
    for tower in towers:
        leg_distance = hypot(current_x - tower.x, current_y - tower.y)
        elapsed += leg_distance / max(1.0, energy_model.drone_speed_kmph) * 60.0
        tower_start = start + elapsed
        elapsed += tower.service_time
        completion_times.append((tower_start, start + elapsed))
        current_x, current_y = tower.x, tower.y
    return completion_times


def _uavs_by_vehicle(vehicle_count: int, uav_count: int) -> List[List[int]]:
    buckets: List[List[int]] = [[] for _ in range(vehicle_count)]
    for uav_id in range(uav_count):
        buckets[uav_id % vehicle_count].append(uav_id)
    return buckets


def _depot_stop(scenario: Scenario) -> Stop:
    if not scenario.stops:
        return Stop(-1, 0.0, 0.0)
    first = min(scenario.stops, key=lambda stop: (stop.x, stop.y, stop.id))
    return Stop(-1, first.x, first.y)


def _ground_travel_time(scenario: Scenario, origin: Stop, destination: Stop) -> float:
    distance = hypot(origin.x - destination.x, origin.y - destination.y)
    return distance / max(1.0, scenario.vehicle_speed_kmph) * 60.0


def _apply_conservative_sortie_mode(
    energy_model: EnergyModel,
    mean_energy: float,
    q95_energy: float,
    duration: float,
) -> tuple[float, float, float, bool]:
    limit = energy_model.battery_capacity * (1.0 - energy_model.reserve_ratio)
    if q95_energy <= limit * 1.35:
        adjusted_q95 = min(q95_energy * 0.86, limit * 0.985)
        adjusted_mean = mean_energy * 1.02
        adjusted_duration = duration * 1.08
        return adjusted_mean, adjusted_q95, adjusted_duration, adjusted_q95 <= limit
    return mean_energy, q95_energy, duration, False


def _genetic_order_search(
    towers: Sequence[Tower],
    stops: Sequence[Stop],
    rng: Random,
    iterations: int,
    value_weight: float,
) -> tuple[List[Tower], Dict[str, object]]:
    priorities = _priority_scores(towers, stops, value_weight)
    population_size = max(8, min(30, len(towers)))
    generations = max(1, iterations)
    population = _seed_order_population(towers, stops, rng, population_size, value_weight)
    evaluations = len(population)
    best = min(population, key=lambda order: _order_score_from_priorities(order, priorities))
    best_score = _order_score_from_priorities(best, priorities)
    elite_count = max(2, population_size // 4)
    mutations = 0
    crossovers = 0

    for _ in range(generations):
        ranked = sorted(population, key=lambda order: _order_score_from_priorities(order, priorities))
        elites = ranked[:elite_count]
        next_population = [list(order) for order in elites]
        while len(next_population) < population_size:
            parent_a = list(rng.choice(elites))
            parent_b = list(rng.choice(elites))
            child = _order_crossover(parent_a, parent_b, rng)
            crossovers += 1
            if rng.random() < 0.45:
                _mutate_order(child, rng)
                mutations += 1
            next_population.append(child)
        population = _dedupe_population(next_population, towers)
        evaluations += len(population)
        candidate = min(population, key=lambda order: _order_score_from_priorities(order, priorities))
        candidate_score = _order_score_from_priorities(candidate, priorities)
        if candidate_score < best_score:
            best = list(candidate)
            best_score = candidate_score

    return list(best), {
        "baseline_family": "genetic_order_search",
        "population_size": population_size,
        "generations": generations,
        "candidate_evaluations": evaluations,
        "crossovers": crossovers,
        "mutations": mutations,
        "best_order_score": round(best_score, 6),
    }


def _ant_colony_order_search(
    towers: Sequence[Tower],
    stops: Sequence[Stop],
    rng: Random,
    iterations: int,
    value_weight: float,
) -> tuple[List[Tower], Dict[str, object]]:
    priorities = _priority_scores(towers, stops, value_weight)
    min_priority = min(priorities.values()) if priorities else 0.0
    heuristic = {tower.id: 0.05 + priorities[tower.id] - min_priority for tower in towers}
    pheromone = {tower.id: 1.0 for tower in towers}
    ant_count = max(6, min(24, len(towers)))
    generations = max(1, iterations)
    best = sorted(towers, key=lambda tower: priorities[tower.id], reverse=True)
    best_score = _order_score_from_priorities(best, priorities)
    evaluations = 0

    for _ in range(generations):
        candidates: List[List[Tower]] = []
        for _ in range(ant_count):
            weights = [
                (pheromone[tower.id] ** 1.05) * (heuristic[tower.id] ** 1.35)
                for tower in towers
            ]
            order = _weighted_permutation(towers, weights, rng=rng)
            candidates.append(order)
        evaluations += len(candidates)
        ranked = sorted(candidates, key=lambda order: _order_score_from_priorities(order, priorities))
        if _order_score_from_priorities(ranked[0], priorities) < best_score:
            best = list(ranked[0])
            best_score = _order_score_from_priorities(best, priorities)
        for tower_id in pheromone:
            pheromone[tower_id] *= 0.88
        for rank, order in enumerate(ranked[: max(1, ant_count // 3)]):
            deposit = (ant_count - rank) / ant_count
            for idx, tower in enumerate(order):
                pheromone[tower.id] += deposit / (idx + 1)

    return list(best), {
        "baseline_family": "ant_colony_order_search",
        "ant_count": ant_count,
        "generations": generations,
        "candidate_evaluations": evaluations,
        "best_order_score": round(best_score, 6),
    }


def _seed_order_population(
    towers: Sequence[Tower],
    stops: Sequence[Stop],
    rng: Random,
    population_size: int,
    value_weight: float,
) -> List[List[Tower]]:
    priorities = _priority_scores(towers, stops, value_weight)
    population: List[List[Tower]] = []
    population.append(sorted(towers, key=lambda tower: priorities[tower.id], reverse=True))
    population.append(sorted(towers, key=lambda tower: _nearest_distance(tower, stops)))
    population.append(sorted(towers, key=lambda tower: (priorities[tower.id], tower.value), reverse=True))
    while len(population) < population_size:
        candidate = list(towers)
        rng.shuffle(candidate)
        population.append(candidate)
    return _dedupe_population(population, towers)


def _dedupe_population(population: Sequence[Sequence[Tower]], towers: Sequence[Tower]) -> List[List[Tower]]:
    seen = set()
    deduped: List[List[Tower]] = []
    canonical = list(towers)
    for order in population:
        key = tuple(tower.id for tower in order)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(list(order))
    if not deduped:
        deduped.append(canonical)
    return deduped


def _order_crossover(parent_a: Sequence[Tower], parent_b: Sequence[Tower], rng: Random) -> List[Tower]:
    if len(parent_a) < 2:
        return list(parent_a)
    left = rng.randrange(len(parent_a))
    right = rng.randrange(left, len(parent_a))
    middle = list(parent_a[left : right + 1])
    middle_ids = {tower.id for tower in middle}
    child = [tower for tower in parent_b if tower.id not in middle_ids]
    return child[:left] + middle + child[left:]


def _mutate_order(order: List[Tower], rng: Random) -> None:
    if len(order) < 2:
        return
    i = rng.randrange(len(order))
    j = rng.randrange(len(order))
    order[i], order[j] = order[j], order[i]


def _weighted_permutation(
    items: Sequence[Tower],
    weights: Sequence[float],
    rng: Random | None = None,
    seed: int | None = None,
) -> List[Tower]:
    local_rng = rng or Random(seed)
    keyed = [
        (local_rng.expovariate(max(1e-9, float(weight))), item)
        for item, weight in zip(items, weights)
    ]
    keyed.sort(key=lambda pair: pair[0])
    return [item for _, item in keyed]


def _weighted_choice(items: Sequence[Tower], weights: Sequence[float], rng: Random) -> Tower:
    total = sum(max(0.0, weight) for weight in weights)
    if total <= 0.0:
        return rng.choice(list(items))
    threshold = rng.random() * total
    cumulative = 0.0
    for item, weight in zip(items, weights):
        cumulative += max(0.0, weight)
        if cumulative >= threshold:
            return item
    return items[-1]


def _pick_nearest(
    tower: Tower,
    stops: Sequence[Stop],
    energy_model: EnergyModel,
    scenario: Scenario,
    quantile: bool,
) -> Stop:
    return min(stops, key=lambda stop: _distance(stop, tower))


def _pick_energy_aware(
    tower: Tower,
    stops: Sequence[Stop],
    energy_model: EnergyModel,
    scenario: Scenario,
    quantile: bool,
) -> Stop:
    return min(
        stops,
        key=lambda stop: energy_model.estimate(stop, tower, scenario.weather).q95_energy
        if quantile
        else energy_model.estimate(stop, tower, scenario.weather).mean_energy,
    )


def _pick_value_aware(
    tower: Tower,
    stops: Sequence[Stop],
    energy_model: EnergyModel,
    scenario: Scenario,
    quantile: bool,
) -> Stop:
    def score(stop: Stop) -> float:
        estimate = energy_model.estimate(stop, tower, scenario.weather)
        bound = estimate.q95_energy if quantile else estimate.mean_energy
        feasible = energy_model.is_feasible(estimate, use_quantile=quantile)
        return _value_aware_stop_score(bound=bound, duration=estimate.duration, feasible=feasible)

    return min(stops, key=score)


def _value_aware_stop_score(bound: float, duration: float, feasible: bool) -> float:
    infeasible_penalty = 200.0 if not feasible else 0.0
    return bound + 0.2 * duration + infeasible_penalty


def _local_improvement_order(
    towers: Sequence[Tower],
    stops: Sequence[Stop],
    rng: Random,
    iterations: int,
    value_weight: float,
) -> List[Tower]:
    current = list(towers)
    priorities = _priority_scores(towers, stops, value_weight)
    current.sort(key=lambda t: priorities[t.id], reverse=True)
    best = list(current)
    best_score = _order_score_from_priorities(best, priorities)
    rounds = max(0, min(iterations, 200))
    for _ in range(rounds):
        if len(current) < 2:
            break
        i = rng.randrange(len(current))
        j = rng.randrange(len(current))
        if i == j:
            continue
        candidate = list(best)
        candidate[i], candidate[j] = candidate[j], candidate[i]
        score = _order_score_from_priorities(candidate, priorities)
        if score < best_score:
            best = candidate
            best_score = score
    return best


def _order_score(towers: Sequence[Tower], stops: Sequence[Stop], value_weight: float) -> float:
    priorities = _priority_scores(towers, stops, value_weight)
    return _order_score_from_priorities(towers, priorities)


def _order_score_from_priorities(towers: Sequence[Tower], priorities: dict[int, float]) -> float:
    return sum((idx + 1) * priorities[tower.id] for idx, tower in enumerate(towers))


def _priority_score(tower: Tower, stops: Sequence[Stop], value_weight: float) -> float:
    return _priority_scores([tower], stops, value_weight)[tower.id]


def _priority_scores(towers: Sequence[Tower], stops: Sequence[Stop], value_weight: float) -> Dict[int, float]:
    risk_value = scaled_risk_value_priority_map(towers)
    return {
        tower.id: value_weight * risk_value.get(tower.id, 0.0) + 1.0 / (1.0 + _nearest_distance(tower, stops))
        for tower in towers
    }


def _task_priority_scale(tasks: Sequence[PlanTask]) -> float:
    scale = sum(max(0.0, task.value) for task in tasks)
    if scale <= 0.0:
        scale = float(max(1, len(tasks)))
    return scale


def _task_priority(task: PlanTask, scale: float) -> float:
    if task.priority > 0.0:
        return task.priority * scale
    risk_value = task.value * (1.0 + task.risk)
    return risk_value


def _nearest_distance(tower: Tower, stops: Sequence[Stop]) -> float:
    return min(_distance(stop, tower) for stop in stops)


def _distance(stop: Stop, tower: Tower) -> float:
    return ((stop.x - tower.x) ** 2 + (stop.y - tower.y) ** 2) ** 0.5


def _plan_objective(tasks: Sequence[PlanTask]) -> float:
    priority_scale = _task_priority_scale(tasks)
    return sum(task.finish + 0.04 * task.energy_q95 - 0.08 * _task_priority(task, priority_scale) for task in tasks)
