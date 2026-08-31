export function createTransactionList({
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
  balanceChart,
  renderCollection,
  matchesSearch,
}) {
  const {
    transactionAccount,
    transactionMonthLabel,
    transactionSearch,
    clearTransactionSearchButton,
    transactionStatusFilterButtons,
    transactionContextCount,
    currentBalanceSummary,
    forecastBalanceLabel,
    forecastBalanceSummary,
    transactionList,
  } = elements;
  let searchDebounceTimer = null;

  transactionSearch.value = state.transactionSearch || "";
  transactionSearch.addEventListener("input", () => {
    state.transactionSearch = transactionSearch.value;
    clearTimeout(searchDebounceTimer);
    searchDebounceTimer = setTimeout(render, 200);
  });
  clearTransactionSearchButton.addEventListener("click", () => {
    state.transactionSearch = "";
    transactionSearch.value = "";
    clearTimeout(searchDebounceTimer);
    render();
    transactionSearch.focus();
  });
  transactionStatusFilterButtons.forEach((button) => button.addEventListener("click", () => {
    state.transactionStatusFilter = button.dataset.transactionStatusFilter || "all";
    render();
  }));

  function render() {
    transactionMonthLabel.textContent = formatMonthShortLabel(state.transactionMonth);
    ensureSelectedAccount();
    if (state.selectedAccountId && transactionAccount.value !== state.selectedAccountId) {
      transactionAccount.value = state.selectedAccountId;
    }
    const accountTransactions = selectedAccountTransactions(state.accountTransactions);
    transactionSearch.value = state.transactionSearch || "";
    clearTransactionSearchButton.hidden = !state.transactionSearch;
    renderStatusFilters();
    const monthTransactions = selectedAccountTransactions(accountTransactions)
      .filter((transaction) => transaction.date.startsWith(state.transactionMonth));
    const searchedTransactions = monthTransactions.filter(matchesSearch);
    renderContextCount(searchedTransactions);
    const visibleTransactions = searchedTransactions.filter(matchesStatusFilter);
    currentBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(todayLocalDateValue(), accountTransactions, true));
    const forecastLimitDate = monthEndDate(state.transactionMonth);
    forecastBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(forecastLimitDate, accountTransactions, false));
    if (forecastBalanceLabel) {
      const account = state.accounts.find((entry) => String(entry.id) === String(state.selectedAccountId));
      const detail = accountHasPreferredCardForecast(account, forecastLimitDate)
        ? " Saldo do fim do mês (inclui despesas conciliadas de cartão)"
        : " Saldo do fim do mês";
      forecastBalanceLabel.innerHTML = `<span class="balance-kind-badge forecast"><span aria-hidden="true">○</span> Previsto</span>${detail}`;
    }
    balanceChart.render();
    renderCollection(transactionList, visibleTransactions, false, accountTransactions);
  }

  function renderStatusFilters() {
    transactionStatusFilterButtons.forEach((button) => {
      const active = button.dataset.transactionStatusFilter === state.transactionStatusFilter;
      button.classList.toggle("active", active);
      button.setAttribute("aria-pressed", String(active));
    });
  }

  function renderContextCount(transactions) {
    const reconciled = transactions.filter((transaction) => transaction.reconciled_at).length;
    const pending = transactions.length - reconciled;
    transactionContextCount.textContent = `${transactions.length} ${transactions.length === 1 ? "lançamento" : "lançamentos"} · ${reconciled} ${reconciled === 1 ? "conciliado" : "conciliados"} · ${pending} ${pending === 1 ? "pendente" : "pendentes"}`;
  }

  function matchesStatusFilter(transaction) {
    if (state.transactionStatusFilter === "reconciled") return Boolean(transaction.reconciled_at);
    if (state.transactionStatusFilter === "pending") return !transaction.reconciled_at;
    return true;
  }

  return { render };
}
