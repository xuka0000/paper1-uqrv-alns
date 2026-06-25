from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "results/figures/tre2style"
MANUSCRIPT_FIGS = PROJECT_ROOT / "manuscript_context" / "tre_published_style" / "figures"

PALETTE = {
    "pale_teal": "#BFDFD2",
    "teal": "#51999F",
    "blue": "#4198AC",
    "light_blue": "#7BC0CD",
    "gold": "#DDCB92",
    "orange": "#EA9E58",
    "coral": "#ED8D5A",
    "green": "#BFDFD2",
    "dark": "#26343B",
    "gray": "#6E7C7C",
    "light": "#BFDFD2",
    "pale": "#DDCB92",
    "grid": "#D9DEDD",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 6.7,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "figure.dpi": 180,
    }
)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    draw_framework()
    draw_mechanisms()
    print("Redrew Fig2_solution_framework and Fig8_algorithm_mechanism.")
    return 0


def save(fig: plt.Figure, stem: str, source_rows: list[dict[str, object]]) -> None:
    base = OUT / stem
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=500, bbox_inches="tight")
    plt.close(fig)
    pd.DataFrame(source_rows).to_csv(OUT / f"{stem}_source.csv", index=False)
    shutil.copyfile(base.with_suffix(".pdf"), MANUSCRIPT_FIGS / f"{stem}.pdf")


def arrow(ax, start, end, color=PALETTE["dark"], lw=0.8, rad=0.0, dashed=False) -> None:
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=7.5,
            lw=lw,
            color=color,
            linestyle="--" if dashed else "-",
            shrinkA=3,
            shrinkB=3,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def box(ax, x, y, w, h, title, body="", fc="white", ec=PALETTE["dark"], lw=0.75, fontsize=6.4) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.016,rounding_size=0.018",
        facecolor=fc,
        edgecolor=ec,
        lw=lw,
    )
    ax.add_patch(patch)
    ax.text(x + w / 2, y + h - 0.035, title, ha="center", va="top", weight="bold", fontsize=fontsize, color=PALETTE["dark"])
    if body:
        ax.text(x + w / 2, y + h / 2 - 0.015, body, ha="center", va="center", fontsize=fontsize - 0.3, color=PALETTE["dark"], linespacing=1.16)


def setup(ax) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axis("off")


def draw_framework() -> None:
    fig, ax = plt.subplots(figsize=(7.25, 3.35), constrained_layout=True)
    setup(ax)
    rows: list[dict[str, object]] = []

    ax.text(0.02, 0.96, "Probabilistic risk-value ALNS used in the manuscript experiments", weight="bold", fontsize=8.0, color=PALETTE["dark"])

    box(
        ax,
        0.03,
        0.66,
        0.16,
        0.18,
        "Inputs",
        r"$\mathcal{T},\mathcal{S},\omega,T$" + "\n" + r"$r_i,\nu_i,q_i,B_d,\rho$",
        fc=PALETTE["light"],
        ec=PALETTE["teal"],
    )
    rows.append({"panel": "framework", "module": "inputs"})

    stage1 = [
        (0.25, 0.66, 0.16, 0.18, "Energy surrogate", r"$(\mu,\sigma,\tau)=f_\theta(\cdot)$" + "\n" + "Eq. (6)"),
        (0.44, 0.66, 0.15, 0.18, "q95 filter", r"$Q=\mu+z_\epsilon\sigma$" + "\n" + "Eqs. (7)-(10)"),
        (0.62, 0.66, 0.16, 0.18, "Service graph", r"$G_F=(\mathcal{S},\mathcal{T},\mathcal{F})$" + "\n" + "Eq. (28)"),
    ]
    for item in stage1:
        box(ax, *item, fc=PALETTE["pale"], ec=PALETTE["orange"])
        rows.append({"panel": "framework", "module": item[4]})

    box(
        ax,
        0.83,
        0.66,
        0.14,
        0.18,
        "Initial state",
        r"$x=\{\Pi,a(i),s(i),C_i\}$" + "\n" + "Eq. (29)",
        fc=PALETTE["light"],
        ec=PALETTE["teal"],
    )
    rows.append({"panel": "framework", "module": "initial_state"})

    for x1, x2 in [(0.19, 0.25), (0.41, 0.44), (0.59, 0.62), (0.78, 0.83)]:
        arrow(ax, (x1, 0.75), (x2, 0.75))

    ax.text(0.43, 0.88, "Stage 1: construct a q95-feasible service layer", ha="center", fontsize=6.6, color=PALETTE["orange"], weight="bold")

    loop_y = 0.28
    loop = [
        (0.08, loop_y, 0.14, 0.18, "Destroy", r"$\Omega_i$ or $R_{ij}$" + "\n" + "Eqs. (30),(31)"),
        (0.29, loop_y, 0.14, 0.18, "Repair", r"$I(\cdot)$, regret" + "\n" + "Eqs. (32),(33)"),
        (0.50, loop_y, 0.14, 0.18, "Evaluate", "stop-batch\nstate"),
        (0.71, loop_y, 0.14, 0.18, "Accept/update", r"$P_\mathrm{acc}$, $\pi_h^k$" + "\n" + "Eqs. (34),(35)"),
    ]
    for item in loop:
        box(ax, *item, fc="white", ec=PALETTE["blue"])
        rows.append({"panel": "framework", "module": item[4]})

    arrow(ax, (0.90, 0.66), (0.78, 0.46), color=PALETTE["teal"], rad=-0.10)
    for x1, x2 in [(0.22, 0.29), (0.43, 0.50), (0.64, 0.71)]:
        arrow(ax, (x1, loop_y + 0.09), (x2, loop_y + 0.09), color=PALETTE["blue"])
    arrow(ax, (0.85, loop_y + 0.09), (0.08, loop_y + 0.09), color=PALETTE["gray"], rad=0.32, dashed=True)
    ax.text(0.46, 0.53, "Stage 2: repeat until iteration budget; evaluate Eq. (17), metrics Eqs. (37)-(39)", ha="center", fontsize=6.5, color=PALETTE["blue"], weight="bold")
    ax.text(0.52, 0.14, "accepted move -> update scores -> select next operator", ha="center", fontsize=6.0, color=PALETTE["gray"])

    box(ax, 0.82, 0.07, 0.15, 0.13, "Outputs", "best schedule\nsource diagnostics", fc=PALETTE["light"], ec=PALETTE["coral"])
    arrow(ax, (0.78, loop_y), (0.86, 0.20), color=PALETTE["coral"], rad=-0.18)
    rows.append({"panel": "framework", "module": "outputs"})

    save(fig, "Fig2_solution_framework", rows)


def draw_mechanisms() -> None:
    fig, axes = plt.subplots(1, 3, figsize=(7.25, 2.60), constrained_layout=True)
    rows: list[dict[str, object]] = []
    rows.extend(draw_screening(axes[0]))
    rows.extend(draw_repair(axes[1]))
    rows.extend(draw_stop_move(axes[2]))
    save(fig, "Fig8_algorithm_mechanism", rows)


def mechanism_axis(ax, title: str) -> None:
    setup(ax)
    ax.set_title(title, loc="left", pad=4, fontsize=7.2, weight="bold", color=PALETTE["dark"])


def draw_screening(ax) -> list[dict[str, object]]:
    mechanism_axis(ax, "A  q95 sortie set")
    rows: list[dict[str, object]] = []
    stops = [(0.18, 0.74, "s1"), (0.18, 0.50, "s2"), (0.18, 0.26, "s3")]
    towers = [(0.78, 0.80, "i1", 0.92), (0.78, 0.62, "i2", 0.58), (0.78, 0.42, "i3", 0.78), (0.78, 0.23, "i4", 0.45)]
    feasible = {("s1", "i1"), ("s1", "i2"), ("s2", "i2"), ("s2", "i3"), ("s3", "i3"), ("s3", "i4")}
    for sx, sy, sid in stops:
        ax.scatter(sx, sy, marker="^", s=76, color=PALETTE["teal"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(sx - 0.055, sy, sid, ha="right", va="center")
        rows.append({"panel": "A", "kind": "stop", "id": sid})
    for tx, ty, tid, rv in towers:
        ax.scatter(tx, ty, s=48 + 48 * rv, color=PALETTE["orange"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(tx + 0.045, ty, tid, ha="left", va="center")
        rows.append({"panel": "A", "kind": "tower", "id": tid, "risk_value": rv})
    for sx, sy, sid in stops:
        for tx, ty, tid, _ in towers:
            keep = (sid, tid) in feasible
            ax.plot(
                [sx, tx],
                [sy, ty],
                color=PALETTE["blue"] if keep else PALETTE["grid"],
                lw=0.85 if keep else 0.45,
                ls="-" if keep else "--",
                alpha=0.72 if keep else 0.35,
                zorder=1,
            )
            rows.append({"panel": "A", "kind": "edge", "stop": sid, "tower": tid, "kept": keep})
    ax.text(0.50, 0.92, r"$Q_{si}\leq B_d(1-\rho)$", ha="center", color=PALETTE["teal"], fontsize=6.4)
    ax.text(0.50, 0.09, "Eq. (10) keeps only feasible stop-tower edges", ha="center", color=PALETTE["gray"], fontsize=5.6)
    return rows


def draw_repair(ax) -> list[dict[str, object]]:
    mechanism_axis(ax, "B  destroy-repair scoring")
    rows: list[dict[str, object]] = []
    xs = [0.15, 0.32, 0.49, 0.66, 0.83]
    before = ["i7", "i2", "gap", "i6", "i9"]
    after = ["i7", "i2", "i4", "i6", "i9"]
    risk = {"i7": 0.34, "i2": 0.72, "i4": 0.98, "i6": 0.52, "i9": 0.43}
    for y, labels, row in [(0.62, before, "destroy"), (0.24, after, "repair")]:
        for idx, (x, label) in enumerate(zip(xs, labels)):
            if idx < len(xs) - 1:
                arrow(ax, (x + 0.045, y), (xs[idx + 1] - 0.045, y), color=PALETTE["gray"], lw=0.62)
            if label == "gap":
                box(ax, x - 0.045, y - 0.042, 0.09, 0.084, "gap", "", fc="white", ec=PALETTE["coral"], fontsize=5.7)
                rows.append({"panel": "B", "kind": "gap"})
            else:
                color = PALETTE["coral"] if label == "i4" else PALETTE["blue"]
                ax.scatter(x, y, s=45 + 55 * risk[label], color=color, edgecolor="white", lw=0.5, zorder=3)
                ax.text(x, y - 0.095, label, ha="center", va="top")
                rows.append({"panel": "B", "kind": "tower", "id": label, "row": row, "risk_value": risk[label]})
    arrow(ax, (0.49, 0.54), (0.49, 0.34), color=PALETTE["coral"], lw=1.0)
    ax.text(0.08, 0.75, r"remove: $\Omega_i,R_{ij}$", color=PALETTE["gray"], fontsize=5.8)
    ax.text(0.58, 0.88, r"$I=\Delta F+\beta_1Q+\beta_2\Delta W-\beta_3\psi/(1+\hat C)$", ha="center", fontsize=5.4)
    ax.text(0.58, 0.08, "Eqs. (30)-(33) connect destroy, risk-value insertion and regret", ha="center", color=PALETTE["gray"], fontsize=5.5)
    return rows


def draw_stop_move(ax) -> list[dict[str, object]]:
    mechanism_axis(ax, "C  stop-batch evaluator")
    rows: list[dict[str, object]] = []
    old = (0.22, 0.72, "arrival")
    new = (0.22, 0.28, "ready")
    tower = (0.78, 0.50, "i5")
    for x, y, label in [old, new]:
        ax.scatter(x, y, marker="^", s=82, color=PALETTE["teal"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(x, y - 0.10, label, ha="center", va="top", fontsize=5.7)
        rows.append({"panel": "C", "kind": "stop", "id": label})
    for x, y, label in [tower, (0.76, 0.80, "i8"), (0.78, 0.22, "i3")]:
        ax.scatter(x, y, s=74, color=PALETTE["orange"], edgecolor="white", lw=0.5, zorder=3)
        ax.text(x + 0.045, y, label, ha="left", va="center")
        rows.append({"panel": "C", "kind": "tower", "id": label})
    ax.plot([old[0], tower[0]], [old[1], tower[1]], ls="--", color=PALETTE["gray"], lw=0.9, alpha=0.45)
    ax.plot([new[0], tower[0]], [new[1], tower[1]], color=PALETTE["coral"], lw=1.25)
    arrow(ax, (0.45, 0.65), (0.45, 0.38), color=PALETTE["coral"], lw=0.9)
    ax.text(0.56, 0.75, "accepted sequence enters\nvehicle--UAV timing", ha="center", fontsize=5.6)
    ax.text(0.56, 0.11, "Evaluator computes support stop, launch time, recovery time and metrics", ha="center", color=PALETTE["gray"], fontsize=5.5)
    rows.append({"panel": "C", "kind": "evaluation", "tower": "i5", "from": "arrival", "to": "ready"})
    return rows


if __name__ == "__main__":
    raise SystemExit(main())
