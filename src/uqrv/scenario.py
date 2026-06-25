from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi, sin
from random import Random
from typing import List


@dataclass(frozen=True)
class Tower:
    id: int
    x: float
    y: float
    risk: float
    value: float
    service_time: float
    payload: float
    segment: int


@dataclass(frozen=True)
class Stop:
    id: int
    x: float
    y: float


@dataclass(frozen=True)
class Weather:
    wind_speed: float
    wind_direction: float
    temperature: float
    uncertainty: float


@dataclass(frozen=True)
class Scenario:
    id: str
    size: str
    seed: int
    towers: List[Tower]
    stops: List[Stop]
    vehicle_count: int
    uav_count: int
    vehicle_speed_kmph: float
    drone_speed_kmph: float
    battery_capacity: float
    weather: Weather


SIZE_CONFIG = {
    "S": {"towers": 12, "stops": 6, "vehicles": 1, "uavs": 2, "segments": 2},
    "M": {"towers": 50, "stops": 24, "vehicles": 2, "uavs": 5, "segments": 3},
    "L": {"towers": 150, "stops": 72, "vehicles": 4, "uavs": 12, "segments": 4},
}


def generate_scenario(size: str = "S", seed: int = 0, uncertainty: str = "medium") -> Scenario:
    if size not in SIZE_CONFIG:
        raise ValueError(f"unknown size {size!r}; expected one of {sorted(SIZE_CONFIG)}")

    rng = Random(seed)
    cfg = SIZE_CONFIG[size]
    uncertainty_scale = {"low": 0.08, "medium": 0.16, "high": 0.28}.get(uncertainty, 0.16)

    towers: List[Tower] = []
    segment_count = cfg["segments"]
    for i in range(cfg["towers"]):
        segment = i % segment_count
        progress = i // segment_count
        corridor_angle = (segment / max(1, segment_count)) * pi / 3.0
        base_x = progress * 2.2 + segment * 1.4
        base_y = segment * 8.0
        jitter = rng.uniform(-0.65, 0.65)
        x = base_x + jitter * cos(corridor_angle)
        y = base_y + jitter * sin(corridor_angle) + rng.uniform(-0.5, 0.5)
        risk = round(rng.betavariate(2.0, 4.0), 4)
        criticality = 1.0 + 1.6 * (segment == 0) + rng.uniform(0.0, 0.7)
        value = round(20.0 + 85.0 * risk * criticality, 4)
        service_time = round(rng.uniform(3.0, 8.0), 4)
        payload = round(rng.uniform(0.4, 1.6), 4)
        towers.append(Tower(i, x, y, risk, value, service_time, payload, segment))

    stops: List[Stop] = []
    for j in range(cfg["stops"]):
        segment = j % segment_count
        progress = j // segment_count
        x = progress * 4.8 + segment * 1.5 + rng.uniform(-0.7, 0.7)
        y = segment * 8.0 + rng.uniform(-1.3, 1.3)
        stops.append(Stop(j, x, y))

    weather = Weather(
        wind_speed=round(rng.uniform(1.0, 9.0), 4),
        wind_direction=round(rng.uniform(0.0, 360.0), 4),
        temperature=round(rng.uniform(8.0, 34.0), 4),
        uncertainty=uncertainty_scale,
    )
    return Scenario(
        id=f"{size}_seed{seed}_{uncertainty}",
        size=size,
        seed=seed,
        towers=towers,
        stops=stops,
        vehicle_count=cfg["vehicles"],
        uav_count=cfg["uavs"],
        vehicle_speed_kmph=65.0,
        drone_speed_kmph=46.0,
        battery_capacity=150.0,
        weather=weather,
    )
