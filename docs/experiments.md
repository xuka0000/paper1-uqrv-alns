# Experiment Reproduction And New Result Evidence

The final manuscript-facing code was rebuilt on 2026-06-25. Legacy result files remain in the repository but should not be used as final evidence for the rebuilt mathematical model.

## Validation Commands

Unit and integration tests:

```powershell
.\RUN_TESTS.ps1
```

Latest verified output:

```text
Ran 112 tests
OK
```

## Rebuilt Main Runs

### P2 Algorithm Comparison

P2 is the main algorithm comparison. It compares the complete proposed method
only against external classical and strong metaheuristic baselines:
nearest, GA, ACO, simulated annealing, tabu search, VNS and hybrid GA-VNS.
Internal ALNS variants are not P2 baselines; they are reserved for P4 ablation.

Command:

```powershell
.\RUN_REPRODUCE_FULL.ps1 -ExperimentId P2_algorithm_comparison -RunId main_external_portfolio_full_20260625 -Seeds 10
```

Output:

```text
P2_algorithm_comparison: wrote 640 rows
```

Key files:

- `results/experiments/P2_algorithm_comparison/raw_data/P2_algorithm_comparison_main_external_portfolio_full_20260625_raw.csv`
- `results/experiments/P2_algorithm_comparison/analysis_data/P2_algorithm_comparison_main_external_portfolio_full_20260625_summary.csv`
- `results/experiments/P2_algorithm_comparison/analysis_data/P2_algorithm_comparison_main_external_portfolio_full_20260625_run_summary.json`

Summary:

- Proposed beats every external baseline on RWCT in all 80 matched seed-scale cases.
- Mean RWCT gain versus the strongest external baseline at each scale ranges from 17.44% to 40.70%.
- Holm-adjusted paired RWCT p value against the strongest external baseline is 0.01367 at each tested scale.
- Proposed has zero infeasible-sortie rate across all P2 scales in this run.
- Top-risk coverage is not uniformly best at small and medium scales; manuscript claims should not state universal TopCov dominance.

### P7 Statistical Tests From P2

Command:

```powershell
python scripts\run_statistical_tests.py --run-id main_external_portfolio_full_20260625
```

Output:

```text
P7_statistical_tests: wrote 224 rows
```

Key files:

- `results/experiments/P7_statistical_tests/raw_data/P7_statistical_tests_main_external_portfolio_full_20260625_raw.csv`
- `results/experiments/P7_statistical_tests/analysis_data/P7_statistical_tests_main_external_portfolio_full_20260625_summary.csv`
- `results/experiments/P7_statistical_tests/analysis_data/P7_statistical_tests_main_external_portfolio_full_20260625_run_summary.json`

### Final Complete Supplementary Runs

The following full supplementary runs were completed on 2026-06-25 after the
P2 external-baseline main experiment was fixed.

| Experiment | Run id | Raw rows | Scope |
| --- | --- | ---: | --- |
| P1 exact small reference | `final_complete_full_20260625` | 90 | HiGHS compact reference, point ALNS, complete proposed method on 10/15/20 towers. |
| P3 energy prediction | `final_complete_full_20260625` | 90 | Fixed physics, point residual and probabilistic residual models over low/medium/high uncertainty. |
| P4 ablation | `final_complete_full_20260625` | 110 | ALNS-family and module-removal variants on the 50-tower high-uncertainty case. |
| P5 case study | `final_complete_full_20260625` | 15 | 200-tower case-study variants. |
| P6 candidate-stop screening | `final_complete_full_20260625` | 120 | Direct, DBSCAN and K-means stop screening over 30/50/75/100 towers. |
| P8 sensitivity | `final_complete_full_20260625` | 150 | Candidate mode, iteration budget, quantile, reserve ratio and UAV-count sweeps. |
| P10 AirLab energy telemetry | `final_complete_full_20260625` | 209 flights / 164 predictions | Held-out energy-model calibration only. |
| P11 repair stress | `final_complete_full_20260625` | 180 | Sparse high-wind, tight-battery and very-sparse-corridor stress cases. |

Command batch used for the final supplementary run:

```powershell
py -3.9 scripts\run_publishable_experiments.py --experiment-id P1_milp_exact_small --run-id final_complete_full_20260625 --mode full
py -3.9 scripts\run_publishable_experiments.py --experiment-id P3_pinn_prediction_accuracy --run-id final_complete_full_20260625 --mode full
py -3.9 scripts\run_publishable_experiments.py --experiment-id P4_ablation --run-id final_complete_full_20260625 --mode full
py -3.9 scripts\run_publishable_experiments.py --experiment-id P5_case_study --run-id final_complete_full_20260625 --mode full
py -3.9 scripts\run_publishable_experiments.py --experiment-id P6_candidate_stop_screening --run-id final_complete_full_20260625 --mode full
py -3.9 scripts\run_publishable_experiments.py --experiment-id P8_sensitivity --run-id final_complete_full_20260625 --mode full
py -3.9 scripts\run_airlab_energy_calibration.py --run-id final_complete_full_20260625
py -3.9 scripts\run_repair_stress_experiment.py --run-id final_complete_full_20260625 --mode full
```

### P4 Ablation

P4 is run after P2 establishes the proposed method against external baselines.
It contains internal ALNS variants (`alns_fixed`, `alns_pinn`,
`alns_pinn_uq`) and module-removal ablations.

```powershell
.\RUN_REPRODUCE_FULL.ps1 -ExperimentId P4_ablation -RunId final_complete_full_20260625
```

Output:

```text
P4_ablation: wrote 110 rows
```

Key result:

- The complete method is best on RWCT and infeasible-sortie rate in the final
  P4 ablation run.
- It is not the best on every secondary metric: `alns_pinn_uq` has the lowest
  mean makespan, and `no_clustering` has the highest feasible top-risk coverage.
  Manuscript claims should therefore be metric-specific.

### P11 Repair Stress

```powershell
.\RUN_REPRODUCE_FULL.ps1 -ExperimentId P11_repair_stress -RunId final_complete_full_20260625
```

Output:

```text
P11_repair_stress: wrote 180 rows
```

Key result:

- In sparse-high-wind, tight-battery and very-sparse-corridor stress cases, the
  complete method is best on RWCT, feasible top-risk coverage and
  infeasible-sortie rate.
- Runtime is not best; the no-UQ variant is fastest in these stress cases.

### P9 Public GIS Cases

```powershell
py -3.9 scripts\run_public_gis_case_experiment.py --case public_bay_area_full --run-id final_complete_public_bay_area_full_20260625 --mode full
py -3.9 scripts\run_public_gis_case_experiment.py --case public_dallas_fort_worth_full --run-id final_complete_public_dallas_fort_worth_full_20260625 --mode full
py -3.9 scripts\run_public_gis_case_experiment.py --case public_los_angeles_inland_full --run-id final_complete_public_los_angeles_inland_full_20260625 --mode full
```

Output:

```text
P9_real_gis_case: wrote 80 rows for each public case
```

Key result:

- The complete method is the best RWCT method in all three public-GIS proxy
  cases.
- Gain versus the strongest external baseline is 17.73% in Bay Area, 6.40% in
  Dallas--Fort Worth and 15.67% in Los Angeles inland.
- The public GIS cases use public geometry and weather inputs, but risk/value
  labels remain proxy labels.

### P10 Energy Telemetry Calibration

```powershell
py -3.9 scripts\run_airlab_energy_calibration.py --run-id final_complete_full_20260625
```

Output:

```text
P10_energy_telemetry_calibration: 209 flights, 164 test predictions
```

Key result:

- The telemetry-weather linear model is best on held-out RMSE, WAPE, SMAPE and
  95% coverage.
- This validates only the energy-calibration component, not a full field trial
  of the routing/scheduling system.

### Regenerate Manuscript Result Tables

```powershell
py -3.9 scripts\write_full_result_tables.py --only all
Copy-Item -Path manuscript_context\tre_published_style\table_*.tex -Destination results\tables -Force
```

## Result Interpretation Boundary

Do not use legacy P2 files that compare ALNS-family variants as the main
algorithm evidence. The current manuscript-facing hierarchy is:

1. P2: external baseline comparison versus the complete proposed method.
2. P7: paired statistical tests from P2 against external baselines.
3. P4/P11: ablation and stress diagnostics after the P2 main claim is supported.

Manuscript text and tables must be regenerated from the rebuilt result files
before final submission. The current regenerated tables are under
`manuscript_context/tre_published_style/table_*.tex` and `results/tables/`.
