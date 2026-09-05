"""Séries mensais por moeda e benchmarks; reutiliza a valorização por data."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from financeiro.calendar_rules import add_months


class PortfolioReturns:
    """Serviço sem estado de carteira; dependências definidas na composição."""

    def __init__(
        self, *, today, error_type, get_portfolio, _position_value_native_as_of,
        fetch_accumulated_indexer_factor, fetch_indexer_rate, compound_annual_factor,
        list_snapshots=None,
    ):
        self.today = today
        self.error_type = error_type
        self.get_portfolio = get_portfolio
        self._position_value_native_as_of = _position_value_native_as_of
        self.fetch_accumulated_indexer_factor = fetch_accumulated_indexer_factor
        self.fetch_indexer_rate = fetch_indexer_rate
        self.compound_annual_factor = compound_annual_factor
        self.list_snapshots = list_snapshots

    def _monthly_return_pct(self, prev_value: int, end_value: int, net_contribution: int) -> Decimal:
        denominator = max(prev_value + max(net_contribution, 0), 1)
        return (Decimal(end_value - prev_value - net_contribution) * Decimal("100")) / Decimal(denominator)

    def get_portfolio_returns(self, user_id: int, force_refresh: bool = False, positions: list[dict] | None = None) -> dict:
        # spec: rentabilidade-portfolio v2.9 — critérios 1 a 10
        # Rentabilidade mensal (em percentual) por moeda consolidada (BRL e USD),
        # comparada ao CDI e ao IPCA do mês. Últimos 12 meses, ou todos os meses
        # disponíveis quando a base é menor. Cada moeda é calculada na própria
        # moeda (valores nativos), sem efeito de câmbio na série.
        try:
            if positions is None:
                portfolio = self.get_portfolio(user_id, force_refresh=force_refresh)
                positions = portfolio.get("positions") or []
            if not positions:
                return {
                    "series": [], "start_month": None, "end_month": None,
                    "has_historical_approximation": False,
                    "snapshot_coverage": {"observed_months": [], "approximate_months": [], "future_months": [], "coverage_percent": 0.0},
                    "error": None,
                }

            today = self.today()
            # A janela é sempre o ano civil corrente. Meses futuros permanecem
            # no eixo para evitar que a escala mude durante o ano; eles recebem
            # zero até haver dados observáveis.
            start_month = date(today.year, 1, 1)
            end_month = date(today.year, 12, 1)

            months = []
            current = start_month
            while current <= end_month:
                months.append(current)
                current = add_months(current, 1)

            currency_order = []
            seen = set()
            for position in positions:
                currency = str(position.get("currency") or "BRL").upper()
                if currency not in seen:
                    seen.add(currency)
                    currency_order.append(currency)

            series: list[dict] = []
            prev_by_currency: dict[str, int] = {}
            prev_invested_by_currency: dict[str, int] = {}
            month_factor_cache: dict[str, Decimal] = {}
            ipca_month_cache: dict[str, float] = {}
            position_factor_cache: dict[str, Decimal] = {}
            snapshot_by_month: dict[str, list[dict]] = {}
            if self.list_snapshots:
                for snapshot in self.list_snapshots(user_id):
                    snapshot_by_month.setdefault(snapshot["snapshot_month"], []).append(snapshot)
            observed_months: list[str] = []
            approximate_months: list[str] = []
            future_months: list[str] = []

            for month_date in months:
                month_start = month_date
                month_end = add_months(month_date, 1) - timedelta(days=1)
                if month_start > date(today.year, today.month, 1):
                    future_months.append(month_date.strftime("%Y-%m"))
                    series.append({
                        "month": month_date.strftime("%Y-%m"),
                        "cdi_return_pct": 0.0,
                        "ipca_return_pct": 0.0,
                        **{f"{currency}_return_pct": 0.0 for currency in currency_order},
                    })
                    continue
                as_of = min(month_end, today)

                month_values: dict[str, int] = {}
                month_invested: dict[str, int] = {}
                month_snapshot_flow: dict[str, int] = {}
                snapshot_rows = snapshot_by_month.get(month_date.strftime("%Y-%m"), [])
                if snapshot_rows:
                    if all(snapshot.get("valuation_status") == "observed" for snapshot in snapshot_rows):
                        observed_months.append(month_date.strftime("%Y-%m"))
                    else:
                        approximate_months.append(month_date.strftime("%Y-%m"))
                    for snapshot in snapshot_rows:
                        currency = str(snapshot.get("currency") or "BRL").upper()
                        month_values[currency] = month_values.get(currency, 0) + int(snapshot.get("market_value_cents") or 0)
                        month_invested[currency] = month_invested.get(currency, 0) + int(snapshot.get("cost_basis_cents") or 0)
                        month_snapshot_flow[currency] = month_snapshot_flow.get(currency, 0) + (
                            int(snapshot.get("contribution_cents") or 0)
                            - int(snapshot.get("redemption_cents") or 0)
                            - int(snapshot.get("dividend_cents") or 0)
                        )
                for position in positions:
                    if snapshot_rows:
                        continue
                    currency = str(position.get("currency") or "BRL").upper()
                    first_operation = date.fromisoformat(position["first_operation_date"])
                    if as_of < first_operation:
                        continue
                    # Posicao que entrou neste mês: conta pelo custo (baseline),
                    # sem retorno sintético de entrada; meses seguintes valorizam.
                    if month_start <= first_operation <= month_end:
                        value = int(position.get("total_cost_cents") or 0)
                    else:
                        value = self._position_value_native_as_of(
                            position, as_of, force_refresh=force_refresh, factor_cache=position_factor_cache
                        )
                    month_values[currency] = month_values.get(currency, 0) + value
                    month_invested[currency] = month_invested.get(currency, 0) + int(position.get("total_cost_cents") or 0)

                month_key = month_date.strftime("%Y-%m")
                cdi_return = (Decimal(str(self._cdi_factor_for_month(month_date, as_of, month_factor_cache, force_refresh=force_refresh))) - Decimal("1")) * Decimal("100")
                ipca_factor = self._ipca_factor_for_month(month_date, as_of, ipca_month_cache, force_refresh=force_refresh)
                ipca_return = (Decimal(str(ipca_factor)) - Decimal("1")) * Decimal("100")

                entry: dict[str, object] = {
                    "month": month_key,
                    "cdi_return_pct": float(cdi_return.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                    "ipca_return_pct": float(ipca_return.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)),
                }

                for currency in currency_order:
                    value = month_values.get(currency, 0)
                    invested = month_invested.get(currency, 0)
                    prev_value = prev_by_currency.get(currency)
                    if prev_value is not None:
                        if prev_value <= 0:
                            portfolio_return = Decimal("0")
                        else:
                            net_contribution = (
                                month_snapshot_flow.get(currency, 0)
                                if snapshot_rows
                                else invested - prev_invested_by_currency.get(currency, 0)
                            )
                            portfolio_return = self._monthly_return_pct(prev_value, value, net_contribution)
                    else:
                        portfolio_return = Decimal("0")
                    entry[f"{currency}_return_pct"] = float(portfolio_return.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP))
                    prev_by_currency[currency] = value
                    prev_invested_by_currency[currency] = invested

                if not snapshot_rows:
                    approximate_months.append(month_date.strftime("%Y-%m"))

                series.append(entry)

            has_approximation = bool(approximate_months)
            elapsed_month_count = len(observed_months) + len(approximate_months)

            return {
                "series": series,
                "start_month": start_month.strftime("%Y-%m"),
                "end_month": end_month.strftime("%Y-%m"),
                "has_historical_approximation": has_approximation,
                "snapshot_coverage": {
                    "observed_months": observed_months,
                    "approximate_months": approximate_months,
                    "future_months": future_months,
                    "coverage_percent": round((len(observed_months) / elapsed_month_count) * 100, 2) if elapsed_month_count else 0.0,
                },
                "error": None,
            }
        except Exception as exc:
            print(f"[portfolio-returns-error] user={user_id}: {exc}")
            return {
                "series": [], "start_month": None, "end_month": None,
                "has_historical_approximation": False,
                "snapshot_coverage": {"observed_months": [], "approximate_months": [], "future_months": [], "coverage_percent": 0.0},
                "error": str(exc),
            }

    def _cdi_factor_for_period(self, start_date: date, end_date: date, force_refresh: bool = False) -> Decimal:
        if end_date < start_date:
            return Decimal("1")
        try:
            return self.fetch_accumulated_indexer_factor("CDI", start_date, end_date, force_refresh=force_refresh)
        except self.error_type:
            try:
                latest_rate = self.fetch_indexer_rate("CDI", force_refresh=force_refresh)
                return self.compound_annual_factor(latest_rate, max((end_date - start_date).days, 0))
            except self.error_type:
                return Decimal("1")

    def _cdi_factor_for_month(self, month_date: date, as_of: date, cache: dict[str, Decimal] | None = None, force_refresh: bool = False) -> Decimal:
        month_end = min(add_months(month_date, 1) - timedelta(days=1), as_of)
        if month_end < month_date:
            return Decimal("1")
        cache_key = f"{month_date.isoformat()}:{month_end.isoformat()}"
        if cache is not None and cache_key in cache:
            return cache[cache_key]
        try:
            factor = self.fetch_accumulated_indexer_factor("CDI", month_date, month_end, force_refresh=force_refresh)
        except self.error_type:
            try:
                latest_rate = self.fetch_indexer_rate("CDI", force_refresh=force_refresh)
                factor = self.compound_annual_factor(latest_rate, max((month_end - month_date).days, 0))
            except self.error_type:
                factor = Decimal("1")
        if cache is not None:
            cache[cache_key] = factor
        return factor

    def _ipca_factor_for_month(self, month_date: date, as_of: date, cache: dict[str, float] | None = None, force_refresh: bool = False) -> float:
        month_end = min(add_months(month_date, 1) - timedelta(days=1), as_of)
        if month_end < month_date:
            return 1.0
        cache_key = f"{month_date.isoformat()}:{month_end.isoformat()}"
        if cache is not None and cache_key in cache:
            return cache[cache_key]
        try:
            factor = self.fetch_accumulated_indexer_factor("IPCA", month_date, month_end, force_refresh=force_refresh)
        except self.error_type:
            try:
                latest_rate = self.fetch_indexer_rate("IPCA", force_refresh=force_refresh)
                factor = self.compound_annual_factor(latest_rate, max((month_end - month_date).days, 0))
            except self.error_type:
                factor = Decimal("1")
        value = float(factor)
        if cache is not None:
            cache[cache_key] = value
        return value
