from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.categories import create_category, get_category_evolution
from financeiro.credit_cards import (
    create_credit_card,
    create_credit_card_transaction,
    set_credit_card_transaction_reconciled,
)
from financeiro.database import initialize_database
from financeiro.cockpit import build_cockpit_summary
from financeiro.reports import _tag_report_query, build_report_overview, build_tag_report
from financeiro.transactions import create_transaction, set_transaction_reconciled


class TagReportTest(unittest.TestCase):
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

    def test_tag_report_groups_income_expense_balance_and_investment(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        category = create_category(user["id"], "Salário", "income")
        create_transaction(user["id"], {
            "type": "income",
            "description": "Salário",
            "amount": "3000,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Salário",
            "tags": "Camila",
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Compra",
            "amount": "1500,00",
            "date": "2026-01-15",
            "account_id": str(account["id"]),
            "category": "Compras",
            "tags": "Camila",
        })

        response = build_tag_report(user["id"], "2026-01")

        self.assertEqual(len(response["tags"]), 1)
        tag = response["tags"][0]
        self.assertEqual(tag["tag"], "Camila")
        self.assertEqual(tag["income_cents"], 300000)
        self.assertEqual(tag["expense_cents"], 150000)
        self.assertEqual(tag["balance_cents"], 150000)
        self.assertEqual(tag["investment_cents"], 0)
        self.assertEqual(tag["count"], 2)

    def test_tag_report_does_not_materialize_detailed_list_helpers(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta", "bank_name": "Banco", "currency": "BRL", "initial_balance": "0,00",
        })
        create_transaction(user["id"], {
            "type": "expense", "description": "Compra", "amount": "10,00", "date": "2026-01-10",
            "account_id": str(account["id"]), "category": "Compras", "tags": "Casa",
        })

        with (
            mock.patch("financeiro.reports.list_transactions", side_effect=AssertionError("lista detalhada")),
            mock.patch("financeiro.reports.list_credit_card_transactions", side_effect=AssertionError("lista detalhada")),
        ):
            response = build_tag_report(user["id"], "2026-01")

        self.assertEqual(response["tags"][0]["expense_cents"], 1000)

    def test_tag_report_month_query_uses_temporal_indexes_without_optional_or(self) -> None:
        sql, params = _tag_report_query(1, "2026-01", "2026-01-01", "2026-01-31")

        self.assertNotIn("IS NULL OR", sql)
        self.assertIn("transactions.date BETWEEN ? AND ?", sql)
        self.assertIn("credit_card_transactions.invoice_month = ?", sql)
        with database.get_connection() as conn:
            plan = "\n".join(row["detail"] for row in conn.execute(f"EXPLAIN QUERY PLAN {sql}", params))
        self.assertIn("idx_transactions_user_date", plan)
        self.assertIn("idx_credit_card_transactions_user_invoice_date", plan)

    def test_cockpit_summary_aggregates_month_without_detailed_lists(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta", "bank_name": "Banco", "currency": "BRL", "initial_balance": "0,00",
        })
        create_transaction(user["id"], {
            "type": "income", "description": "Salário", "amount": "1000,00", "date": "2026-01-05",
            "account_id": str(account["id"]), "category": "Receitas",
        })
        create_transaction(user["id"], {
            "type": "expense", "description": "Aluguel", "amount": "400,00", "date": "2026-01-10",
            "account_id": str(account["id"]), "category": "Moradia", "series_kind": "recurring",
            "recurrence_frequency": "monthly",
        })

        response = build_cockpit_summary(user["id"], "2026-01")

        self.assertEqual(response["month_totals"]["income"], 1000.0)
        self.assertEqual(response["month_totals"]["expense"], 400.0)
        self.assertEqual(response["top_expenses"][0]["label"], "Moradia")
        self.assertEqual(response["planning"]["expense"][0]["total"], 400.0)

        overview = build_report_overview(user["id"], "2026-01")
        self.assertEqual(overview["totals_by_type"]["income"]["BRL"], 100000)
        self.assertEqual(overview["totals_by_type"]["expense"]["BRL"], 40000)
        self.assertEqual(overview["count"], 2)

    def test_tag_report_separates_currencies(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        brl_account = create_checking_account(user["id"], {
            "name": "Conta BRL",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        usd_account = create_checking_account(user["id"], {
            "name": "Conta USD",
            "bank_name": "Banco",
            "currency": "USD",
            "initial_balance": "0,00",
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Despesa BRL",
            "amount": "1000,00",
            "date": "2026-01-10",
            "account_id": str(brl_account["id"]),
            "category": "Compras",
            "tags": "Viagem",
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Despesa USD",
            "amount": "500,00",
            "date": "2026-01-10",
            "account_id": str(usd_account["id"]),
            "category": "Compras",
            "tags": "Viagem",
            "exchange_rate": "5,00",
        })

        response = build_tag_report(user["id"], "2026-01")

        tag = response["tags"][0]
        self.assertEqual(tag["expense_by_currency"]["BRL"], 100000)
        self.assertEqual(tag["expense_by_currency"]["USD"], 50000)
        self.assertEqual(tag["balance_cents"], -150000)

    def test_tag_report_includes_card_transactions_by_invoice_month(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        card = create_credit_card(user["id"], {
            "name": "Cartao principal",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "5000,00",
            "closing_day": "25",
            "due_day": "10",
            "preferred_payment_account_id": str(account["id"]),
        })
        card_transaction = create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Consulta médica",
            "amount": "300,00",
            "date": "2026-01-05",
            "invoice_month": "2026-01",
            "category": "Saúde",
            "tags": "Camila",
        })
        set_credit_card_transaction_reconciled(user["id"], str(card_transaction["id"]), True)

        response = build_tag_report(user["id"], "2026-01")

        self.assertEqual(len(response["tags"]), 1)
        tag = response["tags"][0]
        self.assertEqual(tag["tag"], "Camila")
        self.assertEqual(tag["expense_cents"], 30000)
        self.assertEqual(tag["count"], 1)

    def test_tag_report_excludes_credit_card_payments_and_transfers(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        origin = create_checking_account(user["id"], {
            "name": "Origem",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "1000,00",
        })
        destination = create_checking_account(user["id"], {
            "name": "Destino",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        create_transaction(user["id"], {
            "type": "transfer",
            "description": "Transferência",
            "amount": "200,00",
            "date": "2026-01-05",
            "account_id": str(origin["id"]),
            "destination_account_id": str(destination["id"]),
            "tags": "Camila",
        })

        response = build_tag_report(user["id"], "2026-01")

        self.assertEqual(len(response["tags"]), 0)

    def test_tag_report_counts_multiple_tags_per_transaction(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta principal",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Compra",
            "amount": "1000,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": "Compras",
            "tags": "Casa, Reforma",
        })

        response = build_tag_report(user["id"], "2026-01")

        self.assertEqual(len(response["tags"]), 2)
        tags = {row["tag"]: row for row in response["tags"]}
        self.assertEqual(tags["Casa"]["expense_cents"], 100000)
        self.assertEqual(tags["Reforma"]["expense_cents"], 100000)


class CategoryEvolutionReportTest(unittest.TestCase):
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

    def test_null_subcategory_uses_invoice_month_and_normalized_brl_amounts(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Conta BRL",
            "bank_name": "Banco",
            "currency": "BRL",
            "initial_balance": "0,00",
        })
        usd_account = create_checking_account(user["id"], {
            "name": "Conta USD",
            "bank_name": "Banco",
            "currency": "USD",
            "initial_balance": "0,00",
        })
        card = create_credit_card(user["id"], {
            "name": "Cartao USD",
            "issuer": "Banco",
            "currency": "USD",
            "limit": "5000,00",
            "closing_day": "25",
            "due_day": "10",
            "preferred_payment_account_id": str(usd_account["id"]),
        })
        category = create_category(user["id"], "Cuidados de Teste", "expense")
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Sem subcategoria",
            "amount": "100,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": category["name"],
        })
        create_transaction(user["id"], {
            "type": "expense",
            "description": "Com subcategoria",
            "amount": "900,00",
            "date": "2026-01-10",
            "account_id": str(account["id"]),
            "category": category["name"],
            "subcategory": "Vestuário",
        })
        create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Compra em dólar",
            "amount": "10,00",
            "exchange_rate": "5,00",
            "date": "2026-01-12",
            "invoice_month": "2026-01",
            "category": category["name"],
        })

        evolution = get_category_evolution(user["id"], category["id"], "null", "all")

        self.assertEqual(evolution, [{"month": "2026-01", "total_cents": 15000}])


if __name__ == "__main__":
    unittest.main()
