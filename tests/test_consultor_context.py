import copy
import unittest
from unittest.mock import patch

from financeiro import consultor, consultor_context as context


class ConsultorContextTest(unittest.TestCase):
    def test_public_builders_remain_available_from_facade(self):
        for name in vars(context):
            if name.startswith("build_"):
                self.assertIs(getattr(consultor, name), getattr(context, name))

    def test_compaction_limits_rows_without_mutating_or_exposing_identifiers(self):
        positions = [
            {"id": i, "name": "Private", "ticker": "SECRET",
             "current_value_brl_cents": i * 101, "currency": "BRL"}
            for i in range(15)
        ]
        original = copy.deepcopy(positions)
        summary = context.summarize_portfolio(positions)
        self.assertEqual(summary["total_brl_cents"], 10605)
        self.assertEqual(summary["position_count"], 15)
        self.assertEqual(len(summary["positions"]), 12)
        self.assertEqual(summary["positions"][0]["current_value_brl_cents"], 1414)
        for row in summary["positions"]:
            self.assertTrue({"id", "name", "ticker"}.isdisjoint(row))
        self.assertEqual(positions, original)

    def test_supplied_empty_positions_are_not_reloaded(self):
        with patch("financeiro.portfolio.current_portfolio_positions") as loader:
            result = context.build_currency_exposure_context(7, portfolio_positions=[])
        loader.assert_not_called()
        self.assertEqual(result["portfolio"]["total_brl_cents"], 0)

    def test_evolution_loads_positions_once_and_reuses_same_snapshot(self):
        positions = [{"current_value_brl_cents": 100}]
        score = {"month": "2026-08", "score_total": 50}
        with patch("financeiro.portfolio.current_portfolio_positions", return_value=positions) as loader:
            with patch("financeiro.financial_health.calculate_financial_health_score", return_value=score) as calculate:
                result = context.build_score_evolution_context(7, period_window="12m")
        loader.assert_called_once_with(7, force_refresh=False)
        self.assertEqual(len(result["series"]), 12)
        self.assertEqual(calculate.call_count, 13)
        for call in calculate.call_args_list:
            self.assertEqual(call.args[0], 7)
            self.assertIs(call.kwargs["portfolio_positions"], positions)

    def test_money_display_enrichment_is_recursive_and_non_mutating(self):
        payload = {"items": [{"amount_cents": -12345}], "total_cents": 0}
        original = copy.deepcopy(payload)
        enriched = context.add_money_displays(payload)
        self.assertEqual(enriched["items"][0]["amount_display"], "R$ -123,45")
        self.assertEqual(enriched["total_display"], "R$ 0,00")
        self.assertEqual(payload, original)


if __name__ == "__main__":
    unittest.main()
