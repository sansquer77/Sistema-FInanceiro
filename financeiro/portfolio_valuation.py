"""Valorização por data, juros, impostos e aniversários; sem SQL ou transporte HTTP."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP

from financeiro.calendar_rules import add_months
from financeiro.portfolio_positions import aggregate_savings_anniversaries


class PositionValuation:
    """Serviço sem estado de carteira; dependências definidas na composição."""

    def __init__(
        self, *, today, error_type, fetch_accumulated_indexer_factor,
        fetch_indexer_rate, value_to_brl, fallback_indexer_annual_rate,
        parse_rate_decimal, format_decimal_percent,
    ):
        self.today = today
        self.error_type = error_type
        self.fetch_accumulated_indexer_factor = fetch_accumulated_indexer_factor
        self.fetch_indexer_rate = fetch_indexer_rate
        self.value_to_brl = value_to_brl
        self.fallback_indexer_annual_rate = fallback_indexer_annual_rate
        self.parse_rate_decimal = parse_rate_decimal
        self.format_decimal_percent = format_decimal_percent

    def apply_fixed_income_value(self, position: dict, force_refresh: bool = False) -> None:
        today = self.today()
        factor_cache: dict[str, Decimal] = {}
        net_cents, gross_cents, iof_tax_cents, income_tax_cents, custody_fee_cents, rate_factor, source = self.fixed_income_value_as_of(
            position, today, force_refresh=force_refresh, factor_cache=factor_cache
        )
        mode = position["fixed_income_mode"] or "post"
        indexer = position["fixed_income_indexer"] or "CDI"
        annual_rate = self.parse_rate_decimal(position.get("fixed_income_rate"))
        position["quote"] = self.fixed_income_quote_label(mode, indexer, annual_rate, rate_factor)
        position["quote_source"] = source
        position["quote_status"] = "ok"
        position["quote_date"] = self.today().isoformat()
        position["current_value_cents"] = net_cents
        position["current_value_brl_cents"] = self.value_to_brl(position["current_value_cents"], position["currency"])
        position["fixed_income_gross_value_cents"] = gross_cents
        position["fixed_income_iof_tax_cents"] = iof_tax_cents
        position["fixed_income_income_tax_cents"] = income_tax_cents
        position["fixed_income_custody_fee_cents"] = custody_fee_cents
        position["fixed_income_net_value_cents"] = net_cents
        position["day_result_cents"] = self.day_variation_cents(
            position,
            net_cents,
            today,
            lambda pos, as_of, refresh, cache: self.fixed_income_value_as_of(pos, as_of, force_refresh=refresh, factor_cache=cache)[0],
            force_refresh=force_refresh,
            factor_cache=factor_cache,
        )
        position["day_result_brl_cents"] = self.value_to_brl(position["day_result_cents"], position["currency"])

    def day_variation_cents(
        self,
        position: dict,
        current_value_cents: int,
        as_of_date: date,
        value_provider: object,
        force_refresh: bool = False,
        factor_cache: dict[str, Decimal] | None = None,
    ) -> int:
        # spec: investimentos/investimentos-portfolio v2.52 — criterios 43 a 45
        # (variacao do dia = valor hoje menos valor no dia anterior, com a base de
        #  comparacao limitada a data de aquisicao: no dia da aquisicao a variacao
        #  exibida e zero. Para pos-fixados, dias sem taxa publicada (fim de
        #  semana/feriado) naturalmente produzem variacao zero no indexador)
        baseline_date = date.fromisoformat(position["first_operation_date"])
        if as_of_date <= baseline_date:
            return 0
        previous_date = as_of_date - timedelta(days=1)
        if previous_date < baseline_date:
            previous_date = baseline_date
        previous_value = int(value_provider(position, previous_date, force_refresh, factor_cache))
        return current_value_cents - previous_value

    def fixed_income_value_as_of(
        self,
        position: dict,
        as_of_date: date,
        force_refresh: bool = False,
        factor_cache: dict[str, Decimal] | None = None,
    ) -> tuple[int, int, int, int, int, Decimal, str]:
        start_date = date.fromisoformat(position["first_operation_date"])
        if as_of_date < start_date:
            return 0, 0, 0, 0, 0, Decimal("0"), "Taxa cadastrada"
        maturity_date = self.parse_optional_iso_date(position.get("fixed_income_maturity_date"))
        end_date = min(as_of_date, maturity_date) if maturity_date else as_of_date
        days = max((end_date - start_date).days, 0)
        annual_rate = self.parse_rate_decimal(position.get("fixed_income_rate"))
        mode = position["fixed_income_mode"] or "post"
        indexer = position["fixed_income_indexer"] or "CDI"
        rate_factor = Decimal("0")
        gross_factor = Decimal("1")
        source = "Taxa cadastrada"
        try:
            if mode == "pre":
                rate_factor = annual_rate / Decimal("100")
                gross_factor = self.compound_annual_factor(rate_factor, days)
            else:
                multiplier = annual_rate / Decimal("100") if annual_rate else Decimal("1")
                if factor_cache is not None:
                    indexer_factor = self._accumulated_factor_by_month(
                        indexer, start_date, end_date, multiplier, factor_cache, force_refresh=force_refresh
                    )
                else:
                    indexer_factor = self.fetch_accumulated_indexer_factor(indexer, start_date, end_date, multiplier, force_refresh=force_refresh)
                source = f"Banco Central SGS ({indexer} acumulado)"
                if mode == "hybrid":
                    if factor_cache is not None:
                        indexer_factor_plain = self._accumulated_factor_by_month(
                            indexer, start_date, end_date, Decimal("1"), factor_cache, force_refresh=force_refresh
                        )
                    else:
                        indexer_factor_plain = self.fetch_accumulated_indexer_factor(indexer, start_date, end_date, force_refresh=force_refresh)
                    rate_factor = indexer_factor_plain - Decimal("1") + annual_rate / Decimal("100")
                    gross_factor = indexer_factor_plain * self.compound_annual_factor(annual_rate / Decimal("100"), days)
                else:
                    rate_factor = indexer_factor - Decimal("1")
                    gross_factor = indexer_factor
        except self.error_type:
            if mode == "pre":
                rate_factor = annual_rate / Decimal("100")
                gross_factor = self.compound_annual_factor(rate_factor, days)
            else:
                fallback_indexer_rate = self.fallback_indexer_annual_rate(indexer)
                multiplier = annual_rate / Decimal("100") if annual_rate else Decimal("1")
                fallback_indexer_factor = self.compound_annual_factor(fallback_indexer_rate * multiplier, days)
                source = f"Estimativa local ({indexer}); Banco Central indisponivel"
                if mode == "hybrid":
                    fallback_indexer_factor = self.compound_annual_factor(fallback_indexer_rate, days)
                    rate_factor = fallback_indexer_factor - Decimal("1") + annual_rate / Decimal("100")
                    gross_factor = fallback_indexer_factor * self.compound_annual_factor(annual_rate / Decimal("100"), days)
                else:
                    rate_factor = fallback_indexer_factor - Decimal("1")
                    gross_factor = fallback_indexer_factor
        gross = Decimal(position["total_cost_cents"]) * gross_factor
        gross_cents = int(gross.quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        iof_tax_cents = 0
        income_tax_cents = 0
        custody_fee_cents = self.fixed_income_custody_fee_cents(position, gross_cents, days)
        net_cents = gross_cents
        if self.should_apply_fixed_income_taxes(position):
            gross_profit_cents = max(gross_cents - position["total_cost_cents"], 0)
            iof_tax_cents = self.fixed_income_iof_tax_cents(gross_profit_cents, days)
            income_tax_cents = self.fixed_income_income_tax_cents(max(gross_profit_cents - iof_tax_cents, 0), days)
            net_cents = max(gross_cents - iof_tax_cents - income_tax_cents - custody_fee_cents, 0)
        return net_cents, gross_cents, iof_tax_cents, income_tax_cents, custody_fee_cents, rate_factor, source

    def _position_value_native_as_of(
        self,
        position: dict,
        as_of_date: date,
        force_refresh: bool = False,
        factor_cache: dict[str, Decimal] | None = None,
    ) -> int:
        # spec: rentabilidade-portfolio v1.8 — critério 4
        if as_of_date < date.fromisoformat(position["first_operation_date"]):
            return 0
        if position["asset_type"] == "fixed_income":
            return self.fixed_income_value_as_of(position, as_of_date, force_refresh=force_refresh, factor_cache=factor_cache)[0]
        if position["asset_type"] == "savings":
            return self.savings_value_as_of(position, as_of_date, force_refresh=force_refresh, factor_cache=factor_cache)
        return int(position.get("current_value_cents") or 0)

    def _accumulated_factor_by_month(
        self,
        indexer: str,
        start_date: date,
        end_date: date,
        multiplier: Decimal,
        month_cache: dict[str, Decimal],
        force_refresh: bool = False,
    ) -> Decimal:
        # Decomposicao exata do fator acumulado em fatores mensais com cache
        # compartilhado: evita N x 12 requisicoes BCB distintas no cache frio.
        # Para indexadores diarios o produto por dia e associativo; para indexadores
        # mensais (IPCA/IGP-M) o peso de overlap por mes se preserva na divisao
        # em limites de mes. Fallback de payload vazio tambem e decomponivel
        # (juros compostos somam expoentes), mantendo resultado identico.
        if end_date < start_date:
            return Decimal("1")
        factor = Decimal("1")
        month = date(start_date.year, start_date.month, 1)
        last_month = date(end_date.year, end_date.month, 1)
        while month <= last_month:
            segment_start = max(month, start_date)
            segment_end = min(add_months(month, 1) - timedelta(days=1), end_date)
            cache_key = f"{indexer}:{multiplier}:{segment_start.isoformat()}:{segment_end.isoformat()}"
            if cache_key not in month_cache:
                month_cache[cache_key] = self.fetch_accumulated_indexer_factor(
                    indexer, segment_start, segment_end, multiplier, force_refresh=force_refresh
                )
            factor *= month_cache[cache_key]
            month = add_months(month, 1)
        return factor

    def apply_savings_value(self, position: dict, force_refresh: bool = False) -> None:
        today = self.today()
        factor_cache: dict[str, Decimal] = {}
        current_cents, additional_monthly_rate, source, status = self.savings_value_as_of_with_meta(
            position, today, force_refresh=force_refresh, factor_cache=factor_cache
        )
        position["quote"] = self.savings_quote_label(additional_monthly_rate)
        position["quote_source"] = source
        position["quote_status"] = status
        position["quote_date"] = today.isoformat()
        position["current_value_cents"] = current_cents
        position["current_value_brl_cents"] = self.value_to_brl(current_cents, position["currency"])
        position["fixed_income_gross_value_cents"] = current_cents
        position["fixed_income_iof_tax_cents"] = 0
        position["fixed_income_income_tax_cents"] = 0
        position["fixed_income_custody_fee_cents"] = 0
        position["fixed_income_net_value_cents"] = current_cents
        position["day_result_cents"] = self.day_variation_cents(
            position,
            current_cents,
            today,
            lambda pos, as_of, refresh, cache: self.savings_value_as_of(pos, as_of, force_refresh=refresh, factor_cache=cache),
            force_refresh=force_refresh,
            factor_cache=factor_cache,
        )
        position["day_result_brl_cents"] = self.value_to_brl(position["day_result_cents"], position["currency"])

    def savings_value_as_of_with_meta(
        self,
        position: dict,
        as_of_date: date,
        force_refresh: bool = False,
        factor_cache: dict[str, Decimal] | None = None,
    ) -> tuple[int, Decimal, str, str]:
        anniversaries = aggregate_savings_anniversaries(position.get("savings_anniversaries") or [])
        if not anniversaries:
            anniversaries = [{"date": position["first_operation_date"], "amount_cents": position["total_cost_cents"]}]
        current_value = Decimal("0")
        source = "Banco Central SGS (TR/SELIC); aniversarios mensais"
        status = "ok"
        additional_monthly_rate = Decimal("0")
        try:
            additional_monthly_rate = self.savings_additional_monthly_rate(force_refresh=force_refresh)
            for anniversary in anniversaries:
                start_date = self.parse_optional_iso_date(anniversary.get("date"))
                amount_cents = int(anniversary.get("amount_cents") or 0)
                if not start_date or amount_cents <= 0 or as_of_date < start_date:
                    continue
                current_value += Decimal(amount_cents) * self.savings_factor_for_anniversary(
                    start_date,
                    as_of_date,
                    additional_monthly_rate,
                    force_refresh=force_refresh,
                    factor_cache=factor_cache,
                )
        except self.error_type as exc:
            status = exc.message
            source = "Estimativa local; Banco Central indisponivel"
            fallback_rate = self.fallback_indexer_annual_rate("SELIC")
            additional_monthly_rate = self.savings_additional_monthly_rate_from_selic(fallback_rate)
            for anniversary in anniversaries:
                start_date = self.parse_optional_iso_date(anniversary.get("date"))
                amount_cents = int(anniversary.get("amount_cents") or 0)
                if not start_date or amount_cents <= 0 or as_of_date < start_date:
                    continue
                completed_months = self.completed_savings_anniversaries(start_date, as_of_date)
                current_value += Decimal(amount_cents) * ((Decimal("1") + additional_monthly_rate) ** completed_months)
        return int(current_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)), additional_monthly_rate, source, status

    def savings_value_as_of(
        self,
        position: dict,
        as_of_date: date,
        force_refresh: bool = False,
        factor_cache: dict[str, Decimal] | None = None,
    ) -> int:
        return self.savings_value_as_of_with_meta(position, as_of_date, force_refresh=force_refresh, factor_cache=factor_cache)[0]

    def savings_factor_for_anniversary(
        self,
        start_date: date,
        end_date: date,
        additional_monthly_rate: Decimal,
        force_refresh: bool = False,
        factor_cache: dict[str, Decimal] | None = None,
    ) -> Decimal:
        factor = Decimal("1")
        completed_months = self.completed_savings_anniversaries(start_date, end_date)
        for month_index in range(1, completed_months + 1):
            period_start = add_months(start_date, month_index - 1)
            period_end = add_months(start_date, month_index)
            if factor_cache is not None:
                tr_factor = self._accumulated_factor_by_month(
                    "TR", period_start, period_end, Decimal("1"), factor_cache, force_refresh=force_refresh
                )
            else:
                tr_factor = self.fetch_accumulated_indexer_factor("TR", period_start, period_end, force_refresh=force_refresh)
            factor *= tr_factor * (Decimal("1") + additional_monthly_rate)
        return factor

    def completed_savings_anniversaries(self, start_date: date, end_date: date) -> int:
        if end_date < add_months(start_date, 1):
            return 0
        completed = 0
        while add_months(start_date, completed + 1) <= end_date:
            completed += 1
        return completed

    def savings_additional_monthly_rate(self, force_refresh: bool = False) -> Decimal:
        selic_annual = self.fetch_indexer_rate("SELIC", force_refresh=force_refresh)
        return self.savings_additional_monthly_rate_from_selic(selic_annual)

    def savings_additional_monthly_rate_from_selic(self, selic_annual: Decimal) -> Decimal:
        # spec: investimentos-portfolio v2.52 — secao "Regras > Poupanca"
        # (TR + 0,5% a.m. quando Selic > 8,5% a.a.; TR + 70% da Selic equivalente
        #  mensal quando Selic <= 8,5% a.a. — limiar e formula nao sao obvios)
        if selic_annual > Decimal("0.085"):
            return Decimal("0.005")
        return (Decimal("1") + selic_annual * Decimal("0.70")) ** (Decimal("1") / Decimal("12")) - Decimal("1")

    def savings_quote_label(self, additional_monthly_rate: Decimal) -> str:
        return f"TR + {self.format_decimal_percent(additional_monthly_rate * Decimal('100'))}% a.m."

    def parse_optional_iso_date(self, value: object) -> date | None:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            return date.fromisoformat(raw)
        except ValueError:
            return None

    def compound_annual_factor(self, rate: Decimal, days: int) -> Decimal:
        if not rate or days <= 0:
            return Decimal("1")
        return (Decimal("1") + rate) ** (Decimal(days) / Decimal("365"))

    def fixed_income_quote_label(self, mode: str, indexer: str, annual_rate: Decimal, rate_factor: Decimal) -> str:
        if mode == "pre":
            return f"{self.format_decimal_percent(annual_rate)}% a.a."
        if mode == "hybrid":
            return f"{indexer} + {self.format_decimal_percent(annual_rate)}% a.a."
        if annual_rate:
            return f"{self.format_decimal_percent(annual_rate)}% do {indexer}"
        return f"{self.format_decimal_percent(rate_factor * Decimal('100'))}% acumulado"

    def should_apply_fixed_income_taxes(self, position: dict) -> bool:
        return position["source_type"] == "operation" or (
            position["source_type"] == "opening" and bool(position.get("apply_tax_estimate"))
        )

    def fixed_income_income_tax_cents(self, gross_profit_cents: int, days: int) -> int:
        # spec: investimentos-portfolio v2.52 — criterio 3 (secao "Regras > Renda Fixa":
        # tabela regressiva de IR, 22,5% a 15% conforme dias corridos desde a aquisicao)
        if gross_profit_cents <= 0:
            return 0
        if days <= 180:
            tax_rate = Decimal("0.225")
        elif days <= 360:
            tax_rate = Decimal("0.20")
        elif days <= 720:
            tax_rate = Decimal("0.175")
        else:
            tax_rate = Decimal("0.15")
        return int((Decimal(gross_profit_cents) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def fixed_income_custody_fee_cents(self, position: dict, gross_cents: int, days: int) -> int:
        # spec: investimentos/investimentos-portfolio v2.52 — critério 25
        # Tesouro Direto tem taxa B3 de custodia provisionada diariamente. O app
        # estima a taxa na curva, sem tentar reproduzir marcacao a mercado oficial.
        if gross_cents <= 0 or days <= 0 or not self.is_treasury_direct_position(position):
            return 0
        treasury_name = self.treasury_position_name(position)
        if "RENDA+" in treasury_name or "RENDA +" in treasury_name or "EDUCA+" in treasury_name or "EDUCA +" in treasury_name:
            return 0
        fee_base_cents = gross_cents
        if "SELIC" in treasury_name:
            fee_base_cents = max(gross_cents - 1_000_000, 0)
        if fee_base_cents <= 0:
            return 0
        return int((Decimal(fee_base_cents) * Decimal("0.002") * Decimal(days) / Decimal("365")).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def is_treasury_direct_position(self, position: dict) -> bool:
        name = self.treasury_position_name(position)
        return "TESOURO" in name

    def treasury_position_name(self, position: dict) -> str:
        return " ".join([
            str(position.get("asset_identifier") or ""),
            str(position.get("asset_name") or ""),
        ]).upper()

    def fixed_income_iof_tax_cents(self, gross_profit_cents: int, days: int) -> int:
        # spec: investimentos-portfolio v2.52 — criterio 3 (secao "Regras > Renda Fixa":
        # IOF regressivo so incide ate 30 dias corridos desde a aquisicao)
        if gross_profit_cents <= 0 or days >= 30:
            return 0
        daily_rates = {
            0: Decimal("1"),
            1: Decimal("0.96"),
            2: Decimal("0.93"),
            3: Decimal("0.90"),
            4: Decimal("0.86"),
            5: Decimal("0.83"),
            6: Decimal("0.80"),
            7: Decimal("0.76"),
            8: Decimal("0.73"),
            9: Decimal("0.70"),
            10: Decimal("0.66"),
            11: Decimal("0.63"),
            12: Decimal("0.60"),
            13: Decimal("0.56"),
            14: Decimal("0.53"),
            15: Decimal("0.50"),
            16: Decimal("0.46"),
            17: Decimal("0.43"),
            18: Decimal("0.40"),
            19: Decimal("0.36"),
            20: Decimal("0.33"),
            21: Decimal("0.30"),
            22: Decimal("0.26"),
            23: Decimal("0.23"),
            24: Decimal("0.20"),
            25: Decimal("0.16"),
            26: Decimal("0.13"),
            27: Decimal("0.10"),
            28: Decimal("0.06"),
            29: Decimal("0.03"),
        }
        tax_rate = daily_rates.get(max(days, 0), Decimal("0"))
        return int((Decimal(gross_profit_cents) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def apply_cost_value(self, position: dict, status: str) -> None:
        position["current_value_cents"] = position["total_cost_cents"]
        position["current_value_brl_cents"] = position["total_cost_brl_cents"]
        position["day_result_cents"] = 0
        position["day_result_brl_cents"] = 0
        position["quote_status"] = status
