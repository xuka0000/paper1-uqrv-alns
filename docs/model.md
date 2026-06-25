# Mathematical Model Mapping

This page records how the final manuscript model is implemented in code.

## Sets And Objects

| Manuscript object | Code object | Path |
| --- | --- | --- |
| Towers \(\mathcal T\) | `Tower` | `src/uqrv/scenario.py` |
| Stops \(\mathcal S\) | `Stop` | `src/uqrv/scenario.py` |
| Weather \(\omega\) | `Weather` | `src/uqrv/scenario.py` |
| Same-stop sortie patterns \(\mathcal K_s\) | `SortiePattern` | `src/uqrv/stop_batch_model.py` |
| Feasible service graph \(\mathcal G_K\) | `ServiceGraph` | `src/uqrv/stop_batch_model.py` |
| Sortie assignment \(y^v_{sdk}\) | `SortieAssignment` | `src/uqrv/stop_batch_model.py` |
| Schedule state \(x\) | `ScheduleState` | `src/uqrv/stop_batch_model.py` |

## Energy Interface

`EnergyModel.estimate_sortie(stop, towers, weather)` computes the physical route for one same-stop sortie:

```text
stop -> tower_1 -> ... -> tower_m -> stop
```

The returned fields map to the manuscript as follows:

| Manuscript term | Code field |
| --- | --- |
| \(d^a_{sk}\) | `SortiePattern.distance` |
| \(\tau_{sdk}\) | `SortiePattern.duration` |
| \(\mu_{sdk}\) | `SortiePattern.energy_mean` |
| \(\sigma_{sdk}\) | `SortiePattern.energy_std` |
| \(Q_{sdk}\) | `SortiePattern.energy_q95` |
| \(B_d(1-\rho)-Q_{sdk}\) | `SortiePattern.energy_margin` |

`build_service_graph()` applies the q95 filter. If a tower has no q95-feasible pattern, the graph still retains the least-cost singleton pattern so the scheduler records an infeasible sortie rather than silently dropping the tower.

## Schedule Timing

`evaluate_schedule_state()` implements the stop-batch synchronization rules:

- vehicle arrival at a stop is propagated from the previous stop and road travel time;
- UAV launch time is `max(vehicle_arrival, same_uav_available_time)`;
- sortie recovery is `launch + sortie_duration`;
- vehicle departure from a stop is the maximum recovery time of all sorties launched at that stop;
- tower start and completion times are computed from within-sortie offsets;
- mission makespan includes tower completion and depot return.

This corresponds to the manuscript variables \(A^v_s,D^v_s,L^v_{sdk},R^v_{sdk},S_i,C_i,C_{\max}\).

## Objective

`objective_breakdown()` evaluates the manuscript objective terms:

| Term | Code field |
| --- | --- |
| \(R(x)=\sum_i \psi_i C_i\) | `ObjectiveBreakdown.rwct` |
| \(C_{\max}\) | `ObjectiveBreakdown.makespan` |
| \(G(x)\) | `ObjectiveBreakdown.ground_travel` |
| \(E(x)=\sum Q_{sdk}y^v_{sdk}\) | `ObjectiveBreakdown.q95_energy` |
| missed-service slack | `ObjectiveBreakdown.missed_service_penalty` |
| duplicate-service penalty | `ObjectiveBreakdown.duplicate_service_penalty` |

The priority weights \(\psi_i\) are computed by `risk_value_priority_map()` in `src/uqrv/priority.py`.
