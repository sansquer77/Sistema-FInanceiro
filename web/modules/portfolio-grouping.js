// Stable UI identity only; totals and aggregation are computed in Python.
export function assetGroupKey(position) {
  return JSON.stringify([position.account_id, position.currency, position.asset_type, position.asset_name || position.asset_identifier || "Sem nome", position.cnpj || ""]);
}

export function formatQuantity(value, assetType) {
  const precision = ["crypto", "stablecoin"].includes(String(assetType || "").toLowerCase()) ? 8 : 2;
  return Number(value || 0).toLocaleString("pt-BR", { minimumFractionDigits: precision, maximumFractionDigits: precision });
}
