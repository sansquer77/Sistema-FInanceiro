from __future__ import annotations

import unittest

from app import cockpit_payload


class CockpitPayloadTest(unittest.TestCase):
    def test_credit_card_payment_transaction_is_excluded_from_expense_totals(self) -> None:
        payload = cockpit_payload([
            {
                "type": "expense",
                "amount": 100,
                "amount_brl": 100,
                "category_name": "Serviços Financeiros e Impostos",
                "subcategory_name": "Pagamento de Fatura de Cartão",
                "is_credit_card_payment": True,
            },
            {
                "type": "expense",
                "amount": 100,
                "amount_brl": 100,
                "category_name": "Transporte",
                "subcategory_name": "Lavagem e cuidados com o carro",
            },
        ])

        self.assertEqual(payload["month_totals"]["expense"], 100)
        self.assertEqual(payload["top_expenses"], [
            {
                "label": "Transporte / Lavagem e cuidados com o carro",
                "total": 100.0,
                "count": 1,
            },
        ])

    def test_paid_invoice_month_keeps_card_transactions_in_analytics(self) -> None:
        payload = cockpit_payload([
            {
                "type": "expense",
                "amount": 500,
                "amount_brl": 500,
                "category_name": "Serviços Financeiros",
                "subcategory_name": "Pagamento de Fatura",
                "is_credit_card_payment": True,
            },
            {
                "type": "expense",
                "amount": 350,
                "amount_brl": 350,
                "card_currency": "BRL",
                "invoice_month": "2026-07",
                "category_name": "Transporte",
                "subcategory_name": "Estacionamento",
            },
            {
                "type": "expense",
                "amount": 150,
                "amount_brl": 150,
                "card_currency": "BRL",
                "invoice_month": "2026-07",
                "category_name": "Assinaturas e Serviços",
                "subcategory_name": "Armazenamento em Nuvem e Softwares",
            },
        ])

        self.assertEqual(payload["month_totals"]["expense"], 500)
        self.assertEqual(
            [row["label"] for row in payload["top_expenses"]],
            [
                "Transporte / Estacionamento",
                "Assinaturas e Serviços / Armazenamento em Nuvem e Softwares",
            ],
        )

    def test_planning_keeps_original_values_separated_by_currency(self) -> None:
        payload = cockpit_payload([
            {
                "type": "expense",
                "amount": 100,
                "amount_brl": 550,
                "account_currency": "USD",
                "category_name": "Impostos",
                "subcategory_name": "Imposto EUA",
                "series_kind": "recurring",
            },
            {
                "type": "expense",
                "amount": 100,
                "amount_brl": 100,
                "account_currency": "BRL",
                "category_name": "Impostos",
                "subcategory_name": "Imposto EUA",
                "series_kind": "recurring",
            },
        ])

        self.assertEqual(payload["month_totals"]["expense"], 650)
        self.assertEqual(payload["planning"]["expense"], [
            {
                "label": "Impostos / Imposto EUA",
                "total": 100.0,
                "count": 1,
                "currency": "BRL",
            },
            {
                "label": "Impostos / Imposto EUA",
                "total": 100.0,
                "count": 1,
                "currency": "USD",
            },
        ])


if __name__ == "__main__":
    unittest.main()
