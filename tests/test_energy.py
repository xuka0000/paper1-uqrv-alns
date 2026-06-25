import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.energy import EnergyModel
from uqrv.scenario import Weather, generate_scenario


class EnergyTests(unittest.TestCase):
    def test_quantile_energy_exceeds_mean(self):
        scenario = generate_scenario(size="S", seed=1)
        model = EnergyModel()
        estimate = model.estimate(scenario.stops[0], scenario.towers[0], scenario.weather)
        self.assertGreaterEqual(estimate.q95_energy, estimate.mean_energy)

    def test_feasibility_respects_battery_reserve(self):
        scenario = generate_scenario(size="S", seed=2)
        model = EnergyModel(battery_capacity=1.0)
        estimate = model.estimate(scenario.stops[0], scenario.towers[0], scenario.weather)
        self.assertFalse(model.is_feasible(estimate))

    def test_estimate_exposes_physical_breakdown_and_safety_margin(self):
        scenario = generate_scenario(size="S", seed=3)
        model = EnergyModel(battery_capacity=scenario.battery_capacity, reserve_ratio=0.2)
        estimate = model.estimate(scenario.stops[0], scenario.towers[0], scenario.weather)

        self.assertGreater(estimate.components.flight_energy, 0.0)
        self.assertGreater(estimate.components.hover_energy, 0.0)
        self.assertGreater(estimate.components.sensor_energy, 0.0)
        self.assertGreaterEqual(estimate.components.wind_energy, 0.0)
        self.assertGreaterEqual(estimate.components.payload_energy, 0.0)
        self.assertGreaterEqual(estimate.components.temperature_energy, 0.0)
        self.assertAlmostEqual(estimate.components.total_energy, estimate.mean_energy, places=5)
        self.assertAlmostEqual(estimate.flight_time + estimate.service_time, estimate.duration, places=5)
        self.assertAlmostEqual(estimate.endurance_limit, scenario.battery_capacity * 0.8, places=5)
        self.assertAlmostEqual(estimate.safety_margin, estimate.endurance_limit - estimate.q95_energy, places=5)

    def test_higher_uncertainty_increases_std_and_quantile_bound(self):
        scenario = generate_scenario(size="S", seed=4)
        model = EnergyModel(battery_capacity=scenario.battery_capacity)
        low_weather = Weather(
            wind_speed=scenario.weather.wind_speed,
            wind_direction=scenario.weather.wind_direction,
            temperature=scenario.weather.temperature,
            uncertainty=0.05,
        )
        high_weather = Weather(
            wind_speed=scenario.weather.wind_speed,
            wind_direction=scenario.weather.wind_direction,
            temperature=scenario.weather.temperature,
            uncertainty=0.35,
        )

        low = model.estimate(scenario.stops[0], scenario.towers[0], low_weather)
        high = model.estimate(scenario.stops[0], scenario.towers[0], high_weather)

        self.assertGreater(high.std_energy, low.std_energy)
        self.assertGreater(high.q95_energy, low.q95_energy)

    def test_multi_tower_sortie_uses_continuous_same_stop_path(self):
        scenario = generate_scenario(size="S", seed=5)
        model = EnergyModel(battery_capacity=scenario.battery_capacity)
        stop = scenario.stops[0]
        tower_a = scenario.towers[0]
        tower_b = scenario.towers[1]

        sortie = model.estimate_sortie(stop, [tower_a, tower_b], scenario.weather)
        single_a = model.estimate(stop, tower_a, scenario.weather)
        single_b = model.estimate(stop, tower_b, scenario.weather)

        expected_distance = (
            ((stop.x - tower_a.x) ** 2 + (stop.y - tower_a.y) ** 2) ** 0.5
            + ((tower_a.x - tower_b.x) ** 2 + (tower_a.y - tower_b.y) ** 2) ** 0.5
            + ((tower_b.x - stop.x) ** 2 + (tower_b.y - stop.y) ** 2) ** 0.5
        )
        self.assertAlmostEqual(sortie.distance, expected_distance, places=5)
        self.assertLess(sortie.distance, single_a.distance + single_b.distance)
        self.assertAlmostEqual(sortie.service_time, tower_a.service_time + tower_b.service_time, places=5)
        self.assertGreaterEqual(sortie.q95_energy, sortie.mean_energy)


if __name__ == "__main__":
    unittest.main()
