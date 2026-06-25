# Paper1 Research Code Package

GitHub repository: https://github.com/xuka0000/paper1-uqrv-alns

Code documentation: https://xuka0000.github.io/paper1-uqrv-alns/

This directory is organized as a standard research-code project. It uses one
shared Python source tree instead of one duplicated code copy per manuscript
subsection.

## Layout

| Path | Purpose |
| --- | --- |
| `src/uqrv/` | Python package for scenario generation, solvers, energy models, metrics, and IO helpers. |
| `scripts/` | Reproduction, plotting, manuscript-table, and validation scripts. |
| `tests/` | `unittest` suite for the shared codebase. |
| `results/experiments/` | Experiment run records, raw generated rows, summaries, figures, models, and public/proxy source material grouped by experiment id. |
| `results/tables/` | Manuscript-ready LaTeX result tables. |
| `results/figures/` | Rendered figures and source data consolidated from the delivery package. |
| `results/consolidated_tables/` | CSV/XLSX result tables for direct inspection. |
| `manuscript_context/` | LaTeX context used by manuscript-output tests and table-generation scripts. |
| `validation/` | Delivery validation notes and manifests. |
| `metadata/` | Source package manifest, checksum note, and original by-section readme. |
| `docs/` | Code documentation, model/algorithm mapping, source mapping, and working notes. |

## Validate

```powershell
.\RUN_TESTS.ps1
```

Equivalent direct command:

```powershell
py -3.9 -m unittest discover -s tests -q
```

## Reproduce Experiments

Quick example:

```powershell
.\RUN_REPRODUCE_QUICK.ps1 -ExperimentId P2_algorithm_comparison -RunId reproduced_P2_quick
```

Full example:

```powershell
.\RUN_REPRODUCE_FULL.ps1 -ExperimentId P2_algorithm_comparison -RunId reproduced_P2_full
```

Most `P*` experiments use `scripts/run_publishable_experiments.py`. The root
PowerShell wrappers route special cases such as public GIS, AirLab energy
calibration, and repair-stress experiments to their dedicated scripts.

Outputs are written under `results/experiments/<experiment_id>/`.

## Source Trace

See `docs/PROJECT_SOURCE_MAP.md` for how the previous by-section delivery
package was converted into this standard layout.

## Final Manuscript Model Rebuild

The manuscript-facing model code was rebuilt to use explicit same-stop sortie
patterns, q95 service graphs, schedule-state ALNS, and objective-term
diagnostics.

Documentation:

- `docs/model.md`
- `docs/algorithm.md`
- `docs/api.md`
- `docs/experiments.md`
- `docs/claim_algorithm_evidence_ledger.md`
- `docs/final_experiment_completeness_20260625.md`

Main rebuilt result run:

```powershell
.\RUN_REPRODUCE_FULL.ps1 -ExperimentId P2_algorithm_comparison -RunId main_external_portfolio_full_20260625 -Seeds 10
```

The complete supplementary experiment suite uses run id
`final_complete_full_20260625` for P1/P3/P4/P5/P6/P8/P10/P11, and dedicated
`final_complete_public_*_20260625` run ids for the three public GIS cases.
Legacy result files remain for traceability only.
