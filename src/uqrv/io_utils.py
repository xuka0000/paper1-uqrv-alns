from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, Iterable, List, Mapping


REQUIRED_EXPERIMENT_DIRS = ["raw_data", "analysis_data", "figures", "logs", "runs"]


def ensure_experiment_dirs(root: Path, experiment_id: str, run_id: str) -> Path:
    exp_root = Path(root) / experiment_id
    for name in REQUIRED_EXPERIMENT_DIRS:
        (exp_root / name).mkdir(parents=True, exist_ok=True)
    (exp_root / "runs" / run_id).mkdir(parents=True, exist_ok=True)
    return exp_root


def write_rows_csv(path: Path, rows: Iterable[Mapping[str, object]]) -> None:
    rows = list(rows)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = _ordered_fieldnames(rows)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_json(path: Path, data: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def write_markdown(path: Path, title: str, rows: List[Mapping[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text(f"# {title}\n\nNo rows.\n", encoding="utf-8")
        return
    headers = _ordered_fieldnames(rows)
    lines = [f"# {title}", "", "| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _ordered_fieldnames(rows: Iterable[Mapping[str, object]]) -> List[str]:
    fieldnames: List[str] = []
    seen = set()
    for row in rows:
        for key in row.keys():
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    return fieldnames


def summarize_rows(rows: List[Mapping[str, object]], group_keys: List[str], metric_keys: List[str]) -> List[Dict[str, object]]:
    grouped: Dict[tuple, List[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[tuple(row[key] for key in group_keys)].append(row)

    summary: List[Dict[str, object]] = []
    for key_values, group in sorted(grouped.items(), key=lambda item: item[0]):
        out: Dict[str, object] = {group_keys[i]: key_values[i] for i in range(len(group_keys))}
        out["n"] = len(group)
        for metric in metric_keys:
            values = [float(row[metric]) for row in group if metric in row and row[metric] != ""]
            if not values:
                continue
            out[f"{metric}_mean"] = round(mean(values), 6)
            out[f"{metric}_sd"] = round(stdev(values), 6) if len(values) > 1 else 0.0
        summary.append(out)
    return summary
