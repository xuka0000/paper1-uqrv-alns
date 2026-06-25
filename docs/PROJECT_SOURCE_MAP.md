# Project Source Map

This file records how the previous by-section delivery package was converted
into the current standard research-code layout.

## Source Delivery Package

Root source:

`..\00_CURRENT_PRE_6_24\07_delivery\paper1_colleague_pdf_latex_paired_delivery_20260613_234820\`

## Standard Layout Mapping

| Current path | Source path | Purpose |
| --- | --- | --- |
| `src/uqrv/` | `05_experiment_reproduction_by_section\00_common_full_code_snapshot\02_code\uqrv\` | Single shared Python package. |
| `scripts/` | `05_experiment_reproduction_by_section\00_common_full_code_snapshot\02_code\scripts\` | Shared reproduction, plotting, and manuscript scripts. |
| `scripts/project_figures/` | `05_experiment_reproduction_by_section\00_common_full_code_snapshot\project_level_figure_scripts\` | Project-level figure builders. |
| `tests/` | `05_experiment_reproduction_by_section\00_common_full_code_snapshot\02_code\tests\` | Shared test suite. |
| `results/experiments/` | `05_experiment_reproduction_by_section\00_common_full_code_snapshot\03_experiments\` plus unique by-section experiment records | Experiment outputs grouped by experiment id, not manuscript subsection. |
| `results/tables/` | By-section `results\tables\` folders | Manuscript result tables consolidated into one table directory. |
| `results/figures/` | By-section `plotting\figures\` folders | Rendered figures and figure source data consolidated by artifact type. |
| `results/consolidated_tables/` | `04_results_excel_and_csv\` | CSV/XLSX tables for direct inspection. |
| `manuscript_context/` | `00_CURRENT_PRE_6_24\01_manuscript\` copied via the previous common snapshot | LaTeX files required by manuscript-output tests and generators. |
| `validation/` | `06_validation_and_manifest\` | Validation notes and delivery manifests. |
| `metadata/` | `FILE_MANIFEST.csv`, `SHA256_ZIP.txt`, original by-section README | Source package traceability. |

## Reorganization Notes

- The old `6_*` result-subsection directories were intentionally replaced.
- Duplicate `code\02_code` copies from each subsection were removed in favor of
  the single `src/uqrv`, `scripts`, and `tests` layout.
- Script outputs now target `results/experiments/` instead of
  `03_experiments/`.
- Manuscript-support paths now target `manuscript_context/` instead of
  `01_manuscript/`.

## Verification Target

```powershell
.\RUN_TESTS.ps1
```

Expected result:

```text
Ran 95 tests
OK
```
