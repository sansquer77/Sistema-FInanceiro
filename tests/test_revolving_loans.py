import unittest
import tempfile
from datetime import date
from pathlib import Path

from financeiro import database
from financeiro.auth import create_user
from financeiro.database import begin_immediate, get_connection, initialize_database
from financeiro.accounts import create_checking_account
from financeiro.transactions import create_transaction, set_transaction_reconciled
from financeiro.operation_logs import OperationLogError, create_operation_log_with_conn
from financeiro.revolving_loans import (create_revolving_loan, create_revolving_loan_with_conn,
                                        link_payment, list_revolving_loans, update_revolving_loan)
from financeiro.revolving_loans import (RevolvingLoanError, project_revolving_balance,
                                        simulate_revolving_repayment)
from financeiro.loans import project_payoff_strategy


class RevolvingLoanProjectionTest(unittest.TestCase):
    def test_monthly_effective_rate_converted_to_30_day_daily_rate(self):
        result = project_revolving_balance(
            100_000, "2026-01-01", 10_000, "monthly", "daily", [], "2026-01-31"
        )
        # Daily cent rounding can differ slightly from the nominal monthly quote.
        self.assertEqual(result["balance_cents"], 100_990)
        self.assertEqual(result["interest_cents"], 990)
        self.assertTrue(result["estimated"])

    def test_daily_effective_rate_compounds_for_calendar_days(self):
        result = project_revolving_balance(
            100_000, "2026-01-01", 1_000, "daily", "daily", [], "2026-01-11"
        )
        self.assertEqual(result["balance_cents"], 101_005)
        self.assertEqual(result["interest_cents"], 1_005)
        self.assertFalse(result["estimated"])

    def test_payment_reduces_balance_at_start_of_payment_date(self):
        result = project_revolving_balance(
            100_000, "2026-01-01", 1_000, "daily", "daily",
            [{"date": "2026-01-02", "amount_cents": 30_000}], "2026-01-02",
        )
        self.assertEqual(result["interest_cents"], 100)
        self.assertEqual(result["balance_cents"], 70_100)
        self.assertEqual(result["payments_cents"], 30_000)

    def test_payment_on_balance_date_does_not_accrue_an_extra_day(self):
        result = project_revolving_balance(
            100_000, "2026-01-01", 1_000, "daily", "daily",
            [{"date": "2026-01-01", "amount_cents": 30_000}], "2026-01-01",
        )
        self.assertEqual(result["interest_cents"], 0)
        self.assertEqual(result["balance_cents"], 70_000)

    def test_dated_monthly_and_extraordinary_payments_compare_with_price(self):
        loan = {"balance_cents": 10_000, "balance_date": "2026-01-01", "currency": "BRL",
                "rate_micros": 10_000, "rate_period": "daily", "capitalization": "daily"}
        result = simulate_revolving_repayment(
            loan, 6_000, "2026-01-03", 5_000, "2026-01-02",
            price_principal_cents=10_000, price_rate_micros=0, price_installments=2,
        )
        self.assertTrue(result["revolving"]["paid_off"])
        self.assertEqual(result["revolving"]["months"], 1)
        self.assertEqual(result["revolving"]["interest_cents"], 151)
        self.assertEqual(result["revolving"]["total_paid_cents"], 10_151)
        self.assertEqual(result["no_payment"]["ending_balance_cents"], 10_201)
        self.assertTrue(result["price_offer"]["cheaper"])

    def test_price_offer_requires_all_terms(self):
        with self.assertRaises(RevolvingLoanError):
            simulate_revolving_repayment(
                {"balance_cents": 10_000, "balance_date": "2026-01-01", "currency": "BRL",
                 "rate_micros": 0, "rate_period": "daily", "capitalization": "daily"},
                10_000, "2026-01-01", price_principal_cents=10_000,
            )


class RevolvingLoanMonitoringTest(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()
        self.user = create_user("Rotativo", "rotativo@example.com", "test-password")

    def tearDown(self):
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def test_manual_monitoring_and_revisions_never_create_ledger_transactions(self):
        loan = create_revolving_loan(self.user["id"], {
            "name": "Cheque especial", "debt_type": "overdraft", "currency": "BRL",
            "balance": "1.000,00", "balance_date": "2026-09-25", "rate_percent": "8",
            "rate_period": "monthly", "capitalization": "daily",
        })
        update_revolving_loan(self.user["id"], loan["id"], {
            "name": "Cheque especial", "debt_type": "overdraft", "currency": "BRL",
            "balance": "900,00", "balance_date": "2026-09-26", "rate_percent": "7,5",
            "rate_period": "monthly", "capitalization": "daily",
        })
        listed = list_revolving_loans(self.user["id"])
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["balance_cents"], 90_000)
        self.assertEqual(len(listed[0]["terms_history"]), 2)
        with get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0], 0)

    def test_existing_account_payment_updates_only_after_reconciliation(self):
        loan = create_revolving_loan(self.user["id"], {
            "name": "Cheque especial", "debt_type": "overdraft", "currency": "BRL",
            "balance": "1.000,00", "balance_date": "2026-09-25", "rate_percent": "0",
            "rate_period": "daily", "capitalization": "daily",
        })
        account = create_checking_account(self.user["id"], {
            "name": "Conta", "bank_name": "Banco", "currency": "BRL", "initial_balance": "2.000,00",
        })
        transaction = create_transaction(self.user["id"], {
            "type": "expense", "description": "Pagamento cheque especial", "amount": "200,00",
            "date": "2026-09-26", "account_id": str(account["id"]),
            "category": "Empréstimos e Financiamentos", "revolving_loan_id": loan["id"],
        })
        self.assertEqual(list_revolving_loans(self.user["id"])[0]["balance_cents"], 100_000)
        self.assertEqual(len(list_revolving_loans(self.user["id"])[0]["pending_payments"]), 1)
        set_transaction_reconciled(self.user["id"], str(transaction["id"]), True)
        set_transaction_reconciled(self.user["id"], str(transaction["id"]), True)
        self.assertEqual(list_revolving_loans(self.user["id"])[0]["balance_cents"], 80_000)
        self.assertEqual(len(list_revolving_loans(self.user["id"])[0]["payments"]), 1)
        with get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=?", (self.user["id"],)).fetchone()[0], 1)
            self.assertEqual(conn.execute("SELECT amount_cents FROM transactions WHERE id=?", (transaction["id"],)).fetchone()[0], 20_000)

    def test_individual_study_does_not_persist_contract_or_create_transactions(self):
        loan = create_revolving_loan(self.user["id"], {
            "name": "Cheque especial", "debt_type": "overdraft", "currency": "BRL",
            "balance": "100,00", "balance_date": "2026-09-25", "rate_percent": "0",
            "rate_period": "daily", "capitalization": "daily",
        })
        before = list_revolving_loans(self.user["id"])[0]
        result = simulate_revolving_repayment(before, 3_000, "2026-09-26")
        after = list_revolving_loans(self.user["id"])[0]
        self.assertTrue(result["revolving"]["paid_off"])
        self.assertEqual(before["balance_cents"], after["balance_cents"])
        with get_connection() as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM transactions WHERE user_id=?", (self.user["id"],)).fetchone()[0], 0)

    def test_contract_and_audit_log_commit_or_rollback_together(self):
        payload = {
            "name": "Cheque especial QA", "debt_type": "overdraft", "currency": "BRL",
            "balance": "1.000,00", "balance_date": "2026-09-25", "rate_percent": "1",
            "rate_period": "daily", "capitalization": "daily",
        }
        with self.assertRaises(OperationLogError):
            with get_connection() as conn:
                begin_immediate(conn)
                loan = create_revolving_loan_with_conn(conn, self.user["id"], payload)
                create_operation_log_with_conn(
                    conn, self.user["id"], module="invalid", operation_type="create",
                    entity_type="revolving_loan", description="Dívida rotativa criada", entity_id=loan["id"],
                )
        self.assertEqual(list_revolving_loans(self.user["id"]), [])

        with get_connection() as conn:
            begin_immediate(conn)
            loan = create_revolving_loan_with_conn(conn, self.user["id"], payload)
            create_operation_log_with_conn(
                conn, self.user["id"], module="loans", operation_type="create",
                entity_type="revolving_loan", description="Dívida rotativa criada", entity_id=loan["id"],
            )
        self.assertEqual(len(list_revolving_loans(self.user["id"])), 1)


class RevolvingStrategyTest(unittest.TestCase):
    def test_paid_revolving_strategy_skips_unshown_zero_payment_baseline(self):
        revolving = {
            "id": 1, "name": "Cheque especial", "currency": "BRL", "status": "active",
            "balance_cents": 100_000, "balance_date": date.today().isoformat(),
            "rate_micros": 10_000, "rate_period": "daily", "capitalization": "daily",
        }
        result = project_payoff_strategy([], "snowball", 100_000, revolving_loans=[revolving])
        self.assertIsNone(result["baseline_months"])
        self.assertLess(result["months"], 1200)
        self.assertGreater(result["interest_cents"], 0)
        self.assertEqual(result["priority_order"][0]["kind"], "revolving")

    def test_runaway_revolving_projection_returns_a_domain_error(self):
        revolving = {
            "id": 1, "name": "Cheque especial", "currency": "BRL", "status": "active",
            "balance_cents": 100_000, "balance_date": date.today().isoformat(),
            "rate_micros": 10_000, "rate_period": "daily", "capitalization": "daily",
        }
        with self.assertRaisesRegex(RevolvingLoanError, "Aumente o orçamento mensal"):
            project_payoff_strategy([], "snowball", 1, revolving_loans=[revolving])


if __name__ == "__main__":
    unittest.main()
