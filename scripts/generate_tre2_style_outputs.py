from __future__ import annotations

import shutil
import sys
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(CODE_ROOT))

from uqrv.energy import EnergyModel
from uqrv.proposal_design import ProposalSizeConfig, generate_custom_scenario
from uqrv.solvers import solve


RUN_ID = "final_complete_full_20260625"
P2_RUN_ID = "main_external_portfolio_full_20260625"
P10_RUN_ID = "final_complete_full_20260625"
P11_RUN_ID = "final_complete_full_20260625"
P9_RUN_IDS = {
    "public_bay_area_full": "final_complete_public_bay_area_full_20260625",
    "public_dallas_fort_worth_full": "final_complete_public_dallas_fort_worth_full_20260625",
    "public_los_angeles_inland_full": "final_complete_public_los_angeles_inland_full_20260625",
}
EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
OUT = PROJECT_ROOT / "results/figures/tre2style"
MANUSCRIPT_DIR = PROJECT_ROOT / "manuscript_context" / "tre_published_style"
MANUSCRIPT_FIGS = MANUSCRIPT_DIR / "figures"
TABLES_TEX = MANUSCRIPT_DIR / "generated_tables.tex"
ANALYSIS_MD = PROJECT_ROOT / "docs/project" / "tre2_full_manuscript_figure_table_plan_20260625.md"

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
    "light_gray": "#D9DEDD",
}

METHOD_LABELS = {
    "greedy_nearest": "Nearest",
    "ga": "GA",
    "aco": "ACO",
    "simulated_annealing": "SA",
    "tabu_search": "Tabu",
    "variable_neighborhood_search": "VNS",
    "hybrid_genetic_search": "HGS-VNS",
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
    "probabilistic_pinn": "Probabilistic residual",
    "constant_mean": "Constant mean",
    "parameter_linear": "Parameter linear",
    "parameter_route_linear": "Route linear",
    "telemetry_weather_linear": "Telemetry-weather linear",
}

METHOD_COLORS = {
    "greedy_nearest": PALETTE["gray"],
    "ga": PALETTE["amber"],
    "aco": PALETTE["orange"],
    "simulated_annealing": PALETTE["muted_gold"],
    "tabu_search": "#8E6BBE",
    "variable_neighborhood_search": "#5F7F62",
    "hybrid_genetic_search": "#51646A",
    "alns_fixed": PALETTE["light_cyan"],
    "alns_pinn": PALETTE["blue_teal"],
    "alns_pinn_uq": PALETTE["teal"],
    "alns_pinn_full": PALETTE["coral"],
    "milp_highs": PALETTE["muted_gold"],
    "fixed_physics": PALETTE["gray"],
    "point_pinn": PALETTE["blue_teal"],
    "probabilistic_pinn": PALETTE["coral"],
    "constant_mean": PALETTE["gray"],
    "parameter_linear": PALETTE["light_cyan"],
    "parameter_route_linear": PALETTE["teal"],
    "telemetry_weather_linear": PALETTE["coral"],
    "no_pinn": PALETTE["light_cyan"],
    "no_adaptive": PALETTE["blue_teal"],
    "no_uq": PALETTE["teal"],
    "no_risk_value": PALETTE["orange"],
    "no_energy_repair": PALETTE["muted_gold"],
    "no_sync_repair": PALETTE["amber"],
    "no_clustering": PALETTE["gray"],
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
        "axes.labelsize": 7.0,
        "axes.titlesize": 7.6,
        "xtick.labelsize": 6.2,
        "ytick.labelsize": 6.2,
        "legend.fontsize": 6.0,
        "legend.frameon": False,
        "figure.dpi": 180,
    }
)


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)

    stems = [
        fig1_topology_and_dispatch(),
        fig2_solution_framework(),
        fig3_algorithm_effects(),
        fig4_energy_evidence(),
        fig5_ablation_stress_heatmaps(),
        fig6_public_gis_cases(),
        fig7_scalability_screening(),
    ]
    contact_sheet([p.with_suffix(".png") for p in stems])
    write_tables()
    write_analysis_doc(stems)
    print(f"Generated {len(stems)} TRE2-style figure stems in {OUT}")
    print(f"Wrote manuscript tables to {TABLES_TEX}")
    return 0


def fig1_topology_and_dispatch() -> Path:
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
    tasks["risk_value"] = tasks["risk"] * tasks["value"]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.75), constrained_layout=True)
    for ax in axes:
        ax.set_aspect("equal", adjustable="datalim")
        ax.set_xticks([])
        ax.set_yticks([])

    sc = axes[0].scatter(
        towers["x"],
        towers["y"],
        c=towers["risk"] * towers["value"],
        s=8 + 26 * towers["risk"],
        cmap="YlOrRd",
        alpha=0.86,
        edgecolor="none",
        label="Towers",
    )
    axes[0].scatter(stops["x"], stops["y"], marker="^", s=18, color=PALETTE["teal"], edgecolor="white", lw=0.25, label="Candidate stops")
    for _, seg in towers.groupby("segment"):
        seg = seg.sort_values("x")
        axes[0].plot(seg["x"], seg["y"], color=PALETTE["light_gray"], lw=0.7, zorder=0)
    axes[0].scatter([stops.iloc[0]["x"]], [stops.iloc[0]["y"]], marker="s", s=28, color="black", label="Depot")
    axes[0].legend(loc="upper left", ncol=1, handletextpad=0.3)
    axes[0].set_title("A  Corridor topology and task priority")

    stop_by_id = {int(row.id): row for row in stops.itertuples()}
    tower_by_id = {int(row.id): row for row in towers.itertuples()}
    axes[1].scatter(towers["x"], towers["y"], s=6, color=PALETTE["light_gray"], alpha=0.85, label="Unselected towers")
    top_tasks = tasks.sort_values("risk_value", ascending=False).head(34)
    axes[1].scatter(
        [tower_by_id[int(t.tower_id)].x for t in top_tasks.itertuples()],
        [tower_by_id[int(t.tower_id)].y for t in top_tasks.itertuples()],
        c=top_tasks["risk_value"],
        cmap="YlOrRd",
        s=23,
        edgecolor="white",
        lw=0.25,
        label="High-risk tasks",
    )
    ordered_stops = tasks.sort_values("start")["stop_id"].drop_duplicates().head(30)
    route_xy = [(stop_by_id[int(s)].x, stop_by_id[int(s)].y) for s in ordered_stops]
    if route_xy:
        axes[1].plot([x for x, _ in route_xy], [y for _, y in route_xy], color=PALETTE["dark"], lw=0.8, alpha=0.65, label="Vehicle stop order")
    for task in top_tasks.head(28).itertuples():
        stop = stop_by_id[int(task.stop_id)]
        tower = tower_by_id[int(task.tower_id)]
        axes[1].plot([stop.x, tower.x], [stop.y, tower.y], color=PALETTE["blue_teal"], ls="--", lw=0.55, alpha=0.55)
    axes[1].scatter(stops["x"], stops["y"], marker="^", s=17, color=PALETTE["teal"], edgecolor="white", lw=0.25, label="Stops")
    axes[1].set_title("B  Simplified dispatch network")
    axes[1].legend(loc="upper left", ncol=1, handletextpad=0.3)
    cbar = fig.colorbar(sc, ax=axes, shrink=0.78, pad=0.01)
    cbar.set_label("Risk-value score")

    source = pd.concat(
        [
            towers.assign(kind="tower"),
            stops.assign(kind="stop", risk="", value="", service_time="", payload="", segment=""),
            tasks.assign(kind="task"),
        ],
        ignore_index=True,
        sort=False,
    )
    return save(fig, "Fig1_topology_dispatch", source)


def fig2_solution_framework() -> Path:
    fig, ax = plt.subplots(figsize=(7.2, 2.75), constrained_layout=True)
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)

    def box(x, y, w, h, text, fc="white", ec="black", lw=0.8, rounded=False):
        if rounded:
            patch = mpl.patches.FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.02,rounding_size=0.025",
                facecolor=fc,
                edgecolor=ec,
                lw=lw,
            )
        else:
            patch = mpl.patches.Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, lw=lw)
        ax.add_patch(patch)
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=7.0)

    def arrow(x1, y1, x2, y2, text=None):
        ax.annotate("", xy=(x2, y2), xytext=(x1, y1), arrowprops={"arrowstyle": "->", "lw": 0.8, "color": PALETTE["dark"]})
        if text:
            ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.035, text, ha="center", fontsize=6.2)

    box(0.04, 0.78, 0.13, 0.10, "Start", rounded=True)
    box(0.04, 0.55, 0.20, 0.15, "Inputs\ncorridor, towers,\nstops, weather", fc=PALETTE["pale_teal"], ec=PALETTE["teal"], rounded=True)
    box(0.30, 0.55, 0.25, 0.15, "Stage 1\nprobabilistic energy\nand sortie-pattern screening", fc=PALETTE["muted_gold"], ec=PALETTE["orange"], rounded=True)
    box(0.61, 0.55, 0.24, 0.15, "Stage 2\nrisk-value ALNS\nschedule construction", fc=PALETTE["pale_teal"], ec=PALETTE["teal"], rounded=True)
    box(0.39, 0.25, 0.25, 0.13, "S-scale MILP reference\nand calibration checks", fc="white", ec=PALETTE["gray"], rounded=True)
    box(0.89, 0.55, 0.08, 0.15, "Stop?", fc="white", ec=PALETTE["dark"])
    box(0.88, 0.24, 0.10, 0.10, "Best\nschedule", fc=PALETTE["coral"], ec=PALETTE["dark"], rounded=True)
    arrow(0.105, 0.78, 0.135, 0.70)
    arrow(0.24, 0.625, 0.30, 0.625)
    arrow(0.55, 0.625, 0.61, 0.625)
    arrow(0.85, 0.625, 0.89, 0.625)
    arrow(0.93, 0.55, 0.93, 0.34, "yes")
    ax.annotate("", xy=(0.42, 0.55), xytext=(0.93, 0.55), arrowprops={"arrowstyle": "->", "lw": 0.75, "color": PALETTE["gray"], "connectionstyle": "angle3,angleA=-90,angleB=180"})
    ax.text(0.68, 0.47, "no: update operator weights and return", ha="center", fontsize=6.2, color=PALETTE["gray"])
    arrow(0.43, 0.55, 0.49, 0.38)
    arrow(0.55, 0.38, 0.66, 0.55)
    ax.text(0.02, 0.93, "Two-stage optimization loop used in the manuscript experiments", fontsize=8.3, weight="bold")
    return save(fig, "Fig2_solution_framework", pd.DataFrame({"module": ["inputs", "energy_screening", "alns", "milp_reference", "best_schedule"]}))


def fig3_algorithm_effects() -> Path:
    df = read_summary("P2_algorithm_comparison")
    order = [
        "greedy_nearest",
        "ga",
        "aco",
        "simulated_annealing",
        "tabu_search",
        "variable_neighborhood_search",
        "hybrid_genetic_search",
        "alns_pinn_full",
    ]
    rows = []
    for towers in [100, 500]:
        sub = df[df["tower_count"].eq(towers)].set_index("method").loc[order].reset_index()
        full = float(sub.loc[sub.method.eq("alns_pinn_full"), "risk_weighted_completion_time_mean"].iloc[0])
        external = sub[sub.method.ne("alns_pinn_full")]["risk_weighted_completion_time_mean"].min()
        rows.append({"tower_count": towers, "best_external_gain_pct": (external - full) / external * 100})
    gains = pd.DataFrame(rows)

    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.05), constrained_layout=True)
    for col, towers in enumerate([100, 500]):
        ax = axes[0, col]
        sub = df[df["tower_count"].eq(towers)].set_index("method").loc[order].reset_index()
        colors = [METHOD_COLORS[m] for m in sub.method]
        ax.barh([METHOD_LABELS[m] for m in sub.method], sub["risk_weighted_completion_time_mean"], color=colors, edgecolor="white", lw=0.4)
        ax.set_title(f"{towers}-tower risk-weighted time")
        ax.grid(axis="x", alpha=0.18, lw=0.45)
        ax.invert_yaxis()
        gain = gains[gains.tower_count.eq(towers)].iloc[0]
        ax.text(0.98, 0.08, f"Gain vs best external: {gain.best_external_gain_pct:.2f}%",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=6.2,
                bbox={"boxstyle": "round,pad=0.22", "fc": "white", "ec": PALETTE["light_gray"], "lw": 0.4})

    for col, metric in enumerate(["top_risk_coverage_mean", "infeasible_sortie_rate_mean"]):
        ax = axes[1, col]
        plot_methods = ["aco", "hybrid_genetic_search", "alns_pinn_full"]
        plot = df[df["tower_count"].isin([100, 500]) & df["method"].isin(plot_methods)]
        for method in plot_methods:
            sub = plot[plot.method.eq(method)].sort_values("tower_count")
            ax.plot(sub["tower_count"], sub[metric], marker="o", color=METHOD_COLORS[method], label=METHOD_LABELS[method], lw=1.2)
        ax.set_title("Top-risk coverage" if metric.startswith("top") else "Infeasible sortie rate")
        ax.set_xlabel("Towers")
        ax.grid(alpha=0.18, lw=0.45)
        if metric.startswith("top"):
            ax.set_ylim(0.0, 1.02)
        else:
            ax.set_ylim(0.0, max(0.003, plot[metric].max() * 1.35))
        ax.legend(loc="best")
    label_panels(axes.ravel())
    source = df[df["tower_count"].isin([100, 500])].copy()
    return save(fig, "Fig3_algorithm_effects", source)


def fig4_energy_evidence() -> Path:
    p3 = read_summary("P3_pinn_prediction_accuracy")
    p10 = pd.read_csv(EXPERIMENTS / "P10_energy_telemetry_calibration" / "analysis_data" / f"P10_energy_telemetry_calibration_{P10_RUN_ID}_summary.csv")
    pred = pd.read_csv(EXPERIMENTS / "P10_energy_telemetry_calibration" / "analysis_data" / f"P10_energy_telemetry_calibration_{P10_RUN_ID}_predictions.csv")
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.45), constrained_layout=True)

    high = p3[p3["uncertainty"].eq("high")].set_index("prediction_model").loc[["fixed_physics", "point_pinn", "probabilistic_pinn"]].reset_index()
    x = range(len(high))
    axes[0].bar(x, high["mae_mean"], color=[METHOD_COLORS[m] for m in high.prediction_model], edgecolor="white", lw=0.4)
    axes[0].set_xticks(x, [METHOD_LABELS[m] for m in high.prediction_model], rotation=25, ha="right")
    axes[0].set_ylabel("MAE")
    axes[0].set_title("Simulation energy prediction")
    for i, row in enumerate(high.itertuples()):
        axes[0].text(i, row.mae_mean + 0.35, f"cov. {row.coverage_95_mean:.2f}", ha="center", fontsize=5.8)

    order = ["constant_mean", "parameter_linear", "parameter_route_linear", "telemetry_weather_linear"]
    p10 = p10.set_index("model").loc[order].reset_index()
    axes[1].bar(range(len(p10)), p10["mae_wh"], color=[METHOD_COLORS[m] for m in p10.model], edgecolor="white", lw=0.4)
    axes[1].set_xticks(range(len(p10)), [METHOD_LABELS[m] for m in p10.model], rotation=30, ha="right")
    axes[1].set_ylabel("MAE (Wh)")
    axes[1].set_title("AirLab telemetry calibration")
    base = float(p10.loc[p10.model.eq("constant_mean"), "mae_wh"].iloc[0])
    best = float(p10.loc[p10.model.eq("telemetry_weather_linear"), "mae_wh"].iloc[0])
    axes[1].text(0.98, 0.92, f"{(base - best) / base * 100:.1f}% MAE reduction", transform=axes[1].transAxes, ha="right", va="top", fontsize=6.0)

    best_pred = pred[(pred.model == "telemetry_weather_linear") & (pred.split == "test")]
    axes[2].scatter(best_pred["actual_energy_wh"], best_pred["predicted_energy_wh"], s=16, color=PALETTE["teal"], alpha=0.8, edgecolor="white", lw=0.25)
    lo = min(best_pred["actual_energy_wh"].min(), best_pred["predicted_energy_wh"].min())
    hi = max(best_pred["actual_energy_wh"].max(), best_pred["predicted_energy_wh"].max())
    axes[2].plot([lo, hi], [lo, hi], color=PALETTE["dark"], lw=0.8, ls="--")
    axes[2].set_xlabel("Actual Wh")
    axes[2].set_ylabel("Predicted Wh")
    axes[2].set_title("Held-out telemetry fit")
    for ax in axes:
        ax.grid(alpha=0.18, lw=0.45)
    label_panels(axes)
    return save(fig, "Fig4_energy_evidence", pd.concat([p3.assign(source="P3"), p10.assign(source="P10")], ignore_index=True, sort=False))


def fig5_ablation_stress_heatmaps() -> Path:
    p4 = read_summary("P4_ablation")
    p11 = pd.read_csv(EXPERIMENTS / "P11_repair_stress" / "analysis_data" / f"P11_repair_stress_{P11_RUN_ID}_summary.csv")
    methods = ["alns_fixed", "no_uq", "no_risk_value", "no_energy_repair", "no_sync_repair", "alns_pinn_full"]
    method_short = ["Fixed", "No UQ", "No RV", "No E-rep", "No S-rep", "Full"]
    stress_cases = list(p11["stress_case"].drop_duplicates())
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 3.0), constrained_layout=True)

    matrix_metrics = [
        ("risk_weighted_completion_time_mean", "Stress risk-time (x$10^3$)", "{:.0f}", "Reds", 1000.0),
        ("infeasible_sortie_rate_mean", "Stress infeasible rate", "{:.2f}", "Oranges"),
        ("top_risk_coverage_mean", "Stress top-risk coverage", "{:.2f}", "YlGnBu"),
    ]
    for ax, spec in zip(axes, matrix_metrics):
        if len(spec) == 5:
            metric, title, fmt, cmap, divisor = spec
        else:
            metric, title, fmt, cmap = spec
            divisor = 1.0
        mat = p11[p11.method.isin(methods)].pivot(index="stress_case", columns="method", values=metric).loc[stress_cases, methods]
        mat_plot = mat / divisor
        im = ax.imshow(mat_plot.values, aspect="auto", cmap=cmap)
        ax.set_xticks(range(len(methods)), method_short, rotation=35, ha="right")
        ax.set_yticks(range(len(stress_cases)), [s.replace("_", " ") for s in stress_cases])
        ax.set_title(title)
        for i in range(mat.shape[0]):
            for j in range(mat.shape[1]):
                val = mat_plot.values[i, j]
                ax.text(j, i, fmt.format(val), ha="center", va="center", fontsize=5.2, color="black",
                        bbox={"boxstyle": "round,pad=0.13", "fc": "white", "ec": "none", "alpha": 0.72})
        fig.colorbar(im, ax=ax, fraction=0.046, pad=0.02)
    label_panels(axes)
    source = pd.concat([p4.assign(source="P4_ablation"), p11.assign(source="P11_stress")], ignore_index=True, sort=False)
    return save(fig, "Fig5_ablation_stress_heatmaps", source)


def fig6_public_gis_cases() -> Path:
    cases = [
        ("Bay Area", "public_bay_area_full"),
        ("Los Angeles inland", "public_los_angeles_inland_full"),
        ("Dallas-Fort Worth", "public_dallas_fort_worth_full"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55), constrained_layout=True)
    sources = []
    for ax, (label, folder) in zip(axes, cases):
        root = EXPERIMENTS / "P9_real_gis_case" / folder / "gis_case"
        towers = pd.read_csv(root / "towers.csv")
        stops = pd.read_csv(root / "stops.csv")
        towers["risk_value"] = towers["risk"] * towers["value"]
        top = towers.sort_values("risk_value", ascending=False).head(max(8, int(len(towers) * 0.18)))
        ax.scatter(towers["x"], towers["y"], s=7, c=towers["risk_value"], cmap="YlOrRd", alpha=0.8, edgecolor="none")
        ax.scatter(stops["x"], stops["y"], marker="^", s=16, color=PALETTE["teal"], edgecolor="white", lw=0.2)
        for _, row in top.head(12).iterrows():
            nearest = stops.iloc[((stops["x"] - row["x"]) ** 2 + (stops["y"] - row["y"]) ** 2).idxmin()]
            ax.plot([nearest["x"], row["x"]], [nearest["y"], row["y"]], color=PALETTE["blue_teal"], ls="--", lw=0.45, alpha=0.55)
        for _, seg in towers.groupby("segment"):
            seg = seg.sort_values("x")
            ax.plot(seg["x"], seg["y"], color=PALETTE["light_gray"], lw=0.55, zorder=0)
        ax.set_title(label)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_aspect("equal", adjustable="datalim")
        sources.append(towers.assign(case=label, kind="tower"))
        sources.append(stops.assign(case=label, kind="stop"))
    label_panels(axes)
    return save(fig, "Fig6_public_gis_cases", pd.concat(sources, ignore_index=True, sort=False))


def fig7_scalability_screening() -> Path:
    p2 = read_summary("P2_algorithm_comparison")
    p6 = read_summary("P6_candidate_stop_screening")
    p8 = read_summary("P8_sensitivity")
    fig, axes = plt.subplots(2, 2, figsize=(7.2, 4.05), constrained_layout=True)

    for method in ["hybrid_genetic_search", "variable_neighborhood_search", "alns_pinn_full"]:
        sub = p2[p2.method.eq(method)].sort_values("tower_count")
        axes[0, 0].plot(sub["tower_count"], sub["risk_weighted_completion_time_mean"], marker="o", color=METHOD_COLORS[method], label=METHOD_LABELS[method], lw=1.2)
        axes[0, 1].plot(sub["tower_count"], sub["solver_runtime_mean"], marker="o", color=METHOD_COLORS[method], label=METHOD_LABELS[method], lw=1.2)
    axes[0, 0].set_title("Risk-time scalability")
    axes[0, 1].set_title("Runtime scalability")
    axes[0, 0].set_ylabel("Risk-weighted time")
    axes[0, 1].set_ylabel("Runtime (s)")
    axes[0, 1].set_yscale("log")

    for mode in ["direct", "kmeans", "dbscan"]:
        sub = p6[p6.candidate_mode.eq(mode)].sort_values("tower_count")
        axes[1, 0].plot(sub["tower_count"], sub["candidate_pair_reduction_mean"] * 100, marker="o", label=mode, lw=1.2)
    axes[1, 0].set_title("Candidate-pair reduction")
    axes[1, 0].set_ylabel("Reduction (%)")

    sens = p8[p8.sensitivity_factor.eq("uav_count")].copy()
    sens["uav_count_numeric"] = sens["sensitivity_level"].astype(float)
    axes[1, 1].plot(sens["uav_count_numeric"], sens["makespan_mean"], marker="o", color=PALETTE["coral"], lw=1.2)
    axes[1, 1].set_title("Fleet-size response")
    axes[1, 1].set_ylabel("Makespan")
    axes[1, 1].set_xlabel("UAV count")
    for ax in axes.ravel():
        ax.grid(alpha=0.18, lw=0.45)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc="best")
    label_panels(axes.ravel())
    return save(fig, "Fig7_scalability_screening", pd.concat([p2.assign(source="P2"), p6.assign(source="P6"), p8.assign(source="P8")], ignore_index=True, sort=False))


def write_tables() -> None:
    p2 = read_summary("P2_algorithm_comparison")
    p3 = read_summary("P3_pinn_prediction_accuracy")
    p9 = read_gis_pairwise_summary()
    p10 = pd.read_csv(EXPERIMENTS / "P10_energy_telemetry_calibration" / "analysis_data" / f"P10_energy_telemetry_calibration_{P10_RUN_ID}_summary.csv")
    p11 = pd.read_csv(EXPERIMENTS / "P11_repair_stress" / "analysis_data" / f"P11_repair_stress_{P11_RUN_ID}_summary.csv")

    lines: list[str] = []
    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Positioning of this study relative to representative vehicle--UAV and energy-aware routing literature.}")
    lines.append(r"\label{tab:literature-position}")
    lines.append(r"\footnotesize")
    lines.append(r"\begin{tabularx}{\textwidth}{@{}lccccccX@{}}")
    lines.append(r"\toprule")
    lines.append(r"Reference & EV & UAV & Sync. & Energy UQ & Risk/value & GIS/telemetry & Solution approach \\")
    lines.append(r"\midrule")
    rows = [
        ("Murray and Chu (2015)", "", "Y", "Y", "", "", "", "MILP/heuristic truck--drone delivery formulation"),
        ("Sacramento et al. (2019)", "", "Y", "Y", "", "", "", "ALNS for drone-assisted routing"),
        ("Moadab et al. (2022)", "Y", "Y", "Y", "partial", "", "", "Drone routing with public transport capacity"),
        ("Kim et al. (2026)", "Y", "Y", "Y", "", "", "Y", "Two-echelon energy-supply location-routing"),
        ("Shi and Zhen (2026)", "", "Y", "Y", "", "", "", "LLM-assisted heuristic design"),
        ("This work", "", "Y", "Y", "Y", "Y", "Y", "Probabilistic energy screening and risk-value ALNS for inspection"),
    ]
    for row in rows:
        lines.append(" & ".join(row) + r" \\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabularx}")
    lines.append(r"\end{table*}")
    lines.append("")

    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Selected algorithm-comparison results used in the main text.}")
    lines.append(r"\label{tab:algorithm-results}")
    lines.append(r"\footnotesize")
    lines.append(r"\begin{tabular}{@{}llrrrrr@{}}")
    lines.append(r"\toprule")
    lines.append(r"Towers & Method & Makespan & Risk-time & Top-risk cov. & Infeasible & Runtime (s) \\")
    lines.append(r"\midrule")
    for towers in [100, 500]:
        sub = p2[p2["tower_count"].eq(towers)].set_index("method").loc[[
            "greedy_nearest",
            "ga",
            "aco",
            "simulated_annealing",
            "tabu_search",
            "variable_neighborhood_search",
            "hybrid_genetic_search",
            "alns_pinn_full",
        ]].reset_index()
        for row in sub.itertuples():
            lines.append(
                f"{towers} & {METHOD_LABELS[row.method]} & {row.makespan_mean:.2f} & {row.risk_weighted_completion_time_mean:.0f} & "
                f"{row.top_risk_coverage_mean:.3f} & {row.infeasible_sortie_rate_mean:.4f} & {row.solver_runtime_mean:.3f} \\\\"
            )
        lines.append(r"\addlinespace[2pt]")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")
    lines.append("")

    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Energy-prediction evidence from simulation and AirLab telemetry.}")
    lines.append(r"\label{tab:energy-evidence}")
    lines.append(r"\footnotesize")
    lines.append(r"\begin{tabular}{@{}llrrrr@{}}")
    lines.append(r"\toprule")
    lines.append(r"Evidence block & Model & Test count & MAE & 95\% coverage & False feasible \\")
    lines.append(r"\midrule")
    high = p3[p3["uncertainty"].eq("high")].set_index("prediction_model").loc[["fixed_physics", "point_pinn", "probabilistic_pinn"]].reset_index()
    for row in high.itertuples():
        lines.append(f"Simulation, high uncertainty & {METHOD_LABELS[row.prediction_model]} & {int(row.n)} seeds & {row.mae_mean:.2f} & {row.coverage_95_mean:.3f} & {row.false_feasible_rate_mean:.4f} \\\\")
    p10 = p10.set_index("model").loc[["constant_mean", "parameter_linear", "parameter_route_linear", "telemetry_weather_linear"]].reset_index()
    for row in p10.itertuples():
        lines.append(f"AirLab telemetry & {METHOD_LABELS[row.model]} & {int(row.test_count)} flights & {row.mae_wh:.3f} Wh & {row.coverage_95:.3f} & {row.false_feasible_high_energy_rate:.4f} \\\\")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")
    lines.append("")

    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Public GIS-grounded case evidence. Risk and value labels are generated proxies rather than utility field records.}")
    lines.append(r"\label{tab:gis-results}")
    lines.append(r"\footnotesize")
    lines.append(r"\begin{tabular}{@{}llrrrrrr@{}}")
    lines.append(r"\toprule")
    lines.append(r"Case & Best non-full & Full risk-time & Baseline risk-time & Reduction & Full cov. & Baseline cov. & Full infeas. \\")
    lines.append(r"\midrule")
    for row in p9.itertuples():
        case_name = str(row.case_id).replace("_public_full", "").replace("_", " ").title()
        reduction = float(row.full_risk_reduction_vs_best_nonfull_pct)
        lines.append(
            f"{case_name} & {METHOD_LABELS.get(row.best_nonfull_risk_method, row.best_nonfull_risk_method)} & "
            f"{row.full_risk_time:.0f} & {row.best_nonfull_risk_time:.0f} & {reduction:.3f}\\% & "
            f"{row.full_top_risk_coverage:.3f} & {row.best_nonfull_top_risk_coverage:.3f} & {row.full_infeasible_rate:.3f} \\\\"
        )
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")
    lines.append("")

    lines.append(r"\begin{table*}[t]")
    lines.append(r"\centering")
    lines.append(r"\caption{Stress-test summary for repair and uncertainty components. Lower risk-time and infeasible rate are better; higher top-risk coverage is better.}")
    lines.append(r"\label{tab:stress-results}")
    lines.append(r"\footnotesize")
    lines.append(r"\begin{tabular}{@{}llrrrr@{}}")
    lines.append(r"\toprule")
    lines.append(r"Stress case & Method & Risk-time & Top-risk cov. & Infeasible & Improving moves \\")
    lines.append(r"\midrule")
    keep = ["alns_fixed", "no_uq", "no_risk_value", "no_energy_repair", "no_sync_repair", "alns_pinn_full"]
    for stress_case in p11["stress_case"].drop_duplicates():
        sub = p11[p11.stress_case.eq(stress_case)].set_index("method").loc[keep].reset_index()
        for row in sub.itertuples():
            lines.append(
                f"{stress_case.replace('_', ' ')} & {METHOD_LABELS[row.method]} & {row.risk_weighted_completion_time_mean:.0f} & "
                f"{row.top_risk_coverage_mean:.3f} & {row.infeasible_sortie_rate_mean:.3f} & {row.alns_improving_moves_mean:.1f} \\\\"
            )
        lines.append(r"\addlinespace[2pt]")
    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table*}")
    lines.append("")
    TABLES_TEX.write_text("\n".join(lines), encoding="utf-8")


def write_analysis_doc(stems: list[Path]) -> None:
    text = f"""# TRE2-Style Full Manuscript Figure/Table Plan

Date: 2026-06-25

## Quantified TRE2 pattern used

- TRE2 has 21 pages, 8 visible figures, 6 main tables and a reference section of about 2.2 published pages.
- The visual logic is not decorative: one topology schematic, one two-stage algorithm flowchart, one route/construction example, one benchmark results table, one before/after route map, one sensitivity heatmap, one public GIS map and one simplified application-result map.
- The result discussion repeatedly performs secondary analysis on top of raw metrics: improvement over base, optimality gap, feasibility, sensitivity trend and practical interpretation.

## Figures generated for this manuscript

{chr(10).join(f'- `{p.name}` from project data/source CSV' for p in stems)}

## Manuscript table strategy

- Table 1 mirrors TRE2's literature-positioning table.
- Table 2 in the paper is notation and decision variables.
- Generated tables provide algorithm comparison, energy evidence, GIS-grounded evidence and stress-test evidence.

## Claim boundaries

- P9 GIS cases use public tower/weather sources but proxy risk/value labels.
- P10 uses real AirLab quadcopter telemetry, not transmission-line inspection telemetry.
- P11 supports robustness for RWCT, feasible top-risk coverage and infeasible-sortie rate; runtime is not the best metric for the complete method.
"""
    ANALYSIS_MD.write_text(text, encoding="utf-8")


def read_summary(experiment_id: str) -> pd.DataFrame:
    run_id = P2_RUN_ID if experiment_id == "P2_algorithm_comparison" else RUN_ID
    path = EXPERIMENTS / experiment_id / "analysis_data" / f"{experiment_id}_{run_id}_summary.csv"
    if not path.exists():
        raise FileNotFoundError(path)
    return pd.read_csv(path)


def read_gis_pairwise_summary() -> pd.DataFrame:
    rows = []
    for case_id, run_id in P9_RUN_IDS.items():
        df = pd.read_csv(EXPERIMENTS / "P9_real_gis_case" / "analysis_data" / f"P9_real_gis_case_{run_id}_summary.csv")
        full = df[df["method"].eq("alns_pinn_full")].iloc[0]
        external = df[df["method"].ne("alns_pinn_full")]
        best_risk = external.loc[external["risk_weighted_completion_time_mean"].idxmin()]
        best_cov = external.loc[external["top_risk_coverage_mean"].idxmax()]
        rows.append(
            {
                "case_id": case_id,
                "best_nonfull_risk_method": best_risk.method,
                "full_risk_time": full.risk_weighted_completion_time_mean,
                "best_nonfull_risk_time": best_risk.risk_weighted_completion_time_mean,
                "full_risk_reduction_vs_best_nonfull_pct": (
                    (best_risk.risk_weighted_completion_time_mean - full.risk_weighted_completion_time_mean)
                    / best_risk.risk_weighted_completion_time_mean
                    * 100.0
                ),
                "full_top_risk_coverage": full.top_risk_coverage_mean,
                "best_nonfull_top_risk_coverage": best_cov.top_risk_coverage_mean,
                "full_infeasible_rate": full.infeasible_sortie_rate_mean,
            }
        )
    return pd.DataFrame(rows)


def label_panels(axes) -> None:
    for label, ax in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", axes):
        ax.text(-0.08, 1.04, label, transform=ax.transAxes, weight="bold", fontsize=8.0, va="bottom")


def save(fig: plt.Figure, stem: str, source: pd.DataFrame) -> Path:
    base = OUT / stem
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=450, bbox_inches="tight")
    plt.close(fig)
    source.to_csv(OUT / f"{stem}_source.csv", index=False)
    shutil.copyfile(base.with_suffix(".pdf"), MANUSCRIPT_FIGS / f"{stem}.pdf")
    return base


def contact_sheet(images: list[Path]) -> None:
    from PIL import Image, ImageDraw

    thumbs = []
    for path in images:
        img = Image.open(path).convert("RGB")
        img.thumbnail((420, 250))
        canvas = Image.new("RGB", (440, 285), "white")
        canvas.paste(img, ((440 - img.width) // 2, 8))
        draw = ImageDraw.Draw(canvas)
        draw.text((8, 264), path.stem, fill=(30, 30, 30))
        thumbs.append(canvas)
    cols = 2
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 440, rows * 285), "white")
    for idx, img in enumerate(thumbs):
        sheet.paste(img, ((idx % cols) * 440, (idx // cols) * 285))
    sheet.save(OUT / "tre2style_contact_sheet.png")


if __name__ == "__main__":
    raise SystemExit(main())
