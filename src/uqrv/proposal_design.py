from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
from random import Random
from typing import Dict, Iterable, List

from .scenario import Scenario, Stop, Tower, Weather


@dataclass(frozen=True)
class ProposalSizeConfig:
    size: str
    tower_count: int
    stop_count: int
    vehicle_count: int
    uavs_per_vehicle: int
    purpose: str


PROPOSAL_SIZE_CONFIGS: Dict[str, List[ProposalSizeConfig]] = {
    "S": [
        ProposalSizeConfig("S", 10, 5, 1, 1, "compact MILP reference validation"),
        ProposalSizeConfig("S", 15, 8, 1, 2, "compact MILP reference validation"),
        ProposalSizeConfig("S", 20, 10, 1, 2, "compact MILP reference validation"),
    ],
    "M": [
        ProposalSizeConfig("M", 30, 15, 2, 2, "algorithm comparison"),
        ProposalSizeConfig("M", 50, 25, 2, 2, "algorithm comparison"),
        ProposalSizeConfig("M", 75, 35, 3, 3, "algorithm comparison"),
        ProposalSizeConfig("M", 100, 50, 3, 3, "algorithm comparison"),
    ],
    "L": [
        ProposalSizeConfig("L", 150, 75, 3, 2, "scalability test"),
        ProposalSizeConfig("L", 200, 100, 4, 3, "scalability test"),
        ProposalSizeConfig("L", 300, 150, 5, 3, "scalability test"),
        ProposalSizeConfig("L", 500, 250, 5, 4, "scalability test"),
    ],
}


def generate_proposal_scenario(
    size: str,
    variant_index: int,
    seed: int,
    uncertainty: str = "medium",
) -> Scenario:
    config = PROPOSAL_SIZE_CONFIGS[size][variant_index]
    return generate_custom_scenario(config, seed=seed, uncertainty=uncertainty)


def generate_custom_scenario(
    config: ProposalSizeConfig,
    seed: int,
    uncertainty: str = "medium",
) -> Scenario:
    rng = Random(seed + 7919 * config.tower_count + 104729 * config.stop_count)
    uncertainty_scale = {"low": 0.08, "medium": 0.16, "high": 0.30}.get(uncertainty, 0.16)
    corridor_count = 2 if config.size == "S" else 3 if config.size == "M" else 4

    towers: List[Tower] = []
    for i in range(config.tower_count):
        segment = i % corridor_count
        progress = i // corridor_count
        angle = (segment / max(1, corridor_count - 1)) * pi / 5.0
        base_x = progress * 1.75 + segment * 1.6
        base_y = segment * 7.5
        lateral = rng.uniform(-0.75, 0.75)
        x = base_x + lateral * cos(angle)
        y = base_y + lateral * sin(angle) + rng.uniform(-0.6, 0.6)
        defect_prior = rng.betavariate(2.2, 4.2)
        criticality = 1.0 + 1.5 * (segment == 0) + 0.7 * (i % 11 == 0) + rng.uniform(0.0, 0.5)
        value = 18.0 + 92.0 * defect_prior * criticality
        service_time = rng.uniform(3.0, 8.0)
        payload = rng.uniform(0.35, 1.65)
        towers.append(
            Tower(
                id=i,
                x=round(x, 4),
                y=round(y, 4),
                risk=round(defect_prior, 4),
                value=round(value, 4),
                service_time=round(service_time, 4),
                payload=round(payload, 4),
                segment=segment,
            )
        )

    stops: List[Stop] = []
    for j in range(config.stop_count):
        segment = j % corridor_count
        progress = j // corridor_count
        x = progress * 3.5 + segment * 1.45 + rng.uniform(-0.85, 0.85)
        y = segment * 7.5 + rng.uniform(-1.25, 1.25)
        stops.append(Stop(id=j, x=round(x, 4), y=round(y, 4)))

    weather = Weather(
        wind_speed=round(rng.uniform(1.0, 10.5), 4),
        wind_direction=round(rng.uniform(0.0, 360.0), 4),
        temperature=round(rng.uniform(5.0, 36.0), 4),
        uncertainty=uncertainty_scale,
    )
    return Scenario(
        id=f"{config.size}{config.tower_count}_P{config.stop_count}_seed{seed}_{uncertainty}",
        size=config.size,
        seed=seed,
        towers=towers,
        stops=stops,
        vehicle_count=config.vehicle_count,
        uav_count=config.vehicle_count * config.uavs_per_vehicle,
        vehicle_speed_kmph=70.0 if config.size != "L" else 65.0,
        drone_speed_kmph=46.0,
        battery_capacity=150.0,
        weather=weather,
    )


def build_proposal_experiment_matrix(seeds: Iterable[int], quick: bool = False) -> Dict[str, List[dict]]:
    seeds = list(seeds)
    small_methods = ["milp_highs", "alns_pinn", "alns_pinn_full"]
    comparison_methods = ["greedy_nearest", "ga", "aco", "alns_fixed", "alns_pinn", "alns_pinn_uq", "alns_pinn_full"]
    ablation_methods = [
        "alns_pinn_full",
        "no_pinn",
        "no_adaptive",
        "no_uq",
        "no_risk_value",
        "no_energy_repair",
        "no_sync_repair",
    ]
    matrix: Dict[str, List[dict]] = {
        "P1_milp_exact_small": [],
        "P2_algorithm_comparison": [],
        "P3_pinn_prediction_accuracy": [],
        "P4_ablation": [],
        "P5_case_study": [],
        "P6_candidate_stop_screening": [],
        "P8_sensitivity": [],
    }

    for variant, config in enumerate(PROPOSAL_SIZE_CONFIGS["S"]):
        for seed in seeds:
            for method in small_methods:
                matrix["P1_milp_exact_small"].append(_row(config, variant, seed, method, "medium"))

    for size in ["M", "L"]:
        for variant, config in enumerate(PROPOSAL_SIZE_CONFIGS[size]):
            for seed in seeds:
                for method in comparison_methods:
                    matrix["P2_algorithm_comparison"].append(
                        _row(config, variant, seed, method, "medium", candidate_mode="kmeans")
                    )

    for uncertainty in ["low", "medium", "high"]:
        for seed in seeds:
            config = PROPOSAL_SIZE_CONFIGS["M"][1]
            for model in ["fixed_physics", "point_pinn", "probabilistic_pinn"]:
                row = _row(config, 1, seed, model, uncertainty)
                row["prediction_model"] = model
                matrix["P3_pinn_prediction_accuracy"].append(row)

    for seed in seeds:
        config = PROPOSAL_SIZE_CONFIGS["M"][1]
        for method in ablation_methods + ["no_clustering"]:
            candidate_mode = "direct" if method == "no_clustering" else "kmeans"
            matrix["P4_ablation"].append(
                _row(config, 1, seed, method, "high", candidate_mode=candidate_mode)
            )

    case_config = ProposalSizeConfig("CASE", 200, 100, 4, 3, "realistic corridor case study")
    for seed in seeds[: max(1, min(5, len(seeds)))]:
        for method in ["alns_fixed", "alns_pinn", "alns_pinn_full"]:
            matrix["P5_case_study"].append(
                _row(case_config, 0, seed, method, "high", candidate_mode="kmeans")
            )

    screening_configs = PROPOSAL_SIZE_CONFIGS["M"][:2] if quick else PROPOSAL_SIZE_CONFIGS["M"]
    for variant, config in enumerate(screening_configs):
        for seed in seeds:
            for candidate_mode in ["direct", "kmeans", "dbscan"]:
                matrix["P6_candidate_stop_screening"].append(
                    _row(
                        config,
                        variant,
                        seed,
                        "alns_pinn_full",
                        "medium",
                        candidate_mode=candidate_mode,
                        nearest_per_tower=3,
                    )
                )

    sensitivity_config = PROPOSAL_SIZE_CONFIGS["M"][1]
    sensitivity_levels = {
        "quantile_z": [1.28, 1.645, 1.96],
        "reserve_ratio": [0.08, 0.12, 0.20],
        "iteration_budget": [50, 100, 160],
        "uav_count": [2, 4, 6],
        "candidate_mode": ["direct", "kmeans", "dbscan"],
    }
    for seed in seeds:
        for factor, levels in sensitivity_levels.items():
            for level in levels:
                row = _row(sensitivity_config, 1, seed, "alns_pinn_full", "high", candidate_mode="kmeans")
                row["sensitivity_factor"] = factor
                row["sensitivity_level"] = str(level)
                if factor == "quantile_z":
                    row["quantile_z"] = float(level)
                elif factor == "reserve_ratio":
                    row["reserve_ratio"] = float(level)
                elif factor == "iteration_budget":
                    row["iteration_budget"] = int(level)
                elif factor == "uav_count":
                    row["uav_count_override"] = int(level)
                elif factor == "candidate_mode":
                    row["candidate_mode"] = str(level)
                matrix["P8_sensitivity"].append(row)

    return matrix


def _row(
    config: ProposalSizeConfig,
    variant: int,
    seed: int,
    method: str,
    uncertainty: str,
    candidate_mode: str = "direct",
    nearest_per_tower: int = 3,
) -> dict:
    return {
        "size": config.size,
        "variant_index": variant,
        "tower_count": config.tower_count,
        "stop_count": config.stop_count,
        "vehicle_count": config.vehicle_count,
        "uavs_per_vehicle": config.uavs_per_vehicle,
        "seed": seed,
        "uncertainty": uncertainty,
        "method": method,
        "candidate_mode": candidate_mode,
        "nearest_per_tower": nearest_per_tower,
    }
