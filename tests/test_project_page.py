import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"


def repository_source_paths():
    paths = []
    for root in ["src", "scripts", "tests"]:
        paths.extend(
            path.relative_to(PROJECT_ROOT).as_posix()
            for path in (PROJECT_ROOT / root).rglob("*.py")
        )
    paths.extend(
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in PROJECT_ROOT.glob("RUN_*.ps1")
    )
    return sorted(paths)


class CodeDocumentationPageTests(unittest.TestCase):
    def test_github_pages_files_exist(self):
        for relative in [
            "index.html",
            "styles.css",
            "app.js",
            "data/site.json",
            "assets/fig3_algorithm_effects.png",
            "assets/fig6_public_gis_cases.png",
        ]:
            self.assertTrue((DOCS / relative).exists(), relative)

    def test_code_documentation_data_has_required_sections(self):
        data = json.loads((DOCS / "data" / "site.json").read_text(encoding="utf-8"))
        self.assertEqual(data["page_type"], "code-documentation")
        self.assertIn("Code Documentation", data["title"])
        self.assertIn("research code package", data["subtitle"])

        section_ids = [section["id"] for section in data["sections"]]
        self.assertEqual(
            section_ids,
            [
                "code-package-overview",
                "source-tree",
                "mathematical-model-implementation",
                "algorithm-implementation",
                "experiment-pipeline",
                "result-artifacts",
                "tests-and-validation",
                "paper-alignment",
            ],
        )

        page_text = json.dumps(data, ensure_ascii=False)
        for required in [
            "src/uqrv/stop_batch_model.py",
            "src/uqrv/rv_alns.py",
            "src/uqrv/solvers.py",
            "scripts/run_publishable_experiments.py",
            "RUN_REPRODUCE_FULL.ps1",
            "RUN_TESTS.ps1",
        ]:
            self.assertIn(required, page_text)
        for forbidden in ["Project page", "Abstract", "Main Evidence", "hero", "landing"]:
            self.assertNotIn(forbidden, page_text)

    def test_html_labels_code_documentation_not_project_page(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        self.assertIn("UQ-RV-ALNS Code Documentation", html)
        self.assertIn("Code Map", html)
        self.assertIn("Module Guide", html)
        self.assertIn("Reproduction", html)
        self.assertIn("Every Source File", html)
        self.assertNotIn("Project Page", html)
        self.assertNotIn("Abstract", html)
        self.assertNotIn("Main Evidence", html)

    def test_source_file_catalog_covers_every_repository_source_file(self):
        data = json.loads((DOCS / "data" / "site.json").read_text(encoding="utf-8"))
        catalog = data["source_files"]
        documented_paths = sorted(item["path"] for item in catalog)
        self.assertEqual(documented_paths, repository_source_paths())

        required_categories = {"package", "script", "test", "entrypoint"}
        self.assertTrue(required_categories.issubset({item["category"] for item in catalog}))
        for item in catalog:
            with self.subTest(path=item["path"]):
                self.assertGreaterEqual(len(item["purpose"]), 60)
                self.assertGreaterEqual(len(item["paper_role"]), 40)
                self.assertTrue(item["main_entries"])
                self.assertTrue(all(entry.strip() for entry in item["main_entries"]))

    def test_code_documentation_preserves_experiment_evidence_and_boundaries(self):
        data = json.loads((DOCS / "data" / "site.json").read_text(encoding="utf-8"))
        highlights = " ".join(item["value"] for item in data["result_highlights"])
        self.assertIn("640", highlights)
        self.assertIn("17.44%", highlights)
        self.assertIn("40.70%", highlights)
        self.assertIn("0.01367", highlights)
        boundaries = " ".join(data["boundaries"])
        self.assertIn("Top-risk coverage", boundaries)
        self.assertIn("not uniformly best", boundaries)

    def test_readme_links_to_code_documentation_page(self):
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Code documentation:", readme)
        self.assertIn("https://xuka0000.github.io/paper1-uqrv-alns/", readme)
        self.assertNotIn("Project page:", readme)


if __name__ == "__main__":
    unittest.main()
