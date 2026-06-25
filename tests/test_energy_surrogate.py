import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.energy import EnergyModel
from uqrv.energy_surrogate import (
    ProbabilisticEnergySurrogate,
    SimulationTrainedEnergySurrogate,
    evaluate_energy_surrogate,
    generate_energy_training_samples,
)
from uqrv.scenario import generate_scenario


class EnergySurrogateTests(unittest.TestCase):
    def test_surrogate_exposes_scheduler_parameters_and_truth_boundary(self):
        scenario = generate_scenario(size="S", seed=11)
        surrogate = ProbabilisticEnergySurrogate(
            EnergyModel(battery_capacity=scenario.battery_capacity),
            evidence_level="simulation_calibrated",
        )

        prediction = surrogate.predict(scenario.stops[0], scenario.towers[0], scenario.weather)
        params = prediction.as_scheduler_parameters()

        self.assertEqual(prediction.evidence_level, "simulation_calibrated")
        self.assertEqual(prediction.training_status, "not_field_trained")
        self.assertEqual(prediction.source_model, "explicit_physics_energy_model")
        self.assertFalse(prediction.field_validated)
        self.assertIn("energy_mean", params)
        self.assertIn("energy_q95", params)
        self.assertIn("flight_time", params)
        self.assertIn("service_time", params)
        self.assertIn("endurance_limit", params)
        self.assertIn("q95_feasible", params)
        self.assertAlmostEqual(params["energy_q95"], prediction.energy_q95)

    def test_surrogate_prediction_matches_underlying_energy_estimate(self):
        scenario = generate_scenario(size="S", seed=12)
        model = EnergyModel(battery_capacity=scenario.battery_capacity)
        surrogate = ProbabilisticEnergySurrogate(model)

        estimate = model.estimate(scenario.stops[1], scenario.towers[1], scenario.weather)
        prediction = surrogate.predict(scenario.stops[1], scenario.towers[1], scenario.weather)

        self.assertAlmostEqual(prediction.energy_mean, estimate.mean_energy)
        self.assertAlmostEqual(prediction.energy_std, estimate.std_energy)
        self.assertAlmostEqual(prediction.energy_q95, estimate.q95_energy)
        self.assertAlmostEqual(prediction.safety_margin, estimate.safety_margin)

    def test_simulation_trained_surrogate_records_training_status_and_round_trips(self):
        samples = generate_energy_training_samples(seed_range=range(3), max_pairs_per_scenario=8)
        surrogate = SimulationTrainedEnergySurrogate.fit(samples)
        path = Path(__file__).resolve().parent / "_tmp_energy_surrogate.json"
        try:
            surrogate.to_json(path)
            loaded = SimulationTrainedEnergySurrogate.from_json(path)
        finally:
            if path.exists():
                path.unlink()

        sample = samples[0]
        prediction = loaded.predict(sample.stop, sample.tower, sample.weather)
        self.assertEqual(prediction.evidence_level, "simulation_trained")
        self.assertEqual(prediction.training_status, "simulation_trained_not_field_validated")
        self.assertFalse(prediction.field_validated)
        self.assertGreater(prediction.energy_q95, prediction.energy_mean)
        self.assertGreater(prediction.flight_time, 0.0)
        self.assertGreater(prediction.service_time, 0.0)

    def test_simulation_trained_surrogate_improves_over_nominal_physics_baseline(self):
        train = generate_energy_training_samples(seed_range=range(6), max_pairs_per_scenario=10)
        test = generate_energy_training_samples(seed_range=range(20, 24), max_pairs_per_scenario=10)
        trained = SimulationTrainedEnergySurrogate.fit(train)

        trained_metrics = evaluate_energy_surrogate(trained, test)
        nominal_metrics = evaluate_energy_surrogate(
            ProbabilisticEnergySurrogate(EnergyModel(), evidence_level="nominal_fixed_physics"),
            test,
        )

        self.assertLess(trained_metrics["mae"], nominal_metrics["mae"] * 0.80)
        self.assertGreaterEqual(trained_metrics["coverage_95"], 0.85)


if __name__ == "__main__":
    unittest.main()
