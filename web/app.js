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
  categories: [],
  tags: [],
  spendingLimits: [],
  portfolio: null,
  portfolioDirty: true,
  portfolioLoading: false,
  portfolioError: "",
  portfolioGroup: "none",
  portfolioExpandedGroups: new Set(),
  view: "cockpit",
  transactionMonth: new Date().toISOString().slice(0, 7),
  limitMonth: new Date().toISOString().slice(0, 7),
  cardInvoiceMonth: new Date().toISOString().slice(0, 7),
  reportMonth: new Date().toISOString().slice(0, 7),
  reportTab: "categories",
  reportAccountId: "",
};

const authView = document.querySelector("#authView");
const dashboardView = document.querySelector("#dashboardView");
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
const creditCardMessage = document.querySelector("#creditCardMessage");
const creditCardList = document.querySelector("#creditCardList");
const archivedCreditCardList = document.querySelector("#archivedCreditCardList");
const cancelCreditCardEditButton = document.querySelector("#cancelCreditCardEditButton");
const cardInvoiceCard = document.querySelector("#cardInvoiceCard");
const cardInvoiceMonthLabel = document.querySelector("#cardInvoiceMonthLabel");
const previousCardInvoiceButton = document.querySelector("#previousCardInvoiceButton");
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
const cardTransactionForm = document.querySelector("#cardTransactionForm");
const cardTransactionFormTitle = document.querySelector("#cardTransactionFormTitle");
const cardTransactionType = document.querySelector("#cardTransactionType");
const cardTransactionCategory = document.querySelector("#cardTransactionCategory");
const cardTransactionSubcategory = document.querySelector("#cardTransactionSubcategory");
const cardSeriesKind = document.querySelector("#cardSeriesKind");
const cardInstallmentCount = document.querySelector("#cardInstallmentCount");
const cardInstallmentCountLabel = document.querySelector("#cardInstallmentCountLabel");
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
const portfolioMarketList = document.querySelector("#portfolioMarketList");
const portfolioTypeList = document.querySelector("#portfolioTypeList");
const portfolioIndexerList = document.querySelector("#portfolioIndexerList");
const portfolioCurrencyList = document.querySelector("#portfolioCurrencyList");
const portfolioAccountList = document.querySelector("#portfolioAccountList");
const portfolioPositions = document.querySelector("#portfolioPositions");
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
const clearLaunchesForm = document.querySelector("#clearLaunchesForm");
const deleteUserForm = document.querySelector("#deleteUserForm");
const emailMessage = document.querySelector("#emailMessage");
const passwordMessage = document.querySelector("#passwordMessage");
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
const accountCount = document.querySelector("#accountCount");
const monthIncome = document.querySelector("#monthIncome");
const monthExpense = document.querySelector("#monthExpense");
const monthInvestment = document.querySelector("#monthInvestment");
const savingsRate = document.querySelector("#savingsRate");
const currencyList = document.querySelector("#currencyList");
const cockpitPortfolioByType = document.querySelector("#cockpitPortfolioByType");
const topExpensesChart = document.querySelector("#topExpensesChart");
const cashDistributionChart = document.querySelector("#cashDistributionChart");
const previousMonthButton = document.querySelector("#previousMonthButton");
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

loginTab.addEventListener("click", () => switchAuthMode("login"));
registerTab.addEventListener("click", () => switchAuthMode("register"));
loginForm.addEventListener("submit", handleLogin);
registerForm.addEventListener("submit", handleRegister);
passwordResetRequestForm.addEventListener("submit", handlePasswordResetRequest);
passwordResetConfirmForm.addEventListener("submit", handlePasswordResetConfirm);
forgotPasswordButton.addEventListener("click", () => switchAuthMode("reset-request"));
backToLoginFromRequest.addEventListener("click", () => switchAuthMode("login"));
backToLoginFromConfirm.addEventListener("click", () => switchAuthMode("login"));
accountForm.addEventListener("submit", handleAccountSubmit);
accountForm.elements.account_type.addEventListener("change", updateAccountTypeState);
creditCardForm.addEventListener("submit", handleCreditCardSubmit);
cardInvoiceCard.addEventListener("change", handleCardInvoiceCardChange);
previousCardInvoiceButton.addEventListener("click", () => shiftCardInvoiceMonth(-1));
nextCardInvoiceButton.addEventListener("click", () => shiftCardInvoiceMonth(1));
cardInvoicePaymentForm.addEventListener("submit", handleCardInvoicePaymentSubmit);
cardPaymentAccount.addEventListener("change", renderCardInvoice);
cardTransactionForm.addEventListener("submit", handleCardTransactionSubmit);
cardTransactionType.addEventListener("change", renderCardTransactionCategories);
cardTransactionCategory.addEventListener("change", renderCardTransactionSubcategories);
cardSeriesKind.addEventListener("change", updateCardSeriesState);
transactionForm.addEventListener("submit", handleTransactionSubmit);
categoryForm.addEventListener("submit", handleCategorySubmit);
categoryGroup.addEventListener("change", handleCategoryGroupChange);
subcategoryForm.addEventListener("submit", handleSubcategorySubmit);
tagForm.addEventListener("submit", handleTagSubmit);
limitForm.addEventListener("submit", handleLimitSubmit);
limitCategory.addEventListener("change", renderLimitSubcategories);
importForm.addEventListener("submit", handleImportSubmit);
importTarget.addEventListener("change", renderImportTargets);
downloadImportTemplateButton.addEventListener("click", downloadImportTemplate);
emailForm.addEventListener("submit", handleEmailSubmit);
passwordForm.addEventListener("submit", handlePasswordSubmit);
clearLaunchesForm.addEventListener("submit", handleClearLaunchesSubmit);
deleteUserForm.addEventListener("submit", handleDeleteUserSubmit);
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
seriesKind.addEventListener("change", updateSeriesState);
transactionForm.elements.date.addEventListener("change", updateExchangeRateState);
transactionForm.elements.date.addEventListener("change", updateTransferExchangeRateState);
transactionForm.elements.amount.addEventListener("input", updateDestinationAmountFromRate);
transferExchangeRate.addEventListener("input", updateDestinationAmountFromRate);
previousMonthButton.addEventListener("click", () => shiftTransactionMonth(-1));
nextMonthButton.addEventListener("click", () => shiftTransactionMonth(1));
previousLimitMonthButton.addEventListener("click", () => shiftLimitMonth(-1));
nextLimitMonthButton.addEventListener("click", () => shiftLimitMonth(1));
previousReportMonthButton.addEventListener("click", () => shiftReportMonth(-1));
nextReportMonthButton.addEventListener("click", () => shiftReportMonth(1));
reportTabs.forEach((button) => button.addEventListener("click", () => switchReportTab(button.dataset.reportTab)));
reportAccountSelect.addEventListener("change", () => {
  state.reportAccountId = reportAccountSelect.value;
  renderReports();
});
addPortfolioAssetButton.addEventListener("click", showPortfolioAssetForm);
refreshPortfolioButton.addEventListener("click", () => loadPortfolio({ refreshMessage: true }));
portfolioAssetForm.addEventListener("submit", handlePortfolioAssetSubmit);
portfolioAssetType.addEventListener("change", updatePortfolioAssetTypeState);
portfolioFixedIncomeSubtype.addEventListener("change", syncPortfolioFixedIncomeSubtype);
cancelPortfolioAssetButton.addEventListener("click", resetPortfolioAssetForm);
deletePortfolioAssetButton.addEventListener("click", deletePortfolioAsset);
portfolioGroupFilter.addEventListener("change", () => {
  state.portfolioGroup = portfolioGroupFilter.value;
  renderPortfolio();
});
transactionSearch.addEventListener("input", renderTransactions);
logoutButton.addEventListener("click", handleLogout);
cancelEditButton.addEventListener("click", resetAccountForm);
cancelTransactionEditButton.addEventListener("click", resetTransactionForm);
cancelCreditCardEditButton.addEventListener("click", resetCreditCardForm);
cancelCardTransactionEditButton.addEventListener("click", resetCardTransactionForm);
cancelLimitEditButton.addEventListener("click", resetLimitForm);
navButtons.forEach((button) => button.addEventListener("click", () => showModule(button.dataset.view)));

updateAccountTypeState();
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

function switchAuthMode(mode) {
  const isLogin = mode === "login";
  const isRegister = mode === "register";
  const isResetRequest = mode === "reset-request";
  const isResetConfirm = mode === "reset-confirm";
  loginTab.classList.toggle("active", isLogin);
  registerTab.classList.toggle("active", isRegister);
  loginForm.hidden = !isLogin;
  registerForm.hidden = !isRegister;
  passwordResetRequestForm.hidden = !isResetRequest;
  passwordResetConfirmForm.hidden = !isResetConfirm;
  setMessage(authMessage, "");
}

async function handleLogin(event) {
  event.preventDefault();
  setMessage(authMessage, "");
  const data = formData(loginForm);
  setFormBusy(loginForm, true);
  try {
    const response = await api("/api/login", { method: "POST", body: data });
    state.user = response.user;
    await loadDashboard();
  } catch (error) {
    setMessage(authMessage, error.message, "error");
  } finally {
    setFormBusy(loginForm, false);
  }
}

async function handleRegister(event) {
  event.preventDefault();
  setMessage(authMessage, "");
  const data = formData(registerForm);
  setFormBusy(registerForm, true);
  try {
    const response = await api("/api/register", { method: "POST", body: data });
    state.user = response.user;
    await loadDashboard();
  } catch (error) {
    setMessage(authMessage, error.message, "error");
  } finally {
    setFormBusy(registerForm, false);
  }
}

async function handlePasswordResetRequest(event) {
  event.preventDefault();
  setMessage(authMessage, "");
  const data = formData(passwordResetRequestForm);
  setFormBusy(passwordResetRequestForm, true);
  try {
    const response = await api("/api/password-reset/request", {
      method: "POST",
      body: data,
    });
    passwordResetConfirmForm.elements.token.value = "";
    switchAuthMode("reset-confirm");
    const message = `Se o email existir, o codigo de recuperacao sera enviado. Ele expira em ${response.expires_in_minutes} minutos.`;
    setMessage(authMessage, message, "success");
  } catch (error) {
    setMessage(authMessage, error.message, "error");
  } finally {
    setFormBusy(passwordResetRequestForm, false);
  }
}

async function handlePasswordResetConfirm(event) {
  event.preventDefault();
  setMessage(authMessage, "");
  const data = formData(passwordResetConfirmForm);
  setFormBusy(passwordResetConfirmForm, true);
  try {
    await api("/api/password-reset/confirm", {
      method: "POST",
      body: data,
    });
    passwordResetRequestForm.reset();
    passwordResetConfirmForm.reset();
    switchAuthMode("login");
    setMessage(authMessage, "Senha redefinida. Entre com a nova senha.", "success");
  } catch (error) {
    setMessage(authMessage, error.message, "error");
  } finally {
    setFormBusy(passwordResetConfirmForm, false);
  }
}

async function handleLogout() {
  await api("/api/logout", { method: "POST" });
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
  state.categories = [];
  state.tags = [];
  state.spendingLimits = [];
  state.portfolio = null;
  loginForm.reset();
  registerForm.reset();
  resetAccountForm();
  resetCreditCardForm();
  resetCardTransactionForm();
  resetTransactionForm();
  showAuth();
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
    const [accountsResponse, creditCardsResponse, transactionsResponse, cardTransactionsResponse, cardPaymentsResponse] = await Promise.all([
      api("/api/checking-accounts"),
      api("/api/credit-cards"),
      api("/api/transactions"),
      api("/api/credit-card-transactions"),
      api("/api/credit-card-payments"),
    ]);
    state.accounts = accountsResponse.accounts;
    state.creditCards = creditCardsResponse.cards;
    ensureSelectedCreditCard();
    state.transactions = transactionsResponse.transactions;
    state.cardTransactions = cardTransactionsResponse.transactions;
    state.cardPayments = cardPaymentsResponse.payments || [];
    await loadArchivedAccounts();
    await loadArchivedCreditCards();
    await loadClassifications();
    await loadSpendingLimits();
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
    state.categories = [];
    state.tags = [];
    state.spendingLimits = [];
    state.portfolio = null;
    setMessage(accountMessage, error.message, "error");
  }
  renderAll();
}

async function loadAccounts() {
  const response = await api("/api/checking-accounts");
  state.accounts = response.accounts;
  await loadArchivedAccounts();
  markPortfolioDirty();
  renderAll();
}

async function loadCreditCards() {
  const response = await api("/api/credit-cards");
  state.creditCards = response.cards;
  ensureSelectedCreditCard();
  await loadArchivedCreditCards();
  await loadCardTransactions();
  await loadCardInvoice();
  renderAll();
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
  const [accountsResponse, creditCardsResponse, transactionsResponse, cardTransactionsResponse, cardPaymentsResponse] = await Promise.all([
    api("/api/checking-accounts"),
    api("/api/credit-cards"),
    api("/api/transactions"),
    api("/api/credit-card-transactions"),
    api("/api/credit-card-payments"),
  ]);
  state.accounts = accountsResponse.accounts;
  state.creditCards = creditCardsResponse.cards;
  ensureSelectedCreditCard();
  state.transactions = transactionsResponse.transactions;
  state.cardTransactions = cardTransactionsResponse.transactions;
  state.cardPayments = cardPaymentsResponse.payments || [];
  await loadArchivedAccounts();
  await loadArchivedCreditCards();
  await loadClassifications();
  await loadSpendingLimits();
  await loadCardInvoice();
  markPortfolioDirty();
  renderAll();
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
    state.portfolio = await api("/api/portfolio");
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
  setMessage(portfolioMessage, "");
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
  }
}

function showPortfolioAssetForm() {
  portfolioAssetForm.elements.id.value = "";
  portfolioAssetFormTitle.textContent = "Ativo em carteira";
  deletePortfolioAssetButton.hidden = true;
  renderPortfolioAssetAccounts();
  portfolioAssetFormPanel.hidden = false;
  if (!portfolioAssetForm.elements.acquisition_date.value) {
    portfolioAssetForm.elements.acquisition_date.value = new Date().toISOString().slice(0, 10);
  }
  updatePortfolioAssetTypeState();
  portfolioAssetFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetPortfolioAssetForm() {
  portfolioAssetForm.reset();
  portfolioAssetForm.elements.id.value = "";
  portfolioAssetFormTitle.textContent = "Ativo em carteira";
  deletePortfolioAssetButton.hidden = true;
  portfolioAssetForm.elements.acquisition_date.value = new Date().toISOString().slice(0, 10);
  portfolioAssetFormPanel.hidden = true;
  updatePortfolioAssetTypeState();
}

function editPortfolioPosition(position) {
  if (position.source_type !== "opening" || !position.source_id) {
    setMessage(portfolioMessage, "Edite esta posição pelo lançamento de origem.", "error");
    return;
  }
  renderPortfolioAssetAccounts();
  portfolioAssetForm.reset();
  portfolioAssetForm.elements.id.value = position.source_id;
  portfolioAssetForm.elements.account_id.value = position.account_id;
  portfolioAssetForm.elements.acquisition_date.value = position.first_operation_date || new Date().toISOString().slice(0, 10);
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
  const transaction = state.transactions.find((entry) => String(entry.id) === String(transactionId));
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
  const rawDate = window.prompt("Data do resgate", new Date().toISOString().slice(0, 10));
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
  if (assetType === "fixed_income") {
    portfolioAssetIdentifierLabel.hidden = true;
    const matchedSubtype = [...portfolioFixedIncomeSubtype.options].find((option) => option.value === portfolioAssetIdentifier.value);
    portfolioFixedIncomeSubtype.value = matchedSubtype ? matchedSubtype.value : "";
  } else {
    portfolioAssetIdentifierLabel.hidden = false;
    portfolioAssetIdentifierLabel.childNodes[0].textContent = "Ativo ";
    portfolioAssetIdentifier.placeholder = "Ex.: PETR4, IVVB11, BTC";
    portfolioFixedIncomeSubtype.value = "";
  }
}

function syncPortfolioFixedIncomeSubtype() {
  if (portfolioAssetType.value === "fixed_income" && portfolioFixedIncomeSubtype.value) {
    portfolioAssetIdentifier.value = portfolioFixedIncomeSubtype.value;
  }
}

async function loadClassifications() {
  const [categoriesResponse, tagsResponse] = await Promise.all([
    api("/api/categories"),
    api("/api/tags"),
  ]);
  state.categories = categoriesResponse.categories;
  state.tags = tagsResponse.tags;
  renderTransactionTagOptions();
}

async function loadSpendingLimits() {
  const response = await api(`/api/spending-limits?month=${encodeURIComponent(state.limitMonth)}`);
  state.spendingLimits = response.limits;
}

async function loadCardInvoice() {
  if (!state.selectedCreditCardId) {
    state.cardInvoiceTransactions = [];
    state.cardInvoicePayments = [];
    return;
  }
  const response = await api(`/api/credit-card-invoice?card_id=${encodeURIComponent(state.selectedCreditCardId)}&month=${encodeURIComponent(state.cardInvoiceMonth)}`);
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
  moduleEyebrow.textContent = viewTitles[view][0];
  pageTitle.textContent = viewTitles[view][1];
  if (view === "transactions") {
    ensureSelectedAccount();
    renderTransactionAccounts();
    updateTransactionTypeState();
    renderTransactions();
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
  try {
    await api(isEditing ? `/api/credit-card-transactions/${data.id}` : "/api/credit-card-transactions", {
      method: isEditing ? "PUT" : "POST",
      body: data,
    });
    resetCardTransactionForm();
    await loadCardInvoice();
    await loadCardTransactions();
    renderCreditCards();
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
      data.apply_to_future = window.confirm("Replicar esta alteração nos próximos lançamentos recorrentes desta série?");
    }
    await api(isEditing ? `/api/transactions/${data.id}` : "/api/transactions", {
      method: isEditing ? "PUT" : "POST",
      body: data,
    });
    resetTransactionForm();
    await loadTransactionsAndAccounts();
    setMessage(transactionMessage, isEditing ? "Lançamento atualizado." : "Lançamento salvo.", "success");
  } catch (error) {
    setMessage(transactionMessage, error.message, "error");
  } finally {
    setFormBusy(transactionForm, false);
  }
}

function shouldAskFutureReplication(transactionId) {
  const transaction = state.transactions.find((entry) => String(entry.id) === String(transactionId));
  return Boolean(transaction && transaction.series_id && transaction.series_kind === "recurring");
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

async function handleCategorySubmit(event) {
  event.preventDefault();
  categoryForm.elements.group_type.value = categoryGroup.value;
  await createClassification("categories", categoryForm, categoryMessage);
  categoryForm.elements.group_type.value = categoryGroup.value;
}

function handleCategoryGroupChange() {
  categoryForm.elements.group_type.value = categoryGroup.value;
  setMessage(categoryMessage, "");
  renderClassifications();
}

async function handleSubcategorySubmit(event) {
  event.preventDefault();
  setMessage(categoryMessage, "");
  if (filteredClassificationCategories().length === 0) {
    setMessage(categoryMessage, "Cadastre uma categoria antes de adicionar subcategorias.", "error");
    return;
  }
  try {
    await api("/api/subcategories", { method: "POST", body: formData(subcategoryForm) });
    subcategoryForm.elements.name.value = "";
    await loadClassifications();
    renderClassifications();
    setMessage(categoryMessage, "Subcategoria salva.", "success");
  } catch (error) {
    setMessage(categoryMessage, error.message, "error");
  }
}

async function handleTagSubmit(event) {
  event.preventDefault();
  await createClassification("tags", tagForm, tagMessage);
}

async function handleLimitSubmit(event) {
  event.preventDefault();
  setMessage(limitMessage, "");
  const data = formData(limitForm);
  data.month = state.limitMonth;
  const isEditing = Boolean(data.id);
  try {
    await api(isEditing ? `/api/spending-limits/${data.id}` : "/api/spending-limits", {
      method: isEditing ? "PUT" : "POST",
      body: data,
    });
    resetLimitForm();
    await loadSpendingLimits();
    renderLimits();
    setMessage(limitMessage, "Limite salvo.", "success");
  } catch (error) {
    setMessage(limitMessage, error.message, "error");
  }
}

function editSpendingLimit(limit) {
  limitFormTitle.textContent = "Editar limite";
  limitForm.elements.id.value = limit.id;
  limitForm.elements.limit_amount.value = limit.limit_amount.replace(".", ",");
  limitForm.elements.notes.value = limit.notes || "";
  limitCategory.value = String(limit.category_id);
  renderLimitSubcategories();
  limitSubcategory.value = limit.subcategory_id ? String(limit.subcategory_id) : "";
  cancelLimitEditButton.hidden = false;
  limitForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function deleteSpendingLimit(id) {
  try {
    await api(`/api/spending-limits/${id}`, { method: "DELETE" });
    await loadSpendingLimits();
    renderLimits();
    setMessage(limitMessage, "Limite excluído.", "success");
  } catch (error) {
    setMessage(limitMessage, error.message, "error");
  }
}

function resetLimitForm() {
  limitForm.reset();
  limitForm.elements.id.value = "";
  limitFormTitle.textContent = "Novo limite";
  cancelLimitEditButton.hidden = true;
  limitMonthInput.value = state.limitMonth;
  renderLimitCategories();
  setMessage(limitMessage, "");
}

async function createClassification(type, form, messageElement) {
  setMessage(messageElement, "");
  try {
    await api(`/api/${type}`, { method: "POST", body: formData(form) });
    form.reset();
    await loadClassifications();
    renderClassifications();
    setMessage(messageElement, "Item salvo.", "success");
  } catch (error) {
    setMessage(messageElement, error.message, "error");
  }
}

async function renameClassification(type, item) {
  const label = type === "categories" ? "categoria" : "tag";
  const name = window.prompt(`Renomear ${label}`, item.name);
  if (name === null) {
    return;
  }
  try {
    await api(`/api/${type}/${item.id}`, { method: "PUT", body: { name } });
    await loadClassifications();
    renderClassifications();
  } catch (error) {
    setMessage(type === "categories" ? categoryMessage : tagMessage, error.message, "error");
  }
}

async function deleteClassification(type, item) {
  const messageElement = type === "categories" ? categoryMessage : tagMessage;
  setMessage(messageElement, "");
  try {
    await api(`/api/${type}/${item.id}`, { method: "DELETE" });
    await loadClassifications();
    renderClassifications();
    setMessage(messageElement, "Item excluído.", "success");
  } catch (error) {
    setMessage(messageElement, error.message, "error");
  }
}

async function renameSubcategory(item) {
  const name = window.prompt("Renomear subcategoria", item.name);
  if (name === null) {
    return;
  }
  try {
    await api(`/api/subcategories/${item.id}`, { method: "PUT", body: { name } });
    await loadClassifications();
    renderClassifications();
  } catch (error) {
    setMessage(categoryMessage, error.message, "error");
  }
}

async function deleteSubcategory(item) {
  setMessage(categoryMessage, "");
  try {
    await api(`/api/subcategories/${item.id}`, { method: "DELETE" });
    await loadClassifications();
    renderClassifications();
    setMessage(categoryMessage, "Subcategoria excluída.", "success");
  } catch (error) {
    setMessage(categoryMessage, error.message, "error");
  }
}

async function handleEmailSubmit(event) {
  event.preventDefault();
  setMessage(emailMessage, "");
  try {
    const response = await api("/api/me/email", { method: "POST", body: formData(emailForm) });
    state.user = response.user;
    userName.textContent = state.user.name;
    emailForm.elements.current_password.value = "";
    setMessage(emailMessage, "Email atualizado.", "success");
  } catch (error) {
    setMessage(emailMessage, error.message, "error");
  }
}

async function handlePasswordSubmit(event) {
  event.preventDefault();
  setMessage(passwordMessage, "");
  try {
    await api("/api/me/password", { method: "POST", body: formData(passwordForm) });
    passwordForm.reset();
    setMessage(passwordMessage, "Senha atualizada.", "success");
  } catch (error) {
    setMessage(passwordMessage, error.message, "error");
  }
}

async function handleClearLaunchesSubmit(event) {
  event.preventDefault();
  setMessage(clearLaunchesMessage, "");
  const data = formData(clearLaunchesForm);
  if (data.confirm_clear !== "yes") {
    setMessage(clearLaunchesMessage, "Confirme que entende a exclusao dos lancamentos.", "error");
    return;
  }
  try {
    await api("/api/me/clear-launches", { method: "POST", body: { current_password: data.current_password } });
    clearLaunchesForm.reset();
    state.selectedAccountId = "";
    state.transactions = [];
    state.cardTransactions = [];
    state.cardPayments = [];
    state.cardInvoiceTransactions = [];
    state.cardInvoicePayments = [];
    state.portfolio = null;
    await loadAll();
    setMessage(clearLaunchesMessage, "Lançamentos apagados. Categorias, subcategorias e tags foram preservadas.", "success");
  } catch (error) {
    setMessage(clearLaunchesMessage, error.message, "error");
  }
}

async function handleDeleteUserSubmit(event) {
  event.preventDefault();
  setMessage(deleteUserMessage, "");
  const data = formData(deleteUserForm);
  if (data.confirm_delete !== "yes") {
    setMessage(deleteUserMessage, "Confirme que entende a exclusao permanente dos dados.", "error");
    return;
  }
  try {
    await api("/api/me", { method: "DELETE", body: { current_password: data.current_password } });
    state.user = null;
    state.accounts = [];
    state.archivedAccounts = [];
    state.creditCards = [];
    state.archivedCreditCards = [];
    state.transactions = [];
    state.cardTransactions = [];
    state.cardPayments = [];
    state.cardInvoiceTransactions = [];
    state.cardInvoicePayments = [];
    state.categories = [];
    state.tags = [];
    deleteUserForm.reset();
    showAuth();
  } catch (error) {
    setMessage(deleteUserMessage, error.message, "error");
  }
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
    await api(`/api/credit-card-transactions/${id}`, { method: "DELETE" });
    await loadCardInvoice();
    await loadCardTransactions();
    renderCreditCards();
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
  } catch (error) {
    setMessage(cardInvoiceMessage, error.message, "error");
  }
}

async function deleteTransaction(id) {
  try {
    await api(`/api/transactions/${id}`, { method: "DELETE" });
    await loadTransactionsAndAccounts();
    setMessage(transactionMessage, "Lançamento excluído.", "success");
  } catch (error) {
    setMessage(transactionMessage, error.message, "error");
  }
}

async function toggleTransactionReconciliation(id, reconciled) {
  try {
    await api(`/api/transactions/${id}/reconciliation`, {
      method: "PUT",
      body: { reconciled },
    });
    await loadTransactionsAndAccounts();
    renderTransactions();
  } catch (error) {
    setMessage(transactionMessage, error.message, "error");
  }
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
  setMessage(creditCardMessage, "");
}

function resetCardTransactionForm() {
  cardTransactionForm.reset();
  cardTransactionForm.elements.id.value = "";
  cardTransactionForm.elements.date.value = new Date().toISOString().slice(0, 10);
  cardTransactionForm.elements.credit_card_id.value = state.selectedCreditCardId;
  cardTransactionForm.elements.invoice_month.value = state.cardInvoiceMonth;
  cardSeriesKind.disabled = false;
  cardInstallmentCount.disabled = false;
  cardSeriesKind.value = "single";
  cardInstallmentCount.value = "2";
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
  transactionForm.elements.date.value = new Date().toISOString().slice(0, 10);
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
  seriesKind.value = "single";
  seriesKind.disabled = true;
  updateSeriesState();
  updateTransactionTypeState();
  applyWalletAccountRestrictions();
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
  cardSeriesKind.value = transaction.series_kind || "single";
  cardInstallmentCount.value = transaction.installment_count || "2";
  cardSeriesKind.disabled = true;
  cardInstallmentCount.disabled = true;
  updateCardSeriesState();
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
  cardInstallmentCountLabel.hidden = !isInstallment;
  cardInstallmentCount.disabled = !isInstallment;
}

function renderAll() {
  renderCockpit();
  renderAccounts();
  renderCreditCards();
  renderTransactionAccounts();
  renderImportTargets();
  renderPortfolioAssetAccounts();
  renderTransactionCategories();
  renderTransactions();
  renderClassifications();
  renderLimits();
  renderReports();
  renderPortfolio();
}

function renderCockpit() {
  const totals = getCurrencyTotals();
  const monthTotals = getCurrentMonthTotals();
  accountCount.textContent = String(state.accounts.length);
  monthIncome.textContent = formatMoney(monthTotals.income, "BRL");
  monthExpense.textContent = formatMoney(monthTotals.expense, "BRL");
  monthInvestment.textContent = formatMoney(monthTotals.investment, "BRL");
  savingsRate.textContent = formatPercent(monthTotals.savingsRate);
  renderCurrencyTotals(totals);
  renderCockpitPortfolioByType();
  renderMonthlyPlanning();
  renderInstallmentDebts();
  renderTopExpensesChart();
  renderCashDistributionChart(monthTotals);
}

function renderMonthlyPlanning() {
  const prefix = new Date().toISOString().slice(0, 7);
  const sections = [
    ["Receitas recorrentes", (transaction) => transaction.type === "income" && transaction.series_kind === "recurring"],
    ["Investimentos planejados", (transaction) => isInvestmentTransaction(transaction) && transaction.series_kind !== "single"],
    ["Despesas recorrentes", (transaction) => transaction.type === "expense" && transaction.series_kind === "recurring"],
  ];
  monthlyPlanningList.innerHTML = "";
  for (const [title, predicate] of sections) {
    monthlyPlanningList.append(planningSection(title, state.transactions.filter((transaction) => (
      transaction.date.startsWith(prefix) && predicate(transaction)
    ))));
  }
}

function planningSection(title, transactions) {
  const section = document.createElement("section");
  section.className = "planning-section";
  const grouped = groupTransactionsByCategory(transactions);
  const rows = grouped.length
    ? grouped.map((item) => `
      <div class="planning-row">
        <span>${escapeHtml(item.label)}</span>
        <strong>${formatMoney(item.total, "BRL")}</strong>
      </div>
    `).join("")
    : '<div class="empty-state compact">Nada previsto neste mês.</div>';
  section.innerHTML = `<h3>${title}</h3>${rows}`;
  return section;
}

function renderInstallmentDebts() {
  if (!installmentDebtList) {
    return;
  }
  const currentMonth = new Date().toISOString().slice(0, 7);
  const rows = new Map();
  for (const transaction of state.transactions) {
    if (transaction.series_kind !== "installment" || transaction.type !== "expense" || transaction.date.slice(0, 7) < currentMonth) {
      continue;
    }
    const key = `account:${transaction.account_id}`;
    const row = rows.get(key) || { label: transaction.account_name || "Conta", detail: "Conta", currency: transaction.account_currency || "BRL", total: 0, count: 0 };
    row.total += Number(transaction.amount || 0);
    row.count += 1;
    rows.set(key, row);
  }
  for (const transaction of state.cardTransactions) {
    if (transaction.series_kind !== "installment" || transaction.type !== "expense" || transaction.invoice_month < currentMonth) {
      continue;
    }
    const key = `card:${transaction.credit_card_id}`;
    const row = rows.get(key) || { label: transaction.credit_card_name || "Cartão", detail: "Cartão", currency: transaction.card_currency || "BRL", total: 0, count: 0 };
    row.total += Number(transaction.amount || 0);
    row.count += 1;
    rows.set(key, row);
  }
  const debts = [...rows.values()].sort((a, b) => b.total - a.total);
  if (debts.length === 0) {
    installmentDebtList.innerHTML = '<section class="planning-section"><div class="empty-state compact">Nenhuma compra parcelada em aberto.</div></section>';
    return;
  }
  installmentDebtList.innerHTML = `
    <section class="planning-section">
      ${debts.map((row) => `
        <div class="planning-row">
          <div>
            <strong>${escapeHtml(row.label)}</strong>
            <span>${escapeHtml(row.detail)} · ${row.count} parcela(s) restante(s)</span>
          </div>
          <strong>${formatMoney(row.total, row.currency)}</strong>
        </div>
      `).join("")}
    </section>
  `;
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
  const prefix = new Date().toISOString().slice(0, 7);
  const grouped = groupTransactionsByCategory(state.transactions.filter((transaction) => (
    transaction.date.startsWith(prefix) && transaction.type === "expense"
  ))).slice(0, 6);
  renderDonutListChart(topExpensesChart, grouped, {
    empty: "Nenhuma despesa neste mês.",
    totalLabel: "Despesas",
  });
}

function renderCashDistributionChart(monthTotals) {
  const items = [
    { label: "Despesas", total: monthTotals.expense },
    { label: "Investimentos", total: monthTotals.investment },
  ];
  const remainder = Math.max(monthTotals.income - monthTotals.expense - monthTotals.investment, 0);
  if (remainder > 0) {
    items.push({ label: "Não alocado", total: remainder });
  }
  renderDonutListChart(cashDistributionChart, items.filter((item) => item.total > 0), {
    empty: "Sem receitas no mês para distribuir.",
    total: monthTotals.income,
    totalLabel: "Receitas",
  });
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
  renderCardInvoiceList(card);
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
  const accounts = card
    ? state.accounts.filter((account) => account.currency === card.currency)
    : [];
  cardPaymentAccount.innerHTML = accounts.map((account) => (
    `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
  )).join("") || '<option value="">Cadastre uma conta compatível</option>';
  cardPaymentAccount.disabled = accounts.length === 0;
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
      <div>
        <strong>${escapeHtml(transaction.description)}</strong>
        <div class="account-meta">
          <span>${formatDate(transaction.date)}</span>
          <span>${cardTransactionTypeLabel(transaction.type)}</span>
          ${transactionSeriesLabel(transaction) ? `<span>${transactionSeriesLabel(transaction)}</span>` : ""}
          ${transaction.category_name ? `<span>${escapeHtml(cardCategoryPath(transaction))}</span>` : ""}
        </div>
      </div>
      <div class="transaction-amount">
        <strong>${sign}${formatMoney(transaction.amount, card.currency)}</strong>
        ${state.cardInvoicePayments.length ? "" : `
          <div class="transaction-actions">
            <button class="ghost small-button" type="button" data-card-edit-id="${transaction.id}">Editar</button>
            <button class="reconcile-button ${isReconciled ? "active" : ""}" type="button" data-card-reconcile-id="${transaction.id}" data-reconciled="${isReconciled}" title="${isReconciled ? "Desmarcar conciliação" : "Marcar como conciliado"}">OK</button>
            <button class="danger small-button" type="button" data-card-transaction-id="${transaction.id}">Excluir</button>
          </div>
        `}
      </div>
    `;
    const reconcileButton = item.querySelector("[data-card-reconcile-id]");
    const editButton = item.querySelector("[data-card-edit-id]");
    if (editButton) {
      editButton.addEventListener("click", () => editCardTransaction(transaction));
    }
    if (reconcileButton) {
      reconcileButton.addEventListener("click", () => toggleCardTransactionReconciliation(
        reconcileButton.dataset.cardReconcileId,
        reconcileButton.dataset.reconciled !== "true",
      ));
    }
    const deleteButton = item.querySelector("[data-card-transaction-id]");
    if (deleteButton) {
      deleteButton.addEventListener("click", () => deleteCardTransaction(transaction.id));
    }
    cardInvoiceList.append(item);
  });
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
  portfolioAssetForm.querySelector('button[type="submit"]').disabled = portfolioAccounts.length === 0;
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
  const accountTransactions = selectedAccountTransactions();
  
  const monthTransactions = selectedAccountVisibleTransactions(accountTransactions)
    .filter((transaction) => transaction.date.startsWith(state.transactionMonth))
    .filter(matchesTransactionSearch);
  
  // Calculate balances considering only the filtered transactions
  // Saldo Atual: apenas lançamentos conciliados até hoje
  currentBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(new Date().toISOString().slice(0, 10), accountTransactions, true));
  // Saldo Previsto: todos os lançamentos até o fim do mês
  forecastBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(monthEndDate(state.transactionMonth), accountTransactions, false));
  
  renderTransactionCollection(transactionList, monthTransactions, false);
}

function selectedAccountTransactions(transactions = state.transactions) {
  if (!state.selectedAccountId) {
    return [];
  }
  return transactions.filter((transaction) => (
    String(transaction.account_id) === String(state.selectedAccountId)
    || String(transaction.destination_account_id || "") === String(state.selectedAccountId)
  ));
}

function selectedAccountVisibleTransactions(transactions = state.transactions) {
  if (!state.selectedAccountId) {
    return [];
  }
  return selectedAccountTransactions(transactions).filter((transaction) => (
    !isExchangeTransfer(transaction)
    || String(transaction.destination_account_id || "") === String(state.selectedAccountId)
  ));
}

function renderClassifications() {
  renderSubcategoryOptions();
  renderClassificationList(categoryList, filteredClassificationCategories(), "categories");
  renderClassificationList(tagList, state.tags, "tags");
}

function renderLimits() {
  limitMonthLabel.textContent = formatMonthLabel(state.limitMonth);
  limitMonthInput.value = state.limitMonth;
  renderLimitCategories();
  renderSpendingLimitList();
}

function renderReports() {
  reportMonthLabel.textContent = formatMonthLabel(state.reportMonth);
  reportTabs.forEach((button) => button.classList.toggle("active", button.dataset.reportTab === state.reportTab));
  renderReportAccountOptions();
  const items = reportItemsForMonth(state.reportMonth);
  const totals = reportTotals(items);
  reportIncomeSummary.textContent = formatMoney(totals.income, "BRL");
  reportExpenseSummary.textContent = formatMoney(totals.expense, "BRL");
  reportInvestmentSummary.textContent = formatMoney(totals.investment, "BRL");
  reportResultSummary.textContent = formatMoney(totals.income - totals.expense - totals.investment, "BRL");
  reportResultSummary.classList.toggle("danger-text", totals.income - totals.expense - totals.investment < 0);
  reportAccountFilter.hidden = state.reportTab !== "accounts";
  if (state.reportTab === "cashflow") {
    renderCashflowReport(items);
    return;
  }
  if (state.reportTab === "accounts") {
    renderAccountsReport();
    return;
  }
  if (state.reportTab === "tags") {
    renderTagsReport(items);
    return;
  }
  renderCategoriesReport(items);
}

function renderReportAccountOptions() {
  const options = state.accounts.map((account) => (
    `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
  )).join("");
  reportAccountSelect.innerHTML = options || '<option value="">Cadastre uma conta</option>';
  reportAccountSelect.disabled = state.accounts.length === 0;
  if (!state.accounts.some((account) => String(account.id) === String(state.reportAccountId))) {
    state.reportAccountId = state.accounts[0] ? String(state.accounts[0].id) : "";
  }
  reportAccountSelect.value = state.reportAccountId;
}

function renderCategoriesReport(items) {
  const sections = [
    ["Despesas", "expense"],
    ["Receitas", "income"],
    ["Investimentos", "investment"],
  ];
  reportContent.innerHTML = sections.map(([title, type]) => (
    reportRankedSection(title, groupReportItems(items.filter((item) => item.reportType === type), "category"), `Nenhum item em ${title.toLowerCase()} neste mês.`)
  )).join("");
}

function renderTagsReport(items) {
  const taggedItems = [];
  for (const item of items) {
    for (const tag of item.tags) {
      taggedItems.push({ ...item, tag });
    }
  }
  const sections = [
    ["Despesas", "expense"],
    ["Receitas", "income"],
    ["Investimentos", "investment"],
  ];
  reportContent.innerHTML = sections.map(([title, type]) => (
    reportRankedSection(title, groupReportItems(taggedItems.filter((item) => item.reportType === type), "tag"), `Nenhuma tag em ${title.toLowerCase()} neste mês.`)
  )).join("");
}

function renderCashflowReport(items) {
  const rows = monthDayRows(state.reportMonth).map((dateKey) => {
    const dayItems = items.filter((item) => item.date === dateKey);
    const income = sumReportItems(dayItems, "income");
    const expense = sumReportItems(dayItems, "expense");
    const investment = sumReportItems(dayItems, "investment");
    return {
      date: dateKey,
      income,
      expense,
      investment,
      result: income - expense - investment,
    };
  });
  let running = 0;
  const body = rows.map((row) => {
    running += row.result;
    return `
      <tr>
        <td>${formatDate(row.date)}</td>
        <td class="money-cell positive-text">${formatMoney(row.income, "BRL")}</td>
        <td class="money-cell negative-text">${formatMoney(row.expense, "BRL")}</td>
        <td class="money-cell neutral-text">${formatMoney(row.investment, "BRL")}</td>
        <td class="money-cell ${row.result < 0 ? "negative-text" : "positive-text"}">${formatMoney(row.result, "BRL")}</td>
        <td class="money-cell">${formatMoney(running, "BRL")}</td>
      </tr>
    `;
  }).join("");
  reportContent.innerHTML = `
    <div class="report-table-wrap">
      <table class="report-table">
        <thead>
          <tr>
            <th>Dia</th>
            <th>Entradas</th>
            <th>Despesas</th>
            <th>Aportes</th>
            <th>Resultado</th>
            <th>Saldo do mês</th>
          </tr>
        </thead>
        <tbody>${body}</tbody>
      </table>
    </div>
  `;
}

function renderAccountsReport() {
  const account = state.accounts.find((entry) => String(entry.id) === String(state.reportAccountId));
  if (!account) {
    reportContent.innerHTML = '<div class="empty-state">Cadastre uma conta para visualizar este relatório.</div>';
    return;
  }
  const items = state.transactions
    .filter((transaction) => transaction.date.startsWith(state.reportMonth))
    .filter((transaction) => String(transaction.account_id) === String(account.id));
  const reportItems = items.map(accountTransactionReportItem).filter(Boolean);
  const totals = reportTotals(reportItems);
  const rows = groupReportItems(reportItems, "category");
  reportContent.innerHTML = `
    <div class="account-report-header">
      <div>
        <span>Conta selecionada</span>
        <strong>${escapeHtml(account.name)}</strong>
      </div>
      <div>
        <span>Receitas</span>
        <strong>${formatMoney(totals.income, "BRL")}</strong>
      </div>
      <div>
        <span>Saídas</span>
        <strong>${formatMoney(totals.expense + totals.investment, "BRL")}</strong>
      </div>
      <div>
        <span>Resultado</span>
        <strong>${formatMoney(totals.income - totals.expense - totals.investment, "BRL")}</strong>
      </div>
    </div>
    ${reportRankedSection("Movimentação por categoria", rows, "Nenhum lançamento nesta conta no mês.")}
  `;
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
    portfolioMarketList.innerHTML = "";
    portfolioTypeList.innerHTML = "";
    portfolioIndexerList.innerHTML = "";
    portfolioCurrencyList.innerHTML = "";
    portfolioAccountList.innerHTML = "";
    portfolioPositions.innerHTML = '<div class="empty-state">Nenhuma posição de investimento encontrada.</div>';
    return;
  }
  const summary = portfolio.summary;
  const result = Number(summary.result_brl);
  const dayResult = Number(summary.day_result_brl);
  portfolioCostSummary.textContent = formatMoney(summary.total_cost_brl, "BRL");
  portfolioCurrentSummary.textContent = formatMoney(summary.current_value_brl, "BRL");
  portfolioResultSummary.textContent = formatMoney(summary.result_brl, "BRL");
  portfolioResultSummary.classList.toggle("danger-text", result < 0);
  portfolioResultSummary.classList.toggle("positive-text", result > 0);
  portfolioReturnSummary.textContent = `${Number(summary.result_percent).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  portfolioReturnSummary.classList.toggle("danger-text", result < 0);
  portfolioReturnSummary.classList.toggle("positive-text", result > 0);
  portfolioDayResultSummary.textContent = `${formatMoney(summary.day_result_brl, "BRL")} · ${Number(summary.day_result_percent).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  portfolioDayResultSummary.classList.toggle("danger-text", dayResult < 0);
  portfolioDayResultSummary.classList.toggle("positive-text", dayResult > 0);
  portfolioPositionCount.textContent = String(summary.position_count || 0);
  renderPortfolioGroupList(portfolioMarketList, summary.by_market);
  renderPortfolioGroupList(portfolioTypeList, summary.by_type);
  renderPortfolioGroupList(portfolioIndexerList, summary.by_indexer);
  renderPortfolioGroupList(portfolioCurrencyList, summary.by_currency);
  renderPortfolioGroupList(portfolioAccountList, summary.by_account);
  renderPortfolioPositions(portfolio.positions || []);
}

function renderPortfolioGroupList(container, rows) {
  if (!rows || rows.length === 0) {
    container.innerHTML = '<div class="empty-state compact">Sem dados para consolidar.</div>';
    return;
  }
  const total = rows.reduce((sum, row) => sum + Number(row.current_brl), 0);
  container.innerHTML = rows.map((row, index) => {
    const current = Number(row.current_brl);
    const result = Number(row.result_brl);
    const percent = total > 0 ? current / total : 0;
    return `
      <article class="portfolio-group-row">
        <div>
          <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
          <span>${row.count} posição(ões)</span>
        </div>
        <div>
          <strong>${formatMoney(row.current_brl, "BRL")}</strong>
          <span class="${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(row.result_brl, "BRL")} · ${Number(row.result_percent).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%</span>
        </div>
        <div class="report-bar"><span style="width:${Math.max(percent * 100, 2)}%; background:${chartColor(index)}"></span></div>
      </article>
    `;
  }).join("");
}

function renderPortfolioPositions(positions) {
  if (positions.length === 0) {
    portfolioPositions.innerHTML = '<div class="empty-state">Lance uma compra de investimento para formar o portfólio.</div>';
    return;
  }
  const grouped = groupPortfolioPositions(positions);
  portfolioPositions.innerHTML = grouped.map((group) => `
    ${group.label ? `<h3 class="portfolio-group-title">${escapeHtml(group.label)}</h3>` : ""}
    <div class="report-table-wrap">
      <table class="report-table portfolio-table">
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
  `).join("");
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
    const position = positions.find((entry) => String(entry.source_id) === String(button.dataset.editPortfolioPositionId));
    button.addEventListener("click", () => editPortfolioPosition(position));
  });
  portfolioPositions.querySelectorAll("[data-edit-portfolio-transaction-id]").forEach((button) => {
    button.addEventListener("click", () => editPortfolioSourceTransaction(button.dataset.editPortfolioTransactionId));
  });
  portfolioPositions.querySelectorAll("[data-redeem-portfolio-payload]").forEach((button) => {
    button.addEventListener("click", () => redeemPortfolioPosition(JSON.parse(button.dataset.redeemPortfolioPayload)));
  });
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
    .map(([label, groupPositions]) => ({ label, positions: groupPositions }));
}

function portfolioPositionRows(positions) {
  return portfolioAssetGroups(positions).flatMap((group) => {
    if (group.positions.length === 1) {
      return [portfolioPositionRow(group.positions[0])];
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
  const identifier = position.asset_identifier || position.asset_name || "Sem codigo";
  const assetName = position.asset_name || identifier;
  const rowLabel = options.parent ? assetName : options.child ? options.childLabel : identifier;
  const assetDetail = [
    options.parent ? `${options.childCount} lançamentos` : "",
    options.parent && position.asset_identifier && position.asset_identifier !== assetName ? position.asset_identifier : "",
    options.child ? identifier : "",
    options.child ? formatDate(position.first_operation_date) : "",
    !options.parent && !options.child && position.asset_name && position.asset_name !== identifier ? position.asset_name : "",
    position.cnpj ? `CNPJ ${position.cnpj}` : "",
    position.fixed_income_indexer ? `${position.fixed_income_indexer}${position.fixed_income_rate ? ` · ${position.fixed_income_rate}%` : ""}` : "",
    position.fixed_income_maturity_date ? `Venc. ${formatDate(position.fixed_income_maturity_date)}` : "",
  ].filter(Boolean).join(" · ");
  const toggle = options.parent
    ? `<button class="portfolio-toggle" type="button" data-toggle-portfolio-group="${escapeHtml(options.groupKey)}" aria-label="${options.expanded ? "Recolher" : "Abrir"} ${escapeHtml(identifier)}">${options.expanded ? "-" : "+"}</button>`
    : options.child ? '<span class="portfolio-child-marker"></span>' : "";
  const fixedIncomeIof = Number(position.fixed_income_iof_tax || 0);
  const fixedIncomeTax = Number(position.fixed_income_income_tax || 0);
  const hasFixedIncomeTax = position.asset_type === "fixed_income" && (fixedIncomeIof > 0 || fixedIncomeTax > 0);
  const valueDetail = hasFixedIncomeTax
    ? `<span>Bruto ${formatMoney(position.fixed_income_gross_value || position.current_value, position.currency)}</span>${fixedIncomeIof > 0 ? `<span>IOF estimado -${formatMoney(position.fixed_income_iof_tax, position.currency)}</span>` : ""}<span>IR estimado -${formatMoney(position.fixed_income_income_tax, position.currency)}</span><span>Líquido ${formatMoney(position.fixed_income_net_value, position.currency)}</span>`
    : `<span>${formatMoney(position.current_value_brl, "BRL")}</span>`;
  const actions = position.source_type === "opening" && position.source_id
    ? `<button class="ghost small-button" type="button" data-edit-portfolio-position-id="${position.source_id}">Editar</button>`
    : position.source_type === "operation" && position.source_transaction_id
      ? `<button class="ghost small-button" type="button" data-edit-portfolio-transaction-id="${position.source_transaction_id}">Editar lançamento</button>`
      : `<span class="muted-row">Múltiplas origens</span>`;
  const redeemAction = `<button class="ghost small-button" type="button" data-redeem-portfolio-payload="${escapeHtml(JSON.stringify(portfolioRedemptionPayload(position)))}">Resgatar</button>`;
  return `
    <tr class="${options.parent ? "portfolio-parent-row" : ""} ${options.child ? "portfolio-child-row" : ""}">
      <td>
        <div class="portfolio-asset-name">${toggle}<strong>${escapeHtml(rowLabel)}</strong></div>
        <span>${escapeHtml(assetDetail || "Sem detalhe adicional")}</span>
      </td>
      <td>${escapeHtml(position.asset_type_label)}<span>${escapeHtml(position.market_label || "Brasil")}</span></td>
      <td>${escapeHtml(position.account_name)}<span>${escapeHtml(position.currency)}</span></td>
      <td class="money-cell">${formatDecimal(position.quantity, 6)}</td>
      <td class="money-cell">${formatMoney(position.average_price, position.currency)}</td>
      <td class="money-cell">${formatMoney(position.total_cost, position.currency)}<span>${formatMoney(position.total_cost_brl, "BRL")}</span></td>
      <td class="money-cell">${quoteText}<span>${escapeHtml(quoteStatus || "Pendente")}</span></td>
      <td class="money-cell">${formatMoney(position.current_value_cents / 100, position.currency)}${valueDetail}</td>
      <td class="money-cell ${dayResult < 0 ? "danger-text" : "positive-text"}">${formatMoney(position.day_result_brl, "BRL")}<span>${formatPercent(dayPercent)}</span></td>
      <td class="money-cell ${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(result, "BRL")}<span>${formatPercent(resultPercent)}</span></td>
      <td>${redeemAction}${actions}</td>
    </tr>
  `;
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

function reportRankedSection(title, rows, emptyText) {
  const total = rows.reduce((sum, row) => sum + row.total, 0);
  const content = rows.length ? rows.map((row, index) => {
    const percent = total > 0 ? row.total / total : 0;
    return `
      <article class="report-rank-row">
        <div>
          <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
          <span>${row.count} lançamento(s)</span>
        </div>
        <div class="report-rank-value">
          <strong>${formatMoney(row.total, "BRL")}</strong>
          <span>${formatPercent(percent)}</span>
        </div>
        <div class="report-bar"><span style="width:${Math.max(percent * 100, 2)}%; background:${chartColor(index)}"></span></div>
      </article>
    `;
  }).join("") : `<div class="empty-state compact">${emptyText}</div>`;
  return `
    <section class="report-section">
      <div class="section-heading">
        <h2>${escapeHtml(title)}</h2>
        <strong>${formatMoney(total, "BRL")}</strong>
      </div>
      <div class="report-rank-list">${content}</div>
    </section>
  `;
}

function reportItemsForMonth(month) {
  const accountItems = state.transactions
    .filter((transaction) => transaction.date.startsWith(month))
    .map(accountTransactionReportItem)
    .filter(Boolean);
  const cardItems = state.cardTransactions
    .filter((transaction) => transaction.date.startsWith(month))
    .map(cardTransactionReportItem)
    .filter(Boolean);
  return [...accountItems, ...cardItems];
}

function accountTransactionReportItem(transaction) {
  const reportType = isInvestmentTransaction(transaction)
    ? "investment"
    : transaction.type === "income" || transaction.type === "expense"
      ? transaction.type
      : "";
  if (!reportType) {
    return null;
  }
  return {
    date: transaction.date,
    reportType,
    amount: Number(transaction.amount_brl || transaction.amount),
    category: transaction.category_name || "Sem categoria",
    subcategory: transaction.subcategory_name || "",
    tag: "",
    tags: Array.isArray(transaction.tags) ? transaction.tags : transaction.tag_name ? [transaction.tag_name] : [],
    accountId: transaction.account_id,
    accountName: transaction.account_name,
    source: "Conta",
  };
}

function cardTransactionReportItem(transaction) {
  if (transaction.type !== "income" && transaction.type !== "expense") {
    return null;
  }
  return {
    date: transaction.date,
    reportType: transaction.type,
    amount: Number(transaction.amount),
    category: transaction.category_name || "Sem categoria",
    subcategory: transaction.subcategory_name || "",
    tag: "",
    tags: [],
    accountId: "",
    accountName: transaction.credit_card_name || "Cartão",
    source: "Cartão",
  };
}

function reportTotals(items) {
  return items.reduce((totals, item) => {
    totals[item.reportType] += item.amount;
    return totals;
  }, { income: 0, expense: 0, investment: 0 });
}

function groupReportItems(items, key) {
  const grouped = new Map();
  for (const item of items) {
    const label = key === "tag" ? item.tag : item.category;
    if (!label) {
      continue;
    }
    const current = grouped.get(label) || { label, total: 0, count: 0 };
    current.total += item.amount;
    current.count += 1;
    grouped.set(label, current);
  }
  return [...grouped.values()].sort((a, b) => b.total - a.total || a.label.localeCompare(b.label));
}

function sumReportItems(items, type) {
  return items.reduce((total, item) => item.reportType === type ? total + item.amount : total, 0);
}

function monthDayRows(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  const lastDay = new Date(year, monthNumber, 0).getDate();
  return Array.from({ length: lastDay }, (_, index) => (
    `${year}-${String(monthNumber).padStart(2, "0")}-${String(index + 1).padStart(2, "0")}`
  ));
}

function renderLimitCategories() {
  const selectedCategory = limitCategory.value;
  const expenseCategories = state.categories.filter((category) => category.group_type === "expense");
  limitCategory.innerHTML = expenseCategories.map((category) => (
    `<option value="${category.id}">${escapeHtml(category.name)}</option>`
  )).join("") || '<option value="">Cadastre uma categoria de despesa</option>';
  if (expenseCategories.some((category) => String(category.id) === selectedCategory)) {
    limitCategory.value = selectedCategory;
  }
  limitCategory.disabled = expenseCategories.length === 0;
  limitForm.querySelector('button[type="submit"]').disabled = expenseCategories.length === 0;
  renderLimitSubcategories();
}

function renderLimitSubcategories() {
  const category = state.categories.find((entry) => String(entry.id) === limitCategory.value);
  const subcategories = category ? category.subcategories || [] : [];
  const selectedSubcategory = limitSubcategory.value;
  limitSubcategory.innerHTML = '<option value="">Categoria inteira</option>' + subcategories.map((subcategory) => (
    `<option value="${subcategory.id}">${escapeHtml(subcategory.name)}</option>`
  )).join("");
  if (subcategories.some((subcategory) => String(subcategory.id) === selectedSubcategory)) {
    limitSubcategory.value = selectedSubcategory;
  }
  limitSubcategory.disabled = subcategories.length === 0;
}

function renderSpendingLimitList() {
  spendingLimitList.innerHTML = "";
  const rows = spendingLimitRows();
  renderLimitSummary(rows);
  if (rows.length === 0) {
    spendingLimitList.append(emptyState("Nenhum limite definido para este mês."));
    return;
  }
  rows.forEach((row) => {
    const item = document.createElement("article");
    item.className = `spending-limit-item ${row.percent > 1 ? "over-limit" : ""}`;
    item.innerHTML = `
      <div class="limit-item-main">
        <div>
          <strong>${escapeHtml(row.categoryLabel)}</strong>
          ${row.subcategoryLabel ? `<small class="limit-subcategory">${escapeHtml(row.subcategoryLabel)}</small>` : '<small class="limit-subcategory">Categoria inteira</small>'}
          <span>${formatMoney(row.spent, "BRL")} de ${formatMoney(row.limit, "BRL")}</span>
        </div>
        <strong>${formatPercent(row.percent)}</strong>
      </div>
      <div class="limit-progress" aria-label="${escapeHtml(row.label)} consumido">
        <span style="width:${Math.min(row.percent * 100, 100)}%"></span>
      </div>
      <div class="limit-item-footer">
        <span>${row.remaining >= 0 ? "Disponível" : "Excedido"}: ${formatMoney(Math.abs(row.remaining), "BRL")}</span>
        <div class="card-actions">
          <button class="ghost small-button" type="button" data-action="edit">Editar</button>
          <button class="danger small-button" type="button" data-action="delete">Excluir</button>
        </div>
      </div>
    `;
    item.querySelector('[data-action="edit"]').addEventListener("click", () => editSpendingLimit(row.limitRecord));
    item.querySelector('[data-action="delete"]').addEventListener("click", () => deleteSpendingLimit(row.limitRecord.id));
    spendingLimitList.append(item);
  });
}

function renderLimitSummary(rows) {
  const totals = rows.reduce((summary, row) => {
    summary.spent += row.spent;
    summary.limit += row.limit;
    return summary;
  }, { spent: 0, limit: 0 });
  limitConsumedSummary.textContent = formatMoney(totals.spent, "BRL");
  limitDefinedSummary.textContent = formatMoney(totals.limit, "BRL");
  limitAvailableSummary.textContent = formatMoney(totals.limit - totals.spent, "BRL");
  limitAvailableSummary.classList.toggle("danger-text", totals.spent > totals.limit && totals.limit > 0);
}

function spendingLimitRows() {
  return state.spendingLimits.map((limit) => {
    const spent = spentForLimit(limit);
    const limitAmount = Number(limit.limit_amount);
    return {
      limitRecord: limit,
      label: limit.subcategory_name ? `${limit.category_name} / ${limit.subcategory_name}` : limit.category_name,
      categoryLabel: limit.category_name,
      subcategoryLabel: limit.subcategory_name || "",
      spent,
      limit: limitAmount,
      percent: limitAmount > 0 ? spent / limitAmount : 0,
      remaining: limitAmount - spent,
    };
  }).sort((a, b) => b.percent - a.percent || b.spent - a.spent);
}

function spentForLimit(limit) {
  return state.transactions.reduce((total, transaction) => {
    if (transaction.type !== "expense" || !transaction.date.startsWith(limit.month)) {
      return total;
    }
    if (String(transaction.category_id) !== String(limit.category_id)) {
      return total;
    }
    if (limit.subcategory_id && String(transaction.subcategory_id) !== String(limit.subcategory_id)) {
      return total;
    }
    return total + Number(transaction.amount_brl || transaction.amount);
  }, 0);
}

function renderSubcategoryOptions() {
  const categories = filteredClassificationCategories();
  const options = categories.map((category) => (
    `<option value="${category.id}">${escapeHtml(category.name)}</option>`
  )).join("");
  subcategoryCategory.innerHTML = options || '<option value="">Cadastre uma categoria neste grupo</option>';
  subcategoryForm.querySelector('button[type="submit"]').disabled = categories.length === 0;
}

function filteredClassificationCategories() {
  return state.categories.filter((category) => category.group_type === categoryGroup.value);
}

function renderClassificationList(container, items, type) {
  container.innerHTML = "";
  if (items.length === 0) {
    container.append(emptyState(type === "categories" ? "Nenhuma categoria cadastrada." : "Nenhuma tag cadastrada."));
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("article");
    row.className = "classification-item";
    const subcategories = type === "categories" ? item.subcategories || [] : [];
    row.innerHTML = `
      <div>
        <strong>${escapeHtml(item.name)}</strong>
        <span>${type === "categories" ? `${classificationGroupLabel(item.group_type)} · ` : ""}${item.transaction_count} lançamento(s)</span>
      </div>
      <div class="card-actions">
        <button class="ghost small-button" type="button" data-action="rename">Renomear</button>
        <button class="danger small-button" type="button" data-action="delete">Excluir</button>
      </div>
      ${subcategories.length ? `
        <div class="subcategory-list">
          ${subcategories.map((subcategory) => `
            <div class="subcategory-item" data-subcategory-id="${subcategory.id}">
              <span>${escapeHtml(subcategory.name)} · ${subcategory.transaction_count} lançamento(s)</span>
              <div class="card-actions">
                <button class="ghost small-button" type="button" data-action="rename-subcategory">Renomear</button>
                <button class="danger small-button" type="button" data-action="delete-subcategory">Excluir</button>
              </div>
            </div>
          `).join("")}
        </div>
      ` : ""}
    `;
    row.querySelector('[data-action="rename"]').addEventListener("click", () => renameClassification(type, item));
    row.querySelector('[data-action="delete"]').addEventListener("click", () => deleteClassification(type, item));
    row.querySelectorAll("[data-subcategory-id]").forEach((element) => {
      const subcategory = subcategories.find((entry) => String(entry.id) === element.dataset.subcategoryId);
      element.querySelector('[data-action="rename-subcategory"]').addEventListener("click", () => renameSubcategory(subcategory));
      element.querySelector('[data-action="delete-subcategory"]').addEventListener("click", () => deleteSubcategory(subcategory));
    });
    container.append(row);
  });
}

function renderTransactionCollection(container, transactions, compact) {
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
      group.querySelectorAll("[data-transaction-id]").forEach((button) => {
        button.addEventListener("click", () => deleteTransaction(button.dataset.transactionId));
      });
      group.querySelectorAll("[data-edit-transaction-id]").forEach((button) => {
        const transaction = items.find((entry) => String(entry.id) === String(button.dataset.editTransactionId));
        button.addEventListener("click", () => editTransaction(transaction));
      });
      group.querySelectorAll("[data-reconcile-id]").forEach((button) => {
        button.addEventListener("click", () => toggleTransactionReconciliation(
          button.dataset.reconcileId,
          button.dataset.reconciled !== "true",
        ));
      });
    }
    if (!compact) {
      group.append(dailyBalance(dateKey));
    }
    container.append(group);
  }
  
  // Add subtotal lines at the end: Current Balance (Reconciled) and Forecast Balance
  if (!compact) {
    const today = new Date().toISOString().slice(0, 10);
    const monthEnd = monthEndDate(state.transactionMonth);
    
    const relevantTransactions = selectedAccountTransactions(state.transactions).filter((transaction) => transaction.date <= monthEnd);
    
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
            <button class="ghost small-button" type="button" data-edit-transaction-id="${transaction.id}">Editar</button>
            <button class="reconcile-button ${isReconciled ? "active" : ""}" type="button" data-reconcile-id="${transaction.id}" data-reconciled="${isReconciled}" title="${isReconciled ? "Desmarcar conciliação" : "Marcar como conciliado"}">OK</button>
            <button class="danger small-button" type="button" data-transaction-id="${transaction.id}">Excluir</button>
          </div>
        `}
      </div>
    </article>
  `;
}

function dailyBalance(dateKey) {
  const row = document.createElement("div");
  row.className = "daily-balance";
  row.innerHTML = `
    <span>Saldo no dia</span>
    <strong>${formatCurrencySummary(getBalanceUntil(dateKey))}</strong>
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

function handleTransactionAccountChange() {
  const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
  if (account) {
    state.selectedAccountId = account.id;
  }
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
  investmentFundFields.hidden = !isInvestment || cat !== "Fundos de Investimentos";
  investmentFixedFields.hidden = !isInvestment || cat !== "Renda Fixa";
  for (const field of investmentOperationFields.querySelectorAll("input, select")) {
    field.disabled = !isInvestment;
  }
  investmentAmount.required = isInvestment;
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
  state.transactionMonth = shiftMonth(state.transactionMonth, delta);
  renderTransactions();
}

async function shiftLimitMonth(delta) {
  state.limitMonth = shiftMonth(state.limitMonth, delta);
  resetLimitForm();
  await loadSpendingLimits();
  renderLimits();
}

function shiftReportMonth(delta) {
  state.reportMonth = shiftMonth(state.reportMonth, delta);
  renderReports();
}

function switchReportTab(tab) {
  state.reportTab = tab;
  renderReports();
}

async function shiftCardInvoiceMonth(delta) {
  state.cardInvoiceMonth = shiftMonth(state.cardInvoiceMonth, delta);
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
  const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
  const currency = account ? account.currency : "BRL";
  const isBrl = currency === "BRL";
  exchangeRateLabel.hidden = isBrl;
  exchangeRate.disabled = isBrl;
  if (isBrl) {
    exchangeRate.value = "1,000000";
    return;
  }
  if (!transactionForm.elements.date.value) {
    return;
  }
  exchangeRate.placeholder = "Buscando cotação...";
  try {
    const response = await api(`/api/exchange-rate?currency=${encodeURIComponent(currency)}&date=${encodeURIComponent(transactionForm.elements.date.value)}`);
    exchangeRate.value = response.rate.replace(".", ",");
  } catch (error) {
    exchangeRate.value = "";
    exchangeRate.placeholder = "Informe a cotação manual";
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

function parseDecimalInput(value) {
  const normalized = String(value || "").replace(/\./g, "").replace(",", ".");
  const parsed = Number(normalized);
  return Number.isFinite(parsed) ? parsed : 0;
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
  const reconciledTotals = getBalanceUntil(currentMonthEndDate(), state.transactions, true);
  for (const account of state.accounts) {
    const row = currencyTotalRow(totals, account.currency);
    const amount = Number(account.current_balance);
    row.current += amount;
    row.accounts.push({
      id: account.id,
      name: account.name,
      type: accountTypeLabel(account.account_type),
      amount,
    });
  }
  for (const card of state.creditCards) {
    const row = currencyTotalRow(totals, card.currency);
    const openAmount = cardOpenBalance(card.id);
    const signedAmount = -openAmount;
    row.current += signedAmount;
    row.cards.push({
      id: card.id,
      name: card.name,
      issuer: card.issuer,
      amount: signedAmount,
    });
  }
  for (const [currency, amount] of reconciledTotals.entries()) {
    currencyTotalRow(totals, currency).reconciled = amount;
  }
  for (const card of state.creditCards) {
    const row = currencyTotalRow(totals, card.currency);
    row.reconciled -= cardReconciledBalance(card.id);
  }
  return new Map([...totals.entries()].sort(([currencyA], [currencyB]) => currencyA.localeCompare(currencyB)));
}

function currencyTotalRow(totals, currency) {
  const normalizedCurrency = currency || "BRL";
  if (!totals.has(normalizedCurrency)) {
    totals.set(normalizedCurrency, {
      current: 0,
      reconciled: 0,
      accounts: [],
      cards: [],
    });
  }
  return totals.get(normalizedCurrency);
}

function currentMonthEndDate() {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return `${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, "0")}-${String(end.getDate()).padStart(2, "0")}`;
}

function cardReconciledBalance(cardId) {
  const currentMonth = new Date().toISOString().slice(0, 7);
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

function cardOpenBalance(cardId) {
  const transactionTotal = state.cardTransactions.reduce((total, transaction) => {
    if (String(transaction.credit_card_id) !== String(cardId)) {
      return total;
    }
    const amount = Number(transaction.amount);
    return total + (transaction.type === "expense" ? amount : -amount);
  }, 0);
  const paidTotal = state.cardPayments.reduce((total, payment) => (
    String(payment.credit_card_id) === String(cardId) ? total + Number(payment.amount) : total
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
    const item = document.createElement("div");
    item.className = "currency-item";
    const accountRows = amounts.accounts.map((account) => currencyDetailRow(
      account.name,
      account.type,
      account.amount,
      currency,
    )).join("");
    const cardRows = amounts.cards.map((card) => currencyDetailRow(
      card.name,
      card.issuer ? `Cartão · ${card.issuer}` : "Cartão",
      card.amount,
      currency,
      "card",
    )).join("");
    item.innerHTML = `
      <span>${escapeHtml(currency)} (Previsto)</span>
      <strong>${formatMoney(amounts.current, currency)}</strong>
      <div class="currency-breakdown">
        ${accountRows || '<span class="muted-row">Nenhuma conta ativa nesta moeda.</span>'}
        ${cardRows ? `<div class="currency-section-label">Cartões</div>${cardRows}` : ""}
        <div class="currency-section-label">Saldo conciliado do mês</div>
        ${currencyDetailRow("Consolidado", "Contas e cartões conciliados", amounts.reconciled, currency)}
      </div>
    `;
    currencyList.append(item);
  }
}

function currencyDetailRow(name, detail, amount, currency, kind = "account") {
  const amountClass = amount < 0 ? "danger-text" : amount > 0 ? "positive-text" : "";
  return `
    <div class="currency-detail-row ${kind}">
      <span>
        <b>${escapeHtml(name)}</b>
        <em>${escapeHtml(detail)}</em>
      </span>
      <strong class="${amountClass}">${formatMoney(amount, currency)}</strong>
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
  const total = rows.reduce((sum, row) => sum + Number(row.current_brl || 0), 0);
  cockpitPortfolioByType.innerHTML = rows.map((row, index) => {
    const current = Number(row.current_brl || 0);
    const result = Number(row.result_brl || 0);
    const percent = total > 0 ? current / total : 0;
    return `
      <article class="portfolio-cockpit-row">
        <div>
          <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
          <span>${row.count} posição(ões) · ${formatPercent(percent)}</span>
        </div>
        <div>
          <strong>${formatMoney(current, "BRL")}</strong>
          <span class="${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(result, "BRL")}</span>
        </div>
      </article>
    `;
  }).join("");
}

function showAuth() {
  authView.hidden = false;
  dashboardView.hidden = true;
  switchAuthMode("login");
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

async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      method: options.method || "GET",
      headers: options.body ? { "Content-Type": "application/json" } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    throw new Error(`Nao foi possivel falar com o servidor local. Abra pelo endereco ${window.location.origin}.`);
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Algo nao saiu como esperado.");
  }
  return payload;
}

async function upload(path, body) {
  let response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      method: "POST",
      body,
    });
  } catch (error) {
    throw new Error(`Nao foi possivel falar com o servidor local. Abra pelo endereco ${window.location.origin}.`);
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Algo nao saiu como esperado.");
  }
  return payload;
}

function setFormBusy(form, busy) {
  const button = form.querySelector('button[type="submit"]');
  if (button && !button.dataset.label) {
    button.dataset.label = button.textContent;
  }
  for (const element of form.elements) {
    element.disabled = busy;
  }
  if (button) {
    button.textContent = busy ? "Aguarde..." : button.dataset.label;
  }
}

function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

function setMessage(element, text, tone = "") {
  element.textContent = text;
  element.className = `message ${tone}`.trim();
}

function emptyState(text, compact = false) {
  const empty = document.createElement("div");
  empty.className = compact ? "empty-state compact" : "empty-state";
  empty.textContent = text;
  return empty;
}

function transactionTypeLabel(type) {
  return {
    income: "Receita",
    expense: "Despesa",
    transfer: "Transferência",
    investment: "Investimento",
  }[type] || type;
}

function cardTransactionTypeLabel(type) {
  return {
    income: "Receita",
    expense: "Despesa",
  }[type] || type;
}

function accountTypeLabel(type) {
  return {
    liquidity: "Liquidez",
    wallet: "Carteira",
    investment: "Investimento",
  }[type] || "Liquidez";
}

function classificationGroupLabel(type) {
  return {
    income: "Receitas",
    expense: "Despesas",
    investment: "Investimentos",
  }[type] || "Despesas";
}

function isInvestmentTransfer(transaction) {
  return transaction.type === "transfer" && transaction.destination_account_type === "investment";
}

function isInvestmentTransaction(transaction) {
  return transaction.type === "investment" || isInvestmentTransfer(transaction);
}

function isExchangeTransfer(transaction) {
  return transaction.type === "transfer"
    && transaction.destination_account_id
    && transaction.destination_account_currency
    && transaction.account_currency !== transaction.destination_account_currency;
}

function formatCategoryPath(transaction) {
  if (!transaction.category_name) {
    return "Sem categoria";
  }
  if (!transaction.subcategory_name) {
    return transaction.category_name;
  }
  return `${transaction.category_name} / ${transaction.subcategory_name}`;
}

function cardCategoryPath(transaction) {
  if (!transaction.category_name) {
    return "Sem categoria";
  }
  if (!transaction.subcategory_name) {
    return transaction.category_name;
  }
  return `${transaction.category_name} / ${transaction.subcategory_name}`;
}

function formatMoney(value, currency) {
  const amount = Number(value);
  return amount.toLocaleString("pt-BR", { style: "currency", currency });
}

function portfolioQuoteText(position) {
  if (position.asset_type === "fixed_income") {
    return "-";
  }
  if (!position.quote) {
    return "-";
  }
  const quote = Number(position.quote);
  if (!Number.isFinite(quote)) {
    return "-";
  }
  return formatMoney(quote, position.currency);
}

function formatDecimal(value, maximumFractionDigits = 2) {
  return Number(value || 0).toLocaleString("pt-BR", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  });
}

function moneyInputValue(value) {
  return Number(value).toLocaleString("pt-BR", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
}

function formatPercent(value) {
  return Number(value).toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 1 });
}

function formatMonthLabel(value) {
  const [year, month] = value.split("-").map(Number);
  return new Date(year, month - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
}

function monthEndDate(value) {
  const [year, month] = value.split("-").map(Number);
  const date = new Date(year, month, 0);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

function formatCurrencySummary(totals) {
  if (!totals.size) {
    return formatMoney(0, "BRL");
  }
  return [...totals.entries()].map(([currency, amount]) => formatMoney(amount, currency)).join(" · ");
}

function shiftMonth(value, delta) {
  const [year, month] = value.split("-").map(Number);
  const date = new Date(year, month - 1 + delta, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function transactionSeriesLabel(transaction) {
  if (transaction.series_kind === "installment" && transaction.installment_index && transaction.installment_count) {
    return `Parcela ${transaction.installment_index}/${transaction.installment_count}`;
  }
  if (transaction.series_kind === "recurring") {
    return `Recorrente · ${recurrenceFrequencyLabel(transaction.recurrence_frequency)}`;
  }
  return "";
}

function recurrenceFrequencyLabel(frequency) {
  return {
    weekly: "Semanal",
    monthly: "Mensal",
    quarterly: "Trimestral",
    semiannual: "Semestral",
    annual: "Anual",
  }[frequency] || "Recorrente";
}

function formatDate(value) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function normalizeSearch(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
