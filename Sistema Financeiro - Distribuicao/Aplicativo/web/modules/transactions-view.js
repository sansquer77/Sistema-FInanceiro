export function registerTransactionsView({
  state,
  elements,
  api,
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
  ensureSelectedAccount,
  getBalanceUntil,
  loadCockpit,
  markPortfolioDirty,
  renderFinanceViews,
  renderPortfolio,
  renderImportTargets,
}) {
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
    investmentFundFields,
    investmentFixedFields,
    transactionCategory,
    transactionCategoryRow,
    transactionSubcategory,
    seriesKind,
    seriesKindRow,
    installmentCount,
    installmentCountLabel,
    recurrenceFields,
    recurrenceFrequency,
    recurrenceCount,
    exchangeRate,
    exchangeRateLabel,
    cancelTransactionEditButton,
    transactionMonthLabel,
    previousMonthButton,
    todayMonthButton,
    nextMonthButton,
    currentBalanceSummary,
    forecastBalanceSummary,
    transactionSearch,
  } = elements;

  transactionForm.addEventListener("submit", handleTransactionSubmit);
  transactionType.addEventListener("change", () => {
    applyWalletAccountRestrictions();
    updateTransactionTypeState();
  });
  transactionAccount.addEventListener("change", handleTransactionAccountChange);
  destinationAccount.addEventListener("change", updateTransferExchangeRateState);
  investmentAmount.addEventListener("input", () => {
    if (transactionType.value === "investment") {
      transactionAmount.value = investmentAmount.value;
    }
  });
  transactionCategory.addEventListener("change", () => {
    renderTransactionSubcategories();
    updateInvestmentFieldState();
  });
  transactionSubcategory.addEventListener("change", updateInvestmentFieldState);
  seriesKind.addEventListener("change", updateSeriesState);
  transactionForm.elements.date.addEventListener("change", updateExchangeRateState);
  transactionForm.elements.date.addEventListener("change", updateTransferExchangeRateState);
  transactionForm.elements.amount.addEventListener("input", updateDestinationAmountFromRate);
  transferExchangeRate.addEventListener("input", updateDestinationAmountFromRate);
  previousMonthButton.addEventListener("click", () => shiftTransactionMonth(-1));
  todayMonthButton.addEventListener("click", () => setTransactionMonth(currentMonthValue()));
  transactionMonthLabel.addEventListener("click", (event) => {
    event.stopPropagation();
    openMonthPicker(event.currentTarget, state.transactionMonth, setTransactionMonth);
  });
  nextMonthButton.addEventListener("click", () => shiftTransactionMonth(1));
  transactionSearch.addEventListener("input", renderTransactions);
  transactionList.addEventListener("click", handleTransactionListClick);
  cancelTransactionEditButton.addEventListener("click", resetTransactionForm);

  async function loadTransactionSlice() {
    ensureSelectedAccount();
    const requestId = ++state.transactionSliceRequestId;
    const accountId = String(state.selectedAccountId || "");
    const month = state.transactionMonth;
    if (!state.selectedAccountId) {
      state.accountTransactions = [];
      return;
    }
    const response = await api(`/api/transactions?month=${encodeURIComponent(month)}&account_id=${encodeURIComponent(accountId)}`);
    if (
      requestId !== state.transactionSliceRequestId
      || month !== state.transactionMonth
      || accountId !== String(state.selectedAccountId || "")
    ) {
      return;
    }
    state.accountTransactions = response.transactions || [];
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
      if (isEditing && shouldAskFutureReplication(data.id)) {
        data.apply_to_future = window.confirm("Replicar esta alteração nos próximos lançamentos desta série? Lançamentos passados ou conciliados não serão alterados.");
      }
      await api(isEditing ? `/api/transactions/${data.id}` : "/api/transactions", {
        method: isEditing ? "PUT" : "POST",
        body: data,
      });
      resetTransactionForm();
      await refreshAfterTransactionChange();
      setMessage(transactionMessage, isEditing ? "Lançamento atualizado." : "Lançamento salvo.", "success");
    } catch (error) {
      setMessage(transactionMessage, error.message, "error");
    } finally {
      setFormBusy(transactionForm, false);
      updateInvestmentFieldState();
    }
  }

  function shouldAskFutureReplication(transactionId) {
    const transaction = findTransactionById(transactionId);
    return Boolean(transaction && transaction.series_id && (transaction.series_kind === "recurring" || isInstallmentTransaction(transaction)));
  }

  async function deleteTransaction(id) {
    try {
      const scope = deleteSeriesScope(id, state.accountTransactions.length ? state.accountTransactions : state.transactions, "conta");
      await api(`/api/transactions/${id}${scope}`, { method: "DELETE" });
      await refreshAfterTransactionChange();
      setMessage(transactionMessage, "Lançamento excluído.", "success");
    } catch (error) {
      setMessage(transactionMessage, error.message, "error");
    }
  }

  function deleteSeriesScope(id, transactions, label) {
    const transaction = transactions.find((entry) => String(entry.id) === String(id));
    if (!transaction || !transaction.series_id) {
      return "";
    }
    const isSeries = transaction.series_kind === "recurring" || isInstallmentTransaction(transaction);
    if (!isSeries) {
      return "";
    }
    const replicate = window.confirm(`Este lançamento pertence a uma série. Clique em OK para apagar este lançamento e os próximos lançamentos futuros não conciliados da mesma série no módulo de ${label}. Clique em Cancelar para apagar apenas este lançamento.`);
    return replicate ? "?scope=future" : "";
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
    await Promise.all([
      loadTransactionSlice(),
      loadCockpit(),
    ]);
    markPortfolioDirty();
    renderFinanceViews();
    renderPortfolio();
  }

  function resetTransactionForm() {
    transactionForm.reset();
    transactionForm.elements.id.value = "";
    transactionForm.elements.date.value = todayLocalDateValue();
    installmentCount.value = "2";
    recurrenceFrequency.value = "monthly";
    recurrenceCount.value = "12";
    destinationAmount.value = "";
    transferExchangeRate.value = "";
    investmentAmount.value = "";
    fillInvestmentOperation(null);
    transactionAmount.disabled = false;
    transactionAmount.required = true;
    transactionAmountRow.hidden = false;
    transactionFormTitle.textContent = "Novo lançamento";
    cancelTransactionEditButton.hidden = true;
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
    recurrenceCount.value = transaction.recurrence_count || (transaction.series_kind === "recurring" ? transaction.installment_count : "12") || "12";
    updateSeriesState();
    updateTransactionTypeState();
    applyWalletAccountRestrictions();
    seriesKind.disabled = true;
    installmentCount.disabled = true;
    recurrenceFrequency.disabled = true;
    recurrenceCount.disabled = true;
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
      `<option value="${escapeHtml(subcategory.name)}">${escapeHtml(subcategory.name)}</option>`
    )).join("");
    transactionSubcategory.disabled = subcategories.length === 0;
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
    transactionMonthLabel.textContent = formatMonthLabel(state.transactionMonth);
    ensureSelectedAccount();
    if (state.selectedAccountId && transactionAccount.value !== state.selectedAccountId) {
      transactionAccount.value = state.selectedAccountId;
    }
    const accountTransactions = selectedAccountTransactions(state.accountTransactions);
    const monthTransactions = selectedAccountVisibleTransactions(accountTransactions)
      .filter((transaction) => transaction.date.startsWith(state.transactionMonth))
      .filter(matchesTransactionSearch);

    currentBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(todayLocalDateValue(), accountTransactions, true));
    forecastBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(monthEndDate(state.transactionMonth), accountTransactions, false));
    renderTransactionCollection(transactionList, monthTransactions, false, accountTransactions);
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

  function selectedAccountVisibleTransactions(transactions = state.accountTransactions) {
    if (!state.selectedAccountId) {
      return [];
    }
    return selectedAccountTransactions(transactions);
  }

  function renderTransactionCollection(container, transactions, compact, balanceTransactions = transactions) {
    container.innerHTML = "";
    if (transactions.length === 0) {
      container.append(emptyState("Nenhum lançamento registrado ainda."));
      return;
    }
    const grouped = groupTransactionsByDate(transactions);
    for (const [dateKey, items] of grouped.entries()) {
      const group = document.createElement("section");
      group.className = "transaction-group";
      const rows = items.map((transaction) => transactionTemplate(transaction, compact)).join("");
      group.innerHTML = `
        <h3>${formatDate(dateKey)}</h3>
        <div class="transaction-rows">${rows}</div>
      `;
      if (!compact) {
        group.append(dailyBalance(dateKey, balanceTransactions));
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
      <article class="transaction-row ${signal}">
        <div>
          <strong>${escapeHtml(transaction.description)}</strong>
          <div class="account-meta">
            <span>${typeLabel}</span>
            <span>${accountRoute}</span>
            ${transactionSeriesLabel(transaction) ? `<span>${transactionSeriesLabel(transaction)}</span>` : ""}
            ${transaction.category_name ? `<span>${escapeHtml(formatCategoryPath(transaction))}</span>` : ""}
            ${transaction.tags && transaction.tags.length ? `<span>${transaction.tags.map((tag) => `#${escapeHtml(tag)}`).join(" ")}</span>` : ""}
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
    const balance = getBalanceUntil(dateKey, transactions);
    const balanceTotal = [...balance.values()].reduce((total, value) => total + Number(value), 0);
    const balanceClass = balanceTotal < 0 ? "danger-text" : balanceTotal > 0 ? "positive-text" : "";
    const row = document.createElement("div");
    row.className = "daily-balance";
    row.innerHTML = `
      <span>Saldo no dia</span>
      <strong class="${balanceClass}">${formatCurrencySummary(balance)}</strong>
    `;
    return row;
  }

  function matchesTransactionSearch(transaction) {
    const query = normalizeSearch(transactionSearch.value);
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
      seriesKind.disabled = false;
    }
  }

  function updateInvestmentFieldState() {
    const isInvestment = transactionType.value === "investment";
    const cat = transactionCategory.value;
    const isSavings = isInvestmentSavingsSelection();
    investmentFundFields.hidden = !isInvestment || cat !== "Fundos de Investimentos";
    investmentFixedFields.hidden = !isInvestment || cat !== "Renda Fixa" || isSavings;
    for (const field of investmentOperationFields.querySelectorAll("input, select")) {
      field.disabled = !isInvestment;
    }
    for (const field of investmentFundFields.querySelectorAll("input, select")) {
      field.disabled = !isInvestment || investmentFundFields.hidden;
    }
    for (const field of investmentFixedFields.querySelectorAll("input, select")) {
      field.disabled = !isInvestment || investmentFixedFields.hidden;
    }
    if (isSavings) {
      transactionForm.elements.investment_asset_identifier.value = "POUPANCA";
      if (!transactionForm.elements.investment_asset_name.value) {
        transactionForm.elements.investment_asset_name.value = "Poupança";
      }
    } else if (transactionForm.elements.investment_asset_identifier.value === "POUPANCA") {
      transactionForm.elements.investment_asset_identifier.value = "";
    }
    investmentAmount.required = isInvestment;
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
    seriesKindRow.hidden = Boolean(isWallet);
    seriesKind.disabled = Boolean(isWallet);
    const isInstallment = seriesKind.value === "installment";
    const isRecurring = seriesKind.value === "recurring";
    installmentCountLabel.hidden = !isInstallment;
    installmentCount.disabled = !isInstallment;
    recurrenceFields.hidden = !isRecurring;
    recurrenceFrequency.disabled = !isRecurring;
    recurrenceCount.disabled = !isRecurring;
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
    exchangeRate.disabled = false;
    exchangeRate.value = "1,000000";
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
  };
}
