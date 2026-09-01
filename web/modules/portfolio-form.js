export function fixedIncomePreview({ mode, indexer, rate, fallbackAsset, parseDecimalInput }) {
  const normalizedRate = Math.max(parseDecimalInput(rate), 0);
  if (!mode) return "Selecione a modalidade para visualizar a regra de rentabilidade.";
  if (mode === "prefixado") return `${normalizedRate.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}% ao ano`;
  if (mode === "indexer_percent") return `${normalizedRate.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}% do ${indexer || fallbackAsset || "indexador"}`;
  if (mode === "indexer_plus") return `${indexer || fallbackAsset || "Indexador"} + ${normalizedRate.toLocaleString("pt-BR", { maximumFractionDigits: 4 })}% ao ano`;
  return "Rentabilidade informada manualmente.";
}

export function redemptionPayload(position) {
  return { account_id: position.account_id, currency: position.currency, asset_type: position.asset_type, asset_identifier: position.asset_identifier || "", asset_name: position.asset_name || "", cnpj: position.cnpj || "", quantity: position.quantity || 0, current_value: position.current_value, redemption_unit_price: position.redemption_unit_price };
}

export function valuePayload(position) {
  return { account_id: position.account_id, asset_type: position.asset_type, asset_identifier: position.asset_identifier || "", asset_name: position.asset_name || "", cnpj: position.cnpj || "", fixed_income_indexer: position.fixed_income_indexer || "", fixed_income_maturity_date: position.fixed_income_maturity_date || "", current_value: position.current_value };
}

export function closePayload(position) {
  return { ...redemptionPayload(position), fixed_income_indexer: position.fixed_income_indexer || "", fixed_income_maturity_date: position.fixed_income_maturity_date || "" };
}

export function savingsAnniversariesInputValue(entries, moneyInputValue) {
  if (!Array.isArray(entries)) return "";
  return entries.map((entry) => `${entry.date || ""}; ${moneyInputValue(entry.amount)}`).filter((line) => !line.startsWith(";")).join("\n");
}

export function decimalInputValue(value) {
  if (value === null || value === undefined || value === "") return "";
  return String(value).replace(".", ",");
}
