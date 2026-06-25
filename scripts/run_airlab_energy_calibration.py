from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Tuple

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.io_utils import ensure_experiment_dirs, write_json, write_markdown, write_rows_csv


FEATURE_SETS = {
    "constant_mean": [],
    "parameter_linear": ["speed", "payload", "altitude"],
    "parameter_route_linear": ["speed", "payload", "altitude", "route"],
    "telemetry_weather_linear": ["speed", "payload", "altitude", "route", "duration_s", "mean_wind_speed", "std_wind_speed"],
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibrate energy prediction on the AirLab quadcopter telemetry dataset.")
    parser.add_argument("--airlab-root", default="results/experiments/P10_energy_telemetry_calibration/raw_sources/airlab")
    parser.add_argument("--run-id", default="airlab_energy_calibration_stop_batch_20260606")
    args = parser.parse_args()

    rows = load_airlab_flights(Path(args.airlab_root))
    predictions, summary = run_calibration(rows)
    write_outputs(args.run_id, rows, predictions, summary)
    print(f"P10_energy_telemetry_calibration: {len(rows)} flights, {len(predictions)} test predictions")
    return 0


def load_airlab_flights(root: Path) -> List[dict]:
    parameter_rows = _read_csv(root / "parameters.csv")
    by_flight = {int(float(row["flight"])): row for row in parameter_rows}
    rows = []
    for flight_id, params in sorted(by_flight.items()):
        flight_path = root / "flights" / f"{flight_id}.csv"
        if not flight_path.exists():
            continue
        telemetry = _summarize_telemetry(flight_path)
        if telemetry["duration_s"] <= 0.0 or telemetry["energy_wh"] <= 0.0:
            continue
        rows.append(
            {
                "flight": flight_id,
                "speed": float(params["speed"]),
                "payload": float(params["payload"]),
                "altitude": _numeric_parameter(params["altitude"]),
                "altitude_raw": params["altitude"],
                "route": params["route"],
                "date": params.get("date", ""),
                "local_time": params.get("local_time", ""),
                **telemetry,
                "split": "test" if flight_id % 5 == 0 else "train",
            }
        )
    return rows


def run_calibration(rows: List[dict]) -> Tuple[List[dict], List[dict]]:
    train_rows = [row for row in rows if row["split"] == "train"]
    test_rows = [row for row in rows if row["split"] == "test"]
    route_levels = sorted({row["route"] for row in train_rows})
    predictions = []
    summary = []
    for model_name, features in FEATURE_SETS.items():
        model = _fit_model(train_rows, features, route_levels)
        train_pred = _predict_rows(model, train_rows, features, route_levels)
        test_pred = _predict_rows(model, test_rows, features, route_levels)
        residual_std = _residual_std([row["energy_wh"] for row in train_rows], train_pred)
        for row, pred in zip(test_rows, test_pred):
            q95 = pred + 1.96 * residual_std
            threshold = _high_energy_threshold(train_rows)
            predictions.append(
                {
                    "model": model_name,
                    "flight": row["flight"],
                    "split": "test",
                    "actual_energy_wh": round(row["energy_wh"], 6),
                    "predicted_energy_wh": round(pred, 6),
                    "q95_energy_wh": round(q95, 6),
                    "absolute_error_wh": round(abs(row["energy_wh"] - pred), 6),
                    "covered_95": int(abs(row["energy_wh"] - pred) <= 1.96 * residual_std),
                    "false_feasible_high_energy": int(q95 <= threshold and row["energy_wh"] > threshold),
                    "speed": row["speed"],
                    "payload": row["payload"],
                    "altitude": row["altitude"],
                    "route": row["route"],
                    "mean_wind_speed": round(row["mean_wind_speed"], 6),
                    "duration_s": round(row["duration_s"], 6),
                }
            )
        summary.append(_metric_row(model_name, test_rows, test_pred, residual_std, train_rows))
    return predictions, summary


def write_outputs(run_id: str, aggregate_rows: List[dict], predictions: List[dict], summary: List[dict]) -> Dict[str, Path]:
    root = ensure_experiment_dirs(PROJECT_ROOT / "results" / "experiments", "P10_energy_telemetry_calibration", run_id)
    aggregate_path = root / "raw_data" / f"P10_energy_telemetry_calibration_{run_id}_flight_aggregates.csv"
    pred_path = root / "analysis_data" / f"P10_energy_telemetry_calibration_{run_id}_predictions.csv"
    summary_path = root / "analysis_data" / f"P10_energy_telemetry_calibration_{run_id}_summary.csv"
    summary_md = root / "analysis_data" / f"P10_energy_telemetry_calibration_{run_id}_summary.md"
    run_json = root / "analysis_data" / f"P10_energy_telemetry_calibration_{run_id}_run_summary.json"
    write_rows_csv(aggregate_path, aggregate_rows)
    write_rows_csv(pred_path, predictions)
    write_rows_csv(summary_path, summary)
    write_markdown(summary_md, "P10 AirLab Energy Calibration Summary", summary)
    write_json(
        run_json,
        {
            "experiment_id": "P10_energy_telemetry_calibration",
            "run_id": run_id,
            "flight_count": len(aggregate_rows),
            "train_count": len([row for row in aggregate_rows if row["split"] == "train"]),
            "test_count": len([row for row in aggregate_rows if row["split"] == "test"]),
            "summary_csv": str(summary_path),
            "predictions_csv": str(pred_path),
            "evidence_boundary": "AirLab uses package-delivery quadcopter telemetry, not transmission-line inspection flights.",
        },
    )
    write_markdown(root / "runs" / run_id / "README.md", "P10 AirLab Energy Calibration", summary)
    return {
        "flight_aggregates_csv": aggregate_path,
        "predictions_csv": pred_path,
        "summary_csv": summary_path,
        "summary_md": summary_md,
        "run_summary_json": run_json,
    }


def _summarize_telemetry(path: Path) -> dict:
    rows = _read_csv(path)
    usable = []
    for row in rows:
        try:
            usable.append(
                {
                    "time": float(row["time"]),
                    "wind_speed": float(row["wind_speed"]),
                    "wind_angle": float(row["wind_angle"]),
                    "battery_voltage": float(row["battery_voltage"]),
                    "battery_current": abs(float(row["battery_current"])),
                    "velocity_x": float(row["velocity_x"]),
                    "velocity_y": float(row["velocity_y"]),
                    "velocity_z": float(row["velocity_z"]),
                }
            )
        except (KeyError, ValueError):
            continue
    if len(usable) < 2:
        return {
            "duration_s": 0.0,
            "energy_wh": 0.0,
            "mean_wind_speed": 0.0,
            "std_wind_speed": 0.0,
            "mean_voltage": 0.0,
            "mean_current": 0.0,
            "distance_m": 0.0,
        }
    energy_ws = 0.0
    distance_m = 0.0
    for first, second in zip(usable, usable[1:]):
        dt = second["time"] - first["time"]
        if dt < 0.0 or dt > 2.0:
            continue
        power_w = first["battery_voltage"] * first["battery_current"]
        speed_mps = math.sqrt(first["velocity_x"] ** 2 + first["velocity_y"] ** 2 + first["velocity_z"] ** 2)
        energy_ws += power_w * dt
        distance_m += speed_mps * dt
    wind = [row["wind_speed"] for row in usable]
    voltage = [row["battery_voltage"] for row in usable]
    current = [row["battery_current"] for row in usable]
    return {
        "duration_s": round(max(row["time"] for row in usable) - min(row["time"] for row in usable), 6),
        "energy_wh": round(energy_ws / 3600.0, 6),
        "mean_wind_speed": round(mean(wind), 6),
        "std_wind_speed": round(pstdev(wind), 6) if len(wind) > 1 else 0.0,
        "mean_voltage": round(mean(voltage), 6),
        "mean_current": round(mean(current), 6),
        "distance_m": round(distance_m, 6),
    }


def _fit_model(rows: List[dict], features: List[str], route_levels: List[str]) -> dict:
    y = np.array([row["energy_wh"] for row in rows], dtype=float)
    if not features:
        return {"coef": np.array([float(np.mean(y))]), "stats": {}}
    numeric = [feature for feature in features if feature != "route"]
    stats = _feature_stats(rows, numeric)
    x = _design_matrix(rows, features, route_levels, stats)
    coef, *_ = np.linalg.lstsq(x, y, rcond=None)
    return {"coef": coef, "stats": stats}


def _predict_rows(model: dict, rows: List[dict], features: List[str], route_levels: List[str]) -> List[float]:
    if not features:
        return [float(model["coef"][0]) for _ in rows]
    x = _design_matrix(rows, features, route_levels, model["stats"])
    return [max(0.0, float(value)) for value in x @ model["coef"]]


def _design_matrix(rows: List[dict], features: List[str], route_levels: List[str], stats: Dict[str, Tuple[float, float]]) -> np.ndarray:
    matrix = []
    numeric = [feature for feature in features if feature != "route"]
    for row in rows:
        vector = [1.0]
        for feature in numeric:
            mu, scale = stats[feature]
            vector.append((float(row[feature]) - mu) / scale)
        if "route" in features:
            for route in route_levels[:-1]:
                vector.append(1.0 if row["route"] == route else 0.0)
        matrix.append(vector)
    return np.array(matrix, dtype=float)


def _feature_stats(rows: List[dict], features: Iterable[str]) -> Dict[str, Tuple[float, float]]:
    stats = {}
    for feature in features:
        values = [float(row[feature]) for row in rows]
        scale = pstdev(values) if len(values) > 1 else 1.0
        stats[feature] = (mean(values), scale if scale > 1e-9 else 1.0)
    return stats


def _residual_std(actual: List[float], predicted: List[float]) -> float:
    residuals = [a - p for a, p in zip(actual, predicted)]
    return max(1e-6, pstdev(residuals) if len(residuals) > 1 else abs(residuals[0]))


def _metric_row(model_name: str, rows: List[dict], predicted: List[float], residual_std: float, train_rows: List[dict]) -> dict:
    actual = [row["energy_wh"] for row in rows]
    errors = [a - p for a, p in zip(actual, predicted)]
    abs_errors = [abs(error) for error in errors]
    squared = [error * error for error in errors]
    ape = [abs(error) / max(1e-6, a) for a, error in zip(actual, errors)]
    wape = sum(abs_errors) / max(1e-6, sum(abs(a) for a in actual))
    smape_values = [
        0.0 if abs(a) + abs(p) <= 1e-9 else 2.0 * abs(a - p) / (abs(a) + abs(p))
        for a, p in zip(actual, predicted)
    ]
    threshold = _high_energy_threshold(train_rows)
    q95 = [p + 1.96 * residual_std for p in predicted]
    covered = [abs(a - p) <= 1.96 * residual_std for a, p in zip(actual, predicted)]
    false_feasible = [bound <= threshold and a > threshold for a, bound in zip(actual, q95)]
    return {
        "model": model_name,
        "train_count": len(train_rows),
        "test_count": len(rows),
        "mae_wh": round(mean(abs_errors), 6),
        "rmse_wh": round(math.sqrt(mean(squared)), 6),
        "mape": round(mean(ape), 6),
        "wape": round(wape, 6),
        "smape": round(mean(smape_values), 6),
        "bias_wh": round(mean(errors), 6),
        "residual_std_wh": round(residual_std, 6),
        "coverage_95": round(sum(covered) / len(covered), 6),
        "false_feasible_high_energy_rate": round(sum(false_feasible) / len(false_feasible), 6),
        "high_energy_threshold_wh": round(threshold, 6),
    }


def _high_energy_threshold(rows: List[dict]) -> float:
    values = sorted(row["energy_wh"] for row in rows)
    index = min(len(values) - 1, max(0, int(round(0.75 * (len(values) - 1)))))
    return values[index]


def _read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _numeric_parameter(value: str) -> float:
    parts = [part.strip() for part in value.split("-") if part.strip()]
    numbers = [float(part) for part in parts]
    return mean(numbers)


if __name__ == "__main__":
    raise SystemExit(main())
