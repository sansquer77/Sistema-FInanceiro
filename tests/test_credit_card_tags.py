from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from financeiro import database
from financeiro.auth import create_user
from financeiro.credit_cards import (
    create_credit_card,
    create_credit_card_transaction,
    list_credit_card_invoice,
    update_credit_card_transaction,
)
from financeiro.database import initialize_database


class CreditCardTransactionTagsTest(unittest.TestCase):
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

    def test_credit_card_transaction_tags_are_created_listed_and_updated(self) -> None:
        user = create_user("Alice", "alice@example.com", "correct-password")
        card = create_credit_card(user["id"], {
            "name": "Cartao",
            "issuer": "Banco",
            "currency": "BRL",
            "limit": "2000,00",
            "closing_day": "28",
            "due_day": "10",
        })
        transaction = create_credit_card_transaction(user["id"], {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Mercado",
            "amount": "150,00",
            "date": "2026-07-10",
            "invoice_month": "2026-07",
            "category": "Alimentacao",
            "tags": "Casa, Essencial",
        })

        invoice = list_credit_card_invoice(user["id"], card["id"], transaction["invoice_month"])
        listed = invoice["transactions"][0]

        self.assertEqual(listed["tags"], ["Casa", "Essencial"])
        self.assertEqual(listed["tag_name"], "Casa, Essencial")

        updated = update_credit_card_transaction(user["id"], str(transaction["id"]), {
            "credit_card_id": str(card["id"]),
            "type": "expense",
            "description": "Mercado atualizado",
            "amount": "160,00",
            "date": "2026-07-10",
            "invoice_month": "2026-07",
            "category": "Alimentacao",
            "tags": "Recorrente",
        })

        self.assertEqual(updated["tags"], ["Recorrente"])


if __name__ == "__main__":
    unittest.main()
