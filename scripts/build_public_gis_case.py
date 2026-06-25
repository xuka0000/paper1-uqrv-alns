from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.public_data_ingestion import build_public_gis_case, parse_bbox


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a GIS-grounded case from public tower and weather sources.")
    parser.add_argument("--bbox", required=True, help="min_lon,min_lat,max_lon,max_lat")
    parser.add_argument("--date", default="20250101", help="NASA POWER date in YYYYMMDD format")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--tower-limit", type=int, default=120)
    parser.add_argument("--stop-count", type=int, default=0, help="0 means half of selected tower count")
    parser.add_argument("--vehicle-count", type=int, default=2)
    parser.add_argument("--uav-count", type=int, default=4)
    args = parser.parse_args()

    paths = build_public_gis_case(
        bbox=parse_bbox(args.bbox),
        out_dir=args.out_dir,
        date_yyyymmdd=args.date,
        tower_limit=args.tower_limit,
        stop_count=args.stop_count or None,
        vehicle_count=args.vehicle_count,
        uav_count=args.uav_count,
    )
    print("Wrote public GIS case:")
    for name, path in paths.items():
        print(f"  {name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
