export function registerPortfolioView({
  state,
  elements,
  api,
  formData,
  setMessage,
  escapeHtml,
  formatMoney,
  formatPercent,
  formatDate,
  formatMonthLabel,
  formatMonthShortLabel,
  formatDecimal,
  moneyInputValue,
  portfolioQuoteText,
  todayLocalDateValue,
  chartColor,
  decisionModal,
  onPortfolioChanged = () => {},
  onPortfolioRedeemed = async () => {},
  editSourceTransaction = () => {},
}) {
  const {
    addPortfolioAssetButton,
    refreshPortfolioButton,
    portfolioAssetFormPanel,
    portfolioAssetForm,
    portfolioAssetFormTitle,
    portfolioAssetAccount,
    portfolioAssetType,
    portfolioAssetIdentifier,
    portfolioAssetIdentifierLabel,
    portfolioFundFields,
    portfolioPensionFields,
    portfolioPensionSubtype,
    portfolioSavingsFields,
    portfolioFixedFields,
    portfolioPricingFields,
    portfolioFixedIncomeSubtype,
    portfolioFixedIncomeMode,
    portfolioFixedIncomeIndexer,
    portfolioFixedIncomeRateLabel,
    portfolioFixedIncomeRate,
    portfolioFixedIncomePreview,
    cancelPortfolioAssetButton,
    deletePortfolioAssetButton,
    portfolioCostSummary,
    portfolioCurrentSummary,
    portfolioResultSummary,
    portfolioReturnSummary,
    portfolioDayResultSummary,
    portfolioReturnChartBtn,
    portfolioReturnDrawer,
    portfolioReturnDrawerOverlay,
    portfolioReturnDrawerCloseBtn,
    portfolioReturnDrawerTitle,
    portfolioReturnChart,
    portfolioReturnXLabels,
    portfolioReturnLegend,
    portfolioReturnNotice,
    portfolioPositionCount,
    portfolioMessage,
    portfolioTypeList,
    portfolioIndexerList,
    portfolioCurrencyList,
    portfolioAccountList,
    portfolioPositions,
    portfolioHistory,
    portfolioGroupFilter,
  } = elements;
  const portfolioEmergencyReserveFields = portfolioAssetForm.querySelector("#portfolioEmergencyReserveFields");
  const portfolioAssetName = portfolioAssetForm.elements.asset_name;

  addPortfolioAssetButton.addEventListener("click", showPortfolioAssetForm);
  refreshPortfolioButton.addEventListener("click", () => loadPortfolio({ refreshMessage: true }));
  portfolioAssetForm.addEventListener("submit", handlePortfolioAssetSubmit);
  portfolioAssetType.addEventListener("change", updatePortfolioAssetTypeState);
  portfolioFixedIncomeSubtype.addEventListener("change", syncPortfolioFixedIncomeSubtype);
  portfolioFixedIncomeMode.addEventListener("change", syncPortfolioFixedIncomeRateHint);
  portfolioFixedIncomeIndexer.addEventListener("change", syncPortfolioFixedIncomeRateHint);
  portfolioFixedIncomeRate.addEventListener("input", syncPortfolioFixedIncomeRateHint);
  portfolioAssetIdentifier.addEventListener("input", syncPortfolioFixedIncomeRateHint);
  portfolioAssetName.addEventListener("input", syncPortfolioFixedIncomeRateHint);
  portfolioAssetForm.querySelectorAll("[data-mode-target='portfolio'][data-fixed-income-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      portfolioFixedIncomeMode.value = button.dataset.fixedIncomeMode || "";
      portfolioFixedIncomeMode.dispatchEvent(new Event("change", { bubbles: true }));
    });
  });
  portfolioAssetForm.querySelectorAll("[data-mode-target='portfolio'][data-fixed-income-preset]").forEach((button) => {
    button.addEventListener("click", () => applyPortfolioFixedIncomePreset(button.dataset.fixedIncomePreset || ""));
  });
  portfolioPensionSubtype.addEventListener("change", syncPortfolioPensionSubtype);
  cancelPortfolioAssetButton.addEventListener("click", resetPortfolioAssetForm);
  deletePortfolioAssetButton.addEventListener("click", deletePortfolioAsset);
  portfolioGroupFilter.addEventListener("change", () => {
    state.portfolioGroup = portfolioGroupFilter.value;
    renderPortfolio();
  });
  portfolioPositions.addEventListener("click", handlePortfolioPositionsClick);
  portfolioReturnChartBtn?.addEventListener("click", openPortfolioReturnDrawer);
  portfolioReturnDrawerOverlay?.addEventListener("click", closePortfolioReturnDrawer);
  portfolioReturnDrawerCloseBtn?.addEventListener("click", closePortfolioReturnDrawer);

  function openPortfolioReturnDrawer() {
    if (!portfolioReturnDrawer) {
      return;
    }
    portfolioReturnDrawer.hidden = false;
    portfolioReturnDrawer.setAttribute("aria-hidden", "false");
    renderPortfolioReturns();
  }

  function closePortfolioReturnDrawer() {
    if (!portfolioReturnDrawer) {
      return;
    }
    portfolioReturnDrawer.hidden = true;
    portfolioReturnDrawer.setAttribute("aria-hidden", "true");
  }

  async function loadPortfolio(options = {}) {
    if (state.portfolio && !state.portfolioDirty && !options.force && !options.refreshMessage) {
      renderPortfolio();
      onPortfolioChanged();
      return;
    }
    if (state.portfolioLoading) {
      return;
    }
    state.portfolioLoading = true;
    state.portfolioError = "";
    if (options.refreshMessage) {
      setMessage(portfolioMessage, "Atualizando cotações...");
    }
    let portfolioErrorMessage = "";
    try {
      const endpoint = options.refreshMessage || options.force ? "/api/portfolio?refresh=1" : "/api/portfolio";
      state.portfolio = await api(endpoint);
      state.portfolioDirty = false;
      if (options.refreshMessage) {
        setMessage(portfolioMessage, "Portfólio atualizado.", "success");
      }
    } catch (error) {
      state.portfolio = null;
      portfolioErrorMessage = error.message || "Erro ao carregar portfólio";
      if (options.refreshMessage || state.view === "portfolio") {
        setMessage(portfolioMessage, portfolioErrorMessage, "error");
      }
    }

    try {
      const returnsEndpoint = options.refreshMessage || options.force ? "/api/portfolio/returns?refresh=1" : "/api/portfolio/returns";
      state.portfolioReturns = await api(returnsEndpoint);
      console.log("[portfolio-returns-debug] endpoint returned:", state.portfolioReturns);
    } catch (error) {
      state.portfolioReturns = null;
      console.error("Erro ao carregar rentabilidade:", error);
    }

    state.portfolioLoading = false;
    renderPortfolio();
    onPortfolioChanged();
  }

  function markPortfolioDirty() {
    state.portfolioDirty = true;
  }

  async function handlePortfolioAssetSubmit(event) {
    event.preventDefault();
    if (state.portfolioAssetSaving) {
      return;
    }
    setMessage(portfolioMessage, "");
    const submitButton = portfolioAssetForm.querySelector('button[type="submit"]');
    const originalButtonText = submitButton.textContent;
    state.portfolioAssetSaving = true;
    submitButton.disabled = true;
    submitButton.textContent = "Salvando...";
    try {
      syncPortfolioFixedIncomeSubtype();
      syncPortfolioPensionSubtype();
      const data = formData(portfolioAssetForm);
      const isEditing = Boolean(data.id);
      const response = await api(isEditing ? `/api/portfolio/positions/${data.id}` : "/api/portfolio/positions", {
        method: isEditing ? "PUT" : "POST",
        body: data,
      });
      state.portfolio = response;
      state.portfolioDirty = false;
      resetPortfolioAssetForm();
      renderPortfolio();
      onPortfolioChanged();
      setMessage(portfolioMessage, isEditing ? "Ativo atualizado no portfólio." : "Ativo incluído no portfólio sem movimentar conta.", "success");
    } catch (error) {
      setMessage(portfolioMessage, error.message, "error");
    } finally {
      state.portfolioAssetSaving = false;
      submitButton.textContent = originalButtonText;
      updatePortfolioAssetSubmitState();
    }
  }

  function showPortfolioAssetForm() {
    portfolioAssetForm.elements.id.value = "";
    portfolioAssetFormTitle.textContent = "Ativo em carteira";
    deletePortfolioAssetButton.hidden = true;
    renderPortfolioAssetAccounts();
    portfolioAssetFormPanel.hidden = false;
    if (!portfolioAssetForm.elements.acquisition_date.value) {
      portfolioAssetForm.elements.acquisition_date.value = todayLocalDateValue();
    }
    updatePortfolioAssetTypeState();
    portfolioAssetFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function resetPortfolioAssetForm() {
    portfolioAssetForm.reset();
    portfolioAssetForm.elements.id.value = "";
    portfolioAssetFormTitle.textContent = "Ativo em carteira";
    deletePortfolioAssetButton.hidden = true;
    portfolioAssetForm.elements.acquisition_date.value = todayLocalDateValue();
    portfolioAssetFormPanel.hidden = true;
    updatePortfolioAssetTypeState();
  }

  function editPortfolioPosition(position) {
    if (!position) {
      setMessage(portfolioMessage, "Posição inicial não encontrada. Atualize os dados e tente novamente.", "error");
      return;
    }
    if (position.source_type !== "opening" || !position.source_id) {
      setMessage(portfolioMessage, "Edite esta posição pelo lançamento de origem.", "error");
      return;
    }
    renderPortfolioAssetAccounts();
    portfolioAssetForm.reset();
    portfolioAssetForm.elements.id.value = position.source_id;
    portfolioAssetForm.elements.account_id.value = position.account_id;
    portfolioAssetForm.elements.acquisition_date.value = position.first_operation_date || todayLocalDateValue();
    portfolioAssetForm.elements.asset_type.value = position.asset_type || "other";
    portfolioAssetForm.elements.total_cost.value = moneyInputValue(position.total_cost);
    portfolioAssetForm.elements.asset_identifier.value = position.asset_identifier || "";
    portfolioAssetForm.elements.asset_name.value = position.asset_name || "";
    portfolioAssetForm.elements.cnpj.value = position.cnpj || "";
    portfolioAssetForm.elements.fixed_income_mode.value = position.fixed_income_mode || "";
    portfolioAssetForm.elements.fixed_income_indexer.value = position.fixed_income_indexer || "";
    portfolioAssetForm.elements.fixed_income_rate.value = decimalInputValue(position.fixed_income_rate);
    portfolioAssetForm.elements.fixed_income_maturity_date.value = position.fixed_income_maturity_date || "";
    portfolioAssetForm.elements.apply_tax_estimate.checked = Boolean(position.apply_tax_estimate);
    portfolioAssetForm.elements.emergency_reserve_eligible.checked = Boolean(position.emergency_reserve_eligible);
    portfolioAssetForm.elements.savings_anniversaries.value = savingsAnniversariesInputValue(position.savings_anniversaries);
    portfolioAssetForm.elements.quantity.value = decimalInputValue(position.quantity);
    portfolioAssetForm.elements.unit_price.value = moneyInputValue(position.average_price);
    portfolioAssetForm.elements.exchange_rate_to_brl.value = "";
    portfolioAssetForm.elements.notes.value = "";
    portfolioAssetFormTitle.textContent = "Editar ativo em carteira";
    deletePortfolioAssetButton.hidden = false;
    portfolioAssetFormPanel.hidden = false;
    updatePortfolioAssetTypeState();
    portfolioAssetFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function deletePortfolioAsset() {
    const positionId = portfolioAssetForm.elements.id.value;
    if (!positionId) {
      return;
    }
    const confirmed = window.confirm("Excluir este ativo do portfólio? Esta ação remove apenas a posição inicial cadastrada diretamente no Portfólio.");
    if (!confirmed) {
      return;
    }
    setMessage(portfolioMessage, "");
    try {
      const response = await api(`/api/portfolio/positions/${positionId}`, { method: "DELETE" });
      state.portfolio = response;
      state.portfolioDirty = false;
      resetPortfolioAssetForm();
      renderPortfolio();
      onPortfolioChanged();
      setMessage(portfolioMessage, "Ativo excluído do portfólio.", "success");
    } catch (error) {
      setMessage(portfolioMessage, error.message, "error");
    }
  }

  async function redeemPortfolioPosition(position) {
    const result = await decisionModal.form({
      title: "Resgatar posição",
      message: `${position.asset_name || position.asset_identifier || "Ativo"} · ${position.account_name || "Carteira"} (${position.currency || "BRL"})`,
      fields: [
        {
          name: "date",
          label: "Data do resgate",
          type: "date",
          value: todayLocalDateValue(),
          required: true,
        },
        {
          name: "amount",
          label: `Valor do resgate (${position.currency || "BRL"})`,
          type: "text",
          inputMode: "decimal",
          value: moneyInputValue(position.current_value),
          required: true,
          help: "Informe o valor que retornará para a conta da carteira.",
        },
      ],
      primaryLabel: "Registrar resgate",
    });
    if (!result) {
      return;
    }
    setMessage(portfolioMessage, "Efetuando resgate...");
    try {
      const response = await api("/api/portfolio/redeem", {
        method: "POST",
        body: {
          account_id: position.account_id,
          currency: position.currency,
          asset_type: position.asset_type,
          asset_identifier: position.asset_identifier || "",
          asset_name: position.asset_name || "",
          cnpj: position.cnpj || "",
          amount: result.amount,
          date: result.date,
        },
      });
      state.portfolio = response;
      state.portfolioDirty = false;
      await onPortfolioRedeemed();
      renderPortfolio();
      onPortfolioChanged();
      setMessage(portfolioMessage, "Resgate registrado e valor retornado para a conta da carteira.", "success");
    } catch (error) {
      setMessage(portfolioMessage, error.message, "error");
    }
  }

  function updatePortfolioAssetTypeState() {
    const assetType = portfolioAssetType.value;
    const canBeEmergencyReserve = assetType === "fixed_income" || assetType === "savings";
    portfolioFundFields.hidden = assetType !== "fund";
    portfolioFixedFields.hidden = assetType !== "fixed_income";
    portfolioPricingFields.hidden = assetType === "fixed_income" || assetType === "savings";
    portfolioPensionFields.hidden = assetType !== "private_pension";
    portfolioSavingsFields.hidden = assetType !== "savings";
    if (portfolioEmergencyReserveFields) {
      portfolioEmergencyReserveFields.hidden = !canBeEmergencyReserve;
      for (const field of portfolioEmergencyReserveFields.querySelectorAll("input")) {
        field.disabled = !canBeEmergencyReserve;
        if (!canBeEmergencyReserve) {
          field.checked = false;
        }
      }
    }
    if (assetType === "fixed_income") {
      portfolioAssetIdentifierLabel.hidden = true;
      const matchedSubtype = [...portfolioFixedIncomeSubtype.options].find((option) => option.value === portfolioAssetIdentifier.value);
      portfolioFixedIncomeSubtype.value = matchedSubtype ? matchedSubtype.value : "";
      portfolioPensionSubtype.value = "";
    } else if (assetType === "private_pension") {
      portfolioAssetIdentifierLabel.hidden = true;
      const matchedSubtype = [...portfolioPensionSubtype.options].find((option) => option.value === portfolioAssetIdentifier.value);
      portfolioPensionSubtype.value = matchedSubtype ? matchedSubtype.value : "";
      portfolioFixedIncomeSubtype.value = "";
    } else if (assetType === "savings") {
      portfolioAssetIdentifierLabel.hidden = true;
      portfolioAssetIdentifier.value = "POUPANCA";
      portfolioFixedIncomeSubtype.value = "";
      portfolioPensionSubtype.value = "";
    } else {
      portfolioAssetIdentifierLabel.hidden = false;
      portfolioAssetIdentifierLabel.childNodes[0].textContent = "Ativo ";
      portfolioAssetIdentifier.placeholder = "Ex.: PETR4, IVVB11, BTC";
      if (portfolioAssetIdentifier.value === "POUPANCA") {
        portfolioAssetIdentifier.value = "";
      }
      portfolioFixedIncomeSubtype.value = "";
      portfolioPensionSubtype.value = "";
    }
    for (const field of portfolioPricingFields.querySelectorAll("input, select")) {
      field.disabled = portfolioPricingFields.hidden;
    }
    syncPortfolioFixedIncomeRateHint();
  }

  function syncPortfolioFixedIncomeSubtype() {
    if (portfolioAssetType.value === "fixed_income" && portfolioFixedIncomeSubtype.value) {
      portfolioAssetIdentifier.value = portfolioFixedIncomeSubtype.value;
    }
  }

  function syncPortfolioFixedIncomeRateHint() {
    const mode = portfolioFixedIncomeMode.value;
    if (mode === "pre") {
      portfolioFixedIncomeRateLabel.textContent = "Taxa Anual (% a.a.)";
      portfolioFixedIncomeRate.placeholder = "Ex.: 12,30 (para 12,30% a.a.)";
    } else if (mode === "post") {
      portfolioFixedIncomeRateLabel.textContent = "Percentual do Indexador (%)";
      portfolioFixedIncomeRate.placeholder = "Ex.: 123 (deixe vazio para 100%)";
    } else if (mode === "hybrid") {
      portfolioFixedIncomeRateLabel.textContent = "Taxa Adicional Anual (% a.a.)";
      portfolioFixedIncomeRate.placeholder = "Ex.: 6,50 (para IPCA + 6,50% a.a.)";
    } else {
      portfolioFixedIncomeRateLabel.textContent = "Taxa";
      portfolioFixedIncomeRate.placeholder = "Ex.: 6,50";
    }
    syncFixedIncomeModeButtons(portfolioAssetForm, "portfolio", mode);
    updateFixedIncomePreview({
      mode,
      indexer: portfolioFixedIncomeIndexer.value,
      rate: portfolioFixedIncomeRate.value,
      preview: portfolioFixedIncomePreview,
      fallbackAsset: portfolioAssetIdentifier.value || portfolioAssetName.value,
    });
  }

  function applyPortfolioFixedIncomePreset(preset) {
    const [mode, indexer, rate] = preset.split(":");
    portfolioFixedIncomeMode.value = mode || "";
    portfolioFixedIncomeIndexer.value = indexer || "";
    portfolioFixedIncomeRate.value = rate || "";
    syncPortfolioFixedIncomeRateHint();
  }

  function syncFixedIncomeModeButtons(scope, target, mode) {
    scope.querySelectorAll(`[data-mode-target='${target}'][data-fixed-income-mode]`).forEach((button) => {
      const isActive = button.dataset.fixedIncomeMode === mode;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", isActive ? "true" : "false");
    });
  }

  function updateFixedIncomePreview({ mode, indexer, rate, preview, fallbackAsset }) {
    if (!preview) {
      return;
    }
    const cleanRate = String(rate || "").trim();
    const cleanIndexer = String(indexer || "").trim();
    const assetLabel = String(fallbackAsset || "").trim() || "Título";
    let text = "";
    if (mode === "pre") {
      text = cleanRate
        ? `${assetLabel} configurado: pré-fixado a ${cleanRate}% a.a.`
        : `${assetLabel} configurado: pré-fixado com taxa anual a informar.`;
    } else if (mode === "post") {
      const percent = cleanRate || "100";
      text = cleanIndexer
        ? `${assetLabel} configurado: ${percent}% do ${cleanIndexer}.`
        : `${assetLabel} configurado: ${percent}% do indexador selecionado.`;
    } else if (mode === "hybrid") {
      const rateText = cleanRate ? ` + ${cleanRate}% a.a.` : " + taxa adicional a informar";
      text = cleanIndexer
        ? `${assetLabel} configurado: ${cleanIndexer}${rateText}.`
        : `${assetLabel} configurado: indexador${rateText}.`;
    }
    preview.hidden = !text;
    preview.textContent = text ? `✨ ${text}` : "";
  }

  function syncPortfolioPensionSubtype() {
    if (portfolioAssetType.value === "private_pension" && portfolioPensionSubtype.value) {
      portfolioAssetIdentifier.value = portfolioPensionSubtype.value;
    }
  }

  function renderPortfolioAssetAccounts() {
    const portfolioAccounts = state.accounts.filter((account) => ["liquidity", "investment"].includes(account.account_type));
    portfolioAssetAccount.innerHTML = portfolioAccounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("") || '<option value="">Cadastre uma conta de liquidez ou investimento</option>';
    portfolioAssetAccount.disabled = portfolioAccounts.length === 0;
    updatePortfolioAssetSubmitState();
  }

  function updatePortfolioAssetSubmitState() {
    const hasPortfolioAccount = state.accounts.some((account) => ["liquidity", "investment"].includes(account.account_type));
    const submitButton = portfolioAssetForm.querySelector('button[type="submit"]');
    submitButton.disabled = state.portfolioAssetSaving || !hasPortfolioAccount;
  }

  function renderPortfolio() {
    const portfolio = state.portfolio;
    portfolioGroupFilter.value = state.portfolioGroup;
    if (!portfolio) {
      portfolioCostSummary.textContent = formatMoney(0, "BRL");
      portfolioCurrentSummary.textContent = formatMoney(0, "BRL");
      portfolioResultSummary.textContent = formatMoney(0, "BRL");
      portfolioReturnSummary.textContent = "0,00%";
      portfolioDayResultSummary.textContent = formatMoney(0, "BRL");
      portfolioPositionCount.textContent = "0";
      portfolioTypeList.innerHTML = "";
      portfolioIndexerList.innerHTML = "";
      portfolioCurrencyList.innerHTML = "";
      portfolioAccountList.innerHTML = "";
      portfolioPositions.innerHTML = '<div class="empty-state">Nenhuma posição de investimento encontrada.</div>';
      portfolioHistory.innerHTML = '<div class="empty-state compact">Nenhuma posição encerrada.</div>';
      return;
    }
    const summary = portfolio.summary;
    const currencyRows = portfolioSummaryCurrencyRows(summary);
    portfolioCostSummary.innerHTML = portfolioSummaryMetric(currencyRows, (row) => formatMoney(row.cost_brl, row.currency));
    portfolioCurrentSummary.innerHTML = portfolioSummaryMetric(currencyRows, (row) => formatMoney(row.current_brl, row.currency));
    portfolioResultSummary.innerHTML = portfolioSummaryMetric(currencyRows, (row) => formatMoney(row.result_brl, row.currency), true);
    portfolioReturnSummary.innerHTML = portfolioSummaryMetric(currencyRows, (row) => formatPortfolioPercent(row.result_percent), true, (row) => Number(row.result_brl));
    portfolioDayResultSummary.innerHTML = portfolioSummaryMetric(currencyRows, (row) => `${formatMoney(row.day_result_brl, row.currency)} · ${formatPortfolioPercent(row.day_result_percent)}`, true, (row) => Number(row.day_result_brl));
    portfolioPositionCount.textContent = String(summary.position_count || 0);
    if (portfolioReturnChartBtn) {
      const hasReturns = state.portfolioReturns && state.portfolioReturns.series && state.portfolioReturns.series.length > 0;
      console.log("[portfolio-returns-debug] returns:", state.portfolioReturns, "hasReturns:", hasReturns);
      portfolioReturnChartBtn.hidden = !hasReturns;
    }
    renderPortfolioGroupList(portfolioTypeList, summary.by_type);
    renderPortfolioGroupList(portfolioIndexerList, summary.by_indexer);
    renderPortfolioGroupList(portfolioCurrencyList, summary.by_currency);
    renderPortfolioGroupList(portfolioAccountList, summary.by_account);
    renderPortfolioPositions(portfolio.positions || []);
    renderHighlightedPortfolioPosition();
    renderPortfolioHistory(portfolio.history || []);
  }

  function renderHighlightedPortfolioPosition() {
    if (!state.portfolioHighlightId) {
      return;
    }
    const row = portfolioPositions.querySelector(
      `[data-portfolio-position-id="${CSS.escape(String(state.portfolioHighlightId))}"]`,
    );
    if (!row) {
      state.portfolioHighlightId = "";
      return;
    }
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    row.classList.add("portfolio-highlight-row");
    window.setTimeout(() => row.classList.remove("portfolio-highlight-row"), 3200);
    state.portfolioHighlightId = "";
  }

  function renderPortfolioReturns() {
    const returns = state.portfolioReturns;
    if (!returns) {
      return;
    }
    if (returns.error) {
      if (portfolioReturnChart) {
        portfolioReturnChart.innerHTML = "";
      }
      if (portfolioReturnXLabels) {
        portfolioReturnXLabels.innerHTML = "";
      }
      if (portfolioReturnLegend) {
        portfolioReturnLegend.innerHTML = `<span class="error-text">Não foi possível carregar a rentabilidade.</span>`;
      }
      return;
    }
    if (!returns.series || returns.series.length === 0) {
      return;
    }
    if (portfolioReturnDrawerTitle) {
      const start = formatMonthLabel(returns.start_month);
      const end = formatMonthLabel(returns.end_month);
      portfolioReturnDrawerTitle.textContent = start === end ? start : `${start} a ${end}`;
    }
    if (portfolioReturnNotice) {
      portfolioReturnNotice.hidden = !returns.has_historical_approximation;
    }

    const months = [...new Set(returns.series.map((entry) => entry.month))].sort();
    const currencies = [...new Set(returns.series.map((entry) => entry.currency))].sort();
    const cdiColor = "var(--muted)";
    const barWidth = 7;
    const step = months.length > 1 ? 100 / months.length : 100;
    const centerOffset = (currencies.length * barWidth) / 2;

    const maxAbs = Math.max(
      0.01,
      ...returns.series.map((entry) => Math.max(
        Math.abs(entry.portfolio_return_pct || 0),
        Math.abs(entry.cdi_return_pct || 0),
      )),
    );

    const bars = [];
    const labels = [];

    months.forEach((month, monthIndex) => {
      const xCenter = (monthIndex + 0.5) * step;
      const monthData = returns.series.filter((entry) => entry.month === month);
      const xStart = xCenter - centerOffset - barWidth / 2;

      currencies.forEach((currency, currencyIndex) => {
        const data = monthData.find((entry) => entry.currency === currency);
        const value = data ? data.portfolio_return_pct : 0;
        bars.push(renderReturnBar(xStart + currencyIndex * barWidth, value, maxAbs, chartColor(currencyIndex), currency, barWidth));
      });

      const cdiValue = monthData[0] ? monthData[0].cdi_return_pct : 0;
      bars.push(renderReturnBar(xStart + currencies.length * barWidth, cdiValue, maxAbs, cdiColor, "CDI", barWidth));

      labels.push(`<span style="left:${(xCenter).toFixed(2)}%">${formatReturnMonthLabel(month)}</span>`);
    });

    if (portfolioReturnChart) {
      portfolioReturnChart.innerHTML = `
        <line x1="0" y1="25" x2="100" y2="25" stroke="var(--line)" stroke-width="0.3" />
        ${bars.join("")}
      `;
    }
    if (portfolioReturnXLabels) {
      portfolioReturnXLabels.innerHTML = labels.join("");
    }
    if (portfolioReturnLegend) {
      const legendItems = currencies.map((currency, index) => `
        <span><i style="background:${chartColor(index)}"></i>${escapeHtml(currency)}</span>
      `).join("");
      portfolioReturnLegend.innerHTML = `${legendItems}<span><i style="background:${cdiColor}"></i>CDI</span>`;
    }
  }

  function formatReturnMonthLabel(month) {
    const [year, monthNumber] = month.split("-").map(Number);
    const date = new Date(year, monthNumber - 1, 1);
    return date.toLocaleDateString("pt-BR", { month: "short" }).replace(".", "").slice(0, 1).toUpperCase();
  }

  function renderReturnBar(x, value, maxAbs, color, label, barWidth) {
    const zeroY = 25;
    const height = (Math.abs(value) / maxAbs) * 22;
    const y = value >= 0 ? zeroY - height : zeroY;
    const displayValue = `${(value > 0 ? "+" : "")}${value.toFixed(2)}%`;
    return `
      <g class="portfolio-return-bar-group">
        <rect x="${x.toFixed(2)}" y="${y.toFixed(2)}" width="${barWidth - 0.5}" height="${height.toFixed(2)}" fill="${color}" rx="0.5">
          <title>${escapeHtml(label)}: ${escapeHtml(displayValue)}</title>
        </rect>
        <text x="${(x + barWidth / 2 - 0.25).toFixed(2)}" y="${value >= 0 ? (y - 1.5).toFixed(2) : (y + height + 2).toFixed(2)}" class="portfolio-return-label">${escapeHtml(displayValue)}</text>
      </g>
    `;
  }

  function portfolioSummaryCurrencyRows(summary) {
    const rows = summary.by_currency || [];
    if (rows.length) {
      return rows;
    }
    return [{
      currency: "BRL",
      cost_brl: summary.total_cost_brl || "0.00",
      current_brl: summary.current_value_brl || "0.00",
      result_brl: summary.result_brl || "0.00",
      result_percent: summary.result_percent || "0.00",
      day_result_brl: summary.day_result_brl || "0.00",
      day_result_percent: summary.day_result_percent || "0.00",
    }];
  }

  function portfolioSummaryMetric(rows, formatter, signed = false, signalValue = null) {
    return rows.map((row) => {
      const signal = signalValue ? Number(signalValue(row) || 0) : 0;
      const signalClass = signed ? signalClassName(signal) : "";
      return `
        <span class="portfolio-summary-line ${signalClass}">
          <b>${escapeHtml(row.currency || "BRL")}</b>
          <em>${formatter(row)}</em>
        </span>
      `;
    }).join("");
  }

  function signalClassName(value) {
    if (value < 0) {
      return "danger-text";
    }
    if (value > 0) {
      return "positive-text";
    }
    return "";
  }

  function formatPortfolioPercent(value) {
    return `${Number(value || 0).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  }

  function renderPortfolioGroupList(container, rows) {
    if (!rows || rows.length === 0) {
      container.innerHTML = '<div class="empty-state compact">Sem dados para consolidar.</div>';
      return;
    }
    const chartTotal = portfolioGroupChartTotal(rows);
    container.innerHTML = rows.map((row, index) => {
      const chartValue = Number(row.chart_current_brl || row.current_brl || 0);
      const currentValue = Number(row.current_brl || 0);
      const result = Number(row.result_brl || 0);
      const currency = row.currency || "BRL";
      const percent = chartTotal > 0 ? chartValue / chartTotal : 0;
      return `
        <article class="portfolio-group-row">
          <div>
            <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
            <span>${row.count} posição(ões)</span>
          </div>
          <div class="portfolio-group-value">
            <strong>${formatMoney(currentValue, currency)}</strong>
            <span class="${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(row.result_brl, currency)} · ${Number(row.result_percent).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</span>
          </div>
          <div class="report-bar"><span style="width:${Math.max(percent * 100, 2)}%; background:${chartColor(index)}"></span></div>
        </article>
      `;
    }).join("");
  }

  function portfolioGroupChartTotal(rows) {
    return rows.reduce((total, row) => total + Math.max(Number(row.chart_current_brl || row.current_brl || 0), 0), 0);
  }

  function portfolioTotalsByCurrency(rows) {
    const totals = new Map();
    rows.forEach((row) => {
      const currency = row.currency || "BRL";
      totals.set(currency, (totals.get(currency) || 0) + Number(row.current_brl || 0));
    });
    return totals;
  }

  function renderPortfolioPositions(positions) {
    if (positions.length === 0) {
      portfolioPositions.innerHTML = '<div class="empty-state">Lance uma compra de investimento para formar o portfólio.</div>';
      return;
    }
    const grouped = groupPortfolioPositions(positions);
    const hasTreasuryDirect = positions.some((position) => isTreasuryDirectPosition(position));
    portfolioPositions.innerHTML = `${grouped.map((group) => {
      const collapsed = state.portfolioCollapsedGroups.has(group.key);
      return `
      ${group.label ? portfolioGroupHeader(group, collapsed) : ""}
      <div class="report-table-wrap ${collapsed ? "portfolio-group-collapsed" : ""}">
        <table class="report-table portfolio-table">
          ${portfolioPositionColgroup()}
          <thead>
            <tr>
              <th>Ativo</th>
              <th>Tipo</th>
              <th>Carteira</th>
              <th>Qtd.</th>
              <th>Preço médio</th>
              <th>Custo</th>
              <th>Cotação</th>
              <th>Valor atual</th>
              <th>Dia</th>
              <th>Resultado</th>
              <th>Ações</th>
            </tr>
          </thead>
          <tbody>
            ${portfolioPositionRows(group.positions).join("")}
          </tbody>
        </table>
      </div>
    `;
    }).join("")}${hasTreasuryDirect ? portfolioTreasuryNote() : ""}`;
  }

  function portfolioTreasuryNote() {
    return `
      <p class="portfolio-footnote">
        Tesouro Direto: valores de renda fixa são estimados na curva pela taxa contratada cadastrada. Diferenças frente ao site do Tesouro podem ocorrer por marcação a mercado em resgate antecipado, provisão oficial de taxas e regras específicas do título. A Taxa B3 exibida é estimada em 0,20% a.a. pro rata, com isenção simplificada para Tesouro Selic até R$ 10.000,00 e sem estimativa automática para Renda+/Educa+.
      </p>
    `;
  }

  function isTreasuryDirectPosition(position) {
    return `${position.asset_identifier || ""} ${position.asset_name || ""}`.toUpperCase().includes("TESOURO");
  }

  function handlePortfolioPositionsClick(event) {
    const toggleSectionButton = event.target.closest("[data-toggle-portfolio-section]");
    if (toggleSectionButton) {
      const key = toggleSectionButton.dataset.togglePortfolioSection;
      if (state.portfolioCollapsedGroups.has(key)) {
        state.portfolioCollapsedGroups.delete(key);
      } else {
        state.portfolioCollapsedGroups.add(key);
      }
      renderPortfolioPositions(state.portfolio?.positions || []);
      return;
    }
    const toggleGroupButton = event.target.closest("[data-toggle-portfolio-group]");
    if (toggleGroupButton) {
      const key = toggleGroupButton.dataset.togglePortfolioGroup;
      if (state.portfolioExpandedGroups.has(key)) {
        state.portfolioExpandedGroups.delete(key);
      } else {
        state.portfolioExpandedGroups.add(key);
      }
      renderPortfolioPositions(state.portfolio?.positions || []);
      return;
    }
    const editPositionButton = event.target.closest("[data-edit-portfolio-position-id]");
    if (editPositionButton) {
      const position = findPortfolioOpeningPosition(state.portfolio?.positions || [], editPositionButton.dataset.editPortfolioPositionId);
      editPortfolioPosition(position);
      return;
    }
    const editTransactionButton = event.target.closest("[data-edit-portfolio-transaction-id]");
    if (editTransactionButton) {
      editSourceTransaction(editTransactionButton.dataset.editPortfolioTransactionId);
      return;
    }
    const editValueButton = event.target.closest("[data-edit-portfolio-value-payload]");
    if (editValueButton) {
      editPortfolioCurrentValue(JSON.parse(editValueButton.dataset.editPortfolioValuePayload));
      return;
    }
    const redeemButton = event.target.closest("[data-redeem-portfolio-payload]");
    if (redeemButton) {
      redeemPortfolioPosition(JSON.parse(redeemButton.dataset.redeemPortfolioPayload));
      return;
    }
    const closeButton = event.target.closest("[data-close-portfolio-payload]");
    if (closeButton) {
      closePortfolioPosition(JSON.parse(closeButton.dataset.closePortfolioPayload));
    }
  }

  function findPortfolioOpeningPosition(positions, openingId) {
    for (const position of positions) {
      if (position.source_type === "opening" && String(position.source_id) === String(openingId)) {
        return position;
      }
      const source = (position.sources || []).find((entry) => (
        entry.source_type === "opening" && String(entry.source_id) === String(openingId)
      ));
      if (source) {
        return portfolioSourcePosition(position, source);
      }
    }
    return null;
  }

  function portfolioGroupHeader(group, collapsed) {
    const currentValue = group.positions.reduce((total, position) => total + Number(position.current_value || 0), 0);
    const totalCost = group.positions.reduce((total, position) => total + Number(position.total_cost || 0), 0);
    const result = currentValue - totalCost;
    const resultPercent = totalCost > 0 ? result / totalCost : 0;
    const groupKind = state.portfolioGroup === "account_name" ? "Carteira" : "Grupo";
    const groupCurrency = portfolioGroupCurrency(group.positions);
    return `
      <button class="portfolio-group-title" type="button" data-toggle-portfolio-section="${escapeHtml(group.key)}" aria-expanded="${String(!collapsed)}">
        <span class="portfolio-group-toggle">${collapsed ? "+" : "-"}</span>
        <span>
          <small>${groupKind}</small>
          <strong>${escapeHtml(group.label)}</strong>
          <em>${group.positions.length} posição(ões)</em>
        </span>
        <span class="portfolio-group-total">
          <strong>${formatMoney(currentValue, groupCurrency)}</strong>
          <em class="${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(result, groupCurrency)} · ${formatPercent(resultPercent)}</em>
        </span>
      </button>
    `;
  }

  function portfolioGroupCurrency(positions) {
    const currencies = new Set(positions.map((position) => position.currency || "BRL"));
    return currencies.size === 1 ? [...currencies][0] : "BRL";
  }

  function renderPortfolioHistory(history) {
    if (!history.length) {
      portfolioHistory.innerHTML = '<div class="empty-state compact">Nenhuma posição encerrada.</div>';
      return;
    }
    portfolioHistory.innerHTML = `
      <div class="report-table-wrap">
        <table class="report-table portfolio-table portfolio-history-table">
          <thead>
            <tr>
              <th>Ativo</th>
              <th>Tipo</th>
              <th>Carteira</th>
              <th>Encerramento</th>
              <th>Custo</th>
              <th>Valor final</th>
              <th>Resultado</th>
            </tr>
          </thead>
          <tbody>
            ${history.map(portfolioHistoryRow).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function portfolioHistoryRow(position) {
    const result = Number(position.result_brl || 0);
    const detail = [
      position.asset_identifier && position.asset_identifier !== position.asset_name ? position.asset_identifier : "",
      position.fixed_income_indexer || "",
      position.fixed_income_maturity_date ? `Venc. ${formatDate(position.fixed_income_maturity_date)}` : "",
      Number(position.source_count || 0) > 1 ? `${position.source_count} origem(ns)` : "",
    ].filter(Boolean).join(" · ");
    return `
      <tr>
        <td>
          <div class="portfolio-asset-name"><strong>${escapeHtml(position.asset_name || position.asset_identifier || "Sem nome")}</strong></div>
          <span>${escapeHtml(detail || "Posição encerrada")}</span>
        </td>
        <td>${escapeHtml(position.asset_type_label)}<span>${escapeHtml(position.first_operation_date ? `Desde ${formatDate(position.first_operation_date)}` : "")}</span></td>
        <td>${escapeHtml(position.account_name)}<span>${escapeHtml(position.currency)}</span></td>
        <td>${formatDate(position.closed_at)}<span>${escapeHtml(position.quote_source || "")}</span></td>
        <td class="money-cell">${formatMoney(position.total_cost, position.currency)}<span>${formatMoney(position.total_cost_brl, "BRL")}</span></td>
        <td class="money-cell">${formatMoney(position.closing_value, position.currency)}<span>${formatMoney(position.closing_value_brl, "BRL")}</span></td>
        <td class="money-cell ${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(position.result_brl, "BRL")}<span>${Number(position.result_percent).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</span></td>
      </tr>
    `;
  }

  function groupPortfolioPositions(positions) {
    if (state.portfolioGroup === "none") {
      return [{ label: "", positions }];
    }
    const groups = new Map();
    for (const position of positions) {
      const label = position[state.portfolioGroup] || "Nao informado";
      if (!groups.has(label)) {
        groups.set(label, []);
      }
      groups.get(label).push(position);
    }
    return [...groups.entries()]
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([label, groupPositions]) => ({ label, key: portfolioSectionGroupKey(label), positions: groupPositions }));
  }

  function portfolioSectionGroupKey(label) {
    return JSON.stringify([state.portfolioGroup, label || ""]);
  }

  function portfolioPositionRows(positions) {
    return portfolioAssetGroups(positions).flatMap((group) => {
      if (group.positions.length === 1) {
        const position = group.positions[0];
        const sources = Array.isArray(position.sources) ? position.sources : [];
        if (sources.length <= 1) {
          return [portfolioPositionRow(position)];
        }
        const expanded = state.portfolioExpandedGroups.has(group.key);
        const rows = [portfolioPositionRow(position, {
          parent: true,
          expanded,
          childCount: sources.length,
          groupKey: group.key,
        })];
        if (expanded) {
          rows.push(...sources.map((source, index) => portfolioPositionRow(portfolioSourcePosition(position, source), {
            child: true,
            childLabel: source.description || `Lançamento ${index + 1}`,
          })));
        }
        return rows;
      }
      const expanded = state.portfolioExpandedGroups.has(group.key);
      const parent = aggregatePortfolioPositions(group.positions, group.key);
      const rows = [portfolioPositionRow(parent, {
        parent: true,
        expanded,
        childCount: group.positions.length,
        groupKey: group.key,
      })];
      if (expanded) {
        rows.push(...group.positions.map((position, index) => portfolioPositionRow(position, {
          child: true,
          childLabel: `Lançamento ${index + 1}`,
        })));
      }
      return rows;
    });
  }

  function portfolioSourcePosition(position, source) {
    return {
      ...position,
      ...source,
      asset_name: position.asset_name,
      asset_identifier: position.asset_identifier,
      current_value_cents: Number(source.current_value_cents || 0),
      current_value_brl_cents: Number(source.current_value_brl_cents || 0),
      day_result: "0.00",
      day_result_brl: "0.00",
      fixed_income_gross_value: "0.00",
      fixed_income_iof_tax: "0.00",
      fixed_income_income_tax: "0.00",
      fixed_income_net_value: source.current_value,
      first_operation_date: source.date || position.first_operation_date,
      last_operation_date: source.date || position.last_operation_date,
      source_type: source.source_type,
      source_id: source.source_id,
      source_transaction_id: source.source_transaction_id,
      operations_count: 1,
      sources: [],
    };
  }

  function portfolioAssetGroups(positions) {
    const groups = new Map();
    for (const position of positions) {
      const key = portfolioAssetGroupKey(position);
      if (!groups.has(key)) {
        groups.set(key, []);
      }
      groups.get(key).push(position);
    }
    return [...groups.entries()].map(([key, groupPositions]) => ({ key, positions: groupPositions }));
  }

  function portfolioAssetGroupKey(position) {
    const assetName = position.asset_name || position.asset_identifier || "Sem nome";
    return JSON.stringify([
      position.account_id,
      position.currency,
      position.asset_type,
      assetName,
      position.cnpj || "",
    ]);
  }

  function aggregatePortfolioPositions(positions, groupKey) {
    const base = { ...positions[0] };
    const sum = (field) => positions.reduce((total, position) => total + Number(position[field] || 0), 0);
    const quantity = sum("quantity");
    const totalCost = sum("total_cost");
    const totalCostBrl = sum("total_cost_brl");
    const currentValue = sum("current_value");
    const currentValueBrl = sum("current_value_brl");
    const dayResult = sum("day_result");
    const dayResultBrl = sum("day_result_brl");
    const fixedIncomeGross = sum("fixed_income_gross_value");
    const fixedIncomeIof = sum("fixed_income_iof_tax");
    const fixedIncomeTax = sum("fixed_income_income_tax");
    const fixedIncomeNet = sum("fixed_income_net_value");
    base.quantity = quantity;
    base.average_price = quantity > 0 ? totalCost / quantity : Number(base.average_price || 0);
    base.invested = sum("invested");
    base.costs = sum("costs");
    base.total_cost = totalCost;
    base.total_cost_brl = totalCostBrl;
    base.current_value = currentValue;
    base.current_value_brl = currentValueBrl;
    base.current_value_cents = Math.round(currentValue * 100);
    base.current_value_brl_cents = Math.round(currentValueBrl * 100);
    base.day_result = dayResult;
    base.day_result_brl = dayResultBrl;
    base.fixed_income_gross_value = fixedIncomeGross;
    base.fixed_income_iof_tax = fixedIncomeIof;
    base.fixed_income_income_tax = fixedIncomeTax;
    base.fixed_income_net_value = fixedIncomeNet;
    base.apply_tax_estimate = positions.every((position) => Boolean(position.apply_tax_estimate));
    base.source_type = "aggregate";
    base.source_id = null;
    base.source_transaction_id = null;
    base.operations_count = positions.length;
    base.portfolio_group_key = groupKey;
    return base;
  }

  function portfolioPositionRow(position, options = {}) {
    const result = Number(position.current_value || 0) - Number(position.total_cost || 0);
    const resultPercent = Number(position.total_cost) > 0 ? result / Number(position.total_cost) : 0;
    const dayResult = Number(position.day_result || 0);
    const dayBase = Number(position.current_value || 0) - dayResult;
    const dayPercent = dayBase > 0 ? dayResult / dayBase : 0;
    const quoteStatus = position.quote_status === "ok" ? position.quote_source : position.quote_status;
    const quoteText = portfolioQuoteText(position);
    const quoteStatusLabel = quoteStatus || "Pendente";
    const maturityAlert = portfolioMaturityAlert(position);
    const identifier = position.asset_identifier || position.asset_name || "Sem codigo";
    const assetName = position.asset_name || identifier;
    const rowLabel = options.parent ? assetName : options.child ? options.childLabel : identifier;
    const maturityDetail = maturityAlert
      ? `<span class="portfolio-maturity-pill ${maturityAlert.status}" title="${escapeHtml(maturityAlert.title)}">${escapeHtml(maturityAlert.label)}</span>`
      : "";
    const assetDetail = [
      options.parent ? `${options.childCount} lançamentos` : "",
      options.parent && position.asset_identifier && position.asset_identifier !== assetName ? position.asset_identifier : "",
      options.child ? identifier : "",
      options.child ? formatDate(position.first_operation_date) : "",
      !options.parent && !options.child && position.asset_name && position.asset_name !== identifier ? position.asset_name : "",
      position.cnpj ? `CNPJ ${position.cnpj}` : "",
      position.emergency_reserve_eligible ? "Reserva de emergência" : "",
      portfolioFixedIncomeDetail(position),
      position.fixed_income_maturity_date ? `Venc. ${formatDate(position.fixed_income_maturity_date)}` : "",
    ].filter(Boolean).join(" · ");
    const toggle = options.parent
      ? `<button class="portfolio-toggle" type="button" data-toggle-portfolio-group="${escapeHtml(options.groupKey)}" aria-label="${options.expanded ? "Recolher" : "Abrir"} ${escapeHtml(identifier)}">${options.expanded ? "-" : "+"}</button>`
      : options.child ? '<span class="portfolio-child-marker"></span>' : "";
    const fixedIncomeIof = Number(position.fixed_income_iof_tax || 0);
    const fixedIncomeTax = Number(position.fixed_income_income_tax || 0);
    const fixedIncomeCustodyFee = Number(position.fixed_income_custody_fee || 0);
    const hasFixedIncomeTax = position.asset_type === "fixed_income" && (fixedIncomeIof > 0 || fixedIncomeTax > 0 || fixedIncomeCustodyFee > 0);
    const valueDetail = hasFixedIncomeTax
      ? `<span title="${escapeHtml([
        `Bruto ${formatMoney(position.fixed_income_gross_value || position.current_value, position.currency)}`,
        fixedIncomeIof > 0 ? `IOF estimado -${formatMoney(position.fixed_income_iof_tax, position.currency)}` : "",
        `IR estimado -${formatMoney(position.fixed_income_income_tax, position.currency)}`,
        fixedIncomeCustodyFee > 0 ? `Taxa B3 estimada -${formatMoney(position.fixed_income_custody_fee, position.currency)}` : "",
        `Líquido ${formatMoney(position.fixed_income_net_value, position.currency)}`,
      ].filter(Boolean).join(" · "))}">Líquido ${formatMoney(position.fixed_income_net_value, position.currency)}</span>`
      : portfolioSecondaryMoney(position.current_value, position.current_value_brl, position.currency);
    const actions = position.source_type === "opening" && position.source_id
      ? portfolioIconButton("edit-position", "Editar ativo", `data-edit-portfolio-position-id="${position.source_id}"`)
      : position.source_type === "operation" && position.source_transaction_id
        ? portfolioIconButton("edit-transaction", "Editar lançamento", `data-edit-portfolio-transaction-id="${position.source_transaction_id}"`)
        : portfolioInfoIcon("Múltiplas origens");
    const redeemAction = portfolioIconButton("redeem", "Resgatar", `data-redeem-portfolio-payload="${escapeHtml(JSON.stringify(portfolioRedemptionPayload(position)))}"`);
    const valueAction = portfolioIconButton("edit-value", "Atualizar valor atual", `data-edit-portfolio-value-payload="${escapeHtml(JSON.stringify(portfolioValuePayload(position)))}"`);
    const closeAction = portfolioIconButton("close-position", "Encerrar posição", `data-close-portfolio-payload="${escapeHtml(JSON.stringify(portfolioClosePayload(position)))}"`);
    const rowId = position.source_id || position.position_id || position.id;
    const rowIdAttr = rowId ? `data-portfolio-position-id="${escapeHtml(String(rowId))}"` : "";
    return `
      <tr ${rowIdAttr} class="${options.parent ? "portfolio-parent-row" : ""} ${options.child ? "portfolio-child-row" : ""} ${maturityAlert ? `portfolio-maturity-row ${maturityAlert.status}` : ""}">
        <td>
          <div class="portfolio-asset-name">${toggle}<strong>${escapeHtml(rowLabel)}</strong>${maturityDetail}</div>
          <span class="portfolio-detail" title="${escapeHtml(assetDetail || "Sem detalhe adicional")}">${escapeHtml(assetDetail || "Sem detalhe adicional")}</span>
        </td>
        <td><span class="portfolio-primary">${escapeHtml(position.asset_type_label)}</span><span>${escapeHtml(position.market_label || "Brasil")}</span></td>
        <td><span class="portfolio-primary">${escapeHtml(position.account_name)}</span><span>${escapeHtml(position.currency)}</span></td>
        <td class="money-cell">${formatDecimal(position.quantity, 6)}</td>
        <td class="money-cell">${formatMoney(position.average_price, position.currency)}</td>
        <td class="money-cell">${formatMoney(position.total_cost, position.currency)}${portfolioSecondaryMoney(position.total_cost, position.total_cost_brl, position.currency)}</td>
        <td class="money-cell portfolio-quote-cell"><span class="portfolio-primary">${quoteText}</span><span title="${escapeHtml(quoteStatusLabel)}">${escapeHtml(quoteStatusLabel)}</span></td>
        <td class="money-cell">${formatMoney(position.current_value_cents / 100, position.currency)}${valueDetail}</td>
        <td class="money-cell ${dayResult < 0 ? "danger-text" : "positive-text"}">${formatMoney(dayResult, position.currency)}<span>${formatPercent(dayPercent)}</span></td>
        <td class="money-cell ${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(result, position.currency)}<span>${formatPercent(resultPercent)}</span></td>
        <td><div class="portfolio-actions">${redeemAction}${valueAction}${closeAction}${actions}</div></td>
      </tr>
    `;
  }

  function portfolioPositionColgroup() {
    return `
      <colgroup>
        <col class="portfolio-col-asset">
        <col class="portfolio-col-type">
        <col class="portfolio-col-account">
        <col class="portfolio-col-quantity">
        <col class="portfolio-col-price">
        <col class="portfolio-col-cost">
        <col class="portfolio-col-quote">
        <col class="portfolio-col-value">
        <col class="portfolio-col-day">
        <col class="portfolio-col-result">
        <col class="portfolio-col-actions">
      </colgroup>
    `;
  }

  function portfolioSecondaryMoney(primaryValue, secondaryValue, currency) {
    if (Number(primaryValue || 0) === Number(secondaryValue || 0)) {
      return "";
    }
    return `<span>${formatMoney(secondaryValue, "BRL")}</span>`;
  }

  function portfolioFixedIncomeDetail(position) {
    if (position.asset_type !== "fixed_income") {
      return "";
    }
    if (position.fixed_income_mode === "pre") {
      return ["Préfixado", position.fixed_income_rate ? `${position.fixed_income_rate}%` : ""].filter(Boolean).join(" · ");
    }
    return position.fixed_income_indexer
      ? `${position.fixed_income_indexer}${position.fixed_income_rate ? ` · ${position.fixed_income_rate}%` : ""}`
      : "";
  }

  function portfolioMaturityAlert(position) {
    const maturityDate = String(position.fixed_income_maturity_date || "").trim();
    if (!maturityDate) {
      return null;
    }
    const today = todayLocalDateValue();
    if (maturityDate < today) {
      return {
        status: "overdue",
        label: "Vencido",
        title: `Venceu em ${formatDate(maturityDate)}. Avalie resgate ou encerramento da posição.`,
      };
    }
    if (maturityDate === today) {
      return {
        status: "due-today",
        label: "Vence hoje",
        title: "Vence hoje. Avalie resgate ou encerramento da posição.",
      };
    }
    return null;
  }

  function portfolioMaturityAlerts() {
    const positions = state.portfolio?.positions || [];
    const alerts = [];
    const seen = new Set();
    for (const position of positions) {
      const alert = portfolioMaturityAlert(position);
      if (!alert) {
        continue;
      }
      const key = [
        position.account_id,
        position.asset_type,
        position.asset_identifier || "",
        position.asset_name || "",
        position.cnpj || "",
        position.fixed_income_indexer || "",
        position.fixed_income_maturity_date || "",
        position.source_type || "",
        position.source_id || "",
      ].join("|");
      if (seen.has(key)) {
        continue;
      }
      seen.add(key);
      alerts.push({
        ...alert,
        maturityDate: position.fixed_income_maturity_date,
        label: position.asset_name || position.asset_identifier || position.description || "Ativo sem identificação",
        accountName: position.account_name || "Carteira",
      });
    }
    return alerts.sort((a, b) => {
      if (a.status !== b.status) {
        return a.status === "overdue" ? -1 : 1;
      }
      return String(a.maturityDate).localeCompare(String(b.maturityDate));
    });
  }

  function portfolioIconButton(icon, label, attributes) {
    return `
      <button class="portfolio-icon-button" type="button" ${attributes} title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}">
        ${portfolioIconSvg(icon)}
      </button>
    `;
  }

  function portfolioInfoIcon(label) {
    return `
      <span class="portfolio-icon-button portfolio-icon-static" title="${escapeHtml(label)}" aria-label="${escapeHtml(label)}" role="img">
        ${portfolioIconSvg("multiple")}
      </span>
    `;
  }

  function portfolioIconSvg(icon) {
    const icons = {
      redeem: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h12a4 4 0 0 1 0 8H8"/><path d="M8 11l-4 4 4 4"/><path d="M20 5v4"/><path d="M18 7h4"/></svg>',
      "edit-value": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 18h16"/><path d="M7 15l3-4 3 2 4-7"/><path d="M17 6h3v3"/></svg>',
      "edit-position": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4l11-11a2.8 2.8 0 0 0-4-4L4 16v4z"/><path d="M13 6l5 5"/><path d="M12 20h8"/></svg>',
      "edit-transaction": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3h9l3 3v15H6z"/><path d="M14 3v4h4"/><path d="M8 15l5-5 3 3-5 5H8z"/><path d="M13 10l3 3"/></svg>',
      "close-position": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 6l12 12"/><path d="M18 6L6 18"/><path d="M5 3h14a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2z"/></svg>',
      multiple: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7h10"/><path d="M7 12h10"/><path d="M7 17h10"/><path d="M4 7h.01"/><path d="M4 12h.01"/><path d="M4 17h.01"/></svg>',
    };
    return icons[icon] || icons["edit-position"];
  }

  async function closePortfolioPosition(position) {
    const result = await decisionModal.form({
      title: "Encerrar posição",
      message: "A posição deixará a carteira atual e será movida para Histórico.",
      fields: [
        {
          name: "date",
          label: "Data de encerramento",
          type: "date",
          value: todayLocalDateValue(),
          required: true,
        },
        {
          name: "closing_value",
          label: "Valor final reconhecido pelo banco",
          type: "text",
          inputMode: "decimal",
          value: moneyInputValue(position.current_value),
          required: true,
        },
        {
          name: "register_credit",
          label: "Registrar crédito na conta",
          type: "checkbox",
          value: false,
          help: "Marque apenas se o valor final entrou na conta agora.",
        },
      ],
      primaryLabel: "Encerrar posição",
    });
    if (!result) {
      return;
    }
    setMessage(portfolioMessage, "Encerrando posição...");
    try {
      const response = await api("/api/portfolio/close", {
        method: "POST",
        body: {
          ...position,
          date: result.date,
          closing_value: result.closing_value,
          register_credit: result.register_credit,
        },
      });
      state.portfolio = response;
      state.portfolioDirty = false;
      renderPortfolio();
      onPortfolioChanged();
      setMessage(portfolioMessage, "Posição encerrada e movida para o histórico.", "success");
    } catch (error) {
      setMessage(portfolioMessage, error.message, "error");
    }
  }

  async function editPortfolioCurrentValue(position) {
    const result = await decisionModal.form({
      title: "Atualizar valor atual",
      message: `${position.asset_name || position.asset_identifier || "Ativo"} · ${position.account_name || "Carteira"} (${position.currency || "BRL"})`,
      fields: [
        {
          name: "quote_date",
          label: "Data da atualização",
          type: "date",
          value: todayLocalDateValue(),
          required: true,
        },
        {
          name: "current_value",
          label: `Valor atual (${position.currency || "BRL"})`,
          type: "text",
          inputMode: "decimal",
          value: moneyInputValue(position.current_value),
          required: true,
          help: "Use o valor total atual da posição informado pela instituição.",
        },
      ],
      primaryLabel: "Atualizar valor",
    });
    if (!result) {
      return;
    }
    setMessage(portfolioMessage, "Atualizando valor atual...");
    try {
      const response = await api("/api/portfolio/value", {
        method: "PUT",
        body: {
          ...position,
          current_value: result.current_value,
          quote_date: result.quote_date,
        },
      });
      state.portfolio = response;
      state.portfolioDirty = false;
      renderPortfolio();
      onPortfolioChanged();
      setMessage(portfolioMessage, "Valor atual do portfólio atualizado.", "success");
    } catch (error) {
      setMessage(portfolioMessage, error.message, "error");
    }
  }

  function portfolioRedemptionPayload(position) {
    return {
      account_id: position.account_id,
      currency: position.currency,
      asset_type: position.asset_type,
      asset_identifier: position.asset_identifier || "",
      asset_name: position.asset_name || "",
      cnpj: position.cnpj || "",
      current_value: position.current_value,
    };
  }

  function portfolioValuePayload(position) {
    return {
      account_id: position.account_id,
      asset_type: position.asset_type,
      asset_identifier: position.asset_identifier || "",
      asset_name: position.asset_name || "",
      cnpj: position.cnpj || "",
      fixed_income_indexer: position.fixed_income_indexer || "",
      fixed_income_maturity_date: position.fixed_income_maturity_date || "",
      current_value: position.current_value,
    };
  }

  function portfolioClosePayload(position) {
    return {
      ...portfolioRedemptionPayload(position),
      fixed_income_indexer: position.fixed_income_indexer || "",
      fixed_income_maturity_date: position.fixed_income_maturity_date || "",
    };
  }

  function savingsAnniversariesInputValue(entries) {
    if (!Array.isArray(entries)) {
      return "";
    }
    return entries
      .map((entry) => `${entry.date || ""}; ${moneyInputValue(entry.amount)}`)
      .filter((line) => !line.startsWith(";"))
      .join("\n");
  }

  function decimalInputValue(value) {
    if (value === null || value === undefined || value === "") {
      return "";
    }
    return String(value).replace(".", ",");
  }

  return {
    loadPortfolio,
    markPortfolioDirty,
    showPortfolioAssetForm,
    resetPortfolioAssetForm,
    renderPortfolioAssetAccounts,
    renderPortfolio,
    portfolioTotalsByCurrency,
    portfolioMaturityAlerts,
  };
}
