import shutil
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from train_energy_surrogate import train_and_write


class EnergyTrainingScriptTests(unittest.TestCase):
    def test_train_and_write_creates_model_and_metric_artifacts(self):
        out_dir = Path(__file__).resolve().parent / "_tmp_energy_training"
        if out_dir.exists():
            shutil.rmtree(out_dir)
        try:
            result = train_and_write(
                out_dir,
                train_seed_start=30,
                train_seed_count=3,
                test_seed_start=90,
                test_seed_count=2,
                max_pairs_per_scenario=6,
            )
            self.assertTrue(Path(result["model_path"]).exists())
            self.assertTrue(Path(result["metrics_csv"]).exists())
            self.assertGreater(result["trained_metrics"]["training_sample_count"], 0)
            self.assertLess(result["trained_metrics"]["mae"], result["nominal_metrics"]["mae"])
        finally:
            if out_dir.exists():
                shutil.rmtree(out_dir)


if __name__ == "__main__":
    unittest.main()
