export function parseDecimalInput(value) {
  const normalized = String(value || "").replace(/\./g, "").replace(",", ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
}

export function formatMoney(value, currency) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return formatMoney(0, currency);
  }
  const amount = Math.abs(parsed) < 0.005 ? 0 : parsed;
  return amount.toLocaleString("pt-BR", { style: "currency", currency });
}

export function formatCurrencySummary(totals) {
  if (!totals.size) {
    return formatMoney(0, "BRL");
  }
  return [...totals.entries()].map(([currency, amount]) => formatMoney(amount, currency)).join(" · ");
}

export function formatDecimal(value, maximumFractionDigits = 2) {
  return Number(value || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  });
}

export function moneyInputValue(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "0,00";
  }
  return parsed.toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

export function formatPercent(value) {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return "0,0%";
  }
  return parsed.toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 1 });
}

export function portfolioQuoteText(position) {
  if (position.asset_type === "fixed_income") {
    return "-";
  }
  if (!position.quote) {
    return "-";
  }
  const quote = Number(position.quote);
  if (!Number.isFinite(quote)) {
    return "-";
  }
  return formatMoney(quote, position.currency);
}
