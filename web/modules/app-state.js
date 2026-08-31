export function createAppState({ currentMonth }) {
  return {
    user: null,
    accounts: [], archivedAccounts: [], creditCards: [], archivedCreditCards: [],
    cardInvoiceTransactions: [], cardInvoicePayments: [], cardTransactions: [], cardPayments: [],
    selectedCreditCardId: "", selectedAccountId: "",
    cardInvoiceSearch: "", cardInvoiceStatusFilter: "all",
    transactionSearch: "", transactionStatusFilter: "all", transactionHighlightId: "",
    transactions: [], accountTransactions: [], balanceProjection: null,
    cockpit: null, cockpitLoadedMonth: "", cockpitTab: "summary", cockpitMonth: currentMonth,
    categories: [], tags: [], spendingLimits: [], currentSpendingLimits: [],
    appInfo: null, latestVersion: null,
    portfolio: null, portfolioReturns: null, portfolioDirty: true, portfolioLoading: false, portfolioLoadedAt: 0,
    portfolioError: "", portfolioGroup: "account_name",
    portfolioExpandedGroups: new Set(), portfolioCollapsedGroups: new Set(),
    portfolioAssetSaving: false, portfolioHighlightId: "", portfolioTab: "position",
    view: "cockpit", cockpitRefreshRequestId: 0,
    transactionMonth: currentMonth, limitMonth: currentMonth, cardInvoiceMonth: currentMonth,
    reportMonth: currentMonth, reportTab: "categories", reportAccountId: "",
    statementScope: "consolidated", statementCurrency: "all", statementAccountIds: [], statementCardIds: [],
    transactionSliceRequestId: 0, cardInvoiceRequestId: 0,
  };
}

export function resetSessionData(state, { currentMonth }) {
  Object.assign(state, {
    user: null,
    accounts: [], archivedAccounts: [], creditCards: [], archivedCreditCards: [],
    cardInvoiceTransactions: [], cardInvoicePayments: [], cardTransactions: [], cardPayments: [],
    selectedCreditCardId: "", selectedAccountId: "",
    transactionSearch: "", transactionStatusFilter: "all", transactionHighlightId: "",
    transactions: [], accountTransactions: [], balanceProjection: null,
    cockpit: null, cockpitLoadedMonth: "", cockpitTab: "summary", cockpitMonth: currentMonth,
    categories: [], tags: [], spendingLimits: [], currentSpendingLimits: [],
    portfolio: null, portfolioReturns: null, portfolioDirty: true, portfolioLoading: false, portfolioLoadedAt: 0,
    portfolioError: "", portfolioExpandedGroups: new Set(), portfolioCollapsedGroups: new Set(),
    portfolioAssetSaving: false, portfolioHighlightId: "", portfolioTab: "position",
    cockpitRefreshRequestId: 0, transactionSliceRequestId: 0, cardInvoiceRequestId: 0,
  });
}
