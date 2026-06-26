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

accountForm.addEventListener("submit", handleAccountSubmit);
accountForm.elements.account_type.addEventListener("change", updateAccountTypeState);
creditCardForm.addEventListener("submit", handleCreditCardSubmit);
creditCardForm.elements.currency.addEventListener("change", renderCreditCardPreferredPaymentAccounts);
cardInvoiceCard.addEventListener("change", handleCardInvoiceCardChange);
cardInvoiceList.addEventListener("click", handleCardInvoiceListClick);
previousCardInvoiceButton.addEventListener("click", () => shiftCardInvoiceMonth(-1));
todayCardInvoiceButton.addEventListener("click", () => setCardInvoiceMonth(currentMonthValue()));
cardInvoiceMonthLabel.addEventListener("click", (event) => {
  event.stopPropagation();
  openMonthPicker(event.currentTarget, state.cardInvoiceMonth, setCardInvoiceMonth);
});
nextCardInvoiceButton.addEventListener("click", () => shiftCardInvoiceMonth(1));
cardInvoicePaymentForm.addEventListener("submit", handleCardInvoicePaymentSubmit);
cardPaymentAccount.addEventListener("change", renderCardInvoice);
cardTransactionForm.addEventListener("submit", handleCardTransactionSubmit);
cardTransactionType.addEventListener("change", renderCardTransactionCategories);
cardTransactionCategory.addEventListener("change", renderCardTransactionSubcategories);
cardSeriesKind.addEventListener("change", updateCardSeriesState);
transactionForm.addEventListener("submit", handleTransactionSubmit);
importForm.addEventListener("submit", handleImportSubmit);
importTarget.addEventListener("change", renderImportTargets);
downloadImportTemplateButton.addEventListener("click", downloadImportTemplate);
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
addPortfolioAssetButton.addEventListener("click", showPortfolioAssetForm);
refreshPortfolioButton.addEventListener("click", () => loadPortfolio({ refreshMessage: true }));
portfolioAssetForm.addEventListener("submit", handlePortfolioAssetSubmit);
portfolioAssetType.addEventListener("change", updatePortfolioAssetTypeState);
portfolioFixedIncomeSubtype.addEventListener("change", syncPortfolioFixedIncomeSubtype);
portfolioPensionSubtype.addEventListener("change", syncPortfolioPensionSubtype);
cancelPortfolioAssetButton.addEventListener("click", resetPortfolioAssetForm);
deletePortfolioAssetButton.addEventListener("click", deletePortfolioAsset);
portfolioGroupFilter.addEventListener("change", () => {
  state.portfolioGroup = portfolioGroupFilter.value;
  renderPortfolio();
});
transactionSearch.addEventListener("input", renderTransactions);
transactionList.addEventListener("click", handleTransactionListClick);
cancelEditButton.addEventListener("click", resetAccountForm);
cancelTransactionEditButton.addEventListener("click", resetTransactionForm);
cancelCreditCardEditButton.addEventListener("click", resetCreditCardForm);
cancelCardTransactionEditButton.addEventListener("click", resetCardTransactionForm);
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
  const response = await api("/api/checking-accounts");
  state.accounts = response.accounts;
  ensureSelectedAccount();
  await loadArchivedAccounts();
  await loadTransactionSlice();
  markPortfolioDirty();
  renderBaseViews();
  renderFinanceViews();
}

async function loadCreditCards() {
  const response = await api("/api/credit-cards");
  state.creditCards = response.cards;
  ensureSelectedCreditCard();
  await loadArchivedCreditCards();
  await loadCardTransactions();
  await loadCardInvoice();
  await loadCockpit();
  renderBaseViews();
  renderFinanceViews();
}

async function loadArchivedAccounts() {
  const response = await api("/api/checking-accounts?status=archived");
  state.archivedAccounts = response.accounts;
}

async function loadArchivedCreditCards() {
  const response = await api("/api/credit-cards?status=archived");
  state.archivedCreditCards = response.cards;
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

async function loadCockpit() {
  const response = await api(`/api/cockpit?month=${encodeURIComponent(currentMonthValue())}`);
  state.cockpit = response;
}

async function loadPortfolio(options = {}) {
  if (state.portfolio && !state.portfolioDirty && !options.force && !options.refreshMessage) {
    renderPortfolio();
    renderCockpitPortfolioByType();
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
  try {
    const endpoint = options.refreshMessage || options.force ? "/api/portfolio?refresh=1" : "/api/portfolio";
    state.portfolio = await api(endpoint);
    state.portfolioDirty = false;
    if (options.refreshMessage) {
      setMessage(portfolioMessage, "Portfólio atualizado.", "success");
    }
  } catch (error) {
    state.portfolio = null;
    state.portfolioError = error.message;
    if (options.refreshMessage || state.view === "portfolio") {
      setMessage(portfolioMessage, error.message, "error");
    }
  } finally {
    state.portfolioLoading = false;
  }
  renderPortfolio();
  renderCockpitPortfolioByType();
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
    setMessage(portfolioMessage, "Ativo excluído do portfólio.", "success");
  } catch (error) {
    setMessage(portfolioMessage, error.message, "error");
  }
}

async function redeemPortfolioPosition(position) {
  const rawAmount = window.prompt("Valor do resgate", moneyInputValue(position.current_value));
  if (rawAmount === null) {
    return;
  }
  const rawDate = window.prompt("Data do resgate", todayLocalDateValue());
  if (rawDate === null) {
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
        amount: rawAmount,
        date: rawDate,
      },
    });
    state.portfolio = response;
    state.portfolioDirty = false;
    await loadTransactionsAndAccounts();
    renderPortfolio();
    setMessage(portfolioMessage, "Resgate registrado e valor retornado para a conta da carteira.", "success");
  } catch (error) {
    setMessage(portfolioMessage, error.message, "error");
  }
}

function updatePortfolioAssetTypeState() {
  const assetType = portfolioAssetType.value;
  portfolioFundFields.hidden = assetType !== "fund";
  portfolioFixedFields.hidden = assetType !== "fixed_income";
  portfolioPensionFields.hidden = assetType !== "private_pension";
  portfolioSavingsFields.hidden = assetType !== "savings";
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
}

function syncPortfolioFixedIncomeSubtype() {
  if (portfolioAssetType.value === "fixed_income" && portfolioFixedIncomeSubtype.value) {
    portfolioAssetIdentifier.value = portfolioFixedIncomeSubtype.value;
  }
}

function syncPortfolioPensionSubtype() {
  if (portfolioAssetType.value === "private_pension" && portfolioPensionSubtype.value) {
    portfolioAssetIdentifier.value = portfolioPensionSubtype.value;
  }
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
  const requestId = ++state.cardInvoiceRequestId;
  const cardId = String(state.selectedCreditCardId || "");
  const month = state.cardInvoiceMonth;
  if (!state.selectedCreditCardId) {
    state.cardInvoiceTransactions = [];
    state.cardInvoicePayments = [];
    return;
  }
  const response = await api(`/api/credit-card-invoice?card_id=${encodeURIComponent(cardId)}&month=${encodeURIComponent(month)}`);
  if (
    requestId !== state.cardInvoiceRequestId
    || month !== state.cardInvoiceMonth
    || cardId !== String(state.selectedCreditCardId || "")
  ) {
    return;
  }
  state.cardInvoiceTransactions = response.transactions || [];
  state.cardInvoicePayments = response.payments || [];
}

async function loadCardTransactions() {
  const [transactionsResponse, paymentsResponse] = await Promise.all([
    api("/api/credit-card-transactions"),
    api("/api/credit-card-payments"),
  ]);
  state.cardTransactions = transactionsResponse.transactions || [];
  state.cardPayments = paymentsResponse.payments || [];
}

function ensureSelectedCreditCard() {
  if (state.creditCards.some((card) => String(card.id) === String(state.selectedCreditCardId))) {
    return;
  }
  state.selectedCreditCardId = state.creditCards[0] ? String(state.creditCards[0].id) : "";
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

async function handleAccountSubmit(event) {
  event.preventDefault();
  setMessage(accountMessage, "");
  const data = formData(accountForm);
  const isEditing = Boolean(data.id);
  try {
    await api(isEditing ? `/api/checking-accounts/${data.id}` : "/api/checking-accounts", {
      method: isEditing ? "PUT" : "POST",
      body: data,
    });
    resetAccountForm();
    await loadAccounts();
    setMessage(accountMessage, "Conta salva.", "success");
  } catch (error) {
    setMessage(accountMessage, error.message, "error");
  }
}

async function handleCreditCardSubmit(event) {
  event.preventDefault();
  setMessage(creditCardMessage, "");
  const data = formData(creditCardForm);
  const isEditing = Boolean(data.id);
  try {
    await api(isEditing ? `/api/credit-cards/${data.id}` : "/api/credit-cards", {
      method: isEditing ? "PUT" : "POST",
      body: data,
    });
    resetCreditCardForm();
    await loadCreditCards();
    setMessage(creditCardMessage, "Cartão salvo.", "success");
  } catch (error) {
    setMessage(creditCardMessage, error.message, "error");
  }
}

async function handleCardInvoiceCardChange() {
  state.selectedCreditCardId = cardInvoiceCard.value;
  setMessage(cardInvoiceMessage, "");
  await loadCardInvoice();
  renderCreditCards();
}

async function handleCardTransactionSubmit(event) {
  event.preventDefault();
  setMessage(cardInvoiceMessage, "");
  if (!state.selectedCreditCardId) {
    setMessage(cardInvoiceMessage, "Cadastre um cartão antes de lançar na fatura.", "error");
    return;
  }
  const data = formData(cardTransactionForm);
  setFormBusy(cardTransactionForm, true);
  data.credit_card_id = state.selectedCreditCardId;
  data.invoice_month = state.cardInvoiceMonth;
  const isEditing = Boolean(data.id);
  if (isEditing && shouldAskFutureCardReplication(data.id)) {
    data.apply_to_future = window.confirm("Replicar esta alteração nos próximos lançamentos futuros desta série? Lançamentos passados ou conciliados não serão alterados.");
  }
  try {
    await api(isEditing ? `/api/credit-card-transactions/${data.id}` : "/api/credit-card-transactions", {
      method: isEditing ? "PUT" : "POST",
      body: data,
    });
    resetCardTransactionForm();
    await loadCardInvoice();
    await loadCardTransactions();
    renderCreditCards();
    renderLimits();
    renderCockpit();
    setMessage(cardInvoiceMessage, isEditing ? "Lançamento do cartão atualizado." : "Lançamento do cartão salvo.", "success");
  } catch (error) {
    setMessage(cardInvoiceMessage, error.message, "error");
  } finally {
    setFormBusy(cardTransactionForm, false);
  }
}

async function handleCardInvoicePaymentSubmit(event) {
  event.preventDefault();
  setMessage(cardInvoiceMessage, "");
  const data = formData(cardInvoicePaymentForm);
  data.credit_card_id = state.selectedCreditCardId;
  data.invoice_month = state.cardInvoiceMonth;
  try {
    await api("/api/credit-card-invoice/pay", { method: "POST", body: data });
    await loadTransactionsAndAccounts();
    setMessage(cardInvoiceMessage, "Fatura paga e débito lançado na conta.", "success");
  } catch (error) {
    setMessage(cardInvoiceMessage, error.message, "error");
  }
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

function shouldAskFutureCardReplication(transactionId) {
  const transaction = state.cardTransactions.find((entry) => String(entry.id) === String(transactionId));
  return Boolean(transaction && transaction.series_id && isInstallmentTransaction(transaction));
}

async function handleImportSubmit(event) {
  event.preventDefault();
  setMessage(importMessage, "");
  importResult.innerHTML = "";
  const target = importTarget.value;
  if (target === "account" && state.accounts.length === 0) {
    setMessage(importMessage, "Cadastre uma conta antes de importar lançamentos.", "error");
    return;
  }
  if (target === "card" && state.creditCards.length === 0) {
    setMessage(importMessage, "Cadastre um cartão antes de importar lançamentos.", "error");
    return;
  }
  const data = new FormData(importForm);
  data.set("target", target);
  data.set("target_id", target === "card" ? importCreditCard.value : importAccount.value);
  setFormBusy(importForm, true);
  try {
    const response = await upload("/api/import/system-template", data);
    importForm.reset();
    importTarget.value = target;
    renderImportTargets();
    await loadTransactionsAndAccounts();
    renderImportResult(response);
    setMessage(importMessage, `${response.imported} lançamento(s) importado(s).`, "success");
  } catch (error) {
    setMessage(importMessage, error.message, "error");
  } finally {
    setFormBusy(importForm, false);
  }
}

function downloadImportTemplate() {
  const target = importTarget.value || "account";
  window.location.href = `/api/import/template?target=${encodeURIComponent(target)}`;
}

async function archiveAccount(id) {
  try {
    await api(`/api/checking-accounts/${id}`, { method: "DELETE" });
    await loadAccounts();
  } catch (error) {
    setMessage(accountMessage, error.message, "error");
  }
}

async function restoreAccount(id) {
  try {
    await api(`/api/checking-accounts/${id}/restore`, { method: "POST" });
    await loadAccounts();
  } catch (error) {
    setMessage(accountMessage, error.message, "error");
  }
}

async function archiveCreditCard(id) {
  try {
    await api(`/api/credit-cards/${id}`, { method: "DELETE" });
    await loadCreditCards();
  } catch (error) {
    setMessage(creditCardMessage, error.message, "error");
  }
}

async function restoreCreditCard(id) {
  try {
    await api(`/api/credit-cards/${id}/restore`, { method: "POST" });
    await loadCreditCards();
  } catch (error) {
    setMessage(creditCardMessage, error.message, "error");
  }
}

async function deleteCardTransaction(id) {
  try {
    const scope = deleteSeriesScope(id, state.cardTransactions, "cartão");
    await api(`/api/credit-card-transactions/${id}${scope}`, { method: "DELETE" });
    await loadCardInvoice();
    await loadCardTransactions();
    renderCreditCards();
    renderLimits();
    renderCockpit();
    setMessage(cardInvoiceMessage, "Lançamento do cartão excluído.", "success");
  } catch (error) {
    setMessage(cardInvoiceMessage, error.message, "error");
  }
}

async function toggleCardTransactionReconciliation(id, reconciled) {
  try {
    await api(`/api/credit-card-transactions/${id}/reconciliation`, {
      method: "PUT",
      body: { reconciled },
    });
    await loadCardInvoice();
    await loadCardTransactions();
    renderCreditCards();
    renderLimits();
    renderCockpit();
  } catch (error) {
    setMessage(cardInvoiceMessage, error.message, "error");
  }
}

async function moveCardTransactionInvoice(id, direction) {
  try {
    await api(`/api/credit-card-transactions/${id}/invoice`, {
      method: "PUT",
      body: { direction },
    });
    await loadCardInvoice();
    await loadCardTransactions();
    renderCreditCards();
    renderLimits();
    renderCockpit();
    setMessage(cardInvoiceMessage, direction === "next" ? "Lançamento movido para a próxima fatura." : "Lançamento movido para a fatura anterior.", "success");
  } catch (error) {
    setMessage(cardInvoiceMessage, error.message, "error");
  }
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

function editAccount(account) {
  formTitle.textContent = "Editar conta";
  accountForm.elements.id.value = account.id;
  accountForm.elements.name.value = account.name;
  accountForm.elements.bank_name.value = account.bank_name;
  accountForm.elements.branch.value = account.branch || "";
  accountForm.elements.account_number.value = account.account_number || "";
  accountForm.elements.account_type.value = account.account_type || "liquidity";
  accountForm.elements.currency.value = account.currency;
  accountForm.elements.initial_balance.value = account.initial_balance.replace(".", ",");
  accountForm.elements.notes.value = account.notes || "";
  cancelEditButton.hidden = false;
  updateAccountTypeState();
  accountForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

function editCreditCard(card) {
  creditCardFormTitle.textContent = "Editar cartão";
  creditCardForm.elements.id.value = card.id;
  creditCardForm.elements.name.value = card.name;
  creditCardForm.elements.issuer.value = card.issuer;
  creditCardForm.elements.network.value = card.network || "";
  creditCardForm.elements.currency.value = card.currency;
  creditCardForm.elements.limit.value = card.limit.replace(".", ",");
  creditCardForm.elements.closing_day.value = card.closing_day;
  creditCardForm.elements.due_day.value = card.due_day;
  renderCreditCardPreferredPaymentAccounts();
  creditCardForm.elements.preferred_payment_account_id.value = card.preferred_payment_account_id || "";
  creditCardForm.elements.notes.value = card.notes || "";
  cancelCreditCardEditButton.hidden = false;
  creditCardForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetAccountForm() {
  accountForm.reset();
  accountForm.elements.id.value = "";
  formTitle.textContent = "Nova conta";
  cancelEditButton.hidden = true;
  updateAccountTypeState();
  setMessage(accountMessage, "");
}

function resetCreditCardForm() {
  creditCardForm.reset();
  creditCardForm.elements.id.value = "";
  creditCardFormTitle.textContent = "Novo cartão";
  cancelCreditCardEditButton.hidden = true;
  renderCreditCardPreferredPaymentAccounts();
  setMessage(creditCardMessage, "");
}

function resetCardTransactionForm() {
  cardTransactionForm.reset();
  cardTransactionForm.elements.id.value = "";
  cardTransactionForm.elements.date.value = todayLocalDateValue();
  cardTransactionForm.elements.credit_card_id.value = state.selectedCreditCardId;
  cardTransactionForm.elements.invoice_month.value = state.cardInvoiceMonth;
  cardSeriesKind.disabled = false;
  cardInstallmentCount.disabled = false;
  cardRecurrenceFrequency.disabled = false;
  cardRecurrenceCount.disabled = false;
  cardSeriesKind.value = "single";
  cardInstallmentCount.value = "2";
  cardRecurrenceFrequency.value = "monthly";
  cardRecurrenceCount.value = "12";
  cardTransactionFormTitle.textContent = "Novo lançamento no cartão";
  cancelCardTransactionEditButton.hidden = true;
  cardTransactionForm.querySelector('button[type="submit"]').textContent = "Salvar lançamento";
  updateCardSeriesState();
  renderCardTransactionCategories();
}

function updateAccountTypeState() {
  const isWallet = accountForm.elements.account_type.value === "wallet";
  accountBankLabel.hidden = isWallet;
  accountBankDetails.hidden = isWallet;
  accountForm.elements.bank_name.required = !isWallet;
  accountForm.elements.bank_name.disabled = isWallet;
  accountForm.elements.branch.disabled = isWallet;
  accountForm.elements.account_number.disabled = isWallet;
  if (isWallet) {
    accountForm.elements.bank_name.value = "";
    accountForm.elements.branch.value = "";
    accountForm.elements.account_number.value = "";
  }
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

function editCardTransaction(transaction) {
  setMessage(cardInvoiceMessage, "");
  cardTransactionForm.elements.id.value = transaction.id;
  cardTransactionForm.elements.credit_card_id.value = transaction.credit_card_id;
  cardTransactionForm.elements.invoice_month.value = transaction.invoice_month;
  cardTransactionType.value = transaction.type;
  cardTransactionForm.elements.date.value = transaction.date;
  cardTransactionForm.elements.description.value = transaction.description;
  cardTransactionForm.elements.amount.value = moneyInputValue(transaction.amount);
  cardTransactionForm.elements.notes.value = transaction.notes || "";
  cardSeriesKind.value = isInstallmentTransaction(transaction) ? "installment" : transaction.series_kind || "single";
  cardInstallmentCount.value = transaction.installment_count || "2";
  cardRecurrenceFrequency.value = transaction.recurrence_frequency || "monthly";
  cardRecurrenceCount.value = transaction.installment_count || "12";
  cardSeriesKind.disabled = true;
  cardInstallmentCount.disabled = true;
  cardRecurrenceFrequency.disabled = true;
  cardRecurrenceCount.disabled = true;
  updateCardSeriesState();
  cardSeriesKind.disabled = true;
  cardInstallmentCount.disabled = true;
  cardRecurrenceFrequency.disabled = true;
  cardRecurrenceCount.disabled = true;
  renderCardTransactionCategories();
  if (transaction.category_name) {
    cardTransactionCategory.value = transaction.category_name;
  }
  renderCardTransactionSubcategories();
  if (transaction.subcategory_name) {
    cardTransactionSubcategory.value = transaction.subcategory_name;
  }
  cardTransactionFormTitle.textContent = "Editar lançamento no cartão";
  cancelCardTransactionEditButton.hidden = false;
  cardTransactionForm.querySelector('button[type="submit"]').textContent = "Salvar alterações";
  cardTransactionForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

function updateCardSeriesState() {
  const isInstallment = cardSeriesKind.value === "installment";
  const isRecurring = cardSeriesKind.value === "recurring";
  cardInstallmentCountLabel.hidden = !isInstallment;
  cardInstallmentCount.disabled = !isInstallment;
  cardRecurrenceFields.hidden = !isRecurring;
  cardRecurrenceFrequency.disabled = !isRecurring;
  cardRecurrenceCount.disabled = !isRecurring;
  cardInstallmentCount.name = isRecurring ? "unused_installment_count" : "installment_count";
  cardRecurrenceCount.name = isRecurring ? "installment_count" : "recurrence_count";
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
  const totals = getCurrencyTotals();
  const monthTotals = state.cockpit?.month_totals || getCurrentMonthTotals();
  monthIncome.textContent = formatMoney(monthTotals.income, "BRL");
  monthExpense.textContent = formatMoney(monthTotals.expense, "BRL");
  monthInvestment.textContent = formatMoney(monthTotals.investment, "BRL");
  savingsRate.textContent = formatPercent(monthTotals.savings_rate ?? monthTotals.savingsRate);
  renderCurrencyTotals(totals);
  renderCockpitPortfolioByType();
  renderMonthlyPlanning();
  renderInstallmentDebts();
  renderLimitAlerts();
  renderTopExpensesChart();
  renderTopIncomeChart();
}

function renderLimitAlerts() {
  limitsView.renderLimitAlerts();
}

function renderMonthlyPlanning() {
  if (state.cockpit?.planning) {
    monthlyPlanningList.innerHTML = "";
    monthlyPlanningList.append(
      planningSectionFromRows("Receitas recorrentes", state.cockpit.planning.income || [], "income"),
      planningSectionFromRows("Investimentos planejados", state.cockpit.planning.investment || [], "investment"),
      planningSectionFromRows("Despesas recorrentes", state.cockpit.planning.expense || [], "expense"),
    );
    return;
  }
  const prefix = currentMonthValue();
  const sections = [
    ["Receitas recorrentes", "income", (transaction) => transaction.type === "income" && transaction.series_kind === "recurring"],
    ["Investimentos planejados", "investment", (transaction) => isInvestmentTransaction(transaction) && transaction.series_kind !== "single"],
    ["Despesas recorrentes", "expense", (transaction) => transaction.type === "expense" && transaction.series_kind === "recurring"],
  ];
  monthlyPlanningList.innerHTML = "";
  for (const [title, kind, predicate] of sections) {
    monthlyPlanningList.append(planningSection(title, state.transactions.filter((transaction) => (
      transaction.date.startsWith(prefix) && predicate(transaction)
    )), kind));
  }
}

function planningSectionFromRows(title, rows, kind = "neutral") {
  const section = document.createElement("section");
  section.className = `planning-section planning-section-${kind}`;
  const total = rows.reduce((sum, item) => sum + Number(item.total || 0), 0);
  const content = rows.length
    ? rows.map((item) => `
      <div class="planning-row">
        <span>${escapeHtml(item.label)}</span>
        <strong>${formatMoney(item.total, "BRL")}</strong>
      </div>
    `).join("")
    : '<div class="empty-state compact">Nada previsto neste mês.</div>';
  section.innerHTML = `
    <div class="planning-section-header">
      <h3>${title}</h3>
      <strong>${formatMoney(total, "BRL")}</strong>
    </div>
    ${content}
  `;
  return section;
}

function planningSection(title, transactions, kind = "neutral") {
  const section = document.createElement("section");
  section.className = `planning-section planning-section-${kind}`;
  const grouped = groupTransactionsByCategory(transactions);
  const total = grouped.reduce((sum, item) => sum + item.total, 0);
  const rows = grouped.length
    ? grouped.map((item) => `
      <div class="planning-row">
        <span>${escapeHtml(item.label)}</span>
        <strong>${formatMoney(item.total, "BRL")}</strong>
      </div>
    `).join("")
    : '<div class="empty-state compact">Nada previsto neste mês.</div>';
  section.innerHTML = `
    <div class="planning-section-header">
      <h3>${title}</h3>
      <strong>${formatMoney(total, "BRL")}</strong>
    </div>
    ${rows}
  `;
  return section;
}

function renderInstallmentDebts() {
  if (!installmentDebtList) {
    return;
  }
  const currentMonth = currentMonthValue();
  const rows = new Map();
  for (const transaction of state.transactions) {
    const transactionMonth = transaction.date.slice(0, 7);
    if (!isOpenInstallmentDebt(transaction, transactionMonth, currentMonth)) {
      continue;
    }
    const key = `account:${transaction.account_id}`;
    const row = rows.get(key) || { label: transaction.account_name || "Conta", detail: "Conta", currency: transaction.account_currency || "BRL", total: 0, debts: new Map() };
    addInstallmentDebt(row, transaction, "account");
    rows.set(key, row);
  }
  for (const transaction of state.cardTransactions) {
    if (!isOpenInstallmentDebt(transaction, transaction.invoice_month, currentMonth)) {
      continue;
    }
    const key = `card:${transaction.credit_card_id}`;
    const row = rows.get(key) || { label: transaction.credit_card_name || "Cartão", detail: "Cartão", currency: transaction.card_currency || "BRL", total: 0, debts: new Map() };
    addInstallmentDebt(row, transaction, "card");
    rows.set(key, row);
  }
  const debts = [...rows.values()].sort((a, b) => b.total - a.total);
  if (debts.length === 0) {
    installmentDebtList.innerHTML = `
      <section class="planning-section">
        <div class="planning-section-header">
          <h3>Total em aberto</h3>
          <strong class="danger-text">${formatMoney(0, "BRL")}</strong>
        </div>
        <div class="empty-state compact">Nenhuma compra parcelada em aberto.</div>
      </section>
    `;
    return;
  }
  const debtTotals = summarizeDebtTotals(debts);
  installmentDebtList.innerHTML = `
    <section class="planning-section">
      <div class="planning-section-header">
        <h3>Total em aberto</h3>
        <strong class="danger-text">${formatDebtTotals(debtTotals)}</strong>
      </div>
      ${debts.map((row) => `
        <div class="debt-group">
          <div class="debt-group-header">
            <span>${escapeHtml(row.label)}</span>
            <strong>${formatMoney(row.total, row.currency)}</strong>
          </div>
          <div class="debt-items">
            ${[...row.debts.values()].sort((a, b) => b.total - a.total).map((debt) => `
              <div class="debt-item">
                <span>${escapeHtml(debt.description)} - ${installmentDebtCountLabel(debt.count)}</span>
                <strong>${formatMoney(debt.total, row.currency)}</strong>
              </div>
            `).join("")}
          </div>
        </div>
      `).join("")}
    </section>
  `;
}

function summarizeDebtTotals(debts) {
  return debts.reduce((totals, row) => {
    totals.set(row.currency, (totals.get(row.currency) || 0) + row.total);
    return totals;
  }, new Map());
}

function formatDebtTotals(totals) {
  if (!totals.size) {
    return formatMoney(0, "BRL");
  }
  return [...totals.entries()].map(([currency, total]) => formatMoney(total, currency)).join(" · ");
}

function addInstallmentDebt(row, transaction, origin) {
  const amount = Number(transaction.amount || 0);
  const debtKey = transaction.series_id
    ? `${origin}:series:${transaction.series_id}`
    : `${origin}:single:${transaction.description}`;
  const debt = row.debts.get(debtKey) || { description: transaction.description || "Lançamento parcelado", total: 0, count: 0 };
  row.total += amount;
  debt.total += amount;
  debt.count += 1;
  row.debts.set(debtKey, debt);
}

function installmentDebtCountLabel(count) {
  return `${count} ${count === 1 ? "parcela restante" : "parcelas restantes"}`;
}

function isOpenInstallmentDebt(transaction, transactionMonth, currentMonth) {
  if (!isInstallmentTransaction(transaction) || transaction.type !== "expense" || transactionMonth < currentMonth) {
    return false;
  }
  return transactionMonth > currentMonth || !transaction.reconciled_at;
}

function groupTransactionsByCategory(transactions) {
  const totals = new Map();
  for (const transaction of transactions) {
    const label = formatCategoryPath(transaction);
    totals.set(label, (totals.get(label) || 0) + Number(transaction.amount_brl || transaction.amount));
  }
  return [...totals.entries()]
    .map(([label, total]) => ({ label, total }))
    .sort((a, b) => b.total - a.total);
}

function renderTopExpensesChart() {
  if (state.cockpit?.top_expenses) {
    renderDonutListChart(topExpensesChart, state.cockpit.top_expenses, {
      empty: "Nenhuma despesa neste mês.",
      totalLabel: "Despesas",
    });
    return;
  }
  const prefix = currentMonthValue();
  const grouped = groupTransactionsByCategory(state.transactions.filter((transaction) => (
    transaction.date.startsWith(prefix) && transaction.type === "expense"
  )));
  renderDonutListChart(topExpensesChart, rankedChartItems(grouped, 5), {
    empty: "Nenhuma despesa neste mês.",
    totalLabel: "Despesas",
  });
}

function renderTopIncomeChart() {
  if (state.cockpit?.top_income) {
    renderDonutListChart(cashDistributionChart, state.cockpit.top_income, {
      empty: "Nenhuma receita neste mês.",
      totalLabel: "Receitas",
    });
    return;
  }
  const prefix = currentMonthValue();
  const grouped = groupTransactionsByCategory(state.transactions.filter((transaction) => (
    transaction.date.startsWith(prefix) && transaction.type === "income"
  )));
  renderDonutListChart(cashDistributionChart, rankedChartItems(grouped, 3), {
    empty: "Nenhuma receita neste mês.",
    totalLabel: "Receitas",
  });
}

function rankedChartItems(items, visibleCount) {
  const validItems = items.filter((item) => item.total > 0);
  if (validItems.length <= visibleCount) {
    return validItems;
  }
  const visible = validItems.slice(0, visibleCount);
  const othersTotal = validItems.slice(visibleCount).reduce((sum, item) => sum + item.total, 0);
  if (othersTotal > 0) {
    visible.push({ label: "Outros", total: othersTotal });
  }
  return visible;
}

function renderDonutListChart(container, items, options) {
  container.innerHTML = "";
  const total = options.total ?? items.reduce((sum, item) => sum + item.total, 0);
  if (!total || items.length === 0) {
    container.append(emptyState(options.empty, true));
    return;
  }
  const chart = document.createElement("div");
  chart.className = "donut-chart";
  chart.innerHTML = `
    ${donutSvg(items, total)}
    <div class="donut-center">
      <span>${escapeHtml(options.totalLabel)}</span>
      <strong>${formatMoney(total, "BRL")}</strong>
    </div>
  `;
  const list = document.createElement("div");
  list.className = "chart-list";
  list.innerHTML = items.map((item, index) => {
    const percent = total ? item.total / total : 0;
    return `
      <div class="chart-row">
        <span><i style="background:${chartColor(index)}"></i>${escapeHtml(item.label)}</span>
        <strong>${formatMoney(item.total, "BRL")} · ${formatPercent(percent)}</strong>
      </div>
    `;
  }).join("");
  container.append(chart, list);
}

function donutSvg(items, total) {
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  let offset = 0;
  const circles = items.map((item, index) => {
    const length = total ? (item.total / total) * circumference : 0;
    const circle = `
      <circle cx="60" cy="60" r="${radius}" fill="transparent" stroke="${chartColor(index)}"
        stroke-width="18" stroke-dasharray="${length} ${circumference - length}"
        stroke-dashoffset="${-offset}" />
    `;
    offset += length;
    return circle;
  }).join("");
  return `<svg viewBox="0 0 120 120" role="img" aria-label="Gráfico de distribuição">${circles}</svg>`;
}

function chartColor(index) {
  return ["#14b8a6", "#6366f1", "#f97316", "#ec4899", "#22c55e", "#3b82f6"][index % 6];
}

function renderAccounts() {
  accountList.innerHTML = "";
  if (state.accounts.length === 0) {
    accountList.append(emptyState("Nenhuma conta cadastrada ainda."));
  } else {
    state.accounts.forEach((account) => {
      accountList.append(accountCard(account, "active"));
    });
  }
  renderArchivedAccounts();
}

function renderArchivedAccounts() {
  archivedAccountList.innerHTML = "";
  if (state.archivedAccounts.length === 0) {
    archivedAccountList.append(emptyState("Nenhuma conta arquivada."));
    return;
  }
  state.archivedAccounts.forEach((account) => {
    archivedAccountList.append(accountCard(account, "archived"));
  });
}

function renderCreditCards() {
  creditCardList.innerHTML = "";
  if (state.creditCards.length === 0) {
    creditCardList.append(emptyState("Nenhum cartão cadastrado ainda."));
  } else {
    state.creditCards.forEach((card) => {
      creditCardList.append(creditCardCard(card, "active"));
    });
  }
  renderArchivedCreditCards();
  renderCardInvoice();
}

function renderArchivedCreditCards() {
  archivedCreditCardList.innerHTML = "";
  if (state.archivedCreditCards.length === 0) {
    archivedCreditCardList.append(emptyState("Nenhum cartão arquivado."));
    return;
  }
  state.archivedCreditCards.forEach((card) => {
    archivedCreditCardList.append(creditCardCard(card, "archived"));
  });
}

function renderCardInvoice() {
  renderCardInvoiceSelector();
  renderCardTransactionCategories();
  renderCardPaymentAccounts();
  cardInvoiceMonthLabel.textContent = formatMonthLabel(state.cardInvoiceMonth);
  cardTransactionForm.elements.credit_card_id.value = state.selectedCreditCardId;
  cardTransactionForm.elements.invoice_month.value = state.cardInvoiceMonth;
  cardInvoicePaymentForm.elements.credit_card_id.value = state.selectedCreditCardId;
  cardInvoicePaymentForm.elements.invoice_month.value = state.cardInvoiceMonth;
  const card = selectedCreditCard();
  if (!card) {
    cardInvoiceTotal.textContent = formatMoney(0, "BRL");
    cardInvoiceReconciledTotal.textContent = formatMoney(0, "BRL");
    cardInvoiceClosingDate.textContent = "--";
    cardInvoiceDueDate.textContent = "--";
    cardPaymentDate.value = "";
    cardTransactionForm.querySelector('button[type="submit"]').disabled = true;
    payCardInvoiceButton.disabled = true;
    updateCardInvoiceOpenCount();
    cardInvoiceList.innerHTML = "";
    cardInvoiceList.append(emptyState("Cadastre um cartão para lançar faturas."));
    return;
  }
  const total = cardInvoiceOpenAmount();
  const reconciledTotal = cardInvoiceReconciledAmount();
  const closingDate = cardInvoiceDate(state.cardInvoiceMonth, card.closing_day);
  const dueDate = cardInvoiceDate(state.cardInvoiceMonth, card.due_day);
  cardInvoiceTotal.textContent = formatMoney(total, card.currency);
  cardInvoiceReconciledTotal.textContent = formatMoney(reconciledTotal, card.currency);
  cardInvoiceClosingDate.textContent = formatDate(closingDate);
  cardInvoiceDueDate.textContent = formatDate(dueDate);
  if (!cardPaymentDate.value || !cardPaymentDate.value.startsWith(state.cardInvoiceMonth)) {
    cardPaymentDate.value = dueDate;
  }
  const alreadyPaid = state.cardInvoicePayments.length > 0;
  cardTransactionForm.querySelector('button[type="submit"]').disabled = alreadyPaid;
  payCardInvoiceButton.disabled = total <= 0 || alreadyPaid || !cardPaymentAccount.value;
  payCardInvoiceButton.textContent = alreadyPaid ? "Fatura paga" : "Pagar fatura";
  updateCardInvoiceOpenCount();
  renderCardInvoiceList(card);
}

function updateCardInvoiceOpenCount() {
  if (!cardInvoiceOpenCount) {
    return;
  }
  const pending = state.cardInvoiceTransactions.filter((transaction) => !transaction.reconciled_at).length;
  cardInvoiceOpenCount.textContent = `${pending} não conciliado${pending === 1 ? "" : "s"}`;
  cardInvoiceOpenCount.classList.toggle("danger", pending > 0);
  cardInvoiceOpenCount.classList.toggle("ok", pending === 0);
}

function renderCardInvoiceSelector() {
  const options = state.creditCards.map((card) => (
    `<option value="${card.id}">${escapeHtml(card.name)} (${escapeHtml(card.currency)})</option>`
  )).join("");
  cardInvoiceCard.innerHTML = options || '<option value="">Cadastre um cartão</option>';
  cardInvoiceCard.disabled = state.creditCards.length === 0;
  if (state.selectedCreditCardId) {
    cardInvoiceCard.value = state.selectedCreditCardId;
  }
}

function renderCardPaymentAccounts() {
  const card = selectedCreditCard();
  const previousSelection = cardPaymentAccount.value;
  const previousCardId = cardPaymentAccount.dataset.cardId || "";
  const accounts = card
    ? state.accounts.filter((account) => account.currency === card.currency)
    : [];
  cardPaymentAccount.innerHTML = accounts.map((account) => (
    `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
  )).join("") || '<option value="">Cadastre uma conta compatível</option>';
  if (card && accounts.length) {
    const preferred = card.preferred_payment_account_id ? String(card.preferred_payment_account_id) : "";
    const shouldPreserve = previousCardId === String(card.id) && accounts.some((account) => String(account.id) === previousSelection);
    if (shouldPreserve) {
      cardPaymentAccount.value = previousSelection;
    } else if (preferred && accounts.some((account) => String(account.id) === preferred)) {
      cardPaymentAccount.value = preferred;
    }
  }
  cardPaymentAccount.dataset.cardId = card ? String(card.id) : "";
  cardPaymentAccount.disabled = accounts.length === 0;
}

function renderCreditCardPreferredPaymentAccounts() {
  const selected = creditCardPreferredPaymentAccount.value;
  const currency = creditCardForm.elements.currency.value || "BRL";
  const accounts = state.accounts.filter((account) => account.currency === currency);
  creditCardPreferredPaymentAccount.innerHTML = '<option value="">Sem preferência</option>' + accounts.map((account) => (
    `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
  )).join("");
  if (accounts.some((account) => String(account.id) === String(selected))) {
    creditCardPreferredPaymentAccount.value = selected;
  }
  creditCardPreferredPaymentAccount.disabled = accounts.length === 0;
}

function renderCardTransactionCategories() {
  const groupType = cardTransactionType.value;
  const categories = state.categories.filter((category) => category.group_type === groupType);
  const selected = cardTransactionCategory.value;
  cardTransactionCategory.innerHTML = categories.map((category) => (
    `<option value="${escapeHtml(category.name)}">${escapeHtml(category.name)}</option>`
  )).join("") || '<option value="">Cadastre uma categoria para este grupo</option>';
  if (categories.some((category) => category.name === selected)) {
    cardTransactionCategory.value = selected;
  }
  cardTransactionCategory.disabled = categories.length === 0;
  cardTransactionForm.querySelector('button[type="submit"]').disabled = categories.length === 0 || !state.selectedCreditCardId;
  renderCardTransactionSubcategories();
}

function renderCardTransactionSubcategories() {
  const category = state.categories.find((entry) => (
    entry.group_type === cardTransactionType.value && entry.name === cardTransactionCategory.value
  ));
  const subcategories = category ? category.subcategories || [] : [];
  const selected = cardTransactionSubcategory.value;
  cardTransactionSubcategory.innerHTML = '<option value="">Sem subcategoria</option>' + subcategories.map((subcategory) => (
    `<option value="${escapeHtml(subcategory.name)}">${escapeHtml(subcategory.name)}</option>`
  )).join("");
  if (subcategories.some((subcategory) => subcategory.name === selected)) {
    cardTransactionSubcategory.value = selected;
  }
  cardTransactionSubcategory.disabled = subcategories.length === 0;
}

function renderCardInvoiceList(card) {
  cardInvoiceList.innerHTML = "";
  if (state.cardInvoicePayments.length) {
    const payment = state.cardInvoicePayments[0];
    const paid = document.createElement("article");
    paid.className = "card-invoice-payment";
    paid.innerHTML = `
      <div>
        <strong>Fatura paga</strong>
        <div class="account-meta">
          <span>${formatDate(payment.payment_date)}</span>
          <span>${escapeHtml(payment.account_name)}</span>
        </div>
      </div>
      <strong>${formatMoney(payment.amount, card.currency)}</strong>
    `;
    cardInvoiceList.append(paid);
  }
  if (state.cardInvoiceTransactions.length === 0) {
    cardInvoiceList.append(emptyState("Nenhum lançamento nesta fatura."));
    return;
  }
  state.cardInvoiceTransactions.forEach((transaction) => {
    const item = document.createElement("article");
    item.className = `card-invoice-row ${transaction.type === "income" ? "positive" : "negative"}`;
    const sign = transaction.type === "income" ? "+" : "-";
    const isReconciled = Boolean(transaction.reconciled_at);
    item.innerHTML = `
      <div class="invoice-entry-main">
        <strong>${escapeHtml(transaction.description)}</strong>
        <div class="account-meta invoice-entry-meta">
          <span>${formatDate(transaction.date)}</span>
          <span>${cardTransactionTypeLabel(transaction.type)}</span>
          ${transactionSeriesLabel(transaction) ? `<span>${transactionSeriesLabel(transaction)}</span>` : ""}
        </div>
      </div>
      <div class="invoice-entry-category">
        ${transaction.category_name ? escapeHtml(cardCategoryPath(transaction)) : "Sem categoria"}
      </div>
      <div class="transaction-amount invoice-entry-amount">
        <strong>${sign}${formatMoney(transaction.amount, card.currency)}</strong>
      </div>
      ${state.cardInvoicePayments.length ? "" : `
        <div class="transaction-actions invoice-entry-actions">
          ${launchActionButton("arrow-left", "Mover para a fatura anterior", `data-card-move-id="${transaction.id}" data-card-move-direction="previous"`)}
          ${launchActionButton("arrow-right", "Mover para a próxima fatura", `data-card-move-id="${transaction.id}" data-card-move-direction="next"`)}
          ${launchActionButton("edit", "Editar lançamento", `data-card-edit-id="${transaction.id}"`)}
          ${launchActionButton("check", isReconciled ? "Desmarcar conciliação" : "Marcar como conciliado", `data-card-reconcile-id="${transaction.id}" data-reconciled="${isReconciled}"`, `reconcile-button ${isReconciled ? "active" : ""}`)}
          ${launchActionButton("trash", "Excluir lançamento", `data-card-transaction-id="${transaction.id}"`, "danger-action")}
        </div>
      `}
    `;
    cardInvoiceList.append(item);
  });
}

function handleCardInvoiceListClick(event) {
  const moveButton = event.target.closest("[data-card-move-id]");
  if (moveButton) {
    moveCardTransactionInvoice(moveButton.dataset.cardMoveId, moveButton.dataset.cardMoveDirection);
    return;
  }
  const editButton = event.target.closest("[data-card-edit-id]");
  if (editButton) {
    const transaction = state.cardInvoiceTransactions.find((entry) => String(entry.id) === String(editButton.dataset.cardEditId));
    if (transaction) {
      editCardTransaction(transaction);
    }
    return;
  }
  const reconcileButton = event.target.closest("[data-card-reconcile-id]");
  if (reconcileButton) {
    toggleCardTransactionReconciliation(
      reconcileButton.dataset.cardReconcileId,
      reconcileButton.dataset.reconciled !== "true",
    );
    return;
  }
  const deleteButton = event.target.closest("[data-card-transaction-id]");
  if (deleteButton) {
    deleteCardTransaction(deleteButton.dataset.cardTransactionId);
  }
}

function selectedCreditCard() {
  return state.creditCards.find((card) => String(card.id) === String(state.selectedCreditCardId));
}

function cardInvoiceOpenAmount() {
  const transactionTotal = state.cardInvoiceTransactions.reduce((total, transaction) => {
    const amount = Number(transaction.amount);
    return total + (transaction.type === "expense" ? amount : -amount);
  }, 0);
  const paidTotal = state.cardInvoicePayments.reduce((total, payment) => total + Number(payment.amount), 0);
  return transactionTotal - paidTotal;
}

function cardInvoiceReconciledAmount() {
  return state.cardInvoiceTransactions.reduce((total, transaction) => {
    if (!transaction.reconciled_at) {
      return total;
    }
    const amount = Number(transaction.amount);
    return total + (transaction.type === "expense" ? amount : -amount);
  }, 0);
}

function cardInvoiceDate(month, day) {
  const [year, monthNumber] = month.split("-").map(Number);
  const lastDay = new Date(year, monthNumber, 0).getDate();
  const normalizedDay = Math.min(Number(day), lastDay);
  return `${year}-${String(monthNumber).padStart(2, "0")}-${String(normalizedDay).padStart(2, "0")}`;
}

function creditCardCard(card, status) {
  const item = document.createElement("article");
  item.className = "credit-card-item";
  const actions = status === "archived"
    ? `<button class="ghost" type="button" data-action="restore">Reativar</button>`
    : `
      <button class="ghost" type="button" data-action="edit">Editar</button>
      <button class="danger" type="button" data-action="archive">Arquivar</button>
    `;
  item.innerHTML = `
    <div>
      <h3>${escapeHtml(card.name)}</h3>
      <div class="account-meta">
        <span>${escapeHtml(card.issuer)}</span>
        ${card.network ? `<span>${escapeHtml(card.network)}</span>` : ""}
        <span>${escapeHtml(card.currency)}</span>
        <span>Fecha dia ${card.closing_day}</span>
        <span>Vence dia ${card.due_day}</span>
      </div>
    </div>
    <div class="balance">
      <span>Limite</span>
      <strong>${formatMoney(card.limit, card.currency)}</strong>
      <div class="card-actions">
        ${actions}
      </div>
    </div>
  `;
  const editButton = item.querySelector('[data-action="edit"]');
  const archiveButton = item.querySelector('[data-action="archive"]');
  const restoreButton = item.querySelector('[data-action="restore"]');
  if (editButton) {
    editButton.addEventListener("click", () => editCreditCard(card));
  }
  if (archiveButton) {
    archiveButton.addEventListener("click", () => archiveCreditCard(card.id));
  }
  if (restoreButton) {
    restoreButton.addEventListener("click", () => restoreCreditCard(card.id));
  }
  return item;
}

function accountCard(account, status) {
  const card = document.createElement("article");
  card.className = "account-card";
  const actions = status === "archived"
    ? `<button class="ghost" type="button" data-action="restore">Reativar</button>`
    : `
      <button class="ghost" type="button" data-action="edit">Editar</button>
      <button class="danger" type="button" data-action="archive">Arquivar</button>
    `;

  const logoHtml = getBankLogo(account.bank_name, account.account_type);

  card.innerHTML = `
      <div class="account-card-info">
        ${logoHtml}
        <div>
          <h3>${escapeHtml(account.name)}</h3>
          <div class="account-meta">
            ${account.account_type !== "wallet" ? `<span>${escapeHtml(account.bank_name)}</span>` : ""}
            <span>${accountTypeLabel(account.account_type)}</span>
            <span>${escapeHtml(account.currency)}</span>
            ${account.branch ? `<span>Ag. ${escapeHtml(account.branch)}</span>` : ""}
            ${account.account_number ? `<span>Conta ${escapeHtml(account.account_number)}</span>` : ""}
          </div>
        </div>
      </div>
      <div class="balance">
        <strong>${formatMoney(account.current_balance, account.currency)}</strong>
        <div class="card-actions">
          ${actions}
        </div>
      </div>
    `;
  const editButton = card.querySelector('[data-action="edit"]');
  const archiveButton = card.querySelector('[data-action="archive"]');
  const restoreButton = card.querySelector('[data-action="restore"]');
  if (editButton) {
    card.querySelector('[data-action="edit"]').addEventListener("click", () => editAccount(account));
  }
  if (archiveButton) {
    card.querySelector('[data-action="archive"]').addEventListener("click", () => archiveAccount(account.id));
  }
  if (restoreButton) {
    restoreButton.addEventListener("click", () => restoreAccount(account.id));
  }
  return card;
}

function getBankLogo(bankName, accountType) {
  if (accountType === "wallet") {
    return `<div class="bank-logo-badge" style="background-color: #e2e8f0;" title="Carteira / Dinheiro">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
        <path d="M16 11h6v2h-6z"></path>
        <path d="M12 4v16"></path>
      </svg>
    </div>`;
  }

  const name = String(bankName || "").toLowerCase().trim();
  const logoAsset = bankLogoAsset(name);
  if (logoAsset) {
    return `<div class="bank-logo-badge image-logo" title="${escapeHtml(logoAsset.title)}">
      <img src="${logoAsset.src}" alt="${escapeHtml(logoAsset.title)}">
    </div>`;
  }

  // Nubank
  if (name.includes("nubank") || name.includes("nu ")) {
    return `<div class="bank-logo-badge" style="background-color: #820ad1;" title="Nubank">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">
        <path d="M25 75V25c0 0 10-10 20 0s10 20 10 30c0 10 0 20 20 20s20-20 20-30" />
      </svg>
    </div>`;
  }
  // Itaú
  if (name.includes("itau") || name.includes("itaú")) {
    return `<div class="bank-logo-badge" style="background-color: #ec7000;" title="Itaú">
      <svg viewBox="0 0 100 100" width="30" height="30">
        <rect x="10" y="10" width="80" height="80" rx="15" fill="#002d62" />
        <path d="M25 35h50v6h-22v24h22v6h-50v-6h22V41h-22z" fill="#ec7000" />
        <path d="M30 40h40v4H50v16h20v4H30v-4h16V44H30z" fill="#ffec00" />
      </svg>
    </div>`;
  }
  // Bradesco
  if (name.includes("bradesco")) {
    return `<div class="bank-logo-badge" style="background-color: #cc092f;" title="Bradesco">
      <svg viewBox="0 0 100 100" width="22" height="22" fill="#ffffff">
        <path d="M50 15c-12 0-22 10-22 22 0 6 2 11 6 15L50 68l16-16c4-4 6-9 6-15 0-12-10-22-22-22zm0 8c8 0 14 6 14 14 0 4-2 8-5 10L50 58l-9-11c-3-2-5-6-5-10 0-8 6-14 14-14z" />
        <rect x="25" y="75" width="50" height="8" rx="2" />
        <rect x="35" y="85" width="30" height="5" rx="1" />
      </svg>
    </div>`;
  }
  // Banco do Brasil
  if (name.includes("banco do brasil") || name.includes(" bb ") || name === "bb") {
    return `<div class="bank-logo-badge" style="background-color: #0038a8;" title="Banco do Brasil">
      <svg viewBox="0 0 100 100" width="26" height="26" fill="#fcf800">
        <path d="M20 30c5-10 15-15 30-15s25 5 30 15l-12 6c-3-6-10-10-18-10s-15 4-18 10l-12-6z" />
        <path d="M20 70c5 10 15 15 30 15s25-5 30-15l-12-6c-3 6-10 10-18 10s-15-4-18-10l-12 6z" />
        <path d="M50 35c8 0 15 7 15 15s-7 15-15 15-15-7-15-15 7-15 15-15z" />
      </svg>
    </div>`;
  }
  // Caixa
  if (name.includes("caixa") || name.includes("cef")) {
    return `<div class="bank-logo-badge" style="background-color: #005c9e;" title="Caixa">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="#ffffff">
        <rect x="15" y="15" width="70" height="70" rx="10" />
        <path d="M30 30l15 15-15 15h12l9-9 9 9h12L57 45l15-15H60l-9 9-9-9H30z" fill="#f37021" />
        <circle cx="50" cy="50" r="10" fill="#ffffff" />
      </svg>
    </div>`;
  }
  // Santander
  if (name.includes("santander")) {
    return `<div class="bank-logo-badge" style="background-color: #ec0000;" title="Santander">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="#ffffff">
        <path d="M50 15c-15 0-25 15-20 28 3 7 10 12 17 12h6c7 0 14-5 17-12 5-13-5-28-20-28zm-3 8c1 0 2 1 2 2v6h-4v-6c0-1 1-2 2-2zm6 0c1 0 2 1 2 2v6h-4v-6c0-1 1-2 2-2zM32 50h36v32H32z" />
      </svg>
    </div>`;
  }
  // Inter
  if (name.includes("inter")) {
    return `<div class="bank-logo-badge" style="background-color: #ff7a00;" title="Banco Inter">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round">
        <path d="M30 25h40v50H30z" />
        <path d="M50 25v50" />
      </svg>
    </div>`;
  }
  // C6 Bank
  if (name.includes("c6")) {
    return `<div class="bank-logo-badge" style="background-color: #111111;" title="C6 Bank">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="#ffffff">
        <text x="50" y="65" font-size="45" font-family="Arial, sans-serif" font-weight="900" text-anchor="middle">C6</text>
      </svg>
    </div>`;
  }
  // XP
  if (name.includes("xp")) {
    return `<div class="bank-logo-badge" style="background-color: #000000;" title="XP Investimentos">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="#d5b265">
        <path d="M20 20l25 30-25 30h15l17-21 17 21h15L60 50l25-30H70L53 40 35 20H20z" />
      </svg>
    </div>`;
  }
  // BTG
  if (name.includes("btg")) {
    return `<div class="bank-logo-badge" style="background-color: #0f172a;" title="BTG Pactual">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="#d5b265">
        <text x="50" y="65" font-size="32" font-family="Arial, sans-serif" font-weight="bold" text-anchor="middle">BTG</text>
      </svg>
    </div>`;
  }
  // Sofisa
  if (name.includes("sofisa")) {
    return `<div class="bank-logo-badge" style="background-color: #003b71;" title="Banco Sofisa">
      <svg viewBox="0 0 100 100" width="26" height="26">
        <circle cx="50" cy="50" r="34" fill="#ffffff" opacity="0.16" />
        <path d="M25 61c8 8 20 12 32 8 10-3 17-11 18-21-7 6-15 8-24 5-8-2-13-6-20-5-5 1-9 5-6 13z" fill="#ffffff" />
        <path d="M25 39c8-8 20-12 32-8 10 3 17 11 18 21-7-6-15-8-24-5-8 2-13 6-20 5-5-1-9-5-6-13z" fill="#6bb6ff" />
      </svg>
    </div>`;
  }
  // Avenue
  if (name.includes("avenue")) {
    return `<div class="bank-logo-badge" style="background-color: #0c0c0e;" title="Avenue">
      <svg viewBox="0 0 100 100" width="22" height="22" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round">
        <path d="M25 80L50 20L75 80" />
        <path d="M38 55h24" />
      </svg>
    </div>`;
  }
  // Wise
  if (name.includes("wise")) {
    return `<div class="bank-logo-badge" style="background-color: #9fe870;" title="Wise">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="#1e3b2b">
        <path d="M20 30h40L40 50h30L45 80h10L75 42H50l20-12H20v8z" />
      </svg>
    </div>`;
  }
  // Coinbase
  if (name.includes("coinbase")) {
    return `<div class="bank-logo-badge" style="background-color: #0052ff;" title="Coinbase">
      <svg viewBox="0 0 100 100" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="12">
        <circle cx="50" cy="50" r="30" />
        <circle cx="50" cy="50" r="10" fill="#ffffff" />
      </svg>
    </div>`;
  }
  // Generic Crypto
  if (name.includes("cripto") || name.includes("crypto") || name.includes("binance") || name.includes("ledger") || name.includes("metamask") || name.includes("trezor") || name.includes("blockchain")) {
    return `<div class="bank-logo-badge" style="background-color: #f59e0b;" title="Criptoativos / Wallet">
      <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="9"></circle>
        <path d="M12 7v10M9 9h5a2 2 0 0 1 0 4H9h4a2 2 0 0 1 0 4H9"></path>
      </svg>
    </div>`;
  }

  // Generic Bank
  return `<div class="bank-logo-badge" style="background-color: #f1f5f9;" title="Banco / Outro">
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="#475569" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="10" width="20" height="11" rx="2"></rect>
      <path d="M6 6v4M10 6v4M14 6v4M18 6v4M2 6h20M12 2L2 6h20L12 2z"></path>
    </svg>
  </div>`;
}

function bankLogoAsset(name) {
  const assets = [
    { match: ["itau", "itaú"], title: "Itaú", src: "/assets/banks/itau.png" },
    { match: ["nubank", "nu "], title: "Nubank", src: "/assets/banks/nubank.ico" },
    { match: ["bradesco"], title: "Bradesco", src: "/assets/banks/bradesco.ico" },
    { match: ["banco do brasil", " bb "], exact: ["bb"], title: "Banco do Brasil", src: "/assets/banks/bb.ico" },
    { match: ["inter"], title: "Banco Inter", src: "/assets/banks/inter.ico" },
    { match: ["avenue"], title: "Avenue", src: "/assets/banks/avenue.jpeg" },
    { match: ["wise"], title: "Wise", src: "/assets/banks/wise.png" },
    { match: ["coinbase"], title: "Coinbase", src: "/assets/banks/coinbase.ico" },
    { match: ["sofisa"], title: "Banco Sofisa", src: "/assets/banks/sofisa.ico" },
  ];
  return assets.find((asset) => (
    (asset.exact || []).includes(name)
    || asset.match.some((term) => name.includes(term))
  ));
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

function renderImportTargets() {
  const isCard = importTarget.value === "card";
  importAccountLabel.hidden = isCard;
  importCardLabel.hidden = !isCard;
  importAccount.disabled = isCard;
  importCreditCard.disabled = !isCard;
  importAccount.name = isCard ? "" : "target_id";
  importCreditCard.name = isCard ? "target_id" : "";
  importAccount.innerHTML = state.accounts.map((account) => (
    `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
  )).join("") || '<option value="">Cadastre uma conta</option>';
  importCreditCard.innerHTML = state.creditCards.map((card) => (
    `<option value="${card.id}">${escapeHtml(card.name)} (${escapeHtml(card.currency)})</option>`
  )).join("") || '<option value="">Cadastre um cartão</option>';
  importForm.querySelector('button[type="submit"]').disabled = isCard ? state.creditCards.length === 0 : state.accounts.length === 0;
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
  
  // Calculate balances considering only the filtered transactions
  // Saldo Atual: apenas lançamentos conciliados até hoje
  currentBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(todayLocalDateValue(), accountTransactions, true));
  // Saldo Previsto: todos os lançamentos até o fim do mês
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
  renderPortfolioGroupList(portfolioTypeList, summary.by_type);
  renderPortfolioGroupList(portfolioIndexerList, summary.by_indexer);
  renderPortfolioGroupList(portfolioCurrencyList, summary.by_currency);
  renderPortfolioGroupList(portfolioAccountList, summary.by_account);
  renderPortfolioPositions(portfolio.positions || []);
  renderPortfolioHistory(portfolio.history || []);
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
  const totalsByCurrency = portfolioTotalsByCurrency(rows);
  container.innerHTML = rows.map((row, index) => {
    const current = Number(row.current_brl);
    const result = Number(row.result_brl);
    const currency = row.currency || "BRL";
    const total = totalsByCurrency.get(currency) || 0;
    const percent = total > 0 ? current / total : 0;
    return `
      <article class="portfolio-group-row">
        <div>
          <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
          <span>${row.count} posição(ões)</span>
        </div>
        <div>
          <strong>${formatMoney(row.current_brl, currency)}</strong>
          <span class="${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(row.result_brl, currency)} · ${Number(row.result_percent).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</span>
        </div>
        <div class="report-bar"><span style="width:${Math.max(percent * 100, 2)}%; background:${chartColor(index)}"></span></div>
      </article>
    `;
  }).join("");
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
  portfolioPositions.innerHTML = grouped.map((group) => {
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
  }).join("");
  portfolioPositions.querySelectorAll("[data-toggle-portfolio-section]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.togglePortfolioSection;
      if (state.portfolioCollapsedGroups.has(key)) {
        state.portfolioCollapsedGroups.delete(key);
      } else {
        state.portfolioCollapsedGroups.add(key);
      }
      renderPortfolioPositions(positions);
    });
  });
  portfolioPositions.querySelectorAll("[data-toggle-portfolio-group]").forEach((button) => {
    button.addEventListener("click", () => {
      const key = button.dataset.togglePortfolioGroup;
      if (state.portfolioExpandedGroups.has(key)) {
        state.portfolioExpandedGroups.delete(key);
      } else {
        state.portfolioExpandedGroups.add(key);
      }
      renderPortfolioPositions(positions);
    });
  });
  portfolioPositions.querySelectorAll("[data-edit-portfolio-position-id]").forEach((button) => {
    const position = findPortfolioOpeningPosition(positions, button.dataset.editPortfolioPositionId);
    button.addEventListener("click", () => editPortfolioPosition(position));
  });
  portfolioPositions.querySelectorAll("[data-edit-portfolio-transaction-id]").forEach((button) => {
    button.addEventListener("click", () => editPortfolioSourceTransaction(button.dataset.editPortfolioTransactionId));
  });
  portfolioPositions.querySelectorAll("[data-edit-portfolio-value-payload]").forEach((button) => {
    button.addEventListener("click", () => editPortfolioCurrentValue(JSON.parse(button.dataset.editPortfolioValuePayload)));
  });
  portfolioPositions.querySelectorAll("[data-redeem-portfolio-payload]").forEach((button) => {
    button.addEventListener("click", () => redeemPortfolioPosition(JSON.parse(button.dataset.redeemPortfolioPayload)));
  });
  portfolioPositions.querySelectorAll("[data-close-portfolio-payload]").forEach((button) => {
    button.addEventListener("click", () => closePortfolioPosition(JSON.parse(button.dataset.closePortfolioPayload)));
  });
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
  const currentValue = group.positions.reduce((total, position) => total + Number(position.current_value_brl || 0), 0);
  const totalCost = group.positions.reduce((total, position) => total + Number(position.total_cost_brl || 0), 0);
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
  const result = Number(position.current_value_brl || 0) - Number(position.total_cost_brl || 0);
  const resultPercent = Number(position.total_cost_brl) > 0 ? result / Number(position.total_cost_brl) : 0;
  const dayResult = Number(position.day_result_brl || 0);
  const dayBase = Number(position.current_value_brl || 0) - dayResult;
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
    portfolioFixedIncomeDetail(position),
    position.fixed_income_maturity_date ? `Venc. ${formatDate(position.fixed_income_maturity_date)}` : "",
  ].filter(Boolean).join(" · ");
  const toggle = options.parent
    ? `<button class="portfolio-toggle" type="button" data-toggle-portfolio-group="${escapeHtml(options.groupKey)}" aria-label="${options.expanded ? "Recolher" : "Abrir"} ${escapeHtml(identifier)}">${options.expanded ? "-" : "+"}</button>`
    : options.child ? '<span class="portfolio-child-marker"></span>' : "";
  const fixedIncomeIof = Number(position.fixed_income_iof_tax || 0);
  const fixedIncomeTax = Number(position.fixed_income_income_tax || 0);
  const hasFixedIncomeTax = position.asset_type === "fixed_income" && (fixedIncomeIof > 0 || fixedIncomeTax > 0);
  const valueDetail = hasFixedIncomeTax
    ? `<span title="${escapeHtml([
      `Bruto ${formatMoney(position.fixed_income_gross_value || position.current_value, position.currency)}`,
      fixedIncomeIof > 0 ? `IOF estimado -${formatMoney(position.fixed_income_iof_tax, position.currency)}` : "",
      `IR estimado -${formatMoney(position.fixed_income_income_tax, position.currency)}`,
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
  return `
    <tr class="${options.parent ? "portfolio-parent-row" : ""} ${options.child ? "portfolio-child-row" : ""} ${maturityAlert ? `portfolio-maturity-row ${maturityAlert.status}` : ""}">
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
      <td class="money-cell ${dayResult < 0 ? "danger-text" : "positive-text"}">${formatMoney(position.day_result_brl, position.currency)}<span>${formatPercent(dayPercent)}</span></td>
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
  const rawDate = window.prompt("Data de encerramento", todayLocalDateValue());
  if (rawDate === null) {
    return;
  }
  const rawValue = window.prompt("Valor final reconhecido pelo banco", moneyInputValue(position.current_value));
  if (rawValue === null) {
    return;
  }
  if (!window.confirm("Encerrar esta posição? Ela deixará a posição atual e será movida para Histórico.")) {
    return;
  }
  setMessage(portfolioMessage, "Encerrando posição...");
  try {
    const response = await api("/api/portfolio/close", {
      method: "POST",
      body: {
        ...position,
        date: rawDate,
        closing_value: rawValue,
      },
    });
    state.portfolio = response;
    state.portfolioDirty = false;
    renderPortfolio();
    renderCockpitPortfolioByType();
    setMessage(portfolioMessage, "Posição encerrada e movida para o histórico.", "success");
  } catch (error) {
    setMessage(portfolioMessage, error.message, "error");
  }
}

async function editPortfolioCurrentValue(position) {
  const rawAmount = window.prompt("Valor atual da posição", moneyInputValue(position.current_value));
  if (rawAmount === null) {
    return;
  }
  const rawDate = window.prompt("Data da atualização", todayLocalDateValue());
  if (rawDate === null) {
    return;
  }
  setMessage(portfolioMessage, "Atualizando valor atual...");
  try {
    const response = await api("/api/portfolio/value", {
      method: "PUT",
      body: {
        ...position,
        current_value: rawAmount,
        quote_date: rawDate,
      },
    });
    state.portfolio = response;
    state.portfolioDirty = false;
    renderPortfolio();
    renderCockpitPortfolioByType();
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
  
  // Add subtotal lines at the end: Current Balance (Reconciled) and Forecast Balance
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
      if (option.value === "investment" || option.value === "exchange") {
        option.disabled = true;
      } else {
        option.disabled = false;
      }
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
  return normalizeSearch([transactionCategory.value, transactionSubcategory.value, investmentAssetIdentifier.value].join(" ")).includes("poupanca");
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

async function shiftCardInvoiceMonth(delta) {
  await setCardInvoiceMonth(shiftMonth(state.cardInvoiceMonth, delta));
}

async function setCardInvoiceMonth(month) {
  if (!isValidMonthValue(month)) {
    return;
  }
  state.cardInvoiceMonth = month;
  resetCardTransactionForm();
  setMessage(cardInvoiceMessage, "");
  await loadCardInvoice();
  renderCreditCards();
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
  const currentMonth = currentMonthValue();
  const transactionTotal = state.cardTransactions.reduce((total, transaction) => {
    if (String(transaction.credit_card_id) !== String(cardId) || !transaction.reconciled_at || transaction.invoice_month > currentMonth) {
      return total;
    }
    const amount = Number(transaction.amount);
    return total + (transaction.type === "expense" ? amount : -amount);
  }, 0);
  const paidTotal = state.cardPayments.reduce((total, payment) => (
    String(payment.credit_card_id) === String(cardId) && payment.invoice_month <= currentMonth ? total + Number(payment.amount) : total
  ), 0);
  return transactionTotal - paidTotal;
}

function cardOpenBalance(cardId, untilInvoiceMonth = null) {
  const transactionTotal = state.cardTransactions.reduce((total, transaction) => {
    if (String(transaction.credit_card_id) !== String(cardId)) {
      return total;
    }
    if (untilInvoiceMonth && transaction.invoice_month > untilInvoiceMonth) {
      return total;
    }
    const amount = Number(transaction.amount);
    return total + (transaction.type === "expense" ? amount : -amount);
  }, 0);
  const paidTotal = state.cardPayments.reduce((total, payment) => (
    String(payment.credit_card_id) === String(cardId) && (!untilInvoiceMonth || payment.invoice_month <= untilInvoiceMonth) ? total + Number(payment.amount) : total
  ), 0);
  return transactionTotal - paidTotal;
}

function creditCardCurrency(cardId) {
  const card = state.creditCards.find((entry) => String(entry.id) === String(cardId));
  return card ? card.currency : "BRL";
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

function getCurrentMonthTotals() {
  const now = new Date();
  const prefix = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  return state.transactions.reduce((totals, transaction) => {
    if (!transaction.date.startsWith(prefix)) {
      return totals;
    }
    const amountBrl = Number(transaction.amount_brl || transaction.amount);
    if (transaction.type === "income") {
      totals.income += amountBrl;
    }
    if (transaction.type === "expense") {
      totals.expense += amountBrl;
    }
    if (isInvestmentTransaction(transaction)) {
      totals.investment += amountBrl;
    }
    return totals;
  }, { income: 0, expense: 0, investment: 0, get savingsRate() {
    return this.income > 0 ? this.investment / this.income : 0;
  } });
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

function renderCurrencyTotals(totals) {
  currencyList.innerHTML = "";
  if (totals.size === 0) {
    currencyList.append(emptyState("Nenhuma moeda cadastrada ainda.", true));
    return;
  }
  for (const [currency, amounts] of totals.entries()) {
    const section = document.createElement("section");
    section.className = "currency-section";
    const accountRows = amounts.accounts.map((account) => currencyTableRow(
      account.name,
      account.type,
      account.amount,
      account.reconciled,
      currency,
      "account",
    )).join("");
    const cardRows = amounts.cards.map((card) => currencyTableRow(
      card.name,
      card.issuer || "Cartão",
      card.amount,
      card.reconciled,
      currency,
      "card",
    )).join("");
    section.innerHTML = `
      <div class="currency-section-header">
        <div>
          <span>${escapeHtml(currency)}</span>
          <em>Previsto</em>
        </div>
        <strong>${formatMoney(amounts.current, currency)}</strong>
      </div>
      <div class="currency-table" role="table" aria-label="Saldos em ${escapeHtml(currency)}">
        <div class="currency-table-head" role="row">
          <span>Conta</span>
          <span>Tipo</span>
          <span>Saldo</span>
          <span>Conciliado</span>
        </div>
        ${accountRows || '<div class="currency-empty-row">Nenhuma conta ativa nesta moeda.</div>'}
        ${cardRows ? `<div class="currency-subgroup">Cartões de crédito</div>${cardRows}` : ""}
      </div>
    `;
    currencyList.append(section);
  }
}

function currencyTableRow(name, detail, amount, reconciled, currency, kind = "account") {
  const amountClass = amount < 0 ? "danger-text" : amount > 0 ? "positive-text" : "";
  const reconciledClass = reconciled < 0 ? "danger-text" : reconciled > 0 ? "positive-text" : "";
  return `
    <div class="currency-table-row ${kind}" role="row">
      <span><b>${escapeHtml(name)}</b></span>
      <span>${escapeHtml(detail)}</span>
      <strong class="${amountClass}">${formatMoney(amount, currency)}</strong>
      <strong class="${reconciledClass}">${formatMoney(reconciled || 0, currency)}</strong>
    </div>
  `;
}

function renderCockpitPortfolioByType() {
  if (!cockpitPortfolioByType) {
    return;
  }
  if (!state.portfolio && state.portfolioDirty) {
    cockpitPortfolioByType.innerHTML = '<div class="empty-state compact">Atualizando portfólio...</div>';
    loadPortfolio();
    return;
  }
  if (state.portfolioLoading) {
    cockpitPortfolioByType.innerHTML = '<div class="empty-state compact">Atualizando portfólio...</div>';
    return;
  }
  if (state.portfolioError) {
    cockpitPortfolioByType.innerHTML = `<div class="empty-state compact">${escapeHtml(state.portfolioError)}</div>`;
    return;
  }
  if (state.portfolio && state.portfolioDirty && !state.portfolioLoading) {
    loadPortfolio();
  }
  const rows = state.portfolio && state.portfolio.summary ? state.portfolio.summary.by_type || [] : [];
  if (rows.length === 0) {
    cockpitPortfolioByType.innerHTML = '<div class="empty-state compact">Nenhum investimento em carteira.</div>';
    return;
  }
  const totalsByCurrency = portfolioTotalsByCurrency(rows);
  cockpitPortfolioByType.innerHTML = rows.map((row, index) => {
    const current = Number(row.current_brl || 0);
    const result = Number(row.result_brl || 0);
    const currency = row.currency || "BRL";
    const total = totalsByCurrency.get(currency) || 0;
    const percent = total > 0 ? current / total : 0;
    return `
      <article class="portfolio-cockpit-row">
        <div>
          <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
          <span>${row.count} posição(ões) · ${formatPercent(percent)}</span>
        </div>
        <div>
          <strong>${formatMoney(current, currency)}</strong>
          <span class="${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(result, currency)}</span>
        </div>
      </article>
    `;
  }).join("");
}

function showAuth() {
  authView.hidden = false;
  dashboardView.hidden = true;
  authViewController.switchAuthMode("login");
}

function renderImportResult(result) {
  const errors = result.errors || [];
  importResult.innerHTML = `
    <div class="import-summary">
      <div><span>Total lido</span><strong>${result.total_rows}</strong></div>
      <div><span>Importados</span><strong>${result.imported}</strong></div>
      <div><span>Ignorados</span><strong>${result.skipped}</strong></div>
    </div>
    ${errors.length ? `
      <div class="import-errors">
        ${errors.map((error) => `
          <article>
            <strong>Linha ${error.row}</strong>
            <span>${escapeHtml(error.description || "Sem descrição")}</span>
            <p>${escapeHtml(error.reason)}</p>
          </article>
        `).join("")}
      </div>
    ` : '<div class="empty-state compact">Nenhuma linha ignorada.</div>'}
  `;
}
