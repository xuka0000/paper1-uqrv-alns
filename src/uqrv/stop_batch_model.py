from __future__ import annotations

from dataclasses import dataclass, field
from itertools import permutations
from math import hypot
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .energy import EnergyModel
from .priority import risk_value_priority_map
from .scenario import Scenario, Stop, Tower


@dataclass(frozen=True)
class ModelParameters:
    max_towers_per_sortie: int = 3
    nearest_stops_per_tower: int = 4
    max_near_towers_per_stop: int = 8
    lambda_r: float = 1.0
    lambda_c: float = 0.20
    lambda_g: float = 0.10
    lambda_e: float = 0.10
    r0: float = 1.0
    c0: float = 1.0
    g0: float = 1.0
    e0: float = 1.0
    missed_service_penalty: float = 1000.0
    duplicate_service_penalty: float = 500.0


@dataclass(frozen=True)
class SortiePattern:
    pattern_id: int
    stop_id: int
    tower_ids: Tuple[int, ...]
    distance: float
    duration: float
    energy_mean: float
    energy_std: float
    energy_q95: float
    endurance_limit: float
    energy_margin: float
    feasible: bool
    tower_start_offsets: Dict[int, float]
    tower_finish_offsets: Dict[int, float]


@dataclass(frozen=True)
class ServiceGraph:
    scenario_id: str
    patterns: List[SortiePattern]
    patterns_by_stop: Dict[int, List[int]]
    patterns_by_tower: Dict[int, List[int]]
    feasible_pattern_ids: List[int]

    @property
    def pattern_count(self) -> int:
        return len(self.patterns)

    @property
    def feasible_service_count(self) -> int:
        return len(self.feasible_pattern_ids)

    @property
    def pattern_by_id(self) -> Dict[int, SortiePattern]:
        return {pattern.pattern_id: pattern for pattern in self.patterns}

    def get_pattern(self, pattern_id: int) -> SortiePattern:
        if 0 <= pattern_id < len(self.patterns):
            pattern = self.patterns[pattern_id]
            if pattern.pattern_id == pattern_id:
                return pattern
        for pattern in self.patterns:
            if pattern.pattern_id == pattern_id:
                return pattern
        raise KeyError(pattern_id)

    def require_pattern(self, stop_id: int, tower_ids: Sequence[int]) -> SortiePattern:
        requested = tuple(tower_ids)
        for pattern in self.patterns:
            if pattern.stop_id == stop_id and pattern.tower_ids == requested:
                return pattern
        raise KeyError((stop_id, requested))

    def patterns_covering(
        self,
        tower_ids: Iterable[int],
        allowed_tower_ids: Iterable[int] | None = None,
        feasible_only: bool = True,
    ) -> List[SortiePattern]:
        required = set(tower_ids)
        allowed = set(allowed_tower_ids) if allowed_tower_ids is not None else None
        candidates: List[SortiePattern] = []
        for pattern in self.patterns:
            pattern_towers = set(pattern.tower_ids)
            if feasible_only and not pattern.feasible:
                continue
            if not required.issubset(pattern_towers):
                continue
            if allowed is not None and not pattern_towers.issubset(allowed):
                continue
            candidates.append(pattern)
        return sorted(
            candidates,
            key=lambda item: (
                len(item.tower_ids),
                item.energy_q95 / max(1, len(item.tower_ids)),
                item.duration,
                item.stop_id,
                item.tower_ids,
            ),
        )

    def best_pattern_covering(
        self,
        tower_ids: Iterable[int],
        allowed_tower_ids: Iterable[int] | None = None,
        feasible_only: bool = True,
    ) -> SortiePattern:
        candidates = self.patterns_covering(tower_ids, allowed_tower_ids, feasible_only)
        if not candidates:
            raise KeyError(tuple(sorted(tower_ids)))
        return candidates[0]


@dataclass(frozen=True)
class SortieAssignment:
    pattern_id: int
    vehicle_id: int
    uav_id: int
    sequence: int = 0


@dataclass(frozen=True)
class ScheduledTask:
    tower_id: int
    stop_id: int
    uav_id: int
    vehicle_id: int
    start: float
    finish: float
    energy_mean: float
    energy_q95: float
    feasible: bool
    value: float
    risk: float
    priority: float
    sortie_id: int
    vehicle_arrival: float
    vehicle_departure: float
    road_travel: float


@dataclass(frozen=True)
class ScheduledSortie:
    sortie_id: int
    pattern_id: int
    tower_ids: List[int]
    stop_id: int
    uav_id: int
    vehicle_id: int
    start: float
    return_time: float
    energy_mean: float
    energy_q95: float
    feasible: bool
    vehicle_arrival: float
    vehicle_departure: float
    road_travel: float


@dataclass(frozen=True)
class ScheduleState:
    method: str
    assignments: List[SortieAssignment]
    tasks: List[ScheduledTask]
    sorties: List[ScheduledSortie]
    route_by_vehicle: Dict[int, List[int]]
    missed_tower_ids: List[int]
    duplicate_service_count: int
    makespan: float
    ground_travel_time: float
    ground_travel_distance: float
    diagnostics: Dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ObjectiveBreakdown:
    rwct: float
    makespan: float
    ground_travel: float
    q95_energy: float
    missed_service_count: int
    duplicate_service_count: int
    missed_service_penalty: float
    duplicate_service_penalty: float
    total_objective: float


def build_service_graph(
    scenario: Scenario,
    energy_model: EnergyModel,
    params: ModelParameters | None = None,
    use_quantile: bool = True,
) -> ServiceGraph:
    params = params or ModelParameters()
    if params.max_towers_per_sortie <= 0:
        raise ValueError("max_towers_per_sortie must be positive")
    tower_by_id = {tower.id: tower for tower in scenario.towers}
    nearest_stop_ids_by_tower = _nearest_stop_ids_by_tower(
        scenario.towers, scenario.stops, params.nearest_stops_per_tower
    )
    near_towers_by_stop = _near_towers_by_stop(
        scenario.towers,
        scenario.stops,
        nearest_stop_ids_by_tower,
        params.max_near_towers_per_stop,
    )

    patterns: List[SortiePattern] = []
    seen: set[tuple[int, Tuple[int, ...]]] = set()
    for stop in sorted(scenario.stops, key=lambda item: item.id):
        near_towers = near_towers_by_stop.get(stop.id, [])
        for length in range(1, min(params.max_towers_per_sortie, len(near_towers)) + 1):
            for ordered_towers in permutations(near_towers, length):
                key = (stop.id, tuple(tower.id for tower in ordered_towers))
                if key in seen:
                    continue
                seen.add(key)
                patterns.append(
                    _make_pattern(
                        pattern_id=len(patterns),
                        stop=stop,
                        towers=ordered_towers,
                        tower_by_id=tower_by_id,
                        scenario=scenario,
                        energy_model=energy_model,
                        use_quantile=use_quantile,
                    )
                )

    stop_by_id = {stop.id: stop for stop in scenario.stops}
    for tower in scenario.towers:
        if any((stop_id, (tower.id,)) in seen for stop_id in nearest_stop_ids_by_tower[tower.id]):
            continue
        stop_id = nearest_stop_ids_by_tower[tower.id][0]
        key = (stop_id, (tower.id,))
        seen.add(key)
        patterns.append(
            _make_pattern(
                pattern_id=len(patterns),
                stop=stop_by_id[stop_id],
                towers=[tower],
                tower_by_id=tower_by_id,
                scenario=scenario,
                energy_model=energy_model,
                use_quantile=use_quantile,
            )
        )

    patterns_by_stop: Dict[int, List[int]] = {stop.id: [] for stop in scenario.stops}
    patterns_by_tower: Dict[int, List[int]] = {tower.id: [] for tower in scenario.towers}
    feasible_pattern_ids: List[int] = []
    for pattern in patterns:
        patterns_by_stop.setdefault(pattern.stop_id, []).append(pattern.pattern_id)
        for tower_id in pattern.tower_ids:
            patterns_by_tower.setdefault(tower_id, []).append(pattern.pattern_id)
        if pattern.feasible:
            feasible_pattern_ids.append(pattern.pattern_id)

    for tower_id, ids in patterns_by_tower.items():
        ids.sort(key=lambda pattern_id: _pattern_sort_key(patterns[pattern_id]))
    for stop_id, ids in patterns_by_stop.items():
        ids.sort(key=lambda pattern_id: _pattern_sort_key(patterns[pattern_id]))

    return ServiceGraph(
        scenario_id=scenario.id,
        patterns=patterns,
        patterns_by_stop=patterns_by_stop,
        patterns_by_tower=patterns_by_tower,
        feasible_pattern_ids=feasible_pattern_ids,
    )


def evaluate_schedule_state(
    scenario: Scenario,
    graph: ServiceGraph,
    assignments: Sequence[SortieAssignment],
    energy_model: EnergyModel,
    params: ModelParameters | None = None,
    method: str = "schedule_state",
) -> ScheduleState:
    params = params or ModelParameters()
    pattern_by_id = graph.pattern_by_id
    stop_by_id = {stop.id: stop for stop in scenario.stops}
    tower_by_id = {tower.id: tower for tower in scenario.towers}
    priority = risk_value_priority_map(scenario.towers)
    depot = _depot_stop(scenario)
    ordered_assignments = list(assignments)

    route_by_vehicle: Dict[int, List[int]] = {vehicle_id: [] for vehicle_id in range(max(1, scenario.vehicle_count))}
    assignment_order: Dict[int, List[tuple[int, SortieAssignment]]] = {}
    for idx, assignment in enumerate(ordered_assignments):
        pattern = pattern_by_id[assignment.pattern_id]
        route = route_by_vehicle.setdefault(assignment.vehicle_id, [])
        if pattern.stop_id not in route:
            route.append(pattern.stop_id)
        assignment_order.setdefault(assignment.vehicle_id, []).append((idx, assignment))

    tasks: List[ScheduledTask] = []
    sorties: List[ScheduledSortie] = []
    ground_distance = 0.0
    ground_time = 0.0
    return_completion = 0.0

    for vehicle_id in sorted(route_by_vehicle):
        current_stop = depot
        current_time = 0.0
        vehicle_assignments = assignment_order.get(vehicle_id, [])
        for stop_id in route_by_vehicle[vehicle_id]:
            stop = stop_by_id[stop_id]
            leg_distance = _stop_distance(current_stop, stop)
            road_travel = _travel_time(scenario, leg_distance)
            ground_distance += leg_distance
            ground_time += road_travel
            arrival = current_time + road_travel
            stop_assignments = [
                (idx, assignment)
                for idx, assignment in vehicle_assignments
                if pattern_by_id[assignment.pattern_id].stop_id == stop_id
            ]
            stop_assignments.sort(key=lambda item: (item[1].uav_id, item[1].sequence, item[0]))
            uav_available: Dict[int, float] = {
                assignment.uav_id: arrival for _idx, assignment in stop_assignments
            }
            local_sortie_records: List[tuple[int, float]] = []
            for _idx, assignment in stop_assignments:
                pattern = pattern_by_id[assignment.pattern_id]
                start = max(arrival, uav_available.get(assignment.uav_id, arrival))
                return_time = start + pattern.duration
                uav_available[assignment.uav_id] = return_time
                local_sortie_records.append((len(sorties), return_time))
                sorties.append(
                    ScheduledSortie(
                        sortie_id=len(sorties),
                        pattern_id=pattern.pattern_id,
                        tower_ids=list(pattern.tower_ids),
                        stop_id=pattern.stop_id,
                        uav_id=assignment.uav_id,
                        vehicle_id=assignment.vehicle_id,
                        start=round(start, 6),
                        return_time=round(return_time, 6),
                        energy_mean=round(pattern.energy_mean, 6),
                        energy_q95=round(pattern.energy_q95, 6),
                        feasible=pattern.feasible,
                        vehicle_arrival=round(arrival, 6),
                        vehicle_departure=0.0,
                        road_travel=round(road_travel, 6),
                    )
                )
                energy_share = 1.0 / max(1, len(pattern.tower_ids))
                for tower_id in pattern.tower_ids:
                    tower = tower_by_id[tower_id]
                    tasks.append(
                        ScheduledTask(
                            tower_id=tower_id,
                            stop_id=pattern.stop_id,
                            uav_id=assignment.uav_id,
                            vehicle_id=assignment.vehicle_id,
                            start=round(start + pattern.tower_start_offsets[tower_id], 6),
                            finish=round(start + pattern.tower_finish_offsets[tower_id], 6),
                            energy_mean=round(pattern.energy_mean * energy_share, 6),
                            energy_q95=round(pattern.energy_q95 * energy_share, 6),
                            feasible=pattern.feasible,
                            value=tower.value,
                            risk=tower.risk,
                            priority=round(priority.get(tower_id, 0.0), 12),
                            sortie_id=sorties[-1].sortie_id,
                            vehicle_arrival=round(arrival, 6),
                            vehicle_departure=0.0,
                            road_travel=round(road_travel, 6),
                        )
                    )
            departure = max([arrival] + [return_time for _sortie_id, return_time in local_sortie_records])
            _patch_vehicle_departure(sorties, tasks, [item[0] for item in local_sortie_records], departure)
            current_stop = stop
            current_time = departure
        return_distance = _stop_distance(current_stop, depot)
        ground_distance += return_distance
        return_time = _travel_time(scenario, return_distance)
        ground_time += return_time
        return_completion = max(return_completion, current_time + return_time)

    covered = [task.tower_id for task in tasks]
    covered_set = set(covered)
    duplicate_count = max(0, len(covered) - len(covered_set))
    missed = sorted(tower.id for tower in scenario.towers if tower.id not in covered_set)
    makespan = max([task.finish for task in tasks] + [return_completion, 0.0])
    diagnostics = {
        "service_graph_pattern_count": graph.pattern_count,
        "service_graph_feasible_count": graph.feasible_service_count,
        "selected_sortie_count": len(sorties),
        "missed_service_count": len(missed),
        "duplicate_service_count": duplicate_count,
    }
    return ScheduleState(
        method=method,
        assignments=ordered_assignments,
        tasks=sorted(tasks, key=lambda task: (task.finish, task.tower_id, task.sortie_id)),
        sorties=sorted(sorties, key=lambda sortie: sortie.sortie_id),
        route_by_vehicle={vehicle: list(route) for vehicle, route in route_by_vehicle.items() if route},
        missed_tower_ids=missed,
        duplicate_service_count=duplicate_count,
        makespan=round(makespan, 6),
        ground_travel_time=round(ground_time, 6),
        ground_travel_distance=round(ground_distance, 6),
        diagnostics=diagnostics,
    )


def objective_breakdown(
    scenario: Scenario,
    state: ScheduleState,
    params: ModelParameters | None = None,
) -> ObjectiveBreakdown:
    params = params or ModelParameters()
    rwct = sum(task.priority * task.finish for task in state.tasks)
    q95_energy = sum(sortie.energy_q95 for sortie in state.sorties)
    missed_priority = sum(
        risk_value_priority_map(scenario.towers).get(tower_id, 0.0)
        for tower_id in state.missed_tower_ids
    )
    missed_penalty = params.missed_service_penalty * (len(state.missed_tower_ids) + missed_priority)
    duplicate_penalty = params.duplicate_service_penalty * state.duplicate_service_count
    total = (
        params.lambda_r * rwct / max(params.r0, 1e-9)
        + params.lambda_c * state.makespan / max(params.c0, 1e-9)
        + params.lambda_g * state.ground_travel_time / max(params.g0, 1e-9)
        + params.lambda_e * q95_energy / max(params.e0, 1e-9)
        + missed_penalty
        + duplicate_penalty
    )
    return ObjectiveBreakdown(
        rwct=round(rwct, 6),
        makespan=state.makespan,
        ground_travel=state.ground_travel_time,
        q95_energy=round(q95_energy, 6),
        missed_service_count=len(state.missed_tower_ids),
        duplicate_service_count=state.duplicate_service_count,
        missed_service_penalty=round(missed_penalty, 6),
        duplicate_service_penalty=round(duplicate_penalty, 6),
        total_objective=round(total, 6),
    )


def state_to_plan_tasks(state: ScheduleState):
    from .solvers import PlanTask, PlanSortie

    tasks = [
        PlanTask(
            tower_id=task.tower_id,
            stop_id=task.stop_id,
            uav_id=task.uav_id,
            start=task.start,
            finish=task.finish,
            energy_mean=task.energy_mean,
            energy_q95=task.energy_q95,
            feasible=task.feasible,
            value=task.value,
            risk=task.risk,
            vehicle_id=task.vehicle_id,
            vehicle_arrival=task.vehicle_arrival,
            vehicle_departure=task.vehicle_departure,
            road_travel=task.road_travel,
            priority=task.priority,
            sortie_id=task.sortie_id,
        )
        for task in state.tasks
    ]
    sorties = [
        PlanSortie(
            sortie_id=sortie.sortie_id,
            tower_ids=list(sortie.tower_ids),
            stop_id=sortie.stop_id,
            uav_id=sortie.uav_id,
            vehicle_id=sortie.vehicle_id,
            start=sortie.start,
            return_time=sortie.return_time,
            energy_mean=sortie.energy_mean,
            energy_q95=sortie.energy_q95,
            feasible=sortie.feasible,
            vehicle_arrival=sortie.vehicle_arrival,
            vehicle_departure=sortie.vehicle_departure,
            road_travel=sortie.road_travel,
        )
        for sortie in state.sorties
    ]
    return tasks, sorties


def _make_pattern(
    pattern_id: int,
    stop: Stop,
    towers: Sequence[Tower],
    tower_by_id: Mapping[int, Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> SortiePattern:
    estimate = energy_model.estimate_sortie(stop, towers, scenario.weather)
    offsets = _tower_offsets(stop, towers, energy_model)
    limit = energy_model.battery_capacity * (1.0 - energy_model.reserve_ratio)
    required = estimate.q95_energy if use_quantile else estimate.mean_energy
    return SortiePattern(
        pattern_id=pattern_id,
        stop_id=stop.id,
        tower_ids=tuple(tower.id for tower in towers),
        distance=estimate.distance,
        duration=estimate.duration,
        energy_mean=estimate.mean_energy,
        energy_std=estimate.std_energy,
        energy_q95=estimate.q95_energy,
        endurance_limit=estimate.endurance_limit,
        energy_margin=round(limit - required, 6),
        feasible=required <= limit,
        tower_start_offsets={tower_id: round(start, 6) for tower_id, (start, _finish) in offsets.items()},
        tower_finish_offsets={tower_id: round(finish, 6) for tower_id, (_start, finish) in offsets.items()},
    )


def _tower_offsets(
    stop: Stop,
    towers: Sequence[Tower],
    energy_model: EnergyModel,
) -> Dict[int, tuple[float, float]]:
    elapsed = 0.0
    current_x, current_y = stop.x, stop.y
    offsets: Dict[int, tuple[float, float]] = {}
    for tower in towers:
        leg_distance = hypot(current_x - tower.x, current_y - tower.y)
        elapsed += leg_distance / max(1.0, energy_model.drone_speed_kmph) * 60.0
        start = elapsed
        elapsed += tower.service_time
        offsets[tower.id] = (start, elapsed)
        current_x, current_y = tower.x, tower.y
    return offsets


def _nearest_stop_ids_by_tower(
    towers: Sequence[Tower],
    stops: Sequence[Stop],
    count: int,
) -> Dict[int, List[int]]:
    limit = max(1, count)
    mapping: Dict[int, List[int]] = {}
    for tower in towers:
        ordered = sorted(stops, key=lambda stop: (_distance_stop_tower(stop, tower), stop.id))
        mapping[tower.id] = [stop.id for stop in ordered[: min(limit, len(ordered))]]
    return mapping


def _near_towers_by_stop(
    towers: Sequence[Tower],
    stops: Sequence[Stop],
    nearest_stop_ids_by_tower: Mapping[int, Sequence[int]],
    max_towers: int,
) -> Dict[int, List[Tower]]:
    result: Dict[int, List[Tower]] = {}
    for stop in stops:
        candidates = [
            tower
            for tower in towers
            if stop.id in nearest_stop_ids_by_tower.get(tower.id, ())
        ]
        candidates.sort(key=lambda tower: (_distance_stop_tower(stop, tower), tower.segment, tower.id))
        result[stop.id] = candidates[: max(1, max_towers)]
    return result


def _pattern_sort_key(pattern: SortiePattern) -> tuple:
    return (
        not pattern.feasible,
        pattern.energy_q95 / max(1, len(pattern.tower_ids)),
        pattern.duration / max(1, len(pattern.tower_ids)),
        len(pattern.tower_ids),
        pattern.stop_id,
        pattern.tower_ids,
    )


def _patch_vehicle_departure(
    sorties: List[ScheduledSortie],
    tasks: List[ScheduledTask],
    sortie_ids: Sequence[int],
    departure: float,
) -> None:
    affected = set(sortie_ids)
    for idx, sortie in enumerate(sorties):
        if sortie.sortie_id in affected:
            sorties[idx] = ScheduledSortie(
                sortie_id=sortie.sortie_id,
                pattern_id=sortie.pattern_id,
                tower_ids=sortie.tower_ids,
                stop_id=sortie.stop_id,
                uav_id=sortie.uav_id,
                vehicle_id=sortie.vehicle_id,
                start=sortie.start,
                return_time=sortie.return_time,
                energy_mean=sortie.energy_mean,
                energy_q95=sortie.energy_q95,
                feasible=sortie.feasible,
                vehicle_arrival=sortie.vehicle_arrival,
                vehicle_departure=round(departure, 6),
                road_travel=sortie.road_travel,
            )
    for idx, task in enumerate(tasks):
        if task.sortie_id in affected:
            tasks[idx] = ScheduledTask(
                tower_id=task.tower_id,
                stop_id=task.stop_id,
                uav_id=task.uav_id,
                vehicle_id=task.vehicle_id,
                start=task.start,
                finish=task.finish,
                energy_mean=task.energy_mean,
                energy_q95=task.energy_q95,
                feasible=task.feasible,
                value=task.value,
                risk=task.risk,
                priority=task.priority,
                sortie_id=task.sortie_id,
                vehicle_arrival=task.vehicle_arrival,
                vehicle_departure=round(departure, 6),
                road_travel=task.road_travel,
            )


def _depot_stop(scenario: Scenario) -> Stop:
    if not scenario.stops:
        return Stop(-1, 0.0, 0.0)
    first = min(scenario.stops, key=lambda stop: (stop.x, stop.y, stop.id))
    return Stop(-1, first.x, first.y)


def _stop_distance(left: Stop, right: Stop) -> float:
    return hypot(left.x - right.x, left.y - right.y)


def _distance_stop_tower(stop: Stop, tower: Tower) -> float:
    return hypot(stop.x - tower.x, stop.y - tower.y)


def _travel_time(scenario: Scenario, distance: float) -> float:
    return distance / max(1.0, scenario.vehicle_speed_kmph) * 60.0
