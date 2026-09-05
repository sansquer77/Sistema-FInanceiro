export function createTransactionInvestmentForm({
  elements,
  api,
  decisionModal,
  normalizeSearch,
  moneyInputValue,
  decimalInputValue,
  formatDate,
}) {
  const {
    transactionForm, transactionType, transactionCategory, transactionSubcategory,
    investmentOperationFields, investmentAmount, investmentFundFields,
    fetchInvestmentFundQuoteButton, investmentFundQuoteHint, investmentFixedFields,
    investmentPricingFields, investmentEmergencyReserveFields, investmentTradingCostFields,
    investmentTaxCostFields, investmentFixedIncomeMode, investmentFixedIncomeIndexer,
    investmentFixedIncomeRateLabel, investmentFixedIncomeRate, investmentFixedIncomePreview,
  } = elements;

  fetchInvestmentFundQuoteButton?.addEventListener("click", fetchFundQuote);
  investmentFixedIncomeMode.addEventListener("change", syncFixedIncomeRateHint);
  investmentFixedIncomeIndexer.addEventListener("change", syncFixedIncomeRateHint);
  investmentFixedIncomeRate.addEventListener("input", syncFixedIncomeRateHint);
  transactionForm.elements.investment_asset_identifier.addEventListener("input", syncFixedIncomeRateHint);
  transactionForm.elements.investment_asset_name.addEventListener("input", syncFixedIncomeRateHint);
  transactionForm.querySelectorAll("[data-mode-target='investment'][data-fixed-income-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      investmentFixedIncomeMode.value = button.dataset.fixedIncomeMode || "";
      investmentFixedIncomeMode.dispatchEvent(new Event("change", { bubbles: true }));
    });
  });
  transactionForm.querySelectorAll("[data-mode-target='investment'][data-fixed-income-preset]").forEach((button) => {
    button.addEventListener("click", () => applyFixedIncomePreset(button.dataset.fixedIncomePreset || ""));
  });

  function fill(operation) {
    const fields = ["investment_asset_identifier", "investment_asset_name", "investment_cnpj", "investment_quantity", "investment_unit_price", "investment_brokerage_fee", "investment_exchange_fee", "investment_tax", "investment_other_costs", "investment_fixed_income_indexer", "investment_fixed_income_rate", "investment_fixed_income_maturity_date"];
    fields.forEach((field) => { if (transactionForm.elements[field]) transactionForm.elements[field].value = ""; });
    transactionForm.elements.investment_fixed_income_mode.value = "";
    if (transactionForm.elements.investment_emergency_reserve_eligible) transactionForm.elements.investment_emergency_reserve_eligible.checked = false;
    if (operation) {
      transactionForm.elements.investment_asset_identifier.value = operation.asset_identifier || "";
      transactionForm.elements.investment_asset_name.value = operation.asset_name || "";
      transactionForm.elements.investment_cnpj.value = operation.cnpj || "";
      transactionForm.elements.investment_quantity.value = decimalInputValue(operation.quantity);
      transactionForm.elements.investment_unit_price.value = moneyInputValue(operation.unit_price);
      transactionForm.elements.investment_brokerage_fee.value = moneyInputValue(operation.brokerage_fee);
      transactionForm.elements.investment_exchange_fee.value = moneyInputValue(operation.exchange_fee);
      transactionForm.elements.investment_tax.value = moneyInputValue(operation.tax);
      transactionForm.elements.investment_other_costs.value = moneyInputValue(operation.other_costs);
      transactionForm.elements.investment_fixed_income_mode.value = operation.fixed_income_mode || "";
      transactionForm.elements.investment_fixed_income_indexer.value = operation.fixed_income_indexer || "";
      transactionForm.elements.investment_fixed_income_rate.value = decimalInputValue(operation.fixed_income_rate);
      transactionForm.elements.investment_fixed_income_maturity_date.value = operation.fixed_income_maturity_date || "";
      if (transactionForm.elements.investment_emergency_reserve_eligible) transactionForm.elements.investment_emergency_reserve_eligible.checked = Boolean(operation.emergency_reserve_eligible);
    }
    updateFieldState();
  }

  function updateFieldState() {
    const isInvestment = transactionType.value === "investment";
    const category = transactionCategory.value;
    const savings = isSavingsSelection();
    const usesFundQuote = category === "Fundos de Investimentos" || category === "Previdência Privada";
    const canBeReserve = isInvestment && (category === "Renda Fixa" || savings);
    investmentFundFields.hidden = !isInvestment || !usesFundQuote;
    if (fetchInvestmentFundQuoteButton) fetchInvestmentFundQuoteButton.disabled = investmentFundFields.hidden;
    if (investmentFundQuoteHint && investmentFundFields.hidden) setFundQuoteHint("");
    investmentFixedFields.hidden = !isInvestment || category !== "Renda Fixa" || savings;
    investmentPricingFields.hidden = isInvestment && (category === "Renda Fixa" || savings);
    if (investmentTradingCostFields) investmentTradingCostFields.hidden = !isInvestment || savings;
    if (investmentTaxCostFields) investmentTaxCostFields.hidden = !isInvestment || savings;
    if (investmentEmergencyReserveFields) investmentEmergencyReserveFields.hidden = !canBeReserve;
    toggleFields(investmentOperationFields, !isInvestment);
    toggleFields(investmentFundFields, !isInvestment || investmentFundFields.hidden);
    toggleFields(investmentFixedFields, !isInvestment || investmentFixedFields.hidden);
    toggleFields(investmentPricingFields, investmentPricingFields.hidden);
    if (investmentTradingCostFields) toggleFields(investmentTradingCostFields, investmentTradingCostFields.hidden);
    if (investmentTaxCostFields) toggleFields(investmentTaxCostFields, investmentTaxCostFields.hidden);
    if (investmentEmergencyReserveFields) investmentEmergencyReserveFields.querySelectorAll("input").forEach((field) => {
      field.disabled = !canBeReserve;
      if (!canBeReserve) field.checked = false;
    });
    syncFixedIncomeRateHint();
    if (savings) {
      transactionForm.elements.investment_asset_identifier.value = "POUPANCA";
      if (!transactionForm.elements.investment_asset_name.value) transactionForm.elements.investment_asset_name.value = "Poupança";
    } else if (transactionForm.elements.investment_asset_identifier.value === "POUPANCA") {
      transactionForm.elements.investment_asset_identifier.value = "";
    }
    investmentAmount.required = isInvestment;
    investmentAmount.disabled = !isInvestment;
  }

  function toggleFields(container, disabled) {
    container.querySelectorAll("input, select").forEach((field) => { field.disabled = disabled; });
  }

  async function fetchFundQuote() {
    const cnpjField = transactionForm.elements.investment_cnpj;
    const unitPriceField = transactionForm.elements.investment_unit_price;
    const cnpj = String(cnpjField?.value || "").trim();
    if (!cnpj) { setFundQuoteHint("Informe o CNPJ do fundo antes de buscar a cota.", "error"); cnpjField?.focus(); return; }
    if (unitPriceField?.value.trim()) {
      const overwrite = await decisionModal.choose({ title: "Substituir preço unitário?", message: "O campo Preço unitário já tem valor. Deseja substituir pela cota retornada pela Mais Retorno?", actions: [{ value: "replace", label: "Substituir", variant: "primary" }, { value: null, label: "Manter atual", variant: "ghost" }] });
      if (!overwrite) return;
    }
    const previousLabel = fetchInvestmentFundQuoteButton?.textContent || "Buscar cota";
    if (fetchInvestmentFundQuoteButton) { fetchInvestmentFundQuoteButton.disabled = true; fetchInvestmentFundQuoteButton.textContent = "Buscando..."; }
    setFundQuoteHint("Consultando a Mais Retorno...");
    try {
      const quote = await api(`/api/portfolio/fund-quote?cnpj=${encodeURIComponent(cnpj)}`);
      unitPriceField.value = moneyInputValue(quote.unit_price);
      setFundQuoteHint(`Cota de ${formatDate(quote.quote_date)} preenchida. Confira com o comprovante antes de salvar.`, "success");
    } catch (error) {
      setFundQuoteHint(error.message || "Nao foi possivel buscar a cota do fundo.", "error");
    } finally {
      if (fetchInvestmentFundQuoteButton) { fetchInvestmentFundQuoteButton.disabled = investmentFundFields.hidden; fetchInvestmentFundQuoteButton.textContent = previousLabel; }
    }
  }

  function setFundQuoteHint(text, tone = "") {
    if (!investmentFundQuoteHint) return;
    investmentFundQuoteHint.textContent = text;
    investmentFundQuoteHint.className = `field-hint ${tone}`.trim();
  }

  function isSavingsSelection() {
    return transactionType.value === "investment" && normalizeSearch([transactionCategory.value, transactionSubcategory.value, transactionForm.elements.investment_asset_identifier.value].join(" ")).includes("poupanca");
  }

  function syncFixedIncomeRateHint() {
    const mode = investmentFixedIncomeMode.value;
    const labels = { pre: ["Taxa Anual (% a.a.)", "Ex.: 12,30 (para 12,30% a.a.)"], post: ["Percentual do Indexador (%)", "Ex.: 123 (deixe vazio para 100%)"], hybrid: ["Taxa Adicional Anual (% a.a.)", "Ex.: 6,50 (para IPCA + 6,50% a.a.)"] };
    [investmentFixedIncomeRateLabel.textContent, investmentFixedIncomeRate.placeholder] = labels[mode] || ["Taxa", "Ex.: 6,50"];
    transactionForm.querySelectorAll("[data-mode-target='investment'][data-fixed-income-mode]").forEach((button) => {
      const active = button.dataset.fixedIncomeMode === mode;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
    const rate = String(investmentFixedIncomeRate.value || "").trim();
    const indexer = String(investmentFixedIncomeIndexer.value || "").trim();
    const asset = String(transactionForm.elements.investment_asset_identifier.value || transactionForm.elements.investment_asset_name.value || "Título").trim();
    let text = "";
    if (mode === "pre") text = rate ? `${asset} configurado: pré-fixado a ${rate}% a.a.` : `${asset} configurado: pré-fixado com taxa anual a informar.`;
    if (mode === "post") text = indexer ? `${asset} configurado: ${rate || "100"}% do ${indexer}.` : `${asset} configurado: ${rate || "100"}% do indexador selecionado.`;
    if (mode === "hybrid") text = indexer ? `${asset} configurado: ${indexer}${rate ? ` + ${rate}% a.a.` : " + taxa adicional a informar"}.` : `${asset} configurado: indexador${rate ? ` + ${rate}% a.a.` : " + taxa adicional a informar"}.`;
    investmentFixedIncomePreview.hidden = !text;
    investmentFixedIncomePreview.textContent = text ? `✨ ${text}` : "";
  }

  function applyFixedIncomePreset(preset) {
    const [mode, indexer, rate] = preset.split(":");
    investmentFixedIncomeMode.value = mode || "";
    investmentFixedIncomeIndexer.value = indexer || "";
    investmentFixedIncomeRate.value = rate || "";
    syncFixedIncomeRateHint();
  }

  return { fill, updateFieldState, syncFixedIncomeRateHint };
}
