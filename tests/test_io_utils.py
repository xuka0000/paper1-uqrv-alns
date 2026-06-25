import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.io_utils import ensure_experiment_dirs, write_rows_csv


class IoUtilsTests(unittest.TestCase):
    def test_ensure_experiment_dirs_creates_required_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = ensure_experiment_dirs(Path(tmp), "E0_smoke", "run1")
            for name in ["raw_data", "analysis_data", "figures", "logs", "runs"]:
                self.assertTrue((root / name).exists())
            self.assertTrue((root / "runs" / "run1").exists())

    def test_write_rows_csv_writes_header_and_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rows.csv"
            write_rows_csv(out, [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}])
            text = out.read_text(encoding="utf-8")
            self.assertIn("a,b", text)
            self.assertIn("1,x", text)

    def test_write_rows_csv_allows_later_rows_to_add_columns(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "heterogeneous.csv"
            write_rows_csv(out, [{"a": 1}, {"a": 2, "b": "late"}])
            text = out.read_text(encoding="utf-8")
            self.assertIn("a,b", text)
            self.assertIn("2,late", text)


if __name__ == "__main__":
    unittest.main()
