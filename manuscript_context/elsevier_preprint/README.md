# Elsevier LaTeX Draft

Generated from `02_code/scripts/write_elsevier_latex.py`.

- Main file: `tre_manuscript_preprint.tex`
- Document class: `\documentclass[preprint,12pt,number]{elsarticle}`
- Figure source: `04_manuscript_figures_publishable/`
- Experiment run: `multi_tower_repair2_full_20260612`
- Revision markup: blue text marks passages revised for same-stop multi-tower sorties, repeated dispatch, portfolio selection, and repair2 evidence boundaries.

Compile on this machine with:

```powershell
$env:PATH = 'D:\texlive\2022\bin\win32;' + $env:PATH
latexmk -xelatex -interaction=nonstopmode -halt-on-error tre_manuscript_preprint.tex
```

Evidence boundary: all results are currently simulation-based unless real utility inspection logs are added later.
