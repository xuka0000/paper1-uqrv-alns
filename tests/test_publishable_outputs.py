import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import generate_publishable_figures
import write_full_result_tables
import write_elsevier_latex


class PublishableOutputTests(unittest.TestCase):
    def test_repair_ablation_methods_have_figure_labels_and_colors(self):
        for method in ["no_energy_repair", "no_sync_repair"]:
            self.assertIn(method, generate_publishable_figures.METHOD_LABELS)
            self.assertIn(method, generate_publishable_figures.COLORS)

    def test_latex_context_exposes_repair_ablation_deltas(self):
        context = write_elsevier_latex.metrics_context()
        self.assertIn("risk_gain_vs_no_energy_repair", context)
        self.assertIn("risk_gain_vs_no_sync_repair", context)

    def test_latex_contains_parameter_table_and_complexity_paragraph(self):
        context = write_elsevier_latex.metrics_context()
        manuscript = write_elsevier_latex.tex(
            context,
            write_elsevier_latex.DUAL_DRAFTS["preprint"]["documentclass"],
        )
        self.assertIn(r"\label{tab:parameters}", manuscript)
        self.assertIn("Computational complexity", manuscript)

    def test_latex_includes_graph_based_network_figure(self):
        context = write_elsevier_latex.metrics_context()
        manuscript = write_elsevier_latex.tex(
            context,
            write_elsevier_latex.DUAL_DRAFTS["preprint"]["documentclass"],
        )
        self.assertIn("Fig0_network_construction_ai.png", manuscript)
        self.assertIn(r"\label{fig:network-construction}", manuscript)
        self.assertIn("Graph-based representation", manuscript)

    def test_latex_includes_operator_mechanism_figure(self):
        context = write_elsevier_latex.metrics_context()
        manuscript = write_elsevier_latex.tex(
            context,
            write_elsevier_latex.DUAL_DRAFTS["preprint"]["documentclass"],
        )
        self.assertIn("Fig3_operator_mechanism_ai.png", manuscript)
        self.assertIn(r"\label{fig:operator-mechanism}", manuscript)
        self.assertIn("destroy--repair operator mechanism", manuscript)

    def test_publishable_figure_pipeline_includes_network_construction(self):
        builder_names = [builder.__name__ for builder in generate_publishable_figures.PUBLISHABLE_FIGURE_BUILDERS]
        self.assertEqual(builder_names[0], "fig0_network_construction_ai")

    def test_publishable_figure_pipeline_includes_operator_mechanism(self):
        builder_names = [builder.__name__ for builder in generate_publishable_figures.PUBLISHABLE_FIGURE_BUILDERS]
        self.assertIn("fig3_operator_mechanism_ai", builder_names)

    def test_latex_contains_complete_formulation_labels(self):
        context = write_elsevier_latex.metrics_context()
        manuscript = write_elsevier_latex.tex(
            context,
            write_elsevier_latex.DUAL_DRAFTS["preprint"]["documentclass"],
        )
        for label in [
            r"\label{eq:tower-coverage}",
            r"\label{eq:vehicle-flow}",
            r"\label{eq:sortie-activation}",
            r"\label{eq:time-propagation}",
            r"\label{eq:launch-recovery-sync}",
            r"\label{eq:chance}",
        ]:
            self.assertIn(label, manuscript)

    def test_generated_latex_uses_sortie_pattern_language(self):
        context = write_elsevier_latex.metrics_context()
        manuscript = write_elsevier_latex.tex(
            context,
            write_elsevier_latex.DUAL_DRAFTS["preprint"]["documentclass"],
        )
        self.assertIn(r"\mathcal{K}_s", manuscript)
        self.assertIn("same-stop sortie patterns", manuscript)
        self.assertNotIn("stop--tower pairs", manuscript)
        self.assertNotIn("stop--tower energy", manuscript)
        self.assertNotIn("service-pair", manuscript)

    def test_section3_uses_sortie_pattern_formulation(self):
        section = (CODE_ROOT.parent / "manuscript_context" / "elsevier_preprint" / "section3_stop_batch_model.tex").read_text(
            encoding="utf-8"
        )
        for symbol in [
            r"\mathcal{K}_s",
            r"\delta_{ik}",
            r"y^v_{sdk}",
            r"q^v_{sdkk'}",
            r"Q_{sdk}",
        ]:
            self.assertIn(symbol, section)
        for obsolete_symbol in [
            r"y^v_{sdi}",
            r"q^v_{sdij}",
            r"Q_{sdi}",
        ]:
            self.assertNotIn(obsolete_symbol, section)

    def test_full_body_uses_sortie_pattern_algorithm_interface(self):
        body = (CODE_ROOT.parent / "manuscript_context" / "elsevier_preprint" / "full_body.tex").read_text(
            encoding="utf-8"
        )
        for phrase in [
            "sortie-pattern service set",
            r"Q_{sdk}",
            r"\mathcal{B}_{vsd}",
            r"\mathcal{Y}^{K}",
        ]:
            self.assertIn(phrase, body)
        for obsolete_phrase in [
            "stop--UAV--tower tuple",
            "stop--UAV--tower tuples",
            r"Q_{sdi}",
            r"\mu_{sdi}",
            r"\operatorname{seq}_{vsd}",
        ]:
            self.assertNotIn(obsolete_phrase, body)

    def test_parameter_table_uses_pattern_energy_symbols(self):
        table = (CODE_ROOT.parent / "manuscript_context" / "elsevier_preprint" / "table_model_parameters.tex").read_text(
            encoding="utf-8"
        )
        self.assertIn(r"(\mu_{sdk},\sigma_{sdk},Q_{sdk})", table)
        self.assertNotIn(r"Q_{sdi}", table)
        self.assertNotIn(r"\mu_{sdi}", table)

    def test_latex_compacts_bibliography_spacing(self):
        context = write_elsevier_latex.metrics_context()
        manuscript = write_elsevier_latex.tex(
            context,
            write_elsevier_latex.DUAL_DRAFTS["preprint"]["documentclass"],
        )
        self.assertIn(r"\setlength{\bibsep}{0pt plus 0.3ex}", manuscript)
        self.assertIn(r"\renewcommand{\bibfont}{\small}", manuscript)
        self.assertIn(r"\emergencystretch=2em", manuscript)

    def test_small_reference_table_labels_stop_batch_evaluator_metrics(self):
        df = pd.DataFrame(
            [
                _small_ref_row("milp_highs", 10, 5, 98.35, 15414, 0.35, 0.07, 0.011),
                _small_ref_row("alns_pinn", 10, 5, 96.01, 9673, 0.85, 0.07, 0.001),
                _small_ref_row("alns_pinn_full", 10, 5, 96.81, 9697, 0.80, 0.01, 0.002),
            ]
        )
        table = write_full_result_tables.small_reference_table_text(df)
        self.assertIn("stop-batch schedule evaluator", table)
        self.assertIn("Compact HiGHS (Cmax ref.)", table)
        self.assertIn(r"Eval. RWCT", table)

    def test_small_reference_table_reports_optional_sortie_summary(self):
        rows = [
            _small_ref_row("milp_highs", 10, 5, 98.35, 15414, 0.35, 0.07, 0.011),
            _small_ref_row("alns_pinn", 10, 5, 96.01, 9673, 0.85, 0.07, 0.001),
            _small_ref_row("alns_pinn_full", 10, 5, 96.81, 9697, 0.80, 0.01, 0.002),
        ]
        rows[-1]["sortie_count_mean"] = 4.0
        rows[-1]["avg_towers_per_sortie_mean"] = 2.5
        table = write_full_result_tables.small_reference_table_text(pd.DataFrame(rows))
        self.assertIn("Sorties/avg", table)
        self.assertIn("4/2.50", table)

    def test_stress_table_reports_feasible_top_coverage(self):
        df = pd.DataFrame(
            [
                _stress_row("sparse_high_wind", "alns_fixed", 0.20, 0.10),
                _stress_row("sparse_high_wind", "no_uq", 0.80, 0.30),
                _stress_row("sparse_high_wind", "no_risk_value", 0.70, 0.40),
                _stress_row("sparse_high_wind", "no_energy_repair", 0.50, 0.45),
                _stress_row("sparse_high_wind", "no_sync_repair", 0.50, 0.45),
                _stress_row("sparse_high_wind", "alns_pinn_full", 0.55, 0.50),
            ]
        )
        table = write_full_result_tables.stress_table_text(df)
        self.assertIn("Top/feas. cov.", table)
        self.assertIn("0.550/0.500", table)


def _small_ref_row(method, towers, stops, makespan, rwct, top_cov, infeas, runtime):
    return {
        "method": method,
        "tower_count": towers,
        "stop_count": stops,
        "makespan_mean": makespan,
        "risk_weighted_completion_time_mean": rwct,
        "top_risk_coverage_mean": top_cov,
        "infeasible_sortie_rate_mean": infeas,
        "solver_runtime_mean": runtime,
    }


def _stress_row(case, method, top_cov, feasible_top_cov):
    return {
        "stress_case": case,
        "method": method,
        "makespan_mean": 100.0,
        "risk_weighted_completion_time_mean": 1000.0,
        "top_risk_coverage_mean": top_cov,
        "feasible_top_risk_coverage_mean": feasible_top_cov,
        "infeasible_sortie_rate_mean": 0.1,
        "solver_runtime_mean": 0.2,
        "alns_accepted_moves_mean": 10.0,
        "alns_improving_moves_mean": 2.0,
    }


if __name__ == "__main__":
    unittest.main()
