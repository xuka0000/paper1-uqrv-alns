from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Circle, FancyArrowPatch, FancyBboxPatch, Polygon, Rectangle


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
    "road": "#D9DEDD",
    "water": "#7BC0CD",
    "pale": "#DDCB92",
}

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 6.7,
        "figure.dpi": 180,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
    }
)


def main() -> int:
    print(
        "Fig0_inspection_system_scene is a non-experimental schematic. "
        "Do not regenerate it with Python; use the Image Gen prompt recorded "
        "in the final LaTeX package under figure_prompts/."
    )
    return 0

    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.25, 3.25), constrained_layout=True)
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 52)
    ax.axis("off")
    rows: list[dict[str, object]] = []

    draw_background(ax)
    rows.extend(draw_corridor(ax))
    rows.extend(draw_support_layer(ax))
    draw_weather_and_energy(ax)
    draw_legend(ax)

    ax.text(2, 49.2, "Transmission-line inspection scheduling setting", weight="bold", fontsize=8.6, color=PALETTE["dark"])
    ax.text(
        2,
        46.6,
        "road-access stops and crew vehicle support chance-feasible UAV sorties for risk-value tower inspections",
        fontsize=6.3,
        color=PALETTE["gray"],
    )

    base = OUT / "Fig0_inspection_system_scene"
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=500, bbox_inches="tight")
    plt.close(fig)
    pd.DataFrame(rows).to_csv(OUT / "Fig0_inspection_system_scene_source.csv", index=False)
    shutil.copyfile(base.with_suffix(".pdf"), MANUSCRIPT_FIGS / "Fig0_inspection_system_scene.pdf")
    print(f"Wrote {base.with_suffix('.pdf')}")
    return 0


def draw_background(ax) -> None:
    ax.add_patch(Rectangle((0, 0), 100, 52, facecolor="white", edgecolor="none"))
    hills = Polygon(
        [(0, 13), (10, 17), (24, 14), (38, 19), (53, 15), (69, 20), (84, 16), (100, 18), (100, 0), (0, 0)],
        closed=True,
        facecolor="#F3F1EA",
        edgecolor="none",
        zorder=0,
    )
    ax.add_patch(hills)
    ax.plot([0, 12, 25, 40, 55, 70, 85, 100], [8, 12, 9, 14, 10, 16, 12, 15], color=PALETTE["water"], lw=11, alpha=0.75, zorder=0)
    road_x = np.array([3, 16, 28, 41, 55, 72, 90, 98])
    road_y = np.array([11, 14, 12, 17, 15, 21, 19, 23])
    ax.plot(road_x, road_y, color=PALETTE["road"], lw=6.5, solid_capstyle="round", zorder=1)
    ax.plot(road_x, road_y, color="white", lw=1.1, alpha=0.9, ls="--", zorder=2)


def draw_corridor(ax) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    xs = np.array([9, 20, 31, 42, 54, 66, 78, 90])
    ys = np.array([31, 35, 33, 38, 34, 39, 36, 41])
    risk = np.array([0.35, 0.52, 0.82, 0.46, 0.92, 0.58, 0.76, 0.41])
    ax.plot(xs, ys, color=PALETTE["dark"], lw=1.2, alpha=0.72, zorder=3)
    for idx, (x, y, r) in enumerate(zip(xs, ys, risk), start=1):
        draw_tower(ax, x, y, r)
        rows.append({"kind": "tower", "id": f"i{idx}", "x": x, "y": y, "risk_value": r})
    ax.text(82, 44.5, "transmission corridor", fontsize=6.0, color=PALETTE["dark"])
    return rows


def draw_support_layer(ax) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    stops = [(12, 14, "s1"), (36, 17, "s2"), (63, 20, "s3"), (88, 20, "s4")]
    towers = [(20, 35, "i2"), (31, 33, "i3"), (54, 34, "i5"), (78, 36, "i7")]
    for x, y, label in stops:
        ax.scatter(x, y, marker="^", s=74, color=PALETTE["teal"], edgecolor="white", lw=0.6, zorder=6)
        ax.text(x, y - 3.0, label, ha="center", fontsize=5.8, color=PALETTE["dark"])
        rows.append({"kind": "candidate_stop", "id": label, "x": x, "y": y})

    route = [(4, 11), (12, 14), (36, 17), (63, 20), (88, 20)]
    ax.plot([p[0] for p in route], [p[1] for p in route], color=PALETTE["coral"], lw=1.8, zorder=4)
    for a, b in zip(route[:-1], route[1:]):
        arrow(ax, a, b, color=PALETTE["coral"], lw=1.0)
    draw_vehicle(ax, 4.5, 11.3)
    ax.text(2.2, 7.3, "depot / crew vehicle", fontsize=5.8, color=PALETTE["dark"])
    rows.append({"kind": "vehicle_route", "id": "route"})

    for stop, tower in zip(stops, towers):
        sx, sy, _ = stop
        tx, ty, tid = tower
        ax.plot([sx, tx], [sy, ty], color=PALETTE["blue"], lw=1.0, ls="--", alpha=0.78, zorder=4)
        draw_drone(ax, (sx + tx) / 2, (sy + ty) / 2 + 1.2)
        rows.append({"kind": "uav_sortie", "tower": tid, "stop": stop[2]})

    callout(ax, 66, 6.2, 28, 7.0, "schedule decision", r"$x=\{\Pi,a(i),s(i),C_i\}$" + "\nvehicle route + UAV sorties + completion times")
    return rows


def draw_weather_and_energy(ax) -> None:
    for x in [60, 68, 76]:
        arrow(ax, (x, 47), (x + 7, 42), color=PALETTE["gray"], lw=0.9)
    ax.text(58, 48.0, "wind / weather", fontsize=6.0, color=PALETTE["gray"])
    callout(ax, 5, 38.5, 28, 6.0, "energy screening", r"$Q_{si}=\mu_{si}+z_\epsilon\sigma_{si}\leq B_d(1-\rho)$")
    callout(ax, 38, 40.0, 25, 5.8, "risk-value priority", r"$\psi_i=r_i\nu_i$; early service lowers RWCT")


def draw_tower(ax, x, y, risk_value) -> None:
    ax.plot([x, x], [y - 5.2, y], color=PALETTE["dark"], lw=1.0, zorder=4)
    ax.plot([x - 2.0, x, x + 2.0], [y - 2.4, y - 0.8, y - 2.4], color=PALETTE["dark"], lw=0.8, zorder=4)
    ax.plot([x - 2.7, x + 2.7], [y - 1.6, y - 1.6], color=PALETTE["dark"], lw=0.8, zorder=4)
    color = mpl.colormaps["YlOrRd"](0.22 + 0.72 * risk_value)
    ax.add_patch(Circle((x, y + 1.3), 1.25, facecolor=color, edgecolor="white", lw=0.55, zorder=5))


def draw_vehicle(ax, x, y) -> None:
    ax.add_patch(Rectangle((x - 2.2, y - 0.9), 4.4, 1.8, facecolor=PALETTE["coral"], edgecolor=PALETTE["dark"], lw=0.55, zorder=6))
    ax.add_patch(Rectangle((x - 0.4, y + 0.1), 1.5, 0.75, facecolor="#F5D6C8", edgecolor="none", zorder=7))
    ax.add_patch(Circle((x - 1.35, y - 1.0), 0.45, facecolor=PALETTE["dark"], edgecolor="none", zorder=7))
    ax.add_patch(Circle((x + 1.35, y - 1.0), 0.45, facecolor=PALETTE["dark"], edgecolor="none", zorder=7))


def draw_drone(ax, x, y) -> None:
    ax.plot([x - 1.2, x + 1.2], [y, y], color=PALETTE["dark"], lw=0.8, zorder=7)
    ax.plot([x, x], [y - 1.0, y + 1.0], color=PALETTE["dark"], lw=0.8, zorder=7)
    ax.add_patch(Circle((x, y), 0.35, facecolor=PALETTE["dark"], edgecolor="none", zorder=8))
    for dx, dy in [(-1.2, 0), (1.2, 0), (0, -1.0), (0, 1.0)]:
        ax.add_patch(Circle((x + dx, y + dy), 0.42, facecolor="none", edgecolor=PALETTE["dark"], lw=0.55, zorder=8))


def arrow(ax, start, end, color=PALETTE["dark"], lw=0.8) -> None:
    ax.add_patch(
        FancyArrowPatch(start, end, arrowstyle="-|>", mutation_scale=7, lw=lw, color=color, shrinkA=2, shrinkB=2, zorder=5)
    )


def callout(ax, x, y, w, h, title, body) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.016,rounding_size=0.018",
        facecolor="white",
        edgecolor=PALETTE["grid"] if "grid" in PALETTE else PALETTE["gray"],
        lw=0.65,
        alpha=0.96,
        zorder=9,
    )
    ax.add_patch(patch)
    ax.text(x + 1.2, y + h - 1.4, title, ha="left", va="top", fontsize=6.1, weight="bold", color=PALETTE["dark"], zorder=10)
    ax.text(x + 1.2, y + h / 2 - 0.8, body, ha="left", va="center", fontsize=5.7, color=PALETTE["dark"], linespacing=1.15, zorder=10)


def draw_legend(ax) -> None:
    x0, y0 = 4, 2.5
    ax.add_patch(Rectangle((x0 - 1.2, y0 - 1.2), 44, 4.7, facecolor="white", edgecolor=PALETTE["road"], lw=0.5, alpha=0.94, zorder=9))
    ax.add_patch(Circle((x0 + 2, y0 + 2.2), 1.05, facecolor=mpl.colormaps["YlOrRd"](0.78), edgecolor="white", lw=0.55, zorder=10))
    ax.text(x0 + 5, y0 + 2.1, "tower color = risk-value", fontsize=5.6, va="center", zorder=10)
    ax.scatter(x0 + 20, y0 + 2.1, marker="^", s=56, color=PALETTE["teal"], edgecolor="white", lw=0.5, zorder=10)
    ax.text(x0 + 22, y0 + 2.1, "candidate stop", fontsize=5.6, va="center", zorder=10)
    ax.plot([x0 + 33, x0 + 37], [y0 + 2.1, y0 + 2.1], color=PALETTE["blue"], lw=1.0, ls="--", zorder=10)
    ax.text(x0 + 38, y0 + 2.1, "UAV sortie", fontsize=5.6, va="center", zorder=10)


if __name__ == "__main__":
    raise SystemExit(main())
