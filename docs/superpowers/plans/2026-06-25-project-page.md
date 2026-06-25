# Project Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a GitHub Pages project page that introduces the paper1 research code and evidence without using the repository file list as the primary landing experience.

**Architecture:** The site is a static page under `docs/`. `index.html` provides semantic containers, `styles.css` controls the academic project-page layout, `app.js` renders content from `data/site.json`, and copied result PNGs provide visual evidence.

**Tech Stack:** HTML, CSS, vanilla JavaScript, JSON, Python `unittest` validation.

---

### Task 1: Add Project-Page Acceptance Tests

**Files:**
- Create: `tests/test_project_page.py`

- [x] **Step 1: Write failing tests**

Tests require `docs/index.html`, `docs/styles.css`, `docs/app.js`, `docs/data/site.json`, and copied figure assets. Tests also check the required section order and evidence-boundary text.

- [x] **Step 2: Verify red**

Run:

```powershell
py -3.9 -m unittest tests.test_project_page -v
```

Expected: failure because the site files do not exist yet.

### Task 2: Implement Static Project Page

**Files:**
- Create: `docs/index.html`
- Create: `docs/styles.css`
- Create: `docs/app.js`
- Create: `docs/data/site.json`
- Create: `docs/assets/fig3_algorithm_effects.png`
- Create: `docs/assets/fig6_public_gis_cases.png`

- [x] **Step 1: Copy real figure assets**

Copy generated result figures from `results/figures/rendered/` into `docs/assets/`.

- [x] **Step 2: Write content JSON**

Use current P2/P7 evidence values and claim boundaries from `docs/experiments.md` and `docs/claim_algorithm_evidence_ledger.md`.

- [x] **Step 3: Write page shell and renderer**

Keep the page static and GitHub Pages compatible. Do not add build tooling.

### Task 3: Verify And Publish

**Files:**
- Modify: `README.md` only if the Pages link needs correction.

- [ ] **Step 1: Run page tests**

```powershell
py -3.9 -m unittest tests.test_project_page -v
```

- [ ] **Step 2: Run full test suite**

```powershell
.\RUN_TESTS.ps1
```

- [ ] **Step 3: Validate JSON**

```powershell
py -3.9 -m json.tool docs\data\site.json > $null
```

- [ ] **Step 4: Publish**

Commit and update GitHub `main`. If normal `git push` fails, publish through the GitHub API using the authenticated `gh` session.
