const state = {
  user: null,
  accounts: [],
  archivedAccounts: [],
  creditCards: [],
  archivedCreditCards: [],
  cardInvoiceTransactions: [],
  cardInvoicePayments: [],
  cardTransactions: [],
  selectedCreditCardId: "",
  transactions: [],
  categories: [],
  tags: [],
  spendingLimits: [],
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
const cardInvoiceList = document.querySelector("#cardInvoiceList");
const cancelCardTransactionEditButton = document.querySelector("#cancelCardTransactionEditButton");
const transactionForm = document.querySelector("#transactionForm");
const transactionFormTitle = document.querySelector("#transactionFormTitle");
const transactionMessage = document.querySelector("#transactionMessage");
const transactionList = document.querySelector("#transactionList");
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
const importForm = document.querySelector("#importForm");
const importAccount = document.querySelector("#importAccount");
const importMessage = document.querySelector("#importMessage");
const importResult = document.querySelector("#importResult");
const emailForm = document.querySelector("#emailForm");
const passwordForm = document.querySelector("#passwordForm");
const deleteUserForm = document.querySelector("#deleteUserForm");
const emailMessage = document.querySelector("#emailMessage");
const passwordMessage = document.querySelector("#passwordMessage");
const deleteUserMessage = document.querySelector("#deleteUserMessage");
const monthlyPlanningList = document.querySelector("#monthlyPlanningList");
const transactionType = document.querySelector("#transactionType");
const transactionAccount = document.querySelector("#transactionAccount");
const destinationAccount = document.querySelector("#destinationAccount");
const destinationAccountLabel = document.querySelector("#destinationAccountLabel");
const transactionCategory = document.querySelector("#transactionCategory");
const transactionSubcategory = document.querySelector("#transactionSubcategory");
const seriesKind = document.querySelector("#seriesKind");
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
transactionForm.addEventListener("submit", handleTransactionSubmit);
categoryForm.addEventListener("submit", handleCategorySubmit);
categoryGroup.addEventListener("change", handleCategoryGroupChange);
subcategoryForm.addEventListener("submit", handleSubcategorySubmit);
tagForm.addEventListener("submit", handleTagSubmit);
limitForm.addEventListener("submit", handleLimitSubmit);
limitCategory.addEventListener("change", renderLimitSubcategories);
importForm.addEventListener("submit", handleImportSubmit);
emailForm.addEventListener("submit", handleEmailSubmit);
passwordForm.addEventListener("submit", handlePasswordSubmit);
deleteUserForm.addEventListener("submit", handleDeleteUserSubmit);
transactionType.addEventListener("change", updateTransactionTypeState);
transactionAccount.addEventListener("change", updateTransactionTypeState);
transactionCategory.addEventListener("change", renderTransactionSubcategories);
seriesKind.addEventListener("change", updateSeriesState);
transactionForm.elements.date.addEventListener("change", updateExchangeRateState);
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
  state.selectedCreditCardId = "";
  state.transactions = [];
  state.categories = [];
  state.tags = [];
  state.spendingLimits = [];
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
    const [accountsResponse, creditCardsResponse, transactionsResponse, cardTransactionsResponse] = await Promise.all([
      api("/api/checking-accounts"),
      api("/api/credit-cards"),
      api("/api/transactions"),
      api("/api/credit-card-transactions"),
    ]);
    state.accounts = accountsResponse.accounts;
    state.creditCards = creditCardsResponse.cards;
    ensureSelectedCreditCard();
    state.transactions = transactionsResponse.transactions;
    state.cardTransactions = cardTransactionsResponse.transactions;
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
    state.selectedCreditCardId = "";
    state.transactions = [];
    state.categories = [];
    state.tags = [];
    state.spendingLimits = [];
    setMessage(accountMessage, error.message, "error");
  }
  renderAll();
}

async function loadAccounts() {
  const response = await api("/api/checking-accounts");
  state.accounts = response.accounts;
  await loadArchivedAccounts();
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
  const [accountsResponse, creditCardsResponse, transactionsResponse, cardTransactionsResponse] = await Promise.all([
    api("/api/checking-accounts"),
    api("/api/credit-cards"),
    api("/api/transactions"),
    api("/api/credit-card-transactions"),
  ]);
  state.accounts = accountsResponse.accounts;
  state.creditCards = creditCardsResponse.cards;
  ensureSelectedCreditCard();
  state.transactions = transactionsResponse.transactions;
  state.cardTransactions = cardTransactionsResponse.transactions;
  await loadArchivedAccounts();
  await loadArchivedCreditCards();
  await loadClassifications();
  await loadSpendingLimits();
  await loadCardInvoice();
  renderAll();
}

async function loadClassifications() {
  const [categoriesResponse, tagsResponse] = await Promise.all([
    api("/api/categories"),
    api("/api/tags"),
  ]);
  state.categories = categoriesResponse.categories;
  state.tags = tagsResponse.tags;
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
  const response = await api("/api/credit-card-transactions");
  state.cardTransactions = response.transactions || [];
}

function ensureSelectedCreditCard() {
  if (state.creditCards.some((card) => String(card.id) === String(state.selectedCreditCardId))) {
    return;
  }
  state.selectedCreditCardId = state.creditCards[0] ? String(state.creditCards[0].id) : "";
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
    updateTransactionTypeState();
  }
  if (view === "limits") {
    renderLimits();
  }
  if (view === "reports") {
    renderReports();
  }
  if (view === "creditCards") {
    renderCreditCards();
  }
  if (view === "cardLaunches") {
    renderCardInvoice();
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
    if (data.type === "investment") {
      data.type = "transfer";
      data.tags = data.tags || "Investimento";
    }
    if (data.type !== "transfer") {
      delete data.destination_account_id;
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
  if (state.accounts.length === 0) {
    setMessage(importMessage, "Cadastre uma conta antes de importar lançamentos.", "error");
    return;
  }
  const data = new FormData(importForm);
  setFormBusy(importForm, true);
  try {
    const response = await upload("/api/import/organizze-transactions", data);
    importForm.reset();
    await loadTransactionsAndAccounts();
    renderImportResult(response);
    setMessage(importMessage, `${response.imported} lançamento(s) importado(s).`, "success");
  } catch (error) {
    setMessage(importMessage, error.message, "error");
  } finally {
    setFormBusy(importForm, false);
  }
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
    state.transactions = [];
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
  cardTransactionFormTitle.textContent = "Novo lançamento no cartão";
  cancelCardTransactionEditButton.hidden = true;
  cardTransactionForm.querySelector('button[type="submit"]').textContent = "Salvar lançamento";
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
  transactionFormTitle.textContent = "Novo lançamento";
  cancelTransactionEditButton.hidden = true;
  transactionForm.querySelector('button[type="submit"]').textContent = "Salvar lançamento";
  seriesKind.disabled = false;
  updateSeriesState();
  updateTransactionTypeState();
}

function editTransaction(transaction) {
  setMessage(transactionMessage, "");
  transactionForm.elements.id.value = transaction.id;
  transactionType.value = isInvestmentTransfer(transaction) ? "investment" : transaction.type;
  transactionForm.elements.date.value = transaction.date;
  transactionForm.elements.description.value = transaction.description;
  transactionForm.elements.amount.value = moneyInputValue(transaction.amount);
  transactionAccount.value = String(transaction.account_id);
  transactionForm.elements.notes.value = transaction.notes || "";
  transactionForm.elements.tags.value = (transaction.tags || []).join(", ");
  transactionForm.elements.exchange_rate_to_brl.value = (transaction.exchange_rate_to_brl || "1.000000").replace(".", ",");
  seriesKind.value = "single";
  seriesKind.disabled = true;
  updateSeriesState();
  updateTransactionTypeState();
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
  transactionFormTitle.textContent = "Editar lançamento";
  cancelTransactionEditButton.hidden = false;
  transactionForm.querySelector('button[type="submit"]').textContent = "Salvar alterações";
  transactionForm.scrollIntoView({ behavior: "smooth", block: "start" });
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

function renderAll() {
  renderCockpit();
  renderAccounts();
  renderCreditCards();
  renderTransactionAccounts();
  renderTransactionCategories();
  renderTransactions();
  renderClassifications();
  renderLimits();
  renderReports();
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
  renderMonthlyPlanning();
  renderTopExpensesChart();
  renderCashDistributionChart(monthTotals);
}

function renderMonthlyPlanning() {
  const prefix = new Date().toISOString().slice(0, 7);
  const sections = [
    ["Receitas recorrentes", (transaction) => transaction.type === "income" && transaction.series_kind === "recurring"],
    ["Investimentos planejados", (transaction) => isInvestmentTransfer(transaction) && transaction.series_kind !== "single"],
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
  card.innerHTML = `
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

function renderTransactionAccounts() {
  const options = state.accounts.map((account) => (
    `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
  )).join("");
  transactionAccount.innerHTML = options || '<option value="">Cadastre uma conta</option>';
  importAccount.innerHTML = options || '<option value="">Cadastre uma conta</option>';
  transactionForm.querySelector('button[type="submit"]').disabled = state.accounts.length === 0;
  importForm.querySelector('button[type="submit"]').disabled = state.accounts.length === 0;
  updateTransactionTypeState();
}

function renderTransactionCategories() {
  const groupType = selectedTransactionGroup();
  const categories = state.categories.filter((category) => category.group_type === groupType);
  transactionCategory.innerHTML = categories.map((category) => (
    `<option value="${escapeHtml(category.name)}" data-category-id="${category.id}">${escapeHtml(category.name)}</option>`
  )).join("") || '<option value="">Cadastre uma categoria para este grupo</option>';
  transactionCategory.disabled = categories.length === 0;
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

function renderTransactions() {
  transactionMonthLabel.textContent = formatMonthLabel(state.transactionMonth);
  currentBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(new Date().toISOString().slice(0, 10)));
  forecastBalanceSummary.textContent = formatCurrencySummary(getBalanceUntil(monthEndDate(state.transactionMonth)));
  const monthTransactions = state.transactions
    .filter((transaction) => transaction.date.startsWith(state.transactionMonth))
    .filter(matchesTransactionSearch);
  renderTransactionCollection(transactionList, monthTransactions, false);
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
  const reportType = isInvestmentTransfer(transaction)
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
          <strong>${escapeHtml(row.label)}</strong>
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
}

function transactionTemplate(transaction, compact) {
  const signal = transaction.type === "income" ? "positive" : transaction.type === "expense" ? "negative" : "neutral";
  const amountPrefix = transaction.type === "income" ? "" : transaction.type === "expense" ? "-" : "";
  const destination = transaction.destination_account_name ? ` para ${escapeHtml(transaction.destination_account_name)}` : "";
  const typeLabel = isInvestmentTransfer(transaction) ? "Investimento" : transactionTypeLabel(transaction.type);
  const isReconciled = Boolean(transaction.reconciled_at);
  const convertedAmount = transaction.account_currency === "BRL" ? "" : `
        <span>${formatMoney(transaction.amount_brl, "BRL")}</span>
      `;
  return `
    <article class="transaction-row ${signal}">
      <div>
        <strong>${escapeHtml(transaction.description)}</strong>
        <div class="account-meta">
          <span>${typeLabel}</span>
          <span>${escapeHtml(transaction.account_name)}${destination}</span>
          ${transactionSeriesLabel(transaction) ? `<span>${transactionSeriesLabel(transaction)}</span>` : ""}
          ${transaction.category_name ? `<span>${escapeHtml(formatCategoryPath(transaction))}</span>` : ""}
          ${transaction.tags && transaction.tags.length ? `<span>${transaction.tags.map((tag) => `#${escapeHtml(tag)}`).join(" ")}</span>` : ""}
        </div>
      </div>
      <div class="transaction-amount">
        <strong>${amountPrefix}${formatMoney(transaction.amount, transaction.account_currency)}</strong>
        ${convertedAmount}
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
  const isTransfer = transactionType.value === "transfer" || isInvestment;
  const destinationOptions = destinationAccountOptions(isInvestment);
  destinationAccount.innerHTML = destinationOptions || '<option value="">Cadastre uma conta compatível</option>';
  destinationAccountLabel.hidden = !isTransfer;
  destinationAccount.disabled = !isTransfer || !destinationOptions;
  if (isInvestment && !transactionForm.elements.tags.value.trim()) {
    transactionForm.elements.tags.value = "Investimento";
  }
  renderTransactionCategories();
  updateExchangeRateState();
}

function updateSeriesState() {
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
  if (transactionType.value === "investment") {
    return "investment";
  }
  return "expense";
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
    const current = totals.get(account.currency) || 0;
    totals.set(account.currency, current + Number(account.current_balance));
  }
  return new Map([...totals.entries()].sort(([currencyA], [currencyB]) => currencyA.localeCompare(currencyB)));
}

function getBalanceUntil(limitDate) {
  const totals = new Map();
  for (const account of state.accounts) {
    const current = totals.get(account.currency) || 0;
    totals.set(account.currency, current + Number(account.initial_balance));
  }
  for (const transaction of state.transactions) {
    if (transaction.date > limitDate) {
      continue;
    }
    const amount = Number(transaction.amount);
    const sourceCurrency = transaction.account_currency;
    totals.set(sourceCurrency, (totals.get(sourceCurrency) || 0) + transactionSourceDelta(transaction.type, amount));
    if (transaction.type === "transfer" && transaction.destination_account_id) {
      totals.set(sourceCurrency, (totals.get(sourceCurrency) || 0) + amount);
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
    if (isInvestmentTransfer(transaction)) {
      totals.investment += amountBrl;
    }
    return totals;
  }, { income: 0, expense: 0, investment: 0, get savingsRate() {
    return this.income > 0 ? this.investment / this.income : 0;
  } });
}

function destinationAccountOptions(investmentOnly) {
  const sourceAccount = state.accounts.find((account) => String(account.id) === transactionAccount.value);
  return state.accounts
    .filter((account) => String(account.id) !== transactionAccount.value)
    .filter((account) => !sourceAccount || account.currency === sourceAccount.currency)
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
  for (const [currency, amount] of totals.entries()) {
    const item = document.createElement("div");
    item.className = "currency-item";
    item.innerHTML = `
      <span>${escapeHtml(currency)}</span>
      <strong>${formatMoney(amount, currency)}</strong>
    `;
    currencyList.append(item);
  }
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
