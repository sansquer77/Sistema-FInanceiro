import { api, upload } from "./modules/api.js";
import {
  currentMonthValue,
  formatDate,
  formatMonthLabel,
  isValidMonthValue,
  monthEndDate,
  shiftMonth,
  todayLocalDateValue,
} from "./modules/date-utils.js";
import {
  formatCurrencySummary,
  formatDecimal,
  formatMoney,
  formatPercent,
  moneyInputValue,
  parseDecimalInput,
  portfolioQuoteText,
} from "./modules/money-utils.js";
import {
  emptyState,
  escapeHtml,
  formData,
  normalizeSearch,
  setFormBusy,
  setMessage,
} from "./modules/dom-utils.js";
import {
  accountTypeLabel,
  cardCategoryPath,
  cardTransactionTypeLabel,
  classificationGroupLabel,
  formatCategoryPath,
  transactionSeriesLabel,
  transactionTypeLabel,
} from "./modules/labels.js";
import {
  isExchangeTransfer,
  isInstallmentTransaction,
  isInvestmentTransaction,
  isInvestmentTransfer,
} from "./modules/transaction-kind.js";
import { openMonthPicker } from "./modules/month-picker.js";
import { registerAuthView } from "./modules/auth-view.js";
import { registerUserAdminView } from "./modules/user-admin-view.js";
import { registerClassificationsView } from "./modules/classifications-view.js";
import { registerLimitsView } from "./modules/limits-view.js";
import { registerReportsView } from "./modules/reports-view.js";
import { registerImportsView } from "./modules/imports-view.js";
import { registerCockpitView } from "./modules/cockpit-view.js";
import { registerAccountsView } from "./modules/accounts-view.js";
import { registerCardsView } from "./modules/cards-view.js";
import { registerPortfolioView } from "./modules/portfolio-view.js";
import { registerTransactionsView } from "./modules/transactions-view.js";

const state = {
  user: null,
  accounts: [],
  archivedAccounts: [],
  creditCards: [],
  archivedCreditCards: [],
  cardInvoiceTransactions: [],
  cardInvoicePayments: [],
  cardTransactions: [],
  cardPayments: [],
  selectedCreditCardId: "",
  selectedAccountId: "",
  transactions: [],
  accountTransactions: [],
  cockpit: null,
  categories: [],
  tags: [],
  spendingLimits: [],
  currentSpendingLimits: [],
  portfolio: null,
  portfolioDirty: true,
  portfolioLoading: false,
  portfolioError: "",
  portfolioGroup: "account_name",
  portfolioExpandedGroups: new Set(),
  portfolioCollapsedGroups: new Set(),
  portfolioAssetSaving: false,
  view: "cockpit",
  cockpitRefreshRequestId: 0,
  transactionMonth: currentMonthValue(),
  limitMonth: currentMonthValue(),
  cardInvoiceMonth: currentMonthValue(),
  reportMonth: currentMonthValue(),
  reportTab: "categories",
  reportAccountId: "",
  transactionSliceRequestId: 0,
  cardInvoiceRequestId: 0,
};

const authView = document.querySelector("#authView");
const dashboardView = document.querySelector("#dashboardView");
const appSidebar = document.querySelector(".app-sidebar");
const sidebarToggle = document.querySelector("#sidebarToggle");
const loginTab = document.querySelector("#loginTab");
const registerTab = document.querySelector("#registerTab");
const loginForm = document.querySelector("#loginForm");
const registerForm = document.querySelector("#registerForm");
const passwordResetRequestForm = document.querySelector("#passwordResetRequestForm");
const passwordResetConfirmForm = document.querySelector("#passwordResetConfirmForm");
const forgotPasswordButton = document.querySelector("#forgotPasswordButton");
const backToLoginFromRequest = document.querySelector("#backToLoginFromRequest");
const backToLoginFromConfirm = document.querySelector("#backToLoginFromConfirm");
const authMessage = document.querySelector("#authMessage");
const accountForm = document.querySelector("#accountForm");
const accountBankLabel = document.querySelector("#accountBankLabel");
const accountBankDetails = document.querySelector("#accountBankDetails");
const accountMessage = document.querySelector("#accountMessage");
const accountList = document.querySelector("#accountList");
const archivedAccountList = document.querySelector("#archivedAccountList");
const creditCardForm = document.querySelector("#creditCardForm");
const creditCardFormTitle = document.querySelector("#creditCardFormTitle");
const creditCardPreferredPaymentAccount = document.querySelector("#creditCardPreferredPaymentAccount");
const creditCardMessage = document.querySelector("#creditCardMessage");
const creditCardList = document.querySelector("#creditCardList");
const archivedCreditCardList = document.querySelector("#archivedCreditCardList");
const cancelCreditCardEditButton = document.querySelector("#cancelCreditCardEditButton");
const cardInvoiceCard = document.querySelector("#cardInvoiceCard");
const cardInvoiceMonthLabel = document.querySelector("#cardInvoiceMonthLabel");
const previousCardInvoiceButton = document.querySelector("#previousCardInvoiceButton");
const todayCardInvoiceButton = document.querySelector("#todayCardInvoiceButton");
const nextCardInvoiceButton = document.querySelector("#nextCardInvoiceButton");
const cardInvoiceHistoryChart = document.querySelector("#cardInvoiceHistoryChart");
const cardInvoiceTotal = document.querySelector("#cardInvoiceTotal");
const cardInvoiceReconciledTotal = document.querySelector("#cardInvoiceReconciledTotal");
const cardInvoiceClosingDate = document.querySelector("#cardInvoiceClosingDate");
const cardInvoiceDueDate = document.querySelector("#cardInvoiceDueDate");
const cardInvoicePaymentForm = document.querySelector("#cardInvoicePaymentForm");
const cardPaymentAccount = document.querySelector("#cardPaymentAccount");
const cardPaymentDate = document.querySelector("#cardPaymentDate");
const payCardInvoiceButton = document.querySelector("#payCardInvoiceButton");
const cardInvoiceMessage = document.querySelector("#cardInvoiceMessage");
const cardInvoiceOpenCount = document.querySelector("#cardInvoiceOpenCount");
const cardTransactionForm = document.querySelector("#cardTransactionForm");
const cardTransactionFormTitle = document.querySelector("#cardTransactionFormTitle");
const cardTransactionType = document.querySelector("#cardTransactionType");
const cardTransactionCategory = document.querySelector("#cardTransactionCategory");
const cardTransactionSubcategory = document.querySelector("#cardTransactionSubcategory");
const cardSeriesKind = document.querySelector("#cardSeriesKind");
const cardInstallmentCount = document.querySelector("#cardInstallmentCount");
const cardInstallmentCountLabel = document.querySelector("#cardInstallmentCountLabel");
const cardRecurrenceFields = document.querySelector("#cardRecurrenceFields");
const cardRecurrenceFrequency = document.querySelector("#cardRecurrenceFrequency");
const cardRecurrenceCount = document.querySelector("#cardRecurrenceCount");
const cardInvoiceList = document.querySelector("#cardInvoiceList");
const cancelCardTransactionEditButton = document.querySelector("#cancelCardTransactionEditButton");
const transactionForm = document.querySelector("#transactionForm");
const transactionFormTitle = document.querySelector("#transactionFormTitle");
const transactionMessage = document.querySelector("#transactionMessage");
const transactionList = document.querySelector("#transactionList");
const transactionTagOptions = document.querySelector("#transactionTagOptions");
const categoryForm = document.querySelector("#categoryForm");
const categoryGroup = document.querySelector("#categoryGroup");
const subcategoryForm = document.querySelector("#subcategoryForm");
const subcategoryCategory = document.querySelector("#subcategoryCategory");
const tagForm = document.querySelector("#tagForm");
const categoryMessage = document.querySelector("#categoryMessage");
const tagMessage = document.querySelector("#tagMessage");
const categoryList = document.querySelector("#categoryList");
const tagList = document.querySelector("#tagList");
const limitForm = document.querySelector("#limitForm");
const limitFormTitle = document.querySelector("#limitFormTitle");
const limitCategory = document.querySelector("#limitCategory");
const limitSubcategory = document.querySelector("#limitSubcategory");
const limitMonthInput = document.querySelector("#limitMonthInput");
const limitMonthLabel = document.querySelector("#limitMonthLabel");
const limitConsumedSummary = document.querySelector("#limitConsumedSummary");
const limitDefinedSummary = document.querySelector("#limitDefinedSummary");
const limitAvailableSummary = document.querySelector("#limitAvailableSummary");
const limitMessage = document.querySelector("#limitMessage");
const spendingLimitList = document.querySelector("#spendingLimitList");
const previousLimitMonthButton = document.querySelector("#previousLimitMonthButton");
const nextLimitMonthButton = document.querySelector("#nextLimitMonthButton");
const cancelLimitEditButton = document.querySelector("#cancelLimitEditButton");
const reportMonthLabel = document.querySelector("#reportMonthLabel");
const previousReportMonthButton = document.querySelector("#previousReportMonthButton");
const nextReportMonthButton = document.querySelector("#nextReportMonthButton");
const reportTabs = document.querySelectorAll("[data-report-tab]");
const reportIncomeSummary = document.querySelector("#reportIncomeSummary");
const reportExpenseSummary = document.querySelector("#reportExpenseSummary");
const reportInvestmentSummary = document.querySelector("#reportInvestmentSummary");
const reportResultSummary = document.querySelector("#reportResultSummary");
const reportAccountFilter = document.querySelector("#reportAccountFilter");
const reportAccountSelect = document.querySelector("#reportAccountSelect");
const reportContent = document.querySelector("#reportContent");
const addPortfolioAssetButton = document.querySelector("#addPortfolioAssetButton");
const refreshPortfolioButton = document.querySelector("#refreshPortfolioButton");
const portfolioAssetFormPanel = document.querySelector("#portfolioAssetFormPanel");
const portfolioAssetForm = document.querySelector("#portfolioAssetForm");
const portfolioAssetFormTitle = document.querySelector("#portfolioAssetFormTitle");
const portfolioAssetAccount = document.querySelector("#portfolioAssetAccount");
const portfolioAssetType = document.querySelector("#portfolioAssetType");
const portfolioAssetIdentifier = document.querySelector("#portfolioAssetIdentifier");
const portfolioAssetIdentifierLabel = document.querySelector("#portfolioAssetIdentifierLabel");
const portfolioFundFields = document.querySelector("#portfolioFundFields");
const portfolioPensionFields = document.querySelector("#portfolioPensionFields");
const portfolioPensionSubtype = document.querySelector("#portfolioPensionSubtype");
const portfolioSavingsFields = document.querySelector("#portfolioSavingsFields");
const portfolioFixedFields = document.querySelector("#portfolioFixedFields");
const portfolioFixedIncomeSubtype = document.querySelector("#portfolioFixedIncomeSubtype");
const cancelPortfolioAssetButton = document.querySelector("#cancelPortfolioAssetButton");
const deletePortfolioAssetButton = document.querySelector("#deletePortfolioAssetButton");
const portfolioCostSummary = document.querySelector("#portfolioCostSummary");
const portfolioCurrentSummary = document.querySelector("#portfolioCurrentSummary");
const portfolioResultSummary = document.querySelector("#portfolioResultSummary");
const portfolioReturnSummary = document.querySelector("#portfolioReturnSummary");
const portfolioDayResultSummary = document.querySelector("#portfolioDayResultSummary");
const portfolioPositionCount = document.querySelector("#portfolioPositionCount");
const portfolioMessage = document.querySelector("#portfolioMessage");
const portfolioTypeList = document.querySelector("#portfolioTypeList");
const portfolioIndexerList = document.querySelector("#portfolioIndexerList");
const portfolioCurrencyList = document.querySelector("#portfolioCurrencyList");
const portfolioAccountList = document.querySelector("#portfolioAccountList");
const portfolioPositions = document.querySelector("#portfolioPositions");
const portfolioHistory = document.querySelector("#portfolioHistory");
const portfolioGroupFilter = document.querySelector("#portfolioGroupFilter");
const importForm = document.querySelector("#importForm");
const importTarget = document.querySelector("#importTarget");
const importAccount = document.querySelector("#importAccount");
const importAccountLabel = document.querySelector("#importAccountLabel");
const importCreditCard = document.querySelector("#importCreditCard");
const importCardLabel = document.querySelector("#importCardLabel");
const downloadImportTemplateButton = document.querySelector("#downloadImportTemplateButton");
const importMessage = document.querySelector("#importMessage");
const importResult = document.querySelector("#importResult");
const emailForm = document.querySelector("#emailForm");
const passwordForm = document.querySelector("#passwordForm");
const emailConfigForm = document.querySelector("#emailConfigForm");
const emailConfigProvider = document.querySelector("#emailConfigProvider");
const emailConfigManualFields = document.querySelector("#emailConfigManualFields");
const emailConfigPreset = document.querySelector("#emailConfigPreset");
const clearLaunchesForm = document.querySelector("#clearLaunchesForm");
const deleteUserForm = document.querySelector("#deleteUserForm");
const emailMessage = document.querySelector("#emailMessage");
const passwordMessage = document.querySelector("#passwordMessage");
const emailConfigMessage = document.querySelector("#emailConfigMessage");
const clearLaunchesMessage = document.querySelector("#clearLaunchesMessage");
const deleteUserMessage = document.querySelector("#deleteUserMessage");
const monthlyPlanningList = document.querySelector("#monthlyPlanningList");
const installmentDebtList = document.querySelector("#installmentDebtList");
const transactionType = document.querySelector("#transactionType");
const transactionAccount = document.querySelector("#transactionAccount");
const transactionAmount = document.querySelector("#transactionAmount");
const transactionAmountRow = document.querySelector("#transactionAmountRow");
const destinationAccount = document.querySelector("#destinationAccount");
const destinationAccountLabel = document.querySelector("#destinationAccountLabel");
const exchangeTransferFields = document.querySelector("#exchangeTransferFields");
const destinationAmount = document.querySelector("#destinationAmount");
const transferExchangeRate = document.querySelector("#transferExchangeRate");
const investmentOperationFields = document.querySelector("#investmentOperationFields");
const investmentAmount = document.querySelector("#investmentAmount");
const investmentFundFields = document.querySelector("#investmentFundFields");
const investmentFixedFields = document.querySelector("#investmentFixedFields");
const transactionCategory = document.querySelector("#transactionCategory");
const transactionCategoryRow = document.querySelector("#transactionCategoryRow");
const transactionSubcategory = document.querySelector("#transactionSubcategory");
const seriesKind = document.querySelector("#seriesKind");
const seriesKindRow = document.querySelector("#seriesKindRow");
const installmentCount = document.querySelector("#installmentCount");
const installmentCountLabel = document.querySelector("#installmentCountLabel");
const recurrenceFields = document.querySelector("#recurrenceFields");
const recurrenceFrequency = document.querySelector("#recurrenceFrequency");
const recurrenceCount = document.querySelector("#recurrenceCount");
const exchangeRate = document.querySelector("#exchangeRate");
const exchangeRateLabel = document.querySelector("#exchangeRateLabel");
const userName = document.querySelector("#userName");
const logoutButton = document.querySelector("#logoutButton");
const cancelEditButton = document.querySelector("#cancelEditButton");
const cancelTransactionEditButton = document.querySelector("#cancelTransactionEditButton");
const formTitle = document.querySelector("#formTitle");
const moduleEyebrow = document.querySelector("#moduleEyebrow");
const pageTitle = document.querySelector("#pageTitle");
const monthIncome = document.querySelector("#monthIncome");
const monthExpense = document.querySelector("#monthExpense");
const monthInvestment = document.querySelector("#monthInvestment");
const savingsRate = document.querySelector("#savingsRate");
const currencyList = document.querySelector("#currencyList");
const cockpitPortfolioByType = document.querySelector("#cockpitPortfolioByType");
const cockpitLimitAlert = document.querySelector("#cockpitLimitAlert");
const topExpensesChart = document.querySelector("#topExpensesChart");
const cashDistributionChart = document.querySelector("#cashDistributionChart");
const previousMonthButton = document.querySelector("#previousMonthButton");
const todayMonthButton = document.querySelector("#todayMonthButton");
const nextMonthButton = document.querySelector("#nextMonthButton");
const transactionMonthLabel = document.querySelector("#transactionMonthLabel");
const currentBalanceSummary = document.querySelector("#currentBalanceSummary");
const forecastBalanceSummary = document.querySelector("#forecastBalanceSummary");
const transactionBalanceHistoryChart = document.querySelector("#transactionBalanceHistoryChart");
const transactionSearch = document.querySelector("#transactionSearch");
const navButtons = document.querySelectorAll("[data-view]");
const moduleViews = {
  cockpit: document.querySelector("#cockpitView"),
  accounts: document.querySelector("#accountsView"),
  creditCards: document.querySelector("#creditCardsView"),
  cardLaunches: document.querySelector("#cardLaunchesView"),
  transactions: document.querySelector("#transactionsView"),
  portfolio: document.querySelector("#portfolioView"),
  limits: document.querySelector("#limitsView"),
  reports: document.querySelector("#reportsView"),
  classifications: document.querySelector("#classificationsView"),
  imports: document.querySelector("#importsView"),
  user: document.querySelector("#userView"),
};

const viewTitles = {
  cockpit: ["Cockpit", "Resumo financeiro"],
  accounts: ["Cadastro", "Contas"],
  creditCards: ["Cadastro", "Cartões"],
  cardLaunches: ["Lançamentos", "Cartões"],
  transactions: ["Lançamentos", "Contas"],
  portfolio: ["Gestão", "Portfólio"],
  limits: ["Gestão", "Limite de gastos"],
  reports: ["Gestão", "Relatórios"],
  classifications: ["Gestão", "Categorias e tags"],
  imports: ["Gestão", "Importação"],
  user: ["Usuário", "Preferências"],
};

const SIDEBAR_COLLAPSED_KEY = "financeiro.sidebar.collapsed";

const classificationsView = registerClassificationsView({
  state,
  elements: {
    categoryForm,
    categoryGroup,
    subcategoryForm,
    subcategoryCategory,
    tagForm,
    categoryMessage,
    tagMessage,
    categoryList,
    tagList,
  },
  api,
  formData,
  setMessage,
  emptyState,
  escapeHtml,
  classificationGroupLabel,
  onClassificationsChanged: () => {
    renderTransactionTagOptions();
    renderTransactionCategories();
    renderCardTransactionCategories();
  },
});

const limitsView = registerLimitsView({
  state,
  elements: {
    limitForm,
    limitFormTitle,
    limitCategory,
    limitSubcategory,
    limitMonthInput,
    limitMonthLabel,
    limitConsumedSummary,
    limitDefinedSummary,
    limitAvailableSummary,
    limitMessage,
    spendingLimitList,
    previousLimitMonthButton,
    nextLimitMonthButton,
    cancelLimitEditButton,
    cockpitLimitAlert,
  },
  navButtons,
  api,
  currentMonthValue,
  shiftMonth,
  formatMonthLabel,
  formatMoney,
  formatPercent,
  formData,
  setMessage,
  emptyState,
  escapeHtml,
  onLimitsChanged: renderCockpit,
  goToLimits: () => showModule("limits"),
});

const reportsView = registerReportsView({
  state,
  elements: {
    reportMonthLabel,
    previousReportMonthButton,
    nextReportMonthButton,
    reportTabs,
    reportIncomeSummary,
    reportExpenseSummary,
    reportInvestmentSummary,
    reportResultSummary,
    reportAccountFilter,
    reportAccountSelect,
    reportContent,
  },
  shiftMonth,
  formatDate,
  formatMonthLabel,
  formatMoney,
  formatPercent,
  escapeHtml,
  isInvestmentTransaction,
  chartColor,
});

const importsView = registerImportsView({
  state,
  elements: {
    importForm,
    importTarget,
    importAccount,
    importAccountLabel,
    importCreditCard,
    importCardLabel,
    downloadImportTemplateButton,
    importMessage,
    importResult,
  },
  upload,
  setFormBusy,
  setMessage,
  escapeHtml,
  onImportCompleted: loadTransactionsAndAccounts,
});

const cockpitView = registerCockpitView({
  state,
  elements: {
    monthIncome,
    monthExpense,
    monthInvestment,
    savingsRate,
    currencyList,
    monthlyPlanningList,
    installmentDebtList,
    topExpensesChart,
    cashDistributionChart,
    cockpitPortfolioByType,
  },
  currentMonthValue,
  formatMoney,
  formatPercent,
  emptyState,
  escapeHtml,
  formatCategoryPath,
  isInstallmentTransaction,
  isInvestmentTransaction,
  chartColor,
  getCurrencyTotals,
  renderLimitAlerts: () => limitsView.renderLimitAlerts(),
  loadPortfolio,
  portfolioTotalsByCurrency,
});

const accountsView = registerAccountsView({
  state,
  elements: {
    accountForm,
    accountBankLabel,
    accountBankDetails,
    accountMessage,
    accountList,
    archivedAccountList,
    cancelEditButton,
    formTitle,
  },
  api,
  formData,
  setMessage,
  emptyState,
  escapeHtml,
  formatMoney,
  accountTypeLabel,
  ensureSelectedAccount,
  onAccountsChanged: async () => {
    await loadTransactionSlice();
    markPortfolioDirty();
    renderBaseViews();
    renderFinanceViews();
  },
});

const cardsView = registerCardsView({
  state,
  elements: {
    creditCardForm,
    creditCardFormTitle,
    creditCardPreferredPaymentAccount,
    creditCardMessage,
    creditCardList,
    archivedCreditCardList,
    cancelCreditCardEditButton,
    cardInvoiceCard,
    cardInvoiceMonthLabel,
    previousCardInvoiceButton,
    todayCardInvoiceButton,
    nextCardInvoiceButton,
    cardInvoiceHistoryChart,
    cardInvoiceTotal,
    cardInvoiceReconciledTotal,
    cardInvoiceClosingDate,
    cardInvoiceDueDate,
    cardInvoicePaymentForm,
    cardPaymentAccount,
    cardPaymentDate,
    payCardInvoiceButton,
    cardInvoiceMessage,
    cardInvoiceOpenCount,
    cardTransactionForm,
    cardTransactionFormTitle,
    cardTransactionType,
    cardTransactionCategory,
    cardTransactionSubcategory,
    cardSeriesKind,
    cardInstallmentCount,
    cardInstallmentCountLabel,
    cardRecurrenceFields,
    cardRecurrenceFrequency,
    cardRecurrenceCount,
    cardInvoiceList,
    cancelCardTransactionEditButton,
  },
  api,
  formData,
  setFormBusy,
  setMessage,
  emptyState,
  escapeHtml,
  formatMoney,
  formatDate,
  formatMonthLabel,
  currentMonthValue,
  shiftMonth,
  todayLocalDateValue,
  isValidMonthValue,
  moneyInputValue,
  isInstallmentTransaction,
  cardTransactionTypeLabel,
  transactionSeriesLabel,
  cardCategoryPath,
  launchActionButton,
  deleteSeriesScope,
  openMonthPicker,
  onCreditCardsChanged: async () => {
    await loadCockpit();
    renderBaseViews();
    renderFinanceViews();
  },
  onCardTransactionsChanged: () => {
    renderLimits();
    renderCockpit();
  },
  onInvoicePaid: loadTransactionsAndAccounts,
});

const transactionsView = registerTransactionsView({
  state,
  elements: {
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
    transactionBalanceHistoryChart,
    transactionSearch,
  },
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
});

const portfolioView = registerPortfolioView({
  state,
  elements: {
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
    portfolioFixedIncomeSubtype,
    cancelPortfolioAssetButton,
    deletePortfolioAssetButton,
    portfolioCostSummary,
    portfolioCurrentSummary,
    portfolioResultSummary,
    portfolioReturnSummary,
    portfolioDayResultSummary,
    portfolioPositionCount,
    portfolioMessage,
    portfolioTypeList,
    portfolioIndexerList,
    portfolioCurrencyList,
    portfolioAccountList,
    portfolioPositions,
    portfolioHistory,
    portfolioGroupFilter,
  },
  api,
  formData,
  setMessage,
  escapeHtml,
  formatMoney,
  formatPercent,
  formatDate,
  formatDecimal,
  moneyInputValue,
  portfolioQuoteText,
  todayLocalDateValue,
  chartColor,
  onPortfolioChanged: renderCockpitPortfolioByType,
  onPortfolioRedeemed: loadTransactionsAndAccounts,
  editSourceTransaction: editPortfolioSourceTransaction,
});

navButtons.forEach((button) => button.addEventListener("click", () => showModule(button.dataset.view)));
sidebarToggle.addEventListener("click", () => toggleSidebar());

updateAccountTypeState();
initializeSidebar();
const authViewController = registerAuthView({
  api,
  elements: {
    loginTab,
    registerTab,
    loginForm,
    registerForm,
    passwordResetRequestForm,
    passwordResetConfirmForm,
    forgotPasswordButton,
    backToLoginFromRequest,
    backToLoginFromConfirm,
    authMessage,
    logoutButton,
  },
  formData,
  resetSessionState,
  setFormBusy,
  setMessage,
  state,
  onAuthenticated: loadDashboard,
  onShowAuth: showAuth,
});
const userAdminViewController = registerUserAdminView({
  api,
  elements: {
    emailForm,
    passwordForm,
    emailConfigForm,
    emailConfigProvider,
    emailConfigManualFields,
    emailConfigPreset,
    clearLaunchesForm,
    deleteUserForm,
    emailMessage,
    passwordMessage,
    emailConfigMessage,
    clearLaunchesMessage,
    deleteUserMessage,
    userName,
  },
  formData,
  loadAll,
  resetSessionState,
  setMessage,
  state,
  onShowAuth: showAuth,
});
boot();

async function boot() {
  try {
    const response = await api("/api/me");
    state.user = response.user;
  } catch (error) {
    state.user = null;
  }
  if (!state.user) {
    showAuth();
    return;
  }
  await loadDashboard();
}

function resetSessionState() {
  state.user = null;
  state.accounts = [];
  state.archivedAccounts = [];
  state.creditCards = [];
  state.archivedCreditCards = [];
  state.cardInvoiceTransactions = [];
  state.cardInvoicePayments = [];
  state.cardTransactions = [];
  state.cardPayments = [];
  state.selectedCreditCardId = "";
  state.transactions = [];
  state.accountTransactions = [];
  state.cockpit = null;
  state.categories = [];
  state.tags = [];
  state.spendingLimits = [];
  state.currentSpendingLimits = [];
  state.portfolio = null;
  resetAccountForm();
  resetCreditCardForm();
  resetCardTransactionForm();
  resetTransactionForm();
}

async function loadDashboard() {
  userName.textContent = state.user.name;
  authView.hidden = true;
  dashboardView.hidden = false;
  resetTransactionForm();
  resetCardTransactionForm();
  await loadAll();
  showModule(state.view);
}

async function loadAll() {
  try {
    const [accountsResponse, creditCardsResponse, transactionsResponse, cardTransactionsResponse, cardPaymentsResponse, cockpitResponse] = await Promise.all([
      api("/api/checking-accounts"),
      api("/api/credit-cards"),
      api("/api/transactions"),
      api("/api/credit-card-transactions"),
      api("/api/credit-card-payments"),
      api(`/api/cockpit?month=${encodeURIComponent(currentMonthValue())}`),
    ]);
    state.accounts = accountsResponse.accounts;
    state.creditCards = creditCardsResponse.cards;
    ensureSelectedCreditCard();
    ensureSelectedAccount();
    state.transactions = transactionsResponse.transactions;
    state.accountTransactions = [];
    state.cardTransactions = cardTransactionsResponse.transactions;
    state.cardPayments = cardPaymentsResponse.payments || [];
    state.cockpit = cockpitResponse;
    await loadArchivedAccounts();
    await loadArchivedCreditCards();
    await loadClassifications();
    await loadSpendingLimits();
    await loadCurrentSpendingLimits();
    await loadTransactionSlice();
    await loadCardInvoice();
  } catch (error) {
    state.accounts = [];
    state.archivedAccounts = [];
    state.creditCards = [];
    state.archivedCreditCards = [];
    state.cardInvoiceTransactions = [];
    state.cardInvoicePayments = [];
    state.cardTransactions = [];
    state.cardPayments = [];
    state.selectedCreditCardId = "";
    state.transactions = [];
    state.accountTransactions = [];
    state.cockpit = null;
    state.categories = [];
    state.tags = [];
    state.spendingLimits = [];
    state.currentSpendingLimits = [];
    state.portfolio = null;
    setMessage(accountMessage, error.message, "error");
  }
  renderBaseViews();
  renderFinanceViews();
  renderManagementViews();
}

async function loadAccounts() {
  await accountsView.loadAccounts();
  await loadTransactionSlice();
  markPortfolioDirty();
  renderBaseViews();
  renderFinanceViews();
}

async function loadCreditCards() {
  await cardsView.loadCreditCards();
  await loadCockpit();
  renderBaseViews();
  renderFinanceViews();
}

async function loadArchivedAccounts() {
  await accountsView.loadArchivedAccounts();
}

async function loadArchivedCreditCards() {
  await cardsView.loadArchivedCreditCards();
}

async function loadTransactionsAndAccounts() {
  const [accountsResponse, creditCardsResponse, transactionsResponse, cardTransactionsResponse, cardPaymentsResponse, cockpitResponse] = await Promise.all([
    api("/api/checking-accounts"),
    api("/api/credit-cards"),
    api("/api/transactions"),
    api("/api/credit-card-transactions"),
    api("/api/credit-card-payments"),
    api(`/api/cockpit?month=${encodeURIComponent(currentMonthValue())}`),
  ]);
  state.accounts = accountsResponse.accounts;
  state.creditCards = creditCardsResponse.cards;
  ensureSelectedCreditCard();
  ensureSelectedAccount();
  state.transactions = transactionsResponse.transactions;
  await loadTransactionSlice();
  state.cardTransactions = cardTransactionsResponse.transactions;
  state.cardPayments = cardPaymentsResponse.payments || [];
  state.cockpit = cockpitResponse;
  await loadArchivedAccounts();
  await loadArchivedCreditCards();
  await loadClassifications();
  await loadSpendingLimits();
  await loadCurrentSpendingLimits();
  await loadCardInvoice();
  markPortfolioDirty();
  renderBaseViews();
  renderFinanceViews();
  renderManagementViews();
}

async function loadTransactionSlice() {
  await transactionsView.loadTransactionSlice();
}

async function loadCockpit() {
  const response = await api(`/api/cockpit?month=${encodeURIComponent(currentMonthValue())}`);
  state.cockpit = response;
}

async function refreshCockpitData() {
  const requestId = ++state.cockpitRefreshRequestId;
  const month = currentMonthValue();
  const [
    accountsResponse,
    transactionsResponse,
    cardTransactionsResponse,
    cardPaymentsResponse,
    cockpitResponse,
  ] = await Promise.all([
    api("/api/checking-accounts"),
    api("/api/transactions"),
    api("/api/credit-card-transactions"),
    api("/api/credit-card-payments"),
    api(`/api/cockpit?month=${encodeURIComponent(month)}`),
  ]);
  if (requestId !== state.cockpitRefreshRequestId) {
    return;
  }
  state.accounts = accountsResponse.accounts || [];
  ensureSelectedAccount();
  state.transactions = transactionsResponse.transactions || [];
  state.cardTransactions = cardTransactionsResponse.transactions || [];
  state.cardPayments = cardPaymentsResponse.payments || [];
  state.cockpit = cockpitResponse;
  renderBaseViews();
  if (state.view === "cockpit") {
    renderCockpit();
  }
}

async function loadPortfolio(options = {}) {
  await portfolioView.loadPortfolio(options);
}

function markPortfolioDirty() {
  portfolioView.markPortfolioDirty();
}

function showPortfolioAssetForm() {
  portfolioView.showPortfolioAssetForm();
}

function resetPortfolioAssetForm() {
  portfolioView.resetPortfolioAssetForm();
}

function editPortfolioSourceTransaction(transactionId) {
  const transaction = findTransactionById(transactionId);
  if (!transaction) {
    setMessage(portfolioMessage, "Lançamento de origem não encontrado. Atualize os dados e tente novamente.", "error");
    return;
  }
  showModule("transactions");
  transactionAccount.value = String(transaction.account_id);
  state.selectedAccountId = transaction.account_id;
  renderTransactions();
  editTransaction(transaction);
}

async function loadClassifications() {
  await classificationsView.loadClassifications();
}

async function loadSpendingLimits() {
  await limitsView.loadSpendingLimits();
}

async function loadCurrentSpendingLimits() {
  await limitsView.loadCurrentSpendingLimits();
}

async function loadCardInvoice() {
  await cardsView.loadCardInvoice();
}

async function loadCardTransactions() {
  await cardsView.loadCardTransactions();
}

function ensureSelectedCreditCard() {
  cardsView.ensureSelectedCreditCard();
}

function ensureSelectedAccount() {
  if (state.accounts.some((account) => String(account.id) === String(state.selectedAccountId))) {
    return;
  }
  const orderedAccounts = [...state.accounts].sort((a, b) => Number(a.id) - Number(b.id));
  state.selectedAccountId = orderedAccounts[0] ? String(orderedAccounts[0].id) : "";
}

function showModule(view) {
  state.view = view;
  for (const [name, element] of Object.entries(moduleViews)) {
    element.hidden = name !== view;
  }
  navButtons.forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  renderLimitAlerts();
  moduleEyebrow.textContent = viewTitles[view][0];
  pageTitle.textContent = viewTitles[view][1];
  if (view === "cockpit") {
    renderCockpit();
    refreshCockpitData().catch((error) => console.error(error));
  }
  if (view === "transactions") {
    ensureSelectedAccount();
    renderTransactionAccounts();
    updateTransactionTypeState();
    loadTransactionSlice().then(renderTransactions).catch((error) => setMessage(transactionMessage, error.message, "error"));
  }
  if (view === "limits") {
    renderLimits();
  }
  if (view === "reports") {
    renderReports();
  }
  if (view === "portfolio") {
    renderPortfolio();
    loadPortfolio();
  }
  if (view === "creditCards") {
    renderCreditCards();
  }
  if (view === "cardLaunches") {
    renderCardInvoice();
  }
  if (view === "imports") {
    renderImportTargets();
  }
  if (view === "user" && state.user) {
    emailForm.elements.email.value = state.user.email;
    userAdminViewController.loadEmailConfigStatus();
  }
}

function initializeSidebar() {
  const storedValue = localStorage.getItem(SIDEBAR_COLLAPSED_KEY);
  const preferCollapsed = window.matchMedia("(max-width: 860px)").matches;
  setSidebarCollapsed(storedValue === null ? preferCollapsed : storedValue === "1", false);
}

function toggleSidebar() {
  const collapsed = !dashboardView.classList.contains("sidebar-collapsed");
  setSidebarCollapsed(collapsed, true);
}

function setSidebarCollapsed(collapsed, persist) {
  dashboardView.classList.toggle("sidebar-collapsed", collapsed);
  appSidebar.classList.toggle("is-collapsed", collapsed);
  sidebarToggle.setAttribute("aria-expanded", String(!collapsed));
  sidebarToggle.setAttribute("aria-label", collapsed ? "Expandir menu" : "Recolher menu");
  sidebarToggle.title = collapsed ? "Expandir menu" : "Recolher menu";
  if (persist) {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0");
  }
}

function deleteSeriesScope(id, transactions, label) {
  return transactionsView.deleteSeriesScope(id, transactions, label);
}

function findTransactionById(id) {
  return transactionsView.findTransactionById(id);
}

async function refreshAfterTransactionChange() {
  await transactionsView.refreshAfterTransactionChange();
}

function resetAccountForm() {
  accountsView.resetAccountForm();
}

function resetCreditCardForm() {
  cardsView.resetCreditCardForm();
}

function resetCardTransactionForm() {
  cardsView.resetCardTransactionForm();
}

function updateAccountTypeState() {
  accountsView.updateAccountTypeState();
}

function resetTransactionForm() {
  transactionsView.resetTransactionForm();
}

function editTransaction(transaction) {
  transactionsView.editTransaction(transaction);
}

function updateCardSeriesState() {
  cardsView.updateCardSeriesState();
}

function renderBaseViews() {
  renderAccounts();
  renderCreditCards();
  renderCreditCardPreferredPaymentAccounts();
  renderTransactionAccounts();
  renderImportTargets();
  renderPortfolioAssetAccounts();
  renderTransactionCategories();
}

function renderFinanceViews() {
  renderCockpit();
  renderTransactions();
  renderLimits();
  renderReports();
}

function renderManagementViews() {
  renderClassifications();
  renderPortfolio();
}

function renderCockpit() {
  cockpitView.renderCockpit();
}

function renderLimitAlerts() {
  cockpitView.renderLimitAlerts();
}

function chartColor(index) {
  return ["#14b8a6", "#6366f1", "#f97316", "#ec4899", "#22c55e", "#3b82f6"][index % 6];
}

function renderAccounts() {
  accountsView.renderAccounts();
}

function renderCreditCards() {
  cardsView.renderCreditCards();
}

function renderCardInvoice() {
  cardsView.renderCardInvoice();
}

function renderCreditCardPreferredPaymentAccounts() {
  cardsView.renderCreditCardPreferredPaymentAccounts();
}

function renderCardTransactionCategories() {
  cardsView.renderCardTransactionCategories();
}

function renderCardTransactionSubcategories() {
  cardsView.renderCardTransactionSubcategories();
}

function renderTransactionAccounts() {
  transactionsView.renderTransactionAccounts();
}

function renderImportTargets() {
  importsView.renderImportTargets();
}

function renderPortfolioAssetAccounts() {
  portfolioView.renderPortfolioAssetAccounts();
}

function renderTransactionCategories() {
  transactionsView.renderTransactionCategories();
}

function renderTransactionSubcategories() {
  transactionsView.renderTransactionSubcategories();
}

function renderTransactionTagOptions() {
  transactionsView.renderTransactionTagOptions();
}

function renderTransactions() {
  transactionsView.renderTransactions();
}

function selectedAccountTransactions(transactions = state.accountTransactions) {
  return transactionsView.selectedAccountTransactions(transactions);
}

function renderClassifications() {
  classificationsView.renderClassifications();
}

function renderLimits() {
  limitsView.renderLimits();
}

function renderReports() {
  reportsView.renderReports();
}

function renderPortfolio() {
  portfolioView.renderPortfolio();
}

function portfolioTotalsByCurrency(rows) {
  return portfolioView.portfolioTotalsByCurrency(rows);
}

function renderTransactionCollection(container, transactions, compact, balanceTransactions = transactions) {
  transactionsView.renderTransactionCollection(container, transactions, compact, balanceTransactions);
}

function launchActionButton(icon, label, attributes, extraClass = "") {
  return transactionsView.launchActionButton(icon, label, attributes, extraClass);
}

function updateTransactionTypeState() {
  transactionsView.updateTransactionTypeState();
}

function shiftTransactionMonth(delta) {
  transactionsView.shiftTransactionMonth(delta);
}

async function setTransactionMonth(month) {
  await transactionsView.setTransactionMonth(month);
}

async function shiftCardInvoiceMonth(delta) {
  await cardsView.shiftCardInvoiceMonth(delta);
}

async function setCardInvoiceMonth(month) {
  await cardsView.setCardInvoiceMonth(month);
}

function getCurrencyTotals() {
  const totals = new Map();
  for (const account of state.accounts) {
    const row = currencyTotalRow(totals, account.currency);
    const amount = accountProjectedBalance(account);
    row.current += amount;
    row.accounts.push({
      id: account.id,
      name: account.name,
      type: accountTypeLabel(account.account_type),
      amount,
      reconciled: accountReconciledBalance(account),
    });
  }
  for (const card of state.creditCards) {
    const row = currencyTotalRow(totals, card.currency);
    const openAmount = cardOpenBalance(card.id, currentMonthValue());
    const signedAmount = -openAmount;
    row.current += signedAmount;
    row.cards.push({
      id: card.id,
      name: card.name,
      issuer: card.issuer,
      amount: signedAmount,
      reconciled: -cardReconciledBalance(card.id),
    });
  }
  return new Map([...totals.entries()].sort(([currencyA], [currencyB]) => currencyA.localeCompare(currencyB)));
}

function currencyTotalRow(totals, currency) {
  const normalizedCurrency = currency || "BRL";
  if (!totals.has(normalizedCurrency)) {
    totals.set(normalizedCurrency, {
      current: 0,
      accounts: [],
      cards: [],
    });
  }
  return totals.get(normalizedCurrency);
}

function accountReconciledBalance(account) {
  const limitDate = currentMonthEndDate();
  return accountBalanceUntil(account, limitDate, true);
}

function accountProjectedBalance(account) {
  return accountBalanceUntil(account, currentMonthEndDate(), false);
}

function accountBalanceUntil(account, limitDate, reconciledOnly) {
  return Number(account.initial_balance || 0) + state.transactions.reduce((total, transaction) => {
    if (transaction.date > limitDate || !transaction.reconciled_at) {
      if (reconciledOnly || transaction.date > limitDate) {
        return total;
      }
    }
    if (reconciledOnly && !transaction.reconciled_at) {
      return total;
    }
    const amount = Number(transaction.amount);
    if (String(transaction.account_id) === String(account.id)) {
      total += transactionSourceDelta(transaction.type, amount);
    }
    if (transaction.type === "transfer" && String(transaction.destination_account_id || "") === String(account.id)) {
      total += Number(transaction.destination_amount || transaction.amount);
    }
    return total;
  }, 0);
}

function currentMonthEndDate() {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
}

function cardReconciledBalance(cardId) {
  return cardsView.cardReconciledBalance(cardId);
}

function cardOpenBalance(cardId, untilInvoiceMonth = null) {
  return cardsView.cardOpenBalance(cardId, untilInvoiceMonth);
}

function creditCardCurrency(cardId) {
  return cardsView.creditCardCurrency(cardId);
}

function getBalanceUntil(limitDate, transactions = state.transactions, reconciledOnly = false) {
  const totals = new Map();
  
  // If a specific account is selected, calculate balance only for that account
  if (state.selectedAccountId) {
    const account = state.accounts.find((entry) => String(entry.id) === String(state.selectedAccountId));
    if (account) {
      totals.set(account.currency, Number(account.initial_balance));
      
      for (const transaction of transactions) {
        if (transaction.date > limitDate) {
          continue;
        }
        if (reconciledOnly && !transaction.reconciled_at) {
          continue;
        }
        const amount = Number(transaction.amount);
        const sourceCurrency = transaction.account_currency;
        if (String(transaction.account_id) === String(state.selectedAccountId)) {
          totals.set(sourceCurrency, (totals.get(sourceCurrency) || 0) + transactionSourceDelta(transaction.type, amount));
        }
        if (transaction.type === "transfer" && transaction.destination_account_id) {
          const destinationCurrency = transaction.destination_account_currency || sourceCurrency;
          const destinationAmount = Number(transaction.destination_amount || transaction.amount);
          if (String(transaction.destination_account_id) === String(state.selectedAccountId)) {
            totals.set(destinationCurrency, (totals.get(destinationCurrency) || 0) + destinationAmount);
          }
        }
      }
    }
  } else {
    // No account selected: calculate balance for all accounts
    for (const account of state.accounts) {
      const current = totals.get(account.currency) || 0;
      totals.set(account.currency, current + Number(account.initial_balance));
    }
    for (const transaction of transactions) {
      if (transaction.date > limitDate) {
        continue;
      }
      if (reconciledOnly && !transaction.reconciled_at) {
        continue;
      }
      const amount = Number(transaction.amount);
      const sourceCurrency = transaction.account_currency;
      totals.set(sourceCurrency, (totals.get(sourceCurrency) || 0) + transactionSourceDelta(transaction.type, amount));
      if (transaction.type === "transfer" && transaction.destination_account_id) {
        const destinationCurrency = transaction.destination_account_currency || sourceCurrency;
        const destinationAmount = Number(transaction.destination_amount || transaction.amount);
        totals.set(destinationCurrency, (totals.get(destinationCurrency) || 0) + destinationAmount);
      }
    }
  }
  
  return new Map([...totals.entries()].sort(([currencyA], [currencyB]) => currencyA.localeCompare(currencyB)));
}

function transactionSourceDelta(type, amount) {
  if (type === "income") {
    return amount;
  }
  return -amount;
}

function renderCockpitPortfolioByType() {
  cockpitView.renderCockpitPortfolioByType();
}

function showAuth() {
  authView.hidden = false;
  dashboardView.hidden = true;
  authViewController.switchAuthMode("login");
}
