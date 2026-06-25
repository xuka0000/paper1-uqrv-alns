# Final Manuscript Model-Code Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the code so the final manuscript's mathematical model, ALNS pseudocode and experiment process are executable and auditable.

**Architecture:** Add manuscript-faithful stop-batch model objects and a schedule-state ALNS solver. Keep existing baselines and experiment scripts, but route manuscript-facing ALNS methods through the new implementation.

**Tech Stack:** Python 3.9, dataclasses, unittest, existing `uqrv` package, existing PowerShell reproduction wrappers.

---

### Task 1: Service Graph And Schedule Model

**Files:**
- Create: `src/uqrv/stop_batch_model.py`
- Test: `tests/test_stop_batch_model.py`

- [ ] Write failing tests for service graph construction, q95 filtering, same-stop multi-tower patterns, schedule timing and objective breakdown.
- [ ] Implement `ModelParameters`, `SortiePattern`, `ServiceGraph`, `SortieAssignment`, `ScheduleState` and `ObjectiveBreakdown`.
- [ ] Implement `build_service_graph()` with bounded enumeration of ordered same-stop patterns up to `max_towers_per_sortie`.
- [ ] Implement `evaluate_schedule_state()` with vehicle arrival/departure, UAV launch/recovery, tower completion and depot return.
- [ ] Implement `objective_breakdown()` for RWCT, makespan, ground travel, selected q95 energy and missed-service penalty.
- [ ] Run `py -3.9 -m unittest tests.test_stop_batch_model -q`.

### Task 2: Schedule-State RV-ALNS

**Files:**
- Create: `src/uqrv/rv_alns.py`
- Modify: `src/uqrv/solvers.py`
- Test: `tests/test_rv_alns_schedule_state.py`

- [ ] Write failing tests proving ALNS methods return complete `PlanTask`/`PlanSortie` records with service-graph diagnostics.
- [ ] Implement greedy initial state from \(\mathcal F\) and priority weights.
- [ ] Implement five destroy operators on selected schedule assignments.
- [ ] Implement four repair operators that reinsert removed towers through feasible sortie patterns.
- [ ] Implement pattern replacement/splitting and local search through alternative feasible patterns.
- [ ] Implement adaptive weights and simulated-annealing acceptance.
- [ ] Wire `alns_fixed`, `alns_full`, `uq_rv_alns_full` and ablation methods in `solvers.py` to the new solver.
- [ ] Run `py -3.9 -m unittest tests.test_rv_alns_schedule_state -q`.

### Task 3: Experiment Runner Metadata And Result Refresh

**Files:**
- Modify: `scripts/run_publishable_experiments.py`
- Modify: `scripts/run_repair_stress_experiment.py`
- Test: existing publishable runner tests plus new metadata assertions if needed.

- [ ] Ensure all result rows record `implementation_family=stop_batch_schedule_state_alns`.
- [ ] Ensure ALNS diagnostics export service pattern count, feasible service count, selected sortie count, missed-service count and objective terms.
- [ ] Run `.\RUN_TESTS.ps1`.
- [ ] Rerun main algorithm comparison with a new run id.
- [ ] Rerun ablation/stress quick checks with new run ids.

### Task 4: Documentation And Evidence Ledger

**Files:**
- Create: `docs/model.md`
- Create: `docs/algorithm.md`
- Create: `docs/api.md`
- Create: `docs/experiments.md`
- Create: `docs/claim_algorithm_evidence_ledger.md`
- Modify: `README.md`

- [ ] Document mathematical model symbols and their code fields.
- [ ] Document algorithm pseudocode to implementation mapping.
- [ ] Document public API and result data schema.
- [ ] Document reproduction commands and new result paths.
- [ ] Create the claim/evidence ledger with code paths and commands.

### Task 5: Repository Publication

**Files:**
- Create or update git metadata only after code, tests and docs are ready.

- [ ] Initialize git if the workspace still has no `.git`.
- [ ] Check for GitHub CLI authentication.
- [ ] Create a GitHub repository under the user's account if no remote exists.
- [ ] Commit code, tests, docs and refreshed result metadata.
- [ ] Push to GitHub.
