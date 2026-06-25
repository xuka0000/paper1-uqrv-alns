# Final Experiment Completeness Report

Date: 2026-06-25

This report records the manuscript-facing experiment state after the final code
rebuild. Legacy runs remain in `results/experiments/` for traceability, but the
runs below are the current evidence set.

## Run Matrix

| Experiment | Final run id | Raw rows | Status |
| --- | --- | ---: | --- |
| P1 exact small reference | `final_complete_full_20260625` | 90 | Complete |
| P2 external algorithm comparison | `main_external_portfolio_full_20260625` | 640 | Complete |
| P3 energy prediction accuracy | `final_complete_full_20260625` | 90 | Complete |
| P4 ablation | `final_complete_full_20260625` | 110 | Complete |
| P5 case study | `final_complete_full_20260625` | 15 | Complete |
| P6 candidate-stop screening | `final_complete_full_20260625` | 120 | Complete |
| P7 paired statistical tests | `main_external_portfolio_full_20260625` | 224 | Complete |
| P8 sensitivity | `final_complete_full_20260625` | 150 | Complete |
| P9 Bay Area public GIS | `final_complete_public_bay_area_full_20260625` | 80 | Complete |
| P9 Dallas--Fort Worth public GIS | `final_complete_public_dallas_fort_worth_full_20260625` | 80 | Complete |
| P9 Los Angeles inland public GIS | `final_complete_public_los_angeles_inland_full_20260625` | 80 | Complete |
| P10 AirLab energy telemetry | `final_complete_full_20260625` | 209 flights / 164 predictions | Complete |
| P11 repair stress | `final_complete_full_20260625` | 180 | Complete |

## Main Algorithm Evidence

P2 is the main algorithm experiment and compares the complete proposed method
against external baselines: nearest, GA, ACO, simulated annealing, tabu search,
VNS and HGS-VNS. Internal ALNS variants are not main baselines; they are used in
P4 ablation.

The proposed method beats every external baseline on RWCT in all 80 matched
scale-seed cases. Mean RWCT gain versus the strongest external baseline ranges
from 17.44% to 40.70% across the tested scales. P7 reports 56/56 significant
Holm-adjusted RWCT paired tests with `p_holm = 0.01367184`, and every RWCT pair
has 10 improvements and 0 worsening cases.

The main claim is therefore supported for RWCT. Top-risk coverage should not be
written as uniformly dominant across all scales: the proposed method is strongest
at larger scales, but several small and medium scales have higher TopCov from GA,
ACO or HGS-VNS.

## Supplementary Evidence

P4 ablation supports the integrated design for RWCT and feasibility. The complete
method is best on RWCT and infeasible-sortie rate. It is not best on every
secondary metric: `alns_pinn_uq` has the lowest mean makespan, and
`no_clustering` has the highest feasible top-risk coverage.

P9 public GIS proxy cases support external-scenario RWCT robustness. The complete
method has the lowest RWCT in Bay Area, Dallas--Fort Worth and Los Angeles
inland, with gains versus the strongest external baseline of 17.73%, 6.40% and
15.67%, respectively. These cases use public geometry/weather and proxy
risk-value labels.

P10 supports only energy-model calibration. The telemetry-weather model is best
on held-out RMSE, WAPE, SMAPE and 95% coverage, but this is not a full
transmission-line field validation.

P11 stress tests support robustness under sparse high wind, tight battery and
very sparse corridor settings. The complete method is best on RWCT, feasible
top-risk coverage and infeasible-sortie rate in all three stress cases. Runtime
is not best; no-UQ variants are faster.

## Regenerated Artifacts

- Full manuscript tables: `manuscript_context/tre_published_style/table_*.tex`
- Synchronized result tables: `results/tables/table_*.tex`
- TRE2-style figures and source CSV files: `results/figures/tre2style/`
- Manuscript figure PDFs: `manuscript_context/tre_published_style/figures/`
- Combined generated tables: `manuscript_context/tre_published_style/generated_tables.tex`
