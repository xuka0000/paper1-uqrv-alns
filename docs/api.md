# Data Structures And API

## `ModelParameters`

Path: `src/uqrv/stop_batch_model.py`

Controls service graph size and objective weights:

- `max_towers_per_sortie`
- `nearest_stops_per_tower`
- `max_near_towers_per_stop`
- `lambda_r`, `lambda_c`, `lambda_g`, `lambda_e`
- normalization constants `r0`, `c0`, `g0`, `e0`
- missed and duplicate service penalties

## `SortiePattern`

Represents one ordered same-stop UAV sortie:

- `pattern_id`
- `stop_id`
- `tower_ids`
- `distance`
- `duration`
- `energy_mean`
- `energy_std`
- `energy_q95`
- `energy_margin`
- `feasible`
- `tower_start_offsets`
- `tower_finish_offsets`

## `ServiceGraph`

Indexes all retained sortie patterns:

- `patterns`
- `patterns_by_stop`
- `patterns_by_tower`
- `feasible_pattern_ids`
- `pattern_count`
- `feasible_service_count`

Useful methods:

```python
graph.get_pattern(pattern_id)
graph.require_pattern(stop_id=0, tower_ids=(2, 1, 0))
graph.best_pattern_covering({tower_id})
```

## `ScheduleState`

Represents the executable schedule:

- `assignments`
- `tasks`
- `sorties`
- `route_by_vehicle`
- `missed_tower_ids`
- `duplicate_service_count`
- `makespan`
- `ground_travel_time`
- `ground_travel_distance`
- `diagnostics`

Use `state_to_plan_tasks()` to convert a `ScheduleState` into the existing `PlanTask` and `PlanSortie` objects consumed by metrics and plotting code.

## Experiment Diagnostics

ALNS result rows include:

- `implementation_family`
- `service_graph_pattern_count`
- `service_graph_feasible_count`
- `selected_sortie_count`
- `missed_service_count`
- `duplicate_service_count`
- `objective_rwct`
- `objective_makespan`
- `objective_ground_travel`
- `objective_q95_energy`
- `objective_total`
- operator use counts
