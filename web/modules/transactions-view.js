import { stateMarkup } from "./dom-utils.js";

export function registerTransactionsView({
  state,
  elements,
  api,
  fetchAllListed,
  formData,
  setFormBusy,
  setMessage,
  emptyState,
  escapeHtml,
  normalizeSearch,
  formatCurrencySummary,
  formatMoney,
  formatDate,
  formatMonthLabel,
  formatMonthShortLabel,
  formatShortMonthName,
  formatCategoryPath,
  moneyInputValue,
  parseDecimalInput,
  todayLocalDateValue,
  monthEndDate,
  currentMonthValue,
  shiftMonth,
  isValidMonthValue,
  isExchangeTransfer,
  isInstallmentTransaction,
  isInvestmentTransaction,
  isInvestmentTransfer,
  transactionSeriesLabel,
  transactionTypeLabel,
  openMonthPicker,
  decisionModal,
  ensureSelectedAccount,
  getBalanceUntil,
  accountHasPreferredCardForecast,
  loadCockpit,
  markPortfolioDirty,
  renderBaseViews,
  renderFinanceViews,
  renderPortfolio,
  renderImportTargets,
}) {
  const balanceHistoryChartTop = 10;
  const balanceHistoryChartBottom = 88;
  const balanceHistoryChartBaseline = 94;
  const balanceHistoryChartFlat = 49;
  const {
    transactionForm,
    transactionFormTitle,
    transactionMessage,
    transactionList,
    transactionTagOptions,
    transactionType,
    transactionAccount,
    transactionAmount,
    transactionAmountRow,
    destinationAccount,
    destinationAccountLabel,
    exchangeTransferFields,
    destinationAmount,
    transferExchangeRate,
    investmentOperationFields,
    investmentAmount,
    investmentAmountRow,
    investmentFundFields,
    fetchInvestmentFundQuoteButton,
    investmentFundQuoteHint,
    investmentFixedFields,
    investmentPricingFields,
    investmentEmergencyReserveFields,
    investmentTradingCostFields,
    investmentTaxCostFields,
    investmentFixedIncomeMode,
    investmentFixedIncomeIndexer,
    investmentFixedIncomeRateLabel,
    investmentFixedIncomeRate,
    investmentFixedIncomePreview,
    transactionCategory,
    transactionCategoryRow,
    transactionSubcategory,
    transactionClassificationSuggestion,
    seriesKind,
    seriesKindRow,
    installmentCount,
    installmentCountLabel,
    recurrenceFields,
    recurrenceFrequency,
    recurrenceAverageFields,
    useAverage,
    exchangeRate,
    exchangeRateLabel,
    exchangeRateLabelText,
    cancelTransactionEditButton,
    transactionMonthLabel,
    previousMonthButton,
    todayMonthButton,
    nextMonthButton,
    currentBalanceSummary,
    forecastBalanceLabel,
    forecastBalanceSummary,
    transactionBalanceHistoryChart,
    transactionSearch,
    clearTransactionSearchButton,
    transactionStatusFilterButtons,
    transactionContextCount,
  } = elements;
  let classificationSuggestionTimer = null;
  let classificationSuggestionRequestId = 0;
  let classificationSelectionTouched = false;
  const expandedTransactionDays = new Map();

  transactionForm.addEventListener("submit", handleTransactionSubmit);
  transactionType.addEventListener("change", () => {
    applyWalletAccountRestrictions();
    updateTransactionTypeState();
    scheduleClassificationSuggestion();
  });
  transactionAccount.addEventListener("change", handleTransactionAccountChange);
  destinationAccount.addEventListener("change", updateTransferExchangeRateState);
  fetchInvestmentFundQuoteButton?.addEventListener("click", fetchInvestmentFundQuote);
  investmentAmount.addEventListener("input", () => {
    if (transactionType.value === "investment") {
      transactionAmount.value = investmentAmount.value;
    }
  });
  transactionCategory.addEventListener("change", () => {
    classificationSelectionTouched = true;
    renderTransactionSubcategories();
    updateInvestmentFieldState();
  });
  transactionSubcategory.addEventListener("change", () => {
    classificationSelectionTouched = true;
    updateInvestmentFieldState();
  });
  transactionForm.elements.description.addEventListener("input", scheduleClassificationSuggestion);
  seriesKind.addEventListener("change", updateSeriesState);
  transactionForm.elements.date.addEventListener("change", updateExchangeRateState);
  transactionForm.elements.date.addEventListener("change", updateTransferExchangeRateState);
  transactionForm.elements.amount.addEventListener("input", updateDestinationAmountFromRate);
  transferExchangeRate.addEventListener("input", updateDestinationAmountFromRate);
  investmentFixedIncomeMode.addEventListener("change", syncInvestmentFixedIncomeRateHint);
  investmentFixedIncomeIndexer.addEventListener("change", syncInvestmentFixedIncomeRateHint);
  investmentFixedIncomeRate.addEventListener("input", syncInvestmentFixedIncomeRateHint);
  transactionForm.elements.investment_asset_identifier.addEventListener("input", syncInvestmentFixedIncomeRateHint);
  transactionForm.elements.investment_asset_name.addEventListener("input", syncInvestmentFixedIncomeRateHint);
  transactionForm.querySelectorAll("[data-mode-target='investment'][data-fixed-income-mode]").forEach((button) => {
    button.addEventListener("click", () => {
      investmentFixedIncomeMode.value = button.dataset.fixedIncomeMode || "";
      investmentFixedIncomeMode.dispatchEvent(new Event("change", { bubbles: true }));
    });
  });
  transactionForm.querySelectorAll("[data-mode-target='investment'][data-fixed-income-preset]").forEach((button) => {
    button.addEventListener("click", () => applyInvestmentFixedIncomePreset(button.dataset.fixedIncomePreset || ""));
  });
  previousMonthButton.addEventListener("click", () => shiftTransactionMonth(-1));
  todayMonthButton.addEventListener("click", () => setTransactionMonth(currentMonthValue()));
  transactionMonthLabel.addEventListener("click", (event) => {
    event.stopPropagation();
    openMonthPicker(event.currentTarget, state.transactionMonth, setTransactionMonth);
  });
  nextMonthButton.addEventListener("click", () => shiftTransactionMonth(1));
  transactionSearch.value = state.transactionSearch || "";
  let searchDebounceTimer = null;
  transactionSearch.addEventListener("input", () => {
    state.transactionSearch = transactionSearch.value;
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(renderTransactions, 200);
  });
  clearTransactionSearchButton.addEventListener("click", () => {
    state.transactionSearch = "";
    transactionSearch.value = "";
    clearTimeout(searchDebounceTimer);
    renderTransactions();
    transactionSearch.focus();
  });
  transactionStatusFilterButtons.forEach((button) => {
    button.addEventListener("click", () => {
      state.transactionStatusFilter = button.dataset.transactionStatusFilter || "all";
      renderTransactions();
    });
  });
  transactionList.addEventListener("click", handleTransactionListClick);
  if (transactionBalanceHistoryChart) {
    transactionBalanceHistoryChart.addEventListener("click", handleBalanceHistoryClick);
  }
  cancelTransactionEditButton.addEventListener("click", resetTransactionForm);

  function scheduleClassificationSuggestion() {
    clearTimeout(classificationSuggestionTimer);
    const requestId = ++classificationSuggestionRequestId;
    if (transactionClassificationSuggestion) {
      transactionClassificationSuggestion.textContent = "";
    }
    if (
      transactionForm.elements.id.value
      || classificationSelectionTouched
      || !["expense", "income", "investment"].includes(transactionType.value)
      || transactionForm.elements.description.value.trim().length < 2
    ) {
      return;
    }
    classificationSuggestionTimer = setTimeout(() => {
      applyClassificationSuggestion(requestId);
    }, 300);
  }

  async function applyClassificationSuggestion(requestId) {
    const description = transactionForm.elements.description.value.trim();
    const groupType = transactionType.value;
    try {
      const response = await api(
        `/api/classification-suggestion?description=${encodeURIComponent(description)}&group_type=${encodeURIComponent(groupType)}`,
      );
      if (
        requestId !== classificationSuggestionRequestId
        || classificationSelectionTouched
        || transactionForm.elements.id.value
        || description !== transactionForm.elements.description.value.trim()
        || groupType !== transactionType.value
        || !response.suggestion
      ) {
        return;
      }
      const suggestion = response.suggestion;
      const categoryExists = Array.from(transactionCategory.options).some(
        (option) => option.value === suggestion.category_name,
      );
      if (!categoryExists) {
        return;
      }
      transactionCategory.value = suggestion.category_name;
      renderTransactionSubcategories();
      if (suggestion.subcategory_name) {
        const subcategoryExists = Array.from(transactionSubcategory.options).some(
          (option) => option.value === suggestion.subcategory_name,
        );
        if (subcategoryExists) {
          transactionSubcategory.value = suggestion.subcategory_name;
        }
      }
      updateInvestmentFieldState();
      if (transactionClassificationSuggestion) {
        const path = suggestion.subcategory_name
          ? `${suggestion.category_name} › ${suggestion.subcategory_name}`
          : suggestion.category_name;
        transactionClassificationSuggestion.textContent = `Sugerido pelo histórico: ${path}`;
      }
    } catch {
      // A classificação assistida nunca bloqueia o cadastro manual.
    }
  }

  async function loadTransactionSlice() {
    ensureSelectedAccount();
    const requestId = ++state.transactionSliceRequestId;
    const accountId = String(state.selectedAccountId || "");
    const month = state.transactionMonth;
    if (!state.selectedAccountId) {
      state.accountTransactions = [];
      return;
    }
    const response = await fetchAllListed(`/api/transactions?month=${encodeURIComponent(month)}&account_id=${encodeURIComponent(accountId)}`, "transactions");
    if (
      requestId !== state.transactionSliceRequestId
      || month !== state.transactionMonth
      || accountId !== String(state.selectedAccountId || "")
    ) {
      return;
    }
    state.accountTransactions = response;
  }

  async function handleTransactionSubmit(event) {
    event.preventDefault();
    setMessage(transactionMessage, "");
    if (state.accounts.length === 0) {
      setMessage(transactionMessage, "Cadastre uma conta antes de lançar transações.", "error");
      return;
    }
    try {
      const data = formData(transactionForm);
      setFormBusy(transactionForm, true);
      if (data.type === "investment") {
        data.amount = data.investment_amount || data.amount;
      }
      if (data.type === "exchange") {
        data.type = "transfer";
        data.tags = data.tags || "Câmbio";
      }
      if (data.type === "transfer") {
        delete data.category;
        delete data.subcategory;
        data.series_kind = "single";
      } else {
        delete data.destination_account_id;
        delete data.destination_amount;
        delete data.transfer_exchange_rate;
      }
      const isEditing = Boolean(data.id);
      const editingTransaction = isEditing ? findTransactionById(data.id) : null;
      const averageChanged = Boolean(
        editingTransaction && editingTransaction.series_kind === "recurring" && useAverage
          && Boolean(editingTransaction.use_average) !== useAverage.checked,
      );
      if (editingTransaction && editingTransaction.series_kind === "recurring" && useAverage) {
        // spec: lancamentos v3.24 — critério 55
        // (ao editar recorrente, o estado do checkbox de média é enviado explicitamente)
        data.use_average = useAverage.checked ? "1" : "0";
      }
      if (isEditing && shouldAskFutureReplication(data.id)) {
        if (averageChanged) {
          // spec: lancamentos v3.24 — critérios 56, 57 e 60
          // (flag de média alterada — marcada em série sem a marcação ou desmarcada
          //  em série que a tinha — não exibe modal e aplica em cascata)
          data.apply_to_future = true;
        } else {
          // spec: lancamentos v3.24 — critérios 46 e 58
          // (flag inalterada — ativa ou inativa — mantém o modal de escopo)
          const scope = await chooseSeriesEditScope("conta", Boolean(editingTransaction.use_average));
          if (!scope) {
            return;
          }
          data.apply_to_future = scope === "future";
        }
      }
      const response = await api(isEditing ? `/api/transactions/${data.id}` : "/api/transactions", {
        method: isEditing ? "PUT" : "POST",
        body: data,
      });
      state.transactionHighlightId = String(response.transaction?.id || data.id || "");
      resetTransactionForm();
      await refreshAfterTransactionChange();
      highlightSavedTransaction();
      setMessage(transactionMessage, isEditing ? "Lançamento atualizado." : "Lançamento salvo.", "success");
    } catch (error) {
      setMessage(transactionMessage, error.message, "error");
    } finally {
      setFormBusy(transactionForm, false);
      applyWalletAccountRestrictions();
      updateTransactionTypeState();
    }
  }

  function shouldAskFutureReplication(transactionId) {
    const transaction = findTransactionById(transactionId);
    return Boolean(transaction && transaction.series_id && (transaction.series_kind === "recurring" || isInstallmentTransaction(transaction)));
  }

  async function deleteTransaction(id) {
    try {
      const scope = await deleteSeriesScope(id, state.accountTransactions.length ? state.accountTransactions : state.transactions, "conta");
      if (scope === null) {
        return;
      }
      await api(`/api/transactions/${id}${scope}`, { method: "DELETE" });
      await refreshAfterTransactionChange();
      setMessage(transactionMessage, "Lançamento excluído.", "success");
    } catch (error) {
      setMessage(transactionMessage, error.message, "error");
    }
  }

  async function deleteSeriesScope(id, transactions, label) {
    const transaction = transactions.find((entry) => String(entry.id) === String(id));
    if (!transaction || !transaction.series_id) {
      return "";
    }
    const isSeries = transaction.series_kind === "recurring" || isInstallmentTransaction(transaction);
    if (!isSeries) {
      return "";
    }
    const scope = await decisionModal.choose({
      title: "Excluir lançamento da série",
      message: `Este lançamento pertence a uma série no módulo de ${label}. Como deseja excluir?`,
      actions: [
        { value: "single", label: "Excluir apenas este", variant: "ghost" },
        { value: "future", label: "Excluir este e os próximos", variant: "danger" },
        { value: null, label: "Voltar", variant: "ghost" },
      ],
    });
    if (!scope) {
      return null;
    }
    return scope === "future" ? "?scope=future" : "";
  }

  function chooseSeriesEditScope(label, useAverage = false) {
    return decisionModal.choose({
      title: "Aplicar alteração",
      message: useAverage
        ? `Esta série no módulo de ${label} calcula os valores futuros pela média. Escolha \"Apenas este lançamento\" para alterar somente esta ocorrência, sem recalcular os próximos; escolha \"Este e os próximos\" para recalculá-los pela média.`
        : `Este lançamento pertence a uma série no módulo de ${label}. Como deseja aplicar a mudança?`,
      actions: [
        { value: "single", label: "Apenas este lançamento", variant: "ghost" },
        { value: "future", label: "Este e os próximos", variant: "primary" },
        { value: null, label: "Voltar", variant: "ghost" },
      ],
    });
  }

  function findTransactionById(id) {
    return [...state.accountTransactions, ...state.transactions].find((entry) => String(entry.id) === String(id));
  }

  async function toggleTransactionReconciliation(id, reconciled) {
    try {
      await api(`/api/transactions/${id}/reconciliation`, {
        method: "PUT",
        body: { reconciled },
      });
      await refreshAfterTransactionChange();
    } catch (error) {
      setMessage(transactionMessage, error.message, "error");
    }
  }

  async function refreshAfterTransactionChange() {
    const [, accountsResponse, transactionsResponse] = await Promise.all([
      loadTransactionSlice(),
      api("/api/checking-accounts"),
      fetchAllListed("/api/transactions", "transactions"),
      loadCockpit(),
    ]);
    state.accounts = accountsResponse.accounts || [];
    ensureSelectedAccount();
    state.transactions = transactionsResponse || [];
    markPortfolioDirty();
    renderBaseViews();
    renderFinanceViews();
    renderPortfolio();
  }

  function resetTransactionForm() {
    classificationSelectionTouched = false;
    classificationSuggestionRequestId += 1;
    clearTimeout(classificationSuggestionTimer);
    if (transactionClassificationSuggestion) {
      transactionClassificationSuggestion.textContent = "";
    }
    const selectedAccountId = String(state.selectedAccountId || transactionAccount.value || "");
    transactionForm.reset();
    if (selectedAccountId && state.accounts.some((account) => String(account.id) === selectedAccountId)) {
      transactionAccount.value = selectedAccountId;
    }
    transactionForm.elements.id.value = "";
    transactionForm.elements.date.value = todayLocalDateValue();
    installmentCount.value = "2";
    recurrenceFrequency.value = "monthly";
    if (useAverage) {
      useAverage.checked = false;
    }
    destinationAmount.value = "";
    transferExchangeRate.value = "";
    investmentAmount.value = "";
    fillInvestmentOperation(null);
    transactionAmount.disabled = false;
    transactionAmount.required = true;
    transactionAmountRow.hidden = false;
    investmentAmountRow.hidden = true;
    transactionFormTitle.textContent = "Novo lançamento";
    cancelTransactionEditButton.hidden = false;
    transactionForm.querySelector('button[type="submit"]').textContent = "Salvar lançamento";
    seriesKind.disabled = false;
    updateSeriesState();
    applyWalletAccountDefault();
    applyWalletAccountRestrictions();
    updateTransactionTypeState();
  }

  function editTransaction(transaction) {
    setMessage(transactionMessage, "");
    transactionForm.elements.id.value = transaction.id;
    transactionType.value = isExchangeTransfer(transaction) ? "exchange" : isInvestmentTransfer(transaction) ? "investment" : transaction.type;
    transactionForm.elements.date.value = transaction.date;
    transactionForm.elements.description.value = transaction.description;
    transactionForm.elements.amount.value = moneyInputValue(transaction.amount);
    investmentAmount.value = transaction.investment_operation
      ? moneyInputValue(transaction.investment_operation.invested_amount)
      : "";
    transactionAccount.value = String(transaction.account_id);
    transactionForm.elements.notes.value = transaction.notes || "";
    transactionForm.elements.tags.value = (transaction.tags || []).join(", ");
    transactionForm.elements.exchange_rate_to_brl.value = (transaction.exchange_rate_to_brl || "1.000000").replace(".", ",");
    destinationAmount.value = transaction.destination_amount && Number(transaction.destination_amount) > 0
      ? moneyInputValue(transaction.destination_amount)
      : "";
    transferExchangeRate.value = transaction.transfer_exchange_rate && Number(transaction.transfer_exchange_rate) > 0
      ? transaction.transfer_exchange_rate.replace(".", ",")
      : "";
    fillInvestmentOperation(transaction.investment_operation);
    seriesKind.value = isInstallmentTransaction(transaction) ? "installment" : transaction.series_kind || "single";
    installmentCount.value = transaction.installment_count || "2";
    recurrenceFrequency.value = transaction.recurrence_frequency || "monthly";
    if (useAverage) {
      useAverage.checked = Boolean(transaction.use_average);
    }
    updateSeriesState();
    updateTransactionTypeState();
    applyWalletAccountRestrictions();
    const canChangeRepetition = canChangeCurrentTransactionRepetition();
    seriesKind.disabled = !canChangeRepetition;
    installmentCount.disabled = !canChangeRepetition || seriesKind.value !== "installment";
    recurrenceFrequency.disabled = !canChangeRepetition || seriesKind.value !== "recurring";
    if (transaction.destination_account_id) {
      destinationAccount.value = String(transaction.destination_account_id);
    }
    renderTransactionCategories();
    if (transaction.category_name) {
      transactionCategory.value = transaction.category_name;
    }
    renderTransactionSubcategories();
    if (transaction.subcategory_name) {
      transactionSubcategory.value = transaction.subcategory_name;
    }
    updateInvestmentFieldState();
    transactionFormTitle.textContent = "Editar lançamento";
    cancelTransactionEditButton.hidden = false;
    transactionForm.querySelector('button[type="submit"]').textContent = "Salvar alterações";
    transactionForm.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function fillInvestmentOperation(operation) {
    const fields = [
      "investment_asset_identifier",
      "investment_asset_name",
      "investment_cnpj",
      "investment_quantity",
      "investment_unit_price",
      "investment_brokerage_fee",
      "investment_exchange_fee",
      "investment_tax",
      "investment_other_costs",
      "investment_fixed_income_indexer",
      "investment_fixed_income_rate",
      "investment_fixed_income_maturity_date",
    ];
    for (const field of fields) {
      if (transactionForm.elements[field]) {
        transactionForm.elements[field].value = "";
      }
    }
    transactionForm.elements.investment_fixed_income_mode.value = "";
    if (transactionForm.elements.investment_emergency_reserve_eligible) {
      transactionForm.elements.investment_emergency_reserve_eligible.checked = false;
    }
    if (!operation) {
      updateInvestmentFieldState();
      return;
    }
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
    if (transactionForm.elements.investment_emergency_reserve_eligible) {
      transactionForm.elements.investment_emergency_reserve_eligible.checked = Boolean(operation.emergency_reserve_eligible);
    }
    updateInvestmentFieldState();
  }

  function decimalInputValue(value) {
    if (!value || Number(value) === 0) {
      return "";
    }
    return String(value).replace(".", ",");
  }

  function renderTransactionAccounts() {
    ensureSelectedAccount();
    const options = state.accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("");
    transactionAccount.innerHTML = options || '<option value="">Cadastre uma conta</option>';
    transactionForm.querySelector('button[type="submit"]').disabled = state.accounts.length === 0;
    renderImportTargets();

    if (state.selectedAccountId) {
      transactionAccount.value = state.selectedAccountId;
    }

    applyWalletAccountDefault();
    applyWalletAccountRestrictions();
    updateTransactionTypeState();
  }

  function renderTransactionCategories() {
    if (!transactionRequiresCategory()) {
      transactionCategory.innerHTML = '<option value="">Sem categoria</option>';
      transactionSubcategory.innerHTML = '<option value="">Sem subcategoria</option>';
      transactionCategory.disabled = true;
      transactionCategory.required = false;
      transactionSubcategory.disabled = true;
      transactionForm.querySelector('button[type="submit"]').disabled = state.accounts.length === 0;
      return;
    }
    const groupType = selectedTransactionGroup();
    const categories = state.categories.filter((category) => category.group_type === groupType);
    transactionCategory.innerHTML = categories.map((category) => (
      `<option value="${escapeHtml(category.name)}" data-category-id="${category.id}">${escapeHtml(category.name)}</option>`
    )).join("") || '<option value="">Cadastre uma categoria para este grupo</option>';
    transactionCategory.disabled = categories.length === 0;
    transactionCategory.required = true;
    transactionForm.querySelector('button[type="submit"]').disabled = state.accounts.length === 0 || categories.length === 0;
    renderTransactionSubcategories();
  }

  function renderTransactionSubcategories() {
    const category = selectedTransactionCategory();
    const subcategories = category ? category.subcategories || [] : [];
    transactionSubcategory.innerHTML = '<option value="">Sem subcategoria</option>' + subcategories.map((subcategory) => (
      `<option value="${escapeHtml(subcategory.name)}">${escapeHtml(transactionSubcategoryDisplayName(subcategory.name))}</option>`
    )).join("");
    transactionSubcategory.disabled = subcategories.length === 0;
  }

  function transactionSubcategoryDisplayName(name) {
    const normalized = normalizeSearch(name);
    if (normalized.startsWith("poupanca")) {
      return "Poupança";
    }
    return name;
  }

  function renderTransactionTagOptions() {
    if (!transactionTagOptions) {
      return;
    }
    transactionTagOptions.innerHTML = state.tags
      .map((tag) => `<option value="${escapeHtml(tag.name)}"></option>`)
      .join("");
  }

  function renderTransactions() {
    transactionMonthLabel.textContent = formatMonthShortLabel(state.transactionMonth);
    ensureSelectedAccount();
    if (state.selectedAccountId && transactionAccount.value !== state.selectedAccountId) {
      transactionAccount.value = state.selectedAccountId;
    }
    const accountTransactions = selectedAccountTransactions(state.accountTransactions);
    transactionSearch.value = state.transactionSearch || "";
    clearTransactionSearchButton.hidden = !state.transactionSearch;
    renderTransactionStatusFilters();
    const monthTransactions = selectedAccountTransactions(accountTransactions)
      .filter((transaction) => transaction.date.startsWith(state.transactionMonth));
    const searchedTransactions = monthTransactions.filter(matchesTransactionSearch);
    renderTransactionContextCount(searchedTransactions);
    const visibleTransactions = searchedTransactions.filter(matchesTransactionStatusFilter);

    currentBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(todayLocalDateValue(), accountTransactions, true));
    const forecastLimitDate = monthEndDate(state.transactionMonth);
    forecastBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(forecastLimitDate, accountTransactions, false));
    if (forecastBalanceLabel) {
      const account = state.accounts.find((entry) => String(entry.id) === String(state.selectedAccountId));
      const forecastDetail = accountHasPreferredCardForecast(account, forecastLimitDate)
        ? " Saldo do fim do mês (inclui despesas conciliadas de cartão)"
        : " Saldo do fim do mês";
      forecastBalanceLabel.innerHTML = `<span class="balance-kind-badge forecast"><span aria-hidden="true">○</span> Previsto</span>${forecastDetail}`;
    }
    renderBalanceHistory();
    renderTransactionCollection(transactionList, visibleTransactions, false, accountTransactions);
  }

  function renderTransactionStatusFilters() {
    transactionStatusFilterButtons.forEach((button) => {
      const isActive = button.dataset.transactionStatusFilter === state.transactionStatusFilter;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  }

  function renderTransactionContextCount(transactions) {
    const reconciled = transactions.filter((transaction) => transaction.reconciled_at).length;
    const pending = transactions.length - reconciled;
    const transactionLabel = transactions.length === 1 ? "lançamento" : "lançamentos";
    const reconciledLabel = reconciled === 1 ? "conciliado" : "conciliados";
    const pendingLabel = pending === 1 ? "pendente" : "pendentes";
    transactionContextCount.textContent = `${transactions.length} ${transactionLabel} · ${reconciled} ${reconciledLabel} · ${pending} ${pendingLabel}`;
  }

  function matchesTransactionStatusFilter(transaction) {
    if (state.transactionStatusFilter === "reconciled") {
      return Boolean(transaction.reconciled_at);
    }
    if (state.transactionStatusFilter === "pending") {
      return !transaction.reconciled_at;
    }
    return true;
  }

  function renderBalanceHistory() {
    if (!transactionBalanceHistoryChart) {
      return;
    }
    const account = state.accounts.find((entry) => String(entry.id) === String(state.selectedAccountId));
    if (!account) {
      transactionBalanceHistoryChart.innerHTML = stateMarkup("Selecione uma conta para visualizar a projeção de saldo.", { kind: "info" });
      return;
    }
    const transactions = selectedAccountTransactions(state.transactions.length ? state.transactions : state.accountTransactions);
    const rows = balanceHistoryRows(account, transactions);
    const path = balanceHistoryPath(rows, "past");
    const futurePath = balanceHistoryPath(rows, "future");
    const areaPath = balanceHistoryAreaPath(rows);
    const points = rows.map((row) => `
      <span class="invoice-history-point ${row.isCurrent ? "current" : ""} ${row.offset > 0 ? "future" : ""}" style="left: ${row.x}%; top: ${row.y}%"></span>
    `).join("");
    transactionBalanceHistoryChart.innerHTML = `
      <div class="invoice-history-rail" role="list">
        ${rows.map((row) => {
          const amountText = formatMoney(Math.abs(row.amount), row.currency);
          return `
          <button class="invoice-history-card ${row.isCurrent ? "current" : ""} ${row.offset > 0 ? "future" : ""}" type="button" data-transaction-balance-month="${escapeHtml(row.month)}" role="listitem" aria-current="${row.isCurrent ? "true" : "false"}">
            <span>${escapeHtml(row.label)}</span>
            <strong class="${chartAmountSizeClass(amountText)} ${row.amount < 0 ? "danger-text" : row.amount > 0 ? "positive-text" : ""}">${amountText}</strong>
          </button>
        `;
        }).join("")}
        <div class="invoice-history-plot" aria-hidden="true">
          <svg class="invoice-history-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <defs>
              <linearGradient id="accountBalanceHistoryAreaGradient" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.18"></stop>
                <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"></stop>
              </linearGradient>
            </defs>
            <path class="invoice-history-area account-balance-history-area" d="${areaPath}"></path>
            <path class="invoice-history-line" d="${path}"></path>
            <path class="invoice-history-line future" d="${futurePath}"></path>
          </svg>
          ${points}
        </div>
      </div>
    `;
  }

  function chartAmountSizeClass(text) {
    const length = String(text || "").replace(/\s/g, "").length;
    if (length >= 18) {
      return "chart-amount-xxs";
    }
    if (length >= 13) {
      return "chart-amount-xs";
    }
    if (length >= 10) {
      return "chart-amount-sm";
    }
    return "";
  }

  function balanceHistoryRows(account, transactions) {
    const rawRows = [-1, 0, 1, 2, 3].map((offset) => {
      const month = shiftMonth(state.transactionMonth, offset);
      const balance = getBalanceUntil(monthEndDate(month), transactions, offset < 0);
      const amount = balanceAmountForCurrency(balance, account.currency);
      return {
        offset,
        month,
        label: formatShortMonthName(month),
        description: offset < 0 ? "Conciliado" : "Previsto",
        amount,
        currency: account.currency,
        isCurrent: offset === 0,
      };
    });
    const values = rawRows.map((row) => row.amount);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    const xPositions = [10, 30, 50, 70, 90];
    return rawRows.map((row, index) => ({
      ...row,
      x: xPositions[index],
      y: range === 0
        ? balanceHistoryChartFlat
        : balanceHistoryChartBottom - ((row.amount - min) / range) * (balanceHistoryChartBottom - balanceHistoryChartTop),
    }));
  }

  function balanceAmountForCurrency(balance, currency) {
    if (balance instanceof Map) {
      if (balance.has(currency)) {
        return Number(balance.get(currency) || 0);
      }
      return [...balance.values()].reduce((total, value) => total + Number(value || 0), 0);
    }
    return Number(balance || 0);
  }

  function balanceHistoryPath(rows, mode = "all") {
    const visibleRows = mode === "future" ? rows.slice(1) : mode === "past" ? rows.slice(0, 2) : rows;
    if (visibleRows.length < 2) {
      return "";
    }
    return smoothBalancePath(visibleRows.map((row) => ({ x: row.x, y: row.y })));
  }

  function balanceHistoryAreaPath(rows) {
    const points = rows.map((row) => ({ x: row.x, y: row.y }));
    if (points.length < 2) {
      return "";
    }
    const line = smoothBalancePath(points);
    const first = points[0];
    const last = points[points.length - 1];
    return `${line} L ${last.x} ${balanceHistoryChartBaseline} L ${first.x} ${balanceHistoryChartBaseline} Z`;
  }

  function smoothBalancePath(points) {
    return points.reduce((path, point, index) => {
      if (index === 0) {
        return `M ${point.x} ${point.y}`;
      }
      const previous = points[index - 1];
      const midX = (previous.x + point.x) / 2;
      return `${path} C ${midX} ${previous.y}, ${midX} ${point.y}, ${point.x} ${point.y}`;
    }, "");
  }

  async function handleBalanceHistoryClick(event) {
    const button = event.target.closest("[data-transaction-balance-month]");
    if (!button) {
      return;
    }
    await setTransactionMonth(button.dataset.transactionBalanceMonth);
  }

  function selectedAccountTransactions(transactions = state.accountTransactions) {
    if (!state.selectedAccountId) {
      return [];
    }
    return transactions.filter((transaction) => (
      String(transaction.account_id) === String(state.selectedAccountId)
      || String(transaction.destination_account_id || "") === String(state.selectedAccountId)
    ));
  }

  function renderTransactionCollection(container, transactions, compact, balanceTransactions = transactions) {
    container.innerHTML = "";
    if (transactions.length === 0) {
      const hasActiveFilter = Boolean(state.transactionSearch) || state.transactionStatusFilter !== "all";
      container.append(emptyState(hasActiveFilter
        ? "Nenhum lançamento corresponde à busca ou ao filtro atual."
        : "Nenhum lançamento registrado ainda."));
      return;
    }
    const grouped = groupTransactionsByDate(transactions);
    const today = todayLocalDateValue();
    for (const [dateKey, items] of grouped.entries()) {
      const group = document.createElement("section");
      const containsHighlightedTransaction = items.some(
        (transaction) => String(transaction.id) === state.transactionHighlightId,
      );
      if (containsHighlightedTransaction) {
        setTransactionDayExpanded(dateKey, true);
      }
      const isExpanded = compact
        || containsHighlightedTransaction
        || isTransactionDayExpanded(dateKey, today);
      group.className = `transaction-group${compact ? "" : " collapsible-day"}${isExpanded ? "" : " is-collapsed"}`;
      const rows = items.map((transaction) => transactionTemplate(transaction, compact)).join("");
      const heading = document.createElement("h3");
      if (compact) {
        heading.textContent = formatDate(dateKey);
      } else {
        heading.className = "transaction-day-heading";
        heading.innerHTML = `
          <button class="transaction-day-toggle" type="button" data-transaction-day="${escapeHtml(dateKey)}" aria-expanded="${isExpanded}">
            <span class="transaction-day-chevron" aria-hidden="true">⌄</span>
            <span>${formatDate(dateKey)}</span>
            <span class="transaction-day-count">${items.length} ${items.length === 1 ? "lançamento" : "lançamentos"}</span>
          </button>
        `;
      }
      const content = document.createElement("div");
      content.className = "transaction-day-content";
      content.hidden = !isExpanded;
      content.innerHTML = `<div class="transaction-rows">${rows}</div>`;
      group.append(heading, content);
      if (!compact && isExpanded) {
        content.append(dailyBalance(dateKey, balanceTransactions));
      }
      container.append(group);
    }

    if (!compact) {
      const today = todayLocalDateValue();
      const monthEnd = monthEndDate(state.transactionMonth);
      const relevantTransactions = selectedAccountTransactions(state.accountTransactions).filter((transaction) => transaction.date <= monthEnd);
      const reconciledBalance = getBalanceUntil(today, relevantTransactions, true);
      const forecastBalance = getBalanceUntil(monthEnd, relevantTransactions, false);
      const subtotalSection = document.createElement("section");
      subtotalSection.className = "transaction-subtotals";
      subtotalSection.innerHTML = `
        <div class="subtotal-row">
          <span>Saldo atual (Conciliado)</span>
          <strong>${formatCurrencySummary(reconciledBalance)}</strong>
        </div>
        <div class="subtotal-row">
          <span>Saldo previsto (Todos os lançamentos)</span>
          <strong>${formatCurrencySummary(forecastBalance)}</strong>
        </div>
      `;
      container.append(subtotalSection);
    }
  }

  function handleTransactionListClick(event) {
    const dayToggle = event.target.closest("[data-transaction-day]");
    if (dayToggle) {
      const dateKey = dayToggle.dataset.transactionDay;
      setTransactionDayExpanded(dateKey, dayToggle.getAttribute("aria-expanded") !== "true");
      renderTransactions();
      return;
    }
    const editButton = event.target.closest("[data-edit-transaction-id]");
    if (editButton) {
      const transaction = selectedAccountTransactions(state.accountTransactions)
        .find((entry) => String(entry.id) === String(editButton.dataset.editTransactionId));
      if (transaction) {
        editTransaction(transaction);
      }
      return;
    }
    const reconcileButton = event.target.closest("[data-reconcile-id]");
    if (reconcileButton) {
      toggleTransactionReconciliation(
        reconcileButton.dataset.reconcileId,
        reconcileButton.dataset.reconciled !== "true",
      );
      return;
    }
    const deleteButton = event.target.closest("[data-transaction-id]");
    if (deleteButton) {
      deleteTransaction(deleteButton.dataset.transactionId);
    }
  }

  function transactionDayStateKey(dateKey) {
    return `${state.selectedAccountId || "none"}:${state.transactionMonth}:${dateKey}`;
  }

  function isTransactionDayExpanded(dateKey, today) {
    const key = transactionDayStateKey(dateKey);
    if (!expandedTransactionDays.has(key)) {
      expandedTransactionDays.set(key, dateKey >= today);
    }
    return expandedTransactionDays.get(key);
  }

  function setTransactionDayExpanded(dateKey, isExpanded) {
    expandedTransactionDays.set(transactionDayStateKey(dateKey), isExpanded);
  }

  function transactionTemplate(transaction, compact) {
    const isDestinationView = transaction.type === "transfer"
      && state.selectedAccountId
      && String(transaction.destination_account_id || "") === String(state.selectedAccountId)
      && String(transaction.account_id) !== String(state.selectedAccountId);
    const signal = isDestinationView ? "positive" : transaction.type === "income" ? "positive" : transaction.type === "expense" || transaction.type === "investment" ? "negative" : "neutral";
    const amountPrefix = isDestinationView ? "+" : transaction.type === "income" ? "" : transaction.type === "expense" || transaction.type === "transfer" || transaction.type === "investment" ? "-" : "";
    const displayAmount = isDestinationView && transaction.destination_amount && Number(transaction.destination_amount) > 0 ? transaction.destination_amount : transaction.amount;
    const displayCurrency = isDestinationView ? transaction.destination_account_currency || transaction.account_currency : transaction.account_currency;
    const destination = transaction.destination_account_name ? ` para ${escapeHtml(transaction.destination_account_name)}` : "";
    const accountRoute = isDestinationView
      ? `${escapeHtml(transaction.account_name)} para ${escapeHtml(transaction.destination_account_name || "Conta destino")}`
      : `${escapeHtml(transaction.account_name)}${destination}`;
    const typeLabel = isExchangeTransfer(transaction) ? "Câmbio" : isInvestmentTransaction(transaction) ? "Investimento" : transactionTypeLabel(transaction.type);
    const isReconciled = Boolean(transaction.reconciled_at);
    const convertedAmount = transaction.account_currency === "BRL" ? "" : `
          <span>${formatMoney(transaction.amount_brl, "BRL")}</span>
        `;
    const destinationConvertedAmount = isExchangeTransfer(transaction) ? `
          <span>+${formatMoney(transaction.destination_amount, transaction.destination_account_currency)}</span>
        ` : "";
    const conversionDetails = isDestinationView ? convertedAmount : `${destinationConvertedAmount}${convertedAmount}`;
    return `
      <article class="transaction-row ${signal} ${String(transaction.id) === state.transactionHighlightId ? "recently-saved" : ""}" data-rendered-transaction-id="${transaction.id}">
        <div>
          <strong>${escapeHtml(transaction.description)}</strong>
          <div class="account-meta">
            <span class="transaction-meta-secondary">${typeLabel}</span>
            <span class="transaction-account-route">${accountRoute}</span>
            <span class="reconciliation-status ${isReconciled ? "reconciled" : "pending"}"><span aria-hidden="true">${isReconciled ? "✓" : "○"}</span> ${isReconciled ? "Conciliado" : "Pendente"}</span>
            ${transactionSeriesLabel(transaction) ? `<span class="transaction-meta-secondary">${transactionSeriesLabel(transaction)}</span>` : ""}
            ${transaction.category_name ? `<span class="transaction-category-path transaction-meta-secondary">${escapeHtml(formatCategoryPath(transaction))}</span>` : ""}
            ${transaction.tags && transaction.tags.length ? `<span class="transaction-meta-secondary">${transaction.tags.map((tag) => `#${escapeHtml(tag)}`).join(" ")}</span>` : ""}
          </div>
        </div>
        <div class="transaction-amount">
          <strong>${amountPrefix}${formatMoney(displayAmount, displayCurrency)}</strong>
          ${conversionDetails}
          ${compact ? "" : `
            <div class="transaction-actions">
              ${launchActionButton("edit", "Editar lançamento", `data-edit-transaction-id="${transaction.id}"`)}
              ${launchActionButton("check", isReconciled ? "Desmarcar conciliação" : "Marcar como conciliado", `data-reconcile-id="${transaction.id}" data-reconciled="${isReconciled}"`, `reconcile-button ${isReconciled ? "active" : ""}`)}
              ${launchActionButton("trash", "Excluir lançamento", `data-transaction-id="${transaction.id}"`, "danger-action")}
            </div>
          `}
        </div>
      </article>
    `;
  }

  function launchActionButton(icon, label, attributes, extraClass = "") {
    const safeLabel = escapeHtml(label);
    return `
      <button class="launch-action-button ${extraClass}" type="button" ${attributes} title="${safeLabel}" aria-label="${safeLabel}" data-tooltip="${safeLabel}">
        ${launchActionIconSvg(icon)}
      </button>
    `;
  }

  function launchActionIconSvg(icon) {
    const icons = {
      "arrow-left": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M15 18l-6-6 6-6"/><path d="M20 12H9"/></svg>',
      "arrow-right": '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 18l6-6-6-6"/><path d="M4 12h11"/></svg>',
      check: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6L9 17l-5-5"/></svg>',
      edit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h4l11-11a2.8 2.8 0 0 0-4-4L4 16v4z"/><path d="M13 6l5 5"/></svg>',
      trash: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h18"/><path d="M8 6V4h8v2"/><path d="M6 6l1 15h10l1-15"/><path d="M10 11v6"/><path d="M14 11v6"/></svg>',
    };
    return icons[icon] || icons.edit;
  }

  function dailyBalance(dateKey, transactions = state.transactions) {
    const forecastBalance = getBalanceUntil(dateKey, transactions, false);
    const reconciledBalance = getBalanceUntil(dateKey, transactions, true);
    const row = document.createElement("div");
    row.className = "daily-balance";
    row.innerHTML = `
      ${dailyBalanceLine("Saldo previsto", forecastBalance)}
      ${dailyBalanceLine("Saldo conciliado", reconciledBalance)}
    `;
    return row;
  }

  function dailyBalanceLine(label, balance) {
    const total = [...balance.values()].reduce((sum, value) => sum + Number(value), 0);
    const balanceClass = total < 0 ? "danger-text" : total > 0 ? "positive-text" : "";
    const isReconciled = label.includes("conciliado");
    return `
      <div class="daily-balance-line">
        <span><span class="balance-kind-badge ${isReconciled ? "reconciled" : "forecast"}"><span aria-hidden="true">${isReconciled ? "✓" : "○"}</span> ${isReconciled ? "Conciliado" : "Previsto"}</span></span>
        <strong class="${balanceClass}">${formatCurrencySummary(balance)}</strong>
      </div>
    `;
  }

  function highlightSavedTransaction() {
    if (!state.transactionHighlightId) {
      return;
    }
    const highlightedRow = transactionList.querySelector(
      `[data-rendered-transaction-id="${state.transactionHighlightId}"]`,
    );
    if (!highlightedRow) {
      state.transactionHighlightId = "";
      return;
    }
    highlightedRow.scrollIntoView({ behavior: "smooth", block: "center" });
    window.setTimeout(() => {
      highlightedRow.classList.remove("recently-saved");
      state.transactionHighlightId = "";
    }, 2200);
  }

  function matchesTransactionSearch(transaction) {
    const query = normalizeSearch(state.transactionSearch);
    if (!query) {
      return true;
    }
    const haystack = normalizeSearch([
      transaction.description,
      transaction.account_name,
      transaction.destination_account_name,
      transaction.category_name,
      transaction.subcategory_name,
      transaction.tag_name,
      transaction.amount,
      transaction.amount_brl,
    ].filter(Boolean).join(" "));
    return haystack.includes(query);
  }

  function updateTransactionTypeState() {
    const isInvestment = transactionType.value === "investment";
    const isExchange = transactionType.value === "exchange";
    const isTransfer = transactionType.value === "transfer" || isExchange;
    const needsCategory = !isTransfer;
    const destinationOptions = destinationAccountOptions(false, isExchange);
    destinationAccount.innerHTML = destinationOptions || '<option value="">Cadastre uma conta compatível</option>';
    destinationAccountLabel.hidden = !isTransfer;
    destinationAccount.disabled = !isTransfer || !destinationOptions;
    exchangeTransferFields.hidden = !isExchange;
    destinationAmount.disabled = !isExchange;
    transferExchangeRate.disabled = !isExchange;
    destinationAmount.required = isExchange;
    transferExchangeRate.required = false;
    investmentOperationFields.hidden = !isInvestment;
    investmentAmount.disabled = !isInvestment;
    investmentAmount.required = isInvestment;
    transactionAmountRow.hidden = isInvestment;
    investmentAmountRow.hidden = !isInvestment;
    transactionAmount.disabled = isInvestment;
    transactionAmount.required = !isInvestment;
    transactionCategoryRow.hidden = !needsCategory;
    transactionCategory.disabled = !needsCategory;
    transactionCategory.required = needsCategory;
    transactionSubcategory.disabled = !needsCategory;
    renderTransactionCategories();
    updateSeriesState();
    updateInvestmentFieldState();
    updateExchangeRateState();
    updateTransferExchangeRateState();
  }

  async function handleTransactionAccountChange() {
    const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    if (account) {
      state.selectedAccountId = account.id;
    }
    await loadTransactionSlice();
    applyWalletAccountDefault();
    applyWalletAccountRestrictions();
    updateTransactionTypeState();
    renderTransactions();
  }

  function applyWalletAccountDefault() {
    const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    if (account && account.account_type === "investment" && !transactionForm.elements.id.value) {
      transactionType.value = "investment";
    }
  }

  function applyWalletAccountRestrictions() {
    const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    if (account && account.account_type === "wallet") {
      const currentType = transactionType.value;
      if (!["income", "expense", "transfer"].includes(currentType)) {
        transactionType.value = "expense";
      }
      for (const option of transactionType.options) {
        option.disabled = option.value === "investment" || option.value === "exchange";
      }
      seriesKind.value = "single";
      seriesKind.disabled = true;
      transactionForm.elements.tags.value = "";
    } else {
      for (const option of transactionType.options) {
        option.disabled = false;
      }
      seriesKind.disabled = !canChangeCurrentTransactionRepetition();
    }
  }

  function updateInvestmentFieldState() {
    const isInvestment = transactionType.value === "investment";
    const cat = transactionCategory.value;
    const isSavings = isInvestmentSavingsSelection();
    const usesFundQuote = cat === "Fundos de Investimentos" || cat === "Previdência Privada";
    const canBeEmergencyReserve = isInvestment && (cat === "Renda Fixa" || isSavings);
    investmentFundFields.hidden = !isInvestment || !usesFundQuote;
    if (fetchInvestmentFundQuoteButton) {
      fetchInvestmentFundQuoteButton.disabled = investmentFundFields.hidden;
    }
    if (investmentFundQuoteHint && investmentFundFields.hidden) {
      investmentFundQuoteHint.textContent = "";
      investmentFundQuoteHint.className = "field-hint";
    }
    investmentFixedFields.hidden = !isInvestment || cat !== "Renda Fixa" || isSavings;
    investmentPricingFields.hidden = isInvestment && (cat === "Renda Fixa" || isSavings);
    if (investmentTradingCostFields) {
      investmentTradingCostFields.hidden = !isInvestment || isSavings;
    }
    if (investmentTaxCostFields) {
      investmentTaxCostFields.hidden = !isInvestment || isSavings;
    }
    if (investmentEmergencyReserveFields) {
      investmentEmergencyReserveFields.hidden = !canBeEmergencyReserve;
    }
    for (const field of investmentOperationFields.querySelectorAll("input, select")) {
      field.disabled = !isInvestment;
    }
    for (const field of investmentFundFields.querySelectorAll("input, select")) {
      field.disabled = !isInvestment || investmentFundFields.hidden;
    }
    for (const field of investmentFixedFields.querySelectorAll("input, select")) {
      field.disabled = !isInvestment || investmentFixedFields.hidden;
    }
    for (const field of investmentPricingFields.querySelectorAll("input, select")) {
      field.disabled = investmentPricingFields.hidden;
    }
    if (investmentTradingCostFields) {
      for (const field of investmentTradingCostFields.querySelectorAll("input, select")) {
        field.disabled = investmentTradingCostFields.hidden;
      }
    }
    if (investmentTaxCostFields) {
      for (const field of investmentTaxCostFields.querySelectorAll("input, select")) {
        field.disabled = investmentTaxCostFields.hidden;
      }
    }
    if (investmentEmergencyReserveFields) {
      for (const field of investmentEmergencyReserveFields.querySelectorAll("input")) {
        field.disabled = !canBeEmergencyReserve;
        if (!canBeEmergencyReserve) {
          field.checked = false;
        }
      }
    }
    syncInvestmentFixedIncomeRateHint();
    if (isSavings) {
      transactionForm.elements.investment_asset_identifier.value = "POUPANCA";
      if (!transactionForm.elements.investment_asset_name.value) {
        transactionForm.elements.investment_asset_name.value = "Poupança";
      }
    } else if (transactionForm.elements.investment_asset_identifier.value === "POUPANCA") {
      transactionForm.elements.investment_asset_identifier.value = "";
    }
    investmentAmount.required = isInvestment;
    investmentAmount.disabled = !isInvestment;
  }

  async function fetchInvestmentFundQuote() {
    const cnpjField = transactionForm.elements.investment_cnpj;
    const unitPriceField = transactionForm.elements.investment_unit_price;
    const cnpj = String(cnpjField?.value || "").trim();
    if (!cnpj) {
      setFundQuoteHint("Informe o CNPJ do fundo antes de buscar a cota.", "error");
      cnpjField?.focus();
      return;
    }
    if (unitPriceField?.value.trim()) {
      const overwrite = await decisionModal.choose({
        title: "Substituir preço unitário?",
        message: "O campo Preço unitário já tem valor. Deseja substituir pela cota retornada pela Mais Retorno?",
        actions: [
          { value: "replace", label: "Substituir", variant: "primary" },
          { value: null, label: "Manter atual", variant: "ghost" },
        ],
      });
      if (!overwrite) {
        return;
      }
    }
    const previousLabel = fetchInvestmentFundQuoteButton?.textContent || "Buscar cota";
    if (fetchInvestmentFundQuoteButton) {
      fetchInvestmentFundQuoteButton.disabled = true;
      fetchInvestmentFundQuoteButton.textContent = "Buscando...";
    }
    setFundQuoteHint("Consultando a Mais Retorno...");
    try {
      const quote = await api(`/api/portfolio/fund-quote?cnpj=${encodeURIComponent(cnpj)}`);
      unitPriceField.value = moneyInputValue(quote.unit_price);
      setFundQuoteHint(
        `Cota de ${formatDate(quote.quote_date)} preenchida. Confira com o comprovante antes de salvar.`,
        "success",
      );
    } catch (error) {
      setFundQuoteHint(error.message || "Nao foi possivel buscar a cota do fundo.", "error");
    } finally {
      if (fetchInvestmentFundQuoteButton) {
        fetchInvestmentFundQuoteButton.disabled = investmentFundFields.hidden;
        fetchInvestmentFundQuoteButton.textContent = previousLabel;
      }
    }
  }

  function setFundQuoteHint(text, tone = "") {
    if (!investmentFundQuoteHint) {
      return;
    }
    investmentFundQuoteHint.textContent = text;
    investmentFundQuoteHint.className = `field-hint ${tone}`.trim();
  }

  function isInvestmentSavingsSelection() {
    if (transactionType.value !== "investment") {
      return false;
    }
    return normalizeSearch([
      transactionCategory.value,
      transactionSubcategory.value,
      transactionForm.elements.investment_asset_identifier.value,
    ].join(" ")).includes("poupanca");
  }

  function updateSeriesState() {
    const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    const isWallet = account && account.account_type === "wallet";
    if (isWallet) {
      seriesKind.value = "single";
    }
    const canChangeRepetition = canChangeCurrentTransactionRepetition();
    seriesKindRow.hidden = Boolean(isWallet);
    seriesKind.disabled = Boolean(isWallet) || !canChangeRepetition;
    const isInstallment = seriesKind.value === "installment";
    const isRecurring = seriesKind.value === "recurring";
    installmentCountLabel.hidden = !isInstallment;
    installmentCount.disabled = !isInstallment || !canChangeRepetition;
    recurrenceFields.hidden = !isRecurring;
    recurrenceFrequency.disabled = !isRecurring || !canChangeRepetition;
    if (recurrenceAverageFields) {
      recurrenceAverageFields.hidden = !isRecurring;
    }
    if (useAverage) {
      // spec: lancamentos v3.24 — criterio 52
      // (na edicao de um recorrente o checkbox de media fica habilitado;
      //  so a repeticao/frequencia permanecem travadas na serie)
      useAverage.disabled = !isRecurring;
    }
  }

  function canChangeCurrentTransactionRepetition() {
    const editingId = transactionForm.elements.id.value;
    if (!editingId) {
      return true;
    }
    const transaction = findTransactionById(editingId);
    return Boolean(transaction && !transaction.series_id);
  }

  function shiftTransactionMonth(delta) {
    setTransactionMonth(shiftMonth(state.transactionMonth, delta));
  }

  async function setTransactionMonth(month) {
    if (!isValidMonthValue(month)) {
      return;
    }
    state.transactionMonth = month;
    await loadTransactionSlice();
    renderTransactions();
  }

  function selectedTransactionGroup() {
    if (transactionType.value === "income") {
      return "income";
    }
    if (transactionType.value === "investment" || transactionType.value === "exchange") {
      return "investment";
    }
    return "expense";
  }

  function transactionRequiresCategory() {
    return transactionType.value !== "transfer" && transactionType.value !== "exchange";
  }

  function selectedTransactionCategory() {
    return state.categories.find((category) => (
      category.group_type === selectedTransactionGroup() && category.name === transactionCategory.value
    ));
  }

  async function updateExchangeRateState() {
    exchangeRateLabel.hidden = true;
    exchangeRate.type = "hidden";
    exchangeRate.disabled = false;
    exchangeRate.placeholder = "";
    exchangeRate.value = "1,000000";
    const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    const dateValue = transactionForm.elements.date.value;
    const isEditing = Boolean(transactionForm.elements.id.value);
    if (isEditing || !account || account.currency === "BRL" || !dateValue) {
      return;
    }
    try {
      const rate = await exchangeRateToBrl(account.currency, dateValue);
      exchangeRate.value = rate.toLocaleString("pt-BR", {
        minimumFractionDigits: 6,
        maximumFractionDigits: 6,
      });
    } catch {
      exchangeRateLabelText.textContent = `Cotação (${account.currency} → BRL)`;
      exchangeRate.type = "text";
      exchangeRate.value = "";
      exchangeRate.placeholder = "Informe a cotação manualmente (ex.: 5,900000)";
      exchangeRateLabel.hidden = false;
    }
  }

  async function updateTransferExchangeRateState() {
    if (transactionType.value !== "exchange") {
      return;
    }
    const source = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    const destination = state.accounts.find((entry) => String(entry.id) === destinationAccount.value);
    if (!source || !destination || source.currency === destination.currency || !transactionForm.elements.date.value) {
      return;
    }
    transferExchangeRate.placeholder = "Buscando cotação...";
    try {
      const [sourceToBrl, destinationToBrl] = await Promise.all([
        exchangeRateToBrl(source.currency, transactionForm.elements.date.value),
        exchangeRateToBrl(destination.currency, transactionForm.elements.date.value),
      ]);
      const rate = sourceToBrl / destinationToBrl;
      transferExchangeRate.value = rate.toLocaleString("pt-BR", {
        minimumFractionDigits: 6,
        maximumFractionDigits: 6,
      });
      updateDestinationAmountFromRate();
    } catch (error) {
      transferExchangeRate.placeholder = "Informe a cotação manual";
    }
  }

  function syncInvestmentFixedIncomeRateHint() {
    const mode = investmentFixedIncomeMode.value;
    if (mode === "pre") {
      investmentFixedIncomeRateLabel.textContent = "Taxa Anual (% a.a.)";
      investmentFixedIncomeRate.placeholder = "Ex.: 12,30 (para 12,30% a.a.)";
    } else if (mode === "post") {
      investmentFixedIncomeRateLabel.textContent = "Percentual do Indexador (%)";
      investmentFixedIncomeRate.placeholder = "Ex.: 123 (deixe vazio para 100%)";
    } else if (mode === "hybrid") {
      investmentFixedIncomeRateLabel.textContent = "Taxa Adicional Anual (% a.a.)";
      investmentFixedIncomeRate.placeholder = "Ex.: 6,50 (para IPCA + 6,50% a.a.)";
    } else {
      investmentFixedIncomeRateLabel.textContent = "Taxa";
      investmentFixedIncomeRate.placeholder = "Ex.: 6,50";
    }
    syncFixedIncomeModeButtons(transactionForm, "investment", mode);
    updateFixedIncomePreview({
      mode,
      indexer: investmentFixedIncomeIndexer.value,
      rate: investmentFixedIncomeRate.value,
      preview: investmentFixedIncomePreview,
      fallbackAsset: transactionForm.elements.investment_asset_identifier.value || transactionForm.elements.investment_asset_name.value,
    });
  }

  function applyInvestmentFixedIncomePreset(preset) {
    const [mode, indexer, rate] = preset.split(":");
    investmentFixedIncomeMode.value = mode || "";
    investmentFixedIncomeIndexer.value = indexer || "";
    investmentFixedIncomeRate.value = rate || "";
    syncInvestmentFixedIncomeRateHint();
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

  async function exchangeRateToBrl(currency, dateValue) {
    if (currency === "BRL") {
      return 1;
    }
    const response = await api(`/api/exchange-rate?currency=${encodeURIComponent(currency)}&date=${encodeURIComponent(dateValue)}`);
    return Number(response.rate);
  }

  function updateDestinationAmountFromRate() {
    if (transactionType.value !== "exchange") {
      return;
    }
    const amount = parseDecimalInput(transactionForm.elements.amount.value);
    const rate = parseDecimalInput(transferExchangeRate.value);
    if (!amount || !rate) {
      return;
    }
    destinationAmount.value = (amount * rate).toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function groupTransactionsByDate(transactions) {
    const groups = new Map();
    for (const transaction of transactions) {
      if (!groups.has(transaction.date)) {
        groups.set(transaction.date, []);
      }
      groups.get(transaction.date).push(transaction);
    }
    return groups;
  }

  function destinationAccountOptions(investmentOnly, exchangeOnly = false) {
    const sourceAccount = state.accounts.find((account) => String(account.id) === transactionAccount.value);
    return state.accounts
      .filter((account) => String(account.id) !== transactionAccount.value)
      .filter((account) => !sourceAccount || (exchangeOnly ? account.currency !== sourceAccount.currency : account.currency === sourceAccount.currency))
      .filter((account) => !investmentOnly || account.account_type === "investment")
      .map((account) => `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`)
      .join("");
  }

  return {
    loadTransactionSlice,
    refreshAfterTransactionChange,
    resetTransactionForm,
    editTransaction,
    findTransactionById,
    renderTransactionAccounts,
    renderTransactionCategories,
    renderTransactionSubcategories,
    renderTransactionTagOptions,
    renderTransactions,
    renderTransactionCollection,
    updateTransactionTypeState,
    selectedAccountTransactions,
    deleteSeriesScope,
    launchActionButton,
    shiftTransactionMonth,
    setTransactionMonth,
    highlightSavedTransaction,
  };
}
