from __future__ import annotations

from dataclasses import dataclass, replace
from math import hypot
from random import Random
from typing import Dict, Iterable, List, Sequence, Tuple

from .energy import EnergyModel
from .scenario import Scenario, Stop, Tower


@dataclass(frozen=True)
class CandidateStopSet:
    method: str
    stops: List[Stop]
    assignments: Dict[int, int]
    cluster_sizes: Dict[int, int]


@dataclass(frozen=True)
class ServicePair:
    tower_id: int
    stop_id: int
    rank: int
    distance: float
    energy_mean: float
    energy_q95: float
    duration: float
    feasible: bool


@dataclass(frozen=True)
class ServicePairScreen:
    pairs: List[ServicePair]
    total_pairs: int
    screened_pair_count: int
    feasible_pair_count: int
    reduction_ratio: float
    by_tower_counts: Dict[int, int]


def generate_clustered_stops(
    towers: Sequence[Tower],
    target_count: int,
    method: str = "kmeans",
    seed: int = 0,
    eps: float = 4.0,
    min_samples: int = 2,
) -> CandidateStopSet:
    if target_count <= 0:
        raise ValueError("target_count must be positive")
    if not towers:
        return CandidateStopSet(method=method, stops=[], assignments={}, cluster_sizes={})

    method_key = method.lower()
    if method_key == "kmeans":
        groups = _kmeans_groups(towers, target_count, seed)
    elif method_key == "dbscan":
        groups = _dbscan_groups(towers, eps=eps, min_samples=min_samples)
        if not groups:
            groups = _kmeans_groups(towers, target_count, seed)
        elif len(groups) > target_count:
            groups = _merge_groups_to_target(groups, target_count)
    else:
        raise ValueError(f"unknown candidate stop method {method!r}")

    return _stop_set_from_groups(method_key, groups)


def screen_service_pairs(
    scenario: Scenario,
    stops: Sequence[Stop],
    energy_model: EnergyModel,
    nearest_per_tower: int = 3,
    use_quantile: bool = True,
) -> ServicePairScreen:
    if nearest_per_tower <= 0:
        raise ValueError("nearest_per_tower must be positive")
    total_pairs = len(scenario.towers) * len(stops)
    pairs: List[ServicePair] = []
    by_tower_counts: Dict[int, int] = {}
    for tower in scenario.towers:
        scored = []
        for stop in stops:
            estimate = energy_model.estimate(stop, tower, scenario.weather)
            feasible = energy_model.is_feasible(estimate, use_quantile=use_quantile)
            distance = _distance_tower_stop(tower, stop)
            energy_bound = estimate.q95_energy if use_quantile else estimate.mean_energy
            scored.append((not feasible, energy_bound, distance, stop, estimate, feasible))
        scored.sort(key=lambda item: (item[0], item[1], item[2], item[3].id))
        selected = scored[: min(nearest_per_tower, len(scored))]
        if selected and all(not item[-1] for item in selected):
            selected = [scored[0]]
        by_tower_counts[tower.id] = len(selected)
        for rank, (_penalty, _energy, distance, stop, estimate, feasible) in enumerate(selected, start=1):
            pairs.append(
                ServicePair(
                    tower_id=tower.id,
                    stop_id=stop.id,
                    rank=rank,
                    distance=round(distance, 6),
                    energy_mean=round(estimate.mean_energy, 6),
                    energy_q95=round(estimate.q95_energy, 6),
                    duration=round(estimate.duration, 6),
                    feasible=feasible,
                )
            )
    screened_count = len(pairs)
    feasible_count = sum(1 for pair in pairs if pair.feasible)
    reduction = 0.0 if total_pairs == 0 else 1.0 - screened_count / total_pairs
    return ServicePairScreen(
        pairs=pairs,
        total_pairs=total_pairs,
        screened_pair_count=screened_count,
        feasible_pair_count=feasible_count,
        reduction_ratio=round(max(0.0, reduction), 6),
        by_tower_counts=by_tower_counts,
    )


def with_candidate_stops(scenario: Scenario, candidate_set: CandidateStopSet) -> Scenario:
    suffix = f"{candidate_set.method}{len(candidate_set.stops)}"
    return replace(scenario, id=f"{scenario.id}_{suffix}", stops=list(candidate_set.stops))


def _kmeans_groups(towers: Sequence[Tower], target_count: int, seed: int) -> List[List[Tower]]:
    rng = Random(seed)
    k = min(max(1, target_count), len(towers))
    ordered = sorted(towers, key=lambda tower: (tower.x, tower.y, tower.id))
    centers = [(tower.x, tower.y) for tower in rng.sample(ordered, k)]
    groups = _assign_to_centers(ordered, centers)
    for _ in range(40):
        groups = _ensure_nonempty_groups(groups, centers)
        new_centers = [_tower_mean(group) for group in groups]
        if [_rounded_pair(center) for center in new_centers] == [_rounded_pair(center) for center in centers]:
            break
        centers = new_centers
        groups = _assign_to_centers(ordered, centers)
    return _ensure_nonempty_groups(groups, centers)


def _dbscan_groups(towers: Sequence[Tower], eps: float, min_samples: int) -> List[List[Tower]]:
    ordered = sorted(towers, key=lambda tower: tower.id)
    tower_by_id = {tower.id: tower for tower in ordered}
    visited = set()
    assigned = set()
    groups: List[List[Tower]] = []
    noise: List[Tower] = []

    for tower in ordered:
        if tower.id in visited:
            continue
        visited.add(tower.id)
        neighbors = _region_query(ordered, tower, eps)
        if len(neighbors) < min_samples:
            noise.append(tower)
            continue
        cluster_ids = {neighbor.id for neighbor in neighbors}
        queue = [neighbor.id for neighbor in neighbors]
        while queue:
            current_id = queue.pop(0)
            if current_id not in visited:
                visited.add(current_id)
                current_neighbors = _region_query(ordered, tower_by_id[current_id], eps)
                if len(current_neighbors) >= min_samples:
                    for neighbor in current_neighbors:
                        if neighbor.id not in cluster_ids:
                            cluster_ids.add(neighbor.id)
                            queue.append(neighbor.id)
            assigned.add(current_id)
        groups.append([tower_by_id[tower_id] for tower_id in sorted(cluster_ids)])

    for tower in noise:
        if tower.id not in assigned:
            groups.append([tower])
    return groups


def _merge_groups_to_target(groups: List[List[Tower]], target_count: int) -> List[List[Tower]]:
    merged = [list(group) for group in groups]
    target = max(1, target_count)
    while len(merged) > target:
        centers = [_tower_mean(group) for group in merged]
        best_pair = min(
            (
                (_distance_points(centers[i], centers[j]), i, j)
                for i in range(len(merged))
                for j in range(i + 1, len(merged))
            ),
            key=lambda item: item[0],
        )
        _distance, left, right = best_pair
        merged[left] = merged[left] + merged[right]
        del merged[right]
    return merged


def _assign_to_centers(towers: Sequence[Tower], centers: Sequence[Tuple[float, float]]) -> List[List[Tower]]:
    groups: List[List[Tower]] = [[] for _ in centers]
    for tower in towers:
        idx = min(range(len(centers)), key=lambda i: _distance_points((tower.x, tower.y), centers[i]))
        groups[idx].append(tower)
    return groups


def _ensure_nonempty_groups(groups: List[List[Tower]], centers: Sequence[Tuple[float, float]]) -> List[List[Tower]]:
    groups = [list(group) for group in groups]
    empty_indices = [idx for idx, group in enumerate(groups) if not group]
    for empty_idx in empty_indices:
        donor_idx = max(range(len(groups)), key=lambda idx: len(groups[idx]))
        if len(groups[donor_idx]) <= 1:
            continue
        donor_center = centers[donor_idx]
        moved = max(groups[donor_idx], key=lambda tower: _distance_points((tower.x, tower.y), donor_center))
        groups[donor_idx].remove(moved)
        groups[empty_idx].append(moved)
    return [group for group in groups if group]


def _stop_set_from_groups(method: str, groups: Iterable[Sequence[Tower]]) -> CandidateStopSet:
    grouped = [list(group) for group in groups if group]
    centers = [(_tower_mean(group), group) for group in grouped]
    centers.sort(key=lambda item: (item[0][0], item[0][1]))
    stops: List[Stop] = []
    assignments: Dict[int, int] = {}
    cluster_sizes: Dict[int, int] = {}
    for idx, (center, group) in enumerate(centers):
        stops.append(Stop(id=idx, x=round(center[0], 4), y=round(center[1], 4)))
        cluster_sizes[idx] = len(group)
        for tower in group:
            assignments[tower.id] = idx
    return CandidateStopSet(method=method, stops=stops, assignments=assignments, cluster_sizes=cluster_sizes)


def _region_query(towers: Sequence[Tower], center: Tower, eps: float) -> List[Tower]:
    return [tower for tower in towers if _distance_towers(tower, center) <= eps]


def _tower_mean(towers: Sequence[Tower]) -> Tuple[float, float]:
    return (
        sum(tower.x for tower in towers) / len(towers),
        sum(tower.y for tower in towers) / len(towers),
    )


def _rounded_pair(point: Tuple[float, float]) -> Tuple[float, float]:
    return (round(point[0], 8), round(point[1], 8))


def _distance_towers(left: Tower, right: Tower) -> float:
    return hypot(left.x - right.x, left.y - right.y)


def _distance_tower_stop(tower: Tower, stop: Stop) -> float:
    return hypot(tower.x - stop.x, tower.y - stop.y)


def _distance_points(left: Tuple[float, float], right: Tuple[float, float]) -> float:
    return hypot(left[0] - right[0], left[1] - right[1])
