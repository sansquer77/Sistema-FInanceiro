from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.categories import create_category, create_subcategory
from financeiro.credit_cards import create_credit_card
from financeiro.spending_limits import create_spending_limit, list_spending_limits_with_consumption


class SpendingLimitConsumptionTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.old_paths = database.DATA_DIR, database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test.db"
        database.initialize_database()
        self.user = create_user("Alice", "alice@example.com", "correct-password")
        self.account = create_checking_account(self.user["id"], {
            "name": "Conta", "bank_name": "Banco", "currency": "BRL", "initial_balance": "0,00",
        })
        self.card = create_credit_card(self.user["id"], {
            "name": "Cartão", "issuer": "Banco", "currency": "BRL", "limit": "5000,00",
            "closing_day": "20", "due_day": "10",
        })
        self.category = create_category(self.user["id"], "Despesa de teste do limite", "expense")
        self.subcategory = create_subcategory(self.user["id"], self.category["id"], "Subcategoria de teste")
        create_spending_limit(self.user["id"], {
            "month": "2026-07", "category_id": self.category["id"], "limit_amount": "1000,00",
        })
        create_spending_limit(self.user["id"], {
            "month": "2026-07", "category_id": self.category["id"],
            "subcategory_id": self.subcategory["id"], "limit_amount": "500,00",
        })

    def tearDown(self) -> None:
        database.DATA_DIR, database.DB_PATH = self.old_paths
        self.tempdir.cleanup()

    def test_consumption_is_aggregated_for_requested_competence(self) -> None:
        with database.get_connection() as conn:
            conn.execute(
                """INSERT INTO transactions
                   (user_id, type, description, amount_cents, amount_brl_cents, date, account_id, category_id, subcategory_id)
                   VALUES (?, 'expense', 'Mercado julho', 10000, 10000, '2026-07-10', ?, ?, ?)""",
                (self.user["id"], self.account["id"], self.category["id"], self.subcategory["id"]),
            )
            conn.execute(
                """INSERT INTO transactions
                   (user_id, type, description, amount_cents, amount_brl_cents, date, account_id, category_id, subcategory_id)
                   VALUES (?, 'expense', 'Mercado agosto', 20000, 20000, '2026-08-10', ?, ?, ?)""",
                (self.user["id"], self.account["id"], self.category["id"], self.subcategory["id"]),
            )
            conn.execute(
                """INSERT INTO credit_card_transactions
                   (user_id, credit_card_id, type, description, amount_cents, amount_brl_cents, date, invoice_month, category_id, subcategory_id)
                   VALUES (?, ?, 'expense', 'Cartão agosto', 30000, 30000, '2026-07-25', '2026-08', ?, ?)""",
                (self.user["id"], self.card["id"], self.category["id"], self.subcategory["id"]),
            )

        july = list_spending_limits_with_consumption(self.user["id"], "2026-07")
        august = list_spending_limits_with_consumption(self.user["id"], "2026-08")
        self.assertEqual({row["subcategory_id"]: row["spent_amount_cents"] for row in july}, {None: 10000, self.subcategory["id"]: 10000})
        self.assertEqual({row["subcategory_id"]: row["spent_amount_cents"] for row in august}, {None: 50000, self.subcategory["id"]: 50000})

    def test_payment_transaction_is_excluded_from_consumption(self) -> None:
        with database.get_connection() as conn:
            transaction_id = conn.execute(
                """INSERT INTO transactions
                   (user_id, type, description, amount_cents, amount_brl_cents, date, account_id, category_id)
                   VALUES (?, 'expense', 'Pagamento da fatura', 70000, 70000, '2026-08-10', ?, ?)""",
                (self.user["id"], self.account["id"], self.category["id"]),
            ).lastrowid
            conn.execute(
                """INSERT INTO credit_card_payments
                   (user_id, credit_card_id, invoice_month, account_id, transaction_id, payment_date, amount_cents)
                   VALUES (?, ?, '2026-08', ?, ?, '2026-08-10', 70000)""",
                (self.user["id"], self.card["id"], self.account["id"], transaction_id),
            )

        rows = list_spending_limits_with_consumption(self.user["id"], "2026-08")
        self.assertTrue(all(row["spent_amount_cents"] == 0 for row in rows))
