export function allocationRows(rows, goals) {
  const byLabel = new Map(rows.map((row) => [`${row.label}::${row.currency || "BRL"}`, row]));
  for (const goal of goals) {
    if (Number(goal.target_percent || 0) <= 0) continue;
    const usd = goal.asset_type === "stock_usd";
    const exists = usd
      ? byLabel.has("Renda variável::USD")
      : goal.asset_type === "stock"
        ? byLabel.has("Renda variável::BRL")
        : [...byLabel.keys()].some((key) => key.startsWith(`${goal.label}::`));
    if (!exists) {
      const label = usd ? "Renda variável" : goal.label;
      const currency = usd ? "USD" : "BRL";
      byLabel.set(`${label}::${currency}`, { label, currency, count: 0, current_brl: "0.00", chart_current_brl: "0.00", result_brl: "0.00", result_percent: "0.00" });
    }
  }
  return [...byLabel.values()];
}

export function allocationGoalKey(row) {
  if (row.label === "Renda variável" && row.currency === "USD") return "stock_usd";
  return ({
    "Renda variável": "stock", Cripto: "crypto", Stablecoin: "stablecoin", Fundos: "fund",
    "Renda fixa": "fixed_income", "Previdência privada": "private_pension", Poupança: "savings", Outros: "other",
  })[row.label] || row.label;
}

export function totalsByCurrency(rows) {
  const totals = new Map();
  rows.forEach((row) => {
    const currency = row.currency || "BRL";
    totals.set(currency, (totals.get(currency) || 0) + Number(row.current_brl || 0));
  });
  return totals;
}

export function assetGroupKey(position) {
  return JSON.stringify([position.account_id, position.currency, position.asset_type, position.asset_name || position.asset_identifier || "Sem nome", position.cnpj || ""]);
}

export function aggregatePositions(positions, groupKey) {
  const base = { ...positions[0] };
  const sum = (field) => positions.reduce((total, position) => total + Number(position[field] || 0), 0);
  const quantity = sum("quantity");
  const totalCost = sum("total_cost");
  const currentValue = sum("current_value");
  const currentValueBrl = sum("current_value_brl");
  Object.assign(base, {
    quantity,
    average_price: quantity > 0 ? totalCost / quantity : Number(base.average_price || 0),
    invested: sum("invested"), costs: sum("costs"), total_cost: totalCost,
    total_cost_brl: sum("total_cost_brl"), current_value: currentValue, current_value_brl: currentValueBrl,
    current_value_cents: Math.round(currentValue * 100), current_value_brl_cents: Math.round(currentValueBrl * 100),
    day_result: sum("day_result"), day_result_brl: sum("day_result_brl"),
    fixed_income_gross_value: sum("fixed_income_gross_value"), fixed_income_iof_tax: sum("fixed_income_iof_tax"),
    fixed_income_income_tax: sum("fixed_income_income_tax"), fixed_income_net_value: sum("fixed_income_net_value"),
    apply_tax_estimate: positions.every((position) => Boolean(position.apply_tax_estimate)),
    source_type: "aggregate", source_id: null, source_transaction_id: null,
    operations_count: positions.length, portfolio_group_key: groupKey,
  });
  return base;
}
