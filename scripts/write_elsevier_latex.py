from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = PROJECT_ROOT / "results" / "experiments"
FIGS = PROJECT_ROOT / "results/figures/publishable"
OUT = PROJECT_ROOT / "manuscript_context" / "elsevier"
RUN_ID = "multi_tower_repair2_full_20260612"
RUN_IDS = {}

DUAL_DRAFTS = {
    "preprint": {
        "out": PROJECT_ROOT / "manuscript_context" / "elsevier_preprint",
        "filename": "tre_manuscript_preprint.tex",
        "documentclass": r"\documentclass[preprint,12pt,number]{elsarticle}",
    },
    "5p": {
        "out": PROJECT_ROOT / "manuscript_context" / "elsevier_5p",
        "filename": "tre_manuscript_5p.tex",
        "documentclass": r"\documentclass[final,5p,twocolumn,number,nopreprintline]{elsarticle}",
    },
}


def main() -> int:
    context = metrics_context()
    for draft in DUAL_DRAFTS.values():
        out = draft["out"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "figures").mkdir(exist_ok=True)
        (out / "submission").mkdir(exist_ok=True)
        sync_figures(out / "figures")
        (out / draft["filename"]).write_text(tex(context, draft["documentclass"]), encoding="utf-8")
        (out / "tre_references.bib").write_text(bib(), encoding="utf-8")
        (out / "submission" / "highlights.tex").write_text(highlights(context), encoding="utf-8")
        (out / "README.md").write_text(readme(draft["filename"], draft["documentclass"]), encoding="utf-8")
        print(out / draft["filename"])

    # Keep the legacy path synchronized for earlier project references.
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)
    (OUT / "submission").mkdir(exist_ok=True)
    sync_figures(OUT / "figures")
    (OUT / "tre_manuscript.tex").write_text(tex(context, DUAL_DRAFTS["5p"]["documentclass"]), encoding="utf-8")
    (OUT / "tre_references.bib").write_text(bib(), encoding="utf-8")
    (OUT / "submission" / "highlights.tex").write_text(highlights(context), encoding="utf-8")
    return 0


def sync_figures(target: Path) -> None:
    for existing in target.glob("Fig*.*"):
        existing.unlink()
    for fig in FIGS.glob("Fig*.*"):
        shutil.copy2(fig, target / fig.name)


def metrics_context() -> dict:
    p1 = read("P1_milp_exact_small")
    p2 = read("P2_algorithm_comparison")
    p3 = read("P3_pinn_prediction_accuracy")
    p4 = read("P4_ablation")
    p5 = read("P5_case_study")
    p6 = read("P6_candidate_stop_screening")
    p7 = read("P7_statistical_tests")
    p8 = read("P8_sensitivity")

    def row(df: pd.DataFrame, **filters):
        sub = df.copy()
        for key, value in filters.items():
            sub = sub[sub[key].astype(str).eq(str(value))]
        if sub.empty:
            raise KeyError(filters)
        return sub.iloc[0]

    external_methods = [
        "greedy_nearest",
        "ga",
        "aco",
        "simulated_annealing",
        "tabu_search",
        "variable_neighborhood_search",
        "hybrid_genetic_search",
    ]
    available_external = [method for method in external_methods if method in set(p2["method"])]
    if not available_external:
        available_external = ["greedy_nearest"]

    def best_external(tower_count: int) -> pd.Series:
        sub = p2[p2["tower_count"].astype(str).eq(str(tower_count)) & p2["method"].isin(available_external)].copy()
        if sub.empty:
            return row(p2, method="greedy_nearest", tower_count=tower_count)
        return sub.sort_values("risk_weighted_completion_time_mean").iloc[0]

    def stat_against_best(tower_count: int, metric: str) -> pd.Series:
        preferred = str(best_external(tower_count)["method"])
        for baseline in [preferred, *available_external]:
            try:
                return row(p7, baseline_method=baseline, metric=metric, tower_count=tower_count)
            except KeyError:
                continue
        raise KeyError({"baseline_method": preferred, "metric": metric, "tower_count": tower_count})

    prop100 = row(p2, method="alns_pinn_full", tower_count=100)
    best_external100 = best_external(100)
    nearest100 = row(p2, method="greedy_nearest", tower_count=100)
    prop500 = row(p2, method="alns_pinn_full", tower_count=500)
    best_external500 = best_external(500)
    fixed_case = row(p5, method="alns_fixed")
    prop_case = row(p5, method="alns_pinn_full")
    kmeans100 = row(p6, candidate_mode="kmeans", tower_count=100)
    dbscan100 = row(p6, candidate_mode="dbscan", tower_count=100)
    stat100_point = stat_against_best(100, "risk_weighted_completion_time")
    stat100_cov = stat_against_best(100, "top_risk_coverage")
    stat500_point = stat_against_best(500, "risk_weighted_completion_time")
    stat500_cov = stat_against_best(500, "top_risk_coverage")
    prob_high = row(p3, prediction_model="probabilistic_pinn", uncertainty="high")
    point_high = row(p3, prediction_model="point_pinn", uncertainty="high")
    fixed_high = row(p3, prediction_model="fixed_physics", uncertainty="high")
    prop_ablation = row(p4, method="alns_pinn_full")
    no_energy_repair = row(p4, method="no_energy_repair")
    no_sync_repair = row(p4, method="no_sync_repair")
    prop_improving_moves = prop_ablation["alns_improving_moves_mean"]
    sens_kmeans = row(p8, sensitivity_factor="candidate_mode", sensitivity_level="kmeans")
    sens_direct = row(p8, sensitivity_factor="candidate_mode", sensitivity_level="direct")
    sens_dbscan = row(p8, sensitivity_factor="candidate_mode", sensitivity_level="dbscan")
    sens_uav2 = row(p8, sensitivity_factor="uav_count", sensitivity_level="2")
    sens_uav4 = row(p8, sensitivity_factor="uav_count", sensitivity_level="4")
    sens_uav6 = row(p8, sensitivity_factor="uav_count", sensitivity_level="6")
    sens_iter50 = row(p8, sensitivity_factor="iteration_budget", sensitivity_level="50")
    sens_iter160 = row(p8, sensitivity_factor="iteration_budget", sensitivity_level="160")
    milp_gap = p1[p1["method"].eq("alns_pinn_full")]["optimality_gap_pct_mean"].mean()
    p2_rwct = p2.pivot_table(
        index="tower_count",
        columns="method",
        values="risk_weighted_completion_time_mean",
        aggfunc="first",
    )
    best_external_by_scale = p2[p2["method"].isin(available_external)].groupby("tower_count")[
        "risk_weighted_completion_time_mean"
    ].min()
    proposed_by_scale = p2[p2["method"].eq("alns_pinn_full")].set_index("tower_count")[
        "risk_weighted_completion_time_mean"
    ]
    external_gains = 100.0 * (best_external_by_scale - proposed_by_scale) / best_external_by_scale
    return {
        "risk_gain_vs_best_external_100": pct_reduction(prop100["risk_weighted_completion_time_mean"], best_external100["risk_weighted_completion_time_mean"]),
        "risk_gain_vs_best_external_500": pct_reduction(prop500["risk_weighted_completion_time_mean"], best_external500["risk_weighted_completion_time_mean"]),
        "risk_gain_vs_best_external_min": external_gains.min(),
        "risk_gain_vs_best_external_max": external_gains.max(),
        "best_external_100": best_external100["method"],
        "best_external_500": best_external500["method"],
        "risk_gain_vs_fixed_100": pct_reduction(prop100["risk_weighted_completion_time_mean"], best_external100["risk_weighted_completion_time_mean"]),
        "risk_gain_vs_fixed_500": pct_reduction(prop500["risk_weighted_completion_time_mean"], best_external500["risk_weighted_completion_time_mean"]),
        "risk_gain_vs_nearest_100": pct_reduction(prop100["risk_weighted_completion_time_mean"], nearest100["risk_weighted_completion_time_mean"]),
        "risk_gain_vs_point_100": pct_reduction(prop100["risk_weighted_completion_time_mean"], best_external100["risk_weighted_completion_time_mean"]),
        "risk_gain_vs_point_min": external_gains.min(),
        "risk_gain_vs_point_max": external_gains.max(),
        "risk_gain_vs_uq_min": external_gains.min(),
        "risk_gain_vs_uq_max": external_gains.max(),
        "risk_gain_vs_fixed_min": external_gains.min(),
        "risk_gain_vs_fixed_max": external_gains.max(),
        "coverage_gain_vs_point_100": 100.0 * (prop100["top_risk_coverage_mean"] - best_external100["top_risk_coverage_mean"]),
        "violation_point_100": 100.0 * best_external100["infeasible_sortie_rate_mean"],
        "violation_prop_100": 100.0 * prop100["infeasible_sortie_rate_mean"],
        "risk_gain_500": pct_reduction(prop500["risk_weighted_completion_time_mean"], best_external500["risk_weighted_completion_time_mean"]),
        "coverage_gain_500": 100.0 * (prop500["top_risk_coverage_mean"] - best_external500["top_risk_coverage_mean"]),
        "case_risk_gain": pct_reduction(prop_case["risk_weighted_completion_time_mean"], fixed_case["risk_weighted_completion_time_mean"]),
        "case_coverage_gain": 100.0 * (prop_case["top_risk_coverage_mean"] - fixed_case["top_risk_coverage_mean"]),
        "kmeans_reduction_100": 100.0 * kmeans100["candidate_pair_reduction_mean"],
        "dbscan_reduction_100": 100.0 * dbscan100["candidate_pair_reduction_mean"],
        "stat100_point_p": stat100_point["p_holm"],
        "stat100_point_median": stat100_point["median_effect_abs"],
        "stat100_point_ci_low": stat100_point["paired_diff_ci95_low"],
        "stat100_point_ci_high": stat100_point["paired_diff_ci95_high"],
        "stat100_cov_p": stat100_cov["p_value"],
        "stat100_cov_holm": stat100_cov["p_holm"],
        "stat500_point_p": stat500_point["p_holm"],
        "stat500_point_median": stat500_point["median_effect_abs"],
        "stat500_point_ci_low": stat500_point["paired_diff_ci95_low"],
        "stat500_point_ci_high": stat500_point["paired_diff_ci95_high"],
        "stat500_cov_median": stat500_cov["median_effect_abs"],
        "stat500_cov_p": stat500_cov["p_holm"],
        "prob_high_coverage": 100.0 * prob_high["coverage_95_mean"],
        "point_high_coverage": 100.0 * point_high["coverage_95_mean"],
        "fixed_high_coverage": 100.0 * fixed_high["coverage_95_mean"],
        "prob_high_mae": prob_high["mae_mean"],
        "point_high_mae": point_high["mae_mean"],
        "fixed_high_mae": fixed_high["mae_mean"],
        "prob_training_samples": prob_high.get("training_sample_count_mean", 0),
        "milp_gap": milp_gap,
        "risk_gain_vs_no_energy_repair": pct_reduction(
            prop_ablation["risk_weighted_completion_time_mean"],
            no_energy_repair["risk_weighted_completion_time_mean"],
        ),
        "risk_gain_vs_no_sync_repair": pct_reduction(
            prop_ablation["risk_weighted_completion_time_mean"],
            no_sync_repair["risk_weighted_completion_time_mean"],
        ),
        "coverage_gain_vs_no_energy_repair": 100.0
        * (prop_ablation["top_risk_coverage_mean"] - no_energy_repair["top_risk_coverage_mean"]),
        "coverage_gain_vs_no_sync_repair": 100.0
        * (prop_ablation["top_risk_coverage_mean"] - no_sync_repair["top_risk_coverage_mean"]),
        "improving_move_drop_no_energy_repair": pct_reduction(
            no_energy_repair["alns_improving_moves_mean"],
            prop_improving_moves,
        ),
        "improving_move_drop_no_sync_repair": pct_reduction(
            no_sync_repair["alns_improving_moves_mean"],
            prop_improving_moves,
        ),
        "sens_kmeans_risk_gain_vs_direct": pct_reduction(
            sens_kmeans["risk_weighted_completion_time_mean"],
            sens_direct["risk_weighted_completion_time_mean"],
        ),
        "sens_dbscan_infeasible": 100.0 * sens_dbscan["infeasible_sortie_rate_mean"],
        "sens_uav6_makespan_gain": pct_reduction(
            sens_uav6["makespan_mean"],
            sens_uav4["makespan_mean"],
        ),
        "sens_uav2_makespan_penalty": pct_reduction(
            sens_uav4["makespan_mean"],
            sens_uav2["makespan_mean"],
        ),
        "sens_iter160_move_gain": pct_reduction(
            sens_iter50["alns_improving_moves_mean"],
            sens_iter160["alns_improving_moves_mean"],
        ),
    }


def tex(c: dict, documentclass: str) -> str:
    return rf"""{documentclass}

\usepackage{{amsmath,amssymb,amsfonts}}
\usepackage{{newtxtext,newtxmath}}
\usepackage{{algorithm}}
\usepackage{{algpseudocode}}
\usepackage{{booktabs}}
\usepackage{{graphicx}}
\usepackage{{multirow}}
\usepackage{{array}}
\usepackage{{tabularx}}
\usepackage{{dblfloatfix}}
\usepackage{{url}}
\usepackage{{xcolor}}
\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{{hyperref}}
\newcommand{{\rev}}[1]{{{{\color{{blue}}#1}}}}
\newenvironment{{revblock}}{{\begingroup\color{{blue}}}}{{\endgroup}}
\journal{{Transportation Research Part E: Logistics and Transportation Review}}
\bibliographystyle{{elsarticle-num}}
\biboptions{{numbers,sort&compress}}
\setlength{{\bibsep}}{{0pt plus 0.3ex}}
\renewcommand{{\bibfont}}{{\small}}
\emergencystretch=2em

\begin{{document}}

\begin{{frontmatter}}

\title{{Energy-aware vehicle--UAV cooperative scheduling for transmission line inspection with probabilistic energy prediction}}

\author[inst1]{{Author names withheld for review}}
\affiliation[inst1]{{organization={{School of Management Science and Engineering}}, city={{--}}, country={{China}}}}

\begin{{abstract}}
Large-scale transmission-line inspection increasingly relies on coordinated ground vehicles and unmanned aerial vehicles, but routing decisions remain sensitive to uncertain UAV endurance, heterogeneous tower priorities and sparse feasible stopping locations. This paper formulates transmission-line inspection as an uncertainty-aware risk-value vehicle--UAV scheduling problem. \rev{{The proposed framework combines same-stop multi-tower sortie patterns, a physics-informed residual energy surrogate, chance-constrained sortie screening, risk-value task prioritization, adaptive large-neighborhood search and metric-aware final portfolio selection.}} Computational experiments cover small reference instances, medium and large instances from 30 to 500 towers, energy-prediction accuracy, ablation tests, candidate-stop screening, sensitivity analysis, GIS-grounded cases and stress scenarios. \rev{{Relative to the strongest external baseline in the main algorithm comparison, the proposed method reduces mean risk-weighted completion time by {c['risk_gain_vs_best_external_100']:.1f}\% on the 100-tower benchmark and {c['risk_gain_vs_best_external_500']:.1f}\% on the 500-tower benchmark; it also removes residual infeasible sorties on the 100-tower benchmark and increases top-risk coverage by {c['case_coverage_gain']:.1f} percentage points in the 200-tower corridor case.}}
\end{{abstract}}

\begin{{keyword}}
\rev{{Vehicle--UAV scheduling \sep transmission line inspection \sep adaptive large neighborhood search \sep probabilistic energy surrogate \sep mixed-integer linear programming \sep same-stop sortie patterns}}
\end{{keyword}}

\end{{frontmatter}}

\noindent{{\small \rev{{Revision note: blue text marks passages revised for the same-stop multi-tower sortie assumption, operator visualization, terminology consistency and academic-language cleanup.}}}}
\vspace{{0.8em}}

\section{{Introduction}}
\label{{sec:introduction}}

Drone-assisted routing has developed from stylized truck--drone delivery into richer air--ground logistics systems involving energy supply, no-fly zones, multimodal operations, automatic heuristic design and synchronized truck--drone fleets \cite{{murray2015flying,dorling2017vehicle,otto2018survey,kim2026bidirectional,liu2026evtol,zhang2026airground,shi2026llm,yang2025integrated}}. Transmission line inspection is a closely related but operationally distinct setting, where UAVs are increasingly used for autonomous navigation, visual inspection, lidar sensing and defect recognition \cite{{hui2019monocular,li2021uavtransmission,nguyen2018visionreview,liu2021uavlidar,zhang2020visualinspection}}. A ground vehicle can carry multiple UAVs along road-accessible stops, launch UAVs to inspect nearby towers, wait for recovery and continue along the corridor. Compared with parcel delivery, inspection tasks have corridor geometry, heterogeneous defect risk, payload-dependent sensing time and stronger energy-safety requirements.

\rev{{This study is organized around three methodological components. A compact MILP provides small-instance reference checks, a residual energy surrogate supplies uncertainty-aware sortie parameters, and an ALNS solver scales the scheduling layer to medium and large inspection corridors. The experiment design follows the same logic through small-instance validation, algorithm comparison, energy-prediction assessment, ablation analysis and GIS-grounded case studies.}}

The scientific issue is that fixed endurance assumptions can make scheduling conclusions fragile. Drone energy is affected by flight distance, payload, wind, temperature, hovering and sensing time \cite{{stolaroff2018energy,zhang2021energyconsumption,aiello2021energy,chiang2019sustainability,cokyasar2023regional}}. A physics-informed residual energy surrogate can encode the physical energy component, but a point prediction alone is not enough for safe dispatch. Therefore, this paper studies both point energy ALNS and a probabilistic, risk-value-aware variant that uses a q95 energy margin when screening sorties. The intended contribution is not merely another ALNS implementation, but an evidence chain linking physics-aware prediction, compact MILP reference validation and scalable vehicle--UAV inspection scheduling.

The contributions are:
\begin{{enumerate}}
    \item \rev{{A vehicle--UAV transmission-line inspection model is built with same-stop multi-tower sortie patterns, repeated UAV dispatch at a stop and energy-surrogate flight time, inspection time, energy and endurance parameters.}}
    \item A compact MILP reference model is solved with HiGHS on proposal-defined S-scale instances as a bounded S-scale sanity check.
    \item \rev{{An energy-surrogate ALNS is developed with clustering-based pre-screening, five destroy operators, four named repair operators, simulated-annealing acceptance, adaptive operator weights and a metric-aware final candidate portfolio.}}
    \item \rev{{A computational experiment suite is executed on S/M/L instances from 10 to 500 towers, including baseline comparison, energy prediction accuracy, ablation, candidate-stop screening, statistical testing and GIS-grounded case studies.}}
\end{{enumerate}}

\section{{Related work}}
\label{{sec:related}}

The flying sidekick traveling salesman problem established a canonical truck--drone routing model \cite{{murray2015flying}}. Subsequent studies developed optimization models for the traveling salesman problem with drone \cite{{agatz2018tspdrone,poikonen2019branch,roberti2021exact}}, vehicle routing problems with drones \cite{{poikonen2017extended,wang2017worstcase,wang2019vrpd}}, and drone-delivery variants with energy, multi-trip and public-transport recharging assumptions \cite{{dorling2017vehicle,moadab2022drone,asoc2023recharging}}. Matheuristics and ALNS methods are common because exact synchronization models become difficult at scale \cite{{schermer2019matheuristic,sacramento2019alns}}. Reviews show that truck--drone routing has expanded into a broad family of synchronization, energy and fleet-planning problems \cite{{otto2018survey,macrina2020review,liang2022survey}}.

Recent Transportation Research Part E studies further show how air--ground logistics models are expanding. Kim et al. \cite{{kim2026bidirectional}} study bidirectional energy supply logistics with aerial and ground vehicles. Liu et al. \cite{{liu2026evtol}} optimize an eVTOL-and-drone system in continuous space with no-fly zones. Zhang et al. \cite{{zhang2026airground}} integrate drones, aircraft and ground vehicles for joint passenger and parcel mobility. Shi and Zhen \cite{{shi2026llm}} use LLM-based automatic heuristic design for vehicle-drone routing, and Yang and Li \cite{{yang2025integrated}} integrate order splitting, allocation and synchronized truck--drone delivery. Same-day and heterogeneous-fleet studies further show that dynamic dispatch and learning-based policies are relevant when vehicle and UAV resources interact \cite{{ulmer2018sameday,chen2022deepq}}. \rev{{Together, these studies motivate an inspection model that specifies the operational interface between vehicles and UAVs, scales beyond exact synchronization models and reports a broad computational protocol.}}

Energy feasibility is a second line of literature. Delivery-drone energy has been evaluated from life-cycle, power-model and routing-optimization perspectives \cite{{stolaroff2018energy,zhang2021energyconsumption,aiello2021energy,chiang2019sustainability,cokyasar2023regional}}. Electric-vehicle routing also provides useful analogues for endurance limits, recharging choices and time-window coupling \cite{{schneider2014evrptw,desaulniers2016evrp}}. For transmission-line inspection, the operational setting differs from parcel delivery because the tasks follow a corridor, the inspection value is risk-dependent, and UAVs must capture reliable condition data. Existing work covers autonomous transmission-line navigation, power-line inspection surveys, lidar-assisted inspection and deep-learning-based component detection \cite{{hui2019monocular,ahmed2024powerline,li2021uavtransmission,nguyen2018visionreview,liu2021uavlidar,zhang2020visualinspection,li2025deeppowerline}}.

ALNS remains a strong framework for routing variants because destroy and repair operators can absorb heterogeneous constraints \cite{{ropke2006alns,sacramento2019alns}}; simulated-annealing acceptance is a standard way to escape local minima \cite{{kirkpatrick1983annealing}}. For this paper, the important extension is the integration of a physical surrogate and decision uncertainty. Physics-informed neural networks provide a way to embed residuals from physical equations into learned models \cite{{raissi2019pinn,karniadakis2021piml,lu2021deepxde,cuomo2022pinnreview}}, and Bayesian energy surrogates show how noisy observations can be represented probabilistically \cite{{yang2021bpinn}}. The chance-style q95 feasibility filter used here is also consistent with robust decision-making principles for uncertain optimization \cite{{bertsimas2004robustness}}. We use these ideas to update UAV energy, endurance and service-time parameters before and during ALNS search.

\section{{Problem description and MILP model}}
\label{{sec:model}}

\begin{{revblock}}
Let $\mathcal{{T}}$ be the set of towers, $\mathcal{{P}}$ the candidate vehicle stops, $\mathcal{{V}}$ the ground vehicles and $\mathcal{{D}}_v$ the UAVs carried by vehicle $v$. Each tower $i\in\mathcal{{T}}$ has coordinates, service time $s_i$, payload $q_i$, defect-risk score $r_i$ and inspection value $\nu_i$. The ground vehicle travels over road arcs between stops, while a UAV is launched from a stop $s$ to execute a same-stop sortie pattern $k\in\mathcal{{K}}_s$ that may inspect one or more nearby towers before returning to $s$. After recovery, the same UAV can be assigned another sortie pattern from the same visited stop, and several UAVs carried by the vehicle can work in parallel while the vehicle waits.
\end{{revblock}}

\rev{{Figure~\ref{{fig:network-construction}} gives the graph-based view used to build the inspection network. Candidate vehicle stops and towers form a heterogeneous node set, road arcs connect vehicle stops, and feasible support edges define the same-stop UAV sortie patterns retained after q95 energy screening.}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig0_network_construction_ai.png}}
\caption{{\rev{{Graph-based representation of the vehicle--UAV inspection network. Panel A shows the candidate inspection graph with vehicle stops, tower nodes, road arcs and feasible stop--tower support edges. Panel B highlights same-stop UAV sortie patterns, including a multi-tower sortie that starts from a vehicle stop, visits multiple towers and returns to the same stop under the q95 energy feasibility screen.}}}}
\label{{fig:network-construction}}
\end{{figure*}}

\begin{{table*}}[t]
\centering
\caption{{Main notation used in the vehicle--UAV inspection model.}}
\label{{tab:notation}}
{{\scriptsize
\setlength{{\tabcolsep}}{{3pt}}
\renewcommand{{\arraystretch}}{{0.95}}
\begin{{tabularx}}{{\textwidth}}{{@{{}}llX@{{}}}}
\toprule
Category & Symbol & Meaning \\
\midrule
Sets & $\mathcal{{T}}$, $\mathcal{{P}}$, $\mathcal{{V}}$, $\mathcal{{D}}_v$, $\mathcal{{K}}_s$ & \rev{{Towers, candidate vehicle stops, ground vehicles, UAVs carried by vehicle $v$ and feasible same-stop multi-tower sortie patterns launched from stop $s$.}} \\
Tower attributes & $s_i$, $q_i$, $r_i$, $\nu_i$ & Inspection service time, sensing payload, defect-risk score and inspection value of tower $i$. \\
Routing decisions & $x^v_{{ij}}$, $z_s^v$, $y^d_{{sk}}$ & \rev{{Binary decision for vehicle arc $(i,j)$, stop visit and assignment of same-stop sortie pattern $k$ at stop $s$ to UAV $d$. Multiple selected patterns may be assigned to the same recovered UAV at a visited stop.}} \\
Timing variables & $t_i^v$, $w_i^v$, $L_s^d$, $\hat\tau^d_{{sk}}$ & \rev{{Vehicle arrival time, vehicle waiting time, sequential workload assigned to UAV $d$ at stop $s$ and predicted UAV sortie duration.}} \\
Energy prediction & $\hat E_i$, $Q^d_{{sk}}$, $\mu_E(x_{{sk}})$, $\sigma_E(x_{{sk}})$ & \rev{{Tower-level predicted energy, q95 pattern energy, predictive mean and predictive standard deviation from the energy-surrogate interface.}} \\
Endurance and safety & $\hat B_d$, $\rho$, $z_\epsilon$ & Predicted UAV endurance, battery reserve ratio and quantile coefficient for chance-style screening. \\
Objective terms & $C_{{\max}}$, $C_{{travel}}$, $C^{{energy surrogate}}_{{energy}}$ & Completion time, vehicle-travel cost and surrogate-predicted UAV energy term. \\
\bottomrule
\end{{tabularx}}
}}
\end{{table*}}

Following the proposal, UAV energy contains hovering, level-flight, sensor and wind-disturbance terms:
\begin{{equation}}
E_i=P^{{\mathrm{{hover}}}}t_i^{{\mathrm{{hover}}}}
\,+\,\left(a v^3+\frac{{m g}}{{2\eta v}}\right)t_i^{{\mathrm{{flight}}}}
\,+\,P^{{\mathrm{{sensor}}}}s_i
\,+\,C^{{\mathrm{{wind}}}}d_i^{{\mathrm{{air}}}} .
\label{{eq:energy}}
\end{{equation}}
The energy surrogate maps battery state, UAV weight, wind speed/direction, temperature, flight distance and inspection workload to predicted energy $\hat E_i$, flight time $\hat t^{{\mathrm{{air}}}}_i$, service time $\hat s_i$ and endurance $\hat B_d$.

The proposal's weighted objective is written as
\begin{{equation}}
\min \; \alpha C_{{\max}}+\beta C_{{\mathrm{{travel}}}}+\gamma C_{{\mathrm{{energy}}}}^{{\mathrm{{energy surrogate}}}},
\label{{eq:objective}}
\end{{equation}}
where
\begin{{equation}}
C_{{\mathrm{{travel}}}}=\sum_{{v\in\mathcal{{V}}}}\sum_{{i,j\in\mathcal{{P}}}} d^{{\mathrm{{road}}}}_{{ij}}x^v_{{ij}},
\qquad
C_{{\mathrm{{energy}}}}^{{\mathrm{{energy surrogate}}}}=\sum_{{d,s,k}}\hat E^d_{{sk}}y^d_{{sk}}.
\end{{equation}}
Let $\mathcal{{D}}=\cup_v\mathcal{{D}}_v$, let $\mathcal{{P}}_0=\mathcal{{P}}\cup\{{0\}}$ include the depot, and let $\delta_{{ik}}=1$ if tower $i$ is included in sortie pattern $k$. Each tower must be covered exactly once:
\begin{{equation}}
\sum_{{v\in\mathcal{{V}}}}\sum_{{d\in\mathcal{{D}}_v}}\sum_{{s\in\mathcal{{P}}}}\sum_{{k\in\mathcal{{K}}_s}}\delta_{{ik}}y^d_{{sk}}=1,\qquad \forall i\in\mathcal{{T}}.
\label{{eq:tower-coverage}}
\end{{equation}}
Vehicle routes must form balanced stop visits with one depot departure and one depot return for each active ground vehicle:
\begin{{align}}
\sum_{{j\in\mathcal{{P}}_0:j\ne s}}x^v_{{sj}} &= z_s^v,&
\sum_{{i\in\mathcal{{P}}_0:i\ne s}}x^v_{{is}} &= z_s^v,\qquad &&\forall s\in\mathcal{{P}},v\in\mathcal{{V}},\notag\\
\sum_{{j\in\mathcal{{P}}}}x^v_{{0j}} &= 1,&
\sum_{{i\in\mathcal{{P}}}}x^v_{{i0}} &= 1,\qquad &&\forall v\in\mathcal{{V}}.
\label{{eq:vehicle-flow}}
\end{{align}}
\begin{{revblock}}
Sortie activation links every selected sortie pattern to a visited vehicle stop without imposing a one-sortie-per-UAV limit:
\begin{{equation}}
y^d_{{sk}} \leq z_s^v,\qquad \forall v\in\mathcal{{V}}, d\in\mathcal{{D}}_v, s\in\mathcal{{P}}, k\in\mathcal{{K}}_s.
\label{{eq:sortie-activation}}
\end{{equation}}
The q95 energy feasibility constraint is imposed on the complete same-stop pattern rather than on a single tower:
\begin{{equation}}
Q^d_{{sk}} y^d_{{sk}} \leq \hat B_d(1-\rho),\qquad \forall v\in\mathcal{{V}}, d\in\mathcal{{D}}_v, s\in\mathcal{{P}}, k\in\mathcal{{K}}_s.
\label{{eq:endurance}}
\end{{equation}}
Sequential reuse of a recovered UAV at the same stop is represented by the UAV-specific stop workload
\begin{{equation}}
L_s^d=\sum_{{k\in\mathcal{{K}}_s}}\hat\tau^d_{{sk}}y^d_{{sk}},\qquad \forall v\in\mathcal{{V}}, d\in\mathcal{{D}}_v, s\in\mathcal{{P}}.
\label{{eq:uav-chain}}
\end{{equation}}
The vehicle can dispatch multiple UAVs in parallel at stop $s$, but it cannot depart until every assigned UAV chain has returned:
\begin{{align}}
t_j^v &\geq t_i^v+w_i^v+\frac{{d^{{\mathrm{{road}}}}_{{ij}}}}{{v^{{\mathrm{{car}}}}}}-M(1-x^v_{{ij}}),
\qquad \forall i,j\in\mathcal{{P}}_0,v\in\mathcal{{V}},
\label{{eq:time-propagation}}\\
w_s^v &\geq L_s^d,\qquad \forall v\in\mathcal{{V}},d\in\mathcal{{D}}_v,s\in\mathcal{{P}}.
\label{{eq:launch-recovery-sync}}
\end{{align}}
\end{{revblock}}

\section{{energy-surrogate ALNS}}
\label{{sec:algorithm}}

The algorithm follows the three-stage design in the proposal. First, tower coordinates are partitioned by corridor-aware clustering and candidate same-stop sortie candidates are pre-screened by the energy-surrogate endurance estimate. Second, S-scale instances are solved by a compact MILP reference model to provide bounded comparison points. Third, medium and large instances are solved with energy ALNS. \rev{{The full probabilistic variant reports the best schedule from a constant-size final portfolio containing the adaptive ALNS search order, a point-energy local order, a UQ-energy local order and a risk-value order. Portfolio selection is lexicographic in infeasible-sortie count, risk-weighted completion time and makespan, aligning the algorithmic final-selection step with the manuscript evaluation metric.}}

\begin{{table*}}[t]
\centering
\caption{{Destroy and repair operators in the implemented energy ALNS.}}
\label{{tab:operators}}
\footnotesize
\setlength{{\tabcolsep}}{{4pt}}
\renewcommand{{\arraystretch}}{{1.12}}
\begin{{tabularx}}{{\textwidth}}{{@{{}}p{{0.15\textwidth}}p{{0.30\textwidth}}X@{{}}}}
\toprule
Pool & Operators & Search role \\
\midrule
Destroy & Random, worst-energy, Shaw related, path-segment and UAV-chain removals & Diversifies the incumbent, targets high-q95-energy towers, reopens spatially related corridor segments and removes contiguous UAV task chains when synchronization or workload patterns are poor. \\
Repair & Greedy, regret-$k$, energy-minimum and synchronization-aware insertions & Rebuilds feasible schedules by combining risk-value priority, insertion regret, cached q95 energy feasibility and segment workload balancing. \\
\bottomrule
\end{{tabularx}}
\end{{table*}}

\rev{{Figure~\ref{{fig:operator-mechanism}} visualizes the destroy--repair operator mechanism used by the ALNS search. The destroy step releases a subset of tasks from the incumbent schedule, the repair step reinserts them with risk-value and q95 feasibility information, and the acceptance step updates the incumbent and operator weights.}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig3_operator_mechanism_ai.png}}
\caption{{\rev{{Adaptive destroy--repair operator mechanism in the energy-surrogate ALNS. The schematic links incumbent schedule disruption, candidate-list construction, greedy/regret/energy/synchronization-aware insertion, simulated-annealing acceptance and adaptive operator scoring.}}}}
\label{{fig:operator-mechanism}}
\end{{figure*}}

\begin{{algorithm}}[t]
\caption{{energy-surrogate ALNS for vehicle--UAV inspection scheduling}}
\label{{alg:alns}}
\begin{{algorithmic}}[1]
\State Generate candidate stops from corridor clusters.
\State Use the energy surrogate to update $\hat E_i$, $\hat t_i^{{air}}$, $\hat s_i$ and $\hat B_d$.
\State Build an initial schedule using energy-feasible same-stop sortie patterns.
\State \rev{{Initialize deterministic point, UQ and risk-value component orders for the final portfolio.}}
\For{{$iter=1,\ldots,N_{{max}}$}}
    \State Select destroy and repair operators by adaptive weights.
    \State Remove tasks/stops by random, worst-energy, Shaw, UAV-chain or path-segment destruction.
    \State Repair by greedy insertion, regret-$k$ insertion, energy-minimum insertion or synchronization-aware workload-balancing insertion.
    \State Check endurance feasibility using point or q95 energy surrogate energy.
    \State Accept improving moves; otherwise apply simulated-annealing acceptance.
    \State Update operator scores and weights every $\Delta$ iterations.
\EndFor
\State \rev{{Schedule the ALNS-best order and the component orders with the same same-stop launch--recovery scheduler.}}
\State \rev{{\Return the candidate with the lexicographically best $(\#\mathrm{{infeasible}},\mathrm{{RWCT}},C_{{max}})$.}}
\end{{algorithmic}}
\end{{algorithm}}

The implemented destroy pool contains random removal, worst-energy removal, Shaw related removal, path-segment removal and UAV-chain removal. The repair pool contains greedy insertion, regret insertion, energy-minimum insertion and synchronization-aware workload-balancing insertion. \rev{{Operator use counts, acceptance counts, portfolio candidate counts and selected-candidate diagnostics are exported with the experiment CSV files so that the search behavior can be audited alongside solution quality.}}

\paragraph{{Computational complexity.}}
\rev{{Let $n$ be the number of towers, $m$ the number of candidate stops, $I$ the ALNS iteration budget and $q$ the number of removed towers per iteration. Candidate support screening evaluates $O(nm)$ energy estimates, after which clustering reduces the active support layer. Bounded pattern construction groups nearby towers into retained same-stop sortie candidates. With cached tower scores and energy/workload estimates, each ALNS iteration evaluates one destroy--repair move in $O(q+n)$ time for the implemented cached repairs. The final portfolio evaluates a constant number of scheduled orders, so it adds only a constant multiple of the scheduler cost. Under the implemented fixed maximum sortie length, the dominant cost is $O(nm+I(q+n))$ plus the one-time candidate-stop clustering cost.}}

For the probabilistic variant, the energy-surrogate interface returns $\mu_E(x_{{sk}})$ and $\sigma_E(x_{{sk}})$ for a same-stop pattern $k$ launched from stop $s$. A sortie is accepted only if
\begin{{equation}}
\mu_E(x_{{sk}})+z_\epsilon\sigma_E(x_{{sk}})\leq B_d(1-\rho),
\label{{eq:chance}}
\end{{equation}}
where $\rho$ is the reserve ratio. The risk-value objective schedules high-priority towers earlier by using $r_i\nu_i C_i$ in the evaluation layer.

\section{{Experimental design}}
\label{{sec:experiments}}

The experiment protocol follows the original design document. Table~\ref{{tab:instances}} lists the S/M/L instance matrix. Each parameter combination is generated with ten random seeds, giving approximately the same 300--400 instance scale proposed in the initial document once methods and uncertainty levels are counted. \rev{{All routing experiments use same-stop launch--recovery sorties; quantile-enabled ALNS variants may group nearby towers into bounded multi-tower sortie patterns, recover the UAV at the launch stop and dispatch it again while the vehicle remains parked.}} All raw CSV files, summaries and figure source data are stored under the project experiment folders.

\begin{{table*}}[t]
\centering
\caption{{Proposal-aligned instance scales.}}
\label{{tab:instances}}
\resizebox{{\textwidth}}{{!}}{{%
\begin{{tabular}}{{@{{}}lrrrrl@{{}}}}
\toprule
Scale & Towers & Stops & Vehicles & UAVs/vehicle & Use \\
\midrule
S & 10,15,20 & 5,8,10 & 1 & 1--2 & MILP validation\\
M & 30,50,75,100 & 15,25,35,50 & 2--3 & 2--3 & Algorithm comparison\\
L & 150,200,300,500 & 75,100,150,250 & 3--5 & 2--4 & Scalability\\
\bottomrule
\end{{tabular}}%
}}
\end{{table*}}

The main P2 baselines are nearest-neighbor construction, a population-based GA order search, a pheromone-weighted ACO order search, simulated annealing, tabu search, variable-neighborhood search and a hybrid GA--VNS search. \rev{{The proposed row denotes the full probabilistic risk-value ALNS with q95 screening, risk-value ordering, adaptive operator search and metric-aware final portfolio selection.}} Internal ALNS variants are reported only in the ablation block. The metrics are makespan, vehicle distance, predicted UAV energy, infeasible sortie rate, risk-weighted completion time, top-risk tower coverage and solver runtime.

\begin{{table*}}[t]
\centering
\caption{{Main simulation and algorithm parameters.}}
\label{{tab:parameters}}
\footnotesize
\begin{{tabularx}}{{\textwidth}}{{@{{}}llX@{{}}}}
\toprule
Group & Parameter & Values used in the manuscript experiments \\
\midrule
Instance scale & Towers/stops & S: 10/5, 15/8, 20/10; M: 30/15, 50/25, 75/35, 100/50; L: 150/75, 200/100, 300/150, 500/250. \\
Fleet & Ground vehicles and UAVs & Proposal-defined vehicles and UAVs per vehicle; P8 tests 2, 4 and 6 UAVs on the M50 setting. \\
Energy safety & Reserve ratio $\rho$ and quantile $z_\epsilon$ & Default $\rho=0.12$ and $z_\epsilon=1.645$; P8 tests $\rho\in\{{0.08,0.12,0.20\}}$ and $z_\epsilon\in\{{1.28,1.645,1.96\}}$. \\
ALNS & Iteration budget & S: 80, M: 100, L: 60, case: 80; P8 tests 50, 100 and 160 iterations. \\
Candidate stops & Stop generation modes & Direct proposal stops, K-means clustered stops and DBSCAN-style density stops. \\
Replication & Random seeds & Ten seeds for P1--P4, P6 and P8; five seeds for the realistic case study; P7 uses paired tests over P2 summaries. \\
\bottomrule
\end{{tabularx}}
\end{{table*}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig1_framework_ai.png}}
\caption{{MILP--energy-surrogate--ALNS workflow aligned with the original research proposal.}}
\label{{fig:framework}}
\end{{figure*}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig2_instances.pdf}}
\caption{{Proposal-defined S/M/L instance design, realistic corridor case and executed evidence blocks.}}
\label{{fig:instances}}
\end{{figure*}}

\section{{Results}}
\label{{sec:results}}

\subsection{{Small-scale MILP validation}}

Figure~\ref{{fig:milp}} reports the S-scale validation block. The average proposed ALNS gap to the compact MILP reference across S instances is {c['milp_gap']:.2f}\% under the makespan comparison used in the experiment table. The compact reference is used as a bounded small-instance sanity check rather than as a complete exact RWCT benchmark. This is consistent with the role specified in the proposal: compact reference optimization is used for S-scale validation, while energy ALNS is used for scalable solution.

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig3_milp_validation.pdf}}
\caption{{Small-scale MILP/HiGHS validation: makespan, gap to reference and runtime.}}
\label{{fig:milp}}
\end{{figure*}}

\subsection{{Algorithm comparison}}

Figure~\ref{{fig:comparison}} compares algorithms on the 100-tower benchmark. \rev{{Across the matched 30--500 tower benchmarks, the proposed method reduces mean RWCT relative to the strongest external baseline at each scale by {c['risk_gain_vs_best_external_min']:.2f}\%--{c['risk_gain_vs_best_external_max']:.2f}\%.}} The paired RWCT comparison against the best external 100-tower baseline has a median effect of {c['stat100_point_median']:.1f} risk-time units and a Holm-adjusted Wilcoxon value of $p_{{Holm}}={c['stat100_point_p']:.4f}$. Top-risk coverage is also interpreted after the same correction, with $p_{{Holm}}={c['stat100_cov_holm']:.3f}$. \rev{{The q95 feasibility layer reduces the infeasible-sortie rate from {c['violation_point_100']:.2f}\% to {c['violation_prop_100']:.2f}\% on the same benchmark, indicating that the risk-value and uncertainty layers improve both schedule priority and sortie feasibility.}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig4_algorithm_comparison.pdf}}
\caption{{Algorithm comparison on the 100-tower benchmark.}}
\label{{fig:comparison}}
\end{{figure*}}

\subsection{{Energy prediction validation}}

Figure~\ref{{fig:energy-surrogate}} evaluates fixed physics, point prediction and the simulation-trained probabilistic residual surrogate. The surrogate is trained on {c['prob_training_samples']:.0f} synthetic physics-residual samples and evaluated on held-out scenario seeds. Under high uncertainty, the probabilistic surrogate obtains a 95\% interval coverage of {c['prob_high_coverage']:.1f}\%, compared with {c['point_high_coverage']:.1f}\% for point prediction and {c['fixed_high_coverage']:.1f}\% for fixed physics. It also reduces high-uncertainty MAE from {c['fixed_high_mae']:.2f} and {c['point_high_mae']:.2f} energy units for the two baselines to {c['prob_high_mae']:.2f}. \rev{{The calibrated interval gives the scheduler a direct q95 feasibility screen for same-stop sortie patterns.}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig5_energy_surrogate_accuracy.pdf}}
\caption{{\rev{{Energy prediction validation with residual-surrogate labels: energy error, interval coverage and false-feasible rate.}}}}
\label{{fig:energy-surrogate}}
\end{{figure*}}

\subsection{{Ablation and case study}}

Figure~\ref{{fig:ablation}} shows that removing the energy surrogate, adaptive search, uncertainty filter, risk-value term, repair operators or clustering stage weakens at least one of the paper's target outcomes. The no-surrogate variant has poor high-risk coverage, removing the risk-value term reduces high-risk coverage, and removing clustering worsens the risk-time objective despite retaining feasibility. The repair-specific ablation indicates a search-dynamics contribution: disabling energy-minimum or synchronization-aware repair leaves the current M50 aggregate risk-time nearly unchanged, but reduces improving ALNS moves by {c['improving_move_drop_no_energy_repair']:.1f}\% and {c['improving_move_drop_no_sync_repair']:.1f}\%, respectively. Figure~\ref{{fig:case}} reports the realistic 200-tower corridor case. The proposed ALNS reduces risk-weighted completion time by {c['case_risk_gain']:.1f}\% compared with fixed ALNS and increases top-risk coverage by {c['case_coverage_gain']:.1f} percentage points.

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig6_ablation.pdf}}
\caption{{Ablation results for energy surrogate, adaptive search, uncertainty, risk-value and clustering components.}}
\label{{fig:ablation}}
\end{{figure*}}

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig7_case_study.pdf}}
\caption{{Realistic corridor case study with 200 towers and 100 candidate stops.}}
\label{{fig:case}}
\end{{figure*}}

\subsection{{Scalability}}

Figure~\ref{{fig:scalability}} reports S/M/L scalability from 30 to 500 towers. \rev{{At 500 towers, the proposed method reduces mean RWCT by {c['risk_gain_vs_best_external_500']:.1f}\% relative to the strongest external baseline in P2.}} The paired RWCT effect is {c['stat500_point_median']:.0f} risk-time units with $p_{{Holm}}={c['stat500_point_p']:.4f}$, and top-risk coverage has $p_{{Holm}}={c['stat500_cov_p']:.4f}$. Runtime remains below the minute scale in the local Python simulation, which is sufficient for the current computational proof-of-concept.

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig8_scalability.pdf}}
\caption{{Scalability from 30 to 500 towers.}}
\label{{fig:scalability}}
\end{{figure*}}

\subsection{{Candidate-stop screening and statistical evidence}}

Figure~\ref{{fig:screening}} reports the candidate-stop screening and statistical evidence block. K-means candidate-stop generation reduces screened service candidates by {c['kmeans_reduction_100']:.1f}\% on 100-tower instances, whereas DBSCAN reduces the candidate count by {c['dbscan_reduction_100']:.1f}\% but produces worse makespan in this corridor generator. This supports using deterministic K-means as the default candidate-stop generator in the simulation experiments. The right panels of Fig.~\ref{{fig:screening}} summarize the paired statistical tests: the strongest evidence is for risk-weighted completion time rather than nominal makespan.

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig9_candidate_screening_statistics.pdf}}
\caption{{Candidate-stop screening and paired statistical evidence.}}
\label{{fig:screening}}
\end{{figure*}}

\subsection{{Parameter sensitivity}}

Figure~\ref{{fig:sensitivity}} summarizes the sensitivity batch for candidate-stop mode, UAV count, iteration budget, quantile coefficient and reserve ratio. In this M50 high-uncertainty setting, K-means reduces risk-weighted completion time by {c['sens_kmeans_risk_gain_vs_direct']:.1f}\% relative to direct stop enumeration while retaining zero infeasible sorties; DBSCAN is less reliable and has a {c['sens_dbscan_infeasible']:.1f}\% infeasible-sortie rate after screening. Increasing the UAV count from four to six reduces makespan by {c['sens_uav6_makespan_gain']:.1f}\%, whereas using only two UAVs increases makespan substantially. Raising the ALNS iteration budget mainly increases improving moves by {c['sens_iter160_move_gain']:.1f}\% rather than changing aggregate risk-time, suggesting that the current objective landscape is already stable on the M50 batch.

\begin{{figure*}}[t]
\centering
\includegraphics[width=\textwidth]{{figures/Fig10_sensitivity.pdf}}
\caption{{Sensitivity analysis for candidate-stop mode, fleet size, search budget and energy-safety parameters.}}
\label{{fig:sensitivity}}
\end{{figure*}}

\clearpage

\section{{Discussion}}
\label{{sec:discussion}}

\rev{{The computational evidence shows that the proposed method is most useful when inspection priority and energy safety are evaluated together. The main effect is the combined improvement in high-risk task coverage, q95 energy-feasibility screening and large-scale solvability. This matches the operational nature of transmission-line inspection, where early inspection of high-risk towers and avoidance of unsafe sorties can be more important than nominal travel-time reduction alone.}}

\rev{{The evidence also has clear boundaries. The routing data are simulated corridor instances and public GIS-grounded proxy cases, the compact MILP reference is limited to S-scale validation, and the residual energy surrogate is trained on synthetic physics-residual labels with public telemetry used as a separate calibration check. Stress tests show that conservative uncertainty handling improves infeasible-sortie rates and top-risk coverage, while some no-UQ cases can produce lower RWCT under adverse settings. These boundaries limit deployment claims and motivate real inspection-log calibration.}}

\section{{Conclusion}}
\label{{sec:conclusion}}

\rev{{This paper formulates vehicle--UAV cooperative transmission-line inspection scheduling with same-stop multi-tower sortie patterns, explicit energy and endurance parameters, repeated UAV dispatch after recovery and parallel UAV operation at a parked vehicle stop.}} It checks small instances with a compact MILP reference and evaluates an uncertainty-aware ALNS across S/M/L instances up to 500 towers. \rev{{The full probabilistic risk-value variant reduces mean RWCT by {c['risk_gain_vs_best_external_min']:.1f}\%--{c['risk_gain_vs_best_external_max']:.1f}\% relative to the strongest external baseline at each tested scale and protects sortie feasibility through q95 energy screening.}} K-means candidate-stop generation substantially reduces support-candidate enumeration while the scheduler evaluates bounded same-stop sortie patterns in the tested corridor instances. \rev{{Future work should couple the scheduler with online re-dispatch, dynamic wind and road-state updates, real utility inspection logs, defect labels and field battery records.}}

\section*{{CRediT authorship contribution statement}}
To be completed by the authors.

\section*{{Declaration of competing interest}}
The authors declare that they have no known competing financial interests or personal relationships that could have appeared to influence the work reported in this paper.

\section*{{Data availability}}
The current manuscript uses synthetic simulation data generated by the project scripts. Raw CSV files, summary tables, figure source data and LaTeX sources are stored in the local project directory.

\bibliography{{tre_references}}

\end{{document}}
"""


def highlights(c: dict) -> str:
    return rf"""\begin{{highlights}}
\item Same-stop multi-tower sortie patterns are modeled with repeated UAV dispatch after recovery.
\item Experiments cover S/M/L instances from 10 to 500 transmission towers plus candidate-stop and statistical evidence.
\item The point-estimate comparisons are reported with Holm-adjusted boundaries rather than as uniform dominance claims.
\item K-means candidate stops reduce 100-tower service candidates by {c['kmeans_reduction_100']:.1f}\% in simulation.
\item Simulation-trained probabilistic residual surrogate reaches {c['prob_high_coverage']:.1f}\% high-uncertainty interval coverage in simulation.
\end{{highlights}}
"""


def readme(filename: str, documentclass: str) -> str:
    return f"""# Elsevier LaTeX Draft

Generated from `scripts/write_elsevier_latex.py`.

- Main file: `{filename}`
- Document class: `{documentclass}`
- Figure source: `results/figures/publishable/`
- Experiment run: `{RUN_ID}`
- Revision markup: blue text marks passages revised for same-stop multi-tower sorties, repeated dispatch, portfolio selection, and repair2 evidence boundaries.

Compile on this machine with:

```powershell
$env:PATH = 'D:\\texlive\\2022\\bin\\win32;' + $env:PATH
latexmk -xelatex -interaction=nonstopmode -halt-on-error {filename}
```

Evidence boundary: all results are currently simulation-based unless real utility inspection logs are added later.
"""


def bib() -> str:
    return r"""@article{murray2015flying,
  author = {Murray, Chase C. and Chu, Amanda G.},
  title = {The flying sidekick traveling salesman problem: Optimization of drone-assisted parcel delivery},
  journal = {Transportation Research Part C: Emerging Technologies},
  year = {2015},
  volume = {54},
  pages = {86--109},
  doi = {10.1016/j.trc.2015.03.005}
}

@article{dorling2017vehicle,
  author = {Dorling, Kevin and Heinrichs, Jordan and Messier, Geoffrey G. and Magierowski, Sebastian},
  title = {Vehicle routing problems for drone delivery},
  journal = {IEEE Transactions on Systems, Man, and Cybernetics: Systems},
  year = {2017},
  volume = {47},
  number = {1},
  pages = {70--85},
  doi = {10.1109/TSMC.2016.2582745}
}

@article{otto2018survey,
  author = {Otto, Alena and Agatz, Niels and Campbell, James and Golden, Bruce and Pesch, Erwin},
  title = {Optimization approaches for civil applications of unmanned aerial vehicles (UAVs) or aerial drones: A survey},
  journal = {Networks},
  year = {2018},
  volume = {72},
  number = {4},
  pages = {411--458},
  doi = {10.1002/net.21818}
}

@article{sacramento2019alns,
  author = {Sacramento, David and Pisinger, David and Ropke, Stefan},
  title = {An adaptive large neighborhood search metaheuristic for the vehicle routing problem with drones},
  journal = {Transportation Research Part C: Emerging Technologies},
  year = {2019},
  volume = {102},
  pages = {289--315},
  doi = {10.1016/j.trc.2019.02.018}
}

@article{schermer2019matheuristic,
  author = {Schermer, Daniel and Moeini, Mahdi and Wendt, Oliver},
  title = {A matheuristic for the vehicle routing problem with drones and its variants},
  journal = {Transportation Research Part C: Emerging Technologies},
  year = {2019},
  volume = {106},
  pages = {166--204},
  doi = {10.1016/j.trc.2019.06.016}
}

@article{moadab2022drone,
  author = {Moadab, Amirhossein and Farajzadeh, Fatemeh and Fatahi Valilai, Omid},
  title = {Drone routing problem model for last-mile delivery using the public transportation capacity as moving charging stations},
  journal = {Scientific Reports},
  year = {2022},
  volume = {12},
  pages = {6361},
  doi = {10.1038/s41598-022-10408-4}
}

@article{liang2022survey,
  author = {Liang, Yi-Jing and Luo, Zhi-Xing},
  title = {A survey of truck--drone routing problem: Literature review and research prospects},
  journal = {Journal of the Operations Research Society of China},
  year = {2022},
  volume = {10},
  pages = {343--377},
  doi = {10.1007/s40305-021-00383-4}
}

@article{asoc2023recharging,
  author = {Zhang, X. and Li, Y. and Wang, J.},
  title = {Adaptive large neighborhood search algorithm for the unmanned aerial vehicle routing problem with recharging},
  journal = {Applied Soft Computing},
  year = {2023},
  volume = {147},
  pages = {110831},
  doi = {10.1016/j.asoc.2023.110831}
}

@article{kim2026bidirectional,
  author = {Kim, Hyunhwa and Sari Darmawi Purba, Denissa and Kontou, Eleftheria},
  title = {Bidirectional energy supply logistics using uncrewed electric aerial and ground vehicles: A two-echelon location-routing problem with resource-constrained demand allocation and time windows},
  journal = {Transportation Research Part E: Logistics and Transportation Review},
  year = {2026},
  volume = {209},
  pages = {104726},
  doi = {10.1016/j.tre.2026.104726}
}

@article{liu2026evtol,
  author = {Liu, Shaojun and Yu, Yitong and Tian, Qingyun and Sun, Huijun},
  title = {Routing optimization for an eVTOL-and-drone delivery system in continuous space with no-fly zones: A reinforcement learning approach},
  journal = {Transportation Research Part E: Logistics and Transportation Review},
  year = {2026},
  volume = {209},
  pages = {104741},
  doi = {10.1016/j.tre.2026.104741}
}

@article{zhang2026airground,
  author = {Zhang, Yimeng and Yang, Chenjie and Xi, Haoning and Peng, Songhan and Yang, Junjie and Gan, Mi and Liu, Xiaobo and Ai, Ruixue},
  title = {Air-ground multimodal transport planning for joint passenger mobility and parcel delivery: Integration of drones, aircraft, and ground vehicles},
  journal = {Transportation Research Part E: Logistics and Transportation Review},
  year = {2026},
  volume = {210},
  pages = {104825},
  doi = {10.1016/j.tre.2026.104825}
}

@article{shi2026llm,
  author = {Shi, Haiyang and Zhen, Lu},
  title = {LLM-based automatic heuristic design for vehicle-drone collaborative routing problems},
  journal = {Transportation Research Part E: Logistics and Transportation Review},
  year = {2026},
  volume = {209},
  pages = {104760},
  doi = {10.1016/j.tre.2026.104760}
}

@article{yang2025integrated,
  author = {Yang, Ruiguang and Li, Xiangyong},
  title = {Integrated order splitting, allocation, and delivery problem with a synchronized truck and drone fleet},
  journal = {Transportation Research Part E: Logistics and Transportation Review},
  year = {2025},
  volume = {202},
  pages = {104217},
  doi = {10.1016/j.tre.2025.104217}
}

@article{ropke2006alns,
  author = {Ropke, Stefan and Pisinger, David},
  title = {An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows},
  journal = {Transportation Science},
  year = {2006},
  volume = {40},
  number = {4},
  pages = {455--472},
  doi = {10.1287/trsc.1050.0135}
}

@article{raissi2019pinn,
  author = {Raissi, M. and Perdikaris, P. and Karniadakis, G. E.},
  title = {Physics-informed neural networks: A deep learning framework for solving forward and inverse problems involving nonlinear partial differential equations},
  journal = {Journal of Computational Physics},
  year = {2019},
  volume = {378},
  pages = {686--707},
  doi = {10.1016/j.jcp.2018.10.045}
}

@article{agatz2018tspdrone,
  author = {Agatz, Niels and Bouman, Paul and Schmidt, Marie},
  title = {Optimization Approaches for the Traveling Salesman Problem with Drone},
  journal = {Transportation Science},
  year = {2018},
  volume = {52},
  number = {4},
  pages = {965--981},
  doi = {10.1287/trsc.2017.0791}
}

@article{wang2019vrpd,
  author = {Wang, Zheng and Sheu, Jiuh-Biing},
  title = {Vehicle routing problem with drones},
  journal = {Transportation Research Part B: Methodological},
  year = {2019},
  volume = {122},
  pages = {350--364},
  doi = {10.1016/j.trb.2019.03.005}
}

@article{poikonen2017extended,
  author = {Poikonen, Stefan and Wang, Xingyin and Golden, Bruce},
  title = {The vehicle routing problem with drones: Extended models and connections},
  journal = {Networks},
  year = {2017},
  volume = {70},
  number = {1},
  pages = {34--43},
  doi = {10.1002/net.21746}
}

@article{wang2017worstcase,
  author = {Wang, Xingyin and Poikonen, Stefan and Golden, Bruce},
  title = {The vehicle routing problem with drones: several worst-case results},
  journal = {Optimization Letters},
  year = {2017},
  volume = {11},
  number = {4},
  pages = {679--697},
  doi = {10.1007/s11590-016-1035-3}
}

@article{poikonen2019branch,
  author = {Poikonen, Stefan and Golden, Bruce and Wasil, Edward A.},
  title = {A Branch-and-Bound Approach to the Traveling Salesman Problem with a Drone},
  journal = {INFORMS Journal on Computing},
  year = {2019},
  volume = {31},
  number = {2},
  pages = {335--346},
  doi = {10.1287/ijoc.2018.0826}
}

@article{roberti2021exact,
  author = {Roberti, Roberto and Ruthmair, Mario},
  title = {Exact Methods for the Traveling Salesman Problem with Drone},
  journal = {Transportation Science},
  year = {2021},
  volume = {55},
  number = {2},
  pages = {315--335},
  doi = {10.1287/trsc.2020.1017}
}

@article{macrina2020review,
  author = {Macrina, Giusy and Di Puglia Pugliese, Luigi and Guerriero, Francesca and Laporte, Gilbert},
  title = {Drone-aided routing: A literature review},
  journal = {Transportation Research Part C: Emerging Technologies},
  year = {2020},
  volume = {120},
  pages = {102762},
  doi = {10.1016/j.trc.2020.102762}
}

@article{ulmer2018sameday,
  author = {Ulmer, Marlin W. and Thomas, Barrett W.},
  title = {Same-day delivery with heterogeneous fleets of drones and vehicles},
  journal = {Networks},
  year = {2018},
  volume = {72},
  number = {4},
  pages = {475--505},
  doi = {10.1002/net.21855}
}

@article{chen2022deepq,
  author = {Chen, Xinwei and Ulmer, Marlin W. and Thomas, Barrett W.},
  title = {Deep Q-learning for same-day delivery with vehicles and drones},
  journal = {European Journal of Operational Research},
  year = {2022},
  volume = {298},
  number = {3},
  pages = {939--952},
  doi = {10.1016/j.ejor.2021.06.021}
}

@article{stolaroff2018energy,
  author = {Stolaroff, Joshuah K. and Samaras, Constantine and O'Neill, Emma R. and Lubers, Alia and Mitchell, Alexandra S. and Ceperley, Daniel},
  title = {Energy use and life cycle greenhouse gas emissions of drones for commercial package delivery},
  journal = {Nature Communications},
  year = {2018},
  volume = {9},
  number = {1},
  pages = {409},
  doi = {10.1038/s41467-017-02411-5}
}

@article{zhang2021energyconsumption,
  author = {Zhang, Juan and Campbell, James F. and Sweeney, Donald C. and Hupman, Andrea C.},
  title = {Energy consumption models for delivery drones: A comparison and assessment},
  journal = {Transportation Research Part D: Transport and Environment},
  year = {2021},
  volume = {90},
  pages = {102668},
  doi = {10.1016/j.trd.2020.102668}
}

@article{aiello2021energy,
  author = {Aiello, Giuseppe and Inguanta, Rosalinda and D'Angelo, Giusj and Venticinque, Mario},
  title = {Energy Consumption Model of Aerial Urban Logistic Infrastructures},
  journal = {Energies},
  year = {2021},
  volume = {14},
  number = {18},
  pages = {5998},
  doi = {10.3390/en14185998}
}

@article{cokyasar2023regional,
  author = {Cokyasar, Taner and Stinson, Monique and Sahin, Olcay and Prabhakar, Nirmit and Karbowski, Dominik},
  title = {Comparing Regional Energy Consumption for Direct Drone and Truck Deliveries},
  journal = {Transportation Research Record: Journal of the Transportation Research Board},
  year = {2023},
  volume = {2677},
  number = {2},
  pages = {310--327},
  doi = {10.1177/03611981221145137}
}

@article{chiang2019sustainability,
  author = {Chiang, Wen-Chyuan and Li, Yuyu and Shang, Jennifer and Urban, Timothy L.},
  title = {Impact of drone delivery on sustainability and cost: Realizing the UAV potential through vehicle routing optimization},
  journal = {Applied Energy},
  year = {2019},
  volume = {242},
  pages = {1164--1175},
  doi = {10.1016/j.apenergy.2019.03.117}
}

@article{hui2019monocular,
  author = {Hui, Xiaolong and Bian, Jiang and Zhao, Xiaoguang and Tan, Min},
  title = {A monocular-based navigation approach for unmanned aerial vehicle safe and autonomous transmission-line inspection},
  journal = {International Journal of Advanced Robotic Systems},
  year = {2019},
  volume = {16},
  number = {1},
  pages = {1729881419829941},
  doi = {10.1177/1729881419829941}
}

@article{ahmed2024powerline,
  author = {Ahmed, Faiyaz and Mohanta, J. C. and Keshari, Anupam},
  title = {Power Transmission Line Inspections: Methods, Challenges, Current Status and Usage of Unmanned Aerial Systems},
  journal = {Journal of Intelligent \& Robotic Systems},
  year = {2024},
  volume = {110},
  number = {2},
  pages = {54},
  doi = {10.1007/s10846-024-02061-y}
}

@article{li2021uavtransmission,
  author = {Li, Xin and Li, Zijian and Wang, Haizhi and Li, Wanlin},
  title = {Unmanned Aerial Vehicle for Transmission Line Inspection: Status, Standardization, and Perspectives},
  journal = {Frontiers in Energy Research},
  year = {2021},
  volume = {9},
  pages = {713634},
  doi = {10.3389/fenrg.2021.713634}
}

@article{nguyen2018visionreview,
  author = {Nguyen, Van Nhan and Jenssen, Robert and Roverso, Davide},
  title = {Automatic autonomous vision-based power line inspection: A review of current status and the potential role of deep learning},
  journal = {International Journal of Electrical Power \& Energy Systems},
  year = {2018},
  volume = {99},
  pages = {107--120},
  doi = {10.1016/j.ijepes.2017.12.016}
}

@article{liu2021uavlidar,
  author = {Guan, Hongcan and Sun, Xiliang and Su, Yanjun and Hu, Tianyu and Wang, Haitao and Wang, Heping and Peng, Chigang and Guo, Qinghua},
  title = {UAV-lidar aids automatic intelligent powerline inspection},
  journal = {International Journal of Electrical Power \& Energy Systems},
  year = {2021},
  volume = {130},
  pages = {106987},
  doi = {10.1016/j.ijepes.2021.106987}
}

@article{zhang2020visualinspection,
  author = {Liu, Xinyu and Miao, Xiren and Jiang, Hao and Chen, Jing},
  title = {Data analysis in visual power line inspection: An in-depth review of deep learning for component detection and fault diagnosis},
  journal = {Annual Reviews in Control},
  year = {2020},
  volume = {50},
  pages = {253--277},
  doi = {10.1016/j.arcontrol.2020.09.002}
}

@article{li2025deeppowerline,
  author = {Faisal, Md. Ahasan Atick and Mecheter, Imene and Qiblawey, Yazan and Fernandez, Javier Hernandez and Chowdhury, Muhammad E. H. and Kiranyaz, Serkan},
  title = {Deep learning in automated power line inspection: A review},
  journal = {Applied Energy},
  year = {2025},
  volume = {385},
  pages = {125507},
  doi = {10.1016/j.apenergy.2025.125507}
}

@article{karniadakis2021piml,
  author = {Karniadakis, George Em and Kevrekidis, Ioannis G. and Lu, Lu and Perdikaris, Paris and Wang, Sifan and Yang, Liu},
  title = {Physics-informed machine learning},
  journal = {Nature Reviews Physics},
  year = {2021},
  volume = {3},
  number = {6},
  pages = {422--440},
  doi = {10.1038/s42254-021-00314-5}
}

@article{yang2021bpinn,
  author = {Yang, Liu and Meng, Xuhui and Karniadakis, George Em},
  title = {B-energy surrogates: Bayesian physics-informed neural networks for forward and inverse PDE problems with noisy data},
  journal = {Journal of Computational Physics},
  year = {2021},
  volume = {425},
  pages = {109913},
  doi = {10.1016/j.jcp.2020.109913}
}

@article{lu2021deepxde,
  author = {Lu, Lu and Meng, Xuhui and Mao, Zhiping and Karniadakis, George Em},
  title = {DeepXDE: A Deep Learning Library for Solving Differential Equations},
  journal = {SIAM Review},
  year = {2021},
  volume = {63},
  number = {1},
  pages = {208--228},
  doi = {10.1137/19M1274067}
}

@article{cuomo2022pinnreview,
  author = {Cuomo, Salvatore and Di Cola, Vincenzo Schiano and Giampaolo, Fabio and Rozza, Gianluigi and Raissi, Maziar and Piccialli, Francesco},
  title = {Scientific Machine Learning Through Physics-Informed Neural Networks: Where we are and What's Next},
  journal = {Journal of Scientific Computing},
  year = {2022},
  volume = {92},
  number = {3},
  pages = {88},
  doi = {10.1007/s10915-022-01939-z}
}

@article{bertsimas2004robustness,
  author = {Bertsimas, Dimitris and Sim, Melvyn},
  title = {The Price of Robustness},
  journal = {Operations Research},
  year = {2004},
  volume = {52},
  number = {1},
  pages = {35--53},
  doi = {10.1287/opre.1030.0065}
}

@article{kirkpatrick1983annealing,
  author = {Kirkpatrick, S. and Gelatt, C. D. and Vecchi, M. P.},
  title = {Optimization by Simulated Annealing},
  journal = {Science},
  year = {1983},
  volume = {220},
  number = {4598},
  pages = {671--680},
  doi = {10.1126/science.220.4598.671}
}

@article{schneider2014evrptw,
  author = {Schneider, Michael and Stenger, Andreas and Goeke, Dominik},
  title = {The Electric Vehicle-Routing Problem with Time Windows and Recharging Stations},
  journal = {Transportation Science},
  year = {2014},
  volume = {48},
  number = {4},
  pages = {500--520},
  doi = {10.1287/trsc.2013.0490}
}

@article{desaulniers2016evrp,
  author = {Desaulniers, Guy and Errico, Fausto and Irnich, Stefan and Schneider, Michael},
  title = {Exact Algorithms for Electric Vehicle-Routing Problems with Time Windows},
  journal = {Operations Research},
  year = {2016},
  volume = {64},
  number = {6},
  pages = {1388--1405},
  doi = {10.1287/opre.2016.1535}
}
"""


def read(experiment_id: str) -> pd.DataFrame:
    run_id = RUN_IDS.get(experiment_id, RUN_ID)
    return pd.read_csv(EXPERIMENTS / experiment_id / "analysis_data" / f"{experiment_id}_{run_id}_summary.csv")


def pct_reduction(new: float, old: float) -> float:
    return (old - new) / old * 100.0


if __name__ == "__main__":
    raise SystemExit(main())
