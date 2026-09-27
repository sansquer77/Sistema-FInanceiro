from __future__ import annotations

import tempfile
import unittest
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from financeiro import database
from financeiro.accounts import create_checking_account
from financeiro.auth import create_user
from financeiro.database import get_connection, initialize_database
from financeiro.loans import (
    LoanError,
    archive_loan,
    create_loan,
    delete_loan,
    estimate_remaining_price_values,
    list_loans,
    link_payment,
    project_indexed_payment_plan,
    project_full_payoff,
    project_payoff_strategy,
    project_payoff_vs_cdi,
    project_payment_plan,
    _latest_indexer_projection_assumption,
    update_loan,
)
from financeiro.transactions import create_transaction, set_transaction_reconciled


class LoansTest(unittest.TestCase):
    """Examples use cents internally: R$ 12,000.00 is 1_200_000 cents."""

    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.original_data_dir = database.DATA_DIR
        self.original_db_path = database.DB_PATH
        database.DATA_DIR = Path(self.tempdir.name)
        database.DB_PATH = database.DATA_DIR / "test-finance.db"
        initialize_database()
        self.user = create_user("Loan Tester", "loan@example.com", "correct-password")

    def tearDown(self) -> None:
        database.DATA_DIR = self.original_data_dir
        database.DB_PATH = self.original_db_path
        self.tempdir.cleanup()

    def loan_payload(self, **overrides: object) -> dict:
        payload = {
            "name": "Financiamento exemplo",
            "loan_type": "vehicle",
            "amortization_system": "price",
            "currency": "BRL",
            "installment_amount": "1.066,19",
            "remaining_installments": 12,
            "remaining_commitment": "12.794,28",
            "monthly_rate_percent": "1",
            "next_due_date": "2026-10-10",
        }
        payload.update(overrides)
        return payload

    def test_price_example_12000_12_months_at_one_percent(self) -> None:
        principal, future_interest = estimate_remaining_price_values(
            106_619, 12, 10_000, 1_279_428, "price"
        )
        # The monthly payment is rounded to cents, so the inverse PV can differ
        # from the original principal by a few cents.
        self.assertAlmostEqual(principal, 1_200_000, delta=10)
        self.assertEqual(future_interest, 79_423)

    def test_sac_example_starts_at_1120_and_ends_at_1010(self) -> None:
        first = project_payment_plan(112_000, 12, 10_000, amortization_system="sac")
        self.assertEqual(first["estimated_principal_cents"], 1_200_000)
        self.assertEqual(first["new_installment_cents"], 112_000)
        self.assertEqual(first["interest_cents"], 78_000)
        self.assertEqual(first["months"], 12)

    def test_extra_monthly_payment_reduces_term_and_interest_without_changing_contract_installment(self) -> None:
        result = project_payment_plan(280_905, 32, 2_500, extra_cents=50_000)
        self.assertLess(result["months"], result["baseline_months"])
        self.assertGreater(result["months_saved"], 0)
        self.assertGreater(result["interest_saved_cents"], 0)
        self.assertEqual(result["new_installment_cents"], 280_905)

    def test_extraordinary_amortization_can_compare_term_and_payment_reduction(self) -> None:
        reduce_term = project_payment_plan(
            106_619, 12, 10_000, extraordinary_cents=200_000, amortization_mode="reduce_term"
        )
        reduce_payment = project_payment_plan(
            106_619, 12, 10_000, extraordinary_cents=200_000, amortization_mode="reduce_payment"
        )
        self.assertLess(reduce_term["months"], 12)
        self.assertEqual(reduce_payment["months"], 12)
        self.assertLess(reduce_payment["new_installment_cents"], 106_619)

    def test_sac_additional_payment_uses_constant_principal_and_shortens_term(self) -> None:
        result = project_payment_plan(
            112_000, 12, 10_000, extra_cents=20_000, amortization_system="sac"
        )
        self.assertEqual(result["amortization_system"], "sac")
        self.assertLess(result["months"], result["baseline_months"])
        self.assertGreater(result["interest_saved_cents"], 0)

    def test_indexed_price_projection_applies_historical_factor_and_reports_correction(self) -> None:
        loan = {
            "id": 1, "name": "Imóvel IPCA", "currency": "BRL", "indexer": "IPCA",
            "amortization_system": "price", "remaining_installments": 2,
            "installment_cents": 51_000, "principal_balance_cents": 100_000,
            "principal_balance_date": "2020-01-01", "next_due_date": "2020-02-01",
            "remuneratory_rate_micros": 10_000,
        }
        with patch("financeiro.portfolio.fetch_accumulated_indexer_factor", return_value=Decimal("1.01")) as fetch:
            result = project_indexed_payment_plan(loan)
        self.assertEqual(fetch.call_count, 2)
        self.assertEqual(result["indexer"], "IPCA")
        self.assertGreater(result["indexation_cents"], 0)
        self.assertEqual(result["months"], 2)

    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 61
    def test_indexed_projection_matrix_covers_price_and_sac_with_all_supported_indexers(self) -> None:
        """Exercise historical correction across both schedules and all supported indexes."""
        cases = (
            ("TR", "fetch_accumulated_indexer_factor"),
            ("IPCA", "fetch_accumulated_indexer_factor"),
            ("POUPANCA", "savings_factor_for_anniversary"),
        )
        for indexer, factor_function in cases:
            for system in ("price", "sac"):
                with self.subTest(indexer=indexer, system=system):
                    loan = {
                        "id": 1, "currency": "BRL", "indexer": indexer,
                        "amortization_system": system, "remaining_installments": 2,
                        "installment_cents": 51_000, "principal_balance_cents": 100_000,
                        "principal_balance_date": "2020-01-01", "next_due_date": "2020-02-01",
                        "remuneratory_rate_micros": 10_000,
                    }
                    patches = [
                        patch("financeiro.portfolio.fetch_accumulated_indexer_factor", return_value=Decimal("1.01")),
                        patch("financeiro.portfolio.savings_additional_monthly_rate", return_value=Decimal("0.003")),
                        patch("financeiro.portfolio.savings_factor_for_anniversary", return_value=Decimal("1.01")),
                    ]
                    with patches[0], patches[1], patches[2] as savings_factor:
                        result = project_indexed_payment_plan(loan)

                    self.assertEqual(result["indexer"], indexer)
                    self.assertEqual(result["amortization_system"], system)
                    self.assertEqual(result["months"], 2)
                    self.assertGreater(result["indexation_cents"], 0)
                    if factor_function == "savings_factor_for_anniversary":
                        self.assertEqual(savings_factor.call_count, 2)

    def test_indexed_projection_requires_assumption_for_future_periods(self) -> None:
        today = date.today()
        loan = {
            "id": 1, "currency": "BRL", "indexer": "TR", "amortization_system": "sac",
            "remaining_installments": 2, "installment_cents": 51_000,
            "principal_balance_cents": 100_000,
            "principal_balance_date": today.isoformat(),
            "next_due_date": today.replace(day=min(today.day, 28)).isoformat(),
            "remuneratory_rate_micros": 10_000,
        }
        loan["next_due_date"] = (today.replace(day=1)).isoformat()
        with self.assertRaises(LoanError):
            project_indexed_payment_plan(loan)

    def test_indexed_projection_automatically_uses_accumulated_trailing_twelve_month_rate(self) -> None:
        today = date.today()
        loan = {
            "id": 1, "currency": "BRL", "indexer": "TR", "amortization_system": "price",
            "remaining_installments": 2, "installment_cents": 51_000,
            "principal_balance_cents": 100_000,
            "principal_balance_date": today.isoformat(),
            "next_due_date": "2099-01-10", "remuneratory_rate_micros": 10_000,
        }
        assumption = {
            "factor": Decimal("1.05"), "accumulated_rate_micros": 50_000,
            "monthly_rate": Decimal("1.05") ** (Decimal(1) / Decimal(12)) - Decimal(1),
            "monthly_rate_micros": 4_074, "period_start": "2025-09-27", "period_end": "2026-09-26",
        }
        with patch("financeiro.loans._latest_indexer_projection_assumption", return_value=assumption) as estimate:
            result = project_indexed_payment_plan(loan)
        self.assertEqual(estimate.call_count, 1)
        self.assertGreater(result["indexation_cents"], 0)
        self.assertEqual(result["future_index_accumulated_rate_micros"], 50_000)
        self.assertEqual(result["future_index_monthly_rate_micros"], 4_074)
        self.assertEqual(result["future_index_period_start"], "2025-09-27")

    def test_indexed_strategy_separates_interest_and_indexation(self) -> None:
        today = date.today()
        loan = {
            "id": 1, "name": "Crédito TR", "currency": "BRL", "indexer": "TR",
            "amortization_system": "sac", "remaining_installments": 2,
            "installment_cents": 51_000, "remaining_commitment_cents": 102_000,
            "principal_balance_cents": 100_000, "principal_balance_date": "2020-01-01",
            "next_due_date": "2020-02-01", "remuneratory_rate_micros": 10_000,
        }
        assumption = {
            "factor": Decimal("1.05"), "accumulated_rate_micros": 50_000,
            "monthly_rate": Decimal("1.05") ** (Decimal(1) / Decimal(12)) - Decimal(1),
            "monthly_rate_micros": 4_074, "period_start": "2025-09-27", "period_end": "2026-09-26",
        }
        with patch("financeiro.portfolio.fetch_accumulated_indexer_factor", return_value=Decimal("1.01")), patch(
            "financeiro.loans._latest_indexer_projection_assumption", return_value=assumption
        ):
            result = project_payoff_strategy(
                [loan], "avalanche", 5_000
            )
        self.assertGreater(result["interest_cents"], 0)
        self.assertGreater(result["indexation_cents"], 0)
        self.assertEqual(result["currency"], "BRL")
        self.assertEqual(result["future_index_assumptions"]["TR"]["accumulated_rate_micros"], 50_000)

    def test_future_index_assumption_uses_official_factor_for_latest_twelve_month_window(self) -> None:
        reference = date(2026, 9, 26)
        observed = {
            "factor": Decimal("1.12"), "period_start": "2025-10-01", "period_end": "2026-09-01", "observations": 12,
        }
        with patch("financeiro.portfolio.fetch_trailing_twelve_month_indexer_factor", return_value=observed) as fetch:
            result = _latest_indexer_projection_assumption("IPCA", reference)
        self.assertEqual(fetch.call_args.args[0], "IPCA")
        self.assertEqual(fetch.call_args.args[1], reference)
        self.assertEqual(result["period_start"], "2025-10-01")
        self.assertEqual(result["period_end"], "2026-09-01")
        self.assertEqual(result["accumulated_rate_micros"], 120_000)
        self.assertAlmostEqual(float(result["monthly_rate"]), float(Decimal("1.12") ** (Decimal(1) / Decimal(12)) - 1), places=10)

    def test_trailing_twelve_month_index_factor_uses_twelve_published_months_for_ipca_and_savings(self) -> None:
        from financeiro.portfolio import fetch_trailing_twelve_month_indexer_factor

        reference = date(2026, 9, 26)
        monthly_payload = []
        for year, month in [(2025, month) for month in range(8, 13)] + [(2026, month) for month in range(1, 10)]:
            month_date = date(year, month, 1)
            monthly_payload.append({"data": month_date.strftime("%d/%m/%Y"), "valor": "1"})
        with patch("financeiro.portfolio.cached_json_url", return_value=monthly_payload):
            ipca = fetch_trailing_twelve_month_indexer_factor("IPCA", reference)
        self.assertEqual(ipca["observations"], 12)
        self.assertEqual(ipca["period_start"], "2025-10-01")
        self.assertEqual(ipca["period_end"], "2026-09-01")
        self.assertAlmostEqual(float(ipca["factor"]), 1.01**12, places=10)

        savings_payload = []
        for year, month in [(2025, month) for month in range(8, 13)] + [(2026, month) for month in range(1, 10)]:
            savings_payload.extend([
                {"data": date(year, month, 1).strftime("%d/%m/%Y"), "valor": "0,4"},
                {"data": date(year, month, 15).strftime("%d/%m/%Y"), "valor": "0,5"},
            ])
        with patch("financeiro.portfolio.cached_json_url", return_value=savings_payload):
            savings = fetch_trailing_twelve_month_indexer_factor("POUPANCA", reference)
        self.assertEqual(savings["observations"], 12)
        self.assertEqual(savings["period_start"], "2025-10-15")
        self.assertEqual(savings["period_end"], "2026-09-15")
        self.assertAlmostEqual(float(savings["factor"]), 1.005**12, places=10)

    def test_trailing_twelve_month_tr_factor_uses_daily_observations_until_latest_publication(self) -> None:
        from financeiro.portfolio import fetch_trailing_twelve_month_indexer_factor

        reference = date(2026, 9, 26)
        first = reference - timedelta(days=399)
        payload = []
        current = first
        while current <= reference:
            payload.append({"data": current.strftime("%d/%m/%Y"), "valor": "0,01"})
            current += timedelta(days=1)
        with patch("financeiro.portfolio.cached_json_url", return_value=payload):
            tr = fetch_trailing_twelve_month_indexer_factor("TR", reference)
        self.assertEqual(tr["period_end"], reference.isoformat())
        self.assertEqual(tr["period_start"], "2025-09-27")
        self.assertEqual(tr["observations"], 365)
        self.assertAlmostEqual(float(tr["factor"]), 1.0001**365, places=10)

    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 79
    def test_latest_cdi_assumption_uses_latest_published_daily_rate_and_252_days(self) -> None:
        from financeiro.portfolio import fetch_latest_cdi_assumption

        with patch("financeiro.portfolio.cached_json_url", return_value=[{"data": "23/09/2026", "valor": "0,05"}]):
            cdi = fetch_latest_cdi_assumption()
        self.assertEqual(cdi["rate_date"], "2026-09-23")
        daily = Decimal("0.0005")
        annual_factor = (Decimal("1") + daily) ** 252
        self.assertEqual(cdi["daily_rate"], daily)
        self.assertEqual(cdi["annual_rate"], annual_factor - 1)
        self.assertEqual(cdi["monthly_rate"], annual_factor ** (Decimal("1") / Decimal("12")) - 1)

    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 78
    def test_payoff_vs_cdi_compares_same_extra_contributions_over_baseline_horizon(self) -> None:
        observed = {
            "daily_rate": Decimal("0.0005"), "annual_rate": Decimal("0.134",),
            "monthly_rate": Decimal("0.01"), "rate_date": "2026-09-23",
        }
        result = {"baseline_months": 2, "interest_saved_cents": 30_000}
        with patch("financeiro.portfolio.fetch_latest_cdi_assumption", return_value=observed):
            comparison = project_payoff_vs_cdi(result, 10_000, 100_000)
        self.assertTrue(comparison["available"])
        self.assertEqual(comparison["invested_cents"], 120_000)
        monthly_factor = Decimal("1.01")
        expected_ending = int((Decimal(100_000) * monthly_factor ** 2
                               + Decimal(10_000) * monthly_factor
                               + Decimal(10_000)).quantize(Decimal("1")))
        self.assertEqual(comparison["ending_balance_cents"], expected_ending)
        self.assertEqual(comparison["gross_gain_cents"], expected_ending - 120_000)
        self.assertEqual(comparison["advantage_cents"], 30_000 - (expected_ending - 120_000))
        self.assertEqual(comparison["rate_date"], "2026-09-23")

    # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critérios 84–90
    def test_full_payoff_uses_estimated_principal_and_compares_it_with_cdi(self) -> None:
        create_loan(self.user["id"], self.loan_payload())
        loan = list_loans(self.user["id"])[0]
        observed = {
            "daily_rate": Decimal("0.0005"), "annual_rate": Decimal("0.134"),
            "monthly_rate": Decimal("0.01"), "rate_date": "2026-09-23",
        }
        with patch("financeiro.portfolio.fetch_latest_cdi_assumption", return_value=observed):
            result = project_full_payoff(loan)
        self.assertEqual(result["study_type"], "payoff")
        self.assertEqual(result["payoff_amount_cents"], loan["estimated_principal_cents"])
        self.assertEqual(result["extraordinary_cents"], loan["estimated_principal_cents"])
        self.assertEqual(result["months"], 0)
        self.assertGreater(result["interest_saved_cents"], 0)
        self.assertTrue(result["cdi_comparison"]["available"])

    def test_full_payoff_requires_current_principal_and_rate_data(self) -> None:
        with self.assertRaisesRegex(LoanError, "Atualize o saldo principal"):
            project_full_payoff({"principal_review_required": True})
        with self.assertRaisesRegex(LoanError, "Informe a taxa do contrato"):
            project_full_payoff({"indexer": "none", "estimated_principal_cents": None, "monthly_rate_micros": None})

    def test_payoff_vs_cdi_reports_unavailable_when_history_is_unreachable_or_no_extra_exists(self) -> None:
        result = {"baseline_months": 12, "interest_saved_cents": 500}
        with patch("financeiro.portfolio.fetch_latest_cdi_assumption", side_effect=RuntimeError):
            unavailable = project_payoff_vs_cdi(result, 10_000, 0)
        self.assertFalse(unavailable["available"])
        no_amount = project_payoff_vs_cdi(result, 0, 0)
        self.assertFalse(no_amount["available"])

    def test_payoff_vs_cdi_compares_avoided_indexation_with_gross_cdi_gain(self) -> None:
        observed = {
            "daily_rate": Decimal("0.0005"), "annual_rate": Decimal("0.134"),
            "monthly_rate": Decimal("0.01"), "rate_date": "2026-09-23",
        }
        result = {
            "baseline_months": 1, "interest_saved_cents": 30_000,
            "baseline_indexation_cents": 5_000, "indexation_cents": 2_000,
        }
        with patch("financeiro.portfolio.fetch_latest_cdi_assumption", return_value=observed):
            comparison = project_payoff_vs_cdi(result, 0, 100_000)
        self.assertEqual(comparison["indexation_saved_cents"], 3_000)
        self.assertEqual(comparison["financing_cost_saved_cents"], 33_000)
        self.assertEqual(comparison["advantage_cents"], 32_000)

    def test_reconciled_indexed_payment_marks_old_principal_for_review_and_blocks_studies(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload(
            indexer="IPCA", principal_balance="1000,00", principal_balance_date="2026-10-01",
            remuneratory_rate_percent="1", monthly_rate_percent="", next_due_date="2026-10-10",
        ))
        account = create_checking_account(self.user["id"], {
            "name": "Conta para pagamento indexado", "bank_name": "Banco", "currency": "BRL", "initial_balance": "5000,00",
        })
        transaction = create_transaction(self.user["id"], {
            "type": "expense", "description": "Parcela indexada conciliada", "amount": "1.066,19",
            "date": "2026-10-10", "account_id": str(account["id"]),
            "category": "Empréstimos e Financiamentos", "loan_id": loan["id"],
        })
        set_transaction_reconciled(self.user["id"], str(transaction["id"]), True)
        # spec: emprestimos-quitacao/emprestimos-quitacao v0.57 — critério 77
        current = list_loans(self.user["id"])[0]
        self.assertTrue(current["principal_review_required"])
        self.assertIsNone(current["principal_balance_cents"])
        self.assertEqual(current["latest_payment_date"], "2026-10-10")
        with self.assertRaisesRegex(LoanError, "Atualize o principal e a data-base"):
            project_indexed_payment_plan(current)
        with self.assertRaisesRegex(LoanError, "Atualize o principal e a data-base"):
            project_payoff_strategy([current], "avalanche", 5_000)

    def test_studies_do_not_persist_or_change_registered_contract(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload())
        before = list_loans(self.user["id"])[0]
        project_payment_plan(106_619, 12, 10_000, extra_cents=5_000)
        project_payoff_strategy([{
            "id": loan["id"], "name": "Contrato exemplo", "currency": "BRL", "remaining_installments": 12,
            "installment_cents": 106_619, "remaining_commitment_cents": 1_279_428,
            "monthly_rate_micros": 10_000, "amortization_system": "price", "indexer": "none",
        }], "avalanche", 5_000)
        after = list_loans(self.user["id"])[0]
        self.assertEqual(after["remaining_installments"], before["remaining_installments"])
        self.assertEqual(after["remaining_commitment_cents"], before["remaining_commitment_cents"])

    def test_avalanche_and_snowball_use_distinct_priorities(self) -> None:
        loans = [
            {"id": 1, "name": "Menor saldo", "currency": "BRL", "remaining_installments": 6,
             "installment_cents": 20_000, "remaining_commitment_cents": 120_000,
             "monthly_rate_micros": 10_000, "amortization_system": "price", "indexer": "none"},
            {"id": 2, "name": "Maior taxa", "currency": "BRL", "remaining_installments": 12,
             "installment_cents": 30_000, "remaining_commitment_cents": 360_000,
             "monthly_rate_micros": 30_000, "amortization_system": "price", "indexer": "none"},
        ]
        avalanche = project_payoff_strategy(loans, "avalanche", 10_000)
        snowball = project_payoff_strategy(loans, "snowball", 10_000)
        self.assertEqual(avalanche["priority_order"], [2, 1])
        self.assertEqual(snowball["priority_order"], [1, 2])
        self.assertLessEqual(avalanche["months"], avalanche["baseline_months"])
        self.assertLessEqual(snowball["months"], snowball["baseline_months"])

    def test_revolving_debts_are_prioritized_before_scheduled_loans(self) -> None:
        loan = {"id": 7, "name": "Financiamento", "currency": "BRL", "remaining_installments": 8,
                "installment_cents": 20_000, "remaining_commitment_cents": 160_000,
                "monthly_rate_micros": 10_000, "amortization_system": "price", "indexer": "none"}
        revolving = {"id": 7, "name": "Cheque especial", "currency": "BRL", "status": "active",
                     "balance_cents": 80_000, "balance_date": date.today().isoformat(),
                     "rate_micros": 100_000, "rate_period": "monthly", "capitalization": "daily"}
        result = project_payoff_strategy([loan], "avalanche", 30_000, revolving_loans=[revolving])
        self.assertEqual(result["priority_order"][0], {"kind": "revolving", "id": 7, "name": "Cheque especial"})
        self.assertGreater(result["interest_cents"], 0)
        self.assertLess(result["months"], 1200)
        self.assertIsNone(result["baseline_months"])
        self.assertIsNone(result["months_saved"])

    def test_strategy_rejects_mixed_currencies(self) -> None:
        loans = [
            {"id": 1, "currency": "BRL", "remaining_installments": 1, "installment_cents": 10_000,
             "remaining_commitment_cents": 10_000, "monthly_rate_micros": 0, "indexer": "none"},
            {"id": 2, "currency": "USD", "remaining_installments": 1, "installment_cents": 10_000,
             "remaining_commitment_cents": 10_000, "monthly_rate_micros": 0, "indexer": "none"},
        ]
        with self.assertRaises(LoanError):
            project_payoff_strategy(loans, "avalanche", 0)

    def test_contract_validation_requires_indexed_principal_date_and_remuneratory_rate(self) -> None:
        with self.assertRaises(LoanError):
            create_loan(self.user["id"], self.loan_payload(indexer="IPCA"))

    def test_contract_can_be_created_updated_and_archived(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload())
        changed = update_loan(self.user["id"], loan["id"], self.loan_payload(name="Contrato revisado"))
        self.assertEqual(changed["name"], "Contrato revisado")
        archive_loan(self.user["id"], loan["id"])
        self.assertEqual(list_loans(self.user["id"]), [])

    def test_archived_contract_is_available_only_in_history_and_keeps_linked_payment(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload())
        account = create_checking_account(self.user["id"], {
            "name": "Conta corrente", "bank_name": "Banco", "currency": "BRL", "initial_balance": "5000,00",
        })
        transaction = create_transaction(self.user["id"], {
            "type": "expense", "description": "Parcela preservada", "amount": "1.066,19",
            "date": "2026-10-10", "account_id": str(account["id"]),
            "category": "Empréstimos e Financiamentos", "loan_id": loan["id"],
        })
        set_transaction_reconciled(self.user["id"], str(transaction["id"]), True)
        archive_loan(self.user["id"], loan["id"])

        self.assertEqual(list_loans(self.user["id"]), [])
        archived = list_loans(self.user["id"], include_archived=True)
        self.assertEqual(len(archived), 1)
        self.assertIsNotNone(archived[0]["archived_at"])
        self.assertEqual(archived[0]["total_paid_cents"], 106_619)
        self.assertEqual(archived[0]["payments"][0]["id"], transaction["id"])

    def test_fully_paid_contract_is_returned_for_history(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload())
        with get_connection() as conn:
            conn.execute("UPDATE loans SET remaining_installments=0, remaining_commitment_cents=0 WHERE id=?", (loan["id"],))

        listed = list_loans(self.user["id"])
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["remaining_installments"], 0)

    def test_payment_is_pending_until_reconciliation_and_recognized_once(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload())
        account = create_checking_account(self.user["id"], {
            "name": "Conta corrente", "bank_name": "Banco", "currency": "BRL", "initial_balance": "5000,00",
        })
        transaction = create_transaction(self.user["id"], {
            "type": "expense", "description": "Parcela financiamento", "amount": "1.066,19",
            "date": "2026-10-10", "account_id": str(account["id"]),
            "category": "Empréstimos e Financiamentos", "loan_id": loan["id"],
        })
        self.assertEqual(len(list_loans(self.user["id"])[0]["pending_payments"]), 1)
        self.assertEqual(list_loans(self.user["id"])[0]["remaining_installments"], 12)
        set_transaction_reconciled(self.user["id"], str(transaction["id"]), True)
        set_transaction_reconciled(self.user["id"], str(transaction["id"]), True)
        refreshed = list_loans(self.user["id"])[0]
        self.assertEqual(refreshed["remaining_installments"], 11)
        self.assertEqual(refreshed["paid_installments"], 1)
        self.assertEqual(refreshed["total_paid_cents"], 106_619)

    def test_payment_link_rejects_wrong_currency(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload(currency="USD"))
        account = create_checking_account(self.user["id"], {
            "name": "Conta BRL", "bank_name": "Banco", "currency": "BRL", "initial_balance": "1000,00",
        })
        transaction = create_transaction(self.user["id"], {
            "type": "expense", "description": "Parcela", "amount": "100,00", "date": "2026-10-10",
            "account_id": str(account["id"]), "category": "Empréstimos e Financiamentos",
        })
        with self.assertRaises(LoanError):
            link_payment(self.user["id"], loan["id"], transaction["id"])

    def test_deleting_contract_removes_link_but_preserves_original_transaction(self) -> None:
        loan = create_loan(self.user["id"], self.loan_payload())
        account = create_checking_account(self.user["id"], {
            "name": "Conta corrente", "bank_name": "Banco", "currency": "BRL", "initial_balance": "5000,00",
        })
        transaction = create_transaction(self.user["id"], {
            "type": "expense", "description": "Parcela preservada", "amount": "1.066,19",
            "date": "2026-10-10", "account_id": str(account["id"]),
            "category": "Empréstimos e Financiamentos", "loan_id": loan["id"],
        })
        with database.get_connection() as conn:
            balance_before = conn.execute("SELECT current_balance_cents FROM checking_accounts WHERE id=?", (account["id"],)).fetchone()["current_balance_cents"]
        delete_loan(self.user["id"], loan["id"])
        with database.get_connection() as conn:
            transaction_row = conn.execute("SELECT amount_cents, description FROM transactions WHERE id=?", (transaction["id"],)).fetchone()
            link_count = conn.execute("SELECT COUNT(*) FROM loan_payment_links WHERE transaction_id=?", (transaction["id"],)).fetchone()[0]
            balance_after = conn.execute("SELECT current_balance_cents FROM checking_accounts WHERE id=?", (account["id"],)).fetchone()["current_balance_cents"]
        self.assertEqual(transaction_row["description"], "Parcela preservada")
        self.assertEqual(transaction_row["amount_cents"], 106_619)
        self.assertEqual(link_count, 0)
        self.assertEqual(balance_after, balance_before)


if __name__ == "__main__":
    unittest.main()
