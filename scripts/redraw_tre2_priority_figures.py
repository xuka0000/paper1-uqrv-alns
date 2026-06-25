from __future__ import annotations

import shutil
import sys
from pathlib import Path
from types import SimpleNamespace

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.priority import risk_value_priority_map
from uqrv.proposal_design import ProposalSizeConfig, generate_custom_scenario
from uqrv.solvers import solve


EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
OUT = PROJECT_ROOT / "results/figures/tre2style"
MANUSCRIPT_FIGS = PROJECT_ROOT / "manuscript_context" / "tre_published_style" / "figures"
P11_RUN_ID = "repair_stress_repair2_20260612"

PALETTE = {
    "teal": "#51999F",
    "blue_teal": "#4198AC",
    "light_gray": "#D9DEDD",
    "dark": "#2F3E46",
    "gray": "#6E7C7C",
    "coral": "#ED8D5A",
    "amber": "#ECB66C",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.linewidth": 0.55,
        "axes.labelsize": 6.8,
        "axes.titlesize": 7.4,
        "xtick.labelsize": 5.9,
        "ytick.labelsize": 5.9,
        "legend.fontsize": 5.9,
        "legend.frameon": False,
        "figure.dpi": 180,
    }
)


def save(fig: plt.Figure, stem: str, source: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    base = OUT / stem
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=450, bbox_inches="tight")
    plt.close(fig)
    source.to_csv(OUT / f"{stem}_source.csv", index=False)
    shutil.copyfile(base.with_suffix(".pdf"), MANUSCRIPT_FIGS / f"{stem}.pdf")


def label_panels(axes) -> None:
    for label, ax in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", axes):
        ax.text(-0.13, 1.10, label, transform=ax.transAxes, weight="bold", fontsize=8.0, va="bottom")


def fig1_topology_dispatch() -> None:
    scenario = generate_custom_scenario(
        ProposalSizeConfig("CASE", 200, 100, 4, 3, "illustrative corridor case"),
        seed=2,
        uncertainty="high",
    )
    energy_model = EnergyModel(battery_capacity=scenario.battery_capacity, reserve_ratio=0.12)
    plan = solve(scenario, "alns_full", energy_model=energy_model, iterations=60, seed=2)
    towers = pd.DataFrame([t.__dict__ for t in scenario.towers])
    stops = pd.DataFrame([s.__dict__ for s in scenario.stops])
    tasks = pd.DataFrame([t.__dict__ for t in plan.tasks])
    priority = risk_value_priority_map(scenario.towers)
    tasks["risk_value"] = tasks["tower_id"].map(priority)
    towers["risk_value"] = towers["id"].map(priority)

    fig, axes = plt.subplots(1, 2, figsize=(7.25, 2.15), constrained_layout=True)

    for ax in axes:
        ax.set_xlabel("Corridor x (km)")
        ax.set_ylabel("Corridor y (km)")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(3))
        ax.tick_params(length=2.2, width=0.45)

    sc = axes[0].scatter(
        towers["x"],
        towers["y"],
        c=towers["risk_value"],
        s=7 + 25 * towers["risk"],
        cmap="YlOrRd",
        alpha=0.9,
        edgecolor="none",
        label="Towers",
    )
    for _, seg in towers.groupby("segment"):
        seg = seg.sort_values("x")
        axes[0].plot(seg["x"], seg["y"], color=PALETTE["light_gray"], lw=0.65, zorder=0)
    axes[0].scatter(
        stops["x"],
        stops["y"],
        marker="^",
        s=15,
        color=PALETTE["teal"],
        edgecolor="white",
        lw=0.2,
        label="Candidate stops",
    )
    axes[0].scatter([stops.iloc[0]["x"]], [stops.iloc[0]["y"]], marker="s", s=24, color="black", label="Depot")
    axes[0].set_title("Corridor topology and task priority")
    axes[0].legend(loc="upper left", handletextpad=0.25, borderpad=0.2)

    stop_by_id = {int(row.id): row for row in stops.itertuples()}
    tower_by_id = {int(row.id): row for row in towers.itertuples()}
    axes[1].scatter(towers["x"], towers["y"], s=5.5, color=PALETTE["light_gray"], alpha=0.8, label="Unselected towers")
    top_tasks = tasks.sort_values("risk_value", ascending=False).head(34)
    axes[1].scatter(
        [tower_by_id[int(t.tower_id)].x for t in top_tasks.itertuples()],
        [tower_by_id[int(t.tower_id)].y for t in top_tasks.itertuples()],
        c=top_tasks["risk_value"],
        cmap="YlOrRd",
        s=21,
        edgecolor="white",
        lw=0.25,
        label="High-risk tasks",
    )
    ordered_stops = tasks.sort_values("start")["stop_id"].drop_duplicates().head(30)
    route_xy = [(stop_by_id[int(s)].x, stop_by_id[int(s)].y) for s in ordered_stops]
    if route_xy:
        axes[1].plot(
            [x for x, _ in route_xy],
            [y for _, y in route_xy],
            color=PALETTE["dark"],
            lw=0.8,
            alpha=0.7,
            label="Vehicle stop order",
        )
    for task in top_tasks.head(28).itertuples():
        stop = stop_by_id[int(task.stop_id)]
        tower = tower_by_id[int(task.tower_id)]
        axes[1].plot([stop.x, tower.x], [stop.y, tower.y], color=PALETTE["blue_teal"], ls="--", lw=0.5, alpha=0.58)
    axes[1].scatter(
        stops["x"],
        stops["y"],
        marker="^",
        s=15,
        color=PALETTE["teal"],
        edgecolor="white",
        lw=0.2,
        label="Stops",
    )
    axes[1].set_title("Solved dispatch network")
    axes[1].legend(loc="upper left", handletextpad=0.25, borderpad=0.2)

    y_min = min(towers["y"].min(), stops["y"].min())
    y_max = max(towers["y"].max(), stops["y"].max())
    y_pad = max(1.0, (y_max - y_min) * 0.10)
    for ax in axes:
        ax.set_ylim(y_min - y_pad, y_max + y_pad)
        ax.margins(x=0.025)

    cbar = fig.colorbar(sc, ax=axes, shrink=0.82, pad=0.012)
    cbar.set_label("Risk-value score")
    label_panels(axes)

    source = pd.concat(
        [
            towers.assign(kind="tower"),
            stops.assign(kind="stop", risk="", value="", service_time="", payload="", segment="", risk_value=""),
            tasks.assign(kind="task"),
        ],
        ignore_index=True,
        sort=False,
    )
    save(fig, "Fig1_topology_dispatch", source)


def fig5_stress_heatmaps() -> None:
    p11 = pd.read_csv(
        EXPERIMENTS
        / "P11_repair_stress"
        / "analysis_data"
        / f"P11_repair_stress_{P11_RUN_ID}_summary.csv"
    )
    methods = ["alns_fixed", "no_uq", "no_risk_value", "no_energy_repair", "no_sync_repair", "alns_pinn_full"]
    method_short = ["Fixed", "No UQ", "No RV", "No E-rep", "No S-rep", "Full"]
    stress_cases = ["sparse_high_wind", "tight_battery", "very_sparse_corridor"]
    case_labels = ["Sparse high wind", "Tight battery", "Very sparse corridor"]
    metrics = [
        ("risk_weighted_completion_time_mean", "RWCT (lower better)", "{:.0f}", 1.0),
        ("infeasible_sortie_rate_mean", "Infeas. rate (lower better)", "{:.2f}", 1.0),
        ("top_risk_coverage_mean", "Top-risk cov. (higher better)", "{:.2f}", 1.0),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.65), constrained_layout=True)
    cmap = plt.get_cmap("YlGnBu")

    for ax, (metric, title, fmt, divisor) in zip(axes, metrics):
        mat = (
            p11[p11.method.isin(methods)]
            .pivot(index="stress_case", columns="method", values=metric)
            .loc[stress_cases, methods]
            / divisor
        )
        im = ax.imshow(mat.values, aspect="auto", cmap=cmap)
        ax.set_title(title, pad=7)
        ax.set_xticks(range(len(methods)), method_short, rotation=32, ha="right", rotation_mode="anchor")
        ax.set_yticks(range(len(stress_cases)), case_labels)
        ax.tick_params(length=0)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                val = mat.values[i, j]
                norm_val = im.norm(val)
                color = "white" if norm_val > 0.62 else "#111111"
                ax.text(j, i, fmt.format(val), ha="center", va="center", fontsize=5.5, color=color)
        cbar = fig.colorbar(im, ax=ax, fraction=0.045, pad=0.018)
        cbar.ax.tick_params(labelsize=5.7, length=2)

    label_panels(axes)
    save(fig, "Fig5_ablation_stress_heatmaps", p11.assign(source="P11_stress_routeaware"))


def fig6_public_gis_cases() -> None:
    cases = [
        ("Bay Area", "public_bay_area_full"),
        ("Los Angeles inland", "public_los_angeles_inland_full"),
        ("Dallas-Fort Worth", "public_dallas_fort_worth_full"),
    ]
    all_towers = []
    all_stops = []
    for label, folder in cases:
        root = EXPERIMENTS / "P9_real_gis_case" / folder / "gis_case"
        towers = pd.read_csv(root / "towers.csv").assign(case=label, kind="tower")
        stops = pd.read_csv(root / "stops.csv").assign(case=label, kind="stop")
        priority = risk_value_priority_map([SimpleNamespace(**row.to_dict()) for _, row in towers.iterrows()])
        towers["risk_value"] = towers["id"].map(priority)
        all_towers.append(towers)
        all_stops.append(stops)

    global_min = min(t["risk_value"].min() for t in all_towers)
    global_max = max(t["risk_value"].max() for t in all_towers)
    norm = mpl.colors.Normalize(global_min, global_max)

    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.55), constrained_layout=True)
    sources = []
    last_sc = None
    for ax, (label, _), towers, stops in zip(axes, cases, all_towers, all_stops):
        for _, seg in towers.groupby("segment"):
            seg = seg.sort_values("x")
            ax.plot(seg["x"], seg["y"], color=PALETTE["light_gray"], lw=0.62, zorder=0)

        top = towers.sort_values("risk_value", ascending=False).head(max(8, int(len(towers) * 0.18)))
        for _, row in top.head(10).iterrows():
            nearest_idx = ((stops["x"] - row["x"]) ** 2 + (stops["y"] - row["y"]) ** 2).idxmin()
            nearest = stops.loc[nearest_idx]
            ax.plot(
                [nearest["x"], row["x"]],
                [nearest["y"], row["y"]],
                color=PALETTE["blue_teal"],
                ls="--",
                lw=0.5,
                alpha=0.58,
                zorder=1,
            )

        last_sc = ax.scatter(
            towers["x"],
            towers["y"],
            s=9,
            c=towers["risk_value"],
            cmap="YlOrRd",
            norm=norm,
            alpha=0.9,
            edgecolor="none",
            zorder=2,
        )
        ax.scatter(
            stops["x"],
            stops["y"],
            marker="^",
            s=18,
            color=PALETTE["teal"],
            edgecolor="white",
            lw=0.25,
            zorder=3,
        )
        ax.set_title(label)
        ax.set_xlabel("Projected x (km)")
        ax.set_ylabel("Projected y (km)")
        ax.xaxis.set_major_locator(MaxNLocator(4))
        ax.yaxis.set_major_locator(MaxNLocator(4))
        ax.tick_params(length=2.2, width=0.45)
        ax.set_aspect("equal", adjustable="box")
        ax.margins(0.04)
        sources.append(towers)
        sources.append(stops)

    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=PALETTE["coral"], markeredgecolor="none", markersize=4.5, label="Tower"),
        Line2D([0], [0], marker="^", color="none", markerfacecolor=PALETTE["teal"], markeredgecolor="white", markersize=5.0, label="Candidate stop"),
        Line2D([0], [0], color=PALETTE["blue_teal"], ls="--", lw=0.7, label="Representative service link"),
    ]
    axes[0].legend(handles=handles, loc="upper left", handlelength=1.5, handletextpad=0.3)
    cbar = fig.colorbar(last_sc, ax=axes, shrink=0.82, pad=0.012)
    cbar.set_label("Proxy risk-value score")
    label_panels(axes)

    save(fig, "Fig6_public_gis_cases", pd.concat(sources, ignore_index=True, sort=False))


def main() -> int:
    fig1_topology_dispatch()
    fig5_stress_heatmaps()
    fig6_public_gis_cases()
    print("Redrew Fig1_topology_dispatch, Fig5_ablation_stress_heatmaps and Fig6_public_gis_cases.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
