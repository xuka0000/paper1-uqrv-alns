from __future__ import annotations

import argparse
import csv
import hashlib
import os
import stat
import shutil
import subprocess
import sys
import textwrap
import time
import zipfile
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DELIVERY_ROOT = PROJECT_ROOT / "delivery"
REPAIR_OUTPUT_ROOT = PROJECT_ROOT / "results/analysis_outputs" / "review_repair_20260531"

EXPERIMENTS = [
    "E0_smoke",
    "E1_exact_small",
    "E2_core_comparison",
    "E3_uncertainty_robustness",
    "E4_value_ablation",
    "E5_online_replanning",
    "E6_scalability",
    "P1_milp_exact_small",
    "P2_algorithm_comparison",
    "P3_pinn_prediction_accuracy",
    "P4_ablation",
    "P5_case_study",
    "P6_candidate_stop_screening",
    "P7_statistical_tests",
    "P8_sensitivity",
    "P9_real_gis_case",
    "P10_energy_telemetry_calibration",
    "P11_repair_stress",
]

PUBLICATION_EXPERIMENTS = [exp for exp in EXPERIMENTS if exp.startswith("P")]

IGNORE_NAMES = {
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".venv",
    "venv",
}
IGNORE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".xdv",
    ".fdb_latexmk",
    ".fls",
    ".synctex.gz",
}

LATEX_SCAN_PATTERNS = [
    "LaTeX Warning",
    "Package natbib Warning",
    "Overfull",
    "Underfull",
    "undefined references",
    "Citation",
    "Reference",
    "Undefined control sequence",
    "Emergency stop",
    "Fatal error",
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the colleague delivery package for paper1.")
    parser.add_argument("--name", default="", help="Optional delivery directory name.")
    parser.add_argument("--skip-validation", action="store_true", help="Copy and zip only.")
    args = parser.parse_args()

    stamp = time.strftime("%Y%m%d_%H%M%S")
    name = args.name or f"paper1_colleague_delivery_{stamp}"
    package_dir = DELIVERY_ROOT / name
    if package_dir.exists():
        _safe_rmtree(package_dir)
    DELIVERY_ROOT.mkdir(exist_ok=True)
    package_dir.mkdir()

    paths = _make_dirs(package_dir)
    _copy_original_materials(paths["original"])
    _copy_published_latex(paths["published"])
    _build_submission_latex(paths["submission"])
    _copy_reproducible_code(paths["code"])
    _copy_experiment_packages(paths["experiments"])
    _copy_datasets(paths["datasets"])
    _copy_figure_sources(paths["figures"])
    _write_external_review(paths["review"])
    _copy_revision_change_report(paths["revision_report"])
    _write_delivery_docs(paths["notes"], package_dir.name)

    validation = {}
    if not args.skip_validation:
        validation = _run_validation(package_dir, paths)
    _write_validation_summary(paths["logs"], validation)
    _write_manifest(package_dir, paths["logs"] / "file_manifest.csv")
    archive = _zip_package(package_dir)
    archive_hash = _sha256_file(archive)
    (archive.with_suffix(archive.suffix + ".sha256.txt")).write_text(
        f"{archive_hash}  {archive.name}\n", encoding="utf-8"
    )
    (paths["logs"] / "archive_hash.txt").write_text(
        f"{archive_hash}  {archive.name}\n", encoding="utf-8"
    )
    _write_manifest(package_dir, paths["logs"] / "file_manifest.csv")
    return 0


def _make_dirs(package_dir: Path) -> dict[str, Path]:
    dirs = {
        "notes": package_dir / "00_delivery_notes",
        "published": package_dir / "01_latex_published_style_current",
        "submission": package_dir / "02_latex_submission_elsarticle_current",
        "original": package_dir / "03_original_and_reference_files",
        "code": package_dir / "04_reproducible_code",
        "experiments": package_dir / "05_experiment_data_by_item",
        "datasets": package_dir / "06_downloaded_datasets",
        "review": package_dir / "07_external_review_materials",
        "logs": package_dir / "08_logs_and_validation",
        "figures": package_dir / "09_manuscript_figure_sources",
        "revision_report": package_dir / "10_revision_change_report",
    }
    for path in dirs.values():
        path.mkdir(parents=True, exist_ok=True)
    return dirs


def _safe_rmtree(path: Path) -> None:
    resolved = path.resolve()
    root = DELIVERY_ROOT.resolve()
    if root not in resolved.parents:
        raise RuntimeError(f"refusing to remove outside delivery root: {resolved}")
    def onerror(func, target, exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except Exception:
            raise

    shutil.rmtree(resolved, onerror=onerror)


def _ignore(dir_path: str, names: list[str]) -> set[str]:
    ignored = set()
    for name in names:
        p = Path(dir_path) / name
        if name in IGNORE_NAMES or p.suffix in IGNORE_SUFFIXES:
            ignored.add(name)
    return ignored


def _copytree(src: Path, dst: Path, *, ignore_generated: bool = True) -> None:
    if dst.exists():
        _safe_rmtree(dst)
    ignore = _ignore if ignore_generated else None
    shutil.copytree(src, dst, ignore=ignore)


def _copy_original_materials(dst: Path) -> None:
    for file_name in ["方案.pdf", "deep-research-report.md", "elsarticle (2).zip"]:
        src = PROJECT_ROOT / file_name
        if src.exists():
            shutil.copy2(src, dst / file_name)
    for dir_name in ["F", "06_reference_materials", "fig"]:
        src = PROJECT_ROOT / dir_name
        if src.exists():
            _copytree(src, dst / dir_name, ignore_generated=True)
    readme = """# Original and reference materials

This folder keeps the proposal PDF, deep-research notes, the official Elsevier
template ZIP supplied with the project, reference TRE papers, and figure/source
materials that were used while rebuilding the manuscript. These files are not
all inputs to the executable experiments; they are preserved to keep the writing
and formatting provenance traceable.
"""
    (dst / "README.md").write_text(readme, encoding="utf-8")


def _copy_published_latex(dst: Path) -> None:
    src = PROJECT_ROOT / "manuscript_context" / "tre_published_style"
    out = dst / "tre_published_style"
    out.mkdir(parents=True, exist_ok=True)
    for pattern in ["*.tex", "*.bib", "*.bbl", "*.bst", "*.pdf"]:
        for item in src.glob(pattern):
            shutil.copy2(item, out / item.name)
    _copytree(src / "figures", out / "figures", ignore_generated=False)
    ref_dst = dst / "elsevier"
    ref_dst.mkdir(parents=True, exist_ok=True)
    ref_src = PROJECT_ROOT / "manuscript_context" / "elsevier" / "tre_references.bib"
    if ref_src.exists():
        shutil.copy2(ref_src, ref_dst / "tre_references.bib")
    readme = """# Published-style LaTeX package

Main file: `tre_published_style.tex`.

This is the current full review/manuscript version used as the content source.
It is not an official Elsevier class file; it is a TRE published-style review
layout for internal checking and external review discussion.

Build command:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error tre_published_style.tex
```
"""
    (out / "README.md").write_text(readme, encoding="utf-8")


def _build_submission_latex(dst: Path) -> None:
    manuscript = dst / "tre_submission_current"
    manuscript.mkdir(parents=True, exist_ok=True)
    src = PROJECT_ROOT / "manuscript_context" / "tre_published_style"
    for pattern in ["*.tex", "*.bib", "*.bbl"]:
        for item in src.glob(pattern):
            if item.name == "tre_published_style.tex":
                continue
            shutil.copy2(item, manuscript / item.name)
    ref_src = PROJECT_ROOT / "manuscript_context" / "elsevier" / "tre_references.bib"
    if ref_src.exists():
        shutil.copy2(ref_src, manuscript / "tre_references.bib")
    shutil.copy2(src / "tre_published_extra_references.bib", manuscript / "tre_published_extra_references.bib")
    _copytree(src / "figures", manuscript / "figures", ignore_generated=False)

    template_src = PROJECT_ROOT / "06_reference_materials" / "elsarticle_2_template" / "elsarticle"
    template_dst = dst / "elsarticle_official_template_source"
    if template_src.exists():
        _copytree(template_src, template_dst, ignore_generated=True)
        for bst in template_dst.glob("elsarticle-*.bst"):
            shutil.copy2(bst, manuscript / bst.name)
        _generate_elsarticle_cls(template_dst, manuscript)
    elif (PROJECT_ROOT / "elsarticle (2).zip").exists():
        with zipfile.ZipFile(PROJECT_ROOT / "elsarticle (2).zip") as zf:
            zf.extractall(template_dst.parent)
        extracted = template_dst.parent / "elsarticle"
        if extracted.exists():
            for bst in extracted.glob("elsarticle-*.bst"):
                shutil.copy2(bst, manuscript / bst.name)
            _generate_elsarticle_cls(extracted, manuscript)

    main = r"""\documentclass[preprint,10pt,authoryear]{elsarticle}

\usepackage[a4paper,left=14.8mm,right=14.8mm,top=16mm,bottom=18mm]{geometry}
\usepackage{microtype}
\usepackage{amsmath,amssymb,amsfonts}
\usepackage{newtxtext,newtxmath}
\usepackage{algorithm}
\usepackage{algpseudocode}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{multirow}
\usepackage{array}
\usepackage{tabularx}
\usepackage{longtable}
\usepackage{colortbl}
\usepackage{xcolor}
\usepackage{float}
\usepackage{url}
\usepackage[colorlinks=true,linkcolor=blue,citecolor=blue,urlcolor=blue]{hyperref}

\journal{Transportation Research Part E: Logistics and Transportation Review}
\bibliographystyle{elsarticle-harv}
\biboptions{authoryear,round}
\setlength{\bibsep}{2pt}
\renewcommand{\bibfont}{\small}
\emergencystretch=2em
\Urlmuskip=0mu plus 2mu
\sloppy
\graphicspath{{figures/}}

\begin{document}

\begin{frontmatter}

\title{Uncertainty-aware risk-value vehicle--UAV scheduling for transmission-line inspection with probabilistic energy prediction}

\author[inst1]{Author names withheld for review}
\affiliation[inst1]{organization={School of Management Science and Engineering}, city={--}, country={China}}

\begin{abstract}
Large-scale transmission-line inspection increasingly relies on coordinated ground vehicles and unmanned aerial vehicles, but routing decisions remain sensitive to uncertain UAV endurance, heterogeneous tower priorities and sparse feasible stopping locations. This paper formulates transmission-line inspection as an uncertainty-aware risk-value vehicle--UAV scheduling problem. The proposed framework combines a physics-informed probabilistic energy predictor, chance-constrained sortie screening, risk-value task prioritization and an adaptive large-neighborhood search procedure. The energy branch is evaluated with both simulation-generated inspection instances and public quadcopter telemetry, while the routing branch is tested on synthetic corridor instances and public GIS-grounded tower geometries. Computational experiments cover small reference instances, medium and large instances from 30 to 500 towers, energy-prediction accuracy, ablation tests, candidate-stop screening, sensitivity analysis, GIS-grounded cases and stress scenarios. The evidence supports an algorithmic and GIS-grounded scheduling contribution, while field validation with utility inspection records remains future work.
\end{abstract}

\begin{keyword}
Vehicle--UAV routing \sep transmission-line inspection \sep adaptive large-neighborhood search \sep probabilistic energy prediction \sep risk-value scheduling \sep public GIS proxy
\end{keyword}

\end{frontmatter}

\input{full_body}

\bibliography{tre_references,tre_published_extra_references}

\end{document}
"""
    (manuscript / "tre_submission_current.tex").write_text(main, encoding="utf-8")
    readme = """# Elsevier submission LaTeX package

Main file: `tre_submission_current.tex`.

This package follows the official `elsarticle` template style supplied in
`elsarticle (2).zip` and uses the current full manuscript body from the
published-style review version. It is the handoff submission source, while
`01_latex_published_style_current/` remains the full visual review version.

Build command:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
bibtex tre_submission_current
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
```
"""
    (manuscript / "README.md").write_text(readme, encoding="utf-8")


def _generate_elsarticle_cls(template_dir: Path, manuscript_dir: Path) -> None:
    if (template_dir / "elsarticle.cls").exists():
        shutil.copy2(template_dir / "elsarticle.cls", manuscript_dir / "elsarticle.cls")
        return
    ins = template_dir / "elsarticle.ins"
    if not ins.exists():
        return
    latex = _tex_tool("latex.exe")
    try:
        subprocess.run(
            [str(latex), "-interaction=nonstopmode", "elsarticle.ins"],
            cwd=template_dir,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
            check=False,
        )
    except Exception:
        return
    if (template_dir / "elsarticle.cls").exists():
        shutil.copy2(template_dir / "elsarticle.cls", manuscript_dir / "elsarticle.cls")


def _copy_reproducible_code(dst: Path) -> None:
    _copytree(PROJECT_ROOT / "src", dst / "src", ignore_generated=True)
    _copytree(PROJECT_ROOT / "results" / "experiments", dst / "results" / "experiments", ignore_generated=True)
    manuscript_dst = dst / "manuscript_context"
    manuscript_dst.mkdir(parents=True, exist_ok=True)
    for name in ["tre_published_style", "elsevier", "elsevier_preprint"]:
        src = PROJECT_ROOT / "manuscript_context" / name
        if src.exists():
            _copytree(src, manuscript_dst / name, ignore_generated=True)
    requirements = """# Python 3.9 environment used for validation
numpy
scipy
pandas
matplotlib
Pillow
"""
    (dst / "requirements_py39.txt").write_text(requirements, encoding="utf-8")
    readme = """# Reproducible code package

Recommended working directory:

```powershell
cd 04_reproducible_code
py -3.9 -m unittest discover -s src\\tests -v
```

Quick experiment smoke example:

```powershell
py -3.9 src\\scripts\\run_publishable_experiments.py --only P2_algorithm_comparison --run-id reproduced_quick --quick
```

The code writes outputs into `04_reproducible_code/results/experiments/` by default.
The separate `05_experiment_data_by_item/` folder is a reader-facing copy
organized experiment by experiment with entry scripts and existing result data.

Use Python 3.9. The default Python 3.11 environment on the build machine showed
NumPy/SciPy binary-compatibility errors and should not be used as the validation
environment for this package.
"""
    (dst / "README_REPRODUCE.md").write_text(readme, encoding="utf-8")


def _copy_experiment_packages(dst: Path) -> None:
    for exp in EXPERIMENTS:
        src = PROJECT_ROOT / "results" / "experiments" / exp
        if not src.exists():
            continue
        out = dst / exp
        _copytree(src, out, ignore_generated=True)
        _write_experiment_readme(out, exp)
        _write_entry_scripts(out, exp)
    overview = """# Experiment data by item

Each folder contains the existing raw data, analysis tables, run records,
figures/source-data files when available, and two PowerShell entry scripts:

- `RUN_ENTRY_QUICK.ps1`: a small smoke/reproduction run.
- `RUN_ENTRY_FULL.ps1`: the command closest to the manuscript-scale run.

The current manuscript mainly uses the P1--P11 publication experiments. The
E0--E6 folders are retained because they are earlier experiment-suite outputs
and support provenance checking.
"""
    (dst / "README.md").write_text(overview, encoding="utf-8")


def _write_experiment_readme(out: Path, exp: str) -> None:
    raw = sorted((out / "raw_data").glob("*")) if (out / "raw_data").exists() else []
    analysis = sorted((out / "analysis_data").glob("*")) if (out / "analysis_data").exists() else []
    figures = sorted((out / "figures").glob("*")) if (out / "figures").exists() else []
    runs = sorted((out / "runs").glob("*")) if (out / "runs").exists() else []
    boundary = _experiment_boundary(exp)
    text = f"""# {exp} reproduction package

## Contents

- Raw data files: {len(raw)}
- Analysis/result files: {len(analysis)}
- Figure/source files: {len(figures)}
- Recorded run folders: {len(runs)}

## Code entry

- Quick smoke run: `RUN_ENTRY_QUICK.ps1`
- Full/reference run: `RUN_ENTRY_FULL.ps1`

Both scripts run from `../../04_reproducible_code`, so the executable code and
the full project-style data tree remain together.

## Evidence boundary

{boundary}
"""
    (out / "README_REPRODUCE.md").write_text(text, encoding="utf-8")


def _experiment_boundary(exp: str) -> str:
    if exp == "P9_real_gis_case":
        return "Public GIS coordinates and public weather are used; risk/value labels and candidate stops remain proxy-generated."
    if exp == "P10_energy_telemetry_calibration":
        return "AirLab contains public quadcopter telemetry; it is not utility transmission-line inspection field logging."
    if exp == "P11_repair_stress":
        return "Synthetic stress cases test adverse feasibility conditions and do not represent field deployment."
    if exp.startswith("P"):
        return "Publication experiment based on synthetic proposal-scale or controlled proxy data."
    return "Earlier experiment-suite output retained for provenance and smoke reproduction."


def _write_entry_scripts(out: Path, exp: str) -> None:
    quick, full = _entry_commands(exp)
    for name, command in [("RUN_ENTRY_QUICK.ps1", quick), ("RUN_ENTRY_FULL.ps1", full)]:
        script = f"""$ErrorActionPreference = "Stop"
$root = Resolve-Path "$PSScriptRoot\\..\\..\\04_reproducible_code"
Set-Location $root
{command}
"""
        (out / name).write_text(script, encoding="utf-8")


def _entry_commands(exp: str) -> tuple[str, str]:
    if exp.startswith("E"):
        return (
            f'py -3.9 src\\scripts\\run_experiment_suite.py --only {exp} --run-id reproduced_{exp}_quick --quick',
            f'py -3.9 src\\scripts\\run_experiment_suite.py --only {exp} --run-id reproduced_{exp}_full',
        )
    if exp in {"P1_milp_exact_small", "P2_algorithm_comparison", "P3_pinn_prediction_accuracy", "P4_ablation", "P5_case_study", "P6_candidate_stop_screening", "P7_statistical_tests", "P8_sensitivity"}:
        return (
            f'py -3.9 src\\scripts\\run_publishable_experiments.py --only {exp} --run-id reproduced_{exp}_quick --quick',
            f'py -3.9 src\\scripts\\run_publishable_experiments.py --only {exp} --run-id reproduced_{exp}_full --seeds 10',
        )
    if exp == "P9_real_gis_case":
        return (
            'py -3.9 src\\scripts\\run_public_gis_case_experiment.py --case-root results\\experiments\\\P9_real_gis_case\\public_bay_area_full\\gis_case --case-id public_bay_area_full --run-id reproduced_public_bay_area_quick --seeds 2',
            'py -3.9 src\\scripts\\run_public_gis_case_experiment.py --case-root results\\experiments\\\P9_real_gis_case\\public_bay_area_full\\gis_case --case-id public_bay_area_full --run-id reproduced_public_bay_area_full --seeds 10 --methods greedy_nearest,ga,aco,alns_fixed,alns_pinn,alns_pinn_uq,alns_pinn_full',
        )
    if exp == "P10_energy_telemetry_calibration":
        return (
            'py -3.9 src\\scripts\\run_airlab_energy_calibration.py --run-id reproduced_airlab_energy_calibration',
            'py -3.9 src\\scripts\\run_airlab_energy_calibration.py --run-id reproduced_airlab_energy_calibration',
        )
    if exp == "P11_repair_stress":
        return (
            'py -3.9 src\\scripts\\run_repair_stress_experiment.py --run-id reproduced_repair_stress_quick --seeds 2 --iterations 40',
            'py -3.9 src\\scripts\\run_repair_stress_experiment.py --run-id reproduced_repair_stress_full --seeds 10 --iterations 140',
        )
    return ("Write-Host 'No entry command registered.'", "Write-Host 'No entry command registered.'")


def _copy_datasets(dst: Path) -> None:
    airlab = PROJECT_ROOT / "results" / "experiments" / "P10_energy_telemetry_calibration" / "raw_sources" / "airlab"
    if airlab.exists():
        _copytree(airlab, dst / "airlab_energy_telemetry", ignore_generated=True)
    gis_out = dst / "public_gis_proxy_cases"
    gis_out.mkdir(parents=True, exist_ok=True)
    p9 = PROJECT_ROOT / "results" / "experiments" / "P9_real_gis_case"
    if p9.exists():
        for case in p9.glob("public_*"):
            if case.is_dir():
                _copytree(case, gis_out / case.name, ignore_generated=True)
    readme = """# Downloaded and public-source datasets

## AirLab telemetry

`airlab_energy_telemetry/` contains the public AirLab quadcopter telemetry cache
used for energy calibration. It supports the energy-prediction evidence branch,
but it is not transmission-line inspection field telemetry.

## Public GIS proxy cases

`public_gis_proxy_cases/` contains public-geometry and public-weather case
folders used by the GIS-grounded scheduling experiment. Tower locations and
weather inputs are public-data grounded; inspection risk, task value and some
candidate-stop attributes are generated proxies.
"""
    (dst / "README.md").write_text(readme, encoding="utf-8")


def _copy_figure_sources(dst: Path) -> None:
    for dir_name in [
        "results/figures/manuscript",
        "results/figures/publishable",
        "results/figures/tre2style",
    ]:
        src = PROJECT_ROOT / dir_name
        if src.exists():
            _copytree(src, dst / dir_name, ignore_generated=True)
    readme = """# Manuscript figure sources

The current paper uses the figures copied into
`01_latex_published_style_current/tre_published_style/figures/`.

The `results/figures/tre2style/` copy keeps PDF/PNG/SVG outputs and
source CSV files for the latest TRE-style figure family. Use the Python scripts
under `04_reproducible_code/scripts/` to regenerate the figures rather
than editing PDFs directly.
"""
    (dst / "README.md").write_text(readme, encoding="utf-8")


def _copy_revision_change_report(dst: Path) -> None:
    readme = """# Revision change report

This folder contains the extra modification explanation requested for the
2026-05-31 repair delivery. The PDF records each major repair item, the
original text/problem, the revised paper wording or action, and paired original
versus revised manuscript screenshots.

Primary file:

- `Paper1_revision_change_report_with_screenshots.pdf`

Supporting files:

- `revision_change_report.md`: source markdown version of the same change list.
- `screenshots/`: original/revised manuscript screenshot evidence used in the PDF.
- `claim_evidence_manifest.md`: claim-to-evidence ledger for the repair.
- `repair_execution_log.md`: chronological repair and validation log.
"""
    (dst / "README.md").write_text(readme, encoding="utf-8")

    if not REPAIR_OUTPUT_ROOT.exists():
        (dst / "MISSING_REPAIR_OUTPUT_ROOT.txt").write_text(
            f"Expected repair output root was not found: {REPAIR_OUTPUT_ROOT}\n",
            encoding="utf-8",
        )
        return

    files = [
        "Paper1_revision_change_report_with_screenshots.pdf",
        "revision_change_report.md",
        "claim_evidence_manifest.md",
        "repair_execution_log.md",
        "review_issue_audit.md",
        "experiment_setting_crosswalk.md",
        "risk_value_marginal_audit.md",
        "P9_real_gis_case_metric_alignment_20260531_audit.md",
        "build_revision_change_report.py",
    ]
    for rel in files:
        src = REPAIR_OUTPUT_ROOT / rel
        if src.exists():
            shutil.copy2(src, dst / src.name)

    screenshots_src = REPAIR_OUTPUT_ROOT / "revision_change_report" / "screenshots"
    if screenshots_src.exists():
        _copytree(screenshots_src, dst / "screenshots", ignore_generated=False)

    render_src = REPAIR_OUTPUT_ROOT / "revision_report_render_check"
    if render_src.exists():
        _copytree(render_src, dst / "visual_QA_rendered_pages", ignore_generated=False)


def _write_external_review(dst: Path) -> None:
    for name in ["external_review_round_1.md", "revision_response_round_1.md", "submission_readiness_comparison.md"]:
        src = PROJECT_ROOT / "docs/project" / name
        if src.exists():
            shutil.copy2(src, dst / name)
    tex = r"""\documentclass[11pt]{article}
\usepackage[margin=1in]{geometry}
\usepackage{booktabs}
\usepackage{hyperref}
\usepackage{enumitem}
\setlength{\parindent}{0pt}
\setlength{\parskip}{6pt}
\begin{document}
\begin{center}
{\Large External Review Report}\\[3pt]
{\large Uncertainty-aware risk-value vehicle--UAV scheduling for transmission-line inspection}\\[3pt]
Report date: 2026-05-29
\end{center}

\section*{Overall recommendation}
Major revision before journal submission. The manuscript has a credible
algorithmic core, a reproducible experiment base, and a clearer evidence
boundary than the earlier draft. The main remaining risk is not the code, but
how strongly the paper frames simulation-trained and public-proxy evidence.

\section*{Major comments}
\begin{enumerate}[leftmargin=*]
\item \textbf{Evidence boundary.} The paper should consistently state that the
energy model is simulation-trained and AirLab-calibrated, not field-validated on
utility inspection logs. Public GIS/weather cases are useful proxy evidence, but
risk labels and stops are generated.
\item \textbf{Model-to-code traceability.} The current formulation is more
coherent after the q95 sortie-pattern service set, risk-value objective, compact MILP
reference and ALNS state were linked. The final submission should preserve this
sequence and avoid presenting formulas as independent fragments.
\item \textbf{Baselines.} The baseline table now separates constructive,
population-search, fixed ALNS, point energy ALNS and full UQ-risk-value ALNS.
This is necessary because reviewers will not accept comparison algorithms that
appear without literature or design justification.
\item \textbf{Experiment design.} The result section now has an experiment
design map before the results. This should remain in the submission or move to a
supplement rather than being deleted, because it explains why each table and
figure exists.
\item \textbf{Figures and tables.} The current figures are stronger because
they are tied to source CSV files and full result tables. Large raw-data tables
may be moved to supplementary material for a strict journal page limit, but the
handoff package should keep them.
\end{enumerate}

\section*{Minor comments}
\begin{itemize}[leftmargin=*]
\item Check that the Elsevier submission version and the published-style review
version share the same main claims before final journal upload.
\item Keep ``field validation remains future work'' in the abstract,
discussion or data availability statement.
\item If page limits are strict, move the longest raw-data tables and some
mechanism diagnostics to supplementary material rather than deleting the data.
\item Use Python 3.9 for verification; the local default Python environment can
misreport failures due to NumPy/SciPy binary compatibility.
\end{itemize}

\section*{Submission readiness checklist}
\begin{tabular}{@{}p{0.38\linewidth}p{0.50\linewidth}p{0.08\linewidth}@{}}
\toprule
Item & Required action & Status \\
\midrule
Main manuscript logic & Keep model, method, experiments and claims aligned & Partial \\
Reproducibility & Provide code, raw data, source CSV, logs and entry scripts & Ready \\
Evidence boundary & Avoid utility-field-validation claims & Critical \\
Elsevier source package & Compile current content under elsarticle & Ready for check \\
External data & Document AirLab and public GIS limitations & Ready \\
\bottomrule
\end{tabular}

\section*{Conclusion}
The package is suitable for internal/external review and reproducibility
checking. Before formal submission, the authors should decide whether the
published-style full manuscript is submitted as a long article, or whether the
Elsevier version should move some raw-data tables to supplementary material.
\end{document}
"""
    tex_path = dst / "external_review_report.tex"
    tex_path.write_text(tex, encoding="utf-8")
    _run_latex_sequence(dst, "external_review_report", [], dst / "external_review_compile.log")


def _write_delivery_docs(dst: Path, package_name: str) -> None:
    delivery = f"""# Paper1 交付说明

交付包：`{package_name}`

## 主版本说�?
- `01_latex_published_style_current/tre_published_style/`：当前完整发表风格审阅版，主文件�?`tre_published_style.tex`�?- `02_latex_submission_elsarticle_current/tre_submission_current/`：按官方 `elsarticle` 模板整理的投稿版 LaTeX，主文件�?`tre_submission_current.tex`�?- `03_original_and_reference_files/`：原始方案、官�?Elsevier 模板包、对标论文和写作/图形参考材料�?
## 复现材料

- `04_reproducible_code/`：完整代码、测试、实验脚本、论文源目录和项目式实验数据树�?- `05_experiment_data_by_item/`：逐实验拆包，每个实验含原始数据、分析数据、图、运行记录、`RUN_ENTRY_QUICK.ps1`、`RUN_ENTRY_FULL.ps1` 和说明�?- `06_downloaded_datasets/`：外�?公开数据单独归档，包�?AirLab telemetry �?public GIS proxy cases�?- `09_manuscript_figure_sources/`：论文图源、source CSV 和可追溯图文件�?
## 推荐验证命令

```powershell
cd 04_reproducible_code
py -3.9 -m unittest discover -s src\\tests -v
```

```powershell
cd ..\\01_latex_published_style_current\\tre_published_style
pdflatex -interaction=nonstopmode -halt-on-error tre_published_style.tex
```

```powershell
cd ..\\..\\02_latex_submission_elsarticle_current\\tre_submission_current
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
bibtex tre_submission_current
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
```

## 证据边界

AirLab 是公开四旋�?telemetry，不是电网巡检现场日志。Public GIS cases 使用公开几何和天气，但风险、价值和部分候选站属性仍�?proxy。正式投稿时不要写成 field-validated utility inspection logs�?"""
    (dst / "交付说明.md").write_text(delivery, encoding="utf-8")
    current = f"""# Paper1 Current Delivery Notes

Package: `{package_name}`

## Main Contents

- `01_latex_published_style_current/tre_published_style/`: current full manuscript source and compiled PDF.
- `02_latex_submission_elsarticle_current/tre_submission_current/`: current Elsevier submission-style LaTeX package.
- `04_reproducible_code/`: code, tests, experiment scripts, and reproducibility material.
- `05_experiment_data_by_item/`: per-experiment raw data, analysis data, figures, logs, and run entries.
- `08_logs_and_validation/`: unit-test, LaTeX build, log-scan, manifest, and archive hash records.
- `10_revision_change_report/`: repair modification explanation with original/revised screenshots.

## Key Verification Commands

```powershell
cd 04_reproducible_code
py -3.9 -m unittest discover -s src\\tests -v
```

```powershell
cd ..\\01_latex_published_style_current\\tre_published_style
pdflatex -interaction=nonstopmode -halt-on-error tre_published_style.tex
```

```powershell
cd ..\\..\\02_latex_submission_elsarticle_current\\tre_submission_current
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
bibtex tre_submission_current
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
pdflatex -interaction=nonstopmode -halt-on-error tre_submission_current.tex
```

## Evidence Boundary

AirLab is public quadrotor telemetry rather than field utility-inspection logs.
Public GIS cases use open geometry/weather proxies; risk values and some
candidate-stop attributes remain proxy inputs. Formal submission should keep
these boundaries explicit.
"""
    (dst / "README_CURRENT_PACKAGE.md").write_text(current, encoding="utf-8")
def _run_validation(package_dir: Path, paths: dict[str, Path]) -> dict[str, dict[str, object]]:
    validation: dict[str, dict[str, object]] = {}
    validation["unit_tests"] = _run_command(
        ["py", "-3.9", "-m", "unittest", "discover", "-s", "src\\tests", "-v"],
        cwd=paths["code"],
        log_path=paths["logs"] / "unittest_py39.log",
        timeout=180,
    )
    validation["published_latex"] = _run_latex_sequence(
        paths["published"] / "tre_published_style",
        "tre_published_style",
        ["bibtex"],
        paths["logs"] / "published_latex_build.log",
    )
    validation["submission_latex"] = _run_latex_sequence(
        paths["submission"] / "tre_submission_current",
        "tre_submission_current",
        ["bibtex"],
        paths["logs"] / "submission_latex_build.log",
    )
    scan = _scan_latex_logs(paths)
    (paths["logs"] / "latex_log_scan.txt").write_text(scan, encoding="utf-8")
    validation["latex_log_scan"] = {
        "returncode": 0,
        "log": "latex_log_scan.txt",
        "summary": "See latex_log_scan.txt",
    }
    return validation


def _run_latex_sequence(cwd: Path, stem: str, extra_steps: list[str], log_path: Path) -> dict[str, object]:
    pdflatex = _tex_tool("pdflatex.exe")
    bibtex = _tex_tool("bibtex.exe")
    steps: list[list[str]] = [
        [str(pdflatex), "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"],
    ]
    if "bibtex" in extra_steps:
        steps.append([str(bibtex), stem])
    steps.extend(
        [
            [str(pdflatex), "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"],
            [str(pdflatex), "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"],
            [str(pdflatex), "-interaction=nonstopmode", "-halt-on-error", f"{stem}.tex"],
        ]
    )
    combined = []
    rc = 0
    for step in steps:
        result = subprocess.run(step, cwd=cwd, capture_output=True, timeout=240)
        combined.append(f"$ {' '.join(step)}\n")
        combined.append(_decode_process_output(result.stdout))
        combined.append(_decode_process_output(result.stderr))
        combined.append(f"\n[exit {result.returncode}]\n\n")
        if result.returncode != 0:
            rc = result.returncode
            break
    log_path.write_text("".join(combined), encoding="utf-8", errors="replace")
    return {"returncode": rc, "log": log_path.name}


def _run_command(command: list[str], cwd: Path, log_path: Path, timeout: int) -> dict[str, object]:
    result = subprocess.run(command, cwd=cwd, capture_output=True, timeout=timeout)
    log_path.write_text(
        f"$ {' '.join(command)}\n"
        f"{_decode_process_output(result.stdout)}"
        f"{_decode_process_output(result.stderr)}"
        f"\n[exit {result.returncode}]\n",
        encoding="utf-8",
        errors="replace",
    )
    return {"returncode": result.returncode, "log": log_path.name}


def _decode_process_output(data: bytes | None) -> str:
    if not data:
        return ""
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _tex_tool(name: str) -> Path:
    fixed = Path(r"D:\texlive\2022\bin\win32") / name
    if fixed.exists():
        return fixed
    found = shutil.which(name)
    return Path(found) if found else Path(name)


def _scan_latex_logs(paths: dict[str, Path]) -> str:
    candidates = [
        paths["published"] / "tre_published_style" / "tre_published_style.log",
        paths["submission"] / "tre_submission_current" / "tre_submission_current.log",
    ]
    lines = []
    for log in candidates:
        lines.append(f"## {log.relative_to(paths['logs'].parents[0]) if log.exists() else log.name}")
        if not log.exists():
            lines.append("MISSING LOG")
            continue
        hits = []
        for idx, line in enumerate(log.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if "Package: rerunfilecheck" in line:
                continue
            if any(pattern in line for pattern in LATEX_SCAN_PATTERNS):
                hits.append(f"{idx}: {line}")
        lines.extend(hits if hits else ["No matching warnings/errors."])
        lines.append("")
    return "\n".join(lines)


def _write_validation_summary(dst: Path, validation: dict[str, dict[str, object]]) -> None:
    rows = []
    for name, info in validation.items():
        rows.append(f"- {name}: exit={info.get('returncode')}, log={info.get('log')}")
    if not rows:
        rows.append("- Validation was skipped by command-line option.")
    text = "# Validation summary\n\n" + "\n".join(rows) + "\n"
    (dst / "validation_summary.md").write_text(text, encoding="utf-8")


def _write_manifest(package_dir: Path, manifest_path: Path) -> None:
    rows = []
    for file in sorted(package_dir.rglob("*")):
        if file.is_file():
            rel = file.relative_to(package_dir).as_posix()
            rows.append(
                {
                    "path": rel,
                    "bytes": file.stat().st_size,
                    "sha256": _sha256_file(file),
                }
            )
    with manifest_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["path", "bytes", "sha256"])
        writer.writeheader()
        writer.writerows(rows)


def _zip_package(package_dir: Path) -> Path:
    archive = package_dir.with_suffix(".zip")
    if archive.exists():
        archive.unlink()
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as zf:
        for file in sorted(package_dir.rglob("*")):
            if file.is_file():
                zf.write(file, file.relative_to(package_dir.parent))
    return archive


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


if __name__ == "__main__":
    raise SystemExit(main())
