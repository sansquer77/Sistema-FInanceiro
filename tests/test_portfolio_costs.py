from __future__ import annotations

import json
import unittest

from financeiro.portfolio import build_positions, fixed_income_custody_fee_cents, format_position, group_positions


class PortfolioCostTest(unittest.TestCase):
    def savings_row(self, redeemed_cost_cents: int = 0) -> dict:
        return {
            "id": 1,
            "source_type": "operation",
            "source_id": 1,
            "transaction_id": 10,
            "account_id": 1,
            "account_name": "Carteira",
            "account_currency": "BRL",
            "asset_type": "savings",
            "asset_identifier": "POUPANCA",
            "asset_name": "Poupança",
            "cnpj": None,
            "quantity_micros": 0,
            "unit_price_cents": 0,
            "invested_amount_cents": 30_000,
            "brokerage_fee_cents": 0,
            "exchange_fee_cents": 0,
            "tax_cents": 0,
            "other_costs_cents": 0,
            "fixed_income_mode": None,
            "fixed_income_indexer": None,
            "fixed_income_rate_micros": 0,
            "fixed_income_maturity_date": None,
            "apply_tax_estimate": 0,
            "emergency_reserve_eligible": 0,
            "savings_anniversaries_json": json.dumps([
                {"date": "2026-01-05", "amount_cents": 10_000},
                {"date": "2026-02-05", "amount_cents": 20_000},
            ]),
            "date": "2026-01-05",
            "description": "Aporte Poupança",
            "amount_cents": 30_000,
            "exchange_rate_micros": 1_000_000,
            "redeemed_cost_cents": redeemed_cost_cents,
            "redeemed_quantity_micros": 0,
        }

    def test_savings_redemption_consumes_anniversaries_fifo(self) -> None:
        positions = build_positions([self.savings_row(redeemed_cost_cents=15_000)])

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]["total_cost_cents"], 15_000)
        self.assertEqual(positions[0]["savings_anniversaries"], [
            {"date": "2026-02-05", "amount_cents": 15_000},
        ])

    def test_savings_full_redemption_removes_open_position(self) -> None:
        positions = build_positions([self.savings_row(redeemed_cost_cents=30_000)])

        self.assertEqual(positions, [])

    def test_treasury_direct_custody_fee_is_estimated_with_selic_exemption(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.7 — critério 25
        prefixado = {
            "asset_identifier": "Tesouro Prefixado",
            "asset_name": "TESOURO PREFIXADO 2027",
        }
        selic = {
            "asset_identifier": "Tesouro Selic",
            "asset_name": "TESOURO SELIC 2029",
        }
        renda_mais = {
            "asset_identifier": "Tesouro RendA+",
            "asset_name": "TESOURO RENDA+ 2045",
        }

        self.assertEqual(fixed_income_custody_fee_cents(prefixado, 1_000_000, 365), 2000)
        self.assertEqual(fixed_income_custody_fee_cents(selic, 1_200_000, 365), 400)
        self.assertEqual(fixed_income_custody_fee_cents(renda_mais, 1_200_000, 365), 0)

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

    def test_group_rows_keep_display_currency_and_expose_brl_chart_value(self) -> None:
        rows = group_positions([
            {
                "asset_type_label": "Renda variável",
                "fixed_income_indexer": "",
                "currency": "USD",
                "account_name": "Exterior",
                "total_cost_cents": 9000,
                "current_value_cents": 10000,
                "day_result_cents": 100,
                "total_cost_brl_cents": 45000,
                "current_value_brl_cents": 50000,
                "day_result_brl_cents": 500,
            },
            {
                "asset_type_label": "Renda variável",
                "fixed_income_indexer": "",
                "currency": "USD",
                "account_name": "Exterior",
                "total_cost_cents": 1000,
                "current_value_cents": 2000,
                "day_result_cents": 20,
                "total_cost_brl_cents": 5000,
                "current_value_brl_cents": 10000,
                "day_result_brl_cents": 100,
            },
        ], "asset_type_label")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["currency"], "USD")
        self.assertEqual(rows[0]["current_brl"], "120.00")
        self.assertEqual(rows[0]["chart_current_brl"], "600.00")


if __name__ == "__main__":
    unittest.main()
