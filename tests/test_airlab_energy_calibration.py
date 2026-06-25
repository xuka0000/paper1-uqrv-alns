import csv
import shutil
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from scripts.run_airlab_energy_calibration import _numeric_parameter, _summarize_telemetry, run_calibration


class AirLabEnergyCalibrationTests(unittest.TestCase):
    def test_numeric_parameter_averages_composite_values(self):
        self.assertEqual(_numeric_parameter("25"), 25.0)
        self.assertEqual(_numeric_parameter("25-50-100-25"), 50.0)

    def test_summarize_telemetry_integrates_energy(self):
        root = Path(__file__).resolve().parent / "_tmp_airlab"
        if root.exists():
            shutil.rmtree(root)
        try:
            root.mkdir()
            path = root / "1.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "time",
                        "wind_speed",
                        "wind_angle",
                        "battery_voltage",
                        "battery_current",
                        "velocity_x",
                        "velocity_y",
                        "velocity_z",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "time": 0.0,
                        "wind_speed": 2.0,
                        "wind_angle": 0.0,
                        "battery_voltage": 20.0,
                        "battery_current": 10.0,
                        "velocity_x": 1.0,
                        "velocity_y": 0.0,
                        "velocity_z": 0.0,
                    }
                )
                writer.writerow(
                    {
                        "time": 1.0,
                        "wind_speed": 4.0,
                        "wind_angle": 0.0,
                        "battery_voltage": 20.0,
                        "battery_current": 10.0,
                        "velocity_x": 1.0,
                        "velocity_y": 0.0,
                        "velocity_z": 0.0,
                    }
                )
            summary = _summarize_telemetry(path)
            self.assertAlmostEqual(summary["energy_wh"], 200.0 / 3600.0, places=6)
            self.assertAlmostEqual(summary["distance_m"], 1.0, places=6)
            self.assertAlmostEqual(summary["mean_wind_speed"], 3.0, places=6)
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_run_calibration_returns_summary_and_predictions(self):
        rows = []
        for flight in range(1, 11):
            rows.append(
                {
                    "flight": flight,
                    "speed": 4.0 + flight % 3,
                    "payload": float(flight % 2),
                    "altitude": 25.0,
                    "route": f"R{flight % 3}",
                    "duration_s": 100.0 + flight,
                    "mean_wind_speed": 2.0 + 0.1 * flight,
                    "std_wind_speed": 0.2,
                    "energy_wh": 10.0 + 0.7 * flight,
                    "split": "test" if flight % 5 == 0 else "train",
                }
            )
        predictions, summary = run_calibration(rows)
        self.assertEqual({row["model"] for row in summary}, {"constant_mean", "parameter_linear", "parameter_route_linear", "telemetry_weather_linear"})
        for row in summary:
            self.assertIn("wape", row)
            self.assertIn("smape", row)
            self.assertGreaterEqual(row["wape"], 0.0)
            self.assertLessEqual(row["smape"], 2.0)
        self.assertTrue(predictions)


if __name__ == "__main__":
    unittest.main()
