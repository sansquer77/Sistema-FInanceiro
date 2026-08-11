from __future__ import annotations

import contextlib
import json
import os
import tempfile
import unittest
from urllib.error import URLError
from http import HTTPStatus
from pathlib import Path
from unittest import mock

import app
from financeiro.ai_summary import generate_ai_summary, minimize_trends_payload
from financeiro.ai_summary import SYSTEM_PROMPT
from financeiro import database
from financeiro.auth import create_user
from financeiro.credit_cards import (
    create_credit_card,
    create_credit_card_transaction,
    move_credit_card_transaction_invoice,
)
from financeiro.database import initialize_database
from financeiro.trends import calculate_trends


class TrendsCalculationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-trends.db"
        self.key_env_patch = mock.patch.dict(
            os.environ,
            {"SISTEMA_FINANCEIRO_CONFIG_KEY_PATH": f"{self.tempdir.name}-secure/config.key"},
        )
        self.key_env_patch.start()
        initialize_database()

    def tearDown(self) -> None:
        self.key_env_patch.stop()
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_empty_user_returns_series_and_zero_values(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 1, 3, 5, 6, 27 e 28
        user = create_user("T1", "t1@example.com", "strong-password")
        result = calculate_trends(user["id"], "2026-07")

        self.assertEqual(result["month"], "2026-07")
        self.assertEqual(result["receitas_mes_cents"], 0)
        self.assertEqual(result["despesas_mes_cents"], 0)
        self.assertEqual(result["confianca"], "baixa")
        self.assertEqual(result["orcamento_realizado"], [])
        self.assertTrue(result["resumo_local"])
        self.assertIsNone(result["resumo_ia"])
        self.assertFalse(result["ia_ativa"])
        self.assertEqual(result["currency"], "BRL")
        json.dumps(result, ensure_ascii=False)

    def test_series_includes_account_and_credit_card_by_invoice_month(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 3, 25 e 26
        user = create_user("T2", "t2@example.com", "strong-password")
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
                    (user["id"], "expense", "Mercado junho", "mercado junho", 500_000, 500_000, "2026-06-10", account_id, category_id, "single"),
                    (user["id"], "expense", "Mercado julho", "mercado julho", 200_000, 200_000, "2026-07-10", account_id, category_id, "single"),
                ],
            )
            conn.execute(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, normalized_description,
                    amount_cents, amount_brl_cents, date, invoice_month, series_kind, category_id
                ) VALUES (?, ?, 'expense', 'Compra', 'compra', 100000, 100000, '2026-07-12', '2026-07', 'single', ?)
                """,
                (user["id"], card_id, category_id),
            )

        result = calculate_trends(user["id"], "2026-07")
        months = {entry["month"]: entry for entry in result["serie_mensal"]}
        self.assertEqual(months["2026-06"]["income_cents"], 0)
        self.assertEqual(months["2026-06"]["expense_cents"], 500_000)
        self.assertEqual(months["2026-07"]["income_cents"], 1_000_000)
        self.assertEqual(months["2026-07"]["expense_cents"], 300_000)
        self.assertEqual(result["receitas_mes_cents"], 1_000_000)
        self.assertEqual(result["despesas_mes_cents"], 300_000)
        self.assertEqual(result["confianca"], "baixa")

    def test_foreign_currency_credit_card_uses_ptax_normalized_value(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 3, 26 e 27
        user = create_user("T2B", "t2b@example.com", "strong-password")
        card = create_credit_card(user["id"], {
            "name": "Cartão USD",
            "issuer": "Banco",
            "currency": "USD",
            "limit": "1000,00",
            "closing_day": "10",
            "due_day": "20",
        })
        response_mock = mock.Mock()
        response_mock.__enter__ = mock.Mock(return_value=response_mock)
        response_mock.__exit__ = mock.Mock(return_value=False)
        response_mock.read.return_value = json.dumps({
            "value": [{"cotacaoVenda": 5.50, "dataHoraCotacao": "2026-07-10 13:10:00.000"}]
        }).encode("utf-8")

        with mock.patch("financeiro.transactions.urlopen", return_value=response_mock):
            transaction = create_credit_card_transaction(user["id"], {
                "credit_card_id": str(card["id"]),
                "type": "expense",
                "description": "Assinatura USD",
                "amount": "10,00",
                "date": "2026-07-10",
                "invoice_month": "2026-07",
                "category": "Assinaturas e Serviços",
            })

        result = calculate_trends(user["id"], "2026-07")
        july = next(item for item in result["serie_mensal"] if item["month"] == "2026-07")
        self.assertEqual(transaction["amount_brl"], "55.00")
        self.assertEqual(july["expense_cents"], 5_500)

    def test_budget_vs_actual_uses_existing_limits(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 4 e 5
        user = create_user("T3", "t3@example.com", "strong-password")
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
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, series_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (user["id"], "income", "Salário", "salario", 1_000_000, 1_000_000, "2026-07-05", account_id, None, "recurring"),
                    (user["id"], "expense", "Mercado julho", "mercado julho", 700_000, 700_000, "2026-07-10", account_id, category_id, "single"),
                ],
            )
            conn.execute(
                "INSERT INTO spending_limits (user_id, month, category_id, limit_amount_cents) VALUES (?, '2026-07', ?, 600000)",
                (user["id"], category_id),
            )

        result = calculate_trends(user["id"], "2026-07")
        self.assertEqual(len(result["orcamento_realizado"]), 1)
        row = result["orcamento_realizado"][0]
        self.assertEqual(row["limite_cents"], 600_000)
        self.assertEqual(row["realizado_cents"], 700_000)
        self.assertEqual(row["estado"], "Acima do limite")
        self.assertEqual(row["percentual_usado"], 116.67)

        limit_finding = [f for f in result["achados"] if f["tipo"] == "limite"]
        self.assertTrue(limit_finding)
        self.assertIn("acima do limite", limit_finding[0]["titulo"].lower())

    def test_cash_opportunity_uses_projected_end_of_month_balance(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 54
        user = create_user("T3B", "t3b@example.com", "strong-password")
        with database.get_connection() as conn:
            account_id = conn.execute(
                """
                INSERT INTO checking_accounts (
                    user_id, name, bank_name, account_type, currency,
                    initial_balance_cents, current_balance_cents
                ) VALUES (?, 'Conta', 'Banco', 'liquidity', 'BRL', 1500000, 1500000)
                """,
                (user["id"],),
            ).lastrowid
            category_id = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Casa', 'expense')",
                (user["id"],),
            ).lastrowid
            card_id = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, currency, limit_cents, closing_day, due_day,
                    preferred_payment_account_id
                ) VALUES (?, 'Cartão', 'Banco', 'BRL', 500000, 5, 20, ?)
                """,
                (user["id"], account_id),
            ).lastrowid
            conn.execute(
                "INSERT INTO spending_limits (user_id, month, category_id, limit_amount_cents) VALUES (?, '2026-07', ?, 500000)",
                (user["id"], category_id),
            )
            conn.execute(
                """
                INSERT INTO credit_card_transactions (
                    user_id, credit_card_id, type, description, amount_cents,
                    amount_brl_cents, date, invoice_month, series_kind, category_id,
                    reconciled_at
                ) VALUES (?, ?, 'expense', 'Compra em aberto', 300000, 300000, '2026-07-10', '2026-07', 'single', ?, CURRENT_TIMESTAMP)
                """,
                (user["id"], card_id, category_id),
            )

        result = calculate_trends(user["id"], "2026-07")
        finding = [f for f in result["achados"] if f["tipo"] == "oportunidade_caixa"]
        self.assertTrue(finding)
        self.assertEqual(result["oportunidade_caixa"]["saldo_previsto_fim_mes_cents"], 1_200_000)
        self.assertIn("2x das despesas planejadas", result["resumo_local"])

    def test_point_income_bonus_and_plr(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 8 e 9
        user = create_user("T4", "t4@example.com", "strong-password")
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
            cat_bonus = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Renda Extra', 'income')",
                (user["id"],),
            ).lastrowid
            sub_bonus = conn.execute(
                "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, 'Bônus / PLR')",
                (user["id"], cat_bonus),
            ).lastrowid
            cat_outras = conn.execute(
                "SELECT id FROM categories WHERE user_id = ? AND name = 'Outras Receitas' AND group_type = 'income'",
                (user["id"],),
            ).fetchone()["id"]
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, subcategory_id, series_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (user["id"], "income", "Salário", "salario", 500_000, 500_000, "2026-07-05", account_id, cat_bonus, None, "recurring"),
                    (user["id"], "income", "PLR 2026", "plr 2026", 2_000_000, 2_000_000, "2026-07-20", account_id, cat_bonus, sub_bonus, "single"),
                    (user["id"], "income", "Freela pontual", "freela pontual", 800_000, 800_000, "2026-07-21", account_id, cat_outras, None, "single"),
                ],
            )

        result = calculate_trends(user["id"], "2026-07")
        self.assertEqual(result["receitas_mes_cents"], 3_300_000)
        events = result["eventos_pontuais"]
        self.assertEqual(len(events), 2)
        self.assertTrue(any("PLR" in e["descricao"] for e in events))
        self.assertTrue(any("Freela" in e["descricao"] for e in events))

        point_findings = [f for f in result["achados"] if f["tipo"] == "evento_pontual"]
        self.assertTrue(point_findings)
        self.assertTrue(any("pontual" in f["descricao"].lower() for f in point_findings))

    def test_point_expense_travel_and_emergency(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 13
        user = create_user("T5", "t5@example.com", "strong-password")
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
            cat_lazer = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Viagem e Turismo', 'expense')",
                (user["id"],),
            ).lastrowid
            sub_viagem = conn.execute(
                "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, 'Viagens, Passagens e Hospedagens (Férias)')",
                (user["id"], cat_lazer),
            ).lastrowid
            cat_hab = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Casa', 'expense')",
                (user["id"],),
            ).lastrowid
            sub_reparo = conn.execute(
                "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, 'Manutenção, Reparos e Reformas')",
                (user["id"], cat_hab),
            ).lastrowid
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, subcategory_id, series_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (user["id"], "income", "Salário", "salario", 1_000_000, 1_000_000, "2026-07-05", account_id, None, None, "recurring"),
                    (user["id"], "expense", "Passagem", "passagem", 1_500_000, 1_500_000, "2026-07-10", account_id, cat_lazer, sub_viagem, "single"),
                    (user["id"], "expense", "Reparo", "reparo", 400_000, 400_000, "2026-07-12", account_id, cat_hab, sub_reparo, "single"),
                ],
            )

        result = calculate_trends(user["id"], "2026-07")
        events = result["eventos_pontuais"]
        self.assertEqual(len(events), 2)
        self.assertTrue(any(e["tipo"] == "ferias" for e in events))
        self.assertTrue(any(e["tipo"] == "manutencao_emergencia" for e in events))

    def test_point_event_findings_are_grouped_by_subcategory(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 7, 10 e 13
        user = create_user("T5B", "t5b@example.com", "strong-password")
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
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Casa', 'expense')",
                (user["id"],),
            ).lastrowid
            subcategory_id = conn.execute(
                "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, 'Manutenção, Reparos e Reformas')",
                (user["id"], category_id),
            ).lastrowid
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, subcategory_id, series_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (user["id"], "expense", "Reparo 1", "reparo 1", 100_000, 100_000, "2026-07-10", account_id, category_id, subcategory_id, "single"),
                    (user["id"], "expense", "Reparo 2", "reparo 2", 150_000, 150_000, "2026-07-12", account_id, category_id, subcategory_id, "single"),
                ],
            )

        result = calculate_trends(user["id"], "2026-07")
        findings = [
            finding for finding in result["achados"]
            if finding["tipo"] == "evento_pontual" and "Manutenção" in finding["titulo"]
        ]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["valor_cents"], 250_000)
        self.assertIn("2 lançamento(s)", findings[0]["descricao"])

    def test_installment_acceleration_is_detected_from_operation_log(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 13
        user = create_user("T6", "t6@example.com", "strong-password")
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
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Compras Online', 'expense')",
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

        transaction = create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card_id),
            "type": "expense",
            "description": "Notebook Dell",
            "amount": "300,00",
            "date": "2026-06-05",
            "invoice_month": "2026-08",
            "category": "Compras Online",
            "series_kind": "installment",
            "installment_count": 3,
        })

        with database.get_connection() as conn:
            future_installment_id = conn.execute(
                """
                SELECT id
                FROM credit_card_transactions
                WHERE user_id = ? AND credit_card_id = ? AND invoice_month = '2026-08'
                ORDER BY id
                LIMIT 1
                """,
                (user["id"], card_id),
            ).fetchone()["id"]

        moved = move_credit_card_transaction_invoice(user["id"], str(future_installment_id), "previous")
        self.assertEqual(moved["invoice_month"], "2026-07")

        result = calculate_trends(user["id"], "2026-07")
        self.assertEqual(len(result["antecipacao_parcelas"]), 1)
        self.assertEqual(result["antecipacao_parcelas"][0]["valor_cents"], 10000)
        self.assertEqual(result["antecipacao_parcelas"][0]["compra"], "Notebook Dell")
        acceleration_findings = [finding for finding in result["achados"] if finding["tipo"] == "antecipacao_parcela"]
        self.assertTrue(acceleration_findings)
        self.assertIn("antecipação", acceleration_findings[0]["descricao"].lower())
        self.assertEqual(acceleration_findings[0]["valor_cents"], 10000)
        self.assertIn("totalizando R$ 100,00", acceleration_findings[0]["descricao"])
        self.assertIn("Notebook Dell", acceleration_findings[0]["descricao"])
        self.assertNotIn("parcelas antecipadas", result["resumo_local"].lower())
        self.assertTrue([finding for finding in result["achados"] if finding["tipo"] == "antecipacao_parcela"])
        self.assertNotIn("Notebook Dell", result["resumo_local"])

    def test_installment_postponement_is_not_detected_as_acceleration(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 13
        user = create_user("T6B", "t6b@example.com", "strong-password")
        with database.get_connection() as conn:
            category_id = conn.execute(
                "INSERT INTO categories (user_id, name, group_type) VALUES (?, 'Compras Online', 'expense')",
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

        transaction = create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card_id),
            "type": "expense",
            "description": "Compra postergada",
            "amount": "120,00",
            "date": "2026-07-05",
            "invoice_month": "2026-07",
            "category": "Compras Online",
            "series_kind": "installment",
            "installment_count": 2,
        })

        moved = move_credit_card_transaction_invoice(user["id"], str(transaction["id"]), "next")
        self.assertEqual(moved["invoice_month"], "2026-08")

        result = calculate_trends(user["id"], "2026-08")
        self.assertEqual(result["antecipacao_parcelas"], [])
        self.assertFalse([finding for finding in result["achados"] if finding["tipo"] == "antecipacao_parcela"])

    def test_future_installments_concentrated_in_invoice_are_detected_as_acceleration(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 13
        user = create_user("T6C", "t6c@example.com", "strong-password")
        with database.get_connection() as conn:
            card_id = conn.execute(
                """
                INSERT INTO credit_cards (
                    user_id, name, issuer, currency, limit_cents, closing_day, due_day
                ) VALUES (?, 'Cartão', 'Banco', 'BRL', 500000, 10, 20)
                """,
                (user["id"],),
            ).lastrowid

        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card_id),
            "type": "expense",
            "description": "BYD Original",
            "amount": "300,00",
            "date": "2026-07-05",
            "invoice_month": "2026-07",
            "category": "Transporte",
            "series_kind": "installment",
            "installment_count": 3,
        })

        with database.get_connection() as conn:
            conn.execute(
                """
                UPDATE credit_card_transactions
                SET invoice_month = '2026-07'
                WHERE user_id = ? AND credit_card_id = ? AND date > '2026-07-31'
                """,
                (user["id"], card_id),
            )

        result = calculate_trends(user["id"], "2026-07")
        self.assertEqual(len(result["antecipacao_parcelas"]), 2)
        self.assertEqual(sum(item["valor_cents"] for item in result["antecipacao_parcelas"]), 20000)
        self.assertTrue(all(item["origem"] == "concentracao_parcelas" for item in result["antecipacao_parcelas"]))
        acceleration_findings = [finding for finding in result["achados"] if finding["tipo"] == "antecipacao_parcela"]
        self.assertTrue(acceleration_findings)
        self.assertIn("BYD Original", acceleration_findings[0]["descricao"])
        self.assertNotIn("parcelas antecipadas", result["resumo_local"].lower())
        self.assertTrue([finding for finding in result["achados"] if finding["tipo"] == "antecipacao_parcela"])

    def test_confidence_intermediate_with_three_months(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 6 e 22
        user = create_user("T7", "t7@example.com", "strong-password")
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
            for month in ("2026-04", "2026-05", "2026-06"):
                rows.append((user["id"], "income", "Salário", "salario", 1_000_000, 1_000_000, f"{month}-05", account_id, "recurring"))
                rows.append((user["id"], "expense", "Mercado", "mercado", 400_000, 400_000, f"{month}-10", account_id, "single"))
            rows.append((user["id"], "income", "Salário", "salario", 1_000_000, 1_000_000, "2026-07-05", account_id, "recurring"))
            rows.append((user["id"], "expense", "Mercado", "mercado", 600_000, 600_000, "2026-07-10", account_id, "single"))
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, series_kind
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

        result = calculate_trends(user["id"], "2026-07")
        self.assertEqual(result["confianca"], "intermediaria")
        self.assertEqual(result["historico_meses_disponiveis"], 3)
        self.assertEqual(result["receitas_base_comparacao_cents"], 1_000_000)
        self.assertEqual(result["despesas_base_comparacao_cents"], 400_000)
        self.assertEqual(result["despesas_mes_cents"], 600_000)

        expense_finding = [f for f in result["achados"] if f["tipo"] == "despesa"]
        self.assertTrue(expense_finding)
        self.assertEqual(expense_finding[0]["valor_cents"], 200_000)

    def test_confidence_high_with_six_months(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 6, 22, 96
        user = create_user("T8", "t8@example.com", "strong-password")
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
            for i in range(1, 8):
                month = f"2026-{i:02d}"
                conn.execute(
                    """
                    INSERT INTO transactions (
                        user_id, type, description, normalized_description, amount_cents,
                        amount_brl_cents, date, account_id, series_kind
                    ) VALUES (?, 'income', 'Salário', 'salario', 1000000, 1000000, ?, ?, 'recurring')
                    """,
                    (user["id"], f"{month}-05", account_id),
                )

        result = calculate_trends(user["id"], "2026-07")
        self.assertEqual(result["confianca"], "alta")
        self.assertEqual(result["receitas_base_comparacao_cents"], 1_000_000)

    def test_recurring_subscriptions_aggregated_by_subcategory(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 29
        user = create_user("T10", "t10@example.com", "strong-password")
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
            cat_id = conn.execute(
                "SELECT id FROM categories WHERE user_id = ? AND name = 'Assinaturas e Serviços' AND group_type = 'expense'",
                (user["id"],),
            ).fetchone()["id"]
            sub_streaming = conn.execute(
                "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, 'Streaming de Vídeo')",
                (user["id"], cat_id),
            ).lastrowid
            sub_music = conn.execute(
                "INSERT INTO subcategories (user_id, category_id, name) VALUES (?, ?, 'Streaming de Música')",
                (user["id"], cat_id),
            ).lastrowid
            conn.executemany(
                """
                INSERT INTO transactions (
                    user_id, type, description, normalized_description, amount_cents,
                    amount_brl_cents, date, account_id, category_id, subcategory_id, series_kind, recurrence_frequency
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (user["id"], "income", "Salário", "salario", 3_000_000, 3_000_000, "2026-07-05", account_id, None, None, "recurring", "monthly"),
                    (user["id"], "expense", "Netflix", "netflix", 20_000, 20_000, "2026-07-10", account_id, cat_id, sub_streaming, "recurring", "monthly"),
                    (user["id"], "expense", "Disney+", "disney", 40_000, 40_000, "2026-07-10", account_id, cat_id, sub_streaming, "recurring", "monthly"),
                    (user["id"], "expense", "Spotify", "spotify", 20_000, 20_000, "2026-07-10", account_id, cat_id, sub_music, "recurring", "monthly"),
                    (user["id"], "expense", "Celular", "celular", 100_000, 100_000, "2026-07-15", account_id, cat_id, None, "recurring", "monthly"),
                ],
            )

        result = calculate_trends(user["id"], "2026-07")
        subscriptions = result["assinaturas_e_servicos"]
        self.assertEqual(len(subscriptions), 3)

        streaming = next(item for item in subscriptions if item["subcategory_name"] == "Streaming de Vídeo")
        self.assertEqual(streaming["valor_cents"], 60_000)

        music = next(item for item in subscriptions if item["subcategory_name"] == "Streaming de Música")
        self.assertEqual(music["valor_cents"], 20_000)

        geral = next(item for item in subscriptions if item["subcategory_name"] == "Geral")
        self.assertEqual(geral["valor_cents"], 100_000)

        subscription_findings = [f for f in result["achados"] if f["tipo"] == "assinatura_servico"]
        self.assertEqual(len(subscription_findings), 3)
        for finding in subscription_findings:
            self.assertEqual(finding["severidade"], "info")
            self.assertNotIn("cancele", finding["descricao"].lower())
            self.assertNotIn("cancelar", finding["descricao"].lower())
            self.assertIn("vale revisar", finding["descricao"].lower())

        self.assertIn("Assinaturas e serviços recorrentes", result["resumo_local"])
        self.assertIn("R$ 1.800,00", result["resumo_local"])

    def test_multi_currency_warning(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 27
        user = create_user("T9", "t9@example.com", "strong-password")
        with database.get_connection() as conn:
            conn.executemany(
                """
                INSERT INTO checking_accounts (
                    user_id, name, bank_name, account_type, currency,
                    initial_balance_cents, current_balance_cents
                ) VALUES (?, 'Conta', 'Banco', 'liquidity', ?, 0, 0)
                """,
                [
                    (user["id"], "BRL"),
                    (user["id"], "USD"),
                ],
            )

        result = calculate_trends(user["id"], "2026-07")
        self.assertIsNotNone(result["multi_currency_warning"])
        self.assertIn("BRL", result["multi_currency_warning"])
        self.assertIn("USD", result["multi_currency_warning"])
        self.assertTrue(result["resumo_local"].endswith(result["multi_currency_warning"]))




class TrendsRouteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-trends.db"
        initialize_database()

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def _handler(self, path: str, user: dict | None = None, body: dict | None = None) -> app.AppHandler:
        handler = object.__new__(app.AppHandler)
        handler.headers = {
            "Host": "sistema-financeiro.localhost:8020",
            "Origin": "http://sistema-financeiro.localhost:8020",
        }
        handler.path = path
        handler.send_json = mock.Mock()
        handler.read_json = mock.Mock(return_value=body or {})
        return handler

    def _context(self, user: dict | None = None):
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.object(app, "PORT", 8020))
        stack.enter_context(mock.patch.object(app, "PUBLIC_URL", "http://sistema-financeiro.localhost:8020"))
        if user is None:
            stack.enter_context(mock.patch.object(app.AppHandler, "get_cookie", return_value=None))
        else:
            stack.enter_context(mock.patch.object(app.AppHandler, "require_user", return_value=user))
        return stack

    def test_financial_health_trends_requires_session_user(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 28
        handler = self._handler("/api/financial-health-trends?month=2026-07")
        with self._context():
            with self.assertRaises(app.ApiError) as error:
                handler.handle_financial_health_trends()
        self.assertEqual(error.exception.status, HTTPStatus.UNAUTHORIZED)

    def test_financial_health_trends_returns_payload(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 1 e 3
        user = create_user("RouteUser", "route@example.com", "strong-password")
        handler = self._handler("/api/financial-health-trends?month=2026-07", user=user)
        with self._context(user):
            handler.handle_financial_health_trends()
        handler.send_json.assert_called_once()
        payload = handler.send_json.call_args[0][0]
        self.assertEqual(payload["month"], "2026-07")
        self.assertIn("serie_mensal", payload)
        self.assertIn("achados", payload)
        self.assertFalse(payload["ia_ativa"])

    def test_financial_health_trends_marks_ai_active_when_configured(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 12, 17 e 20
        user = create_user("RouteUserAI", "route-ai@example.com", "strong-password")
        from financeiro.secure_config import save_ai_settings
        save_ai_settings(user["id"], {
            "provider": "local",
            "enabled": True,
            "base_url": "http://localhost:1234/v1",
            "model": "llama",
            "auth_type": "none",
        })

        handler = self._handler("/api/financial-health-trends?month=2026-07", user=user)
        with self._context(user):
            handler.handle_financial_health_trends()

        payload = handler.send_json.call_args[0][0]
        self.assertTrue(payload["ia_ativa"])

    def test_ai_settings_requires_session_user(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 28
        handler = self._handler("/api/ai-settings")
        with self._context():
            with self.assertRaises(app.ApiError) as error:
                handler.handle_ai_settings_status()
        self.assertEqual(error.exception.status, HTTPStatus.UNAUTHORIZED)

    def test_ai_settings_save_and_return_status(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 17, 18, 19, 27 e 28
        user = create_user("RouteUser2", "route2@example.com", "strong-password")
        handler = self._handler(
            "/api/ai-settings",
            user=user,
            body={
                "provider": "local",
                "enabled": True,
                "base_url": "http://localhost:1234/v1",
                "model": "llama",
                "auth_type": "none",
                "timeout_seconds": 5,
                "temperature": 0.2,
                "max_tokens": 500,
            },
        )
        with self._context(user):
            handler.handle_save_ai_settings()
        status = handler.send_json.call_args[0][0]
        self.assertTrue(status["configured"])
        self.assertTrue(status["enabled"])
        self.assertEqual(status["provider"], "local")
        self.assertFalse(status["has_api_key"])
        # segredo nunca retornado
        self.assertNotIn("api_key", status)

        handler2 = self._handler("/api/ai-settings", user=user)
        with self._context(user):
            handler2.handle_ai_settings_status()
        status2 = handler2.send_json.call_args[0][0]
        self.assertEqual(status2["model"], "llama")
        self.assertFalse(status2["has_api_key"])

    def test_ai_settings_put_route_saves_with_valid_origin(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 17, 27 e 28
        user = create_user("RouteUserPut", "route-put@example.com", "strong-password")
        handler = self._handler(
            "/api/ai-settings",
            user=user,
            body={
                "provider": "local",
                "enabled": True,
                "base_url": "http://localhost:1234/v1",
                "model": "llama",
                "auth_type": "none",
            },
        )

        with self._context(user):
            handler.do_PUT()

        status = handler.send_json.call_args[0][0]
        self.assertTrue(status["configured"])
        self.assertTrue(status["enabled"])
        self.assertEqual(status["provider"], "local")

    def test_ai_summary_requires_session_user(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critério 28
        handler = self._handler("/api/financial-health-trends/ai-summary", body={"month": "2026-07"})
        with self._context():
            with self.assertRaises(app.ApiError) as error:
                handler.handle_ai_summary()
        self.assertEqual(error.exception.status, HTTPStatus.UNAUTHORIZED)

    def test_ai_summary_returns_fallback_when_ia_disabled(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 12 e 17
        user = create_user("RouteUser3", "route3@example.com", "strong-password")
        handler = self._handler("/api/financial-health-trends/ai-summary", user=user, body={"month": "2026-07"})
        with self._context(user):
            handler.handle_ai_summary()
        payload = handler.send_json.call_args[0][0]
        self.assertIsNone(payload["resumo_ia"])
        self.assertFalse(payload["ia_usada"])
        self.assertTrue(payload["resumo_local"])

    def test_ai_summary_uses_external_service_when_enabled(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 12, 14 e 16
        user = create_user("RouteUser4", "route4@example.com", "strong-password")
        from financeiro.secure_config import save_ai_settings
        save_ai_settings(user["id"], {
            "provider": "local",
            "enabled": True,
            "base_url": "http://localhost:1234/v1",
            "model": "llama",
            "auth_type": "none",
        })

        handler = self._handler("/api/financial-health-trends/ai-summary", user=user, body={"month": "2026-07"})
        fake_response = {"choices": [{"message": {"content": "Resumo reescrito pela IA."}}]}
        response_mock = mock.Mock()
        response_mock.__enter__ = mock.Mock(return_value=response_mock)
        response_mock.__exit__ = mock.Mock(return_value=False)
        response_mock.read.return_value = json.dumps(fake_response).encode("utf-8")

        with self._context(user):
            with mock.patch("financeiro.ai_summary.urlopen", return_value=response_mock) as urlopen_mock:
                handler.handle_ai_summary()
        payload = handler.send_json.call_args[0][0]
        self.assertEqual(payload["resumo_ia"], "Resumo reescrito pela IA.")
        self.assertTrue(payload["ia_usada"])
        # verifica que a URL segue o contrato OpenAI Chat Completions
        call = urlopen_mock.call_args
        self.assertIn("/chat/completions", call.args[0].full_url)

    def test_ai_summary_minimizes_payload_and_does_not_send_secret(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 14, 16, 21, 23 e 28
        user = create_user("RouteUser5", "route5@example.com", "strong-password")
        from financeiro.secure_config import save_ai_settings
        save_ai_settings(user["id"], {
            "provider": "custom",
            "enabled": True,
            "base_url": "http://localhost:1234/v1/",
            "model": "llama",
            "auth_type": "bearer",
            "api_key": "secret-key",
            "timeout_seconds": 3,
            "temperature": 0.1,
            "max_tokens": 321,
        })
        trends_payload = {
            "month": "2026-07",
            "confianca": "baixa",
            "resumo_local": "Resumo local.",
            "receitas_mes_cents": 100000,
            "despesas_mes_cents": 50000,
            "saldo_mes_cents": 50000,
            "serie_mensal": [{"month": "2026-07", "income_cents": 100000, "expense_cents": 50000}],
            "orcamento_realizado": [{"category_name": "Mercado", "realizado_cents": 50000}],
            "achados": [
                {"tipo": "despesa", "titulo": "Despesa", "descricao": "Subiu", "valor_cents": 50000},
                {"tipo": "limite", "titulo": "Mercado acima", "descricao": "Repetiria card", "valor_cents": 50000},
                {"tipo": "antecipacao_parcela", "titulo": "Antecipação", "descricao": "Repetiria card", "valor_cents": 20000},
            ],
            "eventos_pontuais": [{"tipo": "bonus", "descricao": "PLR", "valor_cents": 100000}],
            "assinaturas_e_servicos": [{"subcategory_name": "Streaming", "valor_cents": 20000}],
        }
        fake_response = {"choices": [{"message": {"content": "Resumo IA."}}]}
        response_mock = mock.Mock()
        response_mock.__enter__ = mock.Mock(return_value=response_mock)
        response_mock.__exit__ = mock.Mock(return_value=False)
        response_mock.read.return_value = json.dumps(fake_response).encode("utf-8")

        with mock.patch("financeiro.ai_summary.urlopen", return_value=response_mock) as urlopen_mock:
            summary = generate_ai_summary(user["id"], trends_payload)

        self.assertEqual(summary, "Resumo IA.")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "http://localhost:1234/v1/chat/completions")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.headers["Authorization"], "Bearer secret-key")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "llama")
        self.assertEqual(body["temperature"], 0.1)
        self.assertEqual(body["max_tokens"], 321)
        serialized_body = json.dumps(body, ensure_ascii=False)
        self.assertIn("síntese executiva integrada", SYSTEM_PROMPT)
        self.assertIn("2 a 4 frases", SYSTEM_PROMPT)
        self.assertIn("Resumo local.", serialized_body)
        self.assertIn("Subiu", serialized_body)
        self.assertIn("contexto_operacional", serialized_body)
        self.assertIn("limites_em_cards", serialized_body)
        self.assertNotIn("Repetiria card", serialized_body)
        self.assertNotIn("secret-key", serialized_body)
        self.assertNotIn("serie_mensal", serialized_body)
        self.assertNotIn("orcamento_realizado", serialized_body)

    def test_ai_summary_uses_gemini_generate_content_contract(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 12, 24 e 32
        user = create_user("GeminiUser", "gemini@example.com", "strong-password")
        from financeiro.secure_config import save_ai_settings
        save_ai_settings(user["id"], {
            "provider": "google",
            "enabled": True,
            "model": "gemini-1.5-flash",
            "api_key": "gemini-secret",
            "timeout_seconds": 3,
            "temperature": 0.1,
            "max_tokens": 321,
        })
        fake_response = {"candidates": [{"content": {"parts": [{"text": "Resumo Gemini."}]}}]}
        response_mock = mock.Mock()
        response_mock.__enter__ = mock.Mock(return_value=response_mock)
        response_mock.__exit__ = mock.Mock(return_value=False)
        response_mock.read.return_value = json.dumps(fake_response).encode("utf-8")

        with mock.patch("financeiro.ai_summary.urlopen", return_value=response_mock) as urlopen_mock:
            summary = generate_ai_summary(user["id"], {"month": "2026-07", "resumo_local": "Local"})

        self.assertEqual(summary, "Resumo Gemini.")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        )
        self.assertEqual(request.headers["X-goog-api-key"], "gemini-secret")
        body = json.loads(request.data.decode("utf-8"))
        self.assertIn("systemInstruction", body)
        self.assertIn("contents", body)
        self.assertEqual(body["generationConfig"]["maxOutputTokens"], 321)
        self.assertNotIn("gemini-secret", json.dumps(body, ensure_ascii=False))

    def test_ai_summary_accepts_gemini_model_with_models_prefix(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 12, 24 e 32
        user = create_user("GeminiPrefixedUser", "gemini-prefixed@example.com", "strong-password")
        from financeiro.secure_config import save_ai_settings
        save_ai_settings(user["id"], {
            "provider": "google",
            "enabled": True,
            "model": "models/gemini-1.5-flash",
            "api_key": "gemini-secret",
        })
        fake_response = {"candidates": [{"content": {"parts": [{"text": "Resumo Gemini."}]}}]}
        response_mock = mock.Mock()
        response_mock.__enter__ = mock.Mock(return_value=response_mock)
        response_mock.__exit__ = mock.Mock(return_value=False)
        response_mock.read.return_value = json.dumps(fake_response).encode("utf-8")

        with mock.patch("financeiro.ai_summary.urlopen", return_value=response_mock) as urlopen_mock:
            summary = generate_ai_summary(user["id"], {"month": "2026-07", "resumo_local": "Local"})

        self.assertEqual(summary, "Resumo Gemini.")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(
            request.full_url,
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
        )

    def test_ai_summary_uses_anthropic_messages_contract(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 12, 24 e 32
        user = create_user("ClaudeUser", "claude@example.com", "strong-password")
        from financeiro.secure_config import save_ai_settings
        save_ai_settings(user["id"], {
            "provider": "anthropic",
            "enabled": True,
            "model": "claude-3-5-haiku-latest",
            "api_key": "anthropic-secret",
            "timeout_seconds": 3,
            "temperature": 0.1,
            "max_tokens": 321,
        })
        fake_response = {"content": [{"type": "text", "text": "Resumo Claude."}]}
        response_mock = mock.Mock()
        response_mock.__enter__ = mock.Mock(return_value=response_mock)
        response_mock.__exit__ = mock.Mock(return_value=False)
        response_mock.read.return_value = json.dumps(fake_response).encode("utf-8")

        with mock.patch("financeiro.ai_summary.urlopen", return_value=response_mock) as urlopen_mock:
            summary = generate_ai_summary(user["id"], {"month": "2026-07", "resumo_local": "Local"})

        self.assertEqual(summary, "Resumo Claude.")
        request = urlopen_mock.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.anthropic.com/v1/messages")
        self.assertEqual(request.headers["X-api-key"], "anthropic-secret")
        self.assertEqual(request.headers["Anthropic-version"], "2023-06-01")
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["model"], "claude-3-5-haiku-latest")
        self.assertEqual(body["max_tokens"], 321)
        self.assertIn("system", body)
        self.assertIn("messages", body)
        self.assertNotIn("anthropic-secret", json.dumps(body, ensure_ascii=False))

    def test_ai_summary_returns_none_on_provider_failure(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 16 e 26
        user = create_user("RouteUser6", "route6@example.com", "strong-password")
        from financeiro.secure_config import save_ai_settings
        save_ai_settings(user["id"], {
            "provider": "local",
            "enabled": True,
            "base_url": "http://localhost:1234/v1",
            "model": "llama",
            "auth_type": "none",
        })
        with mock.patch("financeiro.ai_summary.urlopen", side_effect=URLError("offline")):
            summary = generate_ai_summary(user["id"], {"month": "2026-07", "resumo_local": "Local"})
        self.assertIsNone(summary)

    def test_minimized_ai_payload_keeps_only_narrative_findings(self) -> None:
        # spec: tendencias-saude-financeira v2.21 — critérios 14, 21 e 23
        payload = {
            "month": "2026-07",
            "confianca": "intermediaria",
            "resumo_local": "Resumo local.",
            "achados": [
                {"tipo": "despesa", "titulo": "Despesas", "descricao": "D0", "valor_cents": 1},
                {"tipo": "receita", "titulo": "Receitas", "descricao": "D1", "valor_cents": 1},
                {"tipo": "oportunidade_caixa", "titulo": "Caixa", "descricao": "D2", "valor_cents": 1},
                {"tipo": "limite", "titulo": "Limite", "descricao": "Nao enviar", "valor_cents": 1},
                {"tipo": "evento_pontual", "titulo": "Evento", "descricao": "Nao enviar", "valor_cents": 1},
                {"tipo": "antecipacao_parcela", "titulo": "Antecipação", "descricao": "Nao enviar", "valor_cents": 1},
            ],
            "eventos_pontuais": [
                {"tipo": f"e{i}", "descricao": f"E{i}", "valor_cents": i}
                for i in range(7)
            ],
            "antecipacao_parcelas": [{"valor_cents": 5000}, {"valor_cents": 7000}],
            "assinaturas_e_servicos": [{"subcategory_name": "Streaming", "valor_cents": 1000}],
            "segredo": "nao enviar",
        }
        minimized = minimize_trends_payload(payload)
        self.assertEqual([item["tipo"] for item in minimized["achados"]], ["despesa", "receita", "oportunidade_caixa"])
        self.assertEqual(minimized["contexto_operacional"]["limites_em_cards"], 1)
        self.assertEqual(minimized["contexto_operacional"]["eventos_pontuais_em_cards"], 1)
        self.assertEqual(minimized["contexto_operacional"]["antecipacoes_em_cards"], 1)
        self.assertEqual(minimized["contexto_operacional"]["quantidade_antecipacoes"], 2)
        self.assertEqual(minimized["contexto_operacional"]["total_antecipado_cents"], 12000)
        self.assertNotIn("eventos_pontuais", minimized)
        self.assertNotIn("segredo", minimized)
        self.assertNotIn("valor_cents", minimized["achados"][0])
        self.assertNotIn("Nao enviar", json.dumps(minimized, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
