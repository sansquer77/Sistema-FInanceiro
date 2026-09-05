from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from financeiro.accounts import cents_to_money, money_to_cents
from financeiro.transactions import (
    TransactionError,
    convert_to_brl_cents,
    get_exchange_rate_to_brl,
    parse_exchange_rate,
    rate_to_micros,
)


def calculate_exchange_preview(
    source_currency: str,
    target_currency: str = "BRL",
    transaction_date: str | None = None,
    amount: object | None = None,
    transfer_rate: object | None = None,
) -> dict:
    """Calcula razão cambial e valor convertido com precisão decimal no domínio."""
    source = str(source_currency or "BRL").strip().upper()
    target = str(target_currency or "BRL").strip().upper()
    if str(transfer_rate or "").strip():
        rate = parse_exchange_rate(transfer_rate)
    else:
        source_to_brl = get_exchange_rate_to_brl(source, transaction_date)
        target_to_brl = get_exchange_rate_to_brl(target, transaction_date)
        rate = (source_to_brl / target_to_brl).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
    result = {
        "source_currency": source,
        "target_currency": target,
        "date": transaction_date,
        "rate": f"{rate:.6f}",
    }
    if str(amount or "").strip():
        try:
            amount_cents = money_to_cents(amount)
        except Exception as exc:
            raise TransactionError("Valor invalido para a previa de cambio.") from exc
        destination_cents = convert_to_brl_cents(amount_cents, rate_to_micros(rate))
        result["destination_amount"] = cents_to_money(destination_cents)
    return result
