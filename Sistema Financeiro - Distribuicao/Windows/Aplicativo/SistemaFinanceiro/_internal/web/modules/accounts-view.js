export function registerAccountsView({
  state,
  elements,
  api,
  formData,
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

  function getBankLogo(bankName, accountType) {
    if (accountType === "wallet") {
      return `<div class="bank-logo-badge" style="background-color: var(--bank-logo-wallet-surface);" title="Carteira / Dinheiro">
        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="var(--bank-logo-generic-ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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

    if (name.includes("nubank") || name.includes("nu ")) {
      return `<div class="bank-logo-badge" style="background-color: #820ad1;" title="Nubank">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M25 75V25c0 0 10-10 20 0s10 20 10 30c0 10 0 20 20 20s20-20 20-30" />
        </svg>
      </div>`;
    }
    if (name.includes("itau") || name.includes("itaú")) {
      return `<div class="bank-logo-badge" style="background-color: #ec7000;" title="Itaú">
        <svg viewBox="0 0 100 100" width="30" height="30">
          <rect x="10" y="10" width="80" height="80" rx="15" fill="#002d62" />
          <path d="M25 35h50v6h-22v24h22v6h-50v-6h22V41h-22z" fill="#ec7000" />
          <path d="M30 40h40v4H50v16h20v4H30v-4h16V44H30z" fill="#ffec00" />
        </svg>
      </div>`;
    }
    if (name.includes("bradesco")) {
      return `<div class="bank-logo-badge" style="background-color: #cc092f;" title="Bradesco">
        <svg viewBox="0 0 100 100" width="22" height="22" fill="#ffffff">
          <path d="M50 15c-12 0-22 10-22 22 0 6 2 11 6 15L50 68l16-16c4-4 6-9 6-15 0-12-10-22-22-22zm0 8c8 0 14 6 14 14 0 4-2 8-5 10L50 58l-9-11c-3-2-5-6-5-10 0-8 6-14 14-14z" />
          <rect x="25" y="75" width="50" height="8" rx="2" />
          <rect x="35" y="85" width="30" height="5" rx="1" />
        </svg>
      </div>`;
    }
    if (name.includes("banco do brasil") || name.includes(" bb ") || name === "bb") {
      return `<div class="bank-logo-badge" style="background-color: #0038a8;" title="Banco do Brasil">
        <svg viewBox="0 0 100 100" width="26" height="26" fill="#fcf800">
          <path d="M20 30c5-10 15-15 30-15s25 5 30 15l-12 6c-3-6-10-10-18-10s-15 4-18 10l-12-6z" />
          <path d="M20 70c5 10 15 15 30 15s25-5 30-15l-12-6c-3 6-10 10-18 10s-15-4-18-10l-12 6z" />
          <path d="M50 35c8 0 15 7 15 15s-7 15-15 15-15-7-15-15 7-15 15-15z" />
        </svg>
      </div>`;
    }
    if (name.includes("caixa") || name.includes("cef")) {
      return `<div class="bank-logo-badge" style="background-color: #005c9e;" title="Caixa">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="#ffffff">
          <rect x="15" y="15" width="70" height="70" rx="10" />
          <path d="M30 30l15 15-15 15h12l9-9 9 9h12L57 45l15-15H60l-9 9-9-9H30z" fill="#f37021" />
          <circle cx="50" cy="50" r="10" fill="#ffffff" />
        </svg>
      </div>`;
    }
    if (name.includes("santander")) {
      return `<div class="bank-logo-badge" style="background-color: #ec0000;" title="Santander">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="#ffffff">
          <path d="M50 15c-15 0-25 15-20 28 3 7 10 12 17 12h6c7 0 14-5 17-12 5-13-5-28-20-28zm-3 8c1 0 2 1 2 2v6h-4v-6c0-1 1-2 2-2zm6 0c1 0 2 1 2 2v6h-4v-6c0-1 1-2 2-2zM32 50h36v32H32z" />
        </svg>
      </div>`;
    }
    if (name.includes("inter")) {
      return `<div class="bank-logo-badge" style="background-color: #ff7a00;" title="Banco Inter">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="12" stroke-linecap="round" stroke-linejoin="round">
          <path d="M30 25h40v50H30z" />
          <path d="M50 25v50" />
        </svg>
      </div>`;
    }
    if (name.includes("c6")) {
      return `<div class="bank-logo-badge" style="background-color: #111111;" title="C6 Bank">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="#ffffff">
          <text x="50" y="65" font-size="45" font-family="Arial, sans-serif" font-weight="900" text-anchor="middle">C6</text>
        </svg>
      </div>`;
    }
    if (name.includes("xp")) {
      return `<div class="bank-logo-badge" style="background-color: #000000;" title="XP Investimentos">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="#d5b265">
          <path d="M20 20l25 30-25 30h15l17-21 17 21h15L60 50l25-30H70L53 40 35 20H20z" />
        </svg>
      </div>`;
    }
    if (name.includes("btg")) {
      return `<div class="bank-logo-badge" style="background-color: #0f172a;" title="BTG Pactual">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="#d5b265">
          <text x="50" y="65" font-size="32" font-family="Arial, sans-serif" font-weight="bold" text-anchor="middle">BTG</text>
        </svg>
      </div>`;
    }
    if (name.includes("sofisa")) {
      return `<div class="bank-logo-badge" style="background-color: #003b71;" title="Banco Sofisa">
        <svg viewBox="0 0 100 100" width="26" height="26">
          <circle cx="50" cy="50" r="34" fill="#ffffff" opacity="0.16" />
          <path d="M25 61c8 8 20 12 32 8 10-3 17-11 18-21-7 6-15 8-24 5-8-2-13-6-20-5-5 1-9 5-6 13z" fill="#ffffff" />
          <path d="M25 39c8-8 20-12 32-8 10 3 17 11 18 21-7-6-15-8-24-5-8 2-13 6-20 5-5-1-9-5-6-13z" fill="#6bb6ff" />
        </svg>
      </div>`;
    }
    if (name.includes("avenue")) {
      return `<div class="bank-logo-badge" style="background-color: #0c0c0e;" title="Avenue">
        <svg viewBox="0 0 100 100" width="22" height="22" fill="none" stroke="#ffffff" stroke-width="10" stroke-linecap="round">
          <path d="M25 80L50 20L75 80" />
          <path d="M38 55h24" />
        </svg>
      </div>`;
    }
    if (name.includes("wise")) {
      return `<div class="bank-logo-badge" style="background-color: #9fe870;" title="Wise">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="#1e3b2b">
          <path d="M20 30h40L40 50h30L45 80h10L75 42H50l20-12H20v8z" />
        </svg>
      </div>`;
    }
    if (name.includes("coinbase")) {
      return `<div class="bank-logo-badge" style="background-color: #0052ff;" title="Coinbase">
        <svg viewBox="0 0 100 100" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="12">
          <circle cx="50" cy="50" r="30" />
          <circle cx="50" cy="50" r="10" fill="#ffffff" />
        </svg>
      </div>`;
    }
    if (name.includes("cripto") || name.includes("crypto") || name.includes("binance") || name.includes("ledger") || name.includes("metamask") || name.includes("trezor") || name.includes("blockchain")) {
      return `<div class="bank-logo-badge" style="background-color: #f59e0b;" title="Criptoativos / Wallet">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="9"></circle>
          <path d="M12 7v10M9 9h5a2 2 0 0 1 0 4H9h4a2 2 0 0 1 0 4H9"></path>
        </svg>
      </div>`;
    }

    return `<div class="bank-logo-badge" style="background-color: var(--bank-logo-generic-surface);" title="Banco / Outro">
      <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="var(--bank-logo-generic-ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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

  return {
    loadAccounts,
    loadArchivedAccounts,
    renderAccounts,
    resetAccountForm,
    updateAccountTypeState,
  };
}
