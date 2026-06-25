# Paper1 Standard Research Code Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the previous manuscript-subsection reproduction tree with a standard research-code project layout.

**Architecture:** Use one Python package in `src/uqrv`, one test suite in `tests`, one script directory in `scripts`, and one result tree under `results/experiments/<experiment_id>`.

**Tech Stack:** Python 3.9, PowerShell wrappers, `unittest`, CSV/XLSX experiment outputs.

---

### Task 1: Build Canonical Code Tree

**Files:**
- Create: `src/uqrv/`
- Create: `scripts/`
- Create: `tests/`
- Create: `requirements.txt`
- Create: `pyproject.toml`

- [x] Copy the shared package from the common snapshot to `src/uqrv`.
- [x] Copy shared scripts to `scripts`.
- [x] Copy shared tests to `tests`.
- [x] Add package metadata in `pyproject.toml`.

### Task 2: Consolidate Artifacts By Experiment Id

**Files:**
- Create: `results/experiments/`
- Create: `results/tables/`
- Create: `results/figures/`
- Create: `results/consolidated_tables/`
- Create: `manuscript_context/`
- Create: `validation/`
- Create: `metadata/`

- [x] Move experiment records into `results/experiments/<experiment_id>`.
- [x] Merge manuscript tables into `results/tables`.
- [x] Merge rendered figures and source data into `results/figures`.
- [x] Move consolidated CSV/XLSX tables into `results/consolidated_tables`.
- [x] Move validation notes into `validation`.
- [x] Move source manifests into `metadata`.

### Task 3: Adapt Paths

**Files:**
- Modify: `scripts/*.py`
- Modify: `tests/*.py`

- [x] Update imports to use `src`.
- [x] Update experiment output paths to `results/experiments`.
- [x] Update manuscript context paths to `manuscript_context`.
- [x] Remove old `02_code`, `03_experiments`, and `01_manuscript` assumptions.

### Task 4: Add Stable Entrypoints And Docs

**Files:**
- Create: `RUN_TESTS.ps1`
- Create: `RUN_REPRODUCE_QUICK.ps1`
- Create: `RUN_REPRODUCE_FULL.ps1`
- Modify: `README.md`
- Modify: `README_OPEN_FIRST.txt`
- Create: `docs/PROJECT_SOURCE_MAP.md`

- [x] Add root-level test wrapper.
- [x] Add root-level quick/full reproduction wrappers.
- [x] Rewrite documentation for the standard structure.

### Task 5: Verify And Remove Old Layout

**Files:**
- Remove old by-section directories after verification.

- [x] Run `py -3.9 -m unittest discover -s tests -q`.
- [x] Remove old subsection directories and old root manifests after the new layout is verified.
- [x] Re-run the test suite after removal.
