# TRE2-Style Full Manuscript Figure/Table Plan

Date: 2026-06-25

## Quantified TRE2 pattern used

- TRE2 has 21 pages, 8 visible figures, 6 main tables and a reference section of about 2.2 published pages.
- The visual logic is not decorative: one topology schematic, one two-stage algorithm flowchart, one route/construction example, one benchmark results table, one before/after route map, one sensitivity heatmap, one public GIS map and one simplified application-result map.
- The result discussion repeatedly performs secondary analysis on top of raw metrics: improvement over base, optimality gap, feasibility, sensitivity trend and practical interpretation.

## Figures generated for this manuscript

- `Fig1_topology_dispatch` from project data/source CSV
- `Fig2_solution_framework` from project data/source CSV
- `Fig3_algorithm_effects` from project data/source CSV
- `Fig4_energy_evidence` from project data/source CSV
- `Fig5_ablation_stress_heatmaps` from project data/source CSV
- `Fig6_public_gis_cases` from project data/source CSV
- `Fig7_scalability_screening` from project data/source CSV

## Manuscript table strategy

- Table 1 mirrors TRE2's literature-positioning table.
- Table 2 in the paper is notation and decision variables.
- Generated tables provide algorithm comparison, energy evidence, GIS-grounded evidence and stress-test evidence.

## Claim boundaries

- P9 GIS cases use public tower/weather sources but proxy risk/value labels.
- P10 uses real AirLab quadcopter telemetry, not transmission-line inspection telemetry.
- P11 supports robustness for RWCT, feasible top-risk coverage and infeasible-sortie rate; runtime is not the best metric for the complete method.
