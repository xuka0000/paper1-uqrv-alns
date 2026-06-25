from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List

import matplotlib as mpl
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.scenario import generate_scenario


EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
MANUSCRIPT_FIGURES = PROJECT_ROOT / "results/figures/manuscript"
RUN_ID = "full_20260525"

PALETTE = {
    "pale_teal": "#BFDFD2",
    "teal": "#51999F",
    "blue_teal": "#4198AC",
    "light_cyan": "#7BC0CD",
    "muted_gold": "#DDCB92",
    "amber": "#ECB66C",
    "orange": "#EA9E58",
    "coral": "#ED8D5A",
    "dark": "#2F3E46",
    "gray": "#6E7C7C",
}

METHOD_LABELS = {
    "greedy_nearest": "Nearest",
    "greedy_value": "Value greedy",
    "random_feasible": "Random",
    "ga": "GA",
    "aco": "ACO",
    "alns_fixed": "Fixed ALNS",
    "alns_point": "Point energy ALNS",
    "uq_alns": "UQ-ALNS",
    "rv_alns": "RV-ALNS",
    "uq_rv_alns": "UQ-RV-ALNS",
}

METHOD_COLORS = {
    "greedy_nearest": PALETTE["gray"],
    "greedy_value": PALETTE["muted_gold"],
    "random_feasible": "#C9C9C9",
    "ga": PALETTE["amber"],
    "aco": PALETTE["orange"],
    "alns_fixed": PALETTE["light_cyan"],
    "alns_point": PALETTE["blue_teal"],
    "uq_alns": PALETTE["teal"],
    "rv_alns": PALETTE["muted_gold"],
    "uq_rv_alns": PALETTE["coral"],
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.75,
        "axes.labelsize": 7.5,
        "axes.titlesize": 8.5,
        "xtick.labelsize": 6.7,
        "ytick.labelsize": 6.7,
        "legend.fontsize": 6.7,
        "legend.frameon": False,
        "figure.dpi": 150,
    }
)


def main() -> int:
    MANUSCRIPT_FIGURES.mkdir(parents=True, exist_ok=True)
    made = [
        plot_workflow_schematic(),
        plot_energy_surrogate_interface(),
        plot_core_comparison(),
        plot_uncertainty_robustness(),
        plot_value_ablation(),
        plot_online_replanning(),
        plot_scalability(),
    ]
    make_contact_sheet([path.with_suffix(".png") for path in made])
    write_manifest(made)
    print(f"Generated {len(made)} figure stems in {MANUSCRIPT_FIGURES}")
    return 0


def plot_core_comparison() -> Path:
    df = read_summary("E2_core_comparison")
    keep = [
        "greedy_nearest",
        "ga",
        "aco",
        "alns_point",
        "uq_alns",
        "rv_alns",
        "uq_rv_alns",
    ]
    df = df[df["method"].isin(keep)].copy()
    df["label"] = df["method"].map(METHOD_LABELS)
    df = df.set_index("method").loc[keep].reset_index()

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55), constrained_layout=True)
    panels = [
        ("risk_weighted_completion_time_mean", "Risk-weighted\ncompletion time", False),
        ("top_risk_coverage_mean", "Top-risk\ncoverage", True),
        ("makespan_mean", "Makespan\n(min)", False),
    ]
    for ax, (metric, title, higher) in zip(axes, panels):
        colors = [METHOD_COLORS[m] for m in df["method"]]
        ax.barh(df["label"], df[metric], color=colors, edgecolor="white", linewidth=0.6)
        ax.set_title(title)
        ax.grid(axis="x", alpha=0.18, linewidth=0.5)
        if higher:
            ax.set_xlim(0, 1.0)
        best_idx = df[metric].idxmax() if higher else df[metric].idxmin()
        ax.patches[best_idx].set_edgecolor(PALETTE["dark"])
        ax.patches[best_idx].set_linewidth(1.0)
    add_panel_labels(axes)
    return save_figure(fig, "E2_core_comparison", "manuscript_Fig3_core_comparison", df)


def plot_energy_surrogate_interface() -> Path:
    scenario = generate_scenario(size="M", seed=0, uncertainty="high")
    energy = EnergyModel(battery_capacity=scenario.battery_capacity)
    rows = []
    for tower in scenario.towers:
        stop = min(scenario.stops, key=lambda s: (s.x - tower.x) ** 2 + (s.y - tower.y) ** 2)
        estimate = energy.estimate(stop, tower, scenario.weather)
        rows.append(
            {
                "tower": tower.id,
                "risk_value": tower.risk * tower.value,
                "mean_energy": estimate.mean_energy,
                "q95_energy": estimate.q95_energy,
                "duration": estimate.duration,
                "battery_limit": energy.battery_capacity * (1.0 - energy.reserve_ratio),
                "margin": energy.battery_capacity * (1.0 - energy.reserve_ratio) - estimate.q95_energy,
            }
        )
    df = pd.DataFrame(rows).sort_values("risk_value", ascending=False).head(24).reset_index(drop=True)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.65), constrained_layout=True)
    x = range(len(df))
    axes[0].plot(x, df["mean_energy"], color=PALETTE["teal"], marker="o", markersize=2.8, label="Mean")
    axes[0].plot(x, df["q95_energy"], color=PALETTE["coral"], marker="o", markersize=2.8, label="q95")
    axes[0].axhline(df["battery_limit"].iloc[0], color=PALETTE["dark"], linestyle="--", linewidth=0.9, label="Battery reserve limit")
    axes[0].fill_between(x, df["mean_energy"], df["q95_energy"], color=PALETTE["coral"], alpha=0.16)
    axes[0].set_title("Energy uncertainty passed to scheduling")
    axes[0].set_xlabel("High-value inspection tasks")
    axes[0].set_ylabel("Energy units")
    axes[0].legend(loc="upper right")
    colors = [PALETTE["coral"] if m < 0 else PALETTE["teal"] for m in df["margin"]]
    axes[1].bar(x, df["margin"], color=colors, edgecolor="white", linewidth=0.4)
    axes[1].axhline(0, color=PALETTE["dark"], linewidth=0.8)
    axes[1].set_title("Chance-constraint margin")
    axes[1].set_xlabel("High-value inspection tasks")
    axes[1].set_ylabel("q95 safety margin")
    for ax in axes:
        ax.grid(alpha=0.2, linewidth=0.5)
    add_panel_labels(axes)
    return save_figure(fig, "E3_uncertainty_robustness", "manuscript_Fig2_energy_uq_interface", df)


def plot_uncertainty_robustness() -> Path:
    df = read_summary("E3_uncertainty_robustness")
    methods = ["alns_point", "uq_alns", "uq_rv_alns"]
    order = ["low", "medium", "high"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    for method in methods:
        sub = df[df["method"].eq(method)].set_index("uncertainty").loc[order]
        label = METHOD_LABELS[method]
        color = METHOD_COLORS[method]
        axes[0].plot(order, sub["infeasible_sortie_rate_mean"], marker="o", label=label, color=color)
        axes[1].plot(order, sub["makespan_mean"], marker="o", label=label, color=color)
        axes[2].plot(order, sub["risk_weighted_completion_time_mean"], marker="o", label=label, color=color)
    axes[0].set_title("Violation rate")
    axes[1].set_title("Makespan")
    axes[2].set_title("Risk-weighted completion")
    for ax in axes:
        ax.grid(alpha=0.2, linewidth=0.5)
    axes[0].set_ylabel("Mean")
    axes[2].legend(loc="upper left", bbox_to_anchor=(1.02, 1.0))
    add_panel_labels(axes)
    return save_figure(fig, "E3_uncertainty_robustness", "manuscript_Fig4_uncertainty_robustness", df)


def plot_value_ablation() -> Path:
    df = read_summary("E4_value_ablation")
    methods = ["alns_point", "uq_alns", "rv_alns", "uq_rv_alns"]
    df = df[df["method"].isin(methods)].set_index("method").loc[methods].reset_index()
    labels = [METHOD_LABELS[m] for m in df["method"]]
    x = list(range(len(df)))
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.55), constrained_layout=True)
    axes[0].bar(x, df["top_risk_coverage_mean"], color=PALETTE["teal"], edgecolor="white", linewidth=0.6)
    axes[1].bar(x, df["risk_weighted_completion_time_mean"], color=PALETTE["coral"], edgecolor="white", linewidth=0.6)
    axes[0].set_title("Top-risk coverage")
    axes[1].set_title("Risk-weighted completion time")
    axes[0].set_ylim(0, 1.05)
    for ax in axes:
        ax.set_xticks(x, labels, rotation=20, ha="right")
        ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    axes[0].set_ylabel("Coverage")
    axes[1].set_ylabel("Risk-weighted time")
    add_panel_labels(axes)
    return save_figure(fig, "E4_value_ablation", "manuscript_Fig5_value_ablation", df)


def plot_online_replanning() -> Path:
    df = read_summary("E5_online_replanning")
    order = ["static", "periodic", "event_triggered"]
    colors = [PALETTE["gray"], PALETTE["muted_gold"], PALETTE["coral"]]
    df = df.set_index("policy").loc[order].reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    panels = [
        ("makespan_mean", "Disturbed makespan"),
        ("infeasible_sortie_rate_mean", "Violation rate"),
        ("online_response_time_mean", "Response time"),
    ]
    for ax, (metric, title) in zip(axes, panels):
        ax.bar(df["policy"], df[metric], color=colors, edgecolor="white", linewidth=0.6)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=18)
        ax.grid(axis="y", alpha=0.2, linewidth=0.5)
    add_panel_labels(axes)
    return save_figure(fig, "E5_online_replanning", "manuscript_Fig6_online_replanning", df)


def plot_scalability() -> Path:
    df = read_summary("E6_scalability")
    methods = ["alns_point", "uq_rv_alns"]
    sizes = ["S", "M", "L"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    for method in methods:
        sub = df[df["method"].eq(method)].set_index("size").loc[sizes]
        label = METHOD_LABELS[method]
        color = METHOD_COLORS[method]
        axes[0].plot(sizes, sub["makespan_mean"], marker="o", color=color, label=label)
        axes[1].plot(sizes, sub["solver_runtime_mean"], marker="o", color=color, label=label)
        axes[2].plot(sizes, sub["top_risk_coverage_mean"], marker="o", color=color, label=label)
    axes[0].set_title("Makespan")
    axes[1].set_title("Runtime")
    axes[2].set_title("Top-risk coverage")
    axes[1].set_yscale("log")
    for ax in axes:
        ax.grid(alpha=0.2, linewidth=0.5)
    axes[2].legend(loc="lower right")
    add_panel_labels(axes)
    return save_figure(fig, "E6_scalability", "manuscript_Fig7_scalability", df)


def plot_workflow_schematic() -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 2.65), constrained_layout=True)
    ax.axis("off")
    boxes = [
        (0.04, 0.58, "Corridor\nscenario"),
        (0.22, 0.58, "Probabilistic\nenergy model"),
        (0.42, 0.58, "Chance-constrained\nsortie filter"),
        (0.64, 0.58, "Risk-value\nALNS"),
        (0.84, 0.58, "Inspection\nplan"),
        (0.22, 0.16, "Wind, road,\nurgent events"),
        (0.54, 0.16, "Event-triggered\nreplanning"),
    ]
    for x, y, text in boxes:
        ax.add_patch(
            plt.Rectangle((x, y), 0.13, 0.22, facecolor=PALETTE["pale_teal"], edgecolor=PALETTE["teal"], linewidth=1.0)
        )
        ax.text(x + 0.065, y + 0.11, text, ha="center", va="center", fontsize=7.4)
    arrows = [
        ((0.17, 0.69), (0.22, 0.69)),
        ((0.35, 0.69), (0.42, 0.69)),
        ((0.55, 0.69), (0.64, 0.69)),
        ((0.77, 0.69), (0.84, 0.69)),
        ((0.35, 0.27), (0.54, 0.27)),
        ((0.61, 0.38), (0.68, 0.58)),
        ((0.90, 0.58), (0.61, 0.38)),
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 1.0, "color": PALETTE["dark"]})
    ax.text(0.04, 0.91, "UQ-RV-ALNS closed-loop inspection scheduling", fontsize=9, fontweight="bold")
    source = pd.DataFrame({"module": [b[2].replace("\n", " ") for b in boxes]})
    return save_figure(fig, "E0_smoke", "manuscript_Fig1_workflow", source)


def read_summary(experiment_id: str) -> pd.DataFrame:
    path = EXPERIMENTS / experiment_id / "analysis_data" / f"{experiment_id}_{RUN_ID}_summary.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def save_figure(fig: plt.Figure, experiment_id: str, stem: str, source: pd.DataFrame) -> Path:
    exp_fig = EXPERIMENTS / experiment_id / "figures"
    source_dir = exp_fig / "source_data"
    exp_fig.mkdir(parents=True, exist_ok=True)
    source_dir.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGURES.mkdir(parents=True, exist_ok=True)
    for directory in (exp_fig, MANUSCRIPT_FIGURES):
        fig.savefig(directory / f"{stem}.png", dpi=600, bbox_inches="tight")
        fig.savefig(directory / f"{stem}.svg", bbox_inches="tight")
        fig.savefig(directory / f"{stem}.pdf", bbox_inches="tight")
    source.to_csv(source_dir / f"{stem}_source.csv", index=False)
    source.to_csv(MANUSCRIPT_FIGURES / f"{stem}_source.csv", index=False)
    plt.close(fig)
    return MANUSCRIPT_FIGURES / stem


def add_panel_labels(axes: Iterable[plt.Axes]) -> None:
    for label, ax in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", axes):
        ax.text(-0.12, 1.08, label, transform=ax.transAxes, fontsize=9, fontweight="bold", va="top")


def make_contact_sheet(png_paths: List[Path]) -> None:
    thumbs = []
    for path in png_paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((520, 360))
        canvas = Image.new("RGB", (560, 420), "white")
        canvas.paste(img, ((560 - img.width) // 2, 20))
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 385), path.stem, fill=(20, 20, 20))
        thumbs.append(canvas)
    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 560, rows * 420), "white")
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 560, (i // cols) * 420))
    sheet.save(MANUSCRIPT_FIGURES / "manuscript_figures_contact_sheet.png")


def write_manifest(stems: List[Path]) -> None:
    lines = [
        "# Manuscript Figure Manifest",
        "",
        "Generated by `scripts/generate_manuscript_figures.py`.",
        "",
        "| Figure | PNG | SVG | PDF | Source data |",
        "| --- | --- | --- | --- | --- |",
    ]
    for stem in stems:
        name = stem.name
        lines.append(
            f"| `{name}` | `{name}.png` | `{name}.svg` | `{name}.pdf` | `{name}_source.csv` |"
        )
    lines.extend(["", "Contact sheet:", "", "- `manuscript_figures_contact_sheet.png`", ""])
    (MANUSCRIPT_FIGURES / "figure_manifest.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
