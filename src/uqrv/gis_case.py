from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterable, List

from .scenario import Scenario, Stop, Tower, Weather


def load_gis_case(root: str | Path, case_id: str = "gis_case") -> Scenario:
    """Load a projected-coordinate transmission-line case from CSV files."""

    root = Path(root)
    towers = [
        Tower(
            id=int(row["id"]),
            x=float(row["x"]),
            y=float(row["y"]),
            risk=float(row["risk"]),
            value=float(row["value"]),
            service_time=float(row["service_time"]),
            payload=float(row["payload"]),
            segment=int(row.get("segment", 0) or 0),
        )
        for row in _read_csv(root / "towers.csv")
    ]
    stops = [
        Stop(
            id=int(row["id"]),
            x=float(row["x"]),
            y=float(row["y"]),
        )
        for row in _read_csv(root / "stops.csv")
    ]
    weather_row = _first_row(root / "weather.csv")
    weather = Weather(
        wind_speed=float(weather_row.get("wind_speed", 3.0)),
        wind_direction=float(weather_row.get("wind_direction", 0.0)),
        temperature=float(weather_row.get("temperature", 22.0)),
        uncertainty=float(weather_row.get("uncertainty", 0.16)),
    )
    return Scenario(
        id=case_id,
        size="GIS",
        seed=0,
        towers=towers,
        stops=stops,
        vehicle_count=int(float(weather_row.get("vehicle_count", 1))),
        uav_count=int(float(weather_row.get("uav_count", 2))),
        vehicle_speed_kmph=float(weather_row.get("vehicle_speed_kmph", 65.0)),
        drone_speed_kmph=float(weather_row.get("drone_speed_kmph", 46.0)),
        battery_capacity=float(weather_row.get("battery_capacity", 150.0)),
        weather=weather,
    )


def write_gis_case_templates(root: str | Path) -> Dict[str, Path]:
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    towers_csv = root / "towers.csv"
    stops_csv = root / "stops.csv"
    weather_csv = root / "weather.csv"
    readme = root / "README.md"
    if not towers_csv.exists():
        towers_csv.write_text(
            "id,x,y,risk,value,service_time,payload,segment\n"
            "0,0.0,0.0,0.50,80.0,5.0,1.0,0\n",
            encoding="utf-8",
        )
    if not stops_csv.exists():
        stops_csv.write_text("id,x,y\n0,-0.5,0.0\n", encoding="utf-8")
    if not weather_csv.exists():
        weather_csv.write_text(
            "wind_speed,wind_direction,temperature,uncertainty,battery_capacity,vehicle_count,uav_count,vehicle_speed_kmph,drone_speed_kmph\n"
            "3.0,0.0,22.0,0.16,150.0,1,2,65.0,46.0\n",
            encoding="utf-8",
        )
    readme.write_text(_template_readme(), encoding="utf-8")
    return {
        "towers_csv": towers_csv,
        "stops_csv": stops_csv,
        "weather_csv": weather_csv,
        "readme": readme,
    }


def _read_csv(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _first_row(path: Path) -> dict:
    rows = _read_csv(path)
    if not rows:
        raise ValueError(f"{path} must contain one weather/config row")
    return rows[0]


def _template_readme() -> str:
    return """# GIS Case Input Schema

Use this folder when replacing the synthetic corridor case with a real or GIS-grounded transmission-line case.

Coordinates must be projected kilometer coordinates (`x`, `y`), not raw longitude/latitude. Convert GIS geometry to a local projected CRS first so that route and energy distances remain meaningful.

Required files:

- `towers.csv`: `id,x,y,risk,value,service_time,payload,segment`
- `stops.csv`: `id,x,y`
- `weather.csv`: `wind_speed,wind_direction,temperature,uncertainty,battery_capacity,vehicle_count,uav_count,vehicle_speed_kmph,drone_speed_kmph`

Evidence boundary: loading a GIS case does not by itself create field validation. Field-validation claims require real flight logs, inspection outcomes, or utility-provided operational records.
"""
