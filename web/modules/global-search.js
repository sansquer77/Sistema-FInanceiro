import { stateMarkup } from "./dom-utils.js";

export function registerGlobalSearch({ state, elements, viewTitles, normalizeSearch, escapeHtml, api, onNavigate }) {
  const { trigger, dialog, input, results, closeButton } = elements;
  let visibleItems = [];
  let requestRevision = 0;
  let searchTimer = null;

  trigger.addEventListener("click", open);
  closeButton.addEventListener("click", close);
  input.addEventListener("input", scheduleRender);
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
    scheduleRender();
    queueMicrotask(() => input.focus());
  }

  function close() {
    requestRevision += 1;
    clearTimeout(searchTimer);
    if (dialog.open) dialog.close();
    trigger.focus();
  }

  function scheduleRender() {
    const query = normalizeSearch(input.value);
    const revision = ++requestRevision;
    clearTimeout(searchTimer);
    render(query, [], query.length >= 2);
    if (query.length < 2) return;
    searchTimer = setTimeout(async () => {
      try {
        const response = await api(`/api/global-search?q=${encodeURIComponent(input.value.trim())}&limit=24`);
        if (revision !== requestRevision || !dialog.open) return;
        render(query, remoteSearchItems(response.results || []), false);
      } catch (error) {
        if (revision !== requestRevision || !dialog.open) return;
        render(query, [], false, error.message);
      }
    }, 180);
  }

  function render(query, remoteItems = [], loading = false, error = "") {
    const candidates = query ? [...remoteItems, ...searchItems()] : searchItems();
    visibleItems = candidates
      .filter((item) => !query || normalizeSearch(`${item.title} ${item.meta}`).includes(query))
      .slice(0, 24);
    results.innerHTML = visibleItems.length
      ? visibleItems.map((item, index) => `
          <button class="global-search-result" type="button" role="option" data-global-search-index="${index}">
            <span><strong>${escapeHtml(item.title)}</strong><small>${escapeHtml(item.meta)}</small></span>
            <em>${escapeHtml(item.section)}</em>
          </button>
        `).join("")
      : stateMarkup(
          error || (loading ? "Buscando em todo o histórico…" : "Revise o termo procurado."),
          { kind: error ? "error" : loading ? "loading" : "empty" },
        );
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
    return [...modules, ...accounts, ...cards, ...positions, ...classifications];
  }

  function remoteSearchItems(rows) {
    return rows.map((row) => {
      const accountTransaction = row.kind === "account_transaction";
      return {
        view: accountTransaction ? "transactions" : "cardLaunches",
        title: row.title || (accountTransaction ? "Lançamento" : "Lançamento do cartão"),
        meta: row.meta || row.date || "",
        section: accountTransaction ? "Lançamento" : "Fatura",
        prepare: () => {
          if (accountTransaction) {
            state.selectedAccountId = String(row.owner_id || state.selectedAccountId || "");
            state.transactionMonth = row.month || state.transactionMonth;
            state.transactionHighlightId = String(row.id || "");
          } else {
            state.selectedCreditCardId = String(row.owner_id || state.selectedCreditCardId || "");
            state.cardInvoiceMonth = row.month || state.cardInvoiceMonth;
          }
        },
      };
    });
  }
}

function isTypingTarget(target) {
  return Boolean(target?.closest?.("input, textarea, select, [contenteditable='true']"));
}
