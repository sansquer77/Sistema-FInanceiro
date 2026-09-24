from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class FinancialGoalsFrontendContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
        cls.module = (ROOT / "web" / "modules" / "limits-view.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "web" / "styles.css").read_text(encoding="utf-8")

    def test_limits_exposes_accessible_spending_and_goals_tabs(self) -> None:
        self.assertIn('role="tablist" aria-label="Áreas de limites"', self.html)
        self.assertIn('data-limits-tab="spending"', self.html)
        self.assertIn('data-limits-tab="goals"', self.html)
        self.assertIn('data-limits-panel="goals"', self.html)

    def test_goal_cards_expose_progress_ring_and_textual_percentage(self) -> None:
        self.assertIn('class="goal-progress-ring"', self.module)
        self.assertIn('aria-label="${progress.toLocaleString("pt-BR")}% da meta atendida"', self.module)
        self.assertIn("conic-gradient", self.styles)
        self.assertIn("new window.ApexCharts", self.module)
        self.assertIn("Rendimento projetado", self.module)
        self.assertIn("Ainda descoberto", self.module)

    def test_goal_ui_uses_backend_for_mutations_and_funding_links(self) -> None:
        self.assertIn('api("/api/financial-goals")', self.module)
        self.assertIn("/movements`, { method: \"POST\"", self.module)
        self.assertIn("/funding-sources`, {", self.module)
        self.assertIn("/funding-sources/${linkId}", self.module)

    def test_funding_options_are_consolidated_investments_without_checking_accounts(self) -> None:
        self.assertNotIn("state.accounts.map((account)", self.module)
        self.assertIn("const assets = new Map()", self.module)
        self.assertIn("position.sources || []", self.module)
        self.assertIn("Vincular investimento", self.module)
        self.assertIn("current_value_brl", self.module)

    def test_emergency_reserve_summary_is_not_merged_into_goal_balance(self) -> None:
        self.assertIn('api("/api/financial-goals/emergency-reserve")', self.module)
        self.assertIn("renderEmergencyReserve", self.module)
        self.assertIn("Saldo sem cobertura conferível", self.module)


if __name__ == "__main__":
    unittest.main()
