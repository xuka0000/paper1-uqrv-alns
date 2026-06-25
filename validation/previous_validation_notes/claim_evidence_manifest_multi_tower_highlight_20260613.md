# Claim-Evidence Manifest for Multi-Tower Highlight Repair

Date: 2026-06-13

Baseline source: 20260606 full delivery package copied into `08_rebuild_from_20260606/paper1_latest_full_package_20260606_highlight_repair_work`.

## Scope

This repair returns to the 20260606 full manuscript baseline and updates it for the revised same-stop multi-tower sortie assumptions. The delivered manuscript uses blue highlighting for the main revised passages.

## Claim And Evidence Ledger

| Claim or issue | Action mode | Manuscript locations | Code or data evidence | Validation |
|---|---|---|---|---|
| A UAV sortie may inspect multiple towers and return to the same stop. A recovered UAV may be dispatched again. | Model and text repair | `section3_stop_batch_model.tex`, assumptions and sortie-pattern set; Fig. 1 caption | `02_code/uqrv/energy.py`, `EnergyModel.estimate_sortie`; `02_code/tests/test_energy.py`, multi-tower sortie test | `py -3 -m unittest discover -s 02_code/tests -q`, 95 tests OK |
| One stop may dispatch multiple UAVs in parallel and one UAV may run sequential sorties while the vehicle remains parked. | Model and algorithm repair | `section3_stop_batch_model.tex`, timing constraints and notation; Algorithm 1 | `02_code/uqrv/solvers.py`, `PlanSortie`, `_schedule_tasks_and_sorties`, `_select_metric_aware_schedule` | unittest suite OK; old exact-one-tower phrases scanned absent |
| The algorithm is a two-stage q95 sortie-pattern service-set construction plus risk-value ALNS scheduler. | Algorithm rewrite and figure redraw | `full_body.tex`, Section 4; Algorithm 1; Figs. 2 and 3 | `02_code/uqrv/solvers.py`, `solve`, `_solve_operator_alns`, destroy/repair/operator-weight functions | LaTeX compile OK; Fig. 2 and Fig. 3 PDF-page render QA PASS |
| Abstract and conclusion numerical claims are bounded to the latest evidence. | Claim repair | `tre_submission_current.tex` abstract and keywords; `tre_published_style.tex` abstract; `full_body.tex` conclusion | Latest run id `multi_tower_repair2_full_20260612`; source CSVs under `03_experiments/*/analysis_data` and manuscript source CSVs under `figures/*_source.csv` | Result-table values cross-linked in `generated_tables.tex` and individual `table_*.tex` |
| Experiment sections include full tables and richer result interpretation. | Result narration repair | `full_body.tex`, Section 6; `generated_tables.tex`; `table_*.tex` | P1 to P8 latest summary CSVs with run id `multi_tower_repair2_full_20260612`; P9 and P11 latest repair summaries where used | LaTeX compile OK; logs have zero citation or undefined-reference warnings |
| Non-experimental figures should follow the DOCX client reference style. Figs. 1--3 should use PPT/Visio-style icon compositions rather than whole-image AI redraws. | Figure repair | Figs. 1 to 3 in final PDF | Figs. 1--3 use `Fig0_network_construction_ai.png`, `Fig2_solution_framework_ai.png` and `Fig8_operator_mechanism_ai.png` exported from PPTX/icon source files: `Fig0_network_construction_ppt_icon_source.pptx`, `Fig2_solution_framework_ppt_icon_source.pptx` and `Fig8_operator_mechanism_ppt_icon_source.pptx` | Page renders inspected for pages 5, 9 and 11; all three non-experimental figures were rebuilt with repeated icons, route arrows, dashed same-stop UAV sorties or operator transitions, grouped-pattern tags, feasible-pattern tags, dashed candidate boxes and bottom legends; figure QA manifest PASS |
| Experimental result figures remain data-traceable. | Figure-source retention | Existing experimental figure files in `figures/` | Source CSVs retained beside the plotted PDF/PNG files, for example `Fig4_algorithm_comparison_source.csv` and `Fig10_sensitivity_source.csv` | Python-generated data figures retained; no image-model redraw used for experimental plots |
| Final delivery package must be refreshed after figure and text edits. | Package refresh | `07_delivery/paper1_full_20260606_based_highlighted_multi_tower_delivery_20260613_133222_docx_reference_icon_figs_clean` | Active manuscript source directories and validation notes copied after the DOCX-reference PPT/icon Figs. 1--3 redraw | ZIP `paper1_full_20260606_based_highlighted_multi_tower_delivery_20260613_133222_docx_reference_icon_figs_clean.zip`; final SHA256 is stored in the external `.sha256.txt` sidecar |

## Verification Commands

```powershell
py -3 -m unittest discover -s 02_code/tests -q
```

Result: 95 tests ran and passed.

```powershell
& 'D:\texlive\2022\bin\win32\latexmk.exe' -pdf -interaction=nonstopmode -halt-on-error -silent tre_submission_current.tex
& 'D:\texlive\2022\bin\win32\latexmk.exe' -pdf -interaction=nonstopmode -halt-on-error -silent tre_published_style.tex
```

Result: both LaTeX builds returned exit code 0.

Final PDF status:

| Version | PDF | Pages | Log warnings checked |
|---|---|---:|---:|
| Single-column review version | `tre_submission_current.pdf` | 28 | 0 |
| Published-style journal version | `tre_published_style.pdf` | 29 | 0 |

Keyword scan:

The latest manuscript source was scanned for stale single-tower-only assumption phrases, including exact-one-tower and one-tower-per-sortie wording.

Result: no remaining hits in the latest manuscript source.

## Known Validation Boundary

The optional bridge script `check_claim_evidence_gate.ps1` was not available in the project parent folders, `D:\鍗氬＋鐮旂┒鐢焋, `D:\` or the local `.codex` directory. The delivery therefore uses this manifest plus LaTeX builds, log scans, source keyword scans, PDF text extraction and rendered figure-page QA as the local evidence gate.


