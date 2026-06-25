# Package claim-evidence manifest

Package: `paper1_latest_full_package_20260606`

Date: 2026-06-06

This manifest records the delivery evidence for the latest Paper1 package. It is a package-level gate, not a claim that every scientific result is field validated. Evidence boundaries are kept explicit.

## Delivery requirements

| Requirement | Evidence path | Validation mode |
|---|---|---|
| Original colleague idea and comments | `01_original_idea_and_comments/方案.pdf`; `01_original_idea_and_comments/paper1必须解决的问题(1).docx`; `01_original_idea_and_comments/Topic1问题及建议(1).docx`; `01_original_idea_and_comments/deep-research-report.md`; `01_original_idea_and_comments/original_and_reference_files_snapshot` | Path existence and package manifest |
| Latest manuscript LaTeX | `02_latest_manuscript_latex/submission_elsarticle_current/tre_submission_current`; `02_latest_manuscript_latex/published_style_current/tre_published_style` | LaTeX source and compiled PDF existence; log scan |
| Reproducible experiment code with README | `03_reproducible_experiment_code/04_reproducible_code/README_REPRODUCE.md`; `03_reproducible_experiment_code/04_reproducible_code/02_code` | Path existence; Python source and test folders included |
| Datasets | `04_datasets/06_downloaded_datasets/README.md`; `04_datasets/06_downloaded_datasets/airlab_energy_telemetry`; `04_datasets/06_downloaded_datasets/public_gis_proxy_cases` | Path existence and file manifest |
| One folder per experiment | `05_experiments_by_item/05_experiment_data_by_item` | Directory count, raw or analysis data check, figure/output check where present, local wrapper check |
| Paper analysis written in LaTeX | `06_paper_analysis_latex/paper1_analysis.tex`; `06_paper_analysis_latex/paper1_analysis.pdf` | XeLaTeX compile |

## Experiment evidence map

| Experiment | Main evidence folders | Local code entry |
|---|---|---|
| `E0_smoke` | `raw_data`; `analysis_data`; `figures`; `runs` | `independent_experiment_code/run_E0_smoke.ps1` |
| `E1_exact_small` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_E1_exact_small.ps1` |
| `E2_core_comparison` | `raw_data`; `analysis_data`; `figures`; `runs` | `independent_experiment_code/run_E2_core_comparison.ps1` |
| `E3_uncertainty_robustness` | `raw_data`; `analysis_data`; `figures`; `runs` | `independent_experiment_code/run_E3_uncertainty_robustness.ps1` |
| `E4_value_ablation` | `raw_data`; `analysis_data`; `figures`; `runs` | `independent_experiment_code/run_E4_value_ablation.ps1` |
| `E5_online_replanning` | `raw_data`; `analysis_data`; `figures`; `runs` | `independent_experiment_code/run_E5_online_replanning.ps1` |
| `E6_scalability` | `raw_data`; `analysis_data`; `figures`; `runs` | `independent_experiment_code/run_E6_scalability.ps1` |
| `P1_milp_exact_small` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P1_milp_exact_small.ps1` |
| `P2_algorithm_comparison` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P2_algorithm_comparison.ps1` |
| `P3_pinn_prediction_accuracy` | `raw_data`; `analysis_data`; `figures`; `runs` | `independent_experiment_code/run_P3_pinn_prediction_accuracy.ps1` |
| `P4_ablation` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P4_ablation.ps1` |
| `P5_case_study` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P5_case_study.ps1` |
| `P6_candidate_stop_screening` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P6_candidate_stop_screening.ps1` |
| `P7_statistical_tests` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P7_statistical_tests.ps1` |
| `P8_sensitivity` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P8_sensitivity.ps1` |
| `P9_real_gis_case` | `raw_data`; `analysis_data`; `public_*` GIS cases; `runs` | `independent_experiment_code/run_P9_real_gis_case.ps1` |
| `P10_energy_telemetry_calibration` | `raw_data`; `analysis_data`; `raw_sources`; `runs` | `independent_experiment_code/run_P10_energy_telemetry_calibration.ps1` |
| `P11_repair_stress` | `raw_data`; `analysis_data`; `runs` | `independent_experiment_code/run_P11_repair_stress.ps1` |

## Scientific evidence boundaries

| Claim area | Supported by current package | Boundary |
|---|---|---|
| Robust energy-aware routing and scheduling | Mathematical model, algorithm pseudocode, code, synthetic experiments, public GIS proxy cases, and energy telemetry calibration | Not a field deployment validation on transmission-line missions |
| Exact comparison | Small finite candidate instances with MILP reference | Not a proof of global optimality for large continuous routing |
| Algorithmic comparison | Controlled benchmark, ablation, sensitivity, statistical tests, stress cases | Not uniformly dominant over every strong baseline in every metric. Some comparisons are bounded or comparable |
| Public-data evidence | Public GIS geometry, public weather, AirLab telemetry calibration | Risk/value labels and candidate stops are proxy-generated |
| Reproducibility | Full code, runners, per-experiment evidence folders, datasets, and README | Requires Python 3.9 according to the reproducible-code README |

## Validation artifacts

Fresh validation outputs for this package are stored in:

- `07_validation/current_compile_and_package_check.txt`
- `07_validation/package_manifest.csv`
- `07_validation/package_hashes_sha256.txt`

The external bridge script `check_claim_evidence_gate.ps1` was not present in the local workspace at package time, so this manifest is validated by direct path checks, LaTeX compilation, log scans, wrapper parse checks, manifest generation, and ZIP hashing.
