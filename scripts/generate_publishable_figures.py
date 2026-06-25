from __future__ import annotations

import shutil
import sys
from math import hypot, log10
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.proposal_design import PROPOSAL_SIZE_CONFIGS, ProposalSizeConfig, generate_custom_scenario
from uqrv.solvers import solve


RUN_ID = "multi_tower_repair2_full_20260612"
EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
OUT = PROJECT_ROOT / "results/figures/publishable"
AI_FIGURES = PROJECT_ROOT / "results/figures/ai"

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
    "ga": "GA",
    "aco": "ACO",
    "alns_fixed": "Fixed ALNS",
    "alns_pinn": "Point energy ALNS",
    "alns_pinn_uq": "UQ energy ALNS",
    "alns_pinn_full": "Proposed",
    "milp_highs": "MILP-HiGHS",
    "no_pinn": "No surrogate",
    "no_adaptive": "No adaptive",
    "no_uq": "No UQ",
    "no_risk_value": "No risk-value",
    "no_energy_repair": "No energy repair",
    "no_sync_repair": "No sync repair",
    "no_clustering": "No clustering",
    "fixed_physics": "Fixed physics",
    "point_pinn": "Point residual",
    "probabilistic_pinn": "Sim-trained residual",
}

COLORS = {
    "greedy_nearest": PALETTE["gray"],
    "ga": PALETTE["amber"],
    "aco": PALETTE["orange"],
    "alns_fixed": PALETTE["light_cyan"],
    "alns_pinn": PALETTE["blue_teal"],
    "alns_pinn_uq": PALETTE["teal"],
    "alns_pinn_full": PALETTE["coral"],
    "milp_highs": PALETTE["muted_gold"],
    "fixed_physics": PALETTE["gray"],
    "point_pinn": PALETTE["blue_teal"],
    "probabilistic_pinn": PALETTE["coral"],
    "no_energy_repair": PALETTE["muted_gold"],
    "no_sync_repair": PALETTE["amber"],
    "no_clustering": PALETTE["gray"],
    "no_pinn": PALETTE["light_cyan"],
    "no_adaptive": PALETTE["blue_teal"],
    "no_uq": PALETTE["teal"],
    "no_risk_value": PALETTE["orange"],
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
        "axes.linewidth": 0.7,
        "axes.labelsize": 7.5,
        "axes.titlesize": 8.2,
        "xtick.labelsize": 6.5,
        "ytick.labelsize": 6.5,
        "legend.fontsize": 6.4,
        "legend.frameon": False,
        "figure.dpi": 180,
    }
)


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    made = [builder() for builder in PUBLISHABLE_FIGURE_BUILDERS]
    contact_sheet([p.with_suffix(".png") for p in made])
    manifest(made)
    print(f"Generated {len(made)} publishable figure stems in {OUT}")
    return 0


def copy_ai_figure(stem: str) -> Path:
    """Copy an image-model-drawn non-data manuscript figure into the release folder."""
    source = AI_FIGURES / f"{stem}.png"
    if not source.exists():
        raise FileNotFoundError(f"Missing image-model figure asset: {source}")
    target = OUT / f"{stem}.png"
    shutil.copy2(source, target)
    return OUT / stem


def fig0_network_construction_ai() -> Path:
    return copy_ai_figure("Fig0_network_construction_ai")


def fig1_framework_ai() -> Path:
    return copy_ai_figure("Fig1_framework_ai")


def fig3_operator_mechanism_ai() -> Path:
    return copy_ai_figure("Fig3_operator_mechanism_ai")


def fig0_network_construction() -> Path:
    scenario = generate_custom_scenario(
        ProposalSizeConfig("M", 30, 15, 2, 2, "network construction example"),
        seed=0,
        uncertainty="medium",
    )
    energy_model = EnergyModel(
        battery_capacity=scenario.battery_capacity,
        drone_speed_kmph=scenario.drone_speed_kmph,
    )
    plan = solve(scenario, "uq_rv_alns", energy_model, iterations=80, seed=0)
    towers = {tower.id: tower for tower in scenario.towers}
    stops = {stop.id: stop for stop in scenario.stops}
    corridor_count = 3
    road_edges = []
    for segment in range(corridor_count):
        segment_stops = sorted(
            [stop for stop in scenario.stops if stop.id % corridor_count == segment],
            key=lambda stop: stop.x,
        )
        road_edges.extend(zip(segment_stops, segment_stops[1:]))

    service_edges = []
    for tower in scenario.towers:
        stop = min(scenario.stops, key=lambda candidate: hypot(candidate.x - tower.x, candidate.y - tower.y))
        service_edges.append((stop, tower))

    multi_sorties = [sortie for sortie in plan.sorties if len(sortie.tower_ids) > 1]
    ranked_sorties = sorted(
        plan.sorties,
        key=lambda sortie: (
            len(sortie.tower_ids) > 1,
            max(towers[tower_id].risk * towers[tower_id].value for tower_id in sortie.tower_ids),
        ),
        reverse=True,
    )
    selected_sorties = []
    for sortie in multi_sorties + ranked_sorties:
        if sortie.sortie_id in {item.sortie_id for item in selected_sorties}:
            continue
        selected_sorties.append(sortie)
        if len(selected_sorties) >= 7:
            break

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.2, 3.05),
        constrained_layout=False,
        gridspec_kw={"width_ratios": [1.03, 0.97]},
    )

    rows = []
    for tower in scenario.towers:
        rows.append({"element": "tower", "id": tower.id, "x": tower.x, "y": tower.y, "risk": tower.risk, "value": tower.value})
    for stop in scenario.stops:
        rows.append({"element": "stop", "id": stop.id, "x": stop.x, "y": stop.y, "risk": "", "value": ""})

    for ax in axes:
        for left, right in road_edges:
            ax.plot([left.x, right.x], [left.y, right.y], color="#9AA6A6", lw=0.85, alpha=0.65, zorder=1)
            rows.append({"element": "road_arc", "id": f"{left.id}-{right.id}", "x": left.x, "y": left.y, "target_x": right.x, "target_y": right.y})
        ax.scatter(
            [tower.x for tower in scenario.towers],
            [tower.y for tower in scenario.towers],
            c=[tower.risk for tower in scenario.towers],
            cmap="YlOrRd",
            s=28,
            edgecolor="white",
            linewidth=0.45,
            zorder=4,
        )
        ax.scatter(
            [stop.x for stop in scenario.stops],
            [stop.y for stop in scenario.stops],
            marker="s",
            s=34,
            color=PALETTE["blue_teal"],
            edgecolor="white",
            linewidth=0.55,
            zorder=5,
        )
        ax.set_aspect("equal", adjustable="box")
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)

    axes[0].set_title("A  Candidate inspection graph", loc="left", weight="bold")
    for stop, tower in service_edges:
        axes[0].plot(
            [stop.x, tower.x],
            [stop.y, tower.y],
            color="#B8C4C4",
            lw=0.55,
            ls=(0, (2, 2)),
            alpha=0.65,
            zorder=2,
        )
        rows.append({"element": "candidate_service_edge", "id": f"S{stop.id}-T{tower.id}", "x": stop.x, "y": stop.y, "target_x": tower.x, "target_y": tower.y})
    axes[0].text(
        0.02,
        0.02,
        r"$G=(\mathcal{P}\cup\mathcal{T},\mathcal{A}^{road}\cup\mathcal{K}^{UAV})$",
        transform=axes[0].transAxes,
        fontsize=7.2,
        color=PALETTE["dark"],
    )

    axes[1].set_title("B  Same-stop UAV sortie patterns", loc="left", weight="bold")
    sortie_colors = [PALETTE["coral"], PALETTE["teal"], PALETTE["orange"], PALETTE["amber"], PALETTE["blue_teal"], "#8E6BBE", "#5F7F62"]
    for idx, sortie in enumerate(selected_sorties):
        stop = stops[sortie.stop_id]
        route = [(stop.x, stop.y)] + [(towers[tower_id].x, towers[tower_id].y) for tower_id in sortie.tower_ids] + [(stop.x, stop.y)]
        xs, ys = zip(*route)
        is_multi = len(sortie.tower_ids) > 1
        axes[1].plot(
            xs,
            ys,
            color=sortie_colors[idx % len(sortie_colors)],
            lw=1.45 if is_multi else 1.05,
            alpha=0.95,
            zorder=6,
        )
        axes[1].scatter([stop.x], [stop.y], marker="s", s=58, facecolor="none", edgecolor=sortie_colors[idx % len(sortie_colors)], linewidth=1.2, zorder=7)
        for left, right in zip(route, route[1:]):
            rows.append(
                {
                    "element": "selected_sortie_leg",
                    "id": f"K{sortie.sortie_id}",
                    "x": left[0],
                    "y": left[1],
                    "target_x": right[0],
                    "target_y": right[1],
                    "tower_ids": " ".join(str(tower_id) for tower_id in sortie.tower_ids),
                    "stop_id": sortie.stop_id,
                    "q95_energy": sortie.energy_q95,
                    "feasible": sortie.feasible,
                }
            )

    if multi_sorties:
        sortie = multi_sorties[0]
        stop = stops[sortie.stop_id]
        midpoint = towers[sortie.tower_ids[-1]]
        axes[1].annotate(
            "multi-tower\nsame-stop sortie",
            xy=(midpoint.x, midpoint.y),
            xytext=(stop.x + 2.2, stop.y + 2.4),
            fontsize=6.7,
            color=PALETTE["dark"],
            arrowprops={"arrowstyle": "->", "lw": 0.7, "color": PALETTE["dark"]},
            zorder=9,
        )

    legend_items = [
        Line2D([0], [0], marker="s", color="none", label="Vehicle stop", markerfacecolor=PALETTE["blue_teal"], markeredgecolor="white", markersize=6),
        Line2D([0], [0], marker="o", color="none", label="Inspection tower", markerfacecolor=PALETTE["coral"], markeredgecolor="white", markersize=6),
        Line2D([0], [0], color="#9AA6A6", lw=1.0, label="Road arc"),
        Line2D([0], [0], color="#B8C4C4", lw=1.0, ls=(0, (2, 2)), label="Feasible support edge"),
        Line2D([0], [0], color=PALETTE["coral"], lw=1.4, label="Same-stop sortie"),
    ]
    fig.legend(
        handles=legend_items,
        loc="lower center",
        bbox_to_anchor=(0.5, 0.02),
        ncol=5,
        handlelength=1.7,
        columnspacing=1.15,
    )
    fig.tight_layout(rect=(0, 0.13, 1, 1))
    return save(fig, "Fig0_network_construction", pd.DataFrame(rows))


def fig1_framework() -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 3.0), constrained_layout=True)
    ax.axis("off")
    boxes = [
        (0.03, 0.62, "Transmission\ncorridor"),
        (0.19, 0.62, "K-means / DBSCAN\npartition"),
        (0.39, 0.62, "Energy surrogate\nand endurance update"),
        (0.62, 0.62, "Compact MILP\nsmall-scale reference"),
        (0.81, 0.62, "UQ-RV-ALNS\nlarge-scale schedule"),
        (0.39, 0.22, "Physical energy\nresidual"),
        (0.62, 0.22, "Destroy / repair\noperator adaptation"),
        (0.81, 0.22, "Risk-value and\nUQ feasibility"),
    ]
    for x, y, label in boxes:
        ax.add_patch(plt.Rectangle((x, y), 0.145, 0.20, facecolor=PALETTE["pale_teal"], edgecolor=PALETTE["teal"], lw=1.0))
        ax.text(x + 0.0725, y + 0.10, label, ha="center", va="center", fontsize=7.1)
    arrows = [
        ((0.175, 0.72), (0.19, 0.72)),
        ((0.335, 0.72), (0.39, 0.72)),
        ((0.535, 0.72), (0.62, 0.72)),
        ((0.765, 0.72), (0.81, 0.72)),
        ((0.46, 0.62), (0.46, 0.42)),
        ((0.535, 0.32), (0.62, 0.32)),
        ((0.765, 0.32), (0.81, 0.32)),
        ((0.88, 0.42), (0.88, 0.62)),
    ]
    for start, end in arrows:
        ax.annotate("", xy=end, xytext=start, arrowprops={"arrowstyle": "->", "lw": 0.9, "color": PALETTE["dark"]})
    ax.text(0.03, 0.92, "MILP, energy surrogate and ALNS workflow", fontsize=9, weight="bold")
    return save(fig, "Fig1_framework", pd.DataFrame({"module": [b[2].replace("\n", " ") for b in boxes]}))


def fig2_instances() -> Path:
    configs = [c for group in ["S", "M", "L"] for c in PROPOSAL_SIZE_CONFIGS[group]]
    df = pd.DataFrame([c.__dict__ for c in configs])
    case = generate_custom_scenario(ProposalSizeConfig("CASE", 200, 100, 4, 3, "case study"), 0, "high")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    x = range(len(df))
    axes[0].bar(x, df["tower_count"], color=PALETTE["teal"], label="Towers")
    axes[0].bar(x, df["stop_count"], color=PALETTE["muted_gold"], label="Stops")
    axes[0].set_xticks(x, [f"{r.size}{r.tower_count}" for r in df.itertuples()], rotation=45, ha="right")
    axes[0].set_title("Proposal instance scale")
    axes[0].legend()
    axes[1].scatter([t.x for t in case.towers], [t.y for t in case.towers], c=[t.risk for t in case.towers], s=8, cmap="YlOrRd", alpha=0.85)
    axes[1].scatter([s.x for s in case.stops], [s.y for s in case.stops], marker="s", s=14, color=PALETTE["blue_teal"], alpha=0.75)
    axes[1].set_title("Realistic case corridor")
    axes[1].set_xticks([])
    axes[1].set_yticks([])
    count_df = pd.DataFrame(
        {
            "block": ["MILP", "Comparison", "Energy", "Ablation", "Case", "Stops", "Stats"],
            "rows": [90, 560, 90, 80, 15, 120, 192],
        }
    )
    axes[2].bar(count_df["block"], count_df["rows"], color=[PALETTE["muted_gold"], PALETTE["teal"], PALETTE["blue_teal"], PALETTE["orange"], PALETTE["coral"]])
    axes[2].tick_params(axis="x", rotation=30)
    axes[2].set_title("Executed evidence blocks")
    axes[2].set_ylabel("Raw rows")
    for ax in axes:
        ax.grid(alpha=0.18, lw=0.5)
    label_panels(axes)
    return save(fig, "Fig2_instances", df)


def fig3_operator_mechanism() -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 2.95))
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")
    rows = []

    def add_box(title: str, body: str, x: float, y: float, w: float, h: float, color: str) -> None:
        box = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.018",
            linewidth=0.8,
            edgecolor="#51646A",
            facecolor=color,
            alpha=1.0,
            zorder=3,
        )
        ax.add_patch(box)
        ax.text(x + 0.012, y + h - 0.045, title, fontsize=7.4, weight="bold", color=PALETTE["dark"], va="top", zorder=4)
        ax.text(x + 0.012, y + h - 0.105, body, fontsize=6.6, color=PALETTE["dark"], va="top", linespacing=1.25, zorder=4)
        rows.append({"element": "box", "title": title, "body": body, "x": x, "y": y, "width": w, "height": h})

    for item in [
        ("Current schedule", "Stop A: K1, K2\nStop B: K3\nStop C: K4", 0.04, 0.56, 0.17, 0.28, PALETTE["pale_teal"]),
        ("Destroy operator", "Remove high-energy\nor related tower chain", 0.29, 0.56, 0.18, 0.28, "#F3D0BC"),
        ("Candidate list", "Unserved towers\nranked by risk value", 0.54, 0.56, 0.17, 0.28, "#E7D59A"),
        ("Repair operator", "Greedy, regret-k,\nenergy-minimum,\nsync-aware insertion", 0.78, 0.54, 0.18, 0.32, "#C5DDE3"),
    ]:
        add_box(*item)

    for start, end, label in [
        ((0.215, 0.70), (0.285, 0.70), "select destroy"),
        ((0.475, 0.70), (0.535, 0.70), "removed tasks"),
        ((0.715, 0.70), (0.775, 0.70), "insert"),
    ]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10, lw=1.0, color=PALETTE["dark"], zorder=2))
        ax.text(
            (start[0] + end[0]) / 2,
            start[1] + 0.055,
            label,
            fontsize=6.4,
            ha="center",
            color=PALETTE["gray"],
            bbox={"facecolor": "white", "edgecolor": "none", "pad": 0.3},
            zorder=5,
        )
        rows.append({"element": "arrow", "label": label, "x": start[0], "y": start[1], "target_x": end[0], "target_y": end[1]})

    add_box(
        "Acceptance and scoring",
        "Evaluate q95 feasibility, RWCT and makespan\nAccept or reject candidate; update weights",
        0.19,
        0.12,
        0.62,
        0.22,
        "#F2F4F4",
    )
    for start, end, label in [
        ((0.87, 0.54), (0.72, 0.34), "score candidate"),
        ((0.28, 0.34), (0.13, 0.56), "next incumbent"),
    ]:
        ax.add_patch(FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=10, lw=1.0, color=PALETTE["dark"], zorder=2))
        rows.append({"element": "feedback_arrow", "label": label, "x": start[0], "y": start[1], "target_x": end[0], "target_y": end[1]})

    ax.text(0.5, 0.94, "Adaptive destroy--repair operator loop", fontsize=9, weight="bold", ha="center", color=PALETTE["dark"], zorder=5)
    ax.text(
        0.5,
        0.045,
        "Operator selection is adaptive. Final portfolio selection uses infeasible-sortie count, RWCT and makespan.",
        fontsize=6.7,
        ha="center",
        color=PALETTE["gray"],
        zorder=5,
    )
    return save(fig, "Fig3_operator_mechanism", pd.DataFrame(rows))


def fig3_milp_validation() -> Path:
    df = read("P1_milp_exact_small")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    methods = ["milp_highs", "alns_pinn", "alns_pinn_full"]
    for method in methods:
        sub = df[df.method.eq(method)].sort_values("tower_count")
        axes[0].plot(sub["tower_count"], sub["makespan_mean"], marker="o", label=METHOD_LABELS[method], color=COLORS[method])
        axes[2].plot(sub["tower_count"], sub["solver_runtime_mean"], marker="o", label=METHOD_LABELS[method], color=COLORS[method])
    gap = df[df.method.isin(["alns_pinn", "alns_pinn_full"])].copy()
    width = 0.35
    xs = sorted(gap["tower_count"].unique())
    for offset, method in [(-width / 2, "alns_pinn"), (width / 2, "alns_pinn_full")]:
        sub = gap[gap.method.eq(method)].set_index("tower_count").loc[xs]
        axes[1].bar([i + offset for i in range(len(xs))], sub["optimality_gap_pct_mean"], width=width, color=COLORS[method], label=METHOD_LABELS[method])
    axes[1].set_xticks(range(len(xs)), xs)
    axes[0].set_title("Small-scale makespan")
    axes[1].set_title("Gap to MILP reference")
    axes[2].set_title("Solver runtime")
    axes[2].set_yscale("log")
    axes[0].set_ylabel("min")
    axes[1].set_ylabel("%")
    axes[2].set_ylabel("s")
    axes[0].legend()
    for ax in axes:
        ax.grid(alpha=0.18, lw=0.5)
    label_panels(axes)
    return save(fig, "Fig3_milp_validation", df)


def fig4_algorithm_comparison() -> Path:
    df = read("P2_algorithm_comparison")
    df = df[df.tower_count.eq(100)].copy()
    order = ["greedy_nearest", "ga", "aco", "alns_fixed", "alns_pinn", "alns_pinn_uq", "alns_pinn_full"]
    df = df.set_index("method").loc[order].reset_index()
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.35), constrained_layout=True)
    panels = [
        ("makespan_mean", "Makespan", False),
        ("risk_weighted_completion_time_mean", "Risk-weighted time", False),
        ("top_risk_coverage_mean", "Top-risk coverage", True),
        ("infeasible_sortie_rate_mean", "Infeasible sorties", False),
    ]
    for ax, (metric, title, higher) in zip(axes, panels):
        colors = [COLORS.get(m, PALETTE["gray"]) for m in df.method]
        ax.barh([METHOD_LABELS[m] for m in df.method], df[metric], color=colors, edgecolor="white", lw=0.5)
        ax.set_title(title)
        if higher:
            ax.set_xlim(0, 1.0)
        best = df[metric].idxmax() if higher else df[metric].idxmin()
        ax.patches[best].set_edgecolor(PALETTE["dark"])
        ax.patches[best].set_linewidth(1.0)
        ax.grid(axis="x", alpha=0.18, lw=0.5)
    label_panels(axes)
    return save(fig, "Fig4_algorithm_comparison", df)


def fig5_energy_surrogate_accuracy() -> Path:
    df = read("P3_pinn_prediction_accuracy")
    models = ["fixed_physics", "point_pinn", "probabilistic_pinn"]
    unc = ["low", "medium", "high"]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    for model in models:
        sub = df[df.prediction_model.eq(model)].set_index("uncertainty").loc[unc]
        axes[0].plot(unc, sub["mae_mean"], marker="o", color=COLORS[model], label=METHOD_LABELS[model])
        axes[1].plot(unc, sub["coverage_95_mean"], marker="o", color=COLORS[model])
        axes[2].plot(unc, sub["false_feasible_rate_mean"], marker="o", color=COLORS[model])
    axes[0].set_title("Energy MAE")
    axes[1].set_title("95% coverage")
    axes[2].set_title("False feasible rate")
    axes[1].axhline(0.95, color=PALETTE["dark"], ls="--", lw=0.8)
    axes[0].legend()
    for ax in axes:
        ax.grid(alpha=0.18, lw=0.5)
    label_panels(axes)
    return save(fig, "Fig5_energy_surrogate_accuracy", df)


def fig6_ablation() -> Path:
    df = read("P4_ablation")
    order = [
        "no_pinn",
        "no_adaptive",
        "no_uq",
        "no_risk_value",
        "no_energy_repair",
        "no_sync_repair",
        "no_clustering",
        "alns_pinn_full",
    ]
    df = df.set_index("method").loc[order].reset_index()
    labels = [METHOD_LABELS[m] for m in df.method]
    colors = [COLORS[m] for m in df.method]
    y = range(len(df))
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    for ax, metric, title in [
        (axes[0], "risk_weighted_completion_time_mean", "Risk-weighted time"),
        (axes[1], "top_risk_coverage_mean", "Top-risk coverage"),
        (axes[2], "alns_improving_moves_mean", "Improving ALNS moves"),
    ]:
        ax.barh(y, df[metric], color=colors, edgecolor="white", lw=0.5)
        ax.set_title(title)
        ax.invert_yaxis()
        ax.grid(axis="x", alpha=0.18, lw=0.5)
        proposed_idx = order.index("alns_pinn_full")
        ax.patches[proposed_idx].set_edgecolor(PALETTE["dark"])
        ax.patches[proposed_idx].set_linewidth(1.0)
    axes[0].set_yticks(list(y), labels)
    for ax in axes[1:]:
        ax.set_yticks(list(y), [])
    axes[1].set_xlim(0, 1.0)
    label_panels(axes)
    return save(fig, "Fig6_ablation", df)


def fig7_case_study() -> Path:
    df = read("P5_case_study")
    order = ["alns_fixed", "alns_pinn", "alns_pinn_full"]
    df = df.set_index("method").loc[order].reset_index()
    labels = [METHOD_LABELS[m] for m in df.method]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)
    panels = [
        ("makespan_mean", "Case makespan"),
        ("risk_weighted_completion_time_mean", "Risk-weighted time"),
        ("top_risk_coverage_mean", "Top-risk coverage"),
    ]
    colors = [COLORS[m] for m in df.method]
    for ax, (metric, title) in zip(axes, panels):
        ax.bar(labels, df[metric], color=colors, edgecolor="white", lw=0.5)
        ax.set_title(title)
        ax.tick_params(axis="x", rotation=22)
        ax.grid(axis="y", alpha=0.18, lw=0.5)
    axes[2].set_ylim(0, 1.0)
    label_panels(axes)
    return save(fig, "Fig7_case_study", df)


def fig8_scalability() -> Path:
    df = read("P2_algorithm_comparison")
    df = df[df.method.isin(["alns_pinn", "alns_pinn_full"])].copy()
    sizes = [30, 50, 75, 100, 150, 200, 300, 500]
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.35), constrained_layout=True)
    for method in ["alns_pinn", "alns_pinn_full"]:
        sub = df[df.method.eq(method)].set_index("tower_count").loc[sizes]
        label = METHOD_LABELS[method]
        color = COLORS[method]
        axes[0].plot(sizes, sub["makespan_mean"], marker="o", color=color, label=label)
        axes[1].plot(sizes, sub["risk_weighted_completion_time_mean"], marker="o", color=color)
        axes[2].plot(sizes, sub["top_risk_coverage_mean"], marker="o", color=color)
        axes[3].plot(sizes, sub["solver_runtime_mean"], marker="o", color=color)
    axes[0].set_title("Makespan")
    axes[1].set_title("Risk-weighted time")
    axes[2].set_title("Top-risk coverage")
    axes[3].set_title("Runtime")
    axes[3].set_yscale("log")
    axes[0].legend()
    for ax in axes:
        ax.set_xlabel("Towers")
        ax.grid(alpha=0.18, lw=0.5)
    axes[2].set_ylim(0.75, 1.0)
    label_panels(axes)
    return save(fig, "Fig8_scalability", df)


def fig9_candidate_screening_statistics() -> Path:
    p6 = read("P6_candidate_stop_screening")
    p7 = read("P7_statistical_tests")
    fig, axes = plt.subplots(1, 4, figsize=(7.2, 2.35), constrained_layout=True)
    mode_colors = {
        "direct": PALETTE["gray"],
        "kmeans": PALETTE["teal"],
        "dbscan": PALETTE["orange"],
    }
    for mode in ["direct", "kmeans", "dbscan"]:
        sub = p6[p6.candidate_mode.eq(mode)].sort_values("tower_count")
        axes[0].plot(
            sub["tower_count"],
            100 * sub["candidate_pair_reduction_mean"],
            marker="o",
            color=mode_colors[mode],
            label=mode.upper() if mode == "dbscan" else mode.capitalize(),
        )
        axes[1].plot(
            sub["tower_count"],
            sub["makespan_mean"],
            marker="o",
            color=mode_colors[mode],
        )
    risk = p7[
        p7.metric.eq("risk_weighted_completion_time")
        & p7.baseline_method.isin(["ga", "alns_pinn", "alns_fixed"])
    ].copy()
    for baseline, color in [("alns_pinn", PALETTE["blue_teal"]), ("ga", PALETTE["amber"]), ("alns_fixed", PALETTE["gray"])]:
        sub = risk[risk.baseline_method.eq(baseline)].sort_values("tower_count")
        axes[2].plot(sub["tower_count"], sub["effect_pct"], marker="o", color=color, label=METHOD_LABELS[baseline])
    stat500 = risk[risk.tower_count.eq(500)].copy()
    stat500["neg_log10_p"] = stat500["p_holm"].apply(lambda value: -log10(max(float(value), 1e-12)))
    stat500 = stat500.set_index("baseline_method").loc[["alns_fixed", "ga", "alns_pinn"]].reset_index()
    axes[3].bar(
        [METHOD_LABELS[m] for m in stat500.baseline_method],
        stat500["neg_log10_p"],
        color=[PALETTE["gray"], PALETTE["amber"], PALETTE["blue_teal"]],
        edgecolor="white",
        lw=0.5,
    )
    axes[3].axhline(-log10(0.05), color=PALETTE["dark"], ls="--", lw=0.8)
    axes[0].set_title("Pair screening")
    axes[1].set_title("Stop-mode makespan")
    axes[2].set_title("Risk-time gain")
    axes[3].set_title("Holm evidence at 500")
    axes[0].set_ylabel("Reduction (%)")
    axes[1].set_ylabel("min")
    axes[2].set_ylabel("Gain (%)")
    axes[3].set_ylabel(r"$-\log_{10}(p_{Holm})$")
    axes[0].legend()
    axes[2].legend()
    axes[3].tick_params(axis="x", rotation=25)
    for ax in axes:
        ax.grid(alpha=0.18, lw=0.5)
        if ax is not axes[3]:
            ax.set_xlabel("Towers")
    label_panels(axes)
    source = pd.concat({"P6": p6, "P7": p7}, names=["source"]).reset_index()
    return save(fig, "Fig9_candidate_screening_statistics", source)


def fig10_sensitivity() -> Path:
    df = read("P8_sensitivity")
    fig, axes_grid = plt.subplots(2, 3, figsize=(7.2, 4.65), constrained_layout=True)
    axes = axes_grid.ravel()
    mode_colors = {
        "direct": PALETTE["gray"],
        "kmeans": PALETTE["teal"],
        "dbscan": PALETTE["orange"],
    }

    mode = df[df.sensitivity_factor.eq("candidate_mode")].copy()
    mode = mode.set_index("sensitivity_level").loc[["direct", "kmeans", "dbscan"]].reset_index()
    axes[0].bar(
        [item.capitalize() if item != "dbscan" else "DBSCAN" for item in mode.sensitivity_level],
        mode["risk_weighted_completion_time_mean"],
        color=[mode_colors[item] for item in mode.sensitivity_level],
        edgecolor="white",
        lw=0.5,
    )
    axes[0].set_title("Candidate mode risk-time")
    axes[0].set_ylabel("Risk-time")

    axes[1].bar(
        [item.capitalize() if item != "dbscan" else "DBSCAN" for item in mode.sensitivity_level],
        100 * mode["candidate_pair_reduction_mean"],
        color=[mode_colors[item] for item in mode.sensitivity_level],
        edgecolor="white",
        lw=0.5,
    )
    axes[1].set_title("Pair reduction")
    axes[1].set_ylabel("%")

    uav = _numeric_sensitivity(df, "uav_count")
    axes[2].plot(uav["level"], uav["makespan_mean"], marker="o", color=PALETTE["blue_teal"])
    axes[2].set_title("UAV count")
    axes[2].set_xlabel("UAVs")
    axes[2].set_ylabel("Makespan")

    budget = _numeric_sensitivity(df, "iteration_budget")
    axes[3].plot(budget["level"], budget["alns_improving_moves_mean"], marker="o", color=PALETTE["coral"])
    axes[3].set_title("Iteration budget")
    axes[3].set_xlabel("Iterations")
    axes[3].set_ylabel("Improving moves")

    quantile = _numeric_sensitivity(df, "quantile_z")
    axes[4].plot(quantile["level"], 100 * quantile["infeasible_sortie_rate_mean"], marker="o", color=PALETTE["amber"])
    axes[4].set_title("Energy quantile")
    axes[4].set_xlabel("$z$")
    axes[4].set_ylabel("Infeasible (%)")

    reserve = _numeric_sensitivity(df, "reserve_ratio")
    axes[5].plot(reserve["level"], 100 * reserve["infeasible_sortie_rate_mean"], marker="o", color=PALETTE["orange"])
    axes[5].set_title("Reserve ratio")
    axes[5].set_xlabel("Reserve")
    axes[5].set_ylabel("Infeasible (%)")

    for ax in axes:
        ax.grid(alpha=0.18, lw=0.5)
        ax.tick_params(axis="x", rotation=20)
    label_panels(axes)
    return save(fig, "Fig10_sensitivity", df)


def _numeric_sensitivity(df: pd.DataFrame, factor: str) -> pd.DataFrame:
    out = df[df.sensitivity_factor.eq(factor)].copy()
    out["level"] = out["sensitivity_level"].astype(float)
    return out.sort_values("level")


def read(experiment_id: str) -> pd.DataFrame:
    return pd.read_csv(EXPERIMENTS / experiment_id / "analysis_data" / f"{experiment_id}_{RUN_ID}_summary.csv")


def save(fig, stem: str, source: pd.DataFrame) -> Path:
    out = OUT / stem
    source.to_csv(out.with_name(stem + "_source.csv"), index=False)
    fig.savefig(out.with_suffix(".png"), dpi=300, bbox_inches="tight")
    fig.savefig(out.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(out.with_suffix(".svg"), bbox_inches="tight")
    plt.close(fig)
    return out


def label_panels(axes) -> None:
    for idx, ax in enumerate(axes):
        ax.text(-0.13, 1.08, chr(ord("A") + idx), transform=ax.transAxes, fontsize=8.5, weight="bold")


def contact_sheet(paths: list[Path]) -> None:
    thumbs = []
    for path in paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((520, 260))
        canvas = Image.new("RGB", (560, 330), "white")
        canvas.paste(img, ((560 - img.width) // 2, 20))
        draw = ImageDraw.Draw(canvas)
        draw.text((16, 295), path.stem, fill=(30, 30, 30))
        thumbs.append(canvas)
    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 560, rows * 330), "white")
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 560, (i // cols) * 330))
    sheet.save(OUT / "publishable_figures_contact_sheet.png")


def manifest(paths: list[Path]) -> None:
    lines = ["# Publishable Figure Manifest", ""]
    for i, path in enumerate(paths, 1):
        if path.name.endswith("_ai"):
            lines.append(f"- Fig. {i}: `{path.name}` (AI-generated PNG; non-experimental schematic)")
        else:
            lines.append(f"- Fig. {i}: `{path.name}` (Python PNG/PDF/SVG/source CSV; experimental or source-data figure)")
    (OUT / "figure_manifest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


PUBLISHABLE_FIGURE_BUILDERS = [
    fig0_network_construction_ai,
    fig1_framework_ai,
    fig2_instances,
    fig3_operator_mechanism_ai,
    fig3_milp_validation,
    fig4_algorithm_comparison,
    fig5_energy_surrogate_accuracy,
    fig6_ablation,
    fig7_case_study,
    fig8_scalability,
    fig9_candidate_screening_statistics,
    fig10_sensitivity,
]


if __name__ == "__main__":
    raise SystemExit(main())
