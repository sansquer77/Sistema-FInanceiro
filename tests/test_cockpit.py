from __future__ import annotations

import unittest

from app import cockpit_payload


class CockpitPayloadTest(unittest.TestCase):
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
