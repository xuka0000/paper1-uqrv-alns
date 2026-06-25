# Figure QA Manifest

Date: 2026-06-13

## Tool Split

Non-experimental Figs. 1--3 were rebuilt as DOCX-reference PPT/Visio-style icon compositions. They are manuscript schematics rather than experimental data plots. The final manuscript uses high-resolution PNG files exported from the same icon, connector, label and legend grammar. Editable PPTX source files are retained beside the PNG/PDF assets.

Experimental figures remain Python-generated data figures with source CSV files retained beside each figure.

## Non-Experimental Figures

| Figure | Type | Tool | Final file | Editable source | Inserted page | QA verdict |
|---|---|---|---|---|---:|---|
| Fig. 1 | Route-service inspection network with tower-demand groups, assigned same-stop sorties and q95 status screening | PPTX/icon assembly | `figures/Fig0_network_construction_ai.png` | `Fig0_network_construction_ppt_icon_source.pptx` | 5 | PASS |
| Fig. 2 | Current route-service solution, candidate service list, splitting and q95-feasible subpatterns | PPTX/icon assembly | `figures/Fig2_solution_framework_ai.png` | `Fig2_solution_framework_ppt_icon_source.pptx` | 9 | PASS |
| Fig. 3 | Two-row destroy--repair operator mechanism with risk-value and random reinsertion | PPTX/icon assembly | `figures/Fig8_operator_mechanism_ai.png` | `Fig8_operator_mechanism_ppt_icon_source.pptx` | 11 | PASS |

QA checks completed for these figures:

- Figure type is non-experimental and the tool choice follows the client's latest instruction to use PPT/Visio-style icon composition.
- The DOCX reference figures were used for visual grammar only. Their customer/order content was not copied into the paper.
- Main labels are readable at final manuscript insertion size.
- Routes, dashed UAV sorties, candidate boxes, splitting arrows, red grouped-pattern labels, blue/green feasible labels and bottom legends are present.
- The editable source files contain movable icons, lines, boxes and text objects.
- Experimental data figures were not replaced by schematic images.

Rendered page previews inspected:

- `05_validation_notes/figure_pages_docx_reference_icon_20260613/published_page_5_fig1.png`
- `05_validation_notes/figure_pages_docx_reference_icon_20260613/published_page_9_fig2.png`
- `05_validation_notes/figure_pages_docx_reference_icon_20260613/published_page_11_fig3.png`
- `05_validation_notes/figure_pages_docx_reference_icon_20260613/submission_page_5_fig1.png`
- `05_validation_notes/figure_pages_docx_reference_icon_20260613/submission_page_9_fig2.png`
- `05_validation_notes/figure_pages_docx_reference_icon_20260613/submission_page_11_fig3.png`

## Experimental Data Figures

| Figure group | Type | Tool | Source trace |
|---|---|---|---|
| Algorithm comparison | Experimental data plot | Python and CSV | `figures/Fig4_algorithm_comparison_source.csv` |
| Energy-surrogate evidence | Experimental data plot | Python and CSV | `figures/Fig5_energy_surrogate_accuracy_source.csv` |
| Ablation | Experimental data plot | Python and CSV | `figures/Fig6_ablation_source.csv` |
| GIS case study | Experimental data plot | Python and CSV | `figures/Fig7_case_study_source.csv` |
| Scalability and screening | Experimental data plot | Python and CSV | `figures/Fig8_scalability_source.csv`, `figures/Fig9_candidate_screening_statistics_source.csv` |
| Sensitivity | Experimental data plot | Python and CSV | `figures/Fig10_sensitivity_source.csv` |

Verdict: PASS for the current requested figure workflow. Figs. 1--3 are DOCX-reference PPT/Visio-style icon schematics. Experimental data plots remain data-traceable.
