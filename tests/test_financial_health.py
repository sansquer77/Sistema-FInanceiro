from __future__ import annotations

import json
import unittest

from financeiro.financial_health import (
    FinancialHealthError,
    calculate_debt_pillar,
    calculate_financial_health_score_history,
    calculate_financial_peace,
    calculate_limits_pillar,
    calculate_portfolio_concentration_pillar,
    calculate_reserve_pillar,
    calculate_savings_pillar,
    build_pillars,
    emergency_reserve_cents_from_positions,
)


class FinancialHealthCalculationTest(unittest.TestCase):
    def test_savings_rate_ignores_investment_as_expense(self) -> None:
        pillar = calculate_savings_pillar(1_000_000, 600_000)

        self.assertEqual(pillar["score"], 250)
        self.assertEqual(pillar["taxa_poupanca_pct"], 40.0)

    def test_reserve_uses_only_explicitly_marked_portfolio_positions(self) -> None:
        positions = [
            {"asset_type": "savings", "current_value_brl_cents": 1_000_000, "emergency_reserve_eligible": True},
            {"asset_type": "fixed_income", "current_value_brl_cents": 2_000_000, "emergency_reserve_eligible": True},
            {"asset_type": "fixed_income", "current_value_brl_cents": 5_000_000, "emergency_reserve_eligible": False},
        ]

        eligible_cents = emergency_reserve_cents_from_positions(positions)
        pillar = calculate_reserve_pillar(eligible_cents, 500_000)

        self.assertEqual(eligible_cents, 3_000_000)
        self.assertEqual(pillar["score"], 250)
        self.assertEqual(pillar["meses_reserva"], 6.0)

    def test_debt_uses_monthly_installments_over_income(self) -> None:
        pillar = calculate_debt_pillar(300_000, 1_000_000)

        self.assertEqual(pillar["comprometimento_pct"], 30.0)
        self.assertEqual(pillar["score"], 150)

    def test_limits_score_uses_share_inside_limit(self) -> None:
        # spec: score-saude-financeira v1.4 — critério 5
        pillar = calculate_limits_pillar(3, 2)

        self.assertEqual(pillar["score"], 100)
        self.assertEqual(pillar["aderencia_pct"], 66.67)

    def test_limits_score_is_zero_when_no_limits_defined(self) -> None:
        # spec: score-saude-financeira v1.4 — critério 6
        pillar = calculate_limits_pillar(0, 0)

        self.assertEqual(pillar["score"], 0)
        self.assertTrue(pillar["dados_insuficientes"])
        self.assertIn("não cadastrou limites", pillar["mensagem"])

    def test_portfolio_concentration_penalizes_high_class_and_savings(self) -> None:
        pillar = calculate_portfolio_concentration_pillar([
            {"asset_type": "fixed_income", "asset_name": "CDB", "current_value_brl_cents": 500_000},
            {"asset_type": "savings", "asset_name": "Poupança", "current_value_brl_cents": 300_000},
            {"asset_type": "stock", "asset_name": "PETR4", "current_value_brl_cents": 200_000},
        ])

        self.assertLess(pillar["score"], 150)
        self.assertIn("Poupança representa", pillar["mensagem"])
        self.assertEqual(pillar["concentracao_poupanca_pct"], 30.0)

    def test_financial_peace_uses_recurring_income_or_month_fallback(self) -> None:
        # spec: score-saude-financeira v1.3 — critérios 9 e 10
        recurring = calculate_financial_peace(1_000_000, 800_000)
        fallback = calculate_financial_peace(0, 800_000)

        self.assertEqual(recurring["confianca"], "alta")
        self.assertEqual(recurring["independencia_mensal_cents"], 175_000_000)
        self.assertIn("175x", recurring["independencia_mensal_legenda"])
        self.assertEqual(recurring["reserva_estimada_cents"], 6_000_000)
        self.assertEqual(recurring["recorrentes_saudaveis_cents"], 500_000)
        self.assertEqual(recurring["lazer_saudavel_cents"], 300_000)
        self.assertIn("não são regras fixas", recurring["mensagem"])
        self.assertIn("Consulte um assessor", recurring["disclaimer"])
        self.assertEqual(fallback["confianca"], "menor")
        self.assertEqual(fallback["base_receita_cents"], 800_000)
        self.assertIn("Consulte um assessor", fallback["disclaimer"])

    def test_pillars_payload_is_json_serializable(self) -> None:
        pillars = build_pillars([
            calculate_savings_pillar(1_000_000, 600_000),
            calculate_reserve_pillar(3_000_000, 500_000),
            calculate_debt_pillar(300_000, 1_000_000),
            calculate_limits_pillar(3, 2),
            calculate_portfolio_concentration_pillar([]),
        ])

        encoded = json.dumps({"pilares": pillars}, ensure_ascii=False)
        self.assertIn("Taxa de Poupança", encoded)

    def test_pillars_return_neutral_scores_when_denominator_is_zero(self) -> None:
        # spec: score-saude-financeira v1.2 — critério 4
        savings = calculate_savings_pillar(0, 0)
        reserve = calculate_reserve_pillar(0, 0)
        debt = calculate_debt_pillar(0, 0)

        self.assertEqual(savings["score"], 125)
        self.assertEqual(savings["taxa_poupanca_pct"], 0.0)
        self.assertTrue(savings["dados_insuficientes"])

        self.assertEqual(reserve["score"], 125)
        self.assertEqual(reserve["meses_reserva"], 0.0)
        self.assertTrue(reserve["dados_insuficientes"])

        self.assertEqual(debt["score"], 100)
        self.assertEqual(debt["comprometimento_pct"], 0.0)
        self.assertTrue(debt["dados_insuficientes"])

    def test_score_history_rejects_months_out_of_bounds(self) -> None:
        # spec: score-saude-financeira v1.5 — critérios 12 e 13
        with self.assertRaises(FinancialHealthError) as context:
            calculate_financial_health_score_history(1, 1000)
        self.assertIn("entre 1 e 36", str(context.exception.message))

        with self.assertRaises(FinancialHealthError) as context:
            calculate_financial_health_score_history(1, 0)
        self.assertIn("entre 1 e 36", str(context.exception.message))

        with self.assertRaises(FinancialHealthError) as context:
            calculate_financial_health_score_history(1, "abc")
        self.assertIn("entre 1 e 36", str(context.exception.message))


if __name__ == "__main__":
    unittest.main()
