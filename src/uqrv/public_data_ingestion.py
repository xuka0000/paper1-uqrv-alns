from __future__ import annotations

import csv
import json
import math
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Dict, Iterable, List, Tuple


EARTH_RADIUS_KM = 6371.0088
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
HIFLD_URL = "https://services2.arcgis.com/LYMgRMwHfrWWEg3s/ArcGIS/rest/services/HIFLD_US_Electric_Power_Transmission_Lines/FeatureServer/0/query"
NASA_POWER_URL = "https://power.larc.nasa.gov/api/temporal/hourly/point"
USER_AGENT = "UQRVResearchAudit/1.0"


@dataclass(frozen=True)
class BBox:
    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    @property
    def center_lon(self) -> float:
        return (self.min_lon + self.max_lon) / 2.0

    @property
    def center_lat(self) -> float:
        return (self.min_lat + self.max_lat) / 2.0


@dataclass(frozen=True)
class PublicTowerNode:
    source_id: str
    lon: float
    lat: float
    tags: Dict[str, str]


def parse_bbox(value: str) -> BBox:
    parts = [float(part.strip()) for part in value.split(",")]
    if len(parts) != 4:
        raise ValueError("bbox must use min_lon,min_lat,max_lon,max_lat")
    bbox = BBox(parts[0], parts[1], parts[2], parts[3])
    if bbox.min_lon >= bbox.max_lon or bbox.min_lat >= bbox.max_lat:
        raise ValueError("bbox min values must be smaller than max values")
    return bbox


def project_lonlat_to_km(lon: float, lat: float, bbox: BBox) -> Tuple[float, float]:
    lon0 = math.radians(bbox.center_lon)
    lat0 = math.radians(bbox.center_lat)
    x = EARTH_RADIUS_KM * (math.radians(lon) - lon0) * math.cos(lat0)
    y = EARTH_RADIUS_KM * (math.radians(lat) - lat0)
    return round(x, 6), round(y, 6)


def fetch_osm_towers(bbox: BBox, timeout: int = 45) -> Tuple[List[PublicTowerNode], dict]:
    query = (
        f"[out:json][timeout:{int(timeout)}];"
        f'node["power"="tower"]({bbox.min_lat},{bbox.min_lon},{bbox.max_lat},{bbox.max_lon});'
        "out body;"
    )
    raw = _post_form_json(OVERPASS_URL, {"data": query}, timeout=timeout + 15)
    nodes = []
    for item in raw.get("elements", []):
        if item.get("type") != "node" or "lat" not in item or "lon" not in item:
            continue
        nodes.append(
            PublicTowerNode(
                source_id=str(item.get("id", "")),
                lon=float(item["lon"]),
                lat=float(item["lat"]),
                tags={str(k): str(v) for k, v in item.get("tags", {}).items()},
            )
        )
    return nodes, raw


def fetch_hifld_lines(bbox: BBox, timeout: int = 45, record_count: int = 50) -> dict:
    params = {
        "where": "1=1",
        "geometry": f"{bbox.min_lon},{bbox.min_lat},{bbox.max_lon},{bbox.max_lat}",
        "geometryType": "esriGeometryEnvelope",
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "ID,TYPE,STATUS,OWNER,VOLTAGE,VOLT_CLASS",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "json",
        "resultRecordCount": str(record_count),
    }
    url = HIFLD_URL + "?" + urllib.parse.urlencode(params)
    return _get_json(url, timeout=timeout)


def fetch_nasa_power_weather(bbox: BBox, date_yyyymmdd: str, timeout: int = 60) -> Tuple[dict, dict]:
    params = {
        "parameters": "T2M,WS10M,WD10M",
        "community": "RE",
        "longitude": f"{bbox.center_lon:.6f}",
        "latitude": f"{bbox.center_lat:.6f}",
        "start": date_yyyymmdd,
        "end": date_yyyymmdd,
        "format": "JSON",
        "time-standard": "UTC",
    }
    url = NASA_POWER_URL + "?" + urllib.parse.urlencode(params)
    raw = _get_json(url, timeout=timeout)
    params_raw = raw.get("properties", {}).get("parameter", {})
    temperatures = _valid_values(params_raw.get("T2M", {}))
    wind_speeds = _valid_values(params_raw.get("WS10M", {}))
    wind_directions = _valid_values(params_raw.get("WD10M", {}))
    if not temperatures or not wind_speeds or not wind_directions:
        raise ValueError("NASA POWER response did not contain usable T2M/WS10M/WD10M values")
    weather = {
        "wind_speed": round(mean(wind_speeds), 4),
        "wind_direction": round(_circular_mean_degrees(wind_directions), 4),
        "temperature": round(mean(temperatures), 4),
        "uncertainty": round(_weather_uncertainty(wind_speeds), 4),
    }
    return weather, raw


def build_gis_rows(
    nodes: Iterable[PublicTowerNode],
    bbox: BBox,
    tower_limit: int = 120,
    stop_count: int | None = None,
) -> Tuple[List[dict], List[dict]]:
    projected = []
    for node in nodes:
        x, y = project_lonlat_to_km(node.lon, node.lat, bbox)
        projected.append({"node": node, "x": x, "y": y})
    if not projected:
        raise ValueError("no tower nodes available for GIS case")

    projected.sort(key=lambda row: (row["x"], row["y"]))
    selected = _select_evenly(projected, max(1, min(tower_limit, len(projected))))
    tower_count = len(selected)
    segment_count = min(4, max(1, int(math.sqrt(tower_count) // 2 or 1)))
    towers = []
    for idx, row in enumerate(selected):
        segment = min(segment_count - 1, int(idx * segment_count / max(1, tower_count)))
        risk = _risk_proxy(row["node"], idx, tower_count)
        towers.append(
            {
                "id": idx,
                "x": row["x"],
                "y": row["y"],
                "risk": risk,
                "value": round(35.0 + 115.0 * risk + 12.0 * (segment == 0), 4),
                "service_time": round(3.5 + 4.0 * risk, 4),
                "payload": round(0.55 + 0.85 * _unit_noise(row["node"].source_id, "payload"), 4),
                "segment": segment,
            }
        )

    if stop_count is None:
        stop_count = max(4, min(tower_count, int(math.ceil(tower_count * 0.5))))
    stop_sources = _select_evenly(towers, max(1, min(stop_count, len(towers))))
    nx, ny = _normal_vector(towers)
    stops = []
    for idx, tower in enumerate(stop_sources):
        offset = 0.55 + 0.15 * ((idx % 3) - 1)
        stops.append(
            {
                "id": idx,
                "x": round(float(tower["x"]) + offset * nx, 6),
                "y": round(float(tower["y"]) + offset * ny, 6),
            }
        )
    return towers, stops


def write_public_gis_case(
    out_dir: str | Path,
    towers: List[dict],
    stops: List[dict],
    weather: dict,
    metadata: dict,
) -> Dict[str, Path]:
    out_dir = Path(out_dir)
    raw_dir = out_dir / "raw_sources"
    raw_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "towers_csv": out_dir / "towers.csv",
        "stops_csv": out_dir / "stops.csv",
        "weather_csv": out_dir / "weather.csv",
        "metadata_json": out_dir / "metadata.json",
    }
    _write_csv(paths["towers_csv"], towers, ["id", "x", "y", "risk", "value", "service_time", "payload", "segment"])
    _write_csv(paths["stops_csv"], stops, ["id", "x", "y"])
    weather_row = {
        "wind_speed": weather["wind_speed"],
        "wind_direction": weather["wind_direction"],
        "temperature": weather["temperature"],
        "uncertainty": weather["uncertainty"],
        "battery_capacity": metadata.get("battery_capacity", 150.0),
        "vehicle_count": metadata.get("vehicle_count", 2),
        "uav_count": metadata.get("uav_count", 4),
        "vehicle_speed_kmph": metadata.get("vehicle_speed_kmph", 65.0),
        "drone_speed_kmph": metadata.get("drone_speed_kmph", 46.0),
    }
    _write_csv(
        paths["weather_csv"],
        [weather_row],
        [
            "wind_speed",
            "wind_direction",
            "temperature",
            "uncertainty",
            "battery_capacity",
            "vehicle_count",
            "uav_count",
            "vehicle_speed_kmph",
            "drone_speed_kmph",
        ],
    )
    _write_json(paths["metadata_json"], metadata)
    return paths


def build_public_gis_case(
    bbox: BBox,
    out_dir: str | Path,
    date_yyyymmdd: str,
    tower_limit: int = 120,
    stop_count: int | None = None,
    vehicle_count: int = 2,
    uav_count: int = 4,
) -> Dict[str, Path]:
    out_dir = Path(out_dir)
    raw_dir = out_dir / "raw_sources"
    raw_dir.mkdir(parents=True, exist_ok=True)

    osm_nodes, osm_raw = fetch_osm_towers(bbox)
    if not osm_nodes:
        raise ValueError("OSM returned no power=tower nodes in the requested bbox")
    hifld_raw = _safe_fetch_hifld(bbox)
    weather, nasa_raw = fetch_nasa_power_weather(bbox, date_yyyymmdd)
    towers, stops = build_gis_rows(osm_nodes, bbox, tower_limit=tower_limit, stop_count=stop_count)

    _write_json(raw_dir / "osm_towers_raw.json", osm_raw)
    _write_json(raw_dir / "nasa_power_raw.json", nasa_raw)
    if hifld_raw is not None:
        _write_json(raw_dir / "hifld_lines_raw.json", hifld_raw)

    metadata = {
        "bbox": {
            "min_lon": bbox.min_lon,
            "min_lat": bbox.min_lat,
            "max_lon": bbox.max_lon,
            "max_lat": bbox.max_lat,
        },
        "date_yyyymmdd": date_yyyymmdd,
        "source_counts": {
            "osm_tower_nodes": len(osm_nodes),
            "used_towers": len(towers),
            "generated_stops": len(stops),
            "hifld_features": len((hifld_raw or {}).get("features", [])),
        },
        "sources": {
            "osm_overpass": OVERPASS_URL,
            "hifld_arcgis": HIFLD_URL,
            "nasa_power": NASA_POWER_URL,
        },
        "battery_capacity": 150.0,
        "vehicle_count": vehicle_count,
        "uav_count": uav_count,
        "vehicle_speed_kmph": 65.0,
        "drone_speed_kmph": 46.0,
        "evidence_boundary": (
            "Tower coordinates and weather are public-data grounded. "
            "Risk, value, service time, payload and generated stops are transparent proxies, not field labels."
        ),
    }
    return write_public_gis_case(out_dir, towers, stops, weather, metadata)


def _get_json(url: str, timeout: int = 60) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_form_json(url: str, form: dict, timeout: int = 60) -> dict:
    body = urllib.parse.urlencode(form).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _safe_fetch_hifld(bbox: BBox) -> dict | None:
    try:
        return fetch_hifld_lines(bbox)
    except Exception as exc:  # pragma: no cover - best-effort public source cache
        return {"features": [], "error": str(exc)}


def _write_csv(path: Path, rows: List[dict], fieldnames: List[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def _write_json(path: Path, payload: dict) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)


def _valid_values(raw: dict) -> List[float]:
    values = []
    for value in raw.values():
        number = float(value)
        if number > -900.0:
            values.append(number)
    return values


def _circular_mean_degrees(values: List[float]) -> float:
    sin_mean = mean([math.sin(math.radians(value)) for value in values])
    cos_mean = mean([math.cos(math.radians(value)) for value in values])
    return (math.degrees(math.atan2(sin_mean, cos_mean)) + 360.0) % 360.0


def _weather_uncertainty(wind_speeds: List[float]) -> float:
    if not wind_speeds:
        return 0.16
    spread = pstdev(wind_speeds) / max(0.5, mean(wind_speeds))
    return max(0.08, min(0.30, 0.10 + 0.18 * spread))


def _select_evenly(rows: List[dict], count: int) -> List[dict]:
    if count >= len(rows):
        return list(rows)
    if count <= 1:
        return [rows[0]]
    selected = []
    for idx in range(count):
        source_idx = round(idx * (len(rows) - 1) / (count - 1))
        selected.append(rows[source_idx])
    return selected


def _normal_vector(towers: List[dict]) -> Tuple[float, float]:
    if len(towers) < 2:
        return 0.0, 1.0
    dx = float(towers[-1]["x"]) - float(towers[0]["x"])
    dy = float(towers[-1]["y"]) - float(towers[0]["y"])
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return 0.0, 1.0
    return -dy / length, dx / length


def _risk_proxy(node: PublicTowerNode, index: int, total: int) -> float:
    position = index / max(1, total - 1)
    spatial = 0.25 + 0.25 * math.sin(math.pi * position)
    tag_bias = 0.08 if node.tags.get("tower:type") or node.tags.get("design") else 0.0
    noise = 0.35 * _unit_noise(node.source_id, f"{node.lon:.5f}", f"{node.lat:.5f}")
    return round(max(0.05, min(0.95, spatial + tag_bias + noise)), 4)


def _unit_noise(*values: object) -> float:
    text = "|".join(str(value) for value in values)
    acc = 0
    for char in text:
        acc = (acc * 131 + ord(char)) % 1000003
    raw = math.sin(acc * 12.9898) * 43758.5453
    return raw - math.floor(raw)
