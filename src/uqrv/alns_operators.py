from __future__ import annotations

from dataclasses import dataclass
from math import exp
from random import Random
from typing import Dict, Iterable, List, Sequence

from .energy import EnergyModel
from .priority import scaled_risk_value_priority_map
from .scenario import Scenario, Stop, Tower


@dataclass(frozen=True)
class DestroyMove:
    operator: str
    kept: List[Tower]
    removed: List[Tower]


@dataclass
class OperatorStats:
    weight: float = 1.0
    uses: int = 0
    score: float = 0.0


class AdaptiveOperatorWeights:
    def __init__(self, operator_names: Iterable[str], reaction: float = 0.2, floor: float = 0.05) -> None:
        names = list(operator_names)
        if not names:
            raise ValueError("at least one operator is required")
        if not 0.0 < reaction <= 1.0:
            raise ValueError("reaction must be in (0, 1]")
        self.reaction = reaction
        self.floor = floor
        self.stats: Dict[str, OperatorStats] = {name: OperatorStats() for name in names}

    def probabilities(self) -> Dict[str, float]:
        total = sum(max(self.floor, stat.weight) for stat in self.stats.values())
        return {name: max(self.floor, stat.weight) / total for name, stat in self.stats.items()}

    def select(self, rng: Random) -> str:
        draw = rng.random()
        cumulative = 0.0
        for name, probability in self.probabilities().items():
            cumulative += probability
            if draw <= cumulative:
                return name
        return next(reversed(self.stats))

    def update(self, operator_name: str, score: float) -> None:
        if operator_name not in self.stats:
            raise KeyError(operator_name)
        stat = self.stats[operator_name]
        stat.uses += 1
        stat.score += score
        reward = max(self.floor, score)
        stat.weight = (1.0 - self.reaction) * stat.weight + self.reaction * reward


class SimulatedAnnealingAcceptance:
    def __init__(self, initial_temperature: float, cooling_rate: float = 0.995, min_temperature: float = 1e-4) -> None:
        if initial_temperature <= 0:
            raise ValueError("initial_temperature must be positive")
        if not 0.0 < cooling_rate <= 1.0:
            raise ValueError("cooling_rate must be in (0, 1]")
        self.temperature = initial_temperature
        self.cooling_rate = cooling_rate
        self.min_temperature = min_temperature

    def accept(self, current: float, candidate: float, rng: Random) -> bool:
        delta = candidate - current
        if delta <= 0:
            return True
        probability = exp(-delta / max(self.temperature, self.min_temperature))
        return rng.random() < probability

    def cool(self) -> None:
        self.temperature = max(self.min_temperature, self.temperature * self.cooling_rate)


def random_removal(towers: Sequence[Tower], remove_count: int, rng: Random) -> DestroyMove:
    remove_count = _bounded_remove_count(towers, remove_count)
    indices = set(rng.sample(range(len(towers)), remove_count))
    removed = [tower for idx, tower in enumerate(towers) if idx in indices]
    kept = [tower for idx, tower in enumerate(towers) if idx not in indices]
    return DestroyMove("random_removal", kept, removed)


def worst_energy_removal(
    towers: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    remove_count: int,
    use_quantile: bool = True,
) -> DestroyMove:
    remove_count = _bounded_remove_count(towers, remove_count)
    scored = sorted(
        towers,
        key=lambda tower: _best_stop_energy(tower, scenario.stops, scenario, energy_model, use_quantile),
        reverse=True,
    )
    removed_ids = {tower.id for tower in scored[:remove_count]}
    return DestroyMove(
        "worst_energy_removal",
        [tower for tower in towers if tower.id not in removed_ids],
        [tower for tower in towers if tower.id in removed_ids],
    )


def shaw_related_removal(towers: Sequence[Tower], remove_count: int, rng: Random) -> DestroyMove:
    remove_count = _bounded_remove_count(towers, remove_count)
    seed = rng.choice(list(towers))
    scored = sorted(
        towers,
        key=lambda tower: ((tower.x - seed.x) ** 2 + (tower.y - seed.y) ** 2) ** 0.5
        + 0.4 * abs(tower.risk - seed.risk)
        + 0.01 * abs(tower.value - seed.value),
    )
    removed_ids = {tower.id for tower in scored[:remove_count]}
    return DestroyMove(
        "shaw_related_removal",
        [tower for tower in towers if tower.id not in removed_ids],
        [tower for tower in towers if tower.id in removed_ids],
    )


def path_segment_removal(towers: Sequence[Tower], remove_count: int, rng: Random) -> DestroyMove:
    remove_count = _bounded_remove_count(towers, remove_count)
    segments = sorted({tower.segment for tower in towers})
    segment = rng.choice(segments)
    preferred = [tower for tower in towers if tower.segment == segment]
    if len(preferred) < remove_count:
        preferred = preferred + [tower for tower in towers if tower.segment != segment]
    removed_ids = {tower.id for tower in preferred[:remove_count]}
    return DestroyMove(
        "path_segment_removal",
        [tower for tower in towers if tower.id not in removed_ids],
        [tower for tower in towers if tower.id in removed_ids],
    )


def uav_chain_removal(towers: Sequence[Tower], remove_count: int, rng: Random) -> DestroyMove:
    remove_count = _bounded_remove_count(towers, remove_count)
    if len(towers) == remove_count:
        return DestroyMove("uav_chain_removal", [], list(towers))
    start = rng.randrange(0, len(towers) - remove_count + 1)
    removed_ids = {tower.id for tower in towers[start : start + remove_count]}
    return DestroyMove(
        "uav_chain_removal",
        [tower for tower in towers if tower.id not in removed_ids],
        [tower for tower in towers if tower.id in removed_ids],
    )


def greedy_insert_repair(
    kept: Sequence[Tower],
    removed: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool = True,
    risk_value_weight: float = 0.15,
) -> List[Tower]:
    sequence = list(kept)
    for tower in sorted(removed, key=lambda t: _insertion_priority(t, scenario, energy_model, use_quantile, risk_value_weight), reverse=True):
        best_index = min(
            range(len(sequence) + 1),
            key=lambda idx: _sequence_score(sequence[:idx] + [tower] + sequence[idx:], scenario, energy_model, use_quantile, risk_value_weight),
        )
        sequence.insert(best_index, tower)
    return sequence


def regret_insert_repair(
    kept: Sequence[Tower],
    removed: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool = True,
    risk_value_weight: float = 0.15,
) -> List[Tower]:
    sequence = list(kept)
    remaining = list(removed)
    while remaining:
        best_choice = None
        best_regret = -float("inf")
        for tower in remaining:
            scores = sorted(
                (
                    _sequence_score(
                        sequence[:idx] + [tower] + sequence[idx:],
                        scenario,
                        energy_model,
                        use_quantile,
                        risk_value_weight,
                    ),
                    idx,
                )
                for idx in range(len(sequence) + 1)
            )
            regret = scores[1][0] - scores[0][0] if len(scores) > 1 else 0.0
            if regret > best_regret:
                best_regret = regret
                best_choice = (tower, scores[0][1])
        tower, idx = best_choice
        sequence.insert(idx, tower)
        remaining.remove(tower)
    return sequence


def energy_minimum_insert_repair(
    kept: Sequence[Tower],
    removed: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool = True,
    risk_value_weight: float = 0.15,
) -> List[Tower]:
    sequence = list(kept)
    priority_scores = scaled_risk_value_priority_map(scenario.towers)
    ordered = sorted(
        removed,
        key=lambda tower: (
            _best_stop_energy(tower, scenario.stops, scenario, energy_model, use_quantile),
            -priority_scores.get(tower.id, 0.0),
            tower.id,
        ),
    )
    for tower in ordered:
        idx = _energy_order_insert_index(sequence, tower, scenario, energy_model, use_quantile)
        sequence.insert(idx, tower)
    return sequence


def synchronization_aware_insert_repair(
    kept: Sequence[Tower],
    removed: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool = True,
    risk_value_weight: float = 0.15,
) -> List[Tower]:
    sequence = list(kept)
    remaining = list(removed)
    segment_workloads = _segment_workloads(sequence, scenario, energy_model, use_quantile)
    for tower in remaining:
        segment_workloads.setdefault(tower.segment, 0.0)

    while remaining:
        tower = _select_synchronization_candidate(
            remaining,
            sequence,
            segment_workloads,
            scenario,
            energy_model,
            use_quantile,
        )
        sequence.append(tower)
        segment_workloads[tower.segment] += _tower_workload(tower, scenario, energy_model, use_quantile)
        remaining.remove(tower)
    return sequence


def _bounded_remove_count(towers: Sequence[Tower], remove_count: int) -> int:
    if not towers:
        return 0
    return max(1, min(remove_count, len(towers)))


def _best_stop_energy(
    tower: Tower,
    stops: Sequence[Stop],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> float:
    return min(
        (
            energy_model.estimate(stop, tower, scenario.weather).q95_energy
            if use_quantile
            else energy_model.estimate(stop, tower, scenario.weather).mean_energy
        )
        for stop in stops
    )


def _nearest_stop_distance(tower: Tower, stops: Sequence[Stop]) -> float:
    return min(((stop.x - tower.x) ** 2 + (stop.y - tower.y) ** 2) ** 0.5 for stop in stops)


def _insertion_priority(
    tower: Tower,
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
    risk_value_weight: float,
) -> float:
    risk_value = _risk_value(tower, scenario)
    energy = _best_stop_energy(tower, scenario.stops, scenario, energy_model, use_quantile)
    distance = _nearest_stop_distance(tower, scenario.stops)
    return risk_value_weight * risk_value - 0.04 * energy - 0.1 * distance


def _risk_value(tower: Tower, scenario: Scenario) -> float:
    return scaled_risk_value_priority_map(scenario.towers).get(tower.id, 0.0)


def _energy_order_insert_index(
    sequence: Sequence[Tower],
    tower: Tower,
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> int:
    tower_key = (
        _best_stop_energy(tower, scenario.stops, scenario, energy_model, use_quantile),
        -_risk_value(tower, scenario),
        tower.id,
    )
    for idx, existing in enumerate(sequence):
        existing_key = (
            _best_stop_energy(existing, scenario.stops, scenario, energy_model, use_quantile),
            -_risk_value(existing, scenario),
            existing.id,
        )
        if tower_key < existing_key:
            return idx
    return len(sequence)


def _tower_workload(
    tower: Tower,
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> float:
    best = min(
        (energy_model.estimate(stop, tower, scenario.weather) for stop in scenario.stops),
        key=lambda estimate: estimate.q95_energy if use_quantile else estimate.mean_energy,
    )
    energy = best.q95_energy if use_quantile else best.mean_energy
    return best.duration + 0.02 * energy


def _segment_workloads(
    towers: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> Dict[int, float]:
    workloads: Dict[int, float] = {}
    for tower in towers:
        workloads[tower.segment] = workloads.get(tower.segment, 0.0) + _tower_workload(
            tower,
            scenario,
            energy_model,
            use_quantile,
        )
    return workloads


def _select_synchronization_candidate(
    remaining: Sequence[Tower],
    sequence: Sequence[Tower],
    segment_workloads: Dict[int, float],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
) -> Tower:
    last_segment = sequence[-1].segment if sequence else None
    eligible = [tower for tower in remaining if tower.segment != last_segment] or list(remaining)
    return min(
        eligible,
        key=lambda tower: (
            segment_workloads.get(tower.segment, 0.0),
            _tower_workload(tower, scenario, energy_model, use_quantile),
            -_risk_value(tower, scenario),
            tower.id,
        ),
    )


def _synchronization_insert_index(
    sequence: Sequence[Tower],
    tower: Tower,
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
    risk_value_weight: float,
) -> int:
    return min(
        range(len(sequence) + 1),
        key=lambda idx: (
            _max_segment_run(sequence[:idx] + [tower] + sequence[idx:]),
            _same_segment_neighbors(sequence, tower, idx),
            _sequence_score(
                sequence[:idx] + [tower] + sequence[idx:],
                scenario,
                energy_model,
                use_quantile,
                risk_value_weight,
            ),
            idx,
        ),
    )


def _same_segment_neighbors(sequence: Sequence[Tower], tower: Tower, idx: int) -> int:
    penalty = 0
    if idx > 0 and sequence[idx - 1].segment == tower.segment:
        penalty += 1
    if idx < len(sequence) and sequence[idx].segment == tower.segment:
        penalty += 1
    return penalty


def _max_segment_run(towers: Sequence[Tower]) -> int:
    longest = 0
    current = 0
    previous = None
    for tower in towers:
        current = current + 1 if tower.segment == previous else 1
        previous = tower.segment
        longest = max(longest, current)
    return longest


def _sequence_score(
    towers: Sequence[Tower],
    scenario: Scenario,
    energy_model: EnergyModel,
    use_quantile: bool,
    risk_value_weight: float,
) -> float:
    score = 0.0
    priority_scores = scaled_risk_value_priority_map(scenario.towers)
    for idx, tower in enumerate(towers):
        energy = _best_stop_energy(tower, scenario.stops, scenario, energy_model, use_quantile)
        risk_value = priority_scores.get(tower.id, 0.0)
        score += (idx + 1) * (energy - risk_value_weight * risk_value)
    return score
