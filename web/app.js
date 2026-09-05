import { api, configureApi, fetchAllListed, upload } from "./modules/api.js";
import { destroyAllCharts } from "./modules/chart-adapter.js";
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
  initializeFormUX,
  normalizeSearch,
  setFormBusy,
  setLastUpdated,
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
import { applyTheme, setTheme, storedTheme, toggleTheme } from "./modules/theme-utils.js";
import { applyDensity, setDensity, storedDensity, toggleDensity } from "./modules/density-utils.js";
import { registerAuthView } from "./modules/auth-view.js";
import { registerUserAdminView } from "./modules/user-admin-view.js";
import { registerClassificationsView } from "./modules/classifications-view.js";
import { registerLimitsView } from "./modules/limits-view.js";
import { registerReportsView } from "./modules/reports-view.js";
import { registerImportsView } from "./modules/imports-view.js";
import { registerCockpitView } from "./modules/cockpit-view.js";
import { registerAccountsView } from "./modules/accounts-view.js";
import { registerCardsView } from "./modules/cards-view.js";
import { registerPortfolioView } from "./modules/portfolio-view.js?v=162";
import { registerTransactionsView } from "./modules/transactions-view.js";
import { registerSimulationsView } from "./modules/simulations-view.js";
import { registerOperationHistoryView } from "./modules/operation-history-view.js";
import { registerInstructionsView } from "./modules/instructions-view.js";
import { registerGlobalSearch } from "./modules/global-search.js";
import { registerCommandPalette } from "./modules/command-palette.js";
import { initializeOverlayUX } from "./modules/overlay-utils.js";
import { initializeDataUX } from "./modules/data-ux.js";
import { applyMasks, destroyMasks } from "./modules/input-mask.js";
import { createAppState, resetSessionData } from "./modules/app-state.js";
import { createAppDataLoader } from "./modules/app-data-loader.js";

applyTheme();
applyDensity();
applyPrivacyMode();
initializeFormUX();
initializeOverlayUX();
initializeDataUX();
applyMasks();

const decisionModal = createDecisionModal();

configureApi({
  onUnauthorized: handleSessionExpired,
  onMutation: handleDataMutation,
});

const state = createAppState({ currentMonth: currentMonthValue() });

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
const payPartialCardInvoiceButton = document.querySelector("#payPartialCardInvoiceButton");
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
const categorySearch = document.querySelector("#categorySearch");
const tagSearch = document.querySelector("#tagSearch");
const categoryListSummary = document.querySelector("#categoryListSummary");
const tagListSummary = document.querySelector("#tagListSummary");
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
const portfolioLastUpdated = document.querySelector("#portfolioLastUpdated");
const portfolioAssetFormPanel = document.querySelector("#portfolioAssetFormPanel");
const portfolioAssetForm = document.querySelector("#portfolioAssetForm");
const portfolioAssetFormTitle = document.querySelector("#portfolioAssetFormTitle");
const portfolioAssetAccount = document.querySelector("#portfolioAssetAccount");
const portfolioAssetType = document.querySelector("#portfolioAssetType");
const portfolioAssetIdentifier = document.querySelector("#portfolioAssetIdentifier");
const portfolioAssetIdentifierLabel = document.querySelector("#portfolioAssetIdentifierLabel");
const portfolioCnpjFields = document.querySelector("#portfolioCnpjFields");
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
const portfolioGroupDrawer = document.querySelector("#portfolioGroupDrawer");
const portfolioGroupDrawerOverlay = document.querySelector("#portfolioGroupDrawerOverlay");
const portfolioGroupDrawerCloseBtn = document.querySelector("#portfolioGroupDrawerCloseBtn");
const portfolioGroupDrawerTitle = document.querySelector("#portfolioGroupDrawerTitle");
const portfolioGroupDrawerList = document.querySelector("#portfolioGroupDrawerList");
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
const portfolioEvents = document.querySelector("#portfolioEvents");
const refreshPortfolioEventsButton = document.querySelector("#refreshPortfolioEventsButton");
const portfolioGoalsForm = document.querySelector("#portfolioGoalsForm");
const portfolioGoalsFields = document.querySelector("#portfolioGoalsFields");
const portfolioGoalsTotal = document.querySelector("#portfolioGoalsTotal");
const portfolioGoalsMessage = document.querySelector("#portfolioGoalsMessage");
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
const operationHistoryCount = document.querySelector("#operationHistoryCount");
const operationHistoryMessage = document.querySelector("#operationHistoryMessage");
const operationHistoryLoadMoreButton = document.querySelector("#operationHistoryLoadMoreButton");
const cockpitLastUpdated = document.querySelector("#cockpitLastUpdated");
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
const densityPreference = document.querySelector("#densityPreference");
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
const backupSettingsForm = document.querySelector("#backupSettingsForm");
const backupDirectory = document.querySelector("#backupDirectory");
const backupFrequency = document.querySelector("#backupFrequency");
const backupRetention = document.querySelector("#backupRetention");
const backupRememberPassword = document.querySelector("#backupRememberPassword");
const backupPassword = document.querySelector("#backupPassword");
const backupPasswordConfirmation = document.querySelector("#backupPasswordConfirmation");
const backupSettingsMessage = document.querySelector("#backupSettingsMessage");
const backupLastStatus = document.querySelector("#backupLastStatus");
const backupRunForm = document.querySelector("#backupRunForm");
const backupRunPassword = document.querySelector("#backupRunPassword");
const backupRunMessage = document.querySelector("#backupRunMessage");
const backupRestoreForm = document.querySelector("#backupRestoreForm");
const backupRestorePath = document.querySelector("#backupRestorePath");
const backupRestorePassword = document.querySelector("#backupRestorePassword");
const backupRestoreConfirmButton = document.querySelector("#backupRestoreConfirmButton");
const backupRestoreMessage = document.querySelector("#backupRestoreMessage");
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
const investmentAmountRow = document.querySelector("#investmentAmountRow");
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
const cockpitRoot = document.querySelector("#cockpitView");
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
const cockpitCriticalNotifications = document.querySelector("#cockpitCriticalNotifications");
const cockpitInformationalNotifications = document.querySelector("#cockpitInformationalNotifications");
const cockpitCombinedNotifications = document.querySelector("#cockpitCombinedNotifications");
const cockpitCriticalNotificationCount = document.querySelector("#cockpitCriticalNotificationCount");
const cockpitInformationalNotificationCount = document.querySelector("#cockpitInformationalNotificationCount");
const cockpitCombinedNotificationCount = document.querySelector("#cockpitCombinedNotificationCount");
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
const simulationWeeklyProjection = document.querySelector("#simulationWeeklyProjection");
const simulationWarnings = document.querySelector("#simulationWarnings");
const simulationEmptyState = document.querySelector("#simulationEmptyState");
const simulationResultsContent = document.querySelector("#simulationResultsContent");
const resetSimulationButton = document.querySelector("#resetSimulationButton");
const aboutAppVersion = document.querySelector("#aboutAppVersion");
const globalSearchTrigger = document.querySelector("#globalSearchTrigger");
const globalSearchDialog = document.querySelector("#globalSearchDialog");
const globalSearchInput = document.querySelector("#globalSearchInput");
const globalSearchResults = document.querySelector("#globalSearchResults");
const globalSearchClose = document.querySelector("#globalSearchClose");
const commandPaletteTrigger = document.querySelector("#commandPaletteTrigger");
const commandPaletteDialog = document.querySelector("#commandPaletteDialog");
const commandPaletteInput = document.querySelector("#commandPaletteInput");
const commandPaletteResults = document.querySelector("#commandPaletteResults");
const commandPaletteClose = document.querySelector("#commandPaletteClose");
const commandPaletteCount = document.querySelector("#commandPaletteCount");
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
const NAV_GROUPS_COLLAPSED_KEY = "financeiro.sidebar.navGroupsCollapsed";
const viewScrollPositions = new Map();

const appDataLoader = createAppDataLoader({
  state,
  services: { api, fetchAllListed },
  getViews: () => ({
    accounts: accountsView,
    cards: cardsView,
    transactions: transactionsView,
    cockpit: cockpitView,
    portfolio: portfolioView,
    classifications: classificationsView,
    limits: limitsView,
  }),
  actions: {
    cockpitMonthValue,
    ensureSelectedAccount,
    invalidateFinancialHealth,
    markPortfolioDirty,
    renderBase: renderBaseViews,
    renderFinance: () => { renderBaseViews(); renderFinanceViews(); },
    renderAll: () => { renderBaseViews(); renderFinanceViews(); renderManagementViews(); },
    renderCockpit,
    touchCockpitUpdated: () => setLastUpdated(cockpitLastUpdated),
    setLoadError: (message) => setMessage(accountMessage, message, "error"),
  },
});

const {
  loadAll,
  loadAccounts,
  loadCreditCards,
  loadTransactionsAndAccounts,
  loadTransactionSlice,
  loadCockpit,
  refreshCockpitData,
  loadPortfolio,
  loadClassifications,
  loadSpendingLimits,
  loadCurrentSpendingLimits,
  loadCardInvoice,
} = appDataLoader;

registerGlobalSearch({
  state,
  elements: {
    trigger: globalSearchTrigger,
    dialog: globalSearchDialog,
    input: globalSearchInput,
    results: globalSearchResults,
    closeButton: globalSearchClose,
  },
  viewTitles,
  normalizeSearch,
  escapeHtml,
  api,
  onNavigate: showModule,
});

registerCommandPalette({
  state,
  elements: {
    trigger: commandPaletteTrigger,
    dialog: commandPaletteDialog,
    input: commandPaletteInput,
    results: commandPaletteResults,
    closeButton: commandPaletteClose,
    count: commandPaletteCount,
  },
  viewTitles,
  normalizeSearch,
  escapeHtml,
  onNavigate: showModule,
  actions: {
    openGlobalSearch: () => globalSearchTrigger?.click(),
    getPrivacyMode: () => document.documentElement.dataset.privacy === "enabled",
    togglePrivacy: () => privacyToggleButton?.click(),
    getTheme: () => storedTheme(),
    toggleTheme: () => toggleTheme(),
    getDensity: () => storedDensity(),
    toggleDensity: () => toggleDensity(),
    openContextualHelp: () => contextualHelpButton?.click(),
  },
});

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
    categorySearch,
    tagSearch,
    categoryListSummary,
    tagListSummary,
  },
  api,
  formData,
  setFormBusy,
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
  setFormBusy,
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
    operationHistoryCount,
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
    cockpitRoot,
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
    cockpitCriticalNotifications,
    cockpitInformationalNotifications,
    cockpitCombinedNotifications,
    cockpitCriticalNotificationCount,
    cockpitInformationalNotificationCount,
    cockpitCombinedNotificationCount,
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
  portfolioMaturityAlerts: () => portfolioView.portfolioMaturityAlerts(),
  goToPortfolio: () => showModule("portfolio"),
  onNavigateToTransaction: (transactionId, accountId, date) => {
    // spec: cockpit-calendario v0.9 — critério 17
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
  onNotificationAction: async (action) => {
    const params = action?.params || {};
    if (action?.route === "limits") {
      if (isValidMonthValue(params.month)) state.limitMonth = params.month;
      await loadSpendingLimits();
      showModule("limits");
      return;
    }
    if (action?.route === "transactions") {
      if (isValidMonthValue(params.month)) state.transactionMonth = params.month;
      if (params.account_id) state.selectedAccountId = String(params.account_id);
      showModule("transactions");
      return;
    }
    if (action?.route === "cards") {
      if (isValidMonthValue(params.month)) state.cardInvoiceMonth = params.month;
      if (params.card_id) state.selectedCreditCardId = String(params.card_id);
      showModule("cardLaunches");
      return;
    }
    if (action?.route === "calendar") {
      state.cockpitTab = "calendar";
      showModule("cockpit");
      return;
    }
    if (action?.route === "portfolio") {
      showModule("portfolio");
    }
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
  setFormBusy,
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
    payPartialCardInvoiceButton,
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
  launchActionButton: (...args) => transactionsView.launchActionButton(...args),
  decisionModal,
  deleteSeriesScope,
  openMonthPicker,
  onCreditCardsChanged: async () => {
    await loadCockpit();
    renderBaseViews();
    renderFinanceViews();
  },
  onCardTransactionsChanged: () => {
    limitsView.renderLimits();
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
  loadCockpit,
  markPortfolioDirty,
  renderBaseViews,
  renderFinanceViews,
  renderPortfolio: () => portfolioView.renderPortfolio(),
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
    simulationWeeklyProjection,
    simulationWarnings,
    simulationEmptyState,
    simulationResultsContent,
    resetSimulationButton,
  },
  formatMoney,
  setFormBusy,
});

const portfolioView = registerPortfolioView({
  state,
  elements: {
    addPortfolioAssetButton,
    refreshPortfolioButton,
    portfolioLastUpdated,
    portfolioAssetFormPanel,
    portfolioAssetForm,
    portfolioAssetFormTitle,
    portfolioAssetAccount,
    portfolioAssetType,
    portfolioAssetIdentifier,
    portfolioAssetIdentifierLabel,
    portfolioCnpjFields,
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
    portfolioGroupDrawer,
    portfolioGroupDrawerOverlay,
    portfolioGroupDrawerCloseBtn,
    portfolioGroupDrawerTitle,
    portfolioGroupDrawerList,
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
    portfolioEvents,
    refreshPortfolioEventsButton,
    portfolioGoalsForm,
    portfolioGoalsFields,
    portfolioGoalsTotal,
    portfolioGoalsMessage,
    portfolioGroupFilter,
    portfolioTabButtons,
  },
  api,
  formData,
  setFormBusy,
  setMessage,
  escapeHtml,
  formatMoney,
  formatPercent,
  formatPercentValue,
  formatDate,
  formatMonthShortLabel,
  formatDecimal,
  moneyInputValue,
  parseDecimalInput,
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
document.querySelectorAll(".nav-group-toggle").forEach((toggle) => {
  toggle.addEventListener("click", () => {
    const group = toggle.closest(".nav-group");
    const collapsed = !group.classList.contains("collapsed");
    group.classList.toggle("collapsed", collapsed);
    toggle.setAttribute("aria-expanded", String(!collapsed));
    persistNavGroups();
  });
});
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
document.addEventListener("keydown", (event) => {
  const isPaletteKey = (event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k";
  if (!isPaletteKey || isTypingTarget(event.target)) {
    return;
  }
  event.preventDefault();
  commandPaletteTrigger?.click();
});
updatePrivacyToggleButton(privacyToggleButton, document.documentElement.dataset.privacy);
observePrivacyMoneyValues(document.body);

updateAccountTypeState();
initializeSidebar();
initializeNavGroups();
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
    densityPreference,
    userPrefTabs,
    maisRetornoConfigForm,
    maisRetornoEnabled,
    maisRetornoApiKey,
    maisRetornoConfigMessage,
    backupSettingsForm,
    backupDirectory,
    backupFrequency,
    backupRetention,
    backupRememberPassword,
    backupPassword,
    backupPasswordConfirmation,
    backupSettingsMessage,
    backupLastStatus,
    backupRunForm,
    backupRunPassword,
    backupRunMessage,
    backupRestoreForm,
    backupRestorePath,
    backupRestorePassword,
    backupRestoreConfirmButton,
    backupRestoreMessage,
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
  density: {
    setDensity,
    storedDensity,
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
    state.appInfo = { version: "2.0.0" };
  }
  renderAppInfo();
}

function renderAppInfo() {
  if (aboutAppVersion) {
    aboutAppVersion.textContent = state.appInfo?.version || "2.0.0";
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
  destroyAllCharts();
  destroyMasks();
  resetSessionData(state, { currentMonth: currentMonthValue() });
  operationHistoryView.resetCache();
  userAdminViewController.resetPreferencesCache();
  transactionsView.resetTransactionSliceCache();
  simulationsView.resetFormDataCache();
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
  if (previousView && previousView !== view) {
    viewScrollPositions.set(previousView, window.scrollY);
  }
  state.view = view;
  const updateVisibleModule = () => {
    for (const [name, element] of Object.entries(moduleViews)) {
      element.hidden = name !== view;
    }
    navButtons.forEach((button) => button.classList.toggle("active", button.dataset.view === view));
    expandNavGroupOfView(view);
    moduleEyebrow.textContent = viewTitles[view][0];
    pageTitle.textContent = viewTitles[view][1];
    if (previousView !== view && previousView === "portfolio") {
      portfolioView.onLeave();
    }
  };
  if (shouldAnimateModuleTransition(previousView, view)) {
    document.startViewTransition(updateVisibleModule);
  } else {
    updateVisibleModule();
  }
  if (previousView !== view) {
    requestAnimationFrame(() => window.scrollTo({ top: viewScrollPositions.get(view) || 0, behavior: "auto" }));
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
    transactionsView.updateTransactionTypeState();
    const transactionLoad = loadTransactionSlice();
    renderTransactions();
    transactionLoad.then(() => {
      renderTransactions();
      transactionsView.highlightSavedTransaction();
    }).catch((error) => {
      renderTransactions();
      setMessage(transactionMessage, error.message, "error");
    });
  }
  if (view === "limits") {
    limitsView.renderLimits();
  }
  if (view === "simulations") {
    simulationsView.loadSimulationFormData().catch((error) => setMessage(simulationMessage, error.message, "error"));
  }
  if (view === "reports") {
    reportsView.renderReports();
  }
  if (view === "portfolio") {
    portfolioView.onEnter().catch((error) => setMessage(portfolioMessage, error.message, "error"));
  }
  if (view === "creditCards") {
    renderCreditCards();
    if (!state.cardDataLoaded) {
      cardsView.loadCreditCards().then(renderCreditCards).catch((error) => setMessage(creditCardMessage, error.message, "error"));
    }
  }
  if (view === "cardLaunches") {
    renderCardInvoice();
  }
  if (view === "imports") {
    renderImportTargets();
  }
  if (view === "operationHistory") {
    operationHistoryView.renderFilters();
    operationHistoryView.loadOperationLogs({ reset: true, revalidate: true });
  }
  if (view === "instructions") {
    instructionsView.renderInstructions();
  }
  if (view === "user" && state.user) {
    emailForm.elements.email.value = state.user.email;
    userAdminViewController.syncThemePreference();
    userAdminViewController.syncDensityPreference();
    userAdminViewController.loadPreferences();
  }
}

function handleDataMutation() {
  operationHistoryView?.markDirty();
  userAdminViewController?.markPreferencesDirty();
  transactionsView?.markTransactionSliceDirty();
  simulationsView?.markFormDataDirty();
  state.reportDataMonth = "";
  state.reportOverviewMonth = "";
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

function initializeNavGroups() {
  const storedValue = localStorage.getItem(NAV_GROUPS_COLLAPSED_KEY);
  const collapsedKeys = new Set(storedValue ? String(storedValue).split(",").filter(Boolean) : []);
  document.querySelectorAll(".nav-group").forEach((group) => {
    const key = group.dataset.navGroup;
    if (!key) {
      return;
    }
    const collapsed = collapsedKeys.has(key);
    group.classList.toggle("collapsed", collapsed);
    const toggle = group.querySelector(".nav-group-toggle");
    if (toggle) {
      toggle.setAttribute("aria-expanded", String(!collapsed));
    }
  });
}

function persistNavGroups() {
  const collapsedKeys = [...document.querySelectorAll(".nav-group.collapsed")]
    .map((group) => group.dataset.navGroup)
    .filter(Boolean);
  localStorage.setItem(NAV_GROUPS_COLLAPSED_KEY, collapsedKeys.join(","));
}

function expandNavGroupOfView(view) {
  const button = document.querySelector(`.nav-button[data-view="${view}"]`);
  const group = button?.closest(".nav-group");
  if (!group || !group.classList.contains("collapsed")) {
    return;
  }
  group.classList.remove("collapsed");
  const toggle = group.querySelector(".nav-group-toggle");
  if (toggle) {
    toggle.setAttribute("aria-expanded", "true");
  }
  persistNavGroups();
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
  limitsView.renderLimits();
  reportsView.renderReports();
}

function renderManagementViews() {
  classificationsView.renderClassifications();
  portfolioView.renderPortfolio();
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

function getCurrencyTotals() {
  return new Map((state.cockpit?.currency_totals || []).map(({ currency, ...row }) => [currency, {
    ...row,
    accounts: (row.accounts || []).map((account) => ({ ...account, type: accountTypeLabel(account.type) })),
  }]));
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
