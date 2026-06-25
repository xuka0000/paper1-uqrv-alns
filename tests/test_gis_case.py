import shutil
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from uqrv.gis_case import load_gis_case, write_gis_case_templates


class GisCaseTests(unittest.TestCase):
    def test_load_gis_case_from_csv_templates(self):
        root = Path(__file__).resolve().parent / "_tmp_gis_case"
        if root.exists():
            shutil.rmtree(root)
        try:
            write_gis_case_templates(root)
            (root / "towers.csv").write_text(
                "id,x,y,risk,value,service_time,payload,segment\n"
                "0,0.0,0.0,0.70,100.0,5.0,1.0,0\n"
                "1,2.0,0.5,0.30,50.0,4.0,0.8,0\n",
                encoding="utf-8",
            )
            (root / "stops.csv").write_text(
                "id,x,y\n0,-0.2,0.0\n1,2.3,0.4\n",
                encoding="utf-8",
            )
            (root / "weather.csv").write_text(
                "wind_speed,wind_direction,temperature,uncertainty,battery_capacity,vehicle_count,uav_count,vehicle_speed_kmph,drone_speed_kmph\n"
                "4.5,90.0,26.0,0.18,150.0,1,2,65.0,46.0\n",
                encoding="utf-8",
            )

            scenario = load_gis_case(root, case_id="line_a")

            self.assertEqual(scenario.id, "line_a")
            self.assertEqual(scenario.size, "GIS")
            self.assertEqual(len(scenario.towers), 2)
            self.assertEqual(len(scenario.stops), 2)
            self.assertEqual(scenario.uav_count, 2)
            self.assertAlmostEqual(scenario.weather.wind_speed, 4.5)
        finally:
            if root.exists():
                shutil.rmtree(root)

    def test_template_writer_creates_schema_readme(self):
        root = Path(__file__).resolve().parent / "_tmp_gis_template"
        if root.exists():
            shutil.rmtree(root)
        try:
            paths = write_gis_case_templates(root)
            self.assertTrue(paths["towers_csv"].exists())
            self.assertTrue(paths["stops_csv"].exists())
            self.assertTrue(paths["weather_csv"].exists())
            self.assertTrue(paths["readme"].exists())
            self.assertIn("projected kilometer", paths["readme"].read_text(encoding="utf-8"))
        finally:
            if root.exists():
                shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
