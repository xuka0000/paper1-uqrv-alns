# Claim Algorithm Evidence Ledger

| Claim | Mechanism | Code path | Evidence files | Current status |
| --- | --- | --- | --- | --- |
| Same-stop multi-tower sortie patterns are implemented. | `SortiePattern` stores ordered tower sequences; `EnergyModel.estimate_sortie()` evaluates stop-to-towers-to-stop paths. | `src/uqrv/stop_batch_model.py`, `src/uqrv/energy.py` | `tests/test_stop_batch_model.py`, `tests/test_rv_alns_schedule_state.py` | Supported |
| q95 energy screening is used in scheduling. | `build_service_graph()` marks q95 feasibility; ALNS uses `RvAlnsConfig.use_quantile`. | `src/uqrv/stop_batch_model.py`, `src/uqrv/rv_alns.py` | P2 full raw/summary files with `implementation_family=stop_batch_schedule_state_alns` | Supported |
| The ALNS operates on schedule state rather than only tower order. | ALNS destroy/repair creates `SortieAssignment` lists and evaluates `ScheduleState`. | `src/uqrv/rv_alns.py` | `tests/test_rv_alns_schedule_state.py` | Supported |
| RWCT is evaluated from tower completion times. | `objective_breakdown()` and `evaluate_plan()` both compute priority-weighted completion from task finish times. | `src/uqrv/stop_batch_model.py`, `src/uqrv/metrics.py` | `tests/test_stop_batch_model.py`; P2 full summary | Supported |
| Full method dominates every ALNS baseline on RWCT. | Not supported by rebuilt P2 full results. | `results/experiments/P2_algorithm_comparison/...final_model_rebuild_P2_full_20260625_summary.csv` | P2 full summary | Withdraw or rewrite |
| Full method reduces residual infeasible-sortie rate relative to fixed/point ALNS. | q95 service graph and q95 objective terms reduce selected infeasible sorties. | `src/uqrv/rv_alns.py`, `src/uqrv/metrics.py` | P2 full summary; P4/P11 quick summaries | Supported with scenario-specific magnitude |
| Public GIS case uses real public geometry but proxy risk/value labels. | GIS loader builds `Scenario`; ALNS uses same service graph and metrics. | `src/uqrv/gis_case.py`, `scripts/run_public_gis_case_experiment.py` | P9 quick summary | Supported as GIS-grounded proxy evidence |
| AirLab telemetry validates the full transmission-line inspection simulator. | Telemetry calibration tests energy prediction only. | `scripts/run_airlab_energy_calibration.py` | P10 summary | Not supported; keep as energy calibration only |
