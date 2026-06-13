const state = {
  user: null,
  accounts: [],
  archivedAccounts: [],
  transactions: [],
  view: "cockpit",
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
const accountMessage = document.querySelector("#accountMessage");
const accountList = document.querySelector("#accountList");
const archivedAccountList = document.querySelector("#archivedAccountList");
const transactionForm = document.querySelector("#transactionForm");
const transactionMessage = document.querySelector("#transactionMessage");
const transactionList = document.querySelector("#transactionList");
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
const recentTransactionList = document.querySelector("#recentTransactionList");
const transactionType = document.querySelector("#transactionType");
const transactionAccount = document.querySelector("#transactionAccount");
const destinationAccount = document.querySelector("#destinationAccount");
const destinationAccountLabel = document.querySelector("#destinationAccountLabel");
const userName = document.querySelector("#userName");
const logoutButton = document.querySelector("#logoutButton");
const cancelEditButton = document.querySelector("#cancelEditButton");
const formTitle = document.querySelector("#formTitle");
const moduleEyebrow = document.querySelector("#moduleEyebrow");
const pageTitle = document.querySelector("#pageTitle");
const accountCount = document.querySelector("#accountCount");
const currencyCount = document.querySelector("#currencyCount");
const monthIncome = document.querySelector("#monthIncome");
const monthExpense = document.querySelector("#monthExpense");
const currencyList = document.querySelector("#currencyList");
const navButtons = document.querySelectorAll("[data-view]");
const moduleViews = {
  cockpit: document.querySelector("#cockpitView"),
  accounts: document.querySelector("#accountsView"),
  transactions: document.querySelector("#transactionsView"),
  imports: document.querySelector("#importsView"),
  user: document.querySelector("#userView"),
};

const viewTitles = {
  cockpit: ["Cockpit", "Resumo financeiro"],
  accounts: ["Gestão de contas", "Contas"],
  transactions: ["Operação", "Lançamentos"],
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
transactionForm.addEventListener("submit", handleTransactionSubmit);
importForm.addEventListener("submit", handleImportSubmit);
emailForm.addEventListener("submit", handleEmailSubmit);
passwordForm.addEventListener("submit", handlePasswordSubmit);
deleteUserForm.addEventListener("submit", handleDeleteUserSubmit);
transactionType.addEventListener("change", updateTransactionTypeState);
logoutButton.addEventListener("click", handleLogout);
cancelEditButton.addEventListener("click", resetAccountForm);
navButtons.forEach((button) => button.addEventListener("click", () => showModule(button.dataset.view)));

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
  setFormBusy(loginForm, true);
  try {
    const data = formData(loginForm);
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
  setFormBusy(registerForm, true);
  try {
    const data = formData(registerForm);
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
  setFormBusy(passwordResetRequestForm, true);
  try {
    const response = await api("/api/password-reset/request", {
      method: "POST",
      body: formData(passwordResetRequestForm),
    });
    passwordResetConfirmForm.elements.token.value = response.token || "";
    switchAuthMode("reset-confirm");
    const message = response.token
      ? `Codigo gerado para uso local. Ele expira em ${response.expires_in_minutes} minutos.`
      : "Se o email existir, um codigo de recuperacao sera gerado.";
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
  setFormBusy(passwordResetConfirmForm, true);
  try {
    await api("/api/password-reset/confirm", {
      method: "POST",
      body: formData(passwordResetConfirmForm),
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
  } catch (error) {
    state.accounts = [];
    state.archivedAccounts = [];
    state.transactions = [];
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
  renderAll();
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
  setFormBusy(importForm, true);
  try {
    const response = await upload("/api/import/organizze-transactions", new FormData(importForm));
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

function editAccount(account) {
  formTitle.textContent = "Editar conta";
  accountForm.elements.id.value = account.id;
  accountForm.elements.name.value = account.name;
  accountForm.elements.bank_name.value = account.bank_name;
  accountForm.elements.branch.value = account.branch || "";
  accountForm.elements.account_number.value = account.account_number || "";
  accountForm.elements.currency.value = account.currency;
  accountForm.elements.initial_balance.value = account.initial_balance.replace(".", ",");
  accountForm.elements.notes.value = account.notes || "";
  cancelEditButton.hidden = false;
  accountForm.scrollIntoView({ behavior: "smooth", block: "start" });
}

function resetAccountForm() {
  accountForm.reset();
  accountForm.elements.id.value = "";
  formTitle.textContent = "Nova conta";
  cancelEditButton.hidden = true;
  setMessage(accountMessage, "");
}

function resetTransactionForm() {
  transactionForm.reset();
  transactionForm.elements.date.value = new Date().toISOString().slice(0, 10);
  updateTransactionTypeState();
}

function renderAll() {
  renderCockpit();
  renderAccounts();
  renderTransactionAccounts();
  renderTransactions();
}

function renderCockpit() {
  const totals = getCurrencyTotals();
  const monthTotals = getCurrentMonthTotals();
  accountCount.textContent = String(state.accounts.length);
  currencyCount.textContent = String(totals.size);
  monthIncome.textContent = formatMoney(monthTotals.income, "BRL");
  monthExpense.textContent = formatMoney(monthTotals.expense, "BRL");
  renderCurrencyTotals(totals);
  renderTransactionCollection(recentTransactionList, state.transactions.slice(0, 5), true);
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
          <span>${escapeHtml(account.bank_name)}</span>
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
  destinationAccount.innerHTML = options || '<option value="">Cadastre uma conta</option>';
  importAccount.innerHTML = options || '<option value="">Cadastre uma conta</option>';
  transactionForm.querySelector('button[type="submit"]').disabled = state.accounts.length === 0;
  importForm.querySelector('button[type="submit"]').disabled = state.accounts.length === 0;
}

function renderTransactions() {
  renderTransactionCollection(transactionList, state.transactions, false);
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
    }
    container.append(group);
  }
}

function transactionTemplate(transaction, compact) {
  const signal = transaction.type === "income" ? "positive" : transaction.type === "expense" ? "negative" : "neutral";
  const amountPrefix = transaction.type === "income" ? "" : transaction.type === "expense" ? "-" : "";
  const destination = transaction.destination_account_name ? ` para ${escapeHtml(transaction.destination_account_name)}` : "";
  return `
    <article class="transaction-row ${signal}">
      <div>
        <strong>${escapeHtml(transaction.description)}</strong>
        <div class="account-meta">
          <span>${transactionTypeLabel(transaction.type)}</span>
          <span>${escapeHtml(transaction.account_name)}${destination}</span>
          ${transaction.category_name ? `<span>${escapeHtml(transaction.category_name)}</span>` : ""}
          ${transaction.tag_name ? `<span>#${escapeHtml(transaction.tag_name)}</span>` : ""}
        </div>
      </div>
      <div class="transaction-amount">
        <strong>${amountPrefix}${formatMoney(transaction.amount, transaction.account_currency)}</strong>
        ${compact ? "" : `<button class="danger small-button" type="button" data-transaction-id="${transaction.id}">Excluir</button>`}
      </div>
    </article>
  `;
}

function updateTransactionTypeState() {
  const isTransfer = transactionType.value === "transfer";
  destinationAccountLabel.hidden = !isTransfer;
  destinationAccount.disabled = !isTransfer;
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

function getCurrentMonthTotals() {
  const now = new Date();
  const prefix = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
  return state.transactions.reduce((totals, transaction) => {
    if (!transaction.date.startsWith(prefix) || transaction.account_currency !== "BRL") {
      return totals;
    }
    if (transaction.type === "income") {
      totals.income += Number(transaction.amount);
    }
    if (transaction.type === "expense") {
      totals.expense += Number(transaction.amount);
    }
    return totals;
  }, { income: 0, expense: 0 });
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
    throw new Error("Nao foi possivel falar com o servidor local. Abra pelo endereco http://localhost:8000.");
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
    throw new Error("Nao foi possivel falar com o servidor local. Abra pelo endereco http://localhost:8000.");
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

function formatMoney(value, currency) {
  const amount = Number(value);
  return amount.toLocaleString("pt-BR", { style: "currency", currency });
}

function formatDate(value) {
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
