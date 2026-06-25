from __future__ import annotations

import re
import textwrap
from pathlib import Path

import fitz
from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANUSCRIPT = PROJECT_ROOT / "manuscript_context"
OUT = PROJECT_ROOT / "results" / "analysis" / "render_submission_preview"
PDF = MANUSCRIPT / "paper_UQ_RV_ALNS_TRE_submission_preview.pdf"

PAGE_W, PAGE_H = 595, 842
MARGIN_X, MARGIN_Y = 54, 54
BODY_W = PAGE_W - 2 * MARGIN_X


class PdfWriter:
    def __init__(self) -> None:
        self.doc = fitz.open()
        self.page = None
        self.y = MARGIN_Y
        self.page_no = 0
        self.new_page()

    def new_page(self) -> None:
        self.page = self.doc.new_page(width=PAGE_W, height=PAGE_H)
        self.page_no += 1
        self.y = MARGIN_Y
        self.page.insert_text((MARGIN_X, 30), "Transportation Research Part E submission preview", fontsize=7, color=(0.35, 0.35, 0.35), fontname="helv")
        self.page.draw_line((MARGIN_X, 38), (PAGE_W - MARGIN_X, 38), color=(0.75, 0.75, 0.75), width=0.4)
        self.page.insert_text((PAGE_W - MARGIN_X - 28, PAGE_H - 30), str(self.page_no), fontsize=8, color=(0.35, 0.35, 0.35), fontname="helv")

    def ensure(self, height: float) -> None:
        if self.y + height > PAGE_H - MARGIN_Y:
            self.new_page()

    def heading(self, text: str, level: int) -> None:
        size = 15 if level == 1 else 12
        line_h = size * 1.25
        max_chars = max(34, int(BODY_W / (size * 0.55)))
        lines = textwrap.wrap(text, width=max_chars) or [text]
        gap = 10 if level == 1 else 8
        self.ensure(line_h * len(lines) + gap)
        self.y += 7 if self.y > MARGIN_Y else 0
        for line in lines:
            self.page.insert_text((MARGIN_X, self.y), line, fontsize=size, fontname="helv", color=(0.12, 0.22, 0.24))
            self.y += line_h
        self.y += gap

    def paragraph(self, text: str, size: float = 9.2) -> None:
        text = text.strip()
        if not text:
            self.y += 5
            return
        max_chars = max(42, int(BODY_W / (size * 0.48)))
        lines = []
        for chunk in text.split("\n"):
            lines.extend(textwrap.wrap(chunk, width=max_chars) or [""])
        line_h = size * 1.35
        self.ensure(line_h * len(lines) + 5)
        for line in lines:
            self.page.insert_text((MARGIN_X, self.y), line, fontsize=size, fontname="Times-Roman", color=(0.05, 0.05, 0.05))
            self.y += line_h
        self.y += 4

    def bullet(self, text: str) -> None:
        max_chars = int((BODY_W - 16) / (9.0 * 0.48))
        lines = textwrap.wrap(text, width=max_chars)
        line_h = 12.2
        self.ensure(line_h * len(lines) + 3)
        self.page.insert_text((MARGIN_X + 4, self.y), "-", fontsize=9, fontname="helv")
        for i, line in enumerate(lines):
            self.page.insert_text((MARGIN_X + 17, self.y), line, fontsize=9, fontname="Times-Roman")
            self.y += line_h
        self.y += 2

    def image(self, path: Path, caption: str) -> None:
        if not path.exists():
            return
        with Image.open(path) as img:
            ratio = img.height / img.width
        width = BODY_W
        height = min(width * ratio, 265)
        self.ensure(height + 36)
        rect = fitz.Rect(MARGIN_X, self.y, MARGIN_X + width, self.y + height)
        self.page.insert_image(rect, filename=str(path))
        self.y += height + 10
        self.paragraph(caption, size=8.2)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.doc.save(path, garbage=4, deflate=True)


def main() -> int:
    md = (MANUSCRIPT / "manuscript_draft.md").read_text(encoding="utf-8")
    writer = PdfWriter()
    for raw in md.splitlines():
        line = raw.strip()
        if line.startswith("# "):
            writer.heading(line[2:], 1)
        elif line.startswith("## "):
            writer.heading(line[3:], 1)
        elif line.startswith("### "):
            writer.heading(line[4:], 2)
        elif line.startswith("- "):
            writer.bullet(line[2:])
        elif line.startswith("!["):
            match = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            if match:
                caption, rel = match.groups()
                img = (MANUSCRIPT / rel).resolve()
                writer.image(img, caption)
        else:
            writer.paragraph(line)
    writer.save(PDF)
    render_pages(PDF)
    print(PDF)
    return 0


def render_pages(pdf: Path) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    pngs = []
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
        path = OUT / f"page-{i+1:02d}.png"
        pix.save(path)
        pngs.append(path)
    contact_sheet(pngs)


def contact_sheet(paths: list[Path]) -> None:
    thumbs = []
    for path in paths:
        img = Image.open(path).convert("RGB")
        img.thumbnail((290, 410))
        canvas = Image.new("RGB", (320, 460), "white")
        canvas.paste(img, ((320 - img.width) // 2, 18))
        draw = ImageDraw.Draw(canvas)
        draw.text((14, 432), path.stem, fill=(20, 20, 20))
        thumbs.append(canvas)
    cols = 3
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 320, rows * 460), "white")
    for i, thumb in enumerate(thumbs):
        sheet.paste(thumb, ((i % cols) * 320, (i // cols) * 460))
    sheet.save(OUT / "contact_sheet.png")


if __name__ == "__main__":
    raise SystemExit(main())
