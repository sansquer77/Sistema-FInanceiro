const state = {
  user: null,
  accounts: [],
  archivedAccounts: [],
  transactions: [],
  categories: [],
  tags: [],
  view: "cockpit",
  transactionMonth: new Date().toISOString().slice(0, 7),
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
const transactionForm = document.querySelector("#transactionForm");
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
  transactions: document.querySelector("#transactionsView"),
  classifications: document.querySelector("#classificationsView"),
  imports: document.querySelector("#importsView"),
  user: document.querySelector("#userView"),
};

const viewTitles = {
  cockpit: ["Cockpit", "Resumo financeiro"],
  accounts: ["Gestão de contas", "Contas"],
  transactions: ["Operação", "Lançamentos"],
  classifications: ["Classificação", "Categorias e tags"],
  imports: ["Dados", "Importação"],
  user: ["Segurança", "Usuário"],
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
transactionForm.addEventListener("submit", handleTransactionSubmit);
categoryForm.addEventListener("submit", handleCategorySubmit);
categoryGroup.addEventListener("change", handleCategoryGroupChange);
subcategoryForm.addEventListener("submit", handleSubcategorySubmit);
tagForm.addEventListener("submit", handleTagSubmit);
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
transactionSearch.addEventListener("input", renderTransactions);
logoutButton.addEventListener("click", handleLogout);
cancelEditButton.addEventListener("click", resetAccountForm);
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
  state.transactions = [];
  state.categories = [];
  state.tags = [];
  loginForm.reset();
  registerForm.reset();
  resetAccountForm();
  resetTransactionForm();
  showAuth();
}

async function loadDashboard() {
  userName.textContent = state.user.name;
  authView.hidden = true;
  dashboardView.hidden = false;
  resetTransactionForm();
  await loadAll();
  showModule(state.view);
}

async function loadAll() {
  try {
    const [accountsResponse, transactionsResponse] = await Promise.all([
      api("/api/checking-accounts"),
      api("/api/transactions"),
    ]);
    state.accounts = accountsResponse.accounts;
    state.transactions = transactionsResponse.transactions;
    await loadArchivedAccounts();
    await loadClassifications();
  } catch (error) {
    state.accounts = [];
    state.archivedAccounts = [];
    state.transactions = [];
    state.categories = [];
    state.tags = [];
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

async function loadArchivedAccounts() {
  const response = await api("/api/checking-accounts?status=archived");
  state.archivedAccounts = response.accounts;
}

async function loadTransactionsAndAccounts() {
  const [accountsResponse, transactionsResponse] = await Promise.all([
    api("/api/checking-accounts"),
    api("/api/transactions"),
  ]);
  state.accounts = accountsResponse.accounts;
  state.transactions = transactionsResponse.transactions;
  await loadArchivedAccounts();
  await loadClassifications();
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
    await api("/api/transactions", { method: "POST", body: data });
    resetTransactionForm();
    await loadTransactionsAndAccounts();
    setMessage(transactionMessage, "Lançamento salvo.", "success");
  } catch (error) {
    setMessage(transactionMessage, error.message, "error");
  }
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

function resetAccountForm() {
  accountForm.reset();
  accountForm.elements.id.value = "";
  formTitle.textContent = "Nova conta";
  cancelEditButton.hidden = true;
  updateAccountTypeState();
  setMessage(accountMessage, "");
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
  transactionForm.elements.date.value = new Date().toISOString().slice(0, 10);
  installmentCount.value = "2";
  recurrenceFrequency.value = "monthly";
  recurrenceCount.value = "12";
  updateSeriesState();
  updateTransactionTypeState();
}

function renderAll() {
  renderCockpit();
  renderAccounts();
  renderTransactionAccounts();
  renderTransactionCategories();
  renderTransactions();
  renderClassifications();
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

function formatMoney(value, currency) {
  const amount = Number(value);
  return amount.toLocaleString("pt-BR", { style: "currency", currency });
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
