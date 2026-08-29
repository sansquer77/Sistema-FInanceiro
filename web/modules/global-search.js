export function registerGlobalSearch({ state, elements, viewTitles, normalizeSearch, escapeHtml, onNavigate }) {
  const { trigger, dialog, input, results, closeButton } = elements;
  let visibleItems = [];

  trigger.addEventListener("click", open);
  closeButton.addEventListener("click", close);
  input.addEventListener("input", render);
  input.addEventListener("keydown", handleInputKeydown);
  results.addEventListener("click", handleResultClick);
  results.addEventListener("keydown", handleResultsKeydown);
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) close();
  });
  document.addEventListener("keydown", (event) => {
    if (event.key === "/" && !trigger.closest("[hidden]") && !isTypingTarget(event.target)) {
      event.preventDefault();
      open();
    }
  });

  function open() {
    if (!dialog.open) dialog.showModal();
    input.value = "";
    render();
    queueMicrotask(() => input.focus());
  }

  function close() {
    if (dialog.open) dialog.close();
    trigger.focus();
  }

  function render() {
    const query = normalizeSearch(input.value);
    visibleItems = searchItems().filter((item) => !query || normalizeSearch(`${item.title} ${item.meta}`).includes(query)).slice(0, 24);
    results.innerHTML = visibleItems.length
      ? visibleItems.map((item, index) => `
          <button class="global-search-result" type="button" role="option" data-global-search-index="${index}">
            <span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.meta)}</small></span>
            <em>${escapeHtml(item.section)}</em>
          </button>
        `).join("")
      : '<div class="empty-state compact">Nenhum resultado nos dados carregados.</div>';
  }

  function handleInputKeydown(event) {
    if (event.key !== "ArrowDown") return;
    event.preventDefault();
    results.querySelector("button")?.focus();
  }

  function handleResultClick(event) {
    const button = event.target.closest("[data-global-search-index]");
    if (!button) return;
    const item = visibleItems[Number(button.dataset.globalSearchIndex)];
    if (!item) return;
    close();
    item.prepare?.();
    onNavigate(item.view);
  }

  function handleResultsKeydown(event) {
    if (!["ArrowDown", "ArrowUp", "Enter"].includes(event.key)) return;
    const buttons = [...results.querySelectorAll("button")];
    const index = buttons.indexOf(event.target.closest("button"));
    if (event.key === "Enter") return;
    event.preventDefault();
    const nextIndex = event.key === "ArrowDown"
      ? Math.min(index + 1, buttons.length - 1)
      : index <= 0 ? -1 : index - 1;
    if (nextIndex === -1) input.focus();
    else buttons[nextIndex]?.focus();
  }

  function searchItems() {
    const modules = Object.entries(viewTitles).map(([view, labels]) => ({
      view,
      title: labels[1],
      meta: labels[0],
      section: "Módulo",
    }));
    const accounts = [...(state.accounts || []), ...(state.archivedAccounts || [])].map((account) => ({
      view: "accounts",
      title: account.name,
      meta: `${account.bank_name || "Conta"} · ${account.currency || "BRL"}`,
      section: "Conta",
    }));
    const cards = [...(state.creditCards || []), ...(state.archivedCreditCards || [])].map((card) => ({
      view: "creditCards",
      title: card.name,
      meta: `${card.issuer || "Cartão"} · ${card.currency || "BRL"}`,
      section: "Cartão",
    }));
    const transactions = (state.transactions || []).map((transaction) => ({
      view: "transactions",
      title: transaction.description || "Lançamento",
      meta: `${transaction.date || ""} · ${transaction.category || "Sem categoria"}`,
      section: "Lançamento",
      prepare: () => {
        state.selectedAccountId = String(transaction.account_id || state.selectedAccountId || "");
        state.transactionMonth = String(transaction.date || "").slice(0, 7) || state.transactionMonth;
        state.transactionHighlightId = String(transaction.id || "");
      },
    }));
    const cardTransactions = (state.cardTransactions || []).map((transaction) => ({
      view: "cardLaunches",
      title: transaction.description || "Lançamento do cartão",
      meta: `${transaction.date || ""} · ${transaction.category || "Sem categoria"}`,
      section: "Fatura",
      prepare: () => {
        state.selectedCreditCardId = String(transaction.credit_card_id || state.selectedCreditCardId || "");
        state.cardInvoiceMonth = transaction.invoice_month || String(transaction.date || "").slice(0, 7) || state.cardInvoiceMonth;
      },
    }));
    const positions = (state.portfolio?.positions || []).map((position) => ({
      view: "portfolio",
      title: position.name || position.asset_name || position.identifier || "Ativo",
      meta: `${position.asset_type_label || position.asset_type || "Ativo"} · ${position.currency || "BRL"}`,
      section: "Portfólio",
      prepare: () => {
        state.portfolioTab = "position";
        state.portfolioHighlightId = String(position.id || position.position_id || "");
      },
    }));
    const classifications = [
      ...(state.categories || []).map((item) => ({ view: "classifications", title: item.name, meta: "Categoria", section: "Classificação" })),
      ...(state.tags || []).map((item) => ({ view: "classifications", title: item.name, meta: "Tag", section: "Classificação" })),
    ];
    return [...modules, ...accounts, ...cards, ...transactions, ...cardTransactions, ...positions, ...classifications];
  }
}

function isTypingTarget(target) {
  return Boolean(target?.closest?.("input, textarea, select, [contenteditable='true']"));
}
