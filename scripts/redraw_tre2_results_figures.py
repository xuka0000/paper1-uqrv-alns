from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
OUT = PROJECT_ROOT / "results/figures/tre2style"
MANUSCRIPT_FIGS = PROJECT_ROOT / "manuscript_context" / "tre_published_style" / "figures"
RUN_ID = "multi_tower_repair2_full_20260612"
P10_RUN_ID = "airlab_energy_calibration_stop_batch_20260606"

PALETTE = {
    "pale_teal": "#BFDFD2",
    "teal": "#51999F",
    "blue": "#4198AC",
    "light_blue": "#7BC0CD",
    "gold": "#DDCB92",
    "orange": "#ECB66C",
    "coral": "#ED8D5A",
    "green": "#BFDFD2",
    "dark": "#26343B",
    "gray": "#6E7C7C",
    "light": "#BFDFD2",
    "grid": "#D9DEDD",
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
    "fixed_physics": "Fixed physics",
    "point_pinn": "Point residual",
    "probabilistic_pinn": "Probabilistic residual",
    "constant_mean": "Constant mean",
    "parameter_linear": "Parameter linear",
    "parameter_route_linear": "Route linear",
    "telemetry_weather_linear": "Telemetry-weather",
}

METHOD_COLORS = {
    "greedy_nearest": PALETTE["gray"],
    "ga": PALETTE["gold"],
    "aco": PALETTE["orange"],
    "simulated_annealing": PALETTE["gold"],
    "tabu_search": "#8E6BBE",
    "variable_neighborhood_search": "#5F7F62",
    "hybrid_genetic_search": "#51646A",
    "alns_fixed": PALETTE["light_blue"],
    "alns_pinn": PALETTE["blue"],
    "alns_pinn_uq": PALETTE["teal"],
    "alns_pinn_full": PALETTE["coral"],
    "fixed_physics": PALETTE["gray"],
    "point_pinn": PALETTE["blue"],
    "probabilistic_pinn": PALETTE["coral"],
    "constant_mean": PALETTE["gray"],
    "parameter_linear": PALETTE["light_blue"],
    "parameter_route_linear": PALETTE["teal"],
    "telemetry_weather_linear": PALETTE["coral"],
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 6.7,
        "axes.labelsize": 6.8,
        "axes.titlesize": 7.2,
        "xtick.labelsize": 6.0,
        "ytick.labelsize": 6.0,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.fontsize": 5.8,
        "legend.frameon": False,
        "figure.dpi": 220,
    }
)


def read_summary(experiment_id: str) -> pd.DataFrame:
    path = EXPERIMENTS / experiment_id / "analysis_data" / f"{experiment_id}_{RUN_ID}_summary.csv"
    return pd.read_csv(path)


def label_panels(axes) -> None:
    for letter, ax in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", axes):
        ax.text(
            -0.12,
            1.08,
            letter,
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=7.0,
            fontweight="bold",
        )


def save_figure(fig: plt.Figure, stem: str, source: pd.DataFrame) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    pdf = OUT / f"{stem}.pdf"
    png = OUT / f"{stem}.png"
    svg = OUT / f"{stem}.svg"
    fig.savefig(pdf, bbox_inches="tight")
    fig.savefig(png, dpi=320, bbox_inches="tight")
    fig.savefig(svg, bbox_inches="tight")
    source.to_csv(OUT / f"{stem}_source.csv", index=False)
    shutil.copy2(pdf, MANUSCRIPT_FIGS / f"{stem}.pdf")
    plt.close(fig)


def draw_algorithm_effects() -> None:
    df = read_summary("P2_algorithm_comparison")
    methods = [
        "greedy_nearest",
        "ga",
        "aco",
        "simulated_annealing",
        "tabu_search",
        "variable_neighborhood_search",
        "hybrid_genetic_search",
        "alns_pinn_full",
    ]
    focus_methods = ["aco", "hybrid_genetic_search", "alns_pinn_full"]
    focus_labels = [METHOD_LABELS[m] for m in focus_methods]
    scales = [100, 500]

    fig, axes = plt.subplots(2, 2, figsize=(7.25, 3.95), constrained_layout=True)
    ax_a, ax_b, ax_c, ax_d = axes.ravel()

    for ax, towers in zip([ax_a, ax_b], scales):
        sub = df[df["tower_count"].eq(towers)].set_index("method").loc[methods].reset_index()
        y = list(range(len(methods)))
        means = sub["risk_weighted_completion_time_mean"]
        sds = sub["risk_weighted_completion_time_sd"]
        for yi, row, mean, sd in zip(y, sub.itertuples(), means, sds):
            color = METHOD_COLORS[row.method]
            ax.errorbar(
                mean,
                yi,
                xerr=sd,
                fmt="o",
                ms=3.7 if row.method == "alns_pinn_full" else 3.2,
                lw=0.8,
                capsize=2.0,
                color=color,
                ecolor=color,
                alpha=0.96,
            )
        full = float(sub.loc[sub.method.eq("alns_pinn_full"), "risk_weighted_completion_time_mean"].iloc[0])
        external = float(sub[sub.method.ne("alns_pinn_full")]["risk_weighted_completion_time_mean"].min())
        ax.axvline(full, color=PALETTE["coral"], ls="--", lw=0.75, alpha=0.8)
        ax.set_yticks(y, [METHOD_LABELS[m] for m in methods])
        for tick, method in zip(ax.get_yticklabels(), methods):
            if method == "alns_pinn_full":
                tick.set_color(PALETTE["coral"])
                tick.set_fontweight("bold")
        ax.invert_yaxis()
        ax.set_title(f"{towers}-tower RWCT", loc="left")
        ax.set_xlabel("RWCT (lower better)")
        ax.grid(axis="x", alpha=0.35, lw=0.45, color=PALETTE["grid"])
        ax.text(
            0.98,
            0.08,
            f"vs best external: {(external - full) / external * 100:.2f}%",
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=5.7,
            color=PALETTE["dark"],
            bbox={"boxstyle": "round,pad=0.16", "fc": "white", "ec": PALETTE["grid"], "lw": 0.4},
        )

    offsets = [-0.12, 0.0, 0.12]
    for method, label, offset in zip(focus_methods, focus_labels, offsets):
        sub = df[df["method"].eq(method) & df["tower_count"].isin(scales)].sort_values("tower_count")
        x = [i + offset for i in range(len(scales))]
        ax_c.errorbar(
            x,
            sub["top_risk_coverage_mean"],
            yerr=sub["top_risk_coverage_sd"],
            marker="o",
            ms=3.5,
            lw=1.0,
            capsize=2.0,
            color=METHOD_COLORS[method],
            label=label,
        )
        ax_d.errorbar(
            x,
            sub["infeasible_sortie_rate_mean"] * 100.0,
            yerr=sub["infeasible_sortie_rate_sd"] * 100.0,
            marker="o",
            ms=3.5,
            lw=1.0,
            capsize=2.0,
            color=METHOD_COLORS[method],
            label=label,
        )

    ax_c.set_title("Top-risk coverage", loc="left")
    ax_c.set_ylabel("Coverage (higher better)")
    ax_c.set_xticks(range(len(scales)), [str(s) for s in scales])
    ax_c.set_xlabel("Towers")
    ax_c.set_ylim(0.0, 1.05)
    ax_c.grid(axis="y", alpha=0.35, lw=0.45, color=PALETTE["grid"])
    ax_c.legend(loc="lower right")

    ax_d.set_title("Residual infeasible sorties", loc="left")
    ax_d.set_ylabel("Infeasible-sortie rate (%)")
    ax_d.set_xticks(range(len(scales)), [str(s) for s in scales])
    ax_d.set_xlabel("Towers")
    ax_d.set_ylim(bottom=-0.02)
    ax_d.grid(axis="y", alpha=0.35, lw=0.45, color=PALETTE["grid"])

    label_panels([ax_a, ax_b, ax_c, ax_d])
    source = df[df["tower_count"].isin(scales)].copy()
    save_figure(fig, "Fig3_algorithm_effects", source)


def draw_energy_evidence() -> None:
    p3 = read_summary("P3_pinn_prediction_accuracy")
    p10 = pd.read_csv(
        EXPERIMENTS
        / "P10_energy_telemetry_calibration"
        / "analysis_data"
        / f"P10_energy_telemetry_calibration_{P10_RUN_ID}_summary.csv"
    )
    pred = pd.read_csv(
        EXPERIMENTS
        / "P10_energy_telemetry_calibration"
        / "analysis_data"
        / f"P10_energy_telemetry_calibration_{P10_RUN_ID}_predictions.csv"
    )

    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.42), constrained_layout=True)
    ax_a, ax_b, ax_c = axes

    sim_order = ["fixed_physics", "point_pinn", "probabilistic_pinn"]
    high = p3[p3["uncertainty"].eq("high")].set_index("prediction_model").loc[sim_order].reset_index()
    x = list(range(len(high)))
    ax_a.bar(
        x,
        high["mae_mean"],
        yerr=high["mae_sd"],
        capsize=2.0,
        color=[METHOD_COLORS[m] for m in high["prediction_model"]],
        edgecolor="white",
        lw=0.4,
    )
    ax_a.set_xticks(x, [METHOD_LABELS[m] for m in high["prediction_model"]], rotation=24, ha="right")
    ax_a.set_ylabel("MAE (simulation units)")
    ax_a.set_title("High-uncertainty energy model", loc="left")
    ax_a.grid(axis="y", alpha=0.35, lw=0.45, color=PALETTE["grid"])
    ax_a2 = ax_a.twinx()
    ax_a2.plot(x, high["coverage_95_mean"], marker="D", ms=3.2, lw=1.0, color=PALETTE["blue"], label="95% coverage")
    ax_a2.set_ylim(0.0, 1.06)
    ax_a2.set_ylabel("95% coverage", color=PALETTE["blue"])
    ax_a2.tick_params(axis="y", labelcolor=PALETTE["blue"])
    ax_a2.spines["top"].set_visible(False)
    best_false = float(high.loc[high["prediction_model"].eq("probabilistic_pinn"), "false_feasible_rate_mean"].iloc[0])
    ax_a.text(
        0.98,
        0.92,
        f"false-feasible: {best_false * 100:.1f}%",
        transform=ax_a.transAxes,
        ha="right",
        va="top",
        fontsize=5.7,
        color=PALETTE["dark"],
    )

    telemetry_order = ["constant_mean", "parameter_linear", "parameter_route_linear", "telemetry_weather_linear"]
    tel = p10.set_index("model").loc[telemetry_order].reset_index()
    ax_b.bar(
        range(len(tel)),
        tel["mae_wh"],
        color=[METHOD_COLORS[m] for m in tel["model"]],
        edgecolor="white",
        lw=0.4,
    )
    ax_b.set_xticks(range(len(tel)), [METHOD_LABELS[m] for m in tel["model"]], rotation=26, ha="right")
    ax_b.set_ylabel("Held-out MAE (Wh)")
    ax_b.set_title("AirLab telemetry calibration", loc="left")
    ax_b.grid(axis="y", alpha=0.35, lw=0.45, color=PALETTE["grid"])
    base = float(tel.loc[tel["model"].eq("constant_mean"), "mae_wh"].iloc[0])
    best = float(tel.loc[tel["model"].eq("telemetry_weather_linear"), "mae_wh"].iloc[0])
    ax_b.text(
        0.98,
        0.92,
        f"{(base - best) / base * 100:.1f}% MAE reduction",
        transform=ax_b.transAxes,
        ha="right",
        va="top",
        fontsize=5.7,
        color=PALETTE["dark"],
        bbox={"boxstyle": "round,pad=0.16", "fc": "white", "ec": PALETTE["grid"], "lw": 0.4},
    )

    best_pred = pred[(pred["model"].eq("telemetry_weather_linear")) & (pred["split"].eq("test"))].copy()
    ax_c.scatter(
        best_pred["actual_energy_wh"],
        best_pred["predicted_energy_wh"],
        s=14,
        color=PALETTE["teal"],
        alpha=0.82,
        edgecolor="white",
        lw=0.25,
    )
    lo = min(best_pred["actual_energy_wh"].min(), best_pred["predicted_energy_wh"].min())
    hi = max(best_pred["actual_energy_wh"].max(), best_pred["predicted_energy_wh"].max())
    pad = (hi - lo) * 0.06
    ax_c.plot([lo - pad, hi + pad], [lo - pad, hi + pad], color=PALETTE["dark"], lw=0.8, ls="--")
    ax_c.set_xlim(lo - pad, hi + pad)
    ax_c.set_ylim(lo - pad, hi + pad)
    ax_c.set_xlabel("Actual energy (Wh)")
    ax_c.set_ylabel("Predicted energy (Wh)")
    ax_c.set_title("Held-out telemetry fit", loc="left")
    ax_c.grid(alpha=0.35, lw=0.45, color=PALETTE["grid"])
    ax_c.text(
        0.04,
        0.93,
        f"n={len(best_pred)}; MAE={best:.2f} Wh",
        transform=ax_c.transAxes,
        ha="left",
        va="top",
        fontsize=5.7,
        color=PALETTE["dark"],
    )

    label_panels(axes)
    source = pd.concat([p3.assign(source="P3"), p10.assign(source="P10")], ignore_index=True, sort=False)
    save_figure(fig, "Fig4_energy_evidence", source)


def main() -> int:
    draw_algorithm_effects()
    draw_energy_evidence()
    print("Redrew Fig3_algorithm_effects and Fig4_energy_evidence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
