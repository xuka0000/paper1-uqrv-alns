# Project Page Design

## Goal

Create a GitHub Pages project page at `https://xuka0000.github.io/paper1-uqrv-alns/` that introduces the research code, mathematical model, proposed algorithm, experiment evidence, ablation scope, public GIS scenarios, and claim boundaries.

## Scope

The page is a static documentation site under `docs/` so GitHub Pages can serve it directly. It must not include separate sections for installation, development process, or code architecture.

## Page Content

- Hero: project title, short manuscript-facing summary, repository and documentation links, and a real algorithm-result figure.
- Abstract: concise summary of same-stop sortie patterns, q95 energy screening, schedule-state ALNS, and external-baseline P2 evidence.
- Main evidence cards: P2 row count, RWCT gain range, matched wins, Holm-adjusted p value, and infeasible-sortie rate.
- Sections: mathematical model, proposed algorithm, main experiment, ablation, public GIS scenarios, evidence boundary, and code documentation.
- Media: two real result figures copied from `results/figures/rendered/`.
- Evidence table: source paths for P2, P7, and manuscript table evidence.

## Evidence Boundaries

The page may claim RWCT dominance against external baselines in rebuilt P2. It must explicitly state that Top-risk coverage is not uniformly best at small and medium scales, public GIS cases use proxy risk/value labels, and AirLab telemetry supports only the energy branch.

## Files

- `docs/index.html`: GitHub Pages entry point.
- `docs/styles.css`: project-page visual style.
- `docs/app.js`: renders page content from JSON.
- `docs/data/site.json`: page content and evidence paths.
- `docs/assets/fig3_algorithm_effects.png`: main result figure.
- `docs/assets/fig6_public_gis_cases.png`: GIS visual evidence.
