from contextlib import contextmanager
from decimal import Decimal
from http import HTTPStatus
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from financeiro import database, portfolio
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user


class PortfolioTransactionBoundaryTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tempdir.cleanup)
        self.dir_patch = patch.object(database, "DATA_DIR", Path(self.tempdir.name))
        self.db_patch = patch.object(database, "DB_PATH", Path(self.tempdir.name) / "test.db")
        self.dir_patch.start()
        self.db_patch.start()
        self.addCleanup(self.dir_patch.stop)
        self.addCleanup(self.db_patch.stop)
        database.initialize_database()
        self.connections = []
        self.network_calls = 0

        @contextmanager
        def tracked_connection():
            with database.get_connection() as conn:
                self.connections.append(conn)
                try:
                    yield conn
                finally:
                    self.connections.remove(conn)

        def offline(*args, **kwargs):
            self.assert_no_transaction()
            self.network_calls += 1
            raise portfolio.PortfolioError("Provedor indisponivel no teste.")

        def fx(*args, **kwargs):
            self.assert_no_transaction()
            return Decimal("5")

        quote_positions = portfolio.quote_positions

        def guarded_quotes(*args, **kwargs):
            self.assert_no_transaction()
            return quote_positions(*args, **kwargs)

        for name, replacement in (
            ("get_connection", tracked_connection),
            ("read_json_url", offline),
            ("get_exchange_rate_to_brl", fx),
            ("quote_positions", guarded_quotes),
        ):
            mocker = patch.object(portfolio, name, side_effect=replacement)
            mocker.start()
            self.addCleanup(mocker.stop)
        # Uma chamada que escapasse dos adaptadores também deve falhar, sem rede real.
        network = patch.object(portfolio, "urlopen", side_effect=AssertionError("Rede real proibida"))
        network.start()
        self.addCleanup(network.stop)
        with portfolio.QUOTE_MEMORY_CACHE_LOCK:
            portfolio.QUOTE_MEMORY_CACHE.clear()
        self.user = create_user("Teste", "boundary@example.com", "correct-password")
        self.account = create_checking_account(self.user["id"], {
            "name": "Carteira", "bank_name": "Banco", "account_type": "investment",
            "currency": "BRL", "initial_balance": "0",
        })
        portfolio.create_opening_position(self.user["id"], {
            "account_id": self.account["id"], "asset_type": "stock",
            "asset_identifier": "TEST3", "asset_name": "Teste",
            "acquisition_date": "2026-01-10", "quantity": "10", "total_cost": "100",
        })
        self.payload = {
            "account_id": self.account["id"], "currency": "BRL", "asset_type": "stock",
            "asset_identifier": "TEST3", "asset_name": "Teste", "date": "2026-08-31",
            "quantity": "1", "amount": "10", "closing_value": "100",
            "register_credit": True,
        }

    def assert_no_transaction(self):
        self.assertFalse(any(conn.in_transaction for conn in self.connections),
                         "Cotação/câmbio executado com transação aberta")

    def financial_counts(self):
        with database.get_connection() as conn:
            return tuple(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                         for table in ("transactions", "investment_redemptions",
                                       "investment_redemption_summaries", "investment_closed_positions"))

    def test_redemption_and_closing_do_not_requote_after_cache_is_cleared(self):
        original_begin = portfolio.begin_immediate

        def begin_with_expired_cache(conn):
            # Simula cache perdido depois do preparo, antes da confirmação.
            with portfolio.QUOTE_MEMORY_CACHE_LOCK:
                portfolio.QUOTE_MEMORY_CACHE.clear()
            with database.get_connection() as other:
                other.execute("DELETE FROM quote_cache")
            original_begin(conn)

        with patch.object(portfolio, "begin_immediate", side_effect=begin_with_expired_cache):
            portfolio.redeem_position(self.user["id"], self.payload)
            portfolio.close_position(self.user["id"], self.payload)
        self.assertGreater(self.network_calls, 0)
        self.assertEqual(self.financial_counts(), (2, 1, 1, 1))
        with database.get_connection() as conn:
            balance = conn.execute("SELECT current_balance_cents FROM checking_accounts WHERE id = ?",
                                   (self.account["id"],)).fetchone()[0]
        self.assertEqual(balance, 11000)

    def test_concurrent_lot_change_aborts_both_operations_without_financial_writes(self):
        original_begin = portfolio.begin_immediate

        def change_lot_then_begin(conn):
            with database.get_connection() as other:
                other.execute("UPDATE investment_opening_positions SET quantity_micros = quantity_micros + 1")
            original_begin(conn)

        for operation in (portfolio.redeem_position, portfolio.close_position):
            with self.subTest(operation=operation.__name__):
                with patch.object(portfolio, "begin_immediate", side_effect=change_lot_then_begin):
                    with self.assertRaises(portfolio.PortfolioError) as error:
                        operation(self.user["id"], self.payload)
                self.assertEqual(error.exception.status, HTTPStatus.CONFLICT)
                self.assertIn("tente novamente", str(error.exception))
                self.assertEqual(self.financial_counts(), (0, 0, 0, 0))

    def test_manual_override_change_is_detected(self):
        inputs, _ = portfolio.prepare_portfolio_positions(self.user["id"])
        with database.get_connection() as conn:
            conn.execute("""INSERT INTO investment_value_overrides
                (user_id, account_id, asset_type, current_value_cents, quote_date)
                VALUES (?, ?, 'stock', 5000, '2026-08-31')""",
                (self.user["id"], self.account["id"]))
        with database.get_connection() as conn:
            portfolio.begin_immediate(conn)
            with self.assertRaises(portfolio.PortfolioError) as error:
                portfolio.assert_portfolio_inputs_unchanged(conn, self.user["id"], inputs)
        self.assertEqual(error.exception.status, HTTPStatus.CONFLICT)

    def test_other_user_data_does_not_invalidate_snapshot(self):
        inputs, _ = portfolio.prepare_portfolio_positions(self.user["id"])
        other = create_user("Outro", "other-boundary@example.com", "correct-password")
        create_checking_account(other["id"], {
            "name": "Outra", "bank_name": "Banco", "account_type": "investment",
            "currency": "BRL", "initial_balance": "0",
        })
        with database.get_connection() as conn:
            portfolio.begin_immediate(conn)
            portfolio.assert_portfolio_inputs_unchanged(conn, self.user["id"], inputs)

    def test_foreign_currency_and_multiple_positions_are_prepared_outside_transaction(self):
        # Cobre também o executor paralelo de cotações e a conversão cambial.
        with database.get_connection() as conn:
            conn.execute("UPDATE checking_accounts SET currency = 'USD' WHERE id = ?", (self.account["id"],))
        portfolio.create_opening_position(self.user["id"], {
            "account_id": self.account["id"], "asset_type": "other",
            "asset_identifier": "OUTRO", "asset_name": "Outro",
            "acquisition_date": "2026-01-10", "quantity": "2",
            "total_cost": "20", "exchange_rate": "5",
        })
        payload = {**self.payload, "currency": "USD"}
        portfolio.redeem_position(self.user["id"], payload)
        portfolio.close_position(self.user["id"], payload)
        self.assertEqual(self.financial_counts(), (2, 1, 1, 1))

    def test_revalidation_reads_the_supplied_connection(self):
        inputs, _ = portfolio.prepare_portfolio_positions(self.user["id"])
        with database.get_connection() as conn:
            portfolio.begin_immediate(conn)
            conn.execute("UPDATE investment_opening_positions SET total_cost_cents = total_cost_cents + 1")
            with self.assertRaises(portfolio.PortfolioError):
                portfolio.assert_portfolio_inputs_unchanged(conn, self.user["id"], inputs)
            conn.rollback()

    def test_failure_during_write_rolls_back_redemption_and_closing(self):
        for operation in (portfolio.redeem_position, portfolio.close_position):
            with self.subTest(operation=operation.__name__):
                with patch.object(portfolio, "recompute_account_balance", side_effect=RuntimeError("rollback")):
                    with self.assertRaisesRegex(RuntimeError, "rollback"):
                        operation(self.user["id"], self.payload)
                self.assertEqual(self.financial_counts(), (0, 0, 0, 0))


if __name__ == "__main__":
    unittest.main()
