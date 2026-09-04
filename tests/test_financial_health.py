from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro.auth import create_user
from financeiro.database import initialize_database
from financeiro.financial_health import (
    FinancialHealthError,
    calculate_debt_pillar,
    calculate_financial_health_score,
    calculate_financial_health_score_history,
    calculate_financial_peace,
    calculate_limits_pillar,
    calculate_portfolio_concentration_pillar,
    calculate_reserve_pillar,
    calculate_savings_pillar,
    build_pillars,
    emergency_reserve_cents_from_positions,
    fetch_recurring_income_reference,
    score_level,
)
from financeiro.portfolio import current_portfolio_positions
from financeiro.transactions import create_transaction


class FinancialHealthCalculationTest(unittest.TestCase):
    def test_score_level_uses_four_visual_zones(self) -> None:
        # spec: score-saude-financeira v3.7 — critérios 24, 25, 26 e 27
        self.assertEqual(score_level(0, 1000), "critico")
        self.assertEqual(score_level(249, 1000), "critico")
        self.assertEqual(score_level(250, 1000), "atencao")
        self.assertEqual(score_level(280, 1000), "atencao")
        self.assertEqual(score_level(299, 1000), "atencao")
        self.assertEqual(score_level(499, 1000), "atencao")
        self.assertEqual(score_level(500, 1000), "bom")
        self.assertEqual(score_level(749, 1000), "bom")
        self.assertEqual(score_level(750, 1000), "excelente")
        self.assertEqual(score_level(1000, 1000), "excelente")
        self.assertEqual(score_level(49, 200), "critico")
        self.assertEqual(score_level(50, 200), "atencao")

    def test_gauge_has_equal_quadrants_and_uses_backend_level(self) -> None:
        root = Path(__file__).resolve().parents[1]
        view = (root / "web/modules/financial-health-view.js").read_text()
        css = (root / "web/styles.css").read_text()
        self.assertIn("financialHealthScoreZone(data.nivel)", view)
        for value in (0, 250, 500, 750, 1000):
            self.assertIn(f"<span>{value}</span>", view)
        for token, start, end in (("critical", 0, 45), ("attention", 45, 90), ("moderate", 90, 135), ("solid", 135, 180)):
            self.assertIn(f"var(--health-{token}) {start}deg {end}deg", css)
        self.assertIn("0–249 Crítico", view)
        self.assertIn("250–499 Atenção", view)

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
        # spec: score-saude-financeira v3.7 — critério 5
        pillar = calculate_limits_pillar(3, 2)

        self.assertEqual(pillar["score"], 100)
        self.assertEqual(pillar["aderencia_pct"], 66.67)

    def test_limits_score_is_zero_when_no_limits_defined(self) -> None:
        # spec: score-saude-financeira v3.7 — critério 6
        pillar = calculate_limits_pillar(0, 0)

        self.assertEqual(pillar["score"], 0)
        self.assertTrue(pillar["dados_insuficientes"])
        self.assertIn("não cadastrou limites", pillar["mensagem"])

    def test_portfolio_concentration_penalizes_high_class_and_savings(self) -> None:
        # spec: score-saude-financeira v3.7 — critérios 8 e 10
        pillar = calculate_portfolio_concentration_pillar([
            {"asset_type": "fixed_income", "asset_name": "CDB", "current_value_brl_cents": 500_000},
            {"asset_type": "savings", "asset_name": "Poupança", "current_value_brl_cents": 300_000},
            {"asset_type": "stock", "asset_name": "PETR4", "current_value_brl_cents": 200_000},
        ])

        self.assertLess(pillar["score"], 150)
        self.assertIn("Poupança representa", pillar["mensagem"])
        self.assertEqual(pillar["concentracao_poupanca_pct"], 30.0)

    def test_portfolio_concentration_explains_high_fixed_income_without_prescription(self) -> None:
        # spec: score-saude-financeira v3.7 — critério 8
        pillar = calculate_portfolio_concentration_pillar([
            {"asset_type": "fixed_income", "asset_name": "CDB 1", "current_value_brl_cents": 400_000},
            {"asset_type": "fixed_income", "asset_name": "CDB 2", "current_value_brl_cents": 400_000},
            {"asset_type": "stock", "asset_name": "PETR4", "current_value_brl_cents": 200_000},
        ])

        self.assertLess(pillar["score"], 150)
        self.assertEqual(pillar["maior_concentracao_pct"], 80.0)
        self.assertIn("Renda Fixa", pillar["mensagem"])
        self.assertNotIn("compre", pillar["mensagem"].lower())
        self.assertNotIn("venda", pillar["mensagem"].lower())

    def test_portfolio_concentration_explains_high_single_asset_without_prescription(self) -> None:
        # spec: score-saude-financeira v3.7 — critério 9
        pillar = calculate_portfolio_concentration_pillar([
            {"asset_type": "fixed_income", "asset_name": "CDB", "current_value_brl_cents": 650_000},
            {"asset_type": "stock", "asset_name": "PETR4", "current_value_brl_cents": 350_000},
        ])

        self.assertLess(pillar["score"], 150)
        self.assertEqual(pillar["maior_concentracao_pct"], 65.0)
        self.assertIn("CDB", pillar["mensagem"])
        self.assertNotIn("compre", pillar["mensagem"].lower())
        self.assertNotIn("venda", pillar["mensagem"].lower())

    def test_financial_peace_uses_recurring_income_or_month_fallback(self) -> None:
        # spec: score-saude-financeira v3.7 — critérios 11 e 14
        recurring = calculate_financial_peace({"average_cents": 1_000_000, "months_with_income": 12, "window_months": 12}, 800_000)
        partial = calculate_financial_peace({"average_cents": 900_000, "months_with_income": 6, "window_months": 12}, 800_000)
        fallback = calculate_financial_peace({"average_cents": 0, "months_with_income": 0, "window_months": 12}, 800_000)

        self.assertEqual(recurring["confianca"], "alta")
        self.assertEqual(recurring["meses_receita_recorrente"], 12)
        self.assertEqual(recurring["independencia_mensal_cents"], 175_000_000)
        self.assertIn("175x", recurring["independencia_mensal_legenda"])
        self.assertEqual(recurring["reserva_estimada_cents"], 6_000_000)
        self.assertEqual(recurring["recorrentes_saudaveis_cents"], 500_000)
        self.assertEqual(recurring["lazer_saudavel_cents"], 300_000)
        self.assertIn("não são regras fixas", recurring["mensagem"])
        self.assertIn("Consulte um assessor", recurring["mensagem"])
        self.assertEqual(partial["confianca"], "intermediaria")
        self.assertEqual(partial["base_receita_cents"], 900_000)
        self.assertIn("6 mês(es)", partial["aviso"])
        self.assertEqual(fallback["confianca"], "menor")
        self.assertEqual(fallback["base_receita_cents"], 800_000)
        self.assertIn("Consulte um assessor", fallback["mensagem"])

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
        # spec: score-saude-financeira v3.7 — critério 4
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
        # spec: score-saude-financeira v3.7 — critérios 16 e 17
        with self.assertRaises(FinancialHealthError) as context:
            calculate_financial_health_score_history(1, 1000)
        self.assertIn("entre 1 e 36", str(context.exception.message))

        with self.assertRaises(FinancialHealthError) as context:
            calculate_financial_health_score_history(1, 0)
        self.assertIn("entre 1 e 36", str(context.exception.message))

        with self.assertRaises(FinancialHealthError) as context:
            calculate_financial_health_score_history(1, "abc")
        self.assertIn("entre 1 e 36", str(context.exception.message))

        with self.assertRaises(FinancialHealthError) as context:
            calculate_financial_health_score_history(1, None)
        self.assertIn("deve ser informado", str(context.exception.message))


class FinancialHealthDatabaseIntegrationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_score_payload_uses_database_facts_and_is_json_serializable(self) -> None:
        # spec: score-saude-financeira v3.7 — critérios 1, 2, 5, 6, 11, 14 e 15
        user = create_user("Alice", "alice@example.com", "strong-password")
        with database.get_connection() as conn:
            account_id = conn.execute(
                """
                INSERT INTO checking_accounts (
                    user_id, name, bank_name, account_type, currency,
                    initial_balance_cents, current_balance_cents
                ) VALUES (?, 'Conta', 'Banco', 'liquidity', 'BRL', 0, 0)
                """,
                (user["id"],),
            ).lastrowid
            category_id = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Mercado', 'expense')",
                (user["id"],),
            ).lastrowid
            card_id = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, currency, limit_cents, closing_day, due_day
                ) VALUES (?, 'Cartão', 'Banco', 'BRL', 500000, 10, 20)
                """,
                (user["id"],),
            ).lastrowid
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, series_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (user["id"], "income", "Salário", "salario", 1_000_000, 1_000_000, "2026-07-05", account_id, None, "recurring"),
                    (user["id"], "expense", "Mercado maio", "mercado maio", 500_000, 500_000, "2026-05-10", account_id, category_id, "single"),
                    (user["id"], "expense", "Mercado junho", "mercado junho", 500_000, 500_000, "2026-06-10", account_id, category_id, "single"),
                    (user["id"], "expense", "Mercado julho", "mercado julho", 200_000, 200_000, "2026-07-10", account_id, category_id, "single"),
                ],
            )
            conn.execute(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, normalized_description,
                    amount_cents, amount_brl_cents, date, invoice_month, series_kind, installment_index,
                    installment_count, category_id
                ) VALUES (?, ?, 'expense', 'Parcela', 'parcela', 300000, 300000, '2026-07-12', '2026-07', 'installment', 1, 10, ?)
                """,
                (user["id"], card_id, category_id),
            )
            conn.execute(
                """
                INSERT INTO spending_limits (user_id, month, category_id, limit_amount_cents)
                VALUES (?, '2026-07', ?, 600000)
                """,
                (user["id"], category_id),
            )

        with mock.patch(
            "financeiro.financial_health.current_portfolio_positions",
            return_value=[
                {"asset_type": "fixed_income", "asset_name": "CDB", "current_value_brl_cents": 3_000_000, "emergency_reserve_eligible": True},
                {"asset_type": "stock", "asset_name": "PETR4", "current_value_brl_cents": 1_000_000, "emergency_reserve_eligible": False},
            ],
        ):
            payload = calculate_financial_health_score(user["id"], "2026-07")

        self.assertEqual(payload["receitas_cents"], 1_000_000)
        self.assertEqual(payload["despesas_consumo_cents"], 500_000)
        self.assertEqual(payload["reserva_elegivel_cents"], 3_000_000)
        self.assertEqual(payload["meses_reserva"], 6.0)
        self.assertEqual(payload["dividas_parcelas_mes_cents"], 300_000)
        self.assertEqual(payload["comprometimento_divida_mes_pct"], 30.0)
        self.assertEqual(payload["pilar_limites"], 150)
        self.assertEqual(payload["paz_financeira_base_receita_cents"], 1_000_000)
        self.assertEqual(payload["paz_financeira_confianca"], "intermediaria")
        self.assertEqual(payload["paz_financeira_meses_receita_recorrente"], 1)
        self.assertEqual(len(payload["pilares"]), 5)
        json.dumps(payload, ensure_ascii=False)

    def test_score_history_reuses_single_portfolio_snapshot(self) -> None:
        # spec: score-saude-financeira v3.7 — critério 18
        user = create_user("History", "history@example.com", "strong-password")
        positions = [
            {"asset_type": "fixed_income", "asset_name": "CDB", "current_value_brl_cents": 1_000_000, "emergency_reserve_eligible": True},
        ]
        with mock.patch("financeiro.financial_health.current_portfolio_positions", return_value=positions) as portfolio_mock:
            history = calculate_financial_health_score_history(user["id"], 12)

        self.assertEqual(len(history), 12)
        portfolio_mock.assert_called_once_with(user["id"], force_refresh=False)

    def test_foreign_currency_card_totals_use_brl_normalized_amounts(self) -> None:
        # spec: score-saude-financeira v3.7 — critérios 1, 5 e 6
        user = create_user("Diogo", "diogo@example.com", "strong-password")
        with database.get_connection() as conn:
            account_id = conn.execute(
                """
                INSERT INTO checking_accounts (
                    user_id, name, bank_name, account_type, currency,
                    initial_balance_cents, current_balance_cents
                ) VALUES (?, 'Conta', 'Banco', 'liquidity', 'BRL', 0, 0)
                """,
                (user["id"],),
            ).lastrowid
            category_id = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'International', 'expense')",
                (user["id"],),
            ).lastrowid
            card_id = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, currency, limit_cents, closing_day, due_day
                ) VALUES (?, 'Cartão', 'Banco', 'USD', 500000, 10, 20)
                """,
                (user["id"],),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, series_kind
                ) VALUES (?, 'income', 'Salário', 'salario', 1_000_000, 1_000_000, '2026-07-05', ?, NULL, 'recurring')
                """,
                (user["id"], account_id),
            )
            conn.execute(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, normalized_description,
                    amount_cents, amount_brl_cents, date, invoice_month, series_kind, installment_index,
                    installment_count, category_id
                ) VALUES (?, ?, 'expense', 'Compra USD', 'compra usd', 100000, 550000, '2026-07-12', '2026-07', 'installment', 1, 10, ?)
                """,
                (user["id"], card_id, category_id),
            )

        payload = calculate_financial_health_score(user["id"], "2026-07")

        self.assertEqual(payload["receitas_cents"], 1_000_000)
        self.assertEqual(payload["despesas_consumo_cents"], 550_000)
        self.assertEqual(payload["dividas_parcelas_mes_cents"], 550_000)
        self.assertEqual(payload["comprometimento_divida_mes_pct"], 55.0)

    def test_financial_peace_reference_uses_12_month_recurring_average_ignoring_plr(self) -> None:
        # spec: score-saude-financeira v3.7 — critérios 11, 12 e 13
        user = create_user("Carla", "carla@example.com", "strong-password")
        with database.get_connection() as conn:
            account_id = conn.execute(
                """
                INSERT INTO checking_accounts (
                    user_id, name, bank_name, account_type, currency,
                    initial_balance_cents, current_balance_cents
                ) VALUES (?, 'Conta', 'Banco', 'liquidity', 'BRL', 0, 0)
                """,
                (user["id"],),
            ).lastrowid
            rows = []
            for month in range(8, 13):
                rows.append((user["id"], "income", f"Receita recorrente 2025-{month:02d}", "receita recorrente", 900_000, 900_000, f"2025-{month:02d}-05", account_id, "recurring"))
            for month in range(1, 8):
                rows.append((user["id"], "income", f"Receita recorrente 2026-{month:02d}", "receita recorrente", 1_100_000, 1_100_000, f"2026-{month:02d}-05", account_id, "recurring"))
            rows.append((user["id"], "income", "PLR", "plr", 5_000_000, 5_000_000, "2026-07-20", account_id, "single"))
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, series_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            reference = fetch_recurring_income_reference(conn, user["id"], "2026-07")

        self.assertEqual(reference["months_with_income"], 12)
        self.assertEqual(reference["average_cents"], 1_016_667)

    def test_account_investment_operation_marked_as_reserve_counts_in_score(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.53 — critério 19
        user = create_user("Bob", "bob@example.com", "strong-password")
        with database.get_connection() as conn:
            account_id = conn.execute(
                """
                INSERT INTO checking_accounts (
                    user_id, name, bank_name, account_type, currency,
                    initial_balance_cents, current_balance_cents
                ) VALUES (?, 'Conta Investimento', 'Banco', 'investment', 'BRL', 1000000, 1000000)
                """,
                (user["id"],),
            ).lastrowid
            expense_category_id = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Mercado', 'expense')",
                (user["id"],),
            ).lastrowid
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, series_kind
                ) VALUES (?, 'expense', ?, ?, 100000, 100000, ?, ?, ?, 'single')
                """,
                [
                    (user["id"], "Mercado maio", "mercado maio", "2026-05-10", account_id, expense_category_id),
                    (user["id"], "Mercado junho", "mercado junho", "2026-06-10", account_id, expense_category_id),
                    (user["id"], "Mercado julho", "mercado julho", "2026-07-10", account_id, expense_category_id),
                ],
            )

        created = create_transaction(user["id"], {
            "type": "investment",
            "description": "Aporte Poupança",
            "amount": "500,00",
            "investment_amount": "500,00",
            "date": "2026-07-15",
            "account_id": str(account_id),
            "category": "Renda Fixa",
            "subcategory": "Poupança",
            "investment_asset_name": "Poupança",
            "investment_emergency_reserve_eligible": "1",
        })

        self.assertTrue(created["investment_operation"]["emergency_reserve_eligible"])
        # Fixa a data para o dia do aporte, evitando que o rendimento da poupança
        # varie conforme o dia em que o teste roda (falso-positivo).
        fixed_date = date(2026, 7, 15)

        class _FakePortfolioDate:
            @classmethod
            def today(cls) -> date:
                return fixed_date

            @classmethod
            def fromisoformat(cls, raw: str) -> date:
                return date.fromisoformat(raw)

            def __call__(self, *args, **kwargs) -> date:
                return date(*args, **kwargs)

        with mock.patch("financeiro.portfolio.date", _FakePortfolioDate()):
            positions = current_portfolio_positions(user["id"])
            self.assertEqual(emergency_reserve_cents_from_positions(positions), 50_000)

            payload = calculate_financial_health_score(user["id"], "2026-07")
            self.assertEqual(payload["reserva_elegivel_cents"], 50_000)


if __name__ == "__main__":
    unittest.main()
