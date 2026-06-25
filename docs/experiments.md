# Experiment Reproduction And New Result Evidence

The final manuscript-facing code was rebuilt on 2026-06-25. Legacy result files remain in the repository but should not be used as final evidence for the rebuilt mathematical model.

## Validation Commands

Unit and integration tests:

```powershell
.\RUN_TESTS.ps1
```

Latest verified output:

```text
Ran 101 tests
OK
```

## Rebuilt Main Runs

### P2 Algorithm Comparison

Command:

```powershell
.\RUN_REPRODUCE_FULL.ps1 -ExperimentId P2_algorithm_comparison -RunId final_model_rebuild_P2_full_20260625 -Seeds 10
```

Output:

```text
P2_algorithm_comparison: wrote 560 rows
```

Key files:

- `results/experiments/P2_algorithm_comparison/raw_data/P2_algorithm_comparison_final_model_rebuild_P2_full_20260625_raw.csv`
- `results/experiments/P2_algorithm_comparison/analysis_data/P2_algorithm_comparison_final_model_rebuild_P2_full_20260625_summary.csv`
- `results/experiments/P2_algorithm_comparison/analysis_data/P2_algorithm_comparison_final_model_rebuild_P2_full_20260625_run_summary.json`

### P4 Ablation Quick Check

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

The rebuilt P2 results support a different claim boundary from the old manuscript draft. The full q95 risk-value ALNS strongly reduces infeasible-sortie rates relative to fixed/point energy ALNS. It does not uniformly dominate UQ energy ALNS on RWCT at every scale. Manuscript text and tables must be regenerated from the rebuilt result files before final submission.
