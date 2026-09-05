import hashlib
import json
import unittest

from financeiro import consultor, consultor_catalog as catalog
from financeiro.consultor_errors import ConsultorError


class ConsultorCatalogTest(unittest.TestCase):
    def test_catalog_and_all_prompt_combinations_match_pre_extraction(self):
        # Snapshot da fachada anterior: todos os cards, perfis e períodos válidos.
        prompts = [
            catalog.build_system_prompt(card.analysis_id, investor_profile=profile, period_window=period)
            for card in catalog.ANALYSIS_CATALOG
            for profile in catalog.INVESTOR_PROFILES
            for period in card.period_window_options or (None,)
        ]
        payload = {
            "cards": catalog.list_analysis_cards(),
            "prompts": prompts,
            "profiles": catalog.INVESTOR_PROFILES,
        }
        digest = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
        self.assertEqual(digest, "2d0d347d6e1e11290bd82cd8a0038f492c3f1e763af8c146387431f70a290e5f")

    def test_public_contract_and_exception_identity(self):
        self.assertIs(consultor.ConsultorError, ConsultorError)
        for name in ("AnalysisCard", "ANALYSIS_CATALOG", "list_analysis_cards",
                     "build_system_prompt", "validate_period_window", "validate_investor_profile"):
            self.assertIs(getattr(consultor, name), getattr(catalog, name))
        with self.assertRaises(consultor.ConsultorError):
            catalog.validate_analysis_id("not-a-card")

    def test_listing_returns_independent_serializable_data(self):
        listing = catalog.list_analysis_cards()
        listing[0]["period_window_options"].append("invalid")
        listing[0]["title"] = "changed"
        self.assertNotIn("invalid", catalog.list_analysis_cards()[0]["period_window_options"])
        self.assertNotEqual(catalog.list_analysis_cards()[0]["title"], "changed")
        json.dumps(catalog.list_analysis_cards())


if __name__ == "__main__":
    unittest.main()
