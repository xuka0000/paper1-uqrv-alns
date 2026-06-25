from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


PROJECT = Path(__file__).resolve().parents[1]
EXP = PROJECT / "results" / "experiments"
MANUSCRIPT = PROJECT / "manuscript_context" / "tre_published_style"
RUN_ID = "multi_tower_repair2_full_20260612"
P10_RUN_ID = "airlab_energy_calibration_stop_batch_20260606"
P11_RUN_ID = "repair_stress_repair2_20260612"
P9_RUN_IDS = {
    "public_bay_area_full": "public_bay_area_full_repair2_20260612",
    "public_dallas_fort_worth_full": "public_dallas_fort_worth_full_repair2_20260612",
    "public_los_angeles_inland_full": "public_los_angeles_inland_full_repair2_20260612",
}

METHOD_LABELS = {
    "milp_highs": "Compact HiGHS (Cmax ref.)",
    "greedy_nearest": "Nearest",
    "ga": "GA",
    "aco": "ACO",
    "simulated_annealing": "SA",
    "tabu_search": "Tabu",
    "variable_neighborhood_search": "VNS",
    "hybrid_genetic_search": "HGS-VNS",
    "alns_fixed": "Fixed ALNS",
    "alns_pinn": "Point energy ALNS",
    "alns_pinn_uq": "UQ energy ALNS",
    "alns_pinn_full": "Proposed",
    "no_pinn": "No surrogate",
    "no_adaptive": "No adaptive",
    "no_uq": "No UQ",
    "no_risk_value": "No risk-value",
    "no_energy_repair": "No energy repair",
    "no_sync_repair": "No sync repair",
    "no_clustering": "No clustering",
    "fixed_physics": "Fixed physics",
    "point_pinn": "Point residual",
    "probabilistic_pinn": "Prob. residual",
    "constant_mean": "Constant mean",
    "parameter_linear": "Parameter linear",
    "parameter_route_linear": "Route linear",
    "telemetry_weather_linear": "Telemetry-weather",
}

SMALL_REFERENCE_ORDER = ["milp_highs", "alns_pinn", "alns_pinn_full"]

MAIN_ALGORITHM_ORDER = [
    "greedy_nearest",
    "ga",
    "aco",
    "simulated_annealing",
    "tabu_search",
    "variable_neighborhood_search",
    "hybrid_genetic_search",
    "alns_pinn_full",
]

METHOD_ORDER = MAIN_ALGORITHM_ORDER

ABLATION_METHOD_ORDER = [
    "alns_fixed",
    "alns_pinn",
    "alns_pinn_uq",
    "no_pinn",
    "no_uq",
    "no_risk_value",
    "no_adaptive",
    "no_clustering",
    "no_energy_repair",
    "no_sync_repair",
    "alns_pinn_full",
]

CASE_LABELS = {
    "public_bay_area_full": "Bay Area",
    "public_dallas_fort_worth_full": "Dallas--Fort Worth",
    "public_los_angeles_inland_full": "Los Angeles inland",
}

STRESS_LABELS = {
    "sparse_high_wind": "SHW",
    "tight_battery": "TB",
    "very_sparse_corridor": "VSC",
}


def bold(text: str) -> str:
    return rf"\textbf{{{text}}}"


def fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def fmt_int(value: float) -> str:
    return f"{value:.0f}"


def best_mask(df: pd.DataFrame, metric: str, direction: str) -> pd.Series:
    values = pd.to_numeric(df[metric])
    target = values.min() if direction == "min" else values.max()
    return (values - target).abs() <= 1e-9


def maybe_bold(value: str, is_best: bool) -> str:
    return bold(value) if is_best else value


def fmt_top_feasible(row: pd.Series) -> str:
    feasible = getattr(row, "feasible_top_risk_coverage_mean", row.top_risk_coverage_mean)
    return f"{fmt(row.top_risk_coverage_mean, 3)}/{fmt(feasible, 3)}"


def row_value(row, name: str):
    if isinstance(row, pd.Series):
        return row[name] if name in row.index else None
    return getattr(row, name, None)


def fmt_sortie_summary(row) -> str:
    sortie_count = row_value(row, "sortie_count_mean")
    avg_towers = row_value(row, "avg_towers_per_sortie_mean")
    if sortie_count is None or avg_towers is None:
        return "--"
    if pd.isna(sortie_count) or pd.isna(avg_towers):
        return "--"
    return f"{fmt_int(float(sortie_count))}/{float(avg_towers):.2f}"


def fmt_pct(value: float) -> str:
    return f"{100.0 * value:.1f}\\%"


def row_stop_count(row) -> int:
    if hasattr(row, "stop_count"):
        return int(row.stop_count)
    return int(round(float(row.total_candidate_pairs_mean) / max(1, int(row.tower_count))))


def write(path: str, text: str) -> None:
    (MANUSCRIPT / path).write_text(text.replace("\r\n", "\n"), encoding="utf-8")


def small_reference_table_text(df: pd.DataFrame) -> str:
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{S-scale compact-reference diagnostics. The HiGHS row optimizes the compact makespan--energy model; RWCT and top-risk coverage are computed afterwards by the common stop-batch schedule evaluator and are not HiGHS objective values. Values are means over matched seeds; shaded rows denote the proposed configuration.}",
        r"\label{tab:small-reference}",
        r"\small",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\begin{tabular*}{\textwidth}{@{\extracolsep{\fill}}rrlrrrrrr@{}}",
        r"\toprule",
        r"Towers & Stops & Method & Makespan & Eval. RWCT & Eval. top cov. & Sorties/avg & Infeas. & Time (s) \\",
        r"\midrule",
    ]
    towers = sorted(df["tower_count"].unique())
    for ti, tower in enumerate(towers):
        sub = df[df["tower_count"].eq(tower)].set_index("method")
        stop_count = int(sub["stop_count"].iloc[0])
        for method in SMALL_REFERENCE_ORDER:
            if method not in sub.index:
                continue
            row = sub.loc[method]
            prefix = r"\rowcolor{gray!10}" if method == "alns_pinn_full" else ""
            label = METHOD_LABELS[method]
            if method == "alns_pinn_full":
                label = bold(label)
            vals = [
                fmt(row.makespan_mean, 2),
                fmt_int(row.risk_weighted_completion_time_mean),
                fmt(row.top_risk_coverage_mean, 3),
                fmt_sortie_summary(row),
                fmt(row.infeasible_sortie_rate_mean, 3),
                fmt(row.solver_runtime_mean, 3),
            ]
            if prefix:
                lines.append(prefix)
            lines.append(f"{int(tower)} & {stop_count} & {label} & " + " & ".join(vals) + r" \\")
        if ti != len(towers) - 1:
            lines.append(r"\addlinespace[2pt]")
    lines += [r"\bottomrule", r"\end{tabular*}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def small_reference_table() -> None:
    df = pd.read_csv(EXP / "P1_milp_exact_small" / "analysis_data" / f"P1_milp_exact_small_{RUN_ID}_summary.csv")
    write("table_small_reference.tex", small_reference_table_text(df))


def algorithm_table() -> None:
    df = pd.read_csv(EXP / "P2_algorithm_comparison" / "analysis_data" / f"P2_algorithm_comparison_{RUN_ID}_summary.csv")
    df = df[df["method"].isin(METHOD_ORDER)].copy()
    towers = sorted(df["tower_count"].unique())
    lines = [
        r"\begingroup",
        r"\small",
        r"\setlength{\tabcolsep}{3.0pt}",
        r"\begin{longtable}{@{}rrlrrrrr@{}}",
        r"\caption{Full P2 medium-uncertainty algorithm-comparison data across all tested corridor scales; values are means over ten matched seeds. Shaded rows denote the proposed configuration; bold values indicate the best value within each tower-count block for the corresponding metric direction.}\label{tab:algorithm-results}\\",
        r"\toprule",
        r"Scale & Towers & Method & Makespan $\downarrow$ & RWCT $\downarrow$ & Top cov. $\uparrow$ & Infeas. $\downarrow$ & Time (s) $\downarrow$ \\",
        r"\midrule",
        r"\endfirsthead",
        r"\caption[]{Full P2 medium-uncertainty algorithm-comparison data across all tested corridor scales (continued).}\\",
        r"\toprule",
        r"Scale & Towers & Method & Makespan $\downarrow$ & RWCT $\downarrow$ & Top cov. $\uparrow$ & Infeas. $\downarrow$ & Time (s) $\downarrow$ \\",
        r"\midrule",
        r"\endhead",
    ]
    for ti, tower in enumerate(towers):
        sub = df[df["tower_count"].eq(tower)].set_index("method").loc[METHOD_ORDER].reset_index()
        best = {
            "makespan_mean": best_mask(sub, "makespan_mean", "min"),
            "risk_weighted_completion_time_mean": best_mask(sub, "risk_weighted_completion_time_mean", "min"),
            "top_risk_coverage_mean": best_mask(sub, "top_risk_coverage_mean", "max"),
            "infeasible_sortie_rate_mean": best_mask(sub, "infeasible_sortie_rate_mean", "min"),
            "solver_runtime_mean": best_mask(sub, "solver_runtime_mean", "min"),
        }
        for idx, row in sub.iterrows():
            prefix = r"\rowcolor{gray!10}" if row.method == "alns_pinn_full" else ""
            method = bold(METHOD_LABELS[row.method]) if row.method == "alns_pinn_full" else METHOD_LABELS[row.method]
            vals = [
                maybe_bold(fmt(row.makespan_mean, 2), bool(best["makespan_mean"].iloc[idx])),
                maybe_bold(fmt_int(row.risk_weighted_completion_time_mean), bool(best["risk_weighted_completion_time_mean"].iloc[idx])),
                maybe_bold(fmt(row.top_risk_coverage_mean, 3), bool(best["top_risk_coverage_mean"].iloc[idx])),
                maybe_bold(fmt(row.infeasible_sortie_rate_mean, 4), bool(best["infeasible_sortie_rate_mean"].iloc[idx])),
                maybe_bold(fmt(row.solver_runtime_mean, 3), bool(best["solver_runtime_mean"].iloc[idx])),
            ]
            scale = row["size"]
            line = f"{prefix}\n{scale} & {int(tower)} & {method} & " + " & ".join(vals) + r" \\"
            lines.append(line)
        if ti != len(towers) - 1:
            lines.append(r"\addlinespace[2pt]")
    lines += [r"\bottomrule", r"\end{longtable}", r"\endgroup"]
    write("table_algorithm_results.tex", "\n".join(lines) + "\n")


def energy_table() -> None:
    p3 = pd.read_csv(EXP / "P3_pinn_prediction_accuracy" / "analysis_data" / f"P3_pinn_prediction_accuracy_{RUN_ID}_summary.csv")
    p10 = pd.read_csv(EXP / "P10_energy_telemetry_calibration" / "analysis_data" / f"P10_energy_telemetry_calibration_{P10_RUN_ID}_summary.csv")
    sim_order = ["low", "medium", "high"]
    model_order = ["fixed_physics", "point_pinn", "probabilistic_pinn"]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Full energy-prediction data for scheduler-facing simulation and AirLab telemetry calibration. AirLab rows report MAPE, WAPE and SMAPE because MAPE is unstable for low-energy flights. Shaded rows denote the selected probabilistic or telemetry-weather model; bold values indicate the best value within each uncertainty level or telemetry block.}",
        r"\label{tab:energy-evidence}",
        r"\small",
        r"\setlength{\tabcolsep}{2.1pt}",
        r"\begin{tabular}{@{}lllrrrrrrrr@{}}",
        r"\toprule",
        r"Block & Level & Model & Test & MAE $\downarrow$ & RMSE $\downarrow$ & MAPE $\downarrow$ & WAPE $\downarrow$ & SMAPE $\downarrow$ & Cov. $\uparrow$ & False feas. $\downarrow$ \\",
        r"\midrule",
    ]
    for level in sim_order:
        sub = p3[p3["uncertainty"].eq(level)].set_index("prediction_model").loc[model_order].reset_index()
        best = {
            "mae_mean": best_mask(sub, "mae_mean", "min"),
            "rmse_mean": best_mask(sub, "rmse_mean", "min"),
            "mape_mean": best_mask(sub, "mape_mean", "min"),
            "coverage_95_mean": best_mask(sub, "coverage_95_mean", "max"),
            "false_feasible_rate_mean": best_mask(sub, "false_feasible_rate_mean", "min"),
        }
        for idx, row in sub.iterrows():
            prefix = r"\rowcolor{gray!10}" if row.prediction_model == "probabilistic_pinn" else ""
            model = bold(METHOD_LABELS[row.prediction_model]) if row.prediction_model == "probabilistic_pinn" else METHOD_LABELS[row.prediction_model]
            vals = [
                maybe_bold(fmt(row.mae_mean, 2), bool(best["mae_mean"].iloc[idx])),
                maybe_bold(fmt(row.rmse_mean, 2), bool(best["rmse_mean"].iloc[idx])),
                maybe_bold(fmt(row.mape_mean, 3), bool(best["mape_mean"].iloc[idx])),
                "--",
                "--",
                maybe_bold(fmt(row.coverage_95_mean, 3), bool(best["coverage_95_mean"].iloc[idx])),
                maybe_bold(fmt(row.false_feasible_rate_mean, 4), bool(best["false_feasible_rate_mean"].iloc[idx])),
            ]
            if prefix:
                lines.append(prefix)
            lines.append(f"Simulation & {level.title()} & {model} & 10 seeds & " + " & ".join(vals) + r" \\")
        lines.append(r"\addlinespace[2pt]")
    order = ["constant_mean", "parameter_linear", "parameter_route_linear", "telemetry_weather_linear"]
    tel = p10.set_index("model").loc[order].reset_index()
    best = {
        "mae_wh": best_mask(tel, "mae_wh", "min"),
        "rmse_wh": best_mask(tel, "rmse_wh", "min"),
        "mape": best_mask(tel, "mape", "min"),
        "wape": best_mask(tel, "wape", "min"),
        "smape": best_mask(tel, "smape", "min"),
        "coverage_95": best_mask(tel, "coverage_95", "max"),
        "false_feasible_high_energy_rate": best_mask(tel, "false_feasible_high_energy_rate", "min"),
    }
    for idx, row in tel.iterrows():
        prefix = r"\rowcolor{gray!10}" if row.model == "telemetry_weather_linear" else ""
        model = bold(METHOD_LABELS[row.model]) if row.model == "telemetry_weather_linear" else METHOD_LABELS[row.model]
        vals = [
            maybe_bold(f"{row.mae_wh:.3f} Wh", bool(best["mae_wh"].iloc[idx])),
            maybe_bold(f"{row.rmse_wh:.3f} Wh", bool(best["rmse_wh"].iloc[idx])),
            maybe_bold(fmt(row.mape, 3), bool(best["mape"].iloc[idx])),
            maybe_bold(fmt(row.wape, 3), bool(best["wape"].iloc[idx])),
            maybe_bold(fmt(row.smape, 3), bool(best["smape"].iloc[idx])),
            maybe_bold(fmt(row.coverage_95, 3), bool(best["coverage_95"].iloc[idx])),
            maybe_bold(fmt(row.false_feasible_high_energy_rate, 4), bool(best["false_feasible_high_energy_rate"].iloc[idx])),
        ]
        if prefix:
            lines.append(prefix)
        lines.append(f"AirLab & Held-out & {model} & 41 flights & " + " & ".join(vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("table_energy_evidence.tex", "\n".join(lines) + "\n")


def ablation_table() -> None:
    df = pd.read_csv(EXP / "P4_ablation" / "analysis_data" / f"P4_ablation_{RUN_ID}_summary.csv")
    if "feasible_top_risk_coverage_mean" not in df.columns:
        df["feasible_top_risk_coverage_mean"] = df["top_risk_coverage_mean"]
    order = [method for method in ABLATION_METHOD_ORDER if method in set(df["method"])]
    df = df.set_index("method").loc[order].reset_index()
    best = {
        "makespan_mean": best_mask(df, "makespan_mean", "min"),
        "risk_weighted_completion_time_mean": best_mask(df, "risk_weighted_completion_time_mean", "min"),
        "feasible_top_risk_coverage_mean": best_mask(df, "feasible_top_risk_coverage_mean", "max"),
        "infeasible_sortie_rate_mean": best_mask(df, "infeasible_sortie_rate_mean", "min"),
        "solver_runtime_mean": best_mask(df, "solver_runtime_mean", "min"),
    }
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Full ablation data on the 50-tower high-uncertainty case. Shaded rows denote the proposed configuration; bold values indicate the best value within the ablation block.}",
        r"\label{tab:ablation-results}",
        r"\small",
        r"\setlength{\tabcolsep}{2.7pt}",
        r"\begin{tabular}{@{}llrrrrrrr@{}}",
        r"\toprule",
        r"Method & Stop mode & Makespan $\downarrow$ & RWCT $\downarrow$ & Top/feas. cov. $\uparrow$ & Infeas. $\downarrow$ & Time (s) $\downarrow$ & Acc. & Imp. \\",
        r"\midrule",
    ]
    for idx, row in df.iterrows():
        prefix = r"\rowcolor{gray!10}" if row.method == "alns_pinn_full" else ""
        method = bold(METHOD_LABELS[row.method]) if row.method == "alns_pinn_full" else METHOD_LABELS[row.method]
        vals = [
            maybe_bold(fmt(row.makespan_mean, 2), bool(best["makespan_mean"].iloc[idx])),
            maybe_bold(fmt_int(row.risk_weighted_completion_time_mean), bool(best["risk_weighted_completion_time_mean"].iloc[idx])),
            maybe_bold(fmt_top_feasible(row), bool(best["feasible_top_risk_coverage_mean"].iloc[idx])),
            maybe_bold(fmt(row.infeasible_sortie_rate_mean, 3), bool(best["infeasible_sortie_rate_mean"].iloc[idx])),
            maybe_bold(fmt(row.solver_runtime_mean, 3), bool(best["solver_runtime_mean"].iloc[idx])),
            fmt(row.alns_accepted_moves_mean, 1),
            fmt(row.alns_improving_moves_mean, 1),
        ]
        if prefix:
            lines.append(prefix)
        lines.append(f"{method} & {row.candidate_mode} & " + " & ".join(vals) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("table_ablation_results.tex", "\n".join(lines) + "\n")


def stress_table_text(df: pd.DataFrame) -> str:
    if "feasible_top_risk_coverage_mean" not in df.columns:
        df = df.copy()
        df["feasible_top_risk_coverage_mean"] = df["top_risk_coverage_mean"]
    order = ["alns_fixed", "alns_pinn", "alns_pinn_uq", "no_uq", "no_risk_value", "no_energy_repair", "no_sync_repair", "alns_pinn_full"]
    order = [method for method in order if method in set(df["method"])]
    cases = [case for case in ["sparse_high_wind", "tight_battery", "very_sparse_corridor"] if case in set(df["stress_case"])]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Full stress-test data for uncertainty and repair components. SHW: sparse high wind; TB: tight battery; VSC: very sparse corridor. Top/feas. cov. reports nominal early top-risk coverage followed by q95-feasible early top-risk coverage. Shaded rows denote the proposed configuration; bold values indicate the best value within each stress case.}",
        r"\label{tab:stress-results}",
        r"\small",
        r"\setlength{\tabcolsep}{2.7pt}",
        r"\begin{tabular}{@{}llrrrrrrr@{}}",
        r"\toprule",
        r"Case & Method & Makespan $\downarrow$ & RWCT $\downarrow$ & Top/feas. cov. $\uparrow$ & Infeas. $\downarrow$ & Time (s) $\downarrow$ & Acc. & Imp. \\",
        r"\midrule",
    ]
    for ci, case in enumerate(cases):
        sub = df[df["stress_case"].eq(case)].set_index("method").loc[order].reset_index()
        best = {
            "makespan_mean": best_mask(sub, "makespan_mean", "min"),
            "risk_weighted_completion_time_mean": best_mask(sub, "risk_weighted_completion_time_mean", "min"),
            "feasible_top_risk_coverage_mean": best_mask(sub, "feasible_top_risk_coverage_mean", "max"),
            "infeasible_sortie_rate_mean": best_mask(sub, "infeasible_sortie_rate_mean", "min"),
            "solver_runtime_mean": best_mask(sub, "solver_runtime_mean", "min"),
        }
        for idx, row in sub.iterrows():
            prefix = r"\rowcolor{gray!10}" if row.method == "alns_pinn_full" else ""
            method = bold(METHOD_LABELS[row.method]) if row.method == "alns_pinn_full" else METHOD_LABELS[row.method]
            vals = [
                maybe_bold(fmt(row.makespan_mean, 2), bool(best["makespan_mean"].iloc[idx])),
                maybe_bold(fmt_int(row.risk_weighted_completion_time_mean), bool(best["risk_weighted_completion_time_mean"].iloc[idx])),
                maybe_bold(fmt_top_feasible(row), bool(best["feasible_top_risk_coverage_mean"].iloc[idx])),
                maybe_bold(fmt(row.infeasible_sortie_rate_mean, 3), bool(best["infeasible_sortie_rate_mean"].iloc[idx])),
                maybe_bold(fmt(row.solver_runtime_mean, 3), bool(best["solver_runtime_mean"].iloc[idx])),
                fmt(row.alns_accepted_moves_mean, 1),
                fmt(row.alns_improving_moves_mean, 1),
            ]
            if prefix:
                lines.append(prefix)
            lines.append(f"{STRESS_LABELS[case]} & {method} & " + " & ".join(vals) + r" \\")
        if ci != len(cases) - 1:
            lines.append(r"\addlinespace[2pt]")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    return "\n".join(lines) + "\n"


def stress_table() -> None:
    df = pd.read_csv(EXP / "P11_repair_stress" / "analysis_data" / f"P11_repair_stress_{P11_RUN_ID}_summary.csv")
    write("table_stress_results.tex", stress_table_text(df))


def gis_table() -> None:
    files = [
        ("Bay Area", f"P9_real_gis_case_{P9_RUN_IDS['public_bay_area_full']}_summary.csv"),
        ("Dallas--Fort Worth", f"P9_real_gis_case_{P9_RUN_IDS['public_dallas_fort_worth_full']}_summary.csv"),
        ("Los Angeles inland", f"P9_real_gis_case_{P9_RUN_IDS['public_los_angeles_inland_full']}_summary.csv"),
    ]
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Full public GIS-grounded case data. Geometry and weather are public data; risk/value labels remain proxies. Shaded rows denote the proposed configuration; bold values indicate the best value within each region.}",
        r"\label{tab:gis-results}",
        r"\small",
        r"\setlength{\tabcolsep}{2.7pt}",
        r"\begin{tabular}{@{}llrrrrr@{}}",
        r"\toprule",
        r"Case & Method & Makespan $\downarrow$ & RWCT $\downarrow$ & Top cov. $\uparrow$ & Infeas. $\downarrow$ & Time (s) $\downarrow$ \\",
        r"\midrule",
    ]
    for fi, (case, fname) in enumerate(files):
        sub = pd.read_csv(EXP / "P9_real_gis_case" / "analysis_data" / fname)
        sub = sub.set_index("method").loc[METHOD_ORDER].reset_index()
        best = {
            "makespan_mean": best_mask(sub, "makespan_mean", "min"),
            "risk_weighted_completion_time_mean": best_mask(sub, "risk_weighted_completion_time_mean", "min"),
            "top_risk_coverage_mean": best_mask(sub, "top_risk_coverage_mean", "max"),
            "infeasible_sortie_rate_mean": best_mask(sub, "infeasible_sortie_rate_mean", "min"),
            "solver_runtime_mean": best_mask(sub, "solver_runtime_mean", "min"),
        }
        for idx, row in sub.iterrows():
            prefix = r"\rowcolor{gray!10}" if row.method == "alns_pinn_full" else ""
            method = bold(METHOD_LABELS[row.method]) if row.method == "alns_pinn_full" else METHOD_LABELS[row.method]
            vals = [
                maybe_bold(fmt(row.makespan_mean, 2), bool(best["makespan_mean"].iloc[idx])),
                maybe_bold(fmt_int(row.risk_weighted_completion_time_mean), bool(best["risk_weighted_completion_time_mean"].iloc[idx])),
                maybe_bold(fmt(row.top_risk_coverage_mean, 3), bool(best["top_risk_coverage_mean"].iloc[idx])),
                maybe_bold(fmt(row.infeasible_sortie_rate_mean, 3), bool(best["infeasible_sortie_rate_mean"].iloc[idx])),
                maybe_bold(fmt(row.solver_runtime_mean, 3), bool(best["solver_runtime_mean"].iloc[idx])),
            ]
            lines.append(f"{prefix}\n{case} & {method} & " + " & ".join(vals) + r" \\")
        if fi != len(files) - 1:
            lines.append(r"\addlinespace[2pt]")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("table_gis_results.tex", "\n".join(lines) + "\n")


def scalability_screening_table() -> None:
    p2 = pd.read_csv(EXP / "P2_algorithm_comparison" / "analysis_data" / f"P2_algorithm_comparison_{RUN_ID}_summary.csv")
    p6 = pd.read_csv(EXP / "P6_candidate_stop_screening" / "analysis_data" / f"P6_candidate_stop_screening_{RUN_ID}_summary.csv")
    p8 = pd.read_csv(EXP / "P8_sensitivity" / "analysis_data" / f"P8_sensitivity_{RUN_ID}_summary.csv")

    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Raw scalability, candidate-stop screening and UAV-count sensitivity data used in Fig.~\ref{fig:scale}; values are means over ten matched seeds. Scale and screening rows use the stop-batch evaluator with normalized risk-value RWCT. Feasible pairs are q95-feasible support pairs used to seed same-stop sortie patterns, including direct enumeration. Top/feas. cov. reports nominal and q95-feasible early top-risk coverage. Shaded rows denote the K-means screened proposed configuration or the largest tested UAV count.}",
        r"\label{tab:scalability-screening}",
        r"\small",
        r"\setlength{\tabcolsep}{2.7pt}",
        r"\begin{tabularx}{\textwidth}{@{}>{\raggedright\arraybackslash}p{0.11\textwidth}>{\raggedright\arraybackslash}Xrrrrrrrr@{}}",
        r"\toprule",
        r"Block & Setting & Towers & Stops & Pair red. & Feas. pairs & RWCT & Top/feas. cov. & Infeas. & Time (s) \\",
        r"\midrule",
    ]

    scale = p2[p2["method"].eq("alns_pinn_full")].sort_values("tower_count")
    for row in scale.itertuples():
        lines.append(r"\rowcolor{gray!10}")
        lines.append(
            f"Scale & K-means & {int(row.tower_count)} & {int(row.stop_count)} & "
            f"{fmt_pct(row.candidate_pair_reduction_mean)} & {fmt(row.feasible_candidate_pairs_mean, 1)} & "
            f"{fmt(row.risk_weighted_completion_time_mean, 0)} & {fmt_top_feasible(pd.Series(row._asdict()))} & "
            f"{fmt(row.infeasible_sortie_rate_mean, 3)} & {fmt(row.solver_runtime_mean, 3)} \\\\"
        )
    lines.append(r"\addlinespace[2pt]")

    screening = p6[p6["method"].eq("alns_pinn_full")].copy()
    mode_order = {"direct": 0, "dbscan": 1, "kmeans": 2}
    screening = screening.sort_values(["tower_count", "candidate_mode"], key=lambda col: col.map(mode_order) if col.name == "candidate_mode" else col)
    for row in screening.itertuples():
        is_default = row.candidate_mode == "kmeans"
        if is_default:
            lines.append(r"\rowcolor{gray!10}")
        setting = "K-means" if row.candidate_mode == "kmeans" else "DBSCAN" if row.candidate_mode == "dbscan" else "Direct"
        lines.append(
            f"Screening & {setting} & {int(row.tower_count)} & {int(row.stop_count)} & "
            f"{fmt_pct(row.candidate_pair_reduction_mean)} & {fmt(row.feasible_candidate_pairs_mean, 1)} & "
            f"{fmt(row.risk_weighted_completion_time_mean, 0)} & {fmt_top_feasible(pd.Series(row._asdict()))} & "
            f"{fmt(row.infeasible_sortie_rate_mean, 3)} & {fmt(row.solver_runtime_mean, 3)} \\\\"
        )
    lines.append(r"\addlinespace[2pt]")

    uav = p8[p8["sensitivity_factor"].eq("uav_count")].copy()
    uav["uav_numeric"] = uav["sensitivity_level"].astype(float)
    uav = uav.sort_values("uav_numeric")
    max_uav = uav["uav_numeric"].max()
    for row in uav.itertuples():
        if row.uav_numeric == max_uav:
            lines.append(r"\rowcolor{gray!10}")
        lines.append(
            f"UAV count & {int(row.uav_numeric)} UAVs & {int(row.tower_count)} & {row_stop_count(row)} & "
            f"{fmt_pct(row.candidate_pair_reduction_mean)} & {fmt(row.feasible_candidate_pairs_mean, 1)} & "
            f"{fmt(row.risk_weighted_completion_time_mean, 0)} & {fmt_top_feasible(pd.Series(row._asdict()))} & "
            f"{fmt(row.infeasible_sortie_rate_mean, 3)} & {fmt(row.solver_runtime_mean, 3)} \\\\"
        )

    lines += [r"\bottomrule", r"\end{tabularx}", r"\end{table}"]
    write("table_scalability_screening.tex", "\n".join(lines) + "\n")


def sensitivity_table() -> None:
    df = pd.read_csv(EXP / "P8_sensitivity" / "analysis_data" / f"P8_sensitivity_{RUN_ID}_summary.csv")
    factor_order = ["candidate_mode", "iteration_budget", "quantile_z", "reserve_ratio", "uav_count"]
    defaults = {
        "candidate_mode": "kmeans",
        "iteration_budget": "100",
        "quantile_z": "1.645",
        "reserve_ratio": "0.12",
        "uav_count": "4",
    }
    factor_label = {
        "candidate_mode": "Stop mode",
        "iteration_budget": "Iterations",
        "quantile_z": "$z_\\epsilon$",
        "reserve_ratio": "$\\rho$",
        "uav_count": "UAV count",
    }
    lines = [
        r"\begin{table}[H]",
        r"\centering",
        r"\caption{Full sensitivity-analysis data on the 50-tower high-uncertainty case. Shaded rows denote the default proposed setting used in the main experiments; bold values indicate the best value within each sensitivity factor.}",
        r"\label{tab:sensitivity-results}",
        r"\small",
        r"\setlength{\tabcolsep}{2.7pt}",
        r"\begin{tabular}{@{}llrrrrr@{}}",
        r"\toprule",
        r"Factor & Level & Makespan $\downarrow$ & RWCT $\downarrow$ & Top cov. $\uparrow$ & Infeas. $\downarrow$ & Time (s) $\downarrow$ \\",
        r"\midrule",
    ]
    for fi, factor in enumerate(factor_order):
        sub = df[df["sensitivity_factor"].eq(factor)].copy()
        sub["level_key"] = sub["sensitivity_level"].astype(str)
        def sort_key(x: str):
            try:
                return float(x)
            except ValueError:
                return {"direct": 0, "kmeans": 1, "dbscan": 2}.get(x, 99)
        sub = sub.sort_values("level_key", key=lambda s: s.map(sort_key)).reset_index(drop=True)
        best = {
            "makespan_mean": best_mask(sub, "makespan_mean", "min"),
            "risk_weighted_completion_time_mean": best_mask(sub, "risk_weighted_completion_time_mean", "min"),
            "top_risk_coverage_mean": best_mask(sub, "top_risk_coverage_mean", "max"),
            "infeasible_sortie_rate_mean": best_mask(sub, "infeasible_sortie_rate_mean", "min"),
            "solver_runtime_mean": best_mask(sub, "solver_runtime_mean", "min"),
        }
        for idx, row in sub.iterrows():
            level = str(row.sensitivity_level)
            prefix = r"\rowcolor{gray!10}" if level == defaults[factor] else ""
            vals = [
                maybe_bold(fmt(row.makespan_mean, 2), bool(best["makespan_mean"].iloc[idx])),
                maybe_bold(fmt_int(row.risk_weighted_completion_time_mean), bool(best["risk_weighted_completion_time_mean"].iloc[idx])),
                maybe_bold(fmt(row.top_risk_coverage_mean, 3), bool(best["top_risk_coverage_mean"].iloc[idx])),
                maybe_bold(fmt(row.infeasible_sortie_rate_mean, 3), bool(best["infeasible_sortie_rate_mean"].iloc[idx])),
                maybe_bold(fmt(row.solver_runtime_mean, 3), bool(best["solver_runtime_mean"].iloc[idx])),
            ]
            lines.append(f"{prefix}\n{factor_label[factor]} & {level} & " + " & ".join(vals) + r" \\")
        if fi != len(factor_order) - 1:
            lines.append(r"\addlinespace[2pt]")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}"]
    write("table_sensitivity_results.tex", "\n".join(lines) + "\n")


TABLE_WRITERS = {
    "small_reference": small_reference_table,
    "algorithm": algorithm_table,
    "energy": energy_table,
    "ablation": ablation_table,
    "stress": stress_table,
    "gis": gis_table,
    "scalability": scalability_screening_table,
    "sensitivity": sensitivity_table,
}


def main(argv: list[str] | None = None) -> int:
    global RUN_ID
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", default=RUN_ID)
    parser.add_argument("--only", default="all", choices=["all", *TABLE_WRITERS.keys()])
    args = parser.parse_args(argv)
    RUN_ID = args.run_id

    if args.only == "all":
        selected = TABLE_WRITERS.items()
    else:
        selected = [(args.only, TABLE_WRITERS[args.only])]
    for _, writer in selected:
        writer()
    print(f"Wrote {args.only} manuscript result table(s) for run id {RUN_ID}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
