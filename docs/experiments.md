# Experiment Reproduction And New Result Evidence

The final manuscript-facing code was rebuilt on 2026-06-25. Legacy result files remain in the repository but should not be used as final evidence for the rebuilt mathematical model.

## Validation Commands

Unit and integration tests:

```powershell
.\RUN_TESTS.ps1
```

Latest verified output:

```text
Ran 106 tests
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

### P4 Ablation Quick Check

P4 is run after P2 establishes the proposed method against external baselines.
It contains internal ALNS variants (`alns_fixed`, `alns_pinn`,
`alns_pinn_uq`) and module-removal ablations.

```powershell
.\RUN_REPRODUCE_QUICK.ps1 -ExperimentId P4_ablation -RunId final_model_rebuild_P4_quick_20260625
```

Output:

```text
P4_ablation: wrote 16 rows
```

### P11 Repair Stress Quick Check

```powershell
.\RUN_REPRODUCE_QUICK.ps1 -ExperimentId P11_repair_stress -RunId final_model_rebuild_P11_quick_20260625
```

Output:

```text
P11_repair_stress: wrote 36 rows
```

### P9 Public GIS Quick Check

```powershell
.\RUN_REPRODUCE_QUICK.ps1 -ExperimentId P9_real_gis_case -RunId final_model_rebuild_P9_quick_20260625
```

Output:

```text
P9_real_gis_case: wrote 12 rows
```

### P10 Energy Telemetry Calibration

```powershell
.\RUN_REPRODUCE_QUICK.ps1 -ExperimentId P10_energy_telemetry_calibration -RunId final_model_rebuild_P10_20260625
```

Output:

```text
P10_energy_telemetry_calibration: 209 flights, 164 test predictions
```

## Result Interpretation Boundary

Do not use legacy P2 files that compare ALNS-family variants as the main
algorithm evidence. The current manuscript-facing hierarchy is:

1. P2: external baseline comparison versus the complete proposed method.
2. P7: paired statistical tests from P2 against external baselines.
3. P4/P11: ablation and stress diagnostics after the P2 main claim is supported.

Manuscript text and tables must be regenerated from the rebuilt result files
before final submission.
