# Algorithm Mapping

The final manuscript algorithm is implemented by `src/uqrv/rv_alns.py`.

## Stage 1: Service-Set Construction

Entry point:

```python
build_service_graph(scenario, energy_model, params, use_quantile=True)
```

Implementation steps:

1. Select nearest candidate stops for each tower.
2. Build bounded ordered same-stop patterns up to `max_towers_per_sortie`.
3. Evaluate distance, duration, mean energy, energy uncertainty and q95 energy.
4. Mark q95 feasibility using `EnergyModel.is_feasible()`.
5. Index patterns by stop and tower for ALNS repair.

The bounded pattern universe is deliberate. The manuscript model defines \(\mathcal K_s\); the code constructs a finite, auditable \(\mathcal K_s\) controlled by `ModelParameters`.

## Stage 2: Schedule-State RV-ALNS

Entry point:

```python
solve_schedule_state_alns(scenario, method, energy_model, iterations, rng, config)
```

The solver operates on `ScheduleState`, not on a tower order alone.

Main loop:

1. Build an initial complete schedule from q95 service patterns.
2. Select one destroy and one repair operator with adaptive weights.
3. Remove towers or sortie chains from the current schedule.
4. Reinsert removed towers through indexed feasible service patterns.
5. Recompute the full schedule state and objective.
6. Accept by improvement or simulated annealing.
7. Apply bounded local search on small cases through alternative same-tower-set patterns.
8. Update operator weights.

For the complete proposed method, the ALNS incumbent is followed by a
metric-aware portfolio selection step. The portfolio includes the adaptive ALNS
schedule and risk-bucketed stop-grouping schedules. The selected final schedule
minimizes infeasible-sortie count first, then RWCT, then makespan. This is the
code path behind `alns_pinn_full` in the manuscript-facing P2 main experiment.

## Operators

Destroy operators:

- `random_removal`
- `worst_energy_removal`
- `shaw_related_removal`
- `path_segment_removal`
- `uav_chain_removal`

Repair operators:

- `greedy_insert_repair`
- `regret_insert_repair`
- `energy_minimum_insert_repair`
- `synchronization_aware_insert_repair`

All operator counts are exported to experiment CSV files.

## Solver Method Mapping

| Experiment method | Code path |
| --- | --- |
| `alns_fixed` | schedule-state ALNS, no q95, no risk-value weight |
| `alns_point` / `alns_pinn` | schedule-state ALNS, point energy |
| `uq_alns` / `alns_pinn_uq` | schedule-state ALNS, q95 energy, no risk-value weight |
| `alns_full` / `alns_pinn_full` | schedule-state ALNS, q95 energy and risk-value weight |
| `no_uq` | full ALNS with q95 disabled |
| `no_risk_value` | full ALNS with risk-value weight set to zero |
| `no_energy_repair` | full ALNS with energy-minimum repair disabled |
| `no_sync_repair` | full ALNS with synchronization-aware repair disabled |
| `no_adaptive` | full ALNS with adaptive scoring disabled |

## Main-Experiment External Baselines

P2 main comparison uses external baselines only:

| Experiment method | Code path |
| --- | --- |
| `greedy_nearest` | nearest-stop constructive order |
| `ga` | population-based genetic search over tower order |
| `aco` | pheromone-guided ant-colony order construction |
| `simulated_annealing` | temperature-based swap/insert order search |
| `tabu_search` | tabu swap/insert order search |
| `variable_neighborhood_search` | VNS order search with local descent |
| `hybrid_genetic_search` | GA population search with VNS polishing |

These baselines remain in `src/uqrv/solvers.py` and do not call the
schedule-state ALNS implementation.
