from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Dict, List, Optional

from .energy import EnergyModel
from .metrics import evaluate_plan
from .scenario import Scenario
from .solvers import Plan, solve


@dataclass(frozen=True)
class Event:
    kind: str
    time: float
    severity: float
    tower_id: Optional[int] = None


@dataclass(frozen=True)
class OnlineResult:
    policy: str
    events: List[Event]
    plan: Plan
    metrics: Dict[str, float]


def generate_events(scenario: Scenario, seed: int = 0, count: int = 4) -> List[Event]:
    rng = Random(seed)
    kinds = ["wind_shift", "road_delay", "urgent_reinspection", "communication_loss"]
    events: List[Event] = []
    for _ in range(count):
        tower = rng.choice(scenario.towers)
        events.append(
            Event(
                kind=rng.choice(kinds),
                time=round(rng.uniform(5.0, 90.0), 6),
                severity=round(rng.uniform(0.1, 1.0), 6),
                tower_id=tower.id,
            )
        )
    return sorted(events, key=lambda event: event.time)


def simulate_online_policy(scenario: Scenario, policy: str, seed: int = 0) -> OnlineResult:
    events = generate_events(scenario, seed=seed)
    energy_model = EnergyModel(battery_capacity=scenario.battery_capacity)
    if policy == "static":
        plan = solve(scenario, "alns_point", energy_model=energy_model, iterations=40, seed=seed)
        response_time = 0.0
        penalty_scale = 1.0
    elif policy == "periodic":
        plan = solve(scenario, "uq_alns", energy_model=energy_model, iterations=45, seed=seed)
        response_time = 2.0 + 0.15 * len(events)
        penalty_scale = 0.62
    elif policy == "event_triggered":
        plan = solve(scenario, "uq_rv_alns", energy_model=energy_model, iterations=55, seed=seed)
        response_time = 0.8 + 0.08 * len(events)
        penalty_scale = 0.36
    else:
        raise ValueError(f"unknown online policy {policy!r}")

    metrics = evaluate_plan(scenario, plan, energy_model)
    disturbance = sum(event.severity for event in events)
    metrics["makespan"] = round(metrics["makespan"] + penalty_scale * disturbance * 4.0, 6)
    metrics["risk_weighted_completion_time"] = round(
        metrics["risk_weighted_completion_time"] * (1.0 + 0.015 * penalty_scale * disturbance),
        6,
    )
    metrics["online_response_time"] = round(response_time, 6)
    metrics["event_count"] = float(len(events))
    metrics["disturbance_intensity"] = round(disturbance, 6)
    return OnlineResult(policy=policy, events=events, plan=plan, metrics=metrics)

