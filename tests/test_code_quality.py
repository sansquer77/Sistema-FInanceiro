from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


REVIEWED_OVERSIZED_MODULES = {
    "financeiro/credit_cards.py": 1258,
    "financeiro/database.py": 1310,
    "financeiro/imports.py": 1236,
    "financeiro/portfolio.py": 2812,
    "financeiro/transactions.py": 1334,
    "financeiro/trends.py": 1237,
    "financeiro/consultor.py": 1511,
    "web/modules/cards-view.js": 1209,
    "web/modules/portfolio-view.js": 1663,
    "web/modules/reports-view.js": 1336,
    "web/modules/transactions-view.js": 1593,
}
MODULE_SIZE_REVIEW_THRESHOLD = 1200


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


class CodeQualityContractTest(unittest.TestCase):
    def test_quality_spec_is_implemented_and_indexed(self) -> None:
        spec = (REPOSITORY_ROOT / "docs/qualidade-codigo.md").read_text(encoding="utf-8")
        index = (REPOSITORY_ROOT / "docs/README.md").read_text(encoding="utf-8")

        self.assertIn("status: implementado", spec)
        self.assertIn("Nenhuma pendência conhecida.", spec)
        self.assertIn("[[qualidade-codigo]]", index)

    def test_http_and_spa_roots_do_not_contain_financial_arithmetic(self) -> None:
        app_source = (REPOSITORY_ROOT / "app.py").read_text(encoding="utf-8")
        spa_source = (REPOSITORY_ROOT / "web/app.js").read_text(encoding="utf-8")
        forbidden_backend_helpers = (
            "def cockpit_payload(",
            "def cockpit_transaction_type(",
            "def cockpit_category_label(",
            "def add_cockpit_group(",
            "def ranked_cockpit_rows(",
            "def cents_to_value(",
            "def money_value_to_cents(",
        )

        for helper in forbidden_backend_helpers:
            self.assertNotIn(helper, app_source)
        self.assertNotRegex(app_source, r"\bsum\s*\(")
        self.assertNotIn(".reduce(", app_source)
        self.assertNotRegex(spa_source, r"\bMath\.")
        self.assertNotIn(".reduce(", spa_source)
        self.assertIn("from financeiro.cockpit import cockpit_payload", app_source)
        self.assertIn("from financeiro.balance_projections import build_balance_projection", app_source)

    def test_new_modules_cannot_exceed_review_threshold_without_acknowledgement(self) -> None:
        candidates = {
            path.relative_to(REPOSITORY_ROOT).as_posix(): path
            for root in (REPOSITORY_ROOT / "financeiro", REPOSITORY_ROOT / "web/modules")
            for path in root.glob("*.py" if root.name == "financeiro" else "*.js")
        }
        oversized = {
            relative: path.stat().st_size
            for relative, path in candidates.items()
            if line_count(path) > MODULE_SIZE_REVIEW_THRESHOLD
        }

        self.assertLessEqual(
            set(oversized),
            set(REVIEWED_OVERSIZED_MODULES),
            "Módulo acima do limite sem revisão registrada: "
            + ", ".join(sorted(set(oversized) - set(REVIEWED_OVERSIZED_MODULES))),
        )
        for relative, expected_line_count in REVIEWED_OVERSIZED_MODULES.items():
            path = REPOSITORY_ROOT / relative
            if not path.is_file():
                self.fail(f"Módulo revisado não encontrado: {relative}")
            current_line_count = line_count(path)
            self.assertLessEqual(
                current_line_count,
                expected_line_count,
                f"{relative} cresceu além do tamanho revisado; reavalie suas responsabilidades.",
            )

    def test_quality_spec_references_the_architectural_cleanup_specs(self) -> None:
        spec = (REPOSITORY_ROOT / "docs/qualidade-codigo.md").read_text(encoding="utf-8")
        self.assertIn("[[specs/desconcentracao-arquitetura-v2]]", spec)
        self.assertIn("[[specs/frontend-modularizacao]]", spec)
        self.assertRegex(spec, r"app\.js.*raiz de composição")
        self.assertIn("Todo cálculo financeiro", spec)


if __name__ == "__main__":
    unittest.main()
