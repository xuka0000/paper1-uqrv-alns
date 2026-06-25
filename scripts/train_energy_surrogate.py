from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Dict

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.energy_surrogate import (
    ProbabilisticEnergySurrogate,
    SimulationTrainedEnergySurrogate,
    evaluate_energy_surrogate,
    generate_energy_training_samples,
)
from uqrv.io_utils import write_json, write_markdown, write_rows_csv


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-dir",
        default=str(PROJECT_ROOT / "results" / "experiments" / "P3_pinn_prediction_accuracy" / "models"),
    )
    parser.add_argument("--train-seed-start", type=int, default=30)
    parser.add_argument("--train-seed-count", type=int, default=12)
    parser.add_argument("--test-seed-start", type=int, default=90)
    parser.add_argument("--test-seed-count", type=int, default=6)
    parser.add_argument("--max-pairs-per-scenario", type=int, default=14)
    args = parser.parse_args()

    result = train_and_write(
        Path(args.out_dir),
        train_seed_start=args.train_seed_start,
        train_seed_count=args.train_seed_count,
        test_seed_start=args.test_seed_start,
        test_seed_count=args.test_seed_count,
        max_pairs_per_scenario=args.max_pairs_per_scenario,
    )
    print(result["model_path"])
    print(result["metrics_csv"])
    return 0


def train_and_write(
    out_dir: Path,
    train_seed_start: int = 30,
    train_seed_count: int = 12,
    test_seed_start: int = 90,
    test_seed_count: int = 6,
    max_pairs_per_scenario: int = 14,
) -> Dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    energy_model = EnergyModel(battery_capacity=150.0)
    train_samples = generate_energy_training_samples(
        seed_range=range(train_seed_start, train_seed_start + train_seed_count),
        max_pairs_per_scenario=max_pairs_per_scenario,
        energy_model=energy_model,
    )
    test_samples = generate_energy_training_samples(
        seed_range=range(test_seed_start, test_seed_start + test_seed_count),
        max_pairs_per_scenario=max_pairs_per_scenario,
        energy_model=energy_model,
    )
    trained = SimulationTrainedEnergySurrogate.fit(train_samples, energy_model)
    nominal = ProbabilisticEnergySurrogate(energy_model, evidence_level="simulation_calibrated")
    trained_metrics = evaluate_energy_surrogate(trained, test_samples)
    nominal_metrics = evaluate_energy_surrogate(nominal, test_samples)
    trained_metrics["training_sample_count"] = len(train_samples)
    trained_metrics["test_sample_count"] = len(test_samples)
    nominal_metrics["training_sample_count"] = 0
    nominal_metrics["test_sample_count"] = len(test_samples)

    model_path = out_dir / "simulation_trained_energy_surrogate.json"
    metrics_csv = out_dir / "simulation_trained_energy_surrogate_metrics.csv"
    metrics_json = out_dir / "simulation_trained_energy_surrogate_metrics.json"
    readme = out_dir / "README.md"

    trained.to_json(model_path)
    rows = [
        {"model": "nominal_physics", **nominal_metrics},
        {"model": "simulation_trained_surrogate", **trained_metrics},
    ]
    write_rows_csv(metrics_csv, rows)
    write_json(
        metrics_json,
        {
            "model_path": str(model_path),
            "metrics_csv": str(metrics_csv),
            "train_seed_start": train_seed_start,
            "train_seed_count": train_seed_count,
            "test_seed_start": test_seed_start,
            "test_seed_count": test_seed_count,
            "max_pairs_per_scenario": max_pairs_per_scenario,
            "trained_metrics": trained_metrics,
            "nominal_metrics": nominal_metrics,
            "evidence_boundary": "simulation-trained synthetic energy labels; not field validated",
        },
    )
    write_markdown(
        readme,
        "Simulation-Trained Energy Surrogate",
        [
            {
                "artifact": "model",
                "path": str(model_path),
                "status": "simulation_trained_not_field_validated",
            },
            {
                "artifact": "metrics",
                "path": str(metrics_csv),
                "status": "held-out synthetic evaluation",
            },
        ],
    )
    return {
        "model_path": str(model_path),
        "metrics_csv": str(metrics_csv),
        "metrics_json": str(metrics_json),
        "readme": str(readme),
        "trained_metrics": trained_metrics,
        "nominal_metrics": nominal_metrics,
    }


if __name__ == "__main__":
    raise SystemExit(main())
