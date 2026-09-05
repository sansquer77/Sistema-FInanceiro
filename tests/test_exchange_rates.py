from decimal import Decimal
import unittest
from unittest import mock

from financeiro.exchange_rates import calculate_exchange_preview


class ExchangePreviewTest(unittest.TestCase):
    @mock.patch("financeiro.exchange_rates.get_exchange_rate_to_brl")
    def test_cross_rate_and_destination_amount_are_calculated_in_backend(self, get_rate) -> None:
        get_rate.side_effect = [Decimal("5.000000"), Decimal("6.250000")]
        preview = calculate_exchange_preview("USD", "EUR", "2026-08-31", "100,00")
        self.assertEqual(preview["rate"], "0.800000")
        self.assertEqual(preview["destination_amount"], "80.00")

    def test_manual_transfer_rate_uses_decimal_rounding_without_external_quote(self) -> None:
        preview = calculate_exchange_preview("BRL", "USD", "2026-08-31", "156,26", "0,217126")
        self.assertEqual(preview["rate"], "0.217126")
        self.assertEqual(preview["destination_amount"], "33.93")
