# Section 6 Result-Data Audit

Date: 2026-06-13

Audit target: `paper1_published_style_journal_version.pdf`, Computational experiments and Results and analysis.

## Verdict

The synthetic scheduling, algorithm-comparison, ablation, screening, sensitivity and stress-test results now trace to the modified-assumption result files. The core run identifier is `multi_tower_repair2_full_20260612` for P1 to P8. The stress block uses `repair_stress_repair2_20260612`. The public GIS block uses `repair2_20260612` region summaries and includes multi-tower sortie fields. The AirLab block is external energy-calibration evidence from public quadcopter telemetry and is not a route-scheduling rerun. It is used only to support the energy-prediction interface.

After the 2026-06-13 non-experimental figure redraw, the active single-column and published-style LaTeX trees were rescanned. The active manuscript sources and the rebuilt PDFs do not contain the stale headline values from the previous 100-tower and 500-tower benchmark table or the previous abstract top-risk-coverage statement. Those stale values remain only in historical experiment-code README files and older manuscript snapshots kept under the reproducible-code archive. They are not referenced by the active manuscript PDFs or by the curated delivery folders.

## Result Source Map

| Manuscript block | Source data | Modified-assumption status |
|---|---|---|
| Small reference | `P1_milp_exact_small_multi_tower_repair2_full_20260612_summary.csv` | Yes |
| Algorithm comparison | `P2_algorithm_comparison_multi_tower_repair2_full_20260612_summary.csv` and P7 matched tests | Yes |
| Energy-prediction simulation | `P3_pinn_prediction_accuracy_multi_tower_repair2_full_20260612_summary.csv` | Yes for scheduler-facing simulation |
| AirLab calibration | `P10_energy_telemetry_calibration_airlab_energy_calibration_stop_batch_20260606_summary.csv` | External telemetry calibration only |
| Ablation | `P4_ablation_multi_tower_repair2_full_20260612_summary.csv` | Yes |
| Stress tests | `P11_repair_stress_repair_stress_repair2_20260612_summary.csv` | Yes |
| Public GIS cases | `P9_real_gis_case_public_*_repair2_20260612_summary.csv` | Yes for solver metrics, with public geometry and proxy risk/value labels |
| Scalability and screening | `P6_candidate_stop_screening_multi_tower_repair2_full_20260612_summary.csv` | Yes |
| Sensitivity | `P8_sensitivity_multi_tower_repair2_full_20260612_summary.csv` | Yes |

## Corrections Made During Audit

- Replaced stale algorithm-result tables and experimental figures with the `multi_tower_repair2_full_20260612` values.
- Updated the 100-tower result text to 43.14 percent RWCT reduction over fixed ALNS and 26.77 percent over nearest dispatch.
- Updated the 500-tower result text to 41.95 percent RWCT reduction over fixed ALNS and 17.15 percent over nearest dispatch.
- Updated abstract top-risk coverage text from the stale percentage-point statement to 72.0 percentage points on the 100-tower benchmark.
- Removed duplicate result-summary tables from `generated_tables.tex` so that result labels resolve only to the full Section 6 and 7 tables.
- Recompiled both manuscript versions with zero citation, undefined-reference or duplicate-label warnings.

## Fresh Verification

Direct PDF extraction from the published-style version confirms:

- Present: `705.81`, `3594.58`, `43.14%`, `41.95%`.
- Absent: the previous 100-tower proposed RWCT, previous 500-tower proposed RWCT and previous abstract percentage-point statement.

Direct PDF extraction after the figure redraw confirms for both active PDFs:

- Present: `705.81`, `3594.58`, `43.1%`, `42.0%`, `43.14%`, `41.95%`, `72.0 percentage`.
- Absent: the previous 100-tower proposed RWCT, previous 500-tower proposed RWCT, previous abstract percentage-point statement and the old fixed-ALNS reduction percentages.

Focused source scan after the figure redraw:

| Scope | Stale-value result |
|---|---|
| Active single-column LaTeX tree | No hits |
| Active published-style LaTeX tree | No hits |
| Reproducible-code historical archive | Old run README and old manuscript snapshots still contain historical values, kept only as archive material |

Final compile status:

| Version | Pages | Log warnings |
|---|---:|---:|
| Single-column review version | 28 | 0 citation/reference/undefined warnings |
| Published-style journal version | 28 | 0 citation/reference/undefined warnings |
