from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, hypot, radians
from typing import Sequence

from .scenario import Stop, Tower, Weather


@dataclass(frozen=True)
class EnergyBreakdown:
    base_energy: float
    flight_energy: float
    hover_energy: float
    sensor_energy: float
    wind_energy: float
    payload_energy: float
    temperature_energy: float

    @property
    def total_energy(self) -> float:
        return round(
            self.base_energy
            + self.flight_energy
            + self.hover_energy
            + self.sensor_energy
            + self.wind_energy
            + self.payload_energy
            + self.temperature_energy,
            6,
        )


@dataclass(frozen=True)
class EnergyEstimate:
    mean_energy: float
    std_energy: float
    q95_energy: float
    duration: float
    distance: float
    flight_time: float
    service_time: float
    endurance_limit: float
    reserve_energy: float
    safety_margin: float
    wind_alignment: float
    components: EnergyBreakdown


class EnergyModel:
    def __init__(
        self,
        battery_capacity: float = 220.0,
        reserve_ratio: float = 0.12,
        quantile_z: float = 1.645,
        drone_speed_kmph: float = 46.0,
    ) -> None:
        self.battery_capacity = battery_capacity
        self.reserve_ratio = reserve_ratio
        self.quantile_z = quantile_z
        self.drone_speed_kmph = drone_speed_kmph

    def estimate(self, stop: Stop, tower: Tower, weather: Weather) -> EnergyEstimate:
        one_way_km = hypot(stop.x - tower.x, stop.y - tower.y)
        route_km = 2.0 * one_way_km
        bearing = atan2(tower.y - stop.y, tower.x - stop.x)
        wind_alignment = cos(radians(weather.wind_direction) - bearing)
        nominal_flight_energy = route_km * 8.6
        wind_energy = nominal_flight_energy * 0.025 * weather.wind_speed * (1.0 - 0.35 * wind_alignment)
        temperature_energy = nominal_flight_energy * max(0.0, abs(weather.temperature - 22.0) - 5.0) * 0.006
        payload_energy = nominal_flight_energy * 0.08 * tower.payload
        hover_energy = tower.service_time * 1.85
        sensor_energy = tower.service_time * 0.55
        components = EnergyBreakdown(
            base_energy=12.0,
            flight_energy=round(nominal_flight_energy, 6),
            hover_energy=round(hover_energy, 6),
            sensor_energy=round(sensor_energy, 6),
            wind_energy=round(max(0.0, wind_energy), 6),
            payload_energy=round(max(0.0, payload_energy), 6),
            temperature_energy=round(max(0.0, temperature_energy), 6),
        )
        mean = components.total_energy
        std = max(2.5, mean * weather.uncertainty * (0.8 + 0.04 * weather.wind_speed))
        q95 = mean + self.quantile_z * std
        flight_time = route_km / max(1.0, self.drone_speed_kmph) * 60.0
        duration = flight_time + tower.service_time
        reserve_energy = self.battery_capacity * self.reserve_ratio
        endurance_limit = self.battery_capacity - reserve_energy
        return EnergyEstimate(
            mean_energy=mean,
            std_energy=round(std, 6),
            q95_energy=round(q95, 6),
            duration=round(duration, 6),
            distance=round(route_km, 6),
            flight_time=round(flight_time, 6),
            service_time=round(tower.service_time, 6),
            endurance_limit=round(endurance_limit, 6),
            reserve_energy=round(reserve_energy, 6),
            safety_margin=round(endurance_limit - q95, 6),
            wind_alignment=round(wind_alignment, 6),
            components=components,
        )

    def estimate_sortie(self, stop: Stop, towers: Sequence[Tower], weather: Weather) -> EnergyEstimate:
        if not towers:
            raise ValueError("a sortie must inspect at least one tower")

        route_points = [(stop.x, stop.y)] + [(tower.x, tower.y) for tower in towers] + [(stop.x, stop.y)]
        route_km = 0.0
        wind_energy = 0.0
        weighted_alignment = 0.0
        for left, right in zip(route_points, route_points[1:]):
            leg_km = hypot(left[0] - right[0], left[1] - right[1])
            if leg_km == 0.0:
                continue
            bearing = atan2(right[1] - left[1], right[0] - left[0])
            alignment = cos(radians(weather.wind_direction) - bearing)
            leg_nominal = leg_km * 8.6
            wind_energy += leg_nominal * 0.025 * weather.wind_speed * (1.0 - 0.35 * alignment)
            weighted_alignment += alignment * leg_km
            route_km += leg_km

        service_time = sum(tower.service_time for tower in towers)
        payload_proxy = sum(tower.payload for tower in towers) / len(towers)
        nominal_flight_energy = route_km * 8.6
        temperature_energy = nominal_flight_energy * max(0.0, abs(weather.temperature - 22.0) - 5.0) * 0.006
        payload_energy = nominal_flight_energy * 0.08 * payload_proxy
        hover_energy = service_time * 1.85
        sensor_energy = service_time * 0.55
        components = EnergyBreakdown(
            base_energy=12.0,
            flight_energy=round(nominal_flight_energy, 6),
            hover_energy=round(hover_energy, 6),
            sensor_energy=round(sensor_energy, 6),
            wind_energy=round(max(0.0, wind_energy), 6),
            payload_energy=round(max(0.0, payload_energy), 6),
            temperature_energy=round(max(0.0, temperature_energy), 6),
        )
        mean = components.total_energy
        std = max(2.5, mean * weather.uncertainty * (0.8 + 0.04 * weather.wind_speed))
        q95 = mean + self.quantile_z * std
        flight_time = route_km / max(1.0, self.drone_speed_kmph) * 60.0
        duration = flight_time + service_time
        reserve_energy = self.battery_capacity * self.reserve_ratio
        endurance_limit = self.battery_capacity - reserve_energy
        wind_alignment = weighted_alignment / route_km if route_km > 0.0 else 0.0
        return EnergyEstimate(
            mean_energy=mean,
            std_energy=round(std, 6),
            q95_energy=round(q95, 6),
            duration=round(duration, 6),
            distance=round(route_km, 6),
            flight_time=round(flight_time, 6),
            service_time=round(service_time, 6),
            endurance_limit=round(endurance_limit, 6),
            reserve_energy=round(reserve_energy, 6),
            safety_margin=round(endurance_limit - q95, 6),
            wind_alignment=round(wind_alignment, 6),
            components=components,
        )

    def is_feasible(self, estimate: EnergyEstimate, use_quantile: bool = True) -> bool:
        limit = self.battery_capacity * (1.0 - self.reserve_ratio)
        required = estimate.q95_energy if use_quantile else estimate.mean_energy
        return required <= limit
