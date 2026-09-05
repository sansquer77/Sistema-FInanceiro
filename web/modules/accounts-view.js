import { renderBankLogo, attachBankLogoFallbacks } from "./bank-logos.js";

export function registerAccountsView({
  state,
  elements,
  api,
  formData,
  setFormBusy,
  setMessage,
  emptyState,
  escapeHtml,
  formatMoney,
  accountTypeLabel,
  ensureSelectedAccount,
  onAccountsChanged = async () => {},
}) {
  const {
    accountForm,
    accountBankLabel,
    accountBankDetails,
    accountMessage,
    accountList,
    archivedAccountList,
    cancelEditButton,
    formTitle,
  } = elements;

  accountForm.addEventListener("submit", handleAccountSubmit);
  accountForm.elements.account_type.addEventListener("change", updateAccountTypeState);
  cancelEditButton.addEventListener("click", resetAccountForm);

  async function loadAccounts() {
    const response = await api("/api/checking-accounts");
    state.accounts = response.accounts;
    ensureSelectedAccount();
    await loadArchivedAccounts();
  }

  async function loadArchivedAccounts() {
    const response = await api("/api/checking-accounts?status=archived");
    state.archivedAccounts = response.accounts;
  }

  async function refreshAccounts() {
    await loadAccounts();
    await onAccountsChanged();
  }

  async function handleAccountSubmit(event) {
    event.preventDefault();
    setMessage(accountMessage, "");
    const data = formData(accountForm);
    const isEditing = Boolean(data.id);
    setFormBusy(accountForm, true);
    try {
      await api(isEditing ? `/api/checking-accounts/${data.id}` : "/api/checking-accounts", {
        method: isEditing ? "PUT" : "POST",
        body: data,
      });
      resetAccountForm();
      await refreshAccounts();
      setMessage(accountMessage, "Conta salva.", "success");
    } catch (error) {
      setMessage(accountMessage, error.message, "error");
    } finally {
      setFormBusy(accountForm, false);
    }
  }

  async function archiveAccount(id) {
    try {
      await api(`/api/checking-accounts/${id}`, { method: "DELETE" });
      await refreshAccounts();
    } catch (error) {
      setMessage(accountMessage, error.message, "error");
    }
  }

  async function restoreAccount(id) {
    try {
      await api(`/api/checking-accounts/${id}/restore`, { method: "POST" });
      await refreshAccounts();
    } catch (error) {
      setMessage(accountMessage, error.message, "error");
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

  function renderAccounts() {
    accountList.innerHTML = "";
    if (state.accounts.length === 0) {
      accountList.append(emptyState("Nenhuma conta cadastrada ainda."));
    } else {
      state.accounts.forEach((account) => {
        accountList.append(accountCard(account, "active"));
      });
    }
    attachBankLogoFallbacks(accountList);
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
    attachBankLogoFallbacks(archivedAccountList);
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

    const logoHtml = renderBankLogo({
      name: account.bank_name,
      kind: account.account_type === "wallet" ? "wallet" : "bank",
    });

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
      editButton.addEventListener("click", () => editAccount(account));
    }
    if (archiveButton) {
      archiveButton.addEventListener("click", () => archiveAccount(account.id));
    }
    if (restoreButton) {
      restoreButton.addEventListener("click", () => restoreAccount(account.id));
    }
    return card;
  }

  return {
    loadAccounts,
    loadArchivedAccounts,
    renderAccounts,
    resetAccountForm,
    updateAccountTypeState,
  };
}
