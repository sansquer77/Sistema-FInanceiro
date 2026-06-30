from __future__ import annotations

import unittest

from financeiro.portfolio import build_positions, format_position


class PortfolioCostTest(unittest.TestCase):
    def test_variable_income_cost_uses_invested_amount_without_adding_fees_twice(self) -> None:
        positions = build_positions([
            {
                "id": 1,
                "source_type": "operation",
                "source_id": 1,
                "transaction_id": 10,
                "account_id": 1,
                "account_name": "Corretora",
                "account_currency": "USD",
                "asset_type": "stock",
                "asset_identifier": "ABC",
                "asset_name": "ABC Corp",
                "cnpj": None,
                "quantity_micros": 3_000_000,
                "unit_price_cents": 595,
                "invested_amount_cents": 2035,
                "brokerage_fee_cents": 250,
                "exchange_fee_cents": 0,
                "tax_cents": 0,
                "other_costs_cents": 0,
                "fixed_income_mode": None,
                "fixed_income_indexer": None,
                "fixed_income_rate_micros": 0,
                "fixed_income_maturity_date": None,
                "apply_tax_estimate": 1,
                "savings_anniversaries_json": None,
                "date": "2026-06-30",
                "description": "Compra ABC",
                "amount_cents": 2035,
                "exchange_rate_micros": 1_000_000,
                "redeemed_cost_cents": 0,
                "redeemed_quantity_micros": 0,
            },
        ])

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["total_cost_cents"], 2035)

        formatted = format_position(positions[0])
        self.assertEqual(formatted["total_cost"], "20.35")
        self.assertEqual(formatted["average_price"], "6.78")


if __name__ == "__main__":
    unittest.main()
