from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.request import Request
from unittest import mock

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.portfolio import (
    QUOTE_MEMORY_CACHE,
    PortfolioError,
    apply_fund_quote,
    apply_market_quote,
    delete_position_value_override,
    effective_asset_type,
    fetch_fund_quote_for_user,
    fetch_mais_retorno_quote,
    mais_retorno_fund_identifier,
    normalize_asset_identifier,
    quote_positions,
    seconds_until_end_of_day,
    yahoo_symbol,
)


def fund_position(quantity: str = "10", cnpj: str = "12345678000199", currency: str = "BRL") -> dict:
    return {
        "asset_type": "fund",
        "asset_identifier": "FUNDO ABC",
        "asset_name": "FUNDO ABC",
        "cnpj": cnpj,
        "currency": currency,
        "quantity": Decimal(quantity),
        "total_cost_cents": 100_000,
        "total_cost_brl_cents": 100_000,
        "current_value_cents": 100_000,
        "current_value_brl_cents": 100_000,
        "day_result_cents": 0,
        "day_result_brl_cents": 0,
    }


def fake_quote(**overrides) -> dict:
    quote = {
        "price_cents": 15_000,
        "day_change_cents": 50,
        "date": "2026-08-07",
        "source": "Mais Retorno (12345678000199:fi)",
    }
    quote.update(overrides)
    return quote


class IsolatedDatabaseMixin(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self._original_data_dir = database.DATA_DIR
        self._original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-fund-quotes.db"
        initialize_database()
        QUOTE_MEMORY_CACHE.clear()

    def tearDown(self) -> None:
        QUOTE_MEMORY_CACHE.clear()
        database.DATA_DIR = self._original_data_dir
        database.DB_PATH = self._original_db_path
        self.tempdir.cleanup()


class FundQuoteApplicationTest(IsolatedDatabaseMixin):
    def test_vwra_usd_resolves_to_london_yahoo_symbol(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.37 — critério 53
        self.assertEqual(yahoo_symbol({
            "asset_type": "stock", "asset_identifier": "VWRA", "currency": "USD",
        }), "VWRA.L")

    def test_manual_override_can_return_to_automatic_even_after_legacy_reclassification(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.37 — critérios 51 e 52
        user = create_user("Alice", "alice@example.com", "correct-password")
        account = create_checking_account(user["id"], {
            "name": "Coinbase", "bank_name": "Coinbase", "account_type": "investment", "currency": "BRL",
        })
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO investment_value_overrides (
                    user_id, account_id, asset_type, asset_identifier, asset_name, cnpj,
                    fixed_income_indexer, fixed_income_maturity_date, current_value_cents, quote_date
                ) VALUES (?, ?, 'crypto', 'USDC', 'USD Coin', '', '', '', 10000, '2026-08-29')
                """,
                (user["id"], account["id"]),
            )

        delete_position_value_override(user["id"], {
            "account_id": account["id"], "asset_type": "stablecoin", "asset_identifier": "USDC",
            "asset_name": "USD Coin", "cnpj": "", "fixed_income_indexer": "",
            "fixed_income_maturity_date": "", "quote_date": "2026-08-29",
        })

        with get_connection() as conn:
            remaining = conn.execute("SELECT COUNT(*) FROM investment_value_overrides WHERE user_id = ?", (user["id"],)).fetchone()[0]
        self.assertEqual(remaining, 0)

    def test_stablecoins_have_own_class_and_keep_account_quote_currency(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.37 — critérios 49 e 50
        self.assertEqual(effective_asset_type("crypto", "USDC-BRL"), "stablecoin")
        self.assertEqual(effective_asset_type("crypto", "BTC-BRL"), "crypto")
        self.assertEqual(normalize_asset_identifier("USDT-USD", "stablecoin"), "USDT")
        position = {
            **fund_position(currency="USD"),
            "asset_type": "stablecoin",
            "asset_identifier": "USDC",
            "quantity": Decimal("10"),
        }
        with (
            mock.patch(
                "financeiro.portfolio.fetch_crypto_quote",
                return_value={"price_cents": 100, "day_change_cents": 0, "date": "2026-08-29", "source": "teste"},
            ) as fetch_quote,
            mock.patch("financeiro.portfolio.value_to_brl", side_effect=lambda value, _currency: value),
        ):
            apply_market_quote(position)

        fetch_quote.assert_called_once_with("USDC", "USD", force_refresh=False)
        self.assertEqual(position["current_value_cents"], 1000)


    def test_fund_with_cnpj_brl_and_key_uses_mais_retorno_quote(self) -> None:
        # spec: preferencias-abas v0.5 — critério 9
        position = fund_position()
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value="mr-secret"),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", return_value=fake_quote()) as fetch,
        ):
            apply_fund_quote(position, user_id=7)

        fetch.assert_called_once_with("12345678000199:fi", "mr-secret", force_refresh=False)
        self.assertEqual(position["quote"], "150.00")
        self.assertEqual(position["quote_status"], "ok")
        self.assertEqual(position["quote_date"], "2026-08-07")
        self.assertEqual(position["quote_source"], "Mais Retorno (12345678000199:fi)")
        self.assertEqual(position["current_value_cents"], 150_000)
        self.assertEqual(position["current_value_brl_cents"], 150_000)
        self.assertEqual(position["day_result_cents"], 500)
        self.assertEqual(position["day_result_brl_cents"], 500)

    def test_private_pension_with_cnpj_uses_mais_retorno_quote(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.20 — criterio previdencia-mais-retorno
        position = {**fund_position(quantity="8", cnpj="46.422.299/0001-73"), "asset_type": "private_pension"}
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value="mr-secret"),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", return_value=fake_quote(
                price_cents=12_345,
                day_change_cents=12,
                source="Mais Retorno (46422299000173:fi)",
            )) as fetch,
        ):
            quote_positions([position], user_id=7)

        fetch.assert_called_once_with("46422299000173:fi", "mr-secret", force_refresh=False)
        self.assertEqual(position["quote"], "123.45")
        self.assertEqual(position["quote_status"], "ok")
        self.assertEqual(position["current_value_cents"], 98_760)
        self.assertEqual(position["day_result_cents"], 96)

    def test_fund_without_key_keeps_cost_and_pending_status(self) -> None:
        # spec: preferencias-abas v0.5 — critério 10
        position = fund_position()
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value=""),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", side_effect=AssertionError("nao deve chamar")),
        ):
            apply_fund_quote(position, user_id=7)

        self.assertEqual(position["quote_status"], "Cotacao manual pendente")
        self.assertEqual(position["current_value_cents"], position["total_cost_cents"])
        self.assertEqual(position["current_value_brl_cents"], position["total_cost_brl_cents"])
        self.assertEqual(position["day_result_cents"], 0)

    def test_fund_without_cnpj_keeps_cost_value(self) -> None:
        # spec: preferencias-abas v0.5 — critério 10
        position = fund_position(cnpj="")
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value="mr-secret"),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", side_effect=AssertionError("nao deve chamar")),
        ):
            apply_fund_quote(position, user_id=7)

        self.assertEqual(position["quote_status"], "Cotacao manual pendente")
        self.assertEqual(position["current_value_cents"], position["total_cost_cents"])
        self.assertEqual(position["day_result_cents"], 0)

    def test_fund_in_non_brl_wallet_ignores_integration(self) -> None:
        # spec: preferencias-abas v0.5 — critério 12
        position = fund_position(currency="USD")
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value="mr-secret"),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", side_effect=AssertionError("nao deve chamar")),
        ):
            apply_fund_quote(position, user_id=7)

        self.assertEqual(position["quote_status"], "Cotacao manual pendente")
        self.assertEqual(position["current_value_cents"], position["total_cost_cents"])

    def test_fund_api_failure_keeps_cost_with_friendly_message(self) -> None:
        # spec: preferencias-abas v0.5 — critério 11
        position = fund_position()
        error = PortfolioError("Cotacao do fundo indisponivel")
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value="mr-secret"),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", side_effect=error),
        ):
            apply_fund_quote(position, user_id=7)

        self.assertEqual(position["quote_status"], "Cotacao do fundo indisponivel")
        self.assertEqual(position["current_value_cents"], position["total_cost_cents"])
        self.assertEqual(position["day_result_cents"], 0)

    def test_non_fund_assets_never_call_mais_retorno(self) -> None:
        # spec: preferencias-abas v0.5 — critério 12 (apenas posicoes fund sao afetadas)
        stock = {
            **fund_position(),
            "asset_type": "stock",
            "asset_identifier": "PETR4",
        }
        crypto = {
            **fund_position(),
            "asset_type": "crypto",
            "asset_identifier": "BTC",
        }
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value="mr-secret"),
            mock.patch("financeiro.portfolio.apply_market_quote") as market,
        ):
            quote_positions([stock, crypto], user_id=7)

        self.assertEqual(market.call_count, 2)


class FetchMaisRetornoQuoteTest(IsolatedDatabaseMixin):

    def _response(self, payload: dict):
        response_mock = mock.Mock()
        response_mock.__enter__ = mock.Mock(return_value=response_mock)
        response_mock.__exit__ = mock.Mock(return_value=False)
        response_mock.read.return_value = json.dumps(payload).encode("utf-8")
        return response_mock

    def test_sends_api_key_and_uses_latest_quote_with_previous_change(self) -> None:
        # spec: preferencias-abas v0.5 — critério 9 (cota mais recente e variacao do dia)
        payload = {
            "quotes": [
                {"d": "2026-08-05", "c": 1.20},
                {"d": "2026-08-06", "c": 1.30},
                {"d": "2026-08-07", "c": 1.50},
            ]
        }
        with mock.patch("financeiro.portfolio.urlopen", return_value=self._response(payload)) as urlopen_mock:
            quote = fetch_mais_retorno_quote("12345678000199:fi", "mr-secret")

        request = urlopen_mock.call_args.args[0]
        self.assertIsInstance(request, Request)
        self.assertIn("quotes/12345678000199%3Afi", request.full_url)
        today = datetime.now().strftime("%Y-%m-%d")
        self.assertIn(f"start_date={today}", request.full_url)
        self.assertIn(f"end_date={today}", request.full_url)
        request_headers = {key.lower(): value for key, value in request.headers.items()}
        self.assertEqual(request_headers.get("x-api-key"), "mr-secret")
        self.assertEqual(quote["price_cents"], 150)
        self.assertEqual(quote["day_change_cents"], 20)
        self.assertEqual(quote["date"], "2026-08-07")
        self.assertIn("Mais Retorno", quote["source"])

    def test_cnpj_formatted_is_normalized_to_digits_only(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.14 — critério fundos-mais-retorno
        # (API exige CNPJ sem pontos/barra; ex.: 46.422.299/0001-73 -> 46422299000173)
        self.assertEqual(
            mais_retorno_fund_identifier(fund_position(cnpj="46.422.299/0001-73")),
            "46422299000173:fi",
        )
        self.assertEqual(
            mais_retorno_fund_identifier(fund_position(cnpj="46.422.299/0001-73 ")),
            "46422299000173:fi",
        )
        self.assertEqual(mais_retorno_fund_identifier(fund_position(cnpj="")), "")

    def test_fetch_fund_quote_for_launch_form_returns_editable_unit_price_data(self) -> None:
        # spec: lancamentos v3.23 — criterio cota-fundo-lancamento
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value="mr-secret"),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", return_value=fake_quote(
                price_cents=123_456,
                date="2026-08-10",
                source="Mais Retorno (46422299000173:fi)",
            )) as fetch,
        ):
            quote = fetch_fund_quote_for_user(7, "46.422.299/0001-73")

        fetch.assert_called_once_with("46422299000173:fi", "mr-secret", force_refresh=False)
        self.assertEqual(quote["cnpj"], "46422299000173")
        self.assertEqual(quote["identifier"], "46422299000173:fi")
        self.assertEqual(quote["unit_price"], "1234.56")
        self.assertEqual(quote["quote_date"], "2026-08-10")
        self.assertEqual(quote["quote_source"], "Mais Retorno (46422299000173:fi)")

    def test_fetch_fund_quote_for_launch_form_requires_mais_retorno_key(self) -> None:
        # spec: lancamentos v3.23 — criterio cota-fundo-lancamento
        with (
            mock.patch("financeiro.portfolio.load_mais_retorno_api_key", return_value=""),
            mock.patch("financeiro.portfolio.fetch_mais_retorno_quote", side_effect=AssertionError("nao deve chamar")),
        ):
            with self.assertRaises(PortfolioError) as error:
                fetch_fund_quote_for_user(7, "46.422.299/0001-73")

        self.assertIn("Mais Retorno", error.exception.message)

    def test_float_quote_with_dot_decimal_separator_is_converted_to_cents(self) -> None:
        # spec: preferencias-abas v0.5 — critério 9 e investimentos-portfolio v2.14:
        # a API entrega o preco como numeral JSON (separador ".") — 1.601637 -> 160 centavos
        payload = {"quotes": [{"d": "2026-08-07", "c": 1.601637}]}
        with mock.patch("financeiro.portfolio.urlopen", return_value=self._response(payload)) as urlopen_mock:
            quote = fetch_mais_retorno_quote("12345678000199:fi", "mr-secret")
        self.assertEqual(quote["price_cents"], 160)
        self.assertEqual(quote["date"], "2026-08-07")

    def test_quote_with_comma_string_is_normalized(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.14 — critério fundos-mais-retorno
        # (defesa caso a API retorne texto com virgula: "1,50" -> 150 centavos)
        payload = {"quotes": [{"d": "2026-08-07", "c": "1,50"}]}
        with mock.patch("financeiro.portfolio.urlopen", return_value=self._response(payload)):
            quote = fetch_mais_retorno_quote("12345678000199:fi", "mr-secret")
        self.assertEqual(quote["price_cents"], 150)

    def test_empty_quotes_raises_friendly_error(self) -> None:
        # spec: preferencias-abas v0.5 — critério 11 (resposta inesperada)
        with mock.patch("financeiro.portfolio.urlopen", return_value=self._response({"quotes": []})):
            with self.assertRaises(PortfolioError) as error:
                fetch_mais_retorno_quote("12345678000199:fi", "mr-secret")
        self.assertEqual(error.exception.message, "Cotacao do fundo indisponivel")

    def test_no_quote_today_falls_back_to_recent_window(self) -> None:
        # spec: investimentos/investimentos-portfolio v2.14 — critério fundos-mais-retorno
        # (fim de semana/feriado: a data atual vem vazia e a consulta retroage 7 dias)
        today = datetime.now().strftime("%Y-%m-%d")
        start7 = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        last_quote_day = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        empty = {"quotes": []}
        previous_weekday = {"quotes": [{"d": last_quote_day, "c": 1.0100}]}
        with mock.patch(
            "financeiro.portfolio.urlopen",
            side_effect=[self._response(empty), self._response(previous_weekday)],
        ) as urlopen_mock:
            quote = fetch_mais_retorno_quote("46422299000173:fi", "mr-secret")

        urls = [call.args[0].full_url for call in urlopen_mock.call_args_list]
        self.assertIn(f"start_date={today}", urls[0])
        self.assertIn(f"start_date={start7}", urls[1])
        self.assertIn(f"end_date={today}", urls[1])
        self.assertEqual(quote["price_cents"], 101)
        self.assertEqual(quote["date"], last_quote_day)

    def test_quote_is_cached_until_end_of_day(self) -> None:
        # spec: preferencias-abas v0.5 — regra de cache diario (ate o fim do dia corrente)
        ttl = seconds_until_end_of_day()
        self.assertGreater(ttl, 0)
        self.assertLessEqual(ttl, 24 * 60 * 60)
        expiry_limit = datetime.now() + timedelta(seconds=ttl)
        self.assertEqual(expiry_limit.date(), datetime.now().date())
        payload = {"quotes": [{"d": "2026-08-07", "c": "1.50"}]}
        with mock.patch("financeiro.portfolio.urlopen", return_value=self._response(payload)) as urlopen_mock:
            first = fetch_mais_retorno_quote("99999999000137:cached", "mr-secret")
            second = fetch_mais_retorno_quote("99999999000137:cached", "mr-secret")
            forced = fetch_mais_retorno_quote("99999999000137:cached", "mr-secret", force_refresh=True)

        self.assertEqual(urlopen_mock.call_count, 2)
        self.assertEqual(first["price_cents"], second["price_cents"])
        self.assertEqual(forced["price_cents"], 150)


if __name__ == "__main__":
    unittest.main()
