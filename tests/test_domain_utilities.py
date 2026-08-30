from __future__ import annotations

from datetime import date
from decimal import Decimal
import unittest

from financeiro.calendar_rules import add_months, normalize_iso_date, normalize_iso_month, shift_month
from financeiro.identifiers import optional_positive_int_id, positive_int_id
from financeiro.money import cents_to_money, decimal_to_cents, localized_money_to_cents, split_cents
from financeiro.recurrence import add_recurrence


class DomainUtilitiesTest(unittest.TestCase):
    def test_money_uses_half_up_and_preserves_split_total(self) -> None:
        self.assertEqual(decimal_to_cents(Decimal("1.005")), 101)
        self.assertEqual(localized_money_to_cents("1.234,56"), 123456)
        self.assertEqual(cents_to_money(123456), "1234.56")
        parts = split_cents(100, 3)
        self.assertEqual(parts, [34, 33, 33])
        self.assertEqual(sum(parts), 100)

    def test_calendar_clamps_month_end_and_normalizes_iso_values(self) -> None:
        self.assertEqual(add_months(date(2024, 1, 31), 1), date(2024, 2, 29))
        self.assertEqual(shift_month("2025-12", 1), "2026-01")
        self.assertEqual(normalize_iso_date("2026-08-30"), "2026-08-30")
        self.assertEqual(normalize_iso_month("2026-08"), "2026-08")
        with self.assertRaises(ValueError):
            normalize_iso_month("2026-13")

    def test_identifiers_accept_only_positive_integers(self) -> None:
        self.assertEqual(positive_int_id("42"), 42)
        self.assertIsNone(optional_positive_int_id(""))
        for value in (None, "abc", "0", "-1"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                positive_int_id(value)

    def test_recurrence_uses_shared_calendar_rules(self) -> None:
        start = date(2024, 1, 31)
        self.assertEqual(add_recurrence(start, "monthly", 1), date(2024, 2, 29))
        self.assertEqual(add_recurrence(start, "weekly", 2), date(2024, 2, 14))
        with self.assertRaises(ValueError):
            add_recurrence(start, "daily", 1)


if __name__ == "__main__":
    unittest.main()
