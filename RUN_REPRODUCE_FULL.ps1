param(
    [string]$ExperimentId = "P2_algorithm_comparison",
    [string]$RunId = "reproduced_full",
    [int]$Seeds = 10
)

$ErrorActionPreference = "Stop"
$env:PYTHONPATH = "$PSScriptRoot\src;$PSScriptRoot\scripts;$env:PYTHONPATH"

switch ($ExperimentId) {
    "P9_real_gis_case" {
        $caseRoot = Join-Path $PSScriptRoot "results\experiments\P9_real_gis_case\public_bay_area_full\gis_case"
        & py -3.9 "$PSScriptRoot\scripts\run_public_gis_case_experiment.py" --case-root $caseRoot --case-id public_bay_area_full --run-id $RunId --seeds $Seeds --methods greedy_nearest,ga,aco,alns_fixed,alns_pinn,alns_pinn_uq,alns_pinn_full
    }
    "P10_energy_telemetry_calibration" {
        & py -3.9 "$PSScriptRoot\scripts\run_airlab_energy_calibration.py" --run-id $RunId
    }
    "P11_repair_stress" {
        & py -3.9 "$PSScriptRoot\scripts\run_repair_stress_experiment.py" --run-id $RunId --seeds $Seeds --iterations 140
    }
    default {
        if ($ExperimentId.StartsWith("E")) {
            & py -3.9 "$PSScriptRoot\scripts\run_experiment_suite.py" --only $ExperimentId --run-id $RunId
        } else {
            & py -3.9 "$PSScriptRoot\scripts\run_publishable_experiments.py" --only $ExperimentId --run-id $RunId --seeds $Seeds
        }
    }
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
