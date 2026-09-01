import { renderCollectionRows, destroyVirtualLists } from "./virtual-list.js";
import { createAssetAutocomplete } from "./asset-autocomplete.js";
import { createTransactionSliceLoader } from "./transaction-slice-loader.js";
import { createTransactionReconciliation } from "./transaction-reconciliation.js";
import { createTransactionRefresh } from "./transaction-refresh.js";
import { createClassificationSuggestion } from "./classification-suggestion.js";
import { createTransactionBalanceChart } from "./transaction-balance-chart.js";
import { createTransactionList } from "./transaction-list.js";
import { createTransactionInvestmentForm } from "./transaction-investment-form.js";
import { createTransactionForm } from "./transaction-form.js";

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
  markPortfolioDirty,
  renderBaseViews,
  renderFinanceViews,
  renderImportTargets,
}) {
  const transactionSliceLoader = createTransactionSliceLoader({ state, api, fetchAllListed, ensureSelectedAccount });
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
  const reconciliation = createTransactionReconciliation({
    state, api, markDirty: transactionSliceLoader.markDirty,
    loadSlice: transactionSliceLoader.load, render: renderTransactions, markPortfolioDirty,
    reportError: (message) => setMessage(transactionMessage, message, "error"),
  });
  const expandedTransactionDays = new Map();
  const investmentAssetIdentifier = transactionForm.elements.investment_asset_identifier;
  const investmentAssetAutocomplete = createAssetAutocomplete({
    input: investmentAssetIdentifier,
    nameInput: transactionForm.elements.investment_asset_name,
    getPositions: () => state.portfolio?.positions || [],
  });
  const investmentForm = createTransactionInvestmentForm({
    elements,
    api,
    decisionModal,
    normalizeSearch,
    moneyInputValue,
    decimalInputValue,
    formatDate,
  });
  const baseTransactionForm = createTransactionForm({ state, elements, api });
  const classificationSuggestion = createClassificationSuggestion({
    api,
    form: transactionForm,
    typeInput: transactionType,
    categoryInput: transactionCategory,
    subcategoryInput: transactionSubcategory,
    messageElement: transactionClassificationSuggestion,
    renderSubcategories: renderTransactionSubcategories,
    afterApply: investmentForm.updateFieldState,
    allowedTypes: ["expense", "income", "investment"],
  });
  investmentAssetIdentifier.addEventListener("focus", async () => {
    if (!state.portfolio || state.portfolioDirty) {
      try {
        state.portfolio = await api("/api/portfolio");
        state.portfolioDirty = false;
        investmentAssetAutocomplete.refresh();
      } catch {
        // A digitação livre continua disponível mesmo se o catálogo não carregar.
      }
    }
  });

  transactionForm.addEventListener("submit", handleTransactionSubmit);
  transactionType.addEventListener("change", () => {
    applyWalletAccountRestrictions();
    updateTransactionTypeState();
    classificationSuggestion.schedule();
  });
  transactionAccount.addEventListener("change", handleTransactionAccountChange);
  investmentAmount.addEventListener("input", () => {
    if (transactionType.value === "investment") {
      transactionAmount.value = investmentAmount.value;
    }
  });
  transactionCategory.addEventListener("change", () => {
    classificationSuggestion.markSelectionTouched();
    renderTransactionSubcategories();
    updateInvestmentFieldState();
  });
  transactionSubcategory.addEventListener("change", () => {
    classificationSuggestion.markSelectionTouched();
    updateInvestmentFieldState();
  });
  transactionForm.elements.description.addEventListener("input", classificationSuggestion.schedule);
  seriesKind.addEventListener("change", updateSeriesState);
  previousMonthButton.addEventListener("click", () => shiftTransactionMonth(-1));
  todayMonthButton.addEventListener("click", () => setTransactionMonth(currentMonthValue()));
  transactionMonthLabel.addEventListener("click", (event) => {
    event.stopPropagation();
    openMonthPicker(event.currentTarget, state.transactionMonth, setTransactionMonth);
  });
  nextMonthButton.addEventListener("click", () => shiftTransactionMonth(1));
  transactionList.addEventListener("click", handleTransactionListClick);
  cancelTransactionEditButton.addEventListener("click", resetTransactionForm);

  const loadTransactionSlice = transactionSliceLoader.load;

  function getBalanceUntil(limitDate, _transactions = null, reconciledOnly = false) {
    const row = state.balanceProjection?.balances?.[limitDate];
    return new Map(Object.entries(row?.[reconciledOnly ? "reconciled" : "projected"] || {}));
  }

  function accountHasPreferredCardForecast(account, limitDate) {
    if (!account) return false;
    return Boolean(state.balanceProjection?.preferred_card_forecasts?.[`${account.id}:${limitDate}`]);
  }

  const transactionBalanceChart = createTransactionBalanceChart({
    state,
    element: transactionBalanceHistoryChart,
    formatMoney,
    formatShortMonthName,
    escapeHtml,
    shiftMonth,
    monthEndDate,
    getBalanceUntil,
    selectedAccountTransactions,
    setTransactionMonth,
  });

  const transactionListView = createTransactionList({
    state,
    elements,
    formatMonthShortLabel,
    formatCurrencySummary,
    todayLocalDateValue,
    monthEndDate,
    ensureSelectedAccount,
    selectedAccountTransactions,
    getBalanceUntil,
    accountHasPreferredCardForecast,
    balanceChart: transactionBalanceChart,
    renderCollection: renderTransactionCollection,
    matchesSearch: matchesTransactionSearch,
  });

  const refreshAfterTransactionChange = createTransactionRefresh({
    state, api, fetchAllListed, loader: transactionSliceLoader,
    render: renderTransactions, markPortfolioDirty,
    renderAuxiliary: () => { renderBaseViews(); renderFinanceViews(); },
    reportError: message => setMessage(transactionMessage, message, "error"),
  });

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
        // spec: lancamentos v3.34 — critério 55
        // (ao editar recorrente, o estado do checkbox de média é enviado explicitamente)
        data.use_average = useAverage.checked ? "1" : "0";
      }
      if (isEditing && shouldAskFutureReplication(data.id)) {
        if (averageChanged) {
          // spec: lancamentos v3.34 — critérios 56, 57 e 60
          // (flag de média alterada — marcada em série sem a marcação ou desmarcada
          //  em série que a tinha — não exibe modal e aplica em cascata)
          data.apply_to_future = true;
        } else {
          // spec: lancamentos v3.34 — critérios 46 e 58
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
      setMessage(transactionMessage, isEditing ? "Lançamento atualizado." : "Lançamento salvo.", "success");
      await refreshAfterTransactionChange({ transaction: response.transaction });
      highlightSavedTransaction();
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
      setMessage(transactionMessage, "Lançamento excluído.", "success");
      await refreshAfterTransactionChange({ deletedId: id });
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
    await reconciliation.toggle(id, reconciled);
  }

  function resetTransactionForm() {
    classificationSuggestion.reset();
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
    investmentForm.fill(operation);
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
    transactionListView.render();
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
    destroyVirtualLists(container);
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
      const rowsContainer = document.createElement("div");
      rowsContainer.className = "transaction-rows";
      content.append(rowsContainer);
      group.append(heading, content);
      container.append(group);
      renderCollectionRows(rowsContainer, items, {
        expanded: isExpanded, virtual: !compact, rowHeight: 86,
        initialIndex: items.findIndex(transaction => String(transaction.id) === state.transactionHighlightId),
        renderItem: transaction => transactionTemplate(transaction, compact),
      });
      if (!compact && isExpanded) {
        content.append(dailyBalance(dateKey, balanceTransactions));
      }
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
          <strong>${state.balanceProjection ? formatCurrencySummary(reconciledBalance) : "—"}</strong>
        </div>
        <div class="subtotal-row">
          <span>Saldo previsto (Todos os lançamentos)</span>
          <strong>${state.balanceProjection ? formatCurrencySummary(forecastBalance) : "—"}</strong>
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
              ${launchActionButton("check", isReconciled ? "Desmarcar conciliação" : "Marcar como conciliado", `data-reconcile-id="${transaction.id}" data-reconciled="${isReconciled}" ${reconciliation.isPending(transaction.id) ? 'disabled aria-busy="true"' : ""}`, `reconcile-button ${isReconciled ? "active" : ""}`)}
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
        <strong class="${balanceClass}">${state.balanceProjection ? formatCurrencySummary(balance) : "—"}</strong>
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
    applyWalletAccountDefault();
    applyWalletAccountRestrictions();
    updateTransactionTypeState();
    await loadSelectedTransactionSlice();
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
    investmentForm.updateFieldState();
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
      // spec: lancamentos v3.34 — criterio 52
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
    await loadSelectedTransactionSlice();
  }

  async function loadSelectedTransactionSlice() {
    const request = loadTransactionSlice();
    renderTransactions();
    try {
      await request;
    } catch (error) {
      setMessage(transactionMessage, error.message, "error");
    }
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
    return baseTransactionForm.updateExchangeRateState();
  }

  async function updateTransferExchangeRateState() {
    return baseTransactionForm.updateTransferExchangeRateState();
  }

  async function updateDestinationAmountFromRate() {
    return baseTransactionForm.updateDestinationAmountFromRate();
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
    markTransactionSliceDirty: transactionSliceLoader.markDirty,
    resetTransactionSliceCache: transactionSliceLoader.reset,
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
