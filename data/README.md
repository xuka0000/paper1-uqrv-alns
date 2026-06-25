# Data Directory

The reproducibility package keeps experiment-specific source material next to
the experiment it supports under `results/experiments/<experiment_id>/`.

Examples:

- AirLab telemetry source files:
  `results/experiments/P10_energy_telemetry_calibration/raw_sources/airlab/`
- Public GIS source files:
  `results/experiments/P9_real_gis_case/*/gis_case/raw_sources/`

This avoids duplicating large source files while keeping each experiment
self-contained.
