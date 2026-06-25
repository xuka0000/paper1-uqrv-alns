# Delivery README

Date: 2026-06-13

This package is rebuilt from the 20260606 full manuscript delivery baseline. It is not based on the short draft. The current repair updates the paper for same-stop multi-tower UAV sorties, parallel dispatch at one stop, sequential recovered-UAV dispatch during a stop visit, the revised algorithm description, the latest experiment results and the reference-style redraw of non-experimental Figs. 1--3.

## Main Files

- `00_FINAL_PDFs/FINAL_paper1_single_column_review_version.pdf`
- `00_FINAL_PDFs/FINAL_paper1_published_style_journal_version.pdf`

The single-column review version has 28 pages. The published-style journal version has 29 pages after the 2026-06-13 reference-style redesign of Figs. 1--3.

## Highlighting

Main revised text is highlighted in blue through the `\rev{}` macro. The highlighted passages cover the abstract, keywords, revised assumptions, model interface, algorithm framework, non-experimental figure captions, key experiment interpretation and conclusion.

## Figure Policy

Figs. 1--3 were rebuilt on 2026-06-13 as PPT/Visio-style icon compositions using repeated open-source icons, line connectors, short labels, dashed candidate boxes and bottom legends:

- Fig. 1, route-service inspection network with candidate stops, tower-demand groups, assigned same-stop sortie patterns, support route, parallel dispatch and q95 status screening.
- Fig. 2, current route-service solution, candidate service list, grouped-pattern splitting and q95-feasible subpatterns.
- Fig. 3, two-row destroy--repair operator mechanism comparing risk-value reinsertion and random reinsertion.

Experimental data figures remain Python-generated and retain source CSV files beside the figure outputs.

## Verification

Fresh checks before packaging:

- `latexmk` with `D:\texlive\2022\bin\win32\latexmk.exe`, both manuscript versions OK.
- Final log scan, zero citation or undefined-reference warnings.
- Final page counts, 28 pages and 29 pages.
- Source scan found no remaining exact-one-tower sortie assumption phrases.
- Active source and PDF scans found no stale headline values from the previous benchmark table or previous abstract percentage-point statement.
- Rendered pages 5, 9 and 11 were visually inspected for the three reference-style non-experimental figures.

See `05_validation_notes/claim_evidence_manifest_multi_tower_highlight_20260613.md` and `05_validation_notes/figure_qa_manifest_20260613.md` for details.
