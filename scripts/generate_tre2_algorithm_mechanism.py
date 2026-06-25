from __future__ import annotations

import shutil
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.patches import FancyArrowPatch, Rectangle


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / "results/figures/tre2style"
MANUSCRIPT_FIGS = PROJECT_ROOT / "manuscript_context" / "tre_published_style" / "figures"

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

mpl.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans", "sans-serif"],
        "svg.fonttype": "none",
        "pdf.fonttype": 42,
        "font.size": 7.0,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.spines.left": False,
        "axes.spines.bottom": False,
        "xtick.labelsize": 6.2,
        "ytick.labelsize": 6.2,
        "figure.dpi": 180,
    }
)


def arrow(ax, xy1, xy2, color=PALETTE["dark"], lw=0.8, style="-", mutation=8):
    patch = FancyArrowPatch(
        xy1,
        xy2,
        arrowstyle="-|>",
        mutation_scale=mutation,
        lw=lw,
        linestyle=style,
        color=color,
        shrinkA=2,
        shrinkB=2,
    )
    ax.add_patch(patch)
    return patch


def setup_axis(ax, title: str) -> None:
    ax.set_title(title, loc="left", pad=3, fontsize=7.8, color=PALETTE["dark"])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_xticks([])
    ax.set_yticks([])


def draw_screening_panel(ax) -> list[dict[str, object]]:
    setup_axis(ax, "A  Probabilistic sortie-pattern screening")
    records: list[dict[str, object]] = []
    stops = [(0.14, 0.73, "s1"), (0.14, 0.48, "s2"), (0.14, 0.23, "s3")]
    towers = [(0.78, 0.80, "i1", 0.82), (0.78, 0.61, "i2", 0.48), (0.78, 0.42, "i3", 0.70), (0.78, 0.23, "i4", 0.38)]
    feasible = {("s1", "i1"), ("s1", "i2"), ("s2", "i2"), ("s2", "i3"), ("s3", "i3"), ("s3", "i4")}

    for x, y, label in stops:
        ax.scatter(x, y, marker="^", s=95, color=PALETTE["teal"], edgecolor="white", linewidth=0.5, zorder=4)
        ax.text(x - 0.04, y - 0.11, label, ha="center", va="top", color=PALETTE["dark"])
        records.append({"panel": "A", "type": "stop", "id": label, "x": x, "y": y})
    for x, y, label, risk_value in towers:
        ax.scatter(x, y, s=80 + 45 * risk_value, color=PALETTE["orange"], edgecolor="white", linewidth=0.5, zorder=4)
        ax.text(x + 0.04, y, label, va="center", color=PALETTE["dark"])
        records.append({"panel": "A", "type": "tower", "id": label, "x": x, "y": y, "risk_value": risk_value})

    for sx, sy, slabel in stops:
        for tx, ty, tlabel, _ in towers:
            is_feasible = (slabel, tlabel) in feasible
            color = PALETTE["blue_teal"] if is_feasible else PALETTE["light_gray"]
            alpha = 0.62 if is_feasible else 0.28
            ax.plot([sx, tx], [sy, ty], color=color, lw=0.8 if is_feasible else 0.45, alpha=alpha, ls="--", zorder=1)
            records.append({"panel": "A", "type": "pair", "stop": slabel, "tower": tlabel, "feasible": is_feasible})
    ax.text(0.37, 0.92, r"keep: $Q_{si}\leq B_d(1-\rho)$", color=PALETTE["teal"], ha="center")
    ax.text(0.48, 0.08, "screen out high-q95 edges", color=PALETTE["gray"], ha="center")
    ax.text(0.44, 0.29, "x", color=PALETTE["coral"], fontsize=13, weight="bold", ha="center", va="center")
    return records


def draw_insertion_panel(ax) -> list[dict[str, object]]:
    setup_axis(ax, "B  Risk-value insertion after destroy")
    records: list[dict[str, object]] = []
    before_x = [0.13, 0.29, 0.45, 0.61, 0.77]
    before_labels = ["i7", "i2", "gap", "i6", "i9"]
    after_labels = ["i7", "i2", "i4", "i6", "i9"]
    risk = {"i7": 0.35, "i2": 0.72, "i4": 0.96, "i6": 0.54, "i9": 0.42}

    ax.text(0.05, 0.76, "destroyed sequence", ha="left", va="center", color=PALETTE["gray"])
    ax.text(0.05, 0.32, "after insertion", ha="left", va="center", color=PALETTE["gray"])

    for row_y, labels, row_name in [(0.64, before_labels, "before"), (0.22, after_labels, "after")]:
        for idx, (x, label) in enumerate(zip(before_x, labels)):
            if label == "gap":
                rect = Rectangle((x - 0.045, row_y - 0.04), 0.09, 0.08, facecolor="white", edgecolor=PALETTE["coral"], lw=0.9, ls="--")
                ax.add_patch(rect)
                ax.text(x, row_y, "gap", ha="center", va="center", color=PALETTE["coral"])
                records.append({"panel": "B", "row": row_name, "type": "gap", "x": x, "y": row_y})
            else:
                size = 80 + 70 * risk[label]
                color = PALETTE["coral"] if label == "i4" else PALETTE["blue_teal"]
                ax.scatter(x, row_y, s=size, color=color, edgecolor="white", linewidth=0.5, zorder=3)
                ax.text(x, row_y - 0.105, label, ha="center", va="top", color=PALETTE["dark"])
                records.append({"panel": "B", "row": row_name, "type": "tower", "id": label, "x": x, "y": row_y, "risk_value": risk[label]})
            if idx < len(before_x) - 1:
                arrow(ax, (x + 0.055, row_y), (before_x[idx + 1] - 0.055, row_y), color=PALETTE["gray"], lw=0.65, mutation=6)

    arrow(ax, (0.45, 0.56), (0.45, 0.31), color=PALETTE["coral"], lw=1.0)
    ax.text(
        0.86,
        0.48,
        "score:\nrisk-value\n+ regret\n+ energy margin",
        ha="center",
        va="center",
        color=PALETTE["dark"],
        linespacing=1.15,
        bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "none", "alpha": 0.88},
    )
    return records


def draw_reassignment_panel(ax) -> list[dict[str, object]]:
    setup_axis(ax, "C  Stop-batch evaluator")
    records: list[dict[str, object]] = []
    s_old = (0.18, 0.72, "arrival")
    s_new = (0.21, 0.28, "ready")
    towers = [(0.70, 0.77, "i8"), (0.67, 0.52, "i5"), (0.72, 0.28, "i3")]

    for x, y, label in [s_old, s_new]:
        ax.scatter(x, y, marker="^", s=110, color=PALETTE["teal"], edgecolor="white", linewidth=0.5, zorder=4)
        ax.text(x, y - 0.12, label, ha="center", va="top", color=PALETTE["dark"])
        records.append({"panel": "C", "type": "stop", "id": label, "x": x, "y": y})
    for x, y, label in towers:
        ax.scatter(x, y, s=95, color=PALETTE["orange"], edgecolor="white", linewidth=0.5, zorder=4)
        ax.text(x + 0.04, y, label, va="center", color=PALETTE["dark"])
        records.append({"panel": "C", "type": "tower", "id": label, "x": x, "y": y})

    ax.plot([s_old[0], towers[1][0]], [s_old[1], towers[1][1]], ls="--", color=PALETTE["light_gray"], lw=1.0, label="arrival state")
    ax.plot([s_new[0], towers[1][0]], [s_new[1], towers[1][1]], color=PALETTE["coral"], lw=1.2, label="ready state")
    arrow(ax, (0.42, 0.64), (0.42, 0.43), color=PALETTE["coral"], lw=0.9)
    ax.text(
        0.56,
        0.70,
        "accepted sequence\nenters timing",
        ha="center",
        va="center",
        color=PALETTE["dark"],
        linespacing=1.15,
        bbox={"boxstyle": "round,pad=0.18", "fc": "white", "ec": "none", "alpha": 0.88},
    )
    ax.text(0.72, 0.10, r"accept if $\Delta F<0$ or SA accepts", ha="center", va="center", color=PALETTE["gray"])
    records.append({"panel": "C", "type": "evaluation", "tower": "i5", "from": "arrival", "to": "ready"})
    return records


def update_contact_sheet() -> None:
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return

    images = sorted(OUT.glob("Fig*_*.png"))
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


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    MANUSCRIPT_FIGS.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.55), constrained_layout=True)
    source_rows = []
    source_rows.extend(draw_screening_panel(axes[0]))
    source_rows.extend(draw_insertion_panel(axes[1]))
    source_rows.extend(draw_reassignment_panel(axes[2]))

    base = OUT / "Fig8_algorithm_mechanism"
    fig.savefig(base.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(base.with_suffix(".png"), dpi=450, bbox_inches="tight")
    plt.close(fig)

    pd.DataFrame(source_rows).to_csv(OUT / "Fig8_algorithm_mechanism_source.csv", index=False)
    shutil.copyfile(base.with_suffix(".pdf"), MANUSCRIPT_FIGS / "Fig8_algorithm_mechanism.pdf")
    update_contact_sheet()
    print(f"Wrote {base.with_suffix('.pdf')}")
    print(f"Copied manuscript figure to {MANUSCRIPT_FIGS / 'Fig8_algorithm_mechanism.pdf'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
