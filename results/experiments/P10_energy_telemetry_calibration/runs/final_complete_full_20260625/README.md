# P10 AirLab Energy Calibration

| model | train_count | test_count | mae_wh | rmse_wh | mape | wape | smape | bias_wh | residual_std_wh | coverage_95 | false_feasible_high_energy_rate | high_energy_threshold_wh |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| constant_mean | 168 | 41 | 3.901572 | 5.316285 | 3.280583 | 0.188127 | 0.208979 | 0.586715 | 6.577478 | 0.97561 | 0.0 | 23.979898 |
| parameter_linear | 168 | 41 | 2.409968 | 3.249726 | 2.112204 | 0.116204 | 0.147021 | -0.086657 | 3.998807 | 0.97561 | 0.0 | 23.979898 |
| parameter_route_linear | 168 | 41 | 1.259689 | 1.543576 | 0.075451 | 0.06074 | 0.07097 | -0.335026 | 1.543726 | 0.97561 | 0.0 | 23.979898 |
| telemetry_weather_linear | 168 | 41 | 0.890103 | 1.083295 | 0.066856 | 0.042919 | 0.090855 | -0.112391 | 1.248093 | 1.0 | 0.0 | 23.979898 |
