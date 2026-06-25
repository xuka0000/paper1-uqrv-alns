import shutil
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.gis_case import load_gis_case
from uqrv.public_data_ingestion import (
    BBox,
    PublicTowerNode,
    build_gis_rows,
    parse_bbox,
    project_lonlat_to_km,
    write_public_gis_case,
)


class PublicDataIngestionTests(unittest.TestCase):
    def test_parse_bbox_and_projection(self):
        bbox = parse_bbox("-122.1,37.3,-121.9,37.5")
        self.assertAlmostEqual(bbox.center_lon, -122.0)
        self.assertAlmostEqual(bbox.center_lat, 37.4)
        x0, y0 = project_lonlat_to_km(-122.0, 37.4, bbox)
        self.assertAlmostEqual(x0, 0.0, places=5)
        self.assertAlmostEqual(y0, 0.0, places=5)

    def test_build_rows_can_be_loaded_as_gis_case(self):
        bbox = BBox(-122.1, 37.3, -121.9, 37.5)
        nodes = [
            PublicTowerNode("100", -122.08, 37.33, {"power": "tower"}),
            PublicTowerNode("101", -122.04, 37.36, {"power": "tower"}),
            PublicTowerNode("102", -122.00, 37.39, {"power": "tower"}),
            PublicTowerNode("103", -121.96, 37.42, {"power": "tower"}),
            PublicTowerNode("104", -121.92, 37.46, {"power": "tower"}),
        ]
        root = Path(__file__).resolve().parent / "_tmp_public_gis_case"
        if root.exists():
            shutil.rmtree(root)
        try:
            towers, stops = build_gis_rows(nodes, bbox, tower_limit=5, stop_count=3)
            paths = write_public_gis_case(
                root,
                towers,
                stops,
                {"wind_speed": 4.0, "wind_direction": 80.0, "temperature": 22.0, "uncertainty": 0.15},
                {"vehicle_count": 1, "uav_count": 2, "battery_capacity": 150.0},
            )
            self.assertTrue(paths["metadata_json"].exists())
            scenario = load_gis_case(root, case_id="public_case")
            self.assertEqual(len(scenario.towers), 5)
            self.assertEqual(len(scenario.stops), 3)
            self.assertEqual(scenario.vehicle_count, 1)
            self.assertEqual(scenario.uav_count, 2)
            self.assertGreater(scenario.towers[0].value, 0.0)
        finally:
            if root.exists():
                shutil.rmtree(root)


if __name__ == "__main__":
    unittest.main()
