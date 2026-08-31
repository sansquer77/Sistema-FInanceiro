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
    "web/modules/cards-view.js": 1209,
    "web/modules/portfolio-view.js": 1663,
    "web/modules/reports-view.js": 1336,
}
MODULE_SIZE_REVIEW_THRESHOLD = 1200


def line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


class CodeQualityContractTest(unittest.TestCase):
    def test_consultor_settings_and_catalog_boundaries(self) -> None:
        facade = (REPOSITORY_ROOT / "financeiro/consultor.py").read_text(encoding="utf-8")
        settings = (REPOSITORY_ROOT / "financeiro/consultor_settings.py").read_text(encoding="utf-8")
        catalog = (REPOSITORY_ROOT / "financeiro/consultor_catalog.py").read_text(encoding="utf-8")
        self.assertNotIn("get_connection", facade)
        self.assertNotIn("strict_prompt=", facade)
        self.assertIn("INSERT INTO consultor_settings", settings)
        self.assertIn("encrypt_json_for_storage", settings)
        self.assertIn("history_store.delete_history", settings)
        for source in (settings, catalog):
            self.assertNotIn("from financeiro.consultor import", source)
            self.assertNotIn("consultor_provider", source)
            self.assertNotIn("urlopen", source)
        for forbidden in ("get_connection", "secure_config", "consultor_settings", "consultor_history"):
            self.assertNotIn(forbidden, catalog)

    def test_consultor_context_has_no_facade_config_or_transport_dependency(self) -> None:
        facade = (REPOSITORY_ROOT / "financeiro/consultor.py").read_text(encoding="utf-8")
        context = (REPOSITORY_ROOT / "financeiro/consultor_context.py").read_text(encoding="utf-8")
        self.assertNotIn("def compact_positions(", facade)
        self.assertNotIn("def summarize_portfolio(", facade)
        self.assertIn("def build_analysis_context(", facade)
        for forbidden in ("from financeiro.consultor import", "get_connection", "urlopen",
                          "secure_config", "consultor_provider", "consultor_history"):
            self.assertNotIn(forbidden, context)

    def test_consultor_provider_has_no_persistence_or_facade_dependency(self) -> None:
        facade = (REPOSITORY_ROOT / "financeiro/consultor.py").read_text(encoding="utf-8")
        provider = (REPOSITORY_ROOT / "financeiro/consultor_provider.py").read_text(encoding="utf-8")
        self.assertNotIn("request = Request(", facade)
        self.assertNotIn("/chat/completions", facade)
        self.assertIn("request = Request(", provider)
        self.assertNotIn("from financeiro.consultor import", provider)
        self.assertNotIn("get_connection", provider)
        self.assertIn("opener=urlopen", facade)

    def test_consultor_history_is_extracted_behind_compatible_facade(self) -> None:
        facade = (REPOSITORY_ROOT / "financeiro/consultor.py").read_text(encoding="utf-8")
        history = (REPOSITORY_ROOT / "financeiro/consultor_history.py").read_text(encoding="utf-8")
        self.assertIn("from financeiro import consultor_history as history_store", facade)
        self.assertIn("def list_consultor_history", facade)
        self.assertIn("def delete_consultor_history", facade)
        self.assertNotIn("INSERT INTO consultor_analyses", facade)
        self.assertNotIn("DELETE FROM consultor_analyses", facade)
        self.assertIn("INSERT INTO consultor_analyses", history)
        self.assertIn("DELETE FROM consultor_analyses", history)
        self.assertIn("_FAILURE_COOLDOWNS", history)

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
