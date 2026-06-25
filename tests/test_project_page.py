import json
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS = PROJECT_ROOT / "docs"


class ProjectPageTests(unittest.TestCase):
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

    def test_project_page_data_has_required_sections_without_excluded_sections(self):
        data = json.loads((DOCS / "data" / "site.json").read_text(encoding="utf-8"))
        section_ids = [section["id"] for section in data["sections"]]
        self.assertEqual(
            section_ids,
            [
                "model",
                "algorithm",
                "main-experiment",
                "ablation",
                "public-gis",
                "evidence-boundary",
                "code-docs",
            ],
        )
        page_text = json.dumps(data, ensure_ascii=False)
        for forbidden in ["安装", "开发流程", "架构"]:
            self.assertNotIn(forbidden, page_text)

    def test_project_page_highlights_main_experiment_boundary(self):
        data = json.loads((DOCS / "data" / "site.json").read_text(encoding="utf-8"))
        highlights = " ".join(item["value"] for item in data["result_highlights"])
        self.assertIn("640", highlights)
        self.assertIn("17.44%", highlights)
        self.assertIn("40.70%", highlights)
        self.assertIn("0.01367", highlights)
        boundaries = " ".join(data["boundaries"])
        self.assertIn("Top-risk coverage", boundaries)
        self.assertIn("not uniformly best", boundaries)

    def test_readme_links_to_project_page(self):
        readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("https://xuka0000.github.io/paper1-uqrv-alns/", readme)


if __name__ == "__main__":
    unittest.main()
