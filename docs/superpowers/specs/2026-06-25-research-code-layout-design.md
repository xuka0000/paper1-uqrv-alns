# Research Code Layout Design

## Goal

Replace the manuscript-subsection directory layout with a standard research
project layout that has one source tree, one test suite, one scripts directory,
and experiment artifacts grouped by experiment id.

## Architecture

The canonical code lives in `src/uqrv`. Tests live in `tests`, scripts live in
`scripts`, and outputs live in `results`. Existing experiment records are
grouped under `results/experiments/<experiment_id>` using IDs such as
`P2_algorithm_comparison`, not subsection labels such as `6_2`.

## Data And Results

Large experiment-specific source files remain colocated with their experiment
records under `results/experiments` to avoid duplicating AirLab and GIS source
material. Consolidated spreadsheet tables are kept in
`results/consolidated_tables`.

## Compatibility

Python scripts are updated to import from `src` and to write new runs to
`results/experiments`. Root PowerShell wrappers provide stable entry points for
tests and reproduction.

## Verification

The required verification gate is the shared test suite:

```powershell
.\RUN_TESTS.ps1
```
