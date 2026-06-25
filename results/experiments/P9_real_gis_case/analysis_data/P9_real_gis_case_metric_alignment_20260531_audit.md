# P9 GIS Metric Alignment Audit

| case_id | method | rwct | top_risk_coverage | infeasible_sortie_rate | rwct_rank | top_cov_rank | rank_gap_abs | case_best_rwct_methods | case_best_top_cov_methods | case_has_best_metric_conflict | interpretation_flag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| bay_area_public_full | alns_pinn_full | 139230.14909 | 1.0 | 0.0 | 1 | 1 | 0 | alns_pinn_full | alns_pinn_full | False | aligned_or_minor_gap |
| bay_area_public_full | aco | 139296.284689 | 0.933333 | 0.0 | 2 | 2 | 0 | alns_pinn_full | alns_pinn_full | False | aligned_or_minor_gap |
| bay_area_public_full | ga | 139311.2905 | 0.933333 | 0.0 | 3 | 2 | 1 | alns_pinn_full | alns_pinn_full | False | aligned_or_minor_gap |
| bay_area_public_full | alns_pinn | 139502.961386 | 0.933333 | 0.0 | 4 | 2 | 2 | alns_pinn_full | alns_pinn_full | False | rwct_topcov_conflict |
| bay_area_public_full | alns_pinn_uq | 139514.766928 | 0.933333 | 0.0 | 5 | 2 | 3 | alns_pinn_full | alns_pinn_full | False | rwct_topcov_conflict |
| bay_area_public_full | greedy_nearest | 148680.797616 | 0.4 | 0.0 | 6 | 3 | 3 | alns_pinn_full | alns_pinn_full | False | rwct_topcov_conflict |
| bay_area_public_full | alns_fixed | 153610.082848 | 0.2 | 0.0 | 7 | 4 | 3 | alns_pinn_full | alns_pinn_full | False | rwct_topcov_conflict |
| dallas_fort_worth_public_full | alns_pinn_full | 172847.981194 | 0.866667 | 0.1 | 1 | 2 | 1 | alns_pinn_full | alns_pinn;alns_pinn_uq | True | rwct_topcov_conflict |
| dallas_fort_worth_public_full | greedy_nearest | 178676.217886 | 0.0 | 0.116667 | 2 | 3 | 1 | alns_pinn_full | alns_pinn;alns_pinn_uq | True | rwct_topcov_conflict |
| dallas_fort_worth_public_full | alns_fixed | 181359.039352 | 0.0 | 0.116667 | 3 | 3 | 0 | alns_pinn_full | alns_pinn;alns_pinn_uq | True | rwct_topcov_conflict |
| dallas_fort_worth_public_full | aco | 188896.655467 | 0.866667 | 0.116667 | 4 | 2 | 2 | alns_pinn_full | alns_pinn;alns_pinn_uq | True | rwct_topcov_conflict |
| dallas_fort_worth_public_full | ga | 189611.61552 | 0.866667 | 0.116667 | 5 | 2 | 3 | alns_pinn_full | alns_pinn;alns_pinn_uq | True | rwct_topcov_conflict |
| dallas_fort_worth_public_full | alns_pinn | 190267.204335 | 0.933333 | 0.116667 | 6 | 1 | 5 | alns_pinn_full | alns_pinn;alns_pinn_uq | True | rwct_topcov_conflict |
| dallas_fort_worth_public_full | alns_pinn_uq | 190729.888444 | 0.933333 | 0.1 | 7 | 1 | 6 | alns_pinn_full | alns_pinn;alns_pinn_uq | True | rwct_topcov_conflict |
| los_angeles_inland_public_full | alns_pinn_full | 157353.12077 | 0.933333 | 0.0 | 1 | 1 | 0 | alns_pinn_full | aco;alns_pinn;alns_pinn_full;alns_pinn_uq;ga | False | aligned_or_minor_gap |
| los_angeles_inland_public_full | aco | 158074.23348 | 0.933333 | 0.0 | 2 | 1 | 1 | alns_pinn_full | aco;alns_pinn;alns_pinn_full;alns_pinn_uq;ga | False | aligned_or_minor_gap |
| los_angeles_inland_public_full | ga | 158086.831185 | 0.933333 | 0.0 | 3 | 1 | 2 | alns_pinn_full | aco;alns_pinn;alns_pinn_full;alns_pinn_uq;ga | False | rwct_topcov_conflict |
| los_angeles_inland_public_full | alns_pinn | 158458.335975 | 0.933333 | 0.0 | 4 | 1 | 3 | alns_pinn_full | aco;alns_pinn;alns_pinn_full;alns_pinn_uq;ga | False | rwct_topcov_conflict |
| los_angeles_inland_public_full | alns_pinn_uq | 158542.390637 | 0.933333 | 0.0 | 5 | 1 | 4 | alns_pinn_full | aco;alns_pinn;alns_pinn_full;alns_pinn_uq;ga | False | rwct_topcov_conflict |
| los_angeles_inland_public_full | greedy_nearest | 164184.480305 | 0.133333 | 0.0 | 6 | 2 | 4 | alns_pinn_full | aco;alns_pinn;alns_pinn_full;alns_pinn_uq;ga | False | rwct_topcov_conflict |
| los_angeles_inland_public_full | alns_fixed | 167532.086792 | 0.133333 | 0.0 | 7 | 2 | 5 | alns_pinn_full | aco;alns_pinn;alns_pinn_full;alns_pinn_uq;ga | False | rwct_topcov_conflict |
