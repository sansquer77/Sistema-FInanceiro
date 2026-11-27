import copy
import json
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
        compacted = context.compact_positions(positions)
        self.assertEqual(len(compacted), 6)
        self.assertEqual(compacted[0]["current_value_brl_cents"], 1414)
        for row in compacted:
            self.assertTrue({"id", "name", "ticker"}.isdisjoint(row))
        self.assertEqual(positions, original)

    def test_summarize_portfolio_returns_aggregates_without_individual_positions(self):
        positions = [
            {"current_value_brl_cents": 1000, "asset_type_label": "Renda Fixa", "currency": "BRL"},
            {"current_value_brl_cents": 2000, "asset_type_label": "Renda Variavel", "currency": "BRL"},
        ]
        summary = context.summarize_portfolio(positions)
        self.assertEqual(summary["total_brl_cents"], 3000)
        self.assertEqual(summary["position_count"], 2)
        self.assertIn("by_asset_type", summary)
        self.assertNotIn("positions", summary)

    def test_compact_portfolio_groups_keep_display_values_and_omitted_totals(self):
        rows = [
            {
                "label": f"Classe {index}",
                "current_value_brl_cents": (index + 1) * 1000,
                "current_value_brl": (index + 1) * 10.0,
                "current_value_display": f"R$ {(index + 1) * 10},00",
                "position_count": index + 1,
            }
            for index in range(14)
        ]

        compacted = context.compact_portfolio_group_rows(
            rows, label_prefix="Outras classes", limit=12
        )

        self.assertEqual(len(compacted), 13)
        self.assertEqual(compacted[-1]["label"], "Outras classes omitidas")
        self.assertEqual(compacted[-1]["current_value_display"], "R$ 270,00")
        self.assertEqual(compacted[-1]["position_count"], 27)
        self.assertEqual(compacted[-1]["omitted_group_count"], 2)
        self.assertNotIn("current_value_brl_cents", compacted[0])
        self.assertNotIn("current_value_brl", compacted[0])

    def test_compact_portfolio_context_has_no_individual_position_or_float_duplicates(self):
        compacted = context.compact_portfolio_context({
            "analysis_id": "analise_carteira",
            "investor_profile": "Moderado",
            "complementary_profile": {},
            "portfolio": {
                "total_brl_cents": 300000,
                "total_brl": 3000.0,
                "total_display": "R$ 3.000,00",
                "position_count": 2,
                "positions": [{"ticker": "NAO ENVIAR"}],
                "by_asset_type": [{
                    "label": "Renda Fixa",
                    "current_value_brl_cents": 300000,
                    "current_value_brl": 3000.0,
                    "current_value_brl_display": "R$ 3.000,00",
                    "position_count": 2,
                }],
            },
            "allocation_goals": [],
            "financial_commitments": {"goals": {"count": 0}, "loans_by_currency": []},
            "by_currency": [],
            "by_market": [],
            "score": {"month": "2026-08", "reserve_months": 1.0},
            "market_data": {"observed_sources": []},
        })

        self.assertNotIn("positions", compacted["portfolio"])
        self.assertNotIn("total_brl_cents", compacted["portfolio"])
        self.assertNotIn("total_brl", compacted["portfolio"])
        self.assertEqual(
            compacted["portfolio"]["by_asset_type"][0]["current_value_display"],
            "R$ 3.000,00",
        )

    def test_compact_portfolio_context_stays_within_local_payload_budget(self):
        groups = [
            {
                "label": f"Classe {index}",
                "current_value_brl_cents": 100000 + index,
                "current_value_brl": 1000.0 + index / 100,
                "current_value_brl_display": f"R$ {1000 + index / 100:,.2f}",
                "position_count": 1,
            }
            for index in range(80)
        ]
        compacted = context.compact_portfolio_context({
            "analysis_id": "analise_carteira",
            "investor_profile": "Moderado",
            "complementary_profile": {},
            "portfolio": {
                "total_brl_cents": 8000000,
                "total_display": "R$ 80.000,00",
                "position_count": 80,
                "by_asset_type": groups,
            },
            "allocation_goals": [],
            "financial_commitments": {"goals": {"count": 0}, "loans_by_currency": []},
            "by_currency": groups,
            "by_market": groups,
            "score": {"month": "2026-08", "reserve_months": 1.0},
            "market_data": {"observed_sources": ["Yahoo Finance"]},
        })

        payload_chars = len(json.dumps(compacted, ensure_ascii=False, sort_keys=True))
        self.assertLessEqual(payload_chars, 8000)
        self.assertEqual(len(compacted["portfolio"]["by_asset_type"]), 13)
        self.assertEqual(compacted["portfolio"]["by_asset_type"][-1]["omitted_group_count"], 68)

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

    def test_compact_budget_alerts_accepts_trends_field_names(self):
        rows = context.compact_budget_alerts([{
            "category_name": "Restaurantes",
            "limite_cents": 100000,
            "realizado_cents": 120000,
            "percentual_usado": 120,
        }])
        self.assertEqual(rows[0]["limit_cents"], 100000)
        self.assertEqual(rows[0]["actual_cents"], 120000)
        self.assertEqual(rows[0]["usage_pct"], 120)

    def test_invalid_money_display_logs_only_field_path_and_type(self):
        payload = {"portfolio": {"value_cents": {"invalid": "private"}}}
        with patch.object(context.LOGGER, "warning") as warning:
            with self.assertRaises(TypeError):
                context.add_money_displays(payload)

        warning.assert_called_once_with(
            "consultor invalid monetary context field path=%s value_type=%s",
            "$.portfolio.value_cents",
            "dict",
        )
        self.assertNotIn("private", str(warning.call_args))

    def test_financial_commitment_asset_type_list_is_not_treated_as_money(self):
        with patch("financeiro.financial_goals.list_financial_goals", return_value=[]), \
                patch("financeiro.loans.list_loans", return_value=[]):
            commitments = context.build_financial_commitments_context(7, [], goals=[])

        goals = commitments["goals"]
        self.assertEqual(goals["linked_investments_by_asset_type"], [])
        self.assertNotIn("linked_investments_by_asset_type_brl_cents", goals)
        enriched = context.add_money_displays({
            "financial_commitments": {
                "goals": {
                    "linked_investments_by_asset_type": [
                        {"asset_type": "fixed_income", "current_value_brl_cents": 12345}
                    ]
                }
            }
        })
        linked = enriched["financial_commitments"]["goals"]["linked_investments_by_asset_type"]
        self.assertEqual(linked[0]["current_value_brl_display"], "R$ 123,45")


if __name__ == "__main__":
    unittest.main()
