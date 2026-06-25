from __future__ import annotations

import json
from dataclasses import dataclass
from math import sqrt
from pathlib import Path
from random import Random
from typing import Dict, Iterable, List, Sequence

import numpy as np

from .energy import EnergyBreakdown, EnergyModel
from .scenario import Stop, Tower, Weather, generate_scenario


@dataclass(frozen=True)
class SurrogatePrediction:
    energy_mean: float
    energy_std: float
    energy_q95: float
    endurance_limit: float
    safety_margin: float
    flight_time: float
    service_time: float
    distance: float
    q95_feasible: bool
    components: EnergyBreakdown
    evidence_level: str
    training_status: str
    source_model: str
    field_validated: bool = False

    def as_scheduler_parameters(self) -> Dict[str, float | bool | str]:
        return {
            "energy_mean": self.energy_mean,
            "energy_std": self.energy_std,
            "energy_q95": self.energy_q95,
            "endurance_limit": self.endurance_limit,
            "safety_margin": self.safety_margin,
            "flight_time": self.flight_time,
            "service_time": self.service_time,
            "distance": self.distance,
            "q95_feasible": self.q95_feasible,
            "evidence_level": self.evidence_level,
            "training_status": self.training_status,
            "field_validated": self.field_validated,
        }


class ProbabilisticEnergySurrogate:
    """Scheduling-facing wrapper around the explicit physics energy model.

    This class deliberately records the evidence boundary. It can be replaced by
    a trained energy surrogate later without changing the scheduling interface.
    """

    def __init__(
        self,
        energy_model: EnergyModel | None = None,
        evidence_level: str = "simulation_calibrated",
        training_status: str = "not_field_trained",
        source_model: str = "explicit_physics_energy_model",
    ) -> None:
        self.energy_model = energy_model or EnergyModel()
        self.evidence_level = evidence_level
        self.training_status = training_status
        self.source_model = source_model

    def predict(self, stop: Stop, tower: Tower, weather: Weather) -> SurrogatePrediction:
        estimate = self.energy_model.estimate(stop, tower, weather)
        return SurrogatePrediction(
            energy_mean=estimate.mean_energy,
            energy_std=estimate.std_energy,
            energy_q95=estimate.q95_energy,
            endurance_limit=estimate.endurance_limit,
            safety_margin=estimate.safety_margin,
            flight_time=estimate.flight_time,
            service_time=estimate.service_time,
            distance=estimate.distance,
            q95_feasible=self.energy_model.is_feasible(estimate, use_quantile=True),
            components=estimate.components,
            evidence_level=self.evidence_level,
            training_status=self.training_status,
            source_model=self.source_model,
            field_validated=self.training_status == "field_trained_validated",
        )


@dataclass(frozen=True)
class EnergyTrainingSample:
    stop: Stop
    tower: Tower
    weather: Weather
    observed_energy: float


class SimulationTrainedEnergySurrogate(ProbabilisticEnergySurrogate):
    """Simulation-trained physics-informed residual surrogate.

    The model is intentionally lightweight: it learns a residual calibration on
    top of the explicit physics estimate and returns a probabilistic q95 energy
    value. It upgrades the current evidence from "not trained" to
    "simulation-trained" without claiming field validation.
    """

    def __init__(
        self,
        coefficients: Sequence[float],
        residual_std: float,
        energy_model: EnergyModel | None = None,
    ) -> None:
        super().__init__(
            energy_model=energy_model,
            evidence_level="simulation_trained",
            training_status="simulation_trained_not_field_validated",
            source_model="physics_informed_residual_ridge_surrogate",
        )
        self.coefficients = [float(value) for value in coefficients]
        self.residual_std = float(residual_std)

    @classmethod
    def fit(
        cls,
        samples: Sequence[EnergyTrainingSample],
        energy_model: EnergyModel | None = None,
        ridge: float = 1e-4,
    ) -> "SimulationTrainedEnergySurrogate":
        if len(samples) < 8:
            raise ValueError("at least 8 energy training samples are required")
        model = energy_model or EnergyModel()
        x = np.array([_feature_vector(model, sample.stop, sample.tower, sample.weather) for sample in samples], dtype=float)
        y = np.array([sample.observed_energy for sample in samples], dtype=float)
        regularizer = ridge * np.eye(x.shape[1])
        regularizer[0, 0] = 0.0
        coefficients = np.linalg.solve(x.T @ x + regularizer, x.T @ y)
        residuals = y - x @ coefficients
        residual_std = max(2.5, float(np.sqrt(np.mean(residuals * residuals))))
        return cls(coefficients=coefficients.tolist(), residual_std=residual_std, energy_model=model)

    def predict(self, stop: Stop, tower: Tower, weather: Weather) -> SurrogatePrediction:
        estimate = self.energy_model.estimate(stop, tower, weather)
        features = _feature_vector(self.energy_model, stop, tower, weather)
        mean = float(np.dot(np.array(self.coefficients, dtype=float), np.array(features, dtype=float)))
        lower = estimate.mean_energy * 0.55
        upper = estimate.mean_energy * 2.10
        mean = min(max(mean, lower), upper)
        std = max(2.5, self.residual_std * (0.75 + 1.75 * weather.uncertainty), mean * (0.025 + 0.10 * weather.uncertainty))
        q95 = mean + self.energy_model.quantile_z * std
        return SurrogatePrediction(
            energy_mean=round(mean, 6),
            energy_std=round(std, 6),
            energy_q95=round(q95, 6),
            endurance_limit=estimate.endurance_limit,
            safety_margin=round(estimate.endurance_limit - q95, 6),
            flight_time=estimate.flight_time,
            service_time=estimate.service_time,
            distance=estimate.distance,
            q95_feasible=q95 <= estimate.endurance_limit,
            components=estimate.components,
            evidence_level=self.evidence_level,
            training_status=self.training_status,
            source_model=self.source_model,
            field_validated=False,
        )

    def to_json(self, path: str | Path) -> None:
        payload = {
            "coefficients": self.coefficients,
            "residual_std": self.residual_std,
            "energy_model": {
                "battery_capacity": self.energy_model.battery_capacity,
                "reserve_ratio": self.energy_model.reserve_ratio,
                "quantile_z": self.energy_model.quantile_z,
                "drone_speed_kmph": self.energy_model.drone_speed_kmph,
            },
            "evidence_level": self.evidence_level,
            "training_status": self.training_status,
            "source_model": self.source_model,
        }
        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> "SimulationTrainedEnergySurrogate":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        model_cfg = payload["energy_model"]
        return cls(
            coefficients=payload["coefficients"],
            residual_std=payload["residual_std"],
            energy_model=EnergyModel(
                battery_capacity=model_cfg["battery_capacity"],
                reserve_ratio=model_cfg["reserve_ratio"],
                quantile_z=model_cfg["quantile_z"],
                drone_speed_kmph=model_cfg["drone_speed_kmph"],
            ),
        )


def generate_energy_training_samples(
    seed_range: Iterable[int],
    sizes: Sequence[str] = ("S", "M"),
    uncertainties: Sequence[str] = ("low", "medium", "high"),
    max_pairs_per_scenario: int = 12,
    energy_model: EnergyModel | None = None,
) -> List[EnergyTrainingSample]:
    model = energy_model or EnergyModel(battery_capacity=150.0)
    samples: List[EnergyTrainingSample] = []
    for size in sizes:
        for uncertainty in uncertainties:
            for seed in seed_range:
                scenario = generate_scenario(size=size, seed=seed, uncertainty=uncertainty)
                rng = Random(17017 + seed * 97 + len(size) * 13 + int(scenario.weather.wind_speed * 100))
                towers = scenario.towers[: max(1, max_pairs_per_scenario)]
                for tower in towers:
                    stop = min(scenario.stops, key=lambda item: (item.x - tower.x) ** 2 + (item.y - tower.y) ** 2)
                    estimate = model.estimate(stop, tower, scenario.weather)
                    observed = synthetic_observed_energy(estimate.mean_energy, tower, scenario.weather, estimate.wind_alignment, rng)
                    samples.append(EnergyTrainingSample(stop=stop, tower=tower, weather=scenario.weather, observed_energy=observed))
    return samples


def evaluate_energy_surrogate(surrogate: ProbabilisticEnergySurrogate, samples: Sequence[EnergyTrainingSample]) -> Dict[str, float]:
    if not samples:
        raise ValueError("cannot evaluate an empty energy sample set")
    abs_errors = []
    squared_errors = []
    covered = 0
    false_feasible = 0
    for sample in samples:
        prediction = surrogate.predict(sample.stop, sample.tower, sample.weather)
        error = prediction.energy_mean - sample.observed_energy
        abs_errors.append(abs(error))
        squared_errors.append(error * error)
        covered += int(sample.observed_energy <= prediction.energy_q95)
        false_feasible += int(prediction.energy_mean <= prediction.endurance_limit and sample.observed_energy > prediction.endurance_limit)
    count = len(samples)
    return {
        "mae": sum(abs_errors) / count,
        "rmse": sqrt(sum(squared_errors) / count),
        "coverage_95": covered / count,
        "false_feasible_rate": false_feasible / count,
    }


def synthetic_observed_energy(
    mean_energy: float,
    tower: Tower,
    weather: Weather,
    wind_alignment: float,
    rng: Random,
) -> float:
    temperature_stress = max(0.0, abs(weather.temperature - 22.0) - 4.0)
    wind_load = weather.wind_speed * (1.0 - 0.25 * wind_alignment)
    multiplier = 1.0 + 0.018 * wind_load + 0.035 * tower.payload + 0.004 * temperature_stress + 0.08 * weather.uncertainty
    stochastic = rng.gauss(0.0, 0.018 + 0.045 * weather.uncertainty)
    return round(max(1.0, mean_energy * max(0.55, multiplier + stochastic)), 6)


def _feature_vector(model: EnergyModel, stop: Stop, tower: Tower, weather: Weather) -> List[float]:
    estimate = model.estimate(stop, tower, weather)
    return [
        1.0,
        estimate.mean_energy / 100.0,
        estimate.distance / 20.0,
        tower.service_time / 10.0,
        tower.payload,
        weather.wind_speed / 10.0,
        estimate.wind_alignment,
        abs(weather.temperature - 22.0) / 20.0,
        weather.uncertainty,
        estimate.mean_energy * weather.uncertainty / 100.0,
    ]
