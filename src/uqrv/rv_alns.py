from __future__ import annotations

from dataclasses import dataclass
from random import Random
from time import perf_counter
from typing import Dict, Iterable, List, Sequence, Tuple

from .alns_operators import AdaptiveOperatorWeights, SimulatedAnnealingAcceptance
from .energy import EnergyModel
from .priority import risk_value_priority_map
from .scenario import Scenario, Stop, Tower
from .stop_batch_model import (
    ModelParameters,
    ObjectiveBreakdown,
    ScheduleState,
    ServiceGraph,
    SortieAssignment,
    SortiePattern,
    build_service_graph,
    evaluate_schedule_state,
    objective_breakdown,
)


@dataclass(frozen=True)
class ScheduleStateAlnsResult:
    state: ScheduleState
    objective: ObjectiveBreakdown
    diagnostics: Dict[str, object]
    runtime: float


@dataclass(frozen=True)
class RvAlnsConfig:
    use_quantile: bool
    risk_value_weight: float
    adaptive_enabled: bool = True
    disabled_repair_operators: Tuple[str, ...] = ()
    max_towers_per_sortie: int = 3
    nearest_stops_per_tower: int = 4
    max_near_towers_per_stop: int = 8


DESTROY_OPERATORS = (
    "random_removal",
    "worst_energy_removal",
    "shaw_related_removal",
    "path_segment_removal",
    "uav_chain_removal",
)

REPAIR_OPERATORS = (
    "greedy_insert_repair",
    "regret_insert_repair",
    "energy_minimum_insert_repair",
    "synchronization_aware_insert_repair",
)


def solve_schedule_state_alns(
    scenario: Scenario,
    method: str,
    energy_model: EnergyModel,
    iterations: int,
    rng: Random,
    config: RvAlnsConfig,
) -> ScheduleStateAlnsResult:
    start_time = perf_counter()
    params = ModelParameters(
        max_towers_per_sortie=config.max_towers_per_sortie,
        nearest_stops_per_tower=config.nearest_stops_per_tower,
        max_near_towers_per_stop=config.max_near_towers_per_stop,
    )
    graph = build_service_graph(scenario, energy_model, params, use_quantile=config.use_quantile)
    current = _initial_state(scenario, graph, energy_model, params, method, config)
    current_obj = objective_breakdown(scenario, current, params)
    best = current
    best_obj = current_obj

    active_repair = [name for name in REPAIR_OPERATORS if name not in set(config.disabled_repair_operators)]
    if not active_repair:
        raise ValueError("at least one repair operator must remain active")
    destroy_weights = AdaptiveOperatorWeights(DESTROY_OPERATORS)
    repair_weights = AdaptiveOperatorWeights(active_repair)
    temperature = max(1.0, abs(current_obj.total_objective) * 0.03)
    acceptance = SimulatedAnnealingAcceptance(initial_temperature=temperature, cooling_rate=0.992)

    accepted_moves = 0
    improving_moves = 0
    best_updates = 0
    rejected_moves = 0
    local_search_updates = 0
    objective_evaluations = 1
    repair_position_evaluations = 0
    rounds = max(0, iterations)

    for _round in range(rounds):
        if not current.assignments:
            break
        remove_count = max(1, min(len(scenario.towers), round(len(scenario.towers) * 0.18)))
        destroy_name = destroy_weights.select(rng)
        repair_name = repair_weights.select(rng)
        removed = _select_removed_towers(destroy_name, scenario, current, graph, remove_count, rng)
        repair_position_evaluations += len(removed)
        partial_assignments, uncovered = _remove_towers(current.assignments, graph, removed)
        repaired_assignments = _repair_assignments(
            repair_name,
            scenario,
            graph,
            partial_assignments,
            uncovered,
            energy_model,
            params,
            config,
        )
        candidate = evaluate_schedule_state(
            scenario,
            graph,
            repaired_assignments,
            energy_model,
            params,
            method=method,
        )
        candidate_obj = objective_breakdown(scenario, candidate, params)
        objective_evaluations += 1

        improved = candidate_obj.total_objective < current_obj.total_objective
        best_update = candidate_obj.total_objective < best_obj.total_objective
        accepted = acceptance.accept(current_obj.total_objective, candidate_obj.total_objective, rng)
        if accepted:
            current = candidate
            current_obj = candidate_obj
            accepted_moves += 1
            if improved:
                improving_moves += 1
                if len(scenario.towers) <= 60:
                    local_candidate, local_obj = _local_search(scenario, graph, current, energy_model, params)
                    objective_evaluations += 1
                    if local_obj.total_objective < current_obj.total_objective:
                        current = local_candidate
                        current_obj = local_obj
                        candidate = local_candidate
                        candidate_obj = local_obj
                        local_search_updates += 1
            if best_update or current_obj.total_objective < best_obj.total_objective:
                best = current
                best_obj = current_obj
                best_updates += 1
        else:
            rejected_moves += 1

        reward = _operator_reward(accepted, improved, accepted and current_obj.total_objective <= best_obj.total_objective)
        update_score = reward if config.adaptive_enabled else 1.0
        destroy_weights.update(destroy_name, update_score)
        repair_weights.update(repair_name, update_score)
        acceptance.cool()

    final_obj = objective_breakdown(scenario, best, params)
    runtime = perf_counter() - start_time
    diagnostics: Dict[str, object] = {
        "implementation_family": "stop_batch_schedule_state_alns",
        "iterations": rounds,
        "accepted_moves": accepted_moves,
        "improving_moves": improving_moves,
        "best_updates": best_updates,
        "rejected_moves": rejected_moves,
        "local_search_updates": local_search_updates,
        "objective_evaluations": rounds + 1,
        "alns_objective_evaluations": rounds + 1,
        "score_cache_size": len(scenario.towers),
        "repair_position_evaluations": repair_position_evaluations,
        "alns_portfolio_candidate_count": 1.0,
        "alns_selected_portfolio_candidate": "alns_search",
        "alns_selected_portfolio_infeasible_count": float(len(best.missed_tower_ids)),
        "alns_selected_portfolio_rwct": final_obj.rwct,
        "alns_selected_portfolio_makespan": final_obj.makespan,
        "portfolio_candidate_count": 1.0,
        "selected_portfolio_candidate": "alns_search",
        "selected_portfolio_infeasible_count": float(len(best.missed_tower_ids)),
        "selected_portfolio_rwct": final_obj.rwct,
        "selected_portfolio_makespan": final_obj.makespan,
        "use_quantile": config.use_quantile,
        "risk_value_weight": config.risk_value_weight,
        "adaptive_enabled": config.adaptive_enabled,
        "disabled_repair_operators": list(config.disabled_repair_operators),
        "destroy_uses": {name: destroy_weights.stats[name].uses for name in DESTROY_OPERATORS},
        "repair_uses": {
            name: repair_weights.stats[name].uses if name in repair_weights.stats else 0
            for name in REPAIR_OPERATORS
        },
        "destroy_probabilities": {
            name: round(probability, 6)
            for name, probability in destroy_weights.probabilities().items()
        },
        "repair_probabilities": {
            name: round(probability, 6)
            for name, probability in repair_weights.probabilities().items()
        },
        "service_graph_pattern_count": graph.pattern_count,
        "service_graph_feasible_count": graph.feasible_service_count,
        "selected_sortie_count": len(best.sorties),
        "missed_service_count": len(best.missed_tower_ids),
        "duplicate_service_count": best.duplicate_service_count,
        "objective_rwct": final_obj.rwct,
        "objective_makespan": final_obj.makespan,
        "objective_ground_travel": final_obj.ground_travel,
        "objective_q95_energy": final_obj.q95_energy,
        "objective_missed_penalty": final_obj.missed_service_penalty,
        "objective_duplicate_penalty": final_obj.duplicate_service_penalty,
        "objective_total": final_obj.total_objective,
    }
    for name in DESTROY_OPERATORS:
        diagnostics[f"destroy_{name}_uses"] = float(destroy_weights.stats[name].uses)
    for name in REPAIR_OPERATORS:
        diagnostics[f"repair_{name}_uses"] = float(
            repair_weights.stats[name].uses if name in repair_weights.stats else 0
        )
    diagnostics.update(best.diagnostics)
    diagnostics["implementation_family"] = "stop_batch_schedule_state_alns"
    return ScheduleStateAlnsResult(state=best, objective=final_obj, diagnostics=diagnostics, runtime=runtime)


def _initial_state(
    scenario: Scenario,
    graph: ServiceGraph,
    energy_model: EnergyModel,
    params: ModelParameters,
    method: str,
    config: RvAlnsConfig,
) -> ScheduleState:
    priorities = risk_value_priority_map(scenario.towers)
    ordered_towers = sorted(
        scenario.towers,
        key=lambda tower: (
            priorities.get(tower.id, 0.0) if config.risk_value_weight > 0.0 else 0.0,
            -_nearest_stop_distance(tower, scenario.stops),
            -tower.risk,
            -tower.value,
        ),
        reverse=True,
    )
    uncovered = {tower.id for tower in ordered_towers}
    assignments: List[SortieAssignment] = []
    next_uav_by_vehicle = {vehicle_id: 0 for vehicle_id in range(max(1, scenario.vehicle_count))}
    while uncovered:
        seed = next((tower for tower in ordered_towers if tower.id in uncovered), None)
        if seed is None:
            break
        pattern = _choose_initial_pattern(graph, seed.id, uncovered, priorities, config)
        if pattern is None:
            uncovered.remove(seed.id)
            continue
        vehicle_id = _choose_vehicle_for_pattern(scenario, assignments, graph, pattern)
        uavs = _uavs_for_vehicle(max(1, scenario.vehicle_count), max(1, scenario.uav_count), vehicle_id)
        offset = next_uav_by_vehicle[vehicle_id] % max(1, len(uavs))
        uav_id = uavs[offset]
        next_uav_by_vehicle[vehicle_id] += 1
        assignments.append(
            SortieAssignment(
                pattern_id=pattern.pattern_id,
                vehicle_id=vehicle_id,
                uav_id=uav_id,
                sequence=len(assignments),
            )
        )
        uncovered.difference_update(pattern.tower_ids)
    return evaluate_schedule_state(scenario, graph, assignments, energy_model, params, method=method)


def _select_removed_towers(
    name: str,
    scenario: Scenario,
    state: ScheduleState,
    graph: ServiceGraph,
    remove_count: int,
    rng: Random,
) -> set[int]:
    served = sorted({task.tower_id for task in state.tasks})
    if not served:
        return set()
    remove_count = max(1, min(remove_count, len(served)))
    tower_by_id = {tower.id: tower for tower in scenario.towers}
    priority = risk_value_priority_map(scenario.towers)
    if name == "random_removal":
        return set(rng.sample(served, remove_count))
    if name == "worst_energy_removal":
        energy_by_tower: Dict[int, float] = {}
        for sortie in state.sorties:
            share = sortie.energy_q95 / max(1, len(sortie.tower_ids))
            for tower_id in sortie.tower_ids:
                energy_by_tower[tower_id] = max(energy_by_tower.get(tower_id, 0.0), share)
        ranked = sorted(
            served,
            key=lambda tower_id: (energy_by_tower.get(tower_id, 0.0), priority.get(tower_id, 0.0)),
            reverse=True,
        )
        return set(ranked[:remove_count])
    if name == "shaw_related_removal":
        seed_id = rng.choice(served)
        seed = tower_by_id[seed_id]
        ranked = sorted(
            served,
            key=lambda tower_id: (
                _tower_distance(seed, tower_by_id[tower_id]),
                abs(priority.get(seed_id, 0.0) - priority.get(tower_id, 0.0)),
                tower_id,
            ),
        )
        return set(ranked[:remove_count])
    if name == "path_segment_removal":
        segment = rng.choice(sorted({tower_by_id[tower_id].segment for tower_id in served}))
        ranked = [tower_id for tower_id in served if tower_by_id[tower_id].segment == segment]
        ranked += [tower_id for tower_id in served if tower_by_id[tower_id].segment != segment]
        return set(ranked[:remove_count])
    if name == "uav_chain_removal":
        sortie = rng.choice(state.sorties)
        removed: set[int] = set()
        for candidate in state.sorties:
            if candidate.uav_id == sortie.uav_id and candidate.vehicle_id == sortie.vehicle_id:
                removed.update(candidate.tower_ids)
                if len(removed) >= remove_count:
                    break
        return set(sorted(removed)[:remove_count])
    raise KeyError(name)


def _remove_towers(
    assignments: Sequence[SortieAssignment],
    graph: ServiceGraph,
    removed_tower_ids: Iterable[int],
) -> tuple[List[SortieAssignment], set[int]]:
    removed = set(removed_tower_ids)
    kept: List[SortieAssignment] = []
    uncovered = set(removed)
    for assignment in assignments:
        pattern = graph.get_pattern(assignment.pattern_id)
        if removed.intersection(pattern.tower_ids):
            uncovered.update(pattern.tower_ids)
        else:
            kept.append(assignment)
    return _renumber_assignments(kept), uncovered


def _repair_assignments(
    name: str,
    scenario: Scenario,
    graph: ServiceGraph,
    partial_assignments: Sequence[SortieAssignment],
    uncovered_tower_ids: Iterable[int],
    energy_model: EnergyModel,
    params: ModelParameters,
    config: RvAlnsConfig,
) -> List[SortieAssignment]:
    assignments = list(partial_assignments)
    covered = _covered_towers(assignments, graph)
    uncovered = set(uncovered_tower_ids) - covered
    priorities = risk_value_priority_map(scenario.towers)
    while uncovered:
        pattern = _choose_repair_pattern(name, graph, uncovered, priorities, config)
        if pattern is None:
            uncovered.remove(min(uncovered))
            continue
        vehicle_id = _choose_vehicle_for_pattern(scenario, assignments, graph, pattern)
        uav_id = _choose_uav_for_pattern(scenario, assignments, vehicle_id)
        assignments.append(SortieAssignment(pattern.pattern_id, vehicle_id, uav_id, sequence=len(assignments)))
        uncovered.difference_update(pattern.tower_ids)
    return _renumber_assignments(assignments)


def _local_search(
    scenario: Scenario,
    graph: ServiceGraph,
    state: ScheduleState,
    energy_model: EnergyModel,
    params: ModelParameters,
) -> tuple[ScheduleState, ObjectiveBreakdown]:
    best_state = state
    best_obj = objective_breakdown(scenario, state, params)
    for idx, assignment in enumerate(state.assignments):
        current_pattern = graph.get_pattern(assignment.pattern_id)
        alternatives = [
            pattern
            for pattern in graph.patterns
            if pattern.feasible and set(pattern.tower_ids) == set(current_pattern.tower_ids)
        ]
        alternatives.sort(key=lambda pattern: (pattern.energy_q95, pattern.duration, pattern.stop_id, pattern.tower_ids))
        for pattern in alternatives[:6]:
            if pattern.pattern_id == current_pattern.pattern_id:
                continue
            candidate_assignments = list(state.assignments)
            candidate_assignments[idx] = SortieAssignment(
                pattern.pattern_id,
                assignment.vehicle_id,
                assignment.uav_id,
                assignment.sequence,
            )
            candidate = evaluate_schedule_state(
                scenario,
                graph,
                candidate_assignments,
                energy_model,
                params,
                method=state.method,
            )
            candidate_obj = objective_breakdown(scenario, candidate, params)
            if candidate_obj.total_objective < best_obj.total_objective:
                return candidate, candidate_obj
    return best_state, best_obj


def _choose_initial_pattern(
    graph: ServiceGraph,
    seed_tower_id: int,
    uncovered: set[int],
    priorities: Dict[int, float],
    config: RvAlnsConfig,
) -> SortiePattern | None:
    candidates = _patterns_for_seed(graph, seed_tower_id, uncovered, feasible_only=True)
    if not candidates:
        candidates = _patterns_for_seed(graph, seed_tower_id, uncovered, feasible_only=False)
    if not candidates:
        return None
    return min(
        candidates,
        key=lambda pattern: (
            pattern.tower_ids[0] != seed_tower_id,
            _construction_key(pattern, priorities, config, prefer_large=True),
        ),
    )


def _choose_repair_pattern(
    name: str,
    graph: ServiceGraph,
    uncovered: set[int],
    priorities: Dict[int, float],
    config: RvAlnsConfig,
) -> SortiePattern | None:
    seed_ids = sorted(
        uncovered,
        key=lambda tower_id: (priorities.get(tower_id, 0.0), -tower_id),
        reverse=True,
    )[:5]
    candidates: List[SortiePattern] = []
    for seed_id in seed_ids:
        candidates.extend(_patterns_for_seed(graph, seed_id, uncovered, feasible_only=True))
    if not candidates:
        for seed_id in seed_ids:
            candidates.extend(_patterns_for_seed(graph, seed_id, uncovered, feasible_only=False))
    if not candidates:
        return None
    if name == "energy_minimum_insert_repair":
        return min(candidates, key=lambda pattern: (pattern.energy_q95 / len(pattern.tower_ids), -len(pattern.tower_ids)))
    if name == "synchronization_aware_insert_repair":
        return min(candidates, key=lambda pattern: (pattern.duration / len(pattern.tower_ids), pattern.stop_id, -len(pattern.tower_ids)))
    if name == "regret_insert_repair":
        seed_scores: List[tuple[float, SortiePattern]] = []
        for pattern in candidates:
            coverage_priority = sum(priorities.get(tower_id, 0.0) for tower_id in pattern.tower_ids)
            regret_proxy = coverage_priority * len(pattern.tower_ids) - 0.001 * pattern.energy_q95
            seed_scores.append((-regret_proxy, pattern))
        return min(seed_scores, key=lambda item: item[0])[1]
    return min(candidates, key=lambda pattern: _construction_key(pattern, priorities, config, prefer_large=True))


def _patterns_for_seed(
    graph: ServiceGraph,
    seed_tower_id: int,
    allowed_tower_ids: set[int],
    feasible_only: bool,
) -> List[SortiePattern]:
    candidates: List[SortiePattern] = []
    seen: set[int] = set()
    for pattern_id in graph.patterns_by_tower.get(seed_tower_id, []):
        if pattern_id in seen:
            continue
        seen.add(pattern_id)
        pattern = graph.get_pattern(pattern_id)
        if feasible_only and not pattern.feasible:
            continue
        if set(pattern.tower_ids).issubset(allowed_tower_ids):
            candidates.append(pattern)
    return candidates


def _construction_key(
    pattern: SortiePattern,
    priorities: Dict[int, float],
    config: RvAlnsConfig,
    prefer_large: bool,
) -> tuple:
    coverage = len(pattern.tower_ids)
    priority_gain = sum(priorities.get(tower_id, 0.0) for tower_id in pattern.tower_ids)
    return (
        -coverage if prefer_large else coverage,
        pattern.energy_q95 / coverage,
        pattern.duration / coverage,
        -config.risk_value_weight * priority_gain,
        pattern.stop_id,
        pattern.tower_ids,
    )


def _choose_vehicle_for_pattern(
    scenario: Scenario,
    assignments: Sequence[SortieAssignment],
    graph: ServiceGraph,
    pattern: SortiePattern,
) -> int:
    vehicle_count = max(1, scenario.vehicle_count)
    route_by_vehicle: Dict[int, List[int]] = {vehicle_id: [] for vehicle_id in range(vehicle_count)}
    count_by_vehicle = {vehicle_id: 0 for vehicle_id in range(vehicle_count)}
    for assignment in assignments:
        assigned_pattern = graph.get_pattern(assignment.pattern_id)
        route = route_by_vehicle[assignment.vehicle_id]
        if assigned_pattern.stop_id not in route:
            route.append(assigned_pattern.stop_id)
        count_by_vehicle[assignment.vehicle_id] += 1
    return min(
        range(vehicle_count),
        key=lambda vehicle_id: (
            pattern.stop_id not in route_by_vehicle[vehicle_id],
            count_by_vehicle[vehicle_id],
            vehicle_id,
        ),
    )


def _choose_uav_for_pattern(
    scenario: Scenario,
    assignments: Sequence[SortieAssignment],
    vehicle_id: int,
) -> int:
    uavs = _uavs_for_vehicle(max(1, scenario.vehicle_count), max(1, scenario.uav_count), vehicle_id)
    use_counts = {uav_id: 0 for uav_id in uavs}
    for assignment in assignments:
        if assignment.uav_id in use_counts:
            use_counts[assignment.uav_id] += 1
    return min(uavs, key=lambda uav_id: (use_counts[uav_id], uav_id))


def _uavs_for_vehicle(vehicle_count: int, uav_count: int, vehicle_id: int) -> List[int]:
    uavs = [uav_id for uav_id in range(uav_count) if uav_id % vehicle_count == vehicle_id]
    return uavs or [0]


def _covered_towers(assignments: Sequence[SortieAssignment], graph: ServiceGraph) -> set[int]:
    covered: set[int] = set()
    for assignment in assignments:
        covered.update(graph.get_pattern(assignment.pattern_id).tower_ids)
    return covered


def _renumber_assignments(assignments: Sequence[SortieAssignment]) -> List[SortieAssignment]:
    return [
        SortieAssignment(
            pattern_id=assignment.pattern_id,
            vehicle_id=assignment.vehicle_id,
            uav_id=assignment.uav_id,
            sequence=idx,
        )
        for idx, assignment in enumerate(assignments)
    ]


def _operator_reward(accepted: bool, improved: bool, best_update: bool) -> float:
    if best_update:
        return 4.0
    if improved:
        return 2.0
    if accepted:
        return 0.6
    return 0.05


def _nearest_stop_distance(tower: Tower, stops: Sequence[Stop]) -> float:
    return min(((stop.x - tower.x) ** 2 + (stop.y - tower.y) ** 2) ** 0.5 for stop in stops)


def _tower_distance(left: Tower, right: Tower) -> float:
    return ((left.x - right.x) ** 2 + (left.y - right.y) ** 2) ** 0.5
