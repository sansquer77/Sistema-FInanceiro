import { api, configureApi, fetchAllListed, upload } from "./modules/api.js";
import {
  currentMonthValue,
  formatDate,
  formatMonthLabel,
  formatMonthShortLabel,
  formatShortMonthName,
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
  formatPercentValue,
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
import { createDecisionModal } from "./modules/decision-modal.js";
import {
  applyPrivacyMode,
  isTypingTarget,
  observePrivacyMoneyValues,
  togglePrivacyMode,
  updatePrivacyToggleButton,
} from "./modules/privacy-utils.js";
import { applyTheme, setTheme, storedTheme } from "./modules/theme-utils.js";
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
import { registerSimulationsView } from "./modules/simulations-view.js";
import { registerOperationHistoryView } from "./modules/operation-history-view.js";
import { registerInstructionsView } from "./modules/instructions-view.js";

applyTheme();
applyPrivacyMode();

const decisionModal = createDecisionModal();

configureApi({
  onUnauthorized: handleSessionExpired,
});

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
  cardInvoiceSearch: "",
  cardInvoiceStatusFilter: "all",
  transactionSearch: "",
  transactionStatusFilter: "all",
  transactionHighlightId: "",
  transactions: [],
  accountTransactions: [],
  cockpit: null,
  cockpitLoadedMonth: "",
  cockpitTab: "summary",
  cockpitMonth: currentMonthValue(),
  categories: [],
  tags: [],
  spendingLimits: [],
  currentSpendingLimits: [],
  appInfo: null,
  latestVersion: null,
  portfolio: null,
  portfolioReturns: null,
  portfolioDirty: true,
  portfolioLoading: false,
  portfolioError: "",
  portfolioGroup: "account_name",
  portfolioExpandedGroups: new Set(),
  portfolioCollapsedGroups: new Set(),
  portfolioAssetSaving: false,
  portfolioHighlightId: "",
  portfolioTab: "position",
  view: "cockpit",
  cockpitRefreshRequestId: 0,
  transactionMonth: currentMonthValue(),
  limitMonth: currentMonthValue(),
  cardInvoiceMonth: currentMonthValue(),
  reportMonth: currentMonthValue(),
  reportTab: "categories",
  reportAccountId: "",
  statementScope: "consolidated",
  statementCurrency: "all",
  statementAccountIds: [],
  statementCardIds: [],
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
const cardClassificationSuggestion = document.querySelector("#cardClassificationSuggestion");
const cardTransactionTagOptions = document.querySelector("#cardTransactionTagOptions");
const cardSeriesKind = document.querySelector("#cardSeriesKind");
const cardInstallmentCount = document.querySelector("#cardInstallmentCount");
const cardInstallmentCountLabel = document.querySelector("#cardInstallmentCountLabel");
const cardRecurrenceFields = document.querySelector("#cardRecurrenceFields");
const cardRecurrenceFrequency = document.querySelector("#cardRecurrenceFrequency");
const cardRecurrenceAverageFields = document.querySelector("#cardRecurrenceAverageFields");
const cardUseAverage = document.querySelector("#cardUseAverage");
const cardInvoiceList = document.querySelector("#cardInvoiceList");
const cardInvoiceSearch = document.querySelector("#cardInvoiceSearch");
const cardInvoiceStatusFilterButtons = document.querySelectorAll("[data-card-invoice-status-filter]");
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
const statementControls = document.querySelector("#statementControls");
const statementScopeSelect = document.querySelector("#statementScopeSelect");
const statementCurrencySelect = document.querySelector("#statementCurrencySelect");
const statementAccountSelect = document.querySelector("#statementAccountSelect");
const statementCardSelect = document.querySelector("#statementCardSelect");
const printStatementButton = document.querySelector("#printStatementButton");
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
const portfolioPricingFields = document.querySelector("#portfolioPricingFields");
const portfolioFixedIncomeSubtype = document.querySelector("#portfolioFixedIncomeSubtype");
const portfolioFixedIncomeMode = document.querySelector("#portfolioFixedIncomeMode");
const portfolioFixedIncomeIndexer = document.querySelector("select[name='fixed_income_indexer']");
const portfolioFixedIncomeRateLabel = document.querySelector("#portfolioFixedIncomeRateLabel");
const portfolioFixedIncomeRate = document.querySelector("#portfolioFixedIncomeRate");
const portfolioFixedIncomePreview = document.querySelector("#portfolioFixedIncomePreview");
const cancelPortfolioAssetButton = document.querySelector("#cancelPortfolioAssetButton");
const deletePortfolioAssetButton = document.querySelector("#deletePortfolioAssetButton");
const portfolioCostSummary = document.querySelector("#portfolioCostSummary");
const portfolioCurrentSummary = document.querySelector("#portfolioCurrentSummary");
const portfolioResultSummary = document.querySelector("#portfolioResultSummary");
const portfolioReturnSummary = document.querySelector("#portfolioReturnSummary");
const portfolioDayResultSummary = document.querySelector("#portfolioDayResultSummary");
const portfolioReturnChartBtn = document.querySelector("#portfolioReturnChartBtn");
const portfolioReturnDrawer = document.querySelector("#portfolioReturnDrawer");
const portfolioReturnDrawerOverlay = document.querySelector("#portfolioReturnDrawerOverlay");
const portfolioReturnDrawerCloseBtn = document.querySelector("#portfolioReturnDrawerCloseBtn");
const portfolioReturnDrawerTitle = document.querySelector("#portfolioReturnDrawerTitle");
const portfolioReturnChart = document.querySelector("#portfolioReturnChart");
const portfolioReturnXLabels = document.querySelector("#portfolioReturnXLabels");
const portfolioReturnYAxis = document.querySelector("#portfolioReturnYAxis");
const portfolioReturnLegend = document.querySelector("#portfolioReturnLegend");
const portfolioReturnNotice = document.querySelector("#portfolioReturnNotice");
const portfolioPositionCount = document.querySelector("#portfolioPositionCount");
const portfolioMessage = document.querySelector("#portfolioMessage");
const portfolioTypeList = document.querySelector("#portfolioTypeList");
const portfolioIndexerList = document.querySelector("#portfolioIndexerList");
const portfolioCurrencyList = document.querySelector("#portfolioCurrencyList");
const portfolioAccountList = document.querySelector("#portfolioAccountList");
const portfolioPositions = document.querySelector("#portfolioPositions");
const portfolioHistory = document.querySelector("#portfolioHistory");
const portfolioGroupFilter = document.querySelector("#portfolioGroupFilter");
const portfolioTabButtons = document.querySelectorAll("[data-portfolio-tab]");
const importForm = document.querySelector("#importForm");
const importTarget = document.querySelector("#importTarget");
const importAccount = document.querySelector("#importAccount");
const importAccountLabel = document.querySelector("#importAccountLabel");
const importCreditCard = document.querySelector("#importCreditCard");
const importCardLabel = document.querySelector("#importCardLabel");
const downloadImportTemplateButton = document.querySelector("#downloadImportTemplateButton");
const importMessage = document.querySelector("#importMessage");
const importResult = document.querySelector("#importResult");
const operationHistoryForm = document.querySelector("#operationHistoryForm");
const operationHistoryDateFrom = document.querySelector("#operationHistoryDateFrom");
const operationHistoryDateTo = document.querySelector("#operationHistoryDateTo");
const operationHistoryModule = document.querySelector("#operationHistoryModule");
const operationHistoryType = document.querySelector("#operationHistoryType");
const operationHistoryAccount = document.querySelector("#operationHistoryAccount");
const operationHistoryCard = document.querySelector("#operationHistoryCard");
const operationHistoryGroupBy = document.querySelector("#operationHistoryGroupBy");
const operationHistoryList = document.querySelector("#operationHistoryList");
const operationHistoryMessage = document.querySelector("#operationHistoryMessage");
const operationHistoryLoadMoreButton = document.querySelector("#operationHistoryLoadMoreButton");
const instructionsSearch = document.querySelector("#instructionsSearch");
const instructionsClearSearch = document.querySelector("#instructionsClearSearch");
const instructionsGroups = document.querySelector("#instructionsGroups");
const instructionsEmpty = document.querySelector("#instructionsEmpty");
const emailForm = document.querySelector("#emailForm");
const passwordForm = document.querySelector("#passwordForm");
const emailConfigForm = document.querySelector("#emailConfigForm");
const emailConfigProvider = document.querySelector("#emailConfigProvider");
const emailConfigManualFields = document.querySelector("#emailConfigManualFields");
const emailConfigPreset = document.querySelector("#emailConfigPreset");
const clearLaunchesForm = document.querySelector("#clearLaunchesForm");
const deleteUserForm = document.querySelector("#deleteUserForm");
const themePreference = document.querySelector("#themePreference");
const emailMessage = document.querySelector("#emailMessage");
const passwordMessage = document.querySelector("#passwordMessage");
const emailConfigMessage = document.querySelector("#emailConfigMessage");
const aiConfigForm = document.querySelector("#aiConfigForm");
const aiConfigEnabled = document.querySelector("#aiConfigEnabled");
const aiConfigProvider = document.querySelector("#aiConfigProvider");
const aiConfigCustomFields = document.querySelector("#aiConfigCustomFields");
const aiConfigBaseUrlField = document.querySelector("#aiConfigBaseUrlField");
const aiConfigModelField = document.querySelector("#aiConfigModelField");
const aiConfigAuthTypeField = document.querySelector("#aiConfigAuthTypeField");
const aiConfigApiKeyField = document.querySelector("#aiConfigApiKeyField");
const aiConfigTimeoutField = document.querySelector("#aiConfigTimeoutField");
const aiConfigTemperatureField = document.querySelector("#aiConfigTemperatureField");
const aiConfigMaxTokensField = document.querySelector("#aiConfigMaxTokensField");
const aiConfigBaseUrl = document.querySelector("#aiConfigBaseUrl");
const aiConfigModel = document.querySelector("#aiConfigModel");
const aiConfigAuthType = document.querySelector("#aiConfigAuthType");
const aiConfigApiKey = document.querySelector("#aiConfigApiKey");
const aiConfigTimeout = document.querySelector("#aiConfigTimeout");
const aiConfigTemperature = document.querySelector("#aiConfigTemperature");
const aiConfigMaxTokens = document.querySelector("#aiConfigMaxTokens");
const aiConfigMessage = document.querySelector("#aiConfigMessage");
const userPrefTabs = document.querySelector(".user-pref-tabs");
const consultorConfigForm = document.querySelector("#consultorConfigForm");
const consultorEnabled = document.querySelector("#consultorEnabled");
const consultorInvestorProfile = document.querySelector("#consultorInvestorProfile");
const consultorConfigMessage = document.querySelector("#consultorConfigMessage");
const consultorProfileForm = document.querySelector("#consultorProfileForm");
const consultorProfileAge = document.querySelector("#consultorProfileAge");
const consultorProfileHome = document.querySelector("#consultorProfileHome");
const consultorProfileDependents = document.querySelector("#consultorProfileDependents");
const consultorProfileDependentsCountField = document.querySelector("#consultorProfileDependentsCountField");
const consultorProfileDependentsCount = document.querySelector("#consultorProfileDependentsCount");
const consultorProfileGoal = document.querySelector("#consultorProfileGoal");
const consultorProfileHorizon = document.querySelector("#consultorProfileHorizon");
const consultorProfileLossTolerance = document.querySelector("#consultorProfileLossTolerance");
const consultorProfileIncome = document.querySelector("#consultorProfileIncome");
const consultorProfileDeleteButton = document.querySelector("#consultorProfileDeleteButton");
const consultorProfileMessage = document.querySelector("#consultorProfileMessage");
const maisRetornoConfigForm = document.querySelector("#maisRetornoConfigForm");
const maisRetornoEnabled = document.querySelector("#maisRetornoEnabled");
const maisRetornoApiKey = document.querySelector("#maisRetornoApiKey");
const maisRetornoConfigMessage = document.querySelector("#maisRetornoConfigMessage");
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
const fetchInvestmentFundQuoteButton = document.querySelector("#fetchInvestmentFundQuoteButton");
const investmentFundQuoteHint = document.querySelector("#investmentFundQuoteHint");
const investmentFixedFields = document.querySelector("#investmentFixedFields");
const investmentPricingFields = document.querySelector("#investmentPricingFields");
const investmentEmergencyReserveFields = document.querySelector("#investmentEmergencyReserveFields");
const investmentTradingCostFields = document.querySelector("#investmentTradingCostFields");
const investmentTaxCostFields = document.querySelector("#investmentTaxCostFields");
const investmentFixedIncomeMode = document.querySelector("#investmentFixedIncomeMode");
const investmentFixedIncomeIndexer = document.querySelector("#investmentFixedIncomeIndexer");
const investmentFixedIncomeRateLabel = document.querySelector("#investmentFixedIncomeRateLabel");
const investmentFixedIncomeRate = document.querySelector("#investmentFixedIncomeRate");
const investmentFixedIncomePreview = document.querySelector("#investmentFixedIncomePreview");
const transactionCategory = document.querySelector("#transactionCategory");
const transactionCategoryRow = document.querySelector("#transactionCategoryRow");
const transactionSubcategory = document.querySelector("#transactionSubcategory");
const transactionClassificationSuggestion = document.querySelector("#transactionClassificationSuggestion");
const seriesKind = document.querySelector("#seriesKind");
const seriesKindRow = document.querySelector("#seriesKindRow");
const installmentCount = document.querySelector("#installmentCount");
const installmentCountLabel = document.querySelector("#installmentCountLabel");
const recurrenceFields = document.querySelector("#recurrenceFields");
const recurrenceFrequency = document.querySelector("#recurrenceFrequency");
const recurrenceAverageFields = document.querySelector("#recurrenceAverageFields");
const useAverage = document.querySelector("#useAverage");
const exchangeRate = document.querySelector("#exchangeRate");
const exchangeRateLabel = document.querySelector("#exchangeRateLabel");
const userName = document.querySelector("#userName");
const logoutButton = document.querySelector("#logoutButton");
const cancelEditButton = document.querySelector("#cancelEditButton");
const cancelTransactionEditButton = document.querySelector("#cancelTransactionEditButton");
const formTitle = document.querySelector("#formTitle");
const moduleEyebrow = document.querySelector("#moduleEyebrow");
const pageTitle = document.querySelector("#pageTitle");
const contextualHelpButton = document.querySelector("#contextualHelpButton");
const privacyToggleButton = document.querySelector("#privacyToggleButton");
const monthIncome = document.querySelector("#monthIncome");
const monthExpense = document.querySelector("#monthExpense");
const monthInvestment = document.querySelector("#monthInvestment");
const savingsRate = document.querySelector("#savingsRate");
const cockpitTabs = document.querySelectorAll("[data-cockpit-tab]");
const cockpitSummaryPanel = document.querySelector("#cockpitSummaryPanel");
const cockpitMonthLabel = document.querySelector("#cockpitMonthLabel");
const previousCockpitMonthButton = document.querySelector("#previousCockpitMonthButton");
const todayCockpitMonthButton = document.querySelector("#todayCockpitMonthButton");
const nextCockpitMonthButton = document.querySelector("#nextCockpitMonthButton");
const currencyList = document.querySelector("#currencyList");
const cockpitPortfolioByType = document.querySelector("#cockpitPortfolioByType");
const cockpitLimitAlert = document.querySelector("#cockpitLimitAlert");
const cockpitPortfolioMaturityAlert = document.querySelector("#cockpitPortfolioMaturityAlert");
const cockpitVersionAlert = document.querySelector("#cockpitVersionAlert");
const cockpitVersionAlertVersion = document.querySelector("#cockpitVersionAlertVersion");
const cockpitVersionAlertDismiss = document.querySelector("#cockpitVersionAlertDismiss");
const cockpitCalendarPanel = document.querySelector("#cockpitCalendarPanel");
const cockpitCalendarMeta = document.querySelector("#cockpitCalendarMeta");
const consultorTabs = document.querySelectorAll("[data-consultor-tab]");
const consultorAnalysesPanel = document.querySelector("#consultorAnalysesPanel");
const consultorHistoryPanel = document.querySelector("#consultorHistoryPanel");
const consultorStatus = document.querySelector("#consultorStatus");
const consultorCardGrid = document.querySelector("#consultorCardGrid");
const consultorOutput = document.querySelector("#consultorOutput");
const consultorHistoryList = document.querySelector("#consultorHistoryList");
const consultorHistoryFilter = document.querySelector("#consultorHistoryFilter");
const consultorHistoryRefreshButton = document.querySelector("#consultorHistoryRefreshButton");
const overdueReceivablesList = document.querySelector("#overdueReceivablesList");
const overduePayablesList = document.querySelector("#overduePayablesList");
const maturity30DaysList = document.querySelector("#maturity30DaysList");
const maturity60DaysList = document.querySelector("#maturity60DaysList");
const financialHealthPanel = document.querySelector("#financialHealthPanel");
const financialHealthContent = document.querySelector("#financialHealthContent");
const trendsPanel = document.querySelector("#trendsPanel");
const trendsContent = document.querySelector("#trendsContent");
const trendsMeta = document.querySelector("#trendsMeta");
const topExpensesChart = document.querySelector("#topExpensesChart");
const cashDistributionChart = document.querySelector("#cashDistributionChart");
const previousMonthButton = document.querySelector("#previousMonthButton");
const todayMonthButton = document.querySelector("#todayMonthButton");
const nextMonthButton = document.querySelector("#nextMonthButton");
const transactionMonthLabel = document.querySelector("#transactionMonthLabel");
const currentBalanceSummary = document.querySelector("#currentBalanceSummary");
const forecastBalanceLabel = document.querySelector("#forecastBalanceLabel");
const forecastBalanceSummary = document.querySelector("#forecastBalanceSummary");
const transactionBalanceHistoryChart = document.querySelector("#transactionBalanceHistoryChart");
const transactionSearch = document.querySelector("#transactionSearch");
const clearTransactionSearchButton = document.querySelector("#clearTransactionSearchButton");
const transactionStatusFilterButtons = document.querySelectorAll("[data-transaction-status-filter]");
const transactionContextCount = document.querySelector("#transactionContextCount");
const simulationForm = document.querySelector("#simulationForm");
const simulationType = document.querySelector("#simulationType");
const simulationDate = document.querySelector("#simulationDate");
const simulationAccount = document.querySelector("#simulationAccount");
const simulationSeriesKind = document.querySelector("#simulationSeriesKind");
const simulationInstallmentCountLabel = document.querySelector("#simulationInstallmentCountLabel");
const simulationInstallmentCount = document.querySelector("#simulationInstallmentCount");
const simulationRecurrenceGroup = document.querySelector("#simulationRecurrenceGroup");
const simulationRecurrenceFrequency = document.querySelector("#simulationRecurrenceFrequency");
const simulationMessage = document.querySelector("#simulationMessage");
const simulationCurrentBalance = document.querySelector("#simulationCurrentBalance");
const simulationProjectedBalance = document.querySelector("#simulationProjectedBalance");
const simulationDifference = document.querySelector("#simulationDifference");
const simulationChart = document.querySelector("#simulationChart");
  const simulationWarnings = document.querySelector("#simulationWarnings");
const resetSimulationButton = document.querySelector("#resetSimulationButton");
const aboutAppVersion = document.querySelector("#aboutAppVersion");
const navButtons = document.querySelectorAll("[data-view]");
const moduleViews = {
  cockpit: document.querySelector("#cockpitView"),
  accounts: document.querySelector("#accountsView"),
  creditCards: document.querySelector("#creditCardsView"),
  cardLaunches: document.querySelector("#cardLaunchesView"),
  transactions: document.querySelector("#transactionsView"),
  portfolio: document.querySelector("#portfolioView"),
  limits: document.querySelector("#limitsView"),
  simulations: document.querySelector("#simulationsView"),
  reports: document.querySelector("#reportsView"),
  classifications: document.querySelector("#classificationsView"),
  imports: document.querySelector("#importsView"),
  operationHistory: document.querySelector("#operationHistoryView"),
  user: document.querySelector("#userView"),
  instructions: document.querySelector("#instructionsView"),
  about: document.querySelector("#aboutView"),
};

const viewTitles = {
  cockpit: ["Cockpit", "Resumo financeiro"],
  accounts: ["Cadastro", "Minhas Contas"],
  creditCards: ["Cadastro", "Meus Cartões"],
  cardLaunches: ["Lançamentos", "Fatura de Cartões"],
  transactions: ["Lançamentos", "Extrato de Contas"],
  portfolio: ["Gestão", "Portfólio"],
  limits: ["Gestão", "Limite de gastos"],
  simulations: ["Gestão", "Efeito Borboleta"],
  reports: ["Gestão", "Relatórios"],
  classifications: ["Gestão", "Categorias e tags"],
  imports: ["Gestão", "Importação"],
  operationHistory: ["Gestão", "Histórico de Operações"],
  user: ["Usuário", "Preferências"],
  instructions: ["Usuário", "Instruções"],
  about: ["Usuário", "Sobre"],
};

const CONTEXTUAL_HELP_TOPICS = {
  cockpit: "entender-cockpit",
  accounts: "primeira-conta",
  creditCards: "cadastrar-cartao",
  cardLaunches: "lancar-compras-cartao",
  transactions: "primeiro-lancamento",
  portfolio: "entender-portfolio",
  limits: "limites-gastos",
  simulations: "simulacao-borboleta",
  reports: "relatorios",
  classifications: "categorias-tags",
  imports: "importacao-dados",
  operationHistory: "historico-operacoes",
  user: "tema-privacidade",
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
  formatMonthShortLabel,
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
    statementControls,
    statementScopeSelect,
    statementCurrencySelect,
    statementAccountSelect,
    statementCardSelect,
    printStatementButton,
    reportContent,
  },
  shiftMonth,
  formatDate,
  formatMonthLabel,
  formatMonthShortLabel,
  formatMoney,
  formatPercent,
  escapeHtml,
  isInvestmentTransaction,
  isInstallmentTransaction,
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

const operationHistoryView = registerOperationHistoryView({
  state,
  elements: {
    operationHistoryForm,
    operationHistoryDateFrom,
    operationHistoryDateTo,
    operationHistoryModule,
    operationHistoryType,
    operationHistoryAccount,
    operationHistoryCard,
    operationHistoryGroupBy,
    operationHistoryList,
    operationHistoryMessage,
    operationHistoryLoadMoreButton,
  },
  formatDate,
});

const instructionsView = registerInstructionsView({
  state,
  elements: {
    instructionsSearch,
    instructionsClearSearch,
    instructionsGroups,
    instructionsEmpty,
  },
  escapeHtml,
  emptyState,
  onNavigateToModule: (route) => showModule(route),
});

const cockpitView = registerCockpitView({
  state,
  elements: {
    monthIncome,
    monthExpense,
    monthInvestment,
    savingsRate,
    cockpitTabs,
    cockpitSummaryPanel,
    cockpitMonthLabel,
    previousCockpitMonthButton,
    todayCockpitMonthButton,
    nextCockpitMonthButton,
    currencyList,
    monthlyPlanningList,
    installmentDebtList,
    topExpensesChart,
    cashDistributionChart,
    cockpitPortfolioByType,
    cockpitPortfolioMaturityAlert,
    cockpitVersionAlert,
    cockpitVersionAlertVersion,
    cockpitVersionAlertDismiss,
    cockpitCalendarPanel,
    cockpitCalendarMeta,
    consultorTabs,
    consultorAnalysesPanel,
    consultorHistoryPanel,
    consultorStatus,
    consultorCardGrid,
    consultorOutput,
    consultorHistoryList,
    consultorHistoryFilter,
    consultorHistoryRefreshButton,
    overdueReceivablesList,
    overduePayablesList,
    maturity30DaysList,
    maturity60DaysList,
    financialHealthPanel,
    financialHealthContent,
    trendsPanel,
    trendsContent,
    trendsMeta,
  },
  api,
  currentMonthValue,
  formatMonthLabel,
  formatMonthShortLabel,
  formatDate,
  shiftMonth,
  openMonthPicker,
  formatMoney,
  formatPercent,
  formatPercentValue,
  emptyState,
  escapeHtml,
  formatCategoryPath,
  isInstallmentTransaction,
  isInvestmentTransaction,
  chartColor,
  getCurrencyTotals,
  renderLimitAlerts: () => limitsView.renderLimitAlerts(cockpitMonthValue()),
  onCockpitMonthChanged: refreshCockpitData,
  loadPortfolio,
  portfolioTotalsByCurrency,
  portfolioMaturityAlerts: () => portfolioView.portfolioMaturityAlerts(),
  goToPortfolio: () => showModule("portfolio"),
  onNavigateToTransaction: (transactionId, accountId, date) => {
    // spec: cockpit-calendario v0.6 — critério 17
    state.transactionHighlightId = String(transactionId);
    if (accountId && state.accounts.some((account) => String(account.id) === String(accountId))) {
      state.selectedAccountId = String(accountId);
    }
    if (date) {
      const month = String(date).slice(0, 7);
      if (isValidMonthValue(month)) {
        state.transactionMonth = month;
      }
    }
    state.transactionSearch = "";
    state.transactionStatusFilter = "all";
    showModule("transactions");
  },

  onNavigateToPortfolio: (positionId) => {
    state.portfolioHighlightId = String(positionId);
    showModule("portfolio");
  },
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
    cardInvoiceSearch,
    cardInvoiceStatusFilterButtons,
    cardTransactionForm,
    cardTransactionFormTitle,
    cardTransactionType,
    cardTransactionCategory,
    cardTransactionSubcategory,
    cardClassificationSuggestion,
    cardTransactionTagOptions,
    cardSeriesKind,
    cardInstallmentCount,
    cardInstallmentCountLabel,
    cardRecurrenceFields,
    cardRecurrenceFrequency,
    cardRecurrenceAverageFields,
    cardUseAverage,
    cardInvoiceList,
    cancelCardTransactionEditButton,
  },
  api,
  fetchAllListed,
  formData,
  setFormBusy,
  setMessage,
  emptyState,
  escapeHtml,
  normalizeSearch,
  formatMoney,
  formatDate,
  formatMonthLabel,
  formatMonthShortLabel,
  formatShortMonthName,
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
  decisionModal,
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
  },
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
});

const simulationsView = registerSimulationsView({
  state,
  elements: {
    simulationForm,
    simulationType,
    simulationDate,
    simulationAccount,
    simulationSeriesKind,
    simulationInstallmentCountLabel,
    simulationInstallmentCount,
    simulationRecurrenceGroup,
    simulationRecurrenceFrequency,
    simulationMessage,
    simulationCurrentBalance,
    simulationProjectedBalance,
    simulationDifference,
    simulationChart,
    simulationWarnings,
    resetSimulationButton,
  },
  formatMoney,
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
    portfolioReturnYAxis,
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
    portfolioTabButtons,
  },
  api,
  formData,
  setMessage,
  escapeHtml,
  formatMoney,
  formatPercent,
  formatPercentValue,
  formatDate,
  formatMonthShortLabel,
  formatDecimal,
  moneyInputValue,
  portfolioQuoteText,
  todayLocalDateValue,
  chartColor,
  decisionModal,
  onPortfolioChanged: () => {
    renderCockpitPortfolioByType();
    renderPortfolioMaturityAlerts();
  },
  onPortfolioRedeemed: loadTransactionsAndAccounts,
  editSourceTransaction: editPortfolioSourceTransaction,
});

navButtons.forEach((button) => button.addEventListener("click", () => showModule(button.dataset.view)));
sidebarToggle.addEventListener("click", () => toggleSidebar());
privacyToggleButton?.addEventListener("click", () => {
  const mode = togglePrivacyMode();
  updatePrivacyToggleButton(privacyToggleButton, mode);
});
contextualHelpButton?.addEventListener("click", () => {
  const topicId = contextualHelpButton.dataset.contextualTopic;
  if (!topicId) {
    return;
  }
  showModule("instructions");
  instructionsView.openTopic(topicId);
});
document.addEventListener("keydown", (event) => {
  if (event.key.toLowerCase() !== "p" || event.metaKey || event.ctrlKey || event.altKey || isTypingTarget(event.target)) {
    return;
  }
  event.preventDefault();
  const mode = togglePrivacyMode();
  updatePrivacyToggleButton(privacyToggleButton, mode);
});
updatePrivacyToggleButton(privacyToggleButton, document.documentElement.dataset.privacy);
observePrivacyMoneyValues(document.body);

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
    aiConfigForm,
    aiConfigEnabled,
    aiConfigProvider,
    aiConfigCustomFields,
    aiConfigBaseUrlField,
    aiConfigModelField,
    aiConfigAuthTypeField,
    aiConfigApiKeyField,
    aiConfigTimeoutField,
    aiConfigTemperatureField,
    aiConfigMaxTokensField,
    aiConfigBaseUrl,
    aiConfigModel,
    aiConfigAuthType,
    aiConfigApiKey,
    aiConfigTimeout,
    aiConfigTemperature,
    aiConfigMaxTokens,
    consultorConfigForm,
    consultorEnabled,
    consultorInvestorProfile,
    consultorConfigMessage,
    consultorProfileForm,
    consultorProfileAge,
    consultorProfileHome,
    consultorProfileDependents,
    consultorProfileDependentsCountField,
    consultorProfileDependentsCount,
    consultorProfileGoal,
    consultorProfileHorizon,
    consultorProfileLossTolerance,
    consultorProfileIncome,
    consultorProfileDeleteButton,
    consultorProfileMessage,
    clearLaunchesForm,
    deleteUserForm,
    themePreference,
    userPrefTabs,
    maisRetornoConfigForm,
    maisRetornoEnabled,
    maisRetornoApiKey,
    maisRetornoConfigMessage,
    emailMessage,
    passwordMessage,
    emailConfigMessage,
    aiConfigMessage,
    clearLaunchesMessage,
    deleteUserMessage,
    userName,
  },
  formData,
  loadAll,
  resetSessionState,
  setMessage,
  decisionModal,
  theme: {
    setTheme,
    storedTheme,
  },
  state,
  onShowAuth: showAuth,
});
boot();

async function boot() {
  await loadAppInfo();
  loadLatestVersion().catch(() => {});
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

async function loadAppInfo() {
  try {
    state.appInfo = await api("/api/app-info");
  } catch (error) {
    state.appInfo = { version: "1.0.50" };
  }
  renderAppInfo();
}

function renderAppInfo() {
  if (aboutAppVersion) {
    aboutAppVersion.textContent = state.appInfo?.version || "1.0.50";
  }
}

async function loadLatestVersion() {
  try {
    state.latestVersion = await api("/api/latest-version");
  } catch (error) {
    state.latestVersion = null;
  }
  renderCockpit();
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
  state.transactionSearch = "";
  state.transactionStatusFilter = "all";
  state.transactionHighlightId = "";
  state.transactions = [];
  state.accountTransactions = [];
  state.cockpit = null;
  state.cockpitTab = "summary";
  state.cockpitMonth = currentMonthValue();
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

function handleSessionExpired() {
  resetSessionState();
  renderBaseViews();
  renderFinanceViews();
  renderManagementViews();
  showAuth("Sessao expirada. Entre novamente para continuar.");
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
      fetchAllListed("/api/transactions", "transactions"),
      fetchAllListed("/api/credit-card-transactions", "transactions"),
      fetchAllListed("/api/credit-card-payments", "payments"),
      api(`/api/cockpit?month=${encodeURIComponent(cockpitMonthValue())}`),
    ]);
    state.accounts = accountsResponse.accounts;
    state.creditCards = creditCardsResponse.cards;
    ensureSelectedCreditCard();
    ensureSelectedAccount();
    state.transactions = transactionsResponse;
    state.accountTransactions = [];
    state.cardTransactions = cardTransactionsResponse;
    state.cardPayments = cardPaymentsResponse || [];
    state.cockpit = cockpitResponse;
    state.cockpitLoadedMonth = cockpitMonthValue();
    invalidateFinancialHealth();
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
    state.cockpitLoadedMonth = "";
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
    fetchAllListed("/api/transactions", "transactions"),
    fetchAllListed("/api/credit-card-transactions", "transactions"),
    fetchAllListed("/api/credit-card-payments", "payments"),
    api(`/api/cockpit?month=${encodeURIComponent(cockpitMonthValue())}`),
  ]);
  state.accounts = accountsResponse.accounts;
  state.creditCards = creditCardsResponse.cards;
  ensureSelectedCreditCard();
  ensureSelectedAccount();
  state.transactions = transactionsResponse;
  await loadTransactionSlice();
  state.cardTransactions = cardTransactionsResponse;
  state.cardPayments = cardPaymentsResponse || [];
  state.cockpit = cockpitResponse;
  state.cockpitLoadedMonth = cockpitMonthValue();
  invalidateFinancialHealth();
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
  const response = await api(`/api/cockpit?month=${encodeURIComponent(cockpitMonthValue())}`);
  state.cockpit = response;
  state.cockpitLoadedMonth = cockpitMonthValue();
  invalidateFinancialHealth();
}

async function refreshCockpitData() {
  const requestId = ++state.cockpitRefreshRequestId;
  const month = cockpitMonthValue();
  if (state.cockpit && state.cockpitLoadedMonth === month) {
    renderCockpit();
    return;
  }
  const [
    accountsResponse,
    transactionsResponse,
    cardTransactionsResponse,
    cardPaymentsResponse,
    cockpitResponse,
    spendingLimitsResponse,
  ] = await Promise.all([
    api("/api/checking-accounts"),
    fetchAllListed("/api/transactions", "transactions"),
    fetchAllListed("/api/credit-card-transactions", "transactions"),
    fetchAllListed("/api/credit-card-payments", "payments"),
    api(`/api/cockpit?month=${encodeURIComponent(month)}`),
    api(`/api/spending-limits?month=${encodeURIComponent(month)}`),
  ]);
  if (requestId !== state.cockpitRefreshRequestId) {
    return;
  }
  state.accounts = accountsResponse.accounts || [];
  ensureSelectedAccount();
  state.transactions = transactionsResponse || [];
  state.cardTransactions = cardTransactionsResponse || [];
  state.cardPayments = cardPaymentsResponse || [];
  state.cockpit = cockpitResponse;
  state.cockpitLoadedMonth = month;
  state.currentSpendingLimits = spendingLimitsResponse.limits || [];
  invalidateFinancialHealth();
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
  invalidateFinancialHealth();
}

function invalidateFinancialHealth() {
  cockpitView.invalidateFinancialHealth();
  cockpitView.invalidateCalendar();
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
  await limitsView.loadCurrentSpendingLimits(cockpitMonthValue());
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
  const previousView = state.view;
  state.view = view;
  const updateVisibleModule = () => {
    for (const [name, element] of Object.entries(moduleViews)) {
      element.hidden = name !== view;
    }
    navButtons.forEach((button) => button.classList.toggle("active", button.dataset.view === view));
    moduleEyebrow.textContent = viewTitles[view][0];
    pageTitle.textContent = viewTitles[view][1];
  };
  if (shouldAnimateModuleTransition(previousView, view)) {
    document.startViewTransition(updateVisibleModule);
  } else {
    updateVisibleModule();
  }
  if (contextualHelpButton) {
    const contextualTopic = CONTEXTUAL_HELP_TOPICS[view];
    contextualHelpButton.dataset.contextualTopic = contextualTopic || "";
    contextualHelpButton.hidden = !contextualTopic;
  }
  renderLimitAlerts();
  renderPortfolioMaturityAlerts();
  if (view === "cockpit") {
    renderCockpit();
    refreshCockpitData().catch((error) => console.error(error));
  }
  if (view === "transactions") {
    ensureSelectedAccount();
    renderTransactionAccounts();
    updateTransactionTypeState();
    loadTransactionSlice().then(() => {
      renderTransactions();
      transactionsView.highlightSavedTransaction();
    }).catch((error) => setMessage(transactionMessage, error.message, "error"));
  }
  if (view === "limits") {
    renderLimits();
  }
  if (view === "simulations") {
    simulationsView.loadSimulationFormData().catch((error) => setMessage(simulationMessage, error.message, "error"));
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
  if (view === "operationHistory") {
    operationHistoryView.renderFilters();
    operationHistoryView.loadOperationLogs({ reset: true });
  }
  if (view === "instructions") {
    instructionsView.renderInstructions();
  }
  if (view === "user" && state.user) {
    emailForm.elements.email.value = state.user.email;
    userAdminViewController.syncThemePreference();
    userAdminViewController.loadEmailConfigStatus();
    userAdminViewController.loadAIConfigStatus();
    userAdminViewController.loadConsultorConfigStatus();
    userAdminViewController.loadConsultorProfile();
    userAdminViewController.loadMaisRetornoConfigStatus();
  }
}

function shouldAnimateModuleTransition(previousView, nextView) {
  if (!previousView || previousView === nextView || typeof document.startViewTransition !== "function") {
    return false;
  }
  return !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
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

function renderPortfolioMaturityAlerts() {
  cockpitView.renderPortfolioMaturityAlerts();
}

function chartColor(index) {
  const fallbackPalette = ["#14b8a6", "#6366f1", "#f97316", "#ec4899", "#22c55e", "#3b82f6"];
  const tokenName = `--chart-${(index % fallbackPalette.length) + 1}`;
  const tokenColor = getComputedStyle(document.documentElement).getPropertyValue(tokenName).trim();
  return tokenColor || fallbackPalette[index % fallbackPalette.length];
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
  const cockpitMonth = cockpitMonthValue();
  const cockpitLimitDate = monthEndDate(cockpitMonth);
  const totals = new Map();
  for (const account of state.accounts) {
    const row = currencyTotalRow(totals, account.currency);
    const amount = accountProjectedBalance(account, cockpitLimitDate);
    row.current += amount;
    row.accounts.push({
      id: account.id,
      name: account.name,
      type: accountTypeLabel(account.account_type),
      amount,
      reconciled: accountReconciledBalance(account, cockpitLimitDate),
    });
  }
  for (const card of state.creditCards) {
    const row = currencyTotalRow(totals, card.currency);
    const openAmount = cardInvoiceCompetenceBalance(card.id, cockpitMonth);
    const reservedAmount = preferredCardForecastAmount(card, cockpitLimitDate);
    const signedAmount = -Math.max(openAmount - reservedAmount, 0);
    const displayedAmount = -Math.max(openAmount, 0);
    row.current += signedAmount;
    row.cards.push({
      id: card.id,
      name: card.name,
      issuer: card.issuer,
      amount: displayedAmount,
      reconciled: -cardReconciledBalance(card.id, cockpitMonth),
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

function accountReconciledBalance(account, limitDate) {
  return accountBalanceUntil(account, limitDate, true);
}

function accountProjectedBalance(account, limitDate) {
  return accountBalanceUntil(account, limitDate, false) - preferredCardForecastForAccount(account, limitDate);
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

function accountHasPreferredCardForecast(account, limitDate) {
  return preferredCardForecastForAccount(account, limitDate) > 0;
}

function preferredCardForecastForAccount(account, limitDate) {
  if (!account || !limitDate) {
    return 0;
  }
  return state.creditCards.reduce((total, card) => {
    if (String(card.preferred_payment_account_id || "") !== String(account.id)) {
      return total;
    }
    if ((card.currency || "BRL") !== (account.currency || "BRL")) {
      return total;
    }
    return total + preferredCardForecastAmount(card, limitDate);
  }, 0);
}

function preferredCardForecastAmount(card, limitDate) {
  if (!card || !card.preferred_payment_account_id) {
    return 0;
  }
  const forecastByInvoice = new Map();
  for (const transaction of state.cardTransactions) {
    if (
      String(transaction.credit_card_id) !== String(card.id)
      || !transaction.reconciled_at
      || !transaction.invoice_month
      || cardInvoiceDueDateValue(transaction.invoice_month, card.due_day) > limitDate
      || isCardInvoicePaid(card.id, transaction.invoice_month)
    ) {
      continue;
    }
    const current = forecastByInvoice.get(transaction.invoice_month) || 0;
    forecastByInvoice.set(transaction.invoice_month, current + cardTransactionInvoiceDelta(transaction));
  }
  return [...forecastByInvoice.values()].reduce((total, amount) => total + Math.max(amount, 0), 0);
}

function cardTransactionInvoiceDelta(transaction) {
  const amount = Number(transaction.amount || 0);
  if (transaction.type === "income") {
    return -amount;
  }
  if (transaction.type === "expense") {
    return amount;
  }
  return 0;
}

function isCardInvoicePaid(cardId, invoiceMonth) {
  return state.cardPayments.some((payment) => (
    String(payment.credit_card_id) === String(cardId) && payment.invoice_month === invoiceMonth
  ));
}

function cardInvoiceDueDateValue(invoiceMonth, dueDay) {
  return cardInvoiceDateValue(invoiceMonth, dueDay);
}

function cardInvoiceDateValue(invoiceMonth, day) {
  const [year, month] = String(invoiceMonth).split("-").map(Number);
  const safeDay = Number(day || 1);
  if (!year || !month) {
    return `${invoiceMonth}-01`;
  }
  const lastDay = new Date(year, month, 0).getDate();
  const invoiceDay = Math.min(Math.max(safeDay, 1), lastDay);
  return `${year}-${String(month).padStart(2, "0")}-${String(invoiceDay).padStart(2, "0")}`;
}

function cardInvoiceCompetenceBalance(cardId, invoiceMonth) {
  return state.cardTransactions.reduce((total, transaction) => {
    if (String(transaction.credit_card_id) !== String(cardId) || transaction.invoice_month !== invoiceMonth) {
      return total;
    }
    return total + cardTransactionInvoiceDelta(transaction);
  }, 0);
}

function cardReconciledBalance(cardId, invoiceMonth) {
  return state.cardTransactions.reduce((total, transaction) => {
    if (
      String(transaction.credit_card_id) !== String(cardId)
      || transaction.invoice_month !== invoiceMonth
      || !transaction.reconciled_at
    ) {
      return total;
    }
    return total + cardTransactionInvoiceDelta(transaction);
  }, 0);
}

function cardOpenBalance(cardId, untilInvoiceMonth = null) {
  return cardsView.cardOpenBalance(cardId, untilInvoiceMonth);
}

function creditCardCurrency(cardId) {
  return cardsView.creditCardCurrency(cardId);
}

function cockpitMonthValue() {
  if (!state.cockpitMonth) {
    state.cockpitMonth = currentMonthValue();
  }
  return state.cockpitMonth;
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
      if (!reconciledOnly) {
        totals.set(account.currency, (totals.get(account.currency) || 0) - preferredCardForecastForAccount(account, limitDate));
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
    if (!reconciledOnly) {
      for (const account of state.accounts) {
        totals.set(account.currency, (totals.get(account.currency) || 0) - preferredCardForecastForAccount(account, limitDate));
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

function showAuth(message = "") {
  authView.hidden = false;
  dashboardView.hidden = true;
  authViewController.switchAuthMode("login");
  if (message) {
    setMessage(authMessage, message, "error");
  }
}
