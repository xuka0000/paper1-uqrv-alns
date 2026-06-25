# Elsevier submission LaTeX package

Main file: `tre_submission_current.tex`.

This package follows the official `elsarticle` template style supplied in
`elsarticle (2).zip` and uses the current full manuscript body from the
published-style review version. It is the handoff submission source, while
`01_latex_published_style_current/` remains the full visual review version.

Build command:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
bibtex tre_submission_current
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
```
