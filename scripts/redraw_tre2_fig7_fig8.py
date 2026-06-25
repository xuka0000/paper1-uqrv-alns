from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
OUT = PROJECT_ROOT / "results/figures/tre2style"
MANUSCRIPT_FIGS = PROJECT_ROOT / "manuscript_context" / "tre_published_style" / "figures"
RUN_ID = "multi_tower_repair2_full_20260612"

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
    "alns_pinn": "Point energy ALNS",
    "alns_pinn_full": "Proposed",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 6.6,
        "axes.labelsize": 6.7,
        "axes.titlesize": 7.2,
        "xtick.labelsize": 6.0,
        "ytick.labelsize": 6.0,
        "axes.linewidth": 0.6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.fontsize": 5.8,
        "legend.frameon": False,
        "figure.dpi": 180,
    }
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    draw_fig7()
    draw_fig8()
    update_contact_sheet()
    print("Redrew Fig7_scalability_screening and Fig8_algorithm_mechanism")
    return 0


def draw_fig7() -> None:
    p2 = read_summary("P2_algorithm_comparison")
    p6 = read_summary("P6_candidate_stop_screening")
    p8 = read_summary("P8_sensitivity")

    fig, axes = plt.subplots(2, 2, figsize=(7.25, 3.75), constrained_layout=True)
    ax_a, ax_b, ax_c, ax_d = axes.ravel()

    colors = {"alns_pinn": PALETTE["blue"], "alns_pinn_full": PALETTE["coral"]}
    for method in ["alns_pinn", "alns_pinn_full"]:
        sub = p2[p2["method"].eq(method)].sort_values("tower_count")
        x = sub["tower_count"].to_numpy()
        ax_a.plot(
            x,
            sub["risk_weighted_completion_time_mean"],
            marker="o",
            ms=3.2,
            lw=1.15,
            color=colors[method],
            label=METHOD_LABELS[method],
        )
        ax_b.plot(
            x,
            sub["solver_runtime_mean"],
            marker="o",
            ms=3.2,
            lw=1.15,
            color=colors[method],
            label=METHOD_LABELS[method],
        )
    ax_a.set_title("Risk-time over proposal scales", loc="left")
    ax_a.set_ylabel("RWCT")
    ax_a.set_xlabel("Towers")
    max_towers = int(p2["tower_count"].max())
    max_scale = p2[p2["tower_count"].eq(max_towers)].set_index("method")
    full = float(max_scale.loc["alns_pinn_full", "risk_weighted_completion_time_mean"])
    point = float(max_scale.loc["alns_pinn", "risk_weighted_completion_time_mean"])
    fixed = float(max_scale.loc["alns_fixed", "risk_weighted_completion_time_mean"])
    ax_a.text(
        0.98,
        0.06,
        f"{max_towers} towers:\n{(point - full) / point * 100:.1f}% vs point\n{(fixed - full) / fixed * 100:.1f}% vs fixed",
        transform=ax_a.transAxes,
        ha="right",
        va="bottom",
        fontsize=5.8,
        color=PALETTE["dark"],
        bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": PALETTE["grid"], "lw": 0.4},
    )

    ax_b.set_title("Runtime scaling", loc="left")
    ax_b.set_ylabel("Runtime (s, log)")
    ax_b.set_xlabel("Towers")
    ax_b.set_yscale("log")
    ax_b.text(
        0.03,
        0.06,
        "local Python\nprototype",
        transform=ax_b.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.8,
        color=PALETTE["gray"],
    )

    mode_colors = {"direct": PALETTE["gray"], "kmeans": PALETTE["coral"], "dbscan": PALETTE["green"]}
    mode_labels = {"direct": "Direct", "kmeans": "K-means", "dbscan": "DBSCAN"}
    for mode in ["direct", "kmeans", "dbscan"]:
        sub = p6[p6["candidate_mode"].eq(mode)].sort_values("tower_count")
        ax_c.plot(
            sub["candidate_pair_reduction_mean"] * 100.0,
            sub["infeasible_sortie_rate_mean"] * 100.0,
            marker="o",
            ms=3.1,
            lw=1.1,
            color=mode_colors[mode],
            label=mode_labels[mode],
        )
        for row in sub.itertuples():
            if mode != "direct" and int(row.tower_count) in {30, 100}:
                ax_c.text(
                    row.candidate_pair_reduction_mean * 100.0 + 1.0,
                    row.infeasible_sortie_rate_mean * 100.0 + 1.0,
                    str(int(row.tower_count)),
                    fontsize=5.3,
                    color=mode_colors[mode],
                )
    ax_c.set_title("Screening trade-off", loc="left")
    ax_c.set_xlabel("Candidate-pair reduction (%)")
    ax_c.set_ylabel("Infeasible sorties (%)")
    ax_c.set_xlim(-3, 100)
    ax_c.set_ylim(-4, 88)
    ax_c.text(
        0.55,
        0.08,
        "K-means: compact\nsupport graph",
        transform=ax_c.transAxes,
        ha="left",
        va="bottom",
        fontsize=5.7,
        color=PALETTE["dark"],
        bbox={"boxstyle": "round,pad=0.16", "fc": "white", "ec": PALETTE["grid"], "lw": 0.4},
    )

    sens = p8[p8["sensitivity_factor"].eq("uav_count")].copy()
    sens["uav_count"] = sens["sensitivity_level"].astype(float)
    ax_d.plot(sens["uav_count"], sens["makespan_mean"], marker="o", ms=3.4, lw=1.15, color=PALETTE["coral"], label="Makespan")
    ax_d.set_title("Fleet-size response", loc="left")
    ax_d.set_xlabel("UAV count")
    ax_d.set_ylabel("Makespan", color=PALETTE["coral"])
    ax_d.tick_params(axis="y", labelcolor=PALETTE["coral"])
    ax_d2 = ax_d.twinx()
    ax_d2.plot(
        sens["uav_count"],
        sens["risk_weighted_completion_time_mean"],
        marker="s",
        ms=3.0,
        lw=1.0,
        ls="--",
        color=PALETTE["blue"],
        label="RWCT",
    )
    ax_d2.set_ylabel("RWCT", color=PALETTE["blue"])
    ax_d2.tick_params(axis="y", labelcolor=PALETTE["blue"])
    ax_d2.spines["top"].set_visible(False)
    handles, labels = ax_d.get_legend_handles_labels()
    handles2, labels2 = ax_d2.get_legend_handles_labels()
    ax_d.legend(handles + handles2, labels + labels2, loc="upper right")

    for ax in [ax_a, ax_b, ax_c, ax_d]:
        ax.grid(alpha=0.35, lw=0.45, color=PALETTE["grid"])
    ax_a.legend(loc="upper left")
    ax_b.legend(loc="upper left")
    ax_c.legend(loc="upper left")
    label_panels([ax_a, ax_b, ax_c, ax_d])

    source = pd.concat(
        [p2.assign(source="P2"), p6.assign(source="P6"), p8.assign(source="P8")],
        ignore_index=True,
        sort=False,
    )
    save_figure(fig, "Fig7_scalability_screening", source)


def draw_fig8() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.35), constrained_layout=True)
    source_rows: list[dict[str, object]] = []
    source_rows.extend(draw_screening(axes[0]))
    source_rows.extend(draw_insertion(axes[1]))
    source_rows.extend(draw_reassignment(axes[2]))
    save_figure(fig, "Fig8_algorithm_mechanism", pd.DataFrame(source_rows))


def draw_screening(ax) -> list[dict[str, object]]:
    setup_mechanism_axis(ax, "A  q95 sortie set")
    records: list[dict[str, object]] = []
    stops = [(0.18, 0.75, "s1"), (0.18, 0.50, "s2"), (0.18, 0.25, "s3")]
    towers = [(0.78, 0.80, "i1", 0.92), (0.78, 0.61, "i2", 0.56), (0.78, 0.42, "i3", 0.78), (0.78, 0.23, "i4", 0.44)]
    feasible = {("s1", "i1"), ("s1", "i2"), ("s2", "i2"), ("s2", "i3"), ("s3", "i3"), ("s3", "i4")}
    for sx, sy, sid in stops:
        ax.scatter(sx, sy, marker="^", s=70, color=PALETTE["teal"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(sx - 0.06, sy, sid, ha="right", va="center")
        records.append({"panel": "A", "kind": "stop", "id": sid, "x": sx, "y": sy})
    for tx, ty, tid, risk in towers:
        ax.scatter(tx, ty, s=50 + 45 * risk, color=PALETTE["orange"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(tx + 0.045, ty, tid, ha="left", va="center")
        records.append({"panel": "A", "kind": "tower", "id": tid, "x": tx, "y": ty, "risk_value": risk})
    for sx, sy, sid in stops:
        for tx, ty, tid, _ in towers:
            keep = (sid, tid) in feasible
            ax.plot(
                [sx, tx],
                [sy, ty],
                color=PALETTE["blue"] if keep else PALETTE["grid"],
                lw=0.85 if keep else 0.45,
                ls="-" if keep else "--",
                alpha=0.72 if keep else 0.36,
                zorder=1,
            )
            records.append({"panel": "A", "kind": "edge", "stop": sid, "tower": tid, "kept": keep})
    ax.text(0.50, 0.93, r"keep if $Q_{si}\leq B_d(1-\rho)$", ha="center", color=PALETTE["teal"], fontsize=6.2)
    ax.text(0.42, 0.09, "dropped high-q95 edges", ha="center", color=PALETTE["gray"], fontsize=5.8)
    return records


def draw_insertion(ax) -> list[dict[str, object]]:
    setup_mechanism_axis(ax, "B  risk-value repair")
    records: list[dict[str, object]] = []
    xs = [0.16, 0.33, 0.50, 0.67, 0.84]
    before = ["i7", "i2", "gap", "i6", "i9"]
    after = ["i7", "i2", "i4", "i6", "i9"]
    risk = {"i7": 0.34, "i2": 0.72, "i4": 0.98, "i6": 0.52, "i9": 0.43}
    for y, labels, row in [(0.64, before, "destroy"), (0.25, after, "repair")]:
        for idx, (x, label) in enumerate(zip(xs, labels)):
            if idx < len(xs) - 1:
                draw_arrow(ax, (x + 0.045, y), (xs[idx + 1] - 0.045, y), color=PALETTE["gray"], lw=0.65)
            if label == "gap":
                rounded_box(ax, x - 0.045, y - 0.04, 0.09, 0.08, "gap", edge=PALETTE["coral"], face="white", fontsize=5.8, dashed=True)
                records.append({"panel": "B", "kind": "gap", "row": row, "x": x, "y": y})
            else:
                color = PALETTE["coral"] if label == "i4" else PALETTE["blue"]
                ax.scatter(x, y, s=45 + 55 * risk[label], color=color, edgecolor="white", lw=0.5, zorder=3)
                ax.text(x, y - 0.10, label, ha="center", va="top")
                records.append({"panel": "B", "kind": "tower", "row": row, "id": label, "x": x, "y": y, "risk_value": risk[label]})
    draw_arrow(ax, (0.50, 0.55), (0.50, 0.34), color=PALETTE["coral"], lw=1.0)
    ax.text(0.08, 0.76, "destroy", color=PALETTE["gray"], fontsize=5.8)
    ax.text(0.08, 0.37, "repair", color=PALETTE["gray"], fontsize=5.8)
    ax.text(
        0.68,
        0.91,
        r"$I=\Delta F+\beta_Q Q+\beta_W\Delta W-\beta_\psi\psi/(1+\hat C)$",
        ha="center",
        va="center",
        fontsize=5.8,
        color=PALETTE["dark"],
    )
    return records


def draw_reassignment(ax) -> list[dict[str, object]]:
    setup_mechanism_axis(ax, "C  stop-batch evaluator")
    records: list[dict[str, object]] = []
    old = (0.22, 0.72, "arrival")
    new = (0.22, 0.26, "ready")
    tower = (0.78, 0.50, "i5")
    other = [(0.76, 0.80, "i8"), (0.78, 0.22, "i3")]
    for x, y, label in [old, new]:
        ax.scatter(x, y, marker="^", s=82, color=PALETTE["teal"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(x, y - 0.11, label, ha="center", va="top", fontsize=5.7)
        records.append({"panel": "C", "kind": "stop", "id": label, "x": x, "y": y})
    for x, y, label in [tower, *other]:
        ax.scatter(x, y, s=74, color=PALETTE["orange"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(x + 0.045, y, label, ha="left", va="center")
        records.append({"panel": "C", "kind": "tower", "id": label, "x": x, "y": y})
    ax.plot([old[0], tower[0]], [old[1], tower[1]], ls="--", color=PALETTE["gray"], lw=0.9, alpha=0.45)
    ax.plot([new[0], tower[0]], [new[1], tower[1]], color=PALETTE["coral"], lw=1.25)
    draw_arrow(ax, (0.44, 0.65), (0.44, 0.40), color=PALETTE["coral"], lw=0.9)
    ax.text(0.58, 0.78, "sequence enters\nvehicle--UAV timing", ha="center", va="center", fontsize=5.8)
    ax.text(0.58, 0.12, r"accept if $\Delta F<0$ or SA", ha="center", va="center", fontsize=5.8, color=PALETTE["gray"])
    records.append({"panel": "C", "kind": "evaluation", "tower": "i5", "from": "arrival", "to": "ready"})
    return records


def setup_mechanism_axis(ax, title: str) -> None:
    ax.set_title(title, loc="left", pad=3, color=PALETTE["dark"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def rounded_box(ax, x, y, w, h, text, edge, face, fontsize=6.0, dashed=False) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.015,rounding_size=0.018",
        facecolor=face,
        edgecolor=edge,
        lw=0.8,
        linestyle="--" if dashed else "-",
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, color=edge)


def draw_arrow(ax, start, end, color=PALETTE["dark"], lw=0.8) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=7,
            lw=lw,
            color=color,
            shrinkA=1.5,
            shrinkB=1.5,
        )
    )


def read_summary(experiment_id: str) -> pd.DataFrame:
    path = EXPERIMENTS / experiment_id / "analysis_data" / f"{experiment_id}_{RUN_ID}_summary.csv"
    return pd.read_csv(path)


def label_panels(axes, x=-0.10, y=1.06) -> None:
    for label, ax in zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ", axes):
        ax.text(x, y, label, transform=ax.transAxes, weight="bold", fontsize=8.2, va="bottom", color=PALETTE["dark"])


def save_figure(fig: plt.Figure, stem: str, source: pd.DataFrame) -> None:
    base = OUT / stem
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=500, bbox_inches="tight")
    plt.close(fig)
    source.to_csv(OUT / f"{stem}_source.csv", index=False)
    shutil.copyfile(base.with_suffix(".pdf"), MANUSCRIPT_FIGS / f"{stem}.pdf")


def update_contact_sheet() -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return

    images = sorted(OUT.glob("Fig*.png"))
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
