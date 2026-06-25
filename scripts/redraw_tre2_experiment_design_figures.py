from __future__ import annotations

import shutil
import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import cm
from matplotlib.colors import Normalize
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from mpl_toolkits.mplot3d import Axes3D  # noqa: F401


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
OUT = PROJECT_ROOT / "results/figures/tre2style"
MANUSCRIPT_FIGS = PROJECT_ROOT / "manuscript_context" / "tre_published_style" / "figures"
SOURCE_OUT = OUT / "source_data"
RUN_ID = "multi_tower_repair2_full_20260612"

sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel  # noqa: E402
from uqrv.gis_case import load_gis_case  # noqa: E402
from uqrv.metrics import evaluate_plan  # noqa: E402
from uqrv.priority import risk_value_priority_map  # noqa: E402
from uqrv.solvers import solve  # noqa: E402


PALETTE = {
    "pale_teal": "#BFDFD2",
    "teal": "#51999F",
    "blue": "#4198AC",
    "light_blue": "#7BC0CD",
    "red": "#ED8D5A",
    "orange": "#EA9E58",
    "gold": "#DDCB92",
    "green": "#BFDFD2",
    "dark": "#111111",
    "gray": "#6E7C7C",
    "light_gray": "#D9DEDD",
    "grid": "#D9DEDD",
}

METHOD_LABELS = {
    "alns_pinn": "Point energy ALNS",
    "alns_pinn_full": "Proposed",
}


mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7.2,
        "axes.labelsize": 7.2,
        "axes.titlesize": 7.8,
        "xtick.labelsize": 6.6,
        "ytick.labelsize": 6.6,
        "axes.linewidth": 0.72,
        "axes.edgecolor": PALETTE["dark"],
        "legend.fontsize": 6.2,
        "legend.frameon": False,
        "figure.dpi": 180,
    }
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    SOURCE_OUT.mkdir(parents=True, exist_ok=True)
    draw_fig7_enriched()
    draw_screening_surface()
    draw_gis_operation_state()
    print("Redrew enriched scalability/screening, response-surface and operating-state figures.")
    return 0


def read_summary(experiment_id: str) -> pd.DataFrame:
    path = EXPERIMENTS / experiment_id / "analysis_data" / f"{experiment_id}_{RUN_ID}_summary.csv"
    return pd.read_csv(path)


def save_figure(fig: plt.Figure, name: str, source: pd.DataFrame) -> None:
    pdf = OUT / f"{name}.pdf"
    png = OUT / f"{name}.png"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=360, bbox_inches="tight")
    shutil.copyfile(pdf, MANUSCRIPT_FIGS / pdf.name)
    shutil.copyfile(png, MANUSCRIPT_FIGS / png.name)
    source.to_csv(SOURCE_OUT / f"{name}_source.csv", index=False)
    plt.close(fig)


def panel_label(ax, label: str) -> None:
    ax.text(
        -0.08,
        1.04,
        label,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=8.5,
        fontweight="bold",
        color=PALETTE["dark"],
    )


def annotate_box(ax, x, y, text: str, color: str, dx: float = 0.0, dy: float = 0.0) -> None:
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(x + dx, y + dy),
        fontsize=6.2,
        color=color,
        ha="center",
        va="center",
        bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": color, "lw": 0.55},
        arrowprops={"arrowstyle": "-", "lw": 0.45, "color": color, "shrinkA": 1.5, "shrinkB": 1.5},
    )


def draw_fig7_enriched() -> None:
    p2 = read_summary("P2_algorithm_comparison")
    p6 = read_summary("P6_candidate_stop_screening")
    p8 = read_summary("P8_sensitivity")

    fig = plt.figure(figsize=(7.25, 4.25))
    gs = GridSpec(2, 2, figure=fig, hspace=0.52, wspace=0.35)
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0])
    ax_d = fig.add_subplot(gs[1, 1])

    method_colors = {"alns_pinn": PALETTE["light_blue"], "alns_pinn_full": PALETTE["red"]}
    for method in ["alns_pinn", "alns_pinn_full"]:
        sub = p2[p2["method"].eq(method)].sort_values("tower_count")
        x = sub["tower_count"].to_numpy()
        y = sub["risk_weighted_completion_time_mean"].to_numpy()
        sd = sub["risk_weighted_completion_time_sd"].to_numpy()
        ax_a.plot(x, y, marker="o", ms=3.6, lw=1.35, color=method_colors[method], label=METHOD_LABELS[method])
        ax_a.fill_between(x, y - sd, y + sd, color=method_colors[method], alpha=0.10, lw=0)
        last = sub.iloc[-1]
        annotate_box(
            ax_a,
            float(last.tower_count),
            float(last.risk_weighted_completion_time_mean),
            f"{float(last.risk_weighted_completion_time_mean):.0f}",
            method_colors[method],
            dx=-55 if method == "alns_pinn_full" else -40,
            dy=25 if method == "alns_pinn_full" else 70,
        )
    ax_a.set_title("Risk-time scaling", loc="left")
    ax_a.set_xlabel("Towers")
    ax_a.set_ylabel("RWCT")
    ax_a.legend(loc="upper left")
    panel_label(ax_a, "A")

    for method in ["alns_pinn", "alns_pinn_full"]:
        sub = p2[p2["method"].eq(method)].sort_values("tower_count")
        x = sub["tower_count"].to_numpy()
        y = sub["solver_runtime_mean"].to_numpy()
        ax_b.plot(x, y, marker="o", ms=3.6, lw=1.35, color=method_colors[method], label=METHOD_LABELS[method])
        for _, row in sub[sub["tower_count"].isin([100, 500])].iterrows():
            ax_b.text(
                row.tower_count,
                row.solver_runtime_mean * (1.18 if method == "alns_pinn_full" else 0.78),
                f"{row.solver_runtime_mean:.2f}s",
                fontsize=5.9,
                ha="center",
                color=method_colors[method],
            )
    ax_b.set_yscale("log")
    ax_b.set_title("Runtime scaling", loc="left")
    ax_b.set_xlabel("Towers")
    ax_b.set_ylabel("Runtime (s, log)")
    panel_label(ax_b, "B")

    mode_order = ["direct", "kmeans", "dbscan"]
    mode_labels = {"direct": "Direct", "kmeans": "K-means", "dbscan": "DBSCAN"}
    mode_colors = {"direct": PALETTE["gray"], "kmeans": PALETTE["teal"], "dbscan": PALETTE["orange"]}
    towers = sorted(p6["tower_count"].unique())
    x = np.arange(len(towers))
    width = 0.22
    ax_c2 = ax_c.twinx()
    for offset, mode in zip([-width, 0.0, width], mode_order):
        sub = p6[p6["candidate_mode"].eq(mode)].sort_values("tower_count")
        reduction = (sub["candidate_pair_reduction_mean"] * 100.0).to_numpy()
        infeas = (sub["infeasible_sortie_rate_mean"] * 100.0).to_numpy()
        bars = ax_c.bar(x + offset, reduction, width=width, color=mode_colors[mode], alpha=0.55, label=f"{mode_labels[mode]} reduction")
        ax_c2.plot(x + offset, infeas, marker="o", ms=3.1, lw=1.0, color=mode_colors[mode], label=f"{mode_labels[mode]} infeas.")
        if mode in {"kmeans", "dbscan"}:
            for bi, bar in enumerate(bars):
                if towers[bi] in {30, 100}:
                    ax_c.text(
                        bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 2.0,
                        f"{bar.get_height():.0f}%",
                        ha="center",
                        fontsize=5.7,
                        color=mode_colors[mode],
                    )
    ax_c.set_xticks(x)
    ax_c.set_xticklabels([str(int(t)) for t in towers])
    ax_c.set_ylim(0, 102)
    ax_c2.set_ylim(0, 88)
    ax_c.set_title("Candidate-stop screening", loc="left")
    ax_c.set_xlabel("Towers")
    ax_c.set_ylabel("Pair reduction (%)")
    ax_c2.set_ylabel("Infeasible sorties (%)")
    ax_c2.spines["top"].set_visible(False)
    mode_handles = [
        Line2D([0], [0], color=mode_colors["direct"], lw=4, alpha=0.55, label="Direct"),
        Line2D([0], [0], color=mode_colors["kmeans"], lw=4, alpha=0.55, label="K-means"),
        Line2D([0], [0], color=mode_colors["dbscan"], lw=4, alpha=0.55, label="DBSCAN"),
        Line2D([0], [0], color=PALETTE["dark"], marker="o", lw=1.0, label="IFR line"),
    ]
    ax_c.legend(handles=mode_handles, loc="lower right", ncol=1, fontsize=5.4, frameon=True, framealpha=0.86)
    panel_label(ax_c, "C")

    sens = p8[p8["sensitivity_factor"].eq("uav_count")].copy()
    sens["uav_count"] = sens["sensitivity_level"].astype(float)
    ax_d.plot(sens["uav_count"], sens["makespan_mean"], marker="o", ms=3.6, lw=1.35, color=PALETTE["red"], label="Makespan")
    ax_d2 = ax_d.twinx()
    ax_d2.plot(
        sens["uav_count"],
        sens["risk_weighted_completion_time_mean"],
        marker="s",
        ms=3.3,
        lw=1.15,
        ls="--",
        color=PALETTE["blue"],
        label="RWCT",
    )
    ax_d.set_ylim(float(sens["makespan_mean"].min()) - 28.0, float(sens["makespan_mean"].max()) + 38.0)
    ax_d2.set_ylim(
        float(sens["risk_weighted_completion_time_mean"].min()) - 18.0,
        float(sens["risk_weighted_completion_time_mean"].max()) + 28.0,
    )
    for idx, row in enumerate(sens.itertuples(index=False)):
        ax_d.annotate(
            f"{row.makespan_mean:.0f}",
            xy=(row.uav_count, row.makespan_mean),
            xytext=(0, 8 if idx != 1 else 11),
            textcoords="offset points",
            ha="center",
            fontsize=6.0,
            color=PALETTE["red"],
        )
        ax_d2.annotate(
            f"{row.risk_weighted_completion_time_mean:.0f}",
            xy=(row.uav_count, row.risk_weighted_completion_time_mean),
            xytext=(0, -12 if idx != 1 else -15),
            textcoords="offset points",
            ha="center",
            fontsize=6.0,
            color=PALETTE["blue"],
        )
    ax_d.set_title("Fleet-size response", loc="left")
    ax_d.set_xlabel("UAV count")
    ax_d.set_ylabel("Makespan", color=PALETTE["red"])
    ax_d2.set_ylabel("RWCT", color=PALETTE["blue"])
    ax_d.tick_params(axis="y", labelcolor=PALETTE["red"])
    ax_d2.tick_params(axis="y", labelcolor=PALETTE["blue"])
    ax_d2.spines["top"].set_visible(False)
    handles, labels = ax_d.get_legend_handles_labels()
    handles2, labels2 = ax_d2.get_legend_handles_labels()
    ax_d.legend(handles + handles2, labels + labels2, loc="upper right")
    panel_label(ax_d, "D")

    for ax in [ax_a, ax_b, ax_c, ax_d]:
        ax.grid(alpha=0.45, lw=0.45, color=PALETTE["grid"])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    ax_b.legend(loc="upper left")
    save_figure(fig, "Fig7_scalability_screening", pd.concat([p2.assign(source="P2"), p6.assign(source="P6"), p8.assign(source="P8")], ignore_index=True, sort=False))


def draw_screening_surface() -> None:
    p6 = read_summary("P6_candidate_stop_screening")
    mode_order = ["direct", "kmeans", "dbscan"]
    mode_labels = ["Direct", "K-means", "DBSCAN"]
    towers = sorted(p6["tower_count"].unique())
    grid = p6.pivot(index="candidate_mode", columns="tower_count", values="risk_weighted_completion_time_mean").loc[mode_order]
    infeas_grid = p6.pivot(index="candidate_mode", columns="tower_count", values="infeasible_sortie_rate_mean").loc[mode_order]
    feasible_grid = p6.pivot(index="candidate_mode", columns="tower_count", values="feasible_candidate_pairs_mean").loc[mode_order]

    x_vals, y_vals = np.meshgrid(np.array(towers, dtype=float), np.arange(len(mode_order), dtype=float))
    z_vals = grid.to_numpy(dtype=float)

    fig = plt.figure(figsize=(7.25, 3.25))
    gs = GridSpec(1, 2, figure=fig, width_ratios=[1.22, 1.0], wspace=0.28)
    ax_a = fig.add_subplot(gs[0, 0], projection="3d")
    ax_b = fig.add_subplot(gs[0, 1])

    norm = Normalize(vmin=float(np.nanmin(z_vals)), vmax=float(np.nanmax(z_vals)))
    surface = ax_a.plot_surface(
        x_vals,
        y_vals,
        z_vals,
        facecolors=cm.YlGnBu_r(norm(z_vals)),
        rstride=1,
        cstride=1,
        linewidth=0.45,
        edgecolor="#7F8C8D",
        alpha=0.90,
        antialiased=True,
    )
    del surface
    ax_a.scatter(x_vals.ravel(), y_vals.ravel(), z_vals.ravel(), s=14, color=PALETTE["red"], depthshade=False, label="Observed data source")
    ax_a.set_title("A  Screening response surface", loc="left", pad=3)
    ax_a.set_xlabel("Towers", labelpad=4)
    ax_a.set_ylabel("Stop mode", labelpad=6)
    ax_a.set_zlabel("")
    ax_a.set_yticks(range(len(mode_order)))
    ax_a.set_yticklabels(mode_labels)
    ax_a.view_init(elev=24, azim=-58)
    ax_a.legend(loc="upper left", bbox_to_anchor=(0.02, 1.02))

    sm = cm.ScalarMappable(norm=norm, cmap=cm.YlGnBu_r)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax_a, shrink=0.64, pad=0.07)
    cbar.set_label("RWCT")

    mode_colors = {"direct": PALETTE["gray"], "kmeans": PALETTE["teal"], "dbscan": PALETTE["orange"]}
    ax_b2 = ax_b.twinx()
    for mode, label in zip(mode_order, mode_labels):
        ax_b.plot(
            towers,
            feasible_grid.loc[mode].to_numpy(dtype=float),
            marker="o",
            ms=3.3,
            lw=1.15,
            color=mode_colors[mode],
            label=f"{label} feasible pairs",
        )
        ax_b2.plot(
            towers,
            infeas_grid.loc[mode].to_numpy(dtype=float) * 100.0,
            marker="s",
            ms=3.0,
            lw=0.95,
            ls="--",
            color=mode_colors[mode],
            label=f"{label} IFR",
        )
    ax_b.set_title("B  Graph density versus residual infeasibility", loc="left")
    ax_b.set_xlabel("Towers")
    ax_b.set_ylabel("Feasible support pairs")
    ax_b2.set_ylabel("Infeasible sorties (%)")
    ax_b.set_xlim(min(towers) - 3, max(towers) + 12)
    ax_b.grid(alpha=0.45, lw=0.45, color=PALETTE["grid"])
    ax_b.spines["top"].set_visible(False)
    ax_b2.spines["top"].set_visible(False)
    ax_b.text(
        0.04,
        0.94,
        "solid: feasible pairs; dashed: IFR",
        transform=ax_b.transAxes,
        ha="left",
        va="top",
        fontsize=6.1,
        color=PALETTE["dark"],
        bbox={"boxstyle": "round,pad=0.15", "fc": "white", "ec": PALETTE["grid"], "lw": 0.45},
    )
    ax_b.text(
        0.56,
        0.84,
        "Direct feasible pairs",
        transform=ax_b.transAxes,
        fontsize=5.8,
        color=mode_colors["direct"],
        va="center",
    )
    source = p6.assign(surface_z_rwct=p6["risk_weighted_completion_time_mean"])
    save_figure(fig, "Fig8_candidate_screening_surface", source)


def draw_gis_operation_state() -> None:
    case_root = EXPERIMENTS / "P9_real_gis_case" / "public_bay_area_full" / "gis_case"
    scenario = load_gis_case(case_root, case_id="public_bay_area_full")
    energy_model = EnergyModel(battery_capacity=scenario.battery_capacity)
    plan = solve(scenario, method="alns_full", energy_model=energy_model, iterations=80, seed=0)
    metrics = evaluate_plan(scenario, plan, energy_model)

    towers = pd.DataFrame([tower.__dict__ for tower in scenario.towers])
    priority = risk_value_priority_map(scenario.towers)
    towers["risk_value"] = towers["id"].map(priority)
    stops = pd.DataFrame([stop.__dict__ for stop in scenario.stops])
    tasks = pd.DataFrame([task.__dict__ for task in plan.tasks]).sort_values(["finish", "start"]).reset_index(drop=True)
    tasks["risk_value"] = tasks["tower_id"].map(priority)
    tasks["duration"] = tasks["finish"] - tasks["start"]
    tasks["service_rank"] = np.arange(1, len(tasks) + 1)
    task_xy = tasks.merge(towers[["id", "x", "y", "risk_value"]], left_on="tower_id", right_on="id", suffixes=("", "_tower"))
    task_xy = task_xy.merge(stops[["id", "x", "y"]], left_on="stop_id", right_on="id", suffixes=("_tower", "_stop"))
    limit = energy_model.battery_capacity * (1.0 - energy_model.reserve_ratio)
    task_xy["q95_margin"] = limit - task_xy["energy_q95"]

    top_count = max(1, int(len(scenario.towers) * 0.25))
    top_ids = set(towers.sort_values("risk_value", ascending=False).head(top_count)["id"].astype(int))
    early_cutoff = tasks.sort_values("finish").iloc[top_count - 1]["finish"]

    fig = plt.figure(figsize=(7.25, 4.65))
    gs = GridSpec(2, 3, figure=fig, width_ratios=[1.24, 1.24, 1.0], height_ratios=[1.0, 0.82], hspace=0.40, wspace=0.35)
    ax_map = fig.add_subplot(gs[:, :2])
    ax_time = fig.add_subplot(gs[0, 2])
    ax_energy = fig.add_subplot(gs[1, 2])

    norm = Normalize(vmin=float(towers["risk_value"].min()), vmax=float(towers["risk_value"].max()))
    ax_map.scatter(stops["x"], stops["y"], marker="^", s=28, color="white", edgecolor=PALETTE["blue"], lw=0.7, label="Candidate stops", zorder=3)
    ax_map.scatter(towers["x"], towers["y"], s=14, color=PALETTE["light_gray"], edgecolor="white", lw=0.25, label="Towers", zorder=2)
    top_towers = towers[towers["id"].isin(top_ids)]
    scatter = ax_map.scatter(
        top_towers["x"],
        top_towers["y"],
        c=top_towers["risk_value"],
        cmap="YlOrRd",
        norm=norm,
        s=28,
        edgecolor=PALETTE["dark"],
        lw=0.25,
        label="Top-risk towers",
        zorder=4,
    )

    selected_stop_ids = tasks.sort_values("start")["stop_id"].drop_duplicates().astype(int).tolist()
    selected = stops[stops["id"].isin(selected_stop_ids)].copy()
    selected["order"] = selected["id"].map({sid: idx + 1 for idx, sid in enumerate(selected_stop_ids)})
    selected = selected.sort_values("order")
    ax_map.scatter(selected["x"], selected["y"], marker="o", s=46, facecolor="white", edgecolor=PALETTE["blue"], lw=1.0, label="Selected stops", zorder=5)
    if len(selected) > 1:
        xs = selected["x"].to_numpy()
        ys = selected["y"].to_numpy()
        ax_map.plot(xs, ys, color=PALETTE["blue"], lw=1.25, alpha=0.86, label="Vehicle stop order", zorder=3)
        for x0, y0, x1, y1 in zip(xs[:-1], ys[:-1], xs[1:], ys[1:]):
            ax_map.annotate(
                "",
                xy=(x1, y1),
                xytext=(x0, y0),
                arrowprops={"arrowstyle": "-|>", "lw": 0.8, "color": PALETTE["blue"], "shrinkA": 4, "shrinkB": 4},
                zorder=3,
            )
    high_task_xy = task_xy[task_xy["tower_id"].isin(top_ids)].sort_values("risk_value", ascending=False).head(26)
    for _, row in high_task_xy.iterrows():
        ax_map.plot(
            [row["x_stop"], row["x_tower"]],
            [row["y_stop"], row["y_tower"]],
            color=PALETTE["teal"],
            lw=0.65,
            ls=(0, (3, 2)),
            alpha=0.62,
            zorder=1,
        )
    ax_map.set_title("A  Bay Area computational dispatch state", loc="left")
    ax_map.set_xlabel("Local x-coordinate (km)")
    ax_map.set_ylabel("Local y-coordinate (km)")
    ax_map.grid(alpha=0.32, lw=0.42, color=PALETTE["grid"])
    ax_map.legend(loc="upper left", ncol=2)
    cbar = fig.colorbar(scatter, ax=ax_map, shrink=0.58, pad=0.015)
    cbar.set_label("Risk-value score")

    cmap = mpl.colormaps["YlOrRd"]
    for _, row in tasks.iterrows():
        color = cmap(norm(row["risk_value"]))
        ax_time.barh(row["uav_id"], row["duration"], left=row["start"], height=0.55, color=color, edgecolor="white", lw=0.25)
    ax_time.axvline(early_cutoff, color=PALETTE["blue"], lw=0.9, ls="--")
    ax_time.text(early_cutoff + 1.5, ax_time.get_ylim()[1] - 0.20, "early cutoff", ha="left", va="top", fontsize=5.8, color=PALETTE["blue"])
    ax_time.set_title("B  UAV service timeline", loc="left")
    ax_time.set_xlabel("Completion time")
    ax_time.set_ylabel("UAV")
    ax_time.set_yticks(sorted(tasks["uav_id"].unique()))
    ax_time.grid(axis="x", alpha=0.32, lw=0.42, color=PALETTE["grid"])

    margin_rows = task_xy[task_xy["tower_id"].isin(top_ids)].sort_values("finish").head(24).copy()
    colors = [PALETTE["red"] if m < 0 else PALETTE["gold"] if m < 10 else PALETTE["teal"] for m in margin_rows["q95_margin"]]
    ax_energy.bar(np.arange(len(margin_rows)), margin_rows["q95_margin"], color=colors, width=0.82, edgecolor="white", lw=0.25)
    ax_energy.axhline(0, color=PALETTE["dark"], lw=0.7)
    ax_energy.set_title("C  q95 energy margin", loc="left")
    ax_energy.set_xlabel("Top-risk services by finish")
    ax_energy.set_ylabel("Margin (Wh)")
    ax_energy.set_xticks([0, len(margin_rows) - 1])
    ax_energy.set_xticklabels(["early", "later"])
    ax_energy.grid(axis="y", alpha=0.32, lw=0.42, color=PALETTE["grid"])
    ax_energy.text(
        0.04,
        0.08,
        f"RWCT={metrics['risk_weighted_completion_time']:.0f}\nTopCov={metrics['top_risk_coverage']:.2f}\nIFR={metrics['infeasible_sortie_rate']:.3f}",
        transform=ax_energy.transAxes,
        fontsize=6.1,
        color=PALETTE["dark"],
        bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": PALETTE["grid"], "lw": 0.55},
    )

    for ax in [ax_map, ax_time, ax_energy]:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

    source = task_xy.assign(
        case_id=scenario.id,
        battery_limit=limit,
        metrics_rwct=metrics["risk_weighted_completion_time"],
        metrics_topcov=metrics["top_risk_coverage"],
        metrics_ifr=metrics["infeasible_sortie_rate"],
    )
    save_figure(fig, "Fig9_public_gis_operation_state", source)


if __name__ == "__main__":
    raise SystemExit(main())
