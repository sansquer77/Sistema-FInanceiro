export function createAppDataLoader({ state, services, getViews, actions }) {
  const { api, fetchAllListed } = services;

  async function loadAll() {
    try {
      const [accountsResponse, creditCardsResponse, transactions, cardTransactions, cardPayments, cockpit] = await coreSnapshot();
      applyCoreSnapshot({ accountsResponse, creditCardsResponse, transactions, cardTransactions, cardPayments, cockpit });
      actions.invalidateFinancialHealth();
      await Promise.all([loadArchivedAccounts(), loadArchivedCreditCards(), loadClassifications(), loadSpendingLimits()]);
      await loadCurrentSpendingLimits();
      await loadTransactionSlice();
      await loadCardInvoice();
    } catch (error) {
      clearLoadedData();
      actions.setLoadError(error.message);
    }
    actions.renderAll();
  }

  async function loadAccounts() {
    await getViews().accounts.loadAccounts();
    await loadTransactionSlice();
    actions.markPortfolioDirty();
    actions.renderFinance();
  }

  async function loadCreditCards() {
    await getViews().cards.loadCreditCards();
    await loadCockpit();
    actions.renderFinance();
  }

  async function loadTransactionsAndAccounts() {
    const [accountsResponse, creditCardsResponse, transactions, cardTransactions, cardPayments, cockpit] = await coreSnapshot();
    applyCoreSnapshot({ accountsResponse, creditCardsResponse, transactions, cardTransactions, cardPayments, cockpit });
    await loadTransactionSlice();
    actions.invalidateFinancialHealth();
    await Promise.all([loadArchivedAccounts(), loadArchivedCreditCards(), loadClassifications(), loadSpendingLimits()]);
    await loadCurrentSpendingLimits();
    await loadCardInvoice();
    actions.markPortfolioDirty();
    actions.renderAll();
  }

  async function coreSnapshot() {
    const month = actions.cockpitMonthValue();
    return Promise.all([
      api("/api/checking-accounts"), api("/api/credit-cards"),
      fetchAllListed("/api/transactions", "transactions"),
      fetchAllListed("/api/credit-card-transactions", "transactions"),
      fetchAllListed("/api/credit-card-payments", "payments"),
      api(`/api/cockpit?month=${encodeURIComponent(month)}`),
    ]);
  }

  function applyCoreSnapshot({ accountsResponse, creditCardsResponse, transactions, cardTransactions, cardPayments, cockpit }) {
    state.accounts = accountsResponse.accounts;
    state.creditCards = creditCardsResponse.cards;
    getViews().cards.ensureSelectedCreditCard();
    actions.ensureSelectedAccount();
    state.transactions = transactions;
    state.cardTransactions = cardTransactions;
    state.cardPayments = cardPayments || [];
    state.cockpit = cockpit;
    state.cockpitLoadedMonth = actions.cockpitMonthValue();
  }

  function clearLoadedData() {
    Object.assign(state, {
      accounts: [], archivedAccounts: [], creditCards: [], archivedCreditCards: [],
      cardInvoiceTransactions: [], cardInvoicePayments: [], cardTransactions: [], cardPayments: [],
      selectedCreditCardId: "", transactions: [], accountTransactions: [], balanceProjection: null,
      cockpit: null, cockpitLoadedMonth: "", categories: [], tags: [], spendingLimits: [],
      currentSpendingLimits: [], portfolio: null,
    });
  }

  async function loadArchivedAccounts() { await getViews().accounts.loadArchivedAccounts(); }
  async function loadArchivedCreditCards() { await getViews().cards.loadArchivedCreditCards(); }
  async function loadTransactionSlice() { await getViews().transactions.loadTransactionSlice(); }

  async function loadCockpit() {
    const month = actions.cockpitMonthValue();
    state.cockpit = await api(`/api/cockpit?month=${encodeURIComponent(month)}`);
    state.cockpitLoadedMonth = month;
    actions.invalidateFinancialHealth();
  }

  async function refreshCockpitData() {
    const requestId = ++state.cockpitRefreshRequestId;
    const month = actions.cockpitMonthValue();
    const cockpit = getViews().cockpit;
    if (state.cockpit && state.cockpitLoadedMonth === month) {
      cockpit.setLoading(false);
      actions.renderCockpit();
      actions.touchCockpitUpdated();
      return;
    }
    cockpit.setLoading(true);
    try {
      const [accountsResponse, transactions, cardTransactions, cardPayments, cockpitResponse, spendingLimitsResponse] = await Promise.all([
        api("/api/checking-accounts"), fetchAllListed("/api/transactions", "transactions"),
        fetchAllListed("/api/credit-card-transactions", "transactions"),
        fetchAllListed("/api/credit-card-payments", "payments"),
        api(`/api/cockpit?month=${encodeURIComponent(month)}`),
        api(`/api/spending-limits?month=${encodeURIComponent(month)}`),
      ]);
      if (requestId !== state.cockpitRefreshRequestId) return;
      state.accounts = accountsResponse.accounts || [];
      actions.ensureSelectedAccount();
      state.transactions = transactions || [];
      state.cardTransactions = cardTransactions || [];
      state.cardPayments = cardPayments || [];
      state.cockpit = cockpitResponse;
      state.cockpitLoadedMonth = month;
      state.currentSpendingLimits = spendingLimitsResponse.limits || [];
      actions.invalidateFinancialHealth();
      actions.renderBase();
      if (state.view === "cockpit") {
        actions.renderCockpit();
        actions.touchCockpitUpdated();
      }
    } finally {
      if (requestId === state.cockpitRefreshRequestId) cockpit.setLoading(false);
    }
  }

  async function loadPortfolio(options = {}) { await getViews().portfolio.loadPortfolio(options); }
  async function loadClassifications() { await getViews().classifications.loadClassifications(); }
  async function loadSpendingLimits() { await getViews().limits.loadSpendingLimits(); }
  async function loadCurrentSpendingLimits() { await getViews().limits.loadCurrentSpendingLimits(actions.cockpitMonthValue()); }
  async function loadCardInvoice() { await getViews().cards.loadCardInvoice(); }
  async function loadCardTransactions() { await getViews().cards.loadCardTransactions(); }

  return {
    loadAll, loadAccounts, loadCreditCards, loadArchivedAccounts, loadArchivedCreditCards,
    loadTransactionsAndAccounts, loadTransactionSlice, loadCockpit, refreshCockpitData,
    loadPortfolio, loadClassifications, loadSpendingLimits, loadCurrentSpendingLimits,
    loadCardInvoice, loadCardTransactions,
  };
}
