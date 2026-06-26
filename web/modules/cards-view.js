export function registerCardsView({
  state,
  elements,
  api,
  formData,
  setFormBusy,
  setMessage,
  emptyState,
  escapeHtml,
  formatMoney,
  formatDate,
  formatMonthLabel,
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
  deleteSeriesScope,
  openMonthPicker,
  onCreditCardsChanged = async () => {},
  onCardTransactionsChanged = () => {},
  onInvoicePaid = async () => {},
}) {
  const {
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
    cardTransactionForm,
    cardTransactionFormTitle,
    cardTransactionType,
    cardTransactionCategory,
    cardTransactionSubcategory,
    cardSeriesKind,
    cardInstallmentCount,
    cardInstallmentCountLabel,
    cardRecurrenceFields,
    cardRecurrenceFrequency,
    cardRecurrenceCount,
    cardInvoiceList,
    cancelCardTransactionEditButton,
  } = elements;

  creditCardForm.addEventListener("submit", handleCreditCardSubmit);
  creditCardForm.elements.currency.addEventListener("change", renderCreditCardPreferredPaymentAccounts);
  cardInvoiceCard.addEventListener("change", handleCardInvoiceCardChange);
  cardInvoiceList.addEventListener("click", handleCardInvoiceListClick);
  previousCardInvoiceButton.addEventListener("click", () => shiftCardInvoiceMonth(-1));
  todayCardInvoiceButton.addEventListener("click", () => setCardInvoiceMonth(currentMonthValue()));
  cardInvoiceMonthLabel.addEventListener("click", (event) => {
    event.stopPropagation();
    openMonthPicker(event.currentTarget, state.cardInvoiceMonth, setCardInvoiceMonth);
  });
  nextCardInvoiceButton.addEventListener("click", () => shiftCardInvoiceMonth(1));
  cardInvoicePaymentForm.addEventListener("submit", handleCardInvoicePaymentSubmit);
  cardPaymentAccount.addEventListener("change", renderCardInvoice);
  cardTransactionForm.addEventListener("submit", handleCardTransactionSubmit);
  cardTransactionType.addEventListener("change", renderCardTransactionCategories);
  cardTransactionCategory.addEventListener("change", renderCardTransactionSubcategories);
  cardSeriesKind.addEventListener("change", updateCardSeriesState);
  cancelCreditCardEditButton.addEventListener("click", resetCreditCardForm);
  cancelCardTransactionEditButton.addEventListener("click", resetCardTransactionForm);

  async function loadCreditCards() {
    const response = await api("/api/credit-cards");
    state.creditCards = response.cards;
    ensureSelectedCreditCard();
    await loadArchivedCreditCards();
    await loadCardTransactions();
    await loadCardInvoice();
  }

  async function loadArchivedCreditCards() {
    const response = await api("/api/credit-cards?status=archived");
    state.archivedCreditCards = response.cards;
  }

  async function loadCardInvoice() {
    const requestId = ++state.cardInvoiceRequestId;
    const cardId = String(state.selectedCreditCardId || "");
    const month = state.cardInvoiceMonth;
    if (!state.selectedCreditCardId) {
      state.cardInvoiceTransactions = [];
      state.cardInvoicePayments = [];
      return;
    }
    const response = await api(`/api/credit-card-invoice?card_id=${encodeURIComponent(cardId)}&month=${encodeURIComponent(month)}`);
    if (
      requestId !== state.cardInvoiceRequestId
      || month !== state.cardInvoiceMonth
      || cardId !== String(state.selectedCreditCardId || "")
    ) {
      return;
    }
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
      await onCreditCardsChanged();
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
    if (isEditing && shouldAskFutureCardReplication(data.id)) {
      data.apply_to_future = window.confirm("Replicar esta alteração nos próximos lançamentos futuros desta série? Lançamentos passados ou conciliados não serão alterados.");
    }
    try {
      await api(isEditing ? `/api/credit-card-transactions/${data.id}` : "/api/credit-card-transactions", {
        method: isEditing ? "PUT" : "POST",
        body: data,
      });
      resetCardTransactionForm();
      await refreshCardLaunches();
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
      await onInvoicePaid();
      setMessage(cardInvoiceMessage, "Fatura paga e débito lançado na conta.", "success");
    } catch (error) {
      setMessage(cardInvoiceMessage, error.message, "error");
    }
  }

  async function archiveCreditCard(id) {
    try {
      await api(`/api/credit-cards/${id}`, { method: "DELETE" });
      await loadCreditCards();
      await onCreditCardsChanged();
    } catch (error) {
      setMessage(creditCardMessage, error.message, "error");
    }
  }

  async function restoreCreditCard(id) {
    try {
      await api(`/api/credit-cards/${id}/restore`, { method: "POST" });
      await loadCreditCards();
      await onCreditCardsChanged();
    } catch (error) {
      setMessage(creditCardMessage, error.message, "error");
    }
  }

  async function deleteCardTransaction(id) {
    try {
      const scope = deleteSeriesScope(id, state.cardTransactions, "cartão");
      await api(`/api/credit-card-transactions/${id}${scope}`, { method: "DELETE" });
      await refreshCardLaunches();
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
      await refreshCardLaunches();
    } catch (error) {
      setMessage(cardInvoiceMessage, error.message, "error");
    }
  }

  async function moveCardTransactionInvoice(id, direction) {
    try {
      await api(`/api/credit-card-transactions/${id}/invoice`, {
        method: "PUT",
        body: { direction },
      });
      await refreshCardLaunches();
      setMessage(cardInvoiceMessage, direction === "next" ? "Lançamento movido para a próxima fatura." : "Lançamento movido para a fatura anterior.", "success");
    } catch (error) {
      setMessage(cardInvoiceMessage, error.message, "error");
    }
  }

  async function refreshCardLaunches() {
    await loadCardInvoice();
    await loadCardTransactions();
    renderCreditCards();
    onCardTransactionsChanged();
  }

  function shouldAskFutureCardReplication(transactionId) {
    const transaction = state.cardTransactions.find((entry) => String(entry.id) === String(transactionId));
    return Boolean(transaction && transaction.series_id && isInstallmentTransaction(transaction));
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
    renderCreditCardPreferredPaymentAccounts();
    creditCardForm.elements.preferred_payment_account_id.value = card.preferred_payment_account_id || "";
    creditCardForm.elements.notes.value = card.notes || "";
    cancelCreditCardEditButton.hidden = false;
    creditCardForm.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function resetCreditCardForm() {
    creditCardForm.reset();
    creditCardForm.elements.id.value = "";
    creditCardFormTitle.textContent = "Novo cartão";
    cancelCreditCardEditButton.hidden = true;
    renderCreditCardPreferredPaymentAccounts();
    setMessage(creditCardMessage, "");
  }

  function resetCardTransactionForm() {
    cardTransactionForm.reset();
    cardTransactionForm.elements.id.value = "";
    cardTransactionForm.elements.date.value = todayLocalDateValue();
    cardTransactionForm.elements.credit_card_id.value = state.selectedCreditCardId;
    cardTransactionForm.elements.invoice_month.value = state.cardInvoiceMonth;
    cardSeriesKind.disabled = false;
    cardInstallmentCount.disabled = false;
    cardRecurrenceFrequency.disabled = false;
    cardRecurrenceCount.disabled = false;
    cardSeriesKind.value = "single";
    cardInstallmentCount.value = "2";
    cardRecurrenceFrequency.value = "monthly";
    cardRecurrenceCount.value = "12";
    cardTransactionFormTitle.textContent = "Novo lançamento no cartão";
    cancelCardTransactionEditButton.hidden = true;
    cardTransactionForm.querySelector('button[type="submit"]').textContent = "Salvar lançamento";
    updateCardSeriesState();
    renderCardTransactionCategories();
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
    cardSeriesKind.value = isInstallmentTransaction(transaction) ? "installment" : transaction.series_kind || "single";
    cardInstallmentCount.value = transaction.installment_count || "2";
    cardRecurrenceFrequency.value = transaction.recurrence_frequency || "monthly";
    cardRecurrenceCount.value = transaction.installment_count || "12";
    cardSeriesKind.disabled = true;
    cardInstallmentCount.disabled = true;
    cardRecurrenceFrequency.disabled = true;
    cardRecurrenceCount.disabled = true;
    updateCardSeriesState();
    cardSeriesKind.disabled = true;
    cardInstallmentCount.disabled = true;
    cardRecurrenceFrequency.disabled = true;
    cardRecurrenceCount.disabled = true;
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
    const isRecurring = cardSeriesKind.value === "recurring";
    cardInstallmentCountLabel.hidden = !isInstallment;
    cardInstallmentCount.disabled = !isInstallment;
    cardRecurrenceFields.hidden = !isRecurring;
    cardRecurrenceFrequency.disabled = !isRecurring;
    cardRecurrenceCount.disabled = !isRecurring;
    cardInstallmentCount.name = isRecurring ? "unused_installment_count" : "installment_count";
    cardRecurrenceCount.name = isRecurring ? "installment_count" : "recurrence_count";
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
      updateCardInvoiceOpenCount();
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
    updateCardInvoiceOpenCount();
    renderCardInvoiceList(card);
  }

  function updateCardInvoiceOpenCount() {
    if (!cardInvoiceOpenCount) {
      return;
    }
    const pending = state.cardInvoiceTransactions.filter((transaction) => !transaction.reconciled_at).length;
    cardInvoiceOpenCount.textContent = `${pending} não conciliado${pending === 1 ? "" : "s"}`;
    cardInvoiceOpenCount.classList.toggle("danger", pending > 0);
    cardInvoiceOpenCount.classList.toggle("ok", pending === 0);
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
    const previousSelection = cardPaymentAccount.value;
    const previousCardId = cardPaymentAccount.dataset.cardId || "";
    const accounts = card
      ? state.accounts.filter((account) => account.currency === card.currency)
      : [];
    cardPaymentAccount.innerHTML = accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("") || '<option value="">Cadastre uma conta compatível</option>';
    if (card && accounts.length) {
      const preferred = card.preferred_payment_account_id ? String(card.preferred_payment_account_id) : "";
      const shouldPreserve = previousCardId === String(card.id) && accounts.some((account) => String(account.id) === previousSelection);
      if (shouldPreserve) {
        cardPaymentAccount.value = previousSelection;
      } else if (preferred && accounts.some((account) => String(account.id) === preferred)) {
        cardPaymentAccount.value = preferred;
      }
    }
    cardPaymentAccount.dataset.cardId = card ? String(card.id) : "";
    cardPaymentAccount.disabled = accounts.length === 0;
  }

  function renderCreditCardPreferredPaymentAccounts() {
    const selected = creditCardPreferredPaymentAccount.value;
    const currency = creditCardForm.elements.currency.value || "BRL";
    const accounts = state.accounts.filter((account) => account.currency === currency);
    creditCardPreferredPaymentAccount.innerHTML = '<option value="">Sem preferência</option>' + accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("");
    if (accounts.some((account) => String(account.id) === String(selected))) {
      creditCardPreferredPaymentAccount.value = selected;
    }
    creditCardPreferredPaymentAccount.disabled = accounts.length === 0;
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
        <div class="invoice-entry-main">
          <strong>${escapeHtml(transaction.description)}</strong>
          <div class="account-meta invoice-entry-meta">
            <span>${formatDate(transaction.date)}</span>
            <span>${cardTransactionTypeLabel(transaction.type)}</span>
            ${transactionSeriesLabel(transaction) ? `<span>${transactionSeriesLabel(transaction)}</span>` : ""}
          </div>
        </div>
        <div class="invoice-entry-category">
          ${transaction.category_name ? escapeHtml(cardCategoryPath(transaction)) : "Sem categoria"}
        </div>
        <div class="transaction-amount invoice-entry-amount">
          <strong>${sign}${formatMoney(transaction.amount, card.currency)}</strong>
        </div>
        ${state.cardInvoicePayments.length ? "" : `
          <div class="transaction-actions invoice-entry-actions">
            ${launchActionButton("arrow-left", "Mover para a fatura anterior", `data-card-move-id="${transaction.id}" data-card-move-direction="previous"`)}
            ${launchActionButton("arrow-right", "Mover para a próxima fatura", `data-card-move-id="${transaction.id}" data-card-move-direction="next"`)}
            ${launchActionButton("edit", "Editar lançamento", `data-card-edit-id="${transaction.id}"`)}
            ${launchActionButton("check", isReconciled ? "Desmarcar conciliação" : "Marcar como conciliado", `data-card-reconcile-id="${transaction.id}" data-reconciled="${isReconciled}"`, `reconcile-button ${isReconciled ? "active" : ""}`)}
            ${launchActionButton("trash", "Excluir lançamento", `data-card-transaction-id="${transaction.id}"`, "danger-action")}
          </div>
        `}
      `;
      cardInvoiceList.append(item);
    });
  }

  function handleCardInvoiceListClick(event) {
    const moveButton = event.target.closest("[data-card-move-id]");
    if (moveButton) {
      moveCardTransactionInvoice(moveButton.dataset.cardMoveId, moveButton.dataset.cardMoveDirection);
      return;
    }
    const editButton = event.target.closest("[data-card-edit-id]");
    if (editButton) {
      const transaction = state.cardInvoiceTransactions.find((entry) => String(entry.id) === String(editButton.dataset.cardEditId));
      if (transaction) {
        editCardTransaction(transaction);
      }
      return;
    }
    const reconcileButton = event.target.closest("[data-card-reconcile-id]");
    if (reconcileButton) {
      toggleCardTransactionReconciliation(
        reconcileButton.dataset.cardReconcileId,
        reconcileButton.dataset.reconciled !== "true",
      );
      return;
    }
    const deleteButton = event.target.closest("[data-card-transaction-id]");
    if (deleteButton) {
      deleteCardTransaction(deleteButton.dataset.cardTransactionId);
    }
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

  async function shiftCardInvoiceMonth(delta) {
    await setCardInvoiceMonth(shiftMonth(state.cardInvoiceMonth, delta));
  }

  async function setCardInvoiceMonth(month) {
    if (!isValidMonthValue(month)) {
      return;
    }
    state.cardInvoiceMonth = month;
    resetCardTransactionForm();
    setMessage(cardInvoiceMessage, "");
    await loadCardInvoice();
    renderCreditCards();
  }

  function cardReconciledBalance(cardId) {
    const currentMonth = currentMonthValue();
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

  function cardOpenBalance(cardId, untilInvoiceMonth = null) {
    const transactionTotal = state.cardTransactions.reduce((total, transaction) => {
      if (String(transaction.credit_card_id) !== String(cardId)) {
        return total;
      }
      if (untilInvoiceMonth && transaction.invoice_month > untilInvoiceMonth) {
        return total;
      }
      const amount = Number(transaction.amount);
      return total + (transaction.type === "expense" ? amount : -amount);
    }, 0);
    const paidTotal = state.cardPayments.reduce((total, payment) => (
      String(payment.credit_card_id) === String(cardId) && (!untilInvoiceMonth || payment.invoice_month <= untilInvoiceMonth)
        ? total + Number(payment.amount)
        : total
    ), 0);
    return transactionTotal - paidTotal;
  }

  function creditCardCurrency(cardId) {
    const card = state.creditCards.find((entry) => String(entry.id) === String(cardId));
    return card ? card.currency : "BRL";
  }

  return {
    loadCreditCards,
    loadArchivedCreditCards,
    loadCardInvoice,
    loadCardTransactions,
    ensureSelectedCreditCard,
    renderCreditCards,
    renderCardInvoice,
    renderCreditCardPreferredPaymentAccounts,
    renderCardTransactionCategories,
    renderCardTransactionSubcategories,
    resetCreditCardForm,
    resetCardTransactionForm,
    updateCardSeriesState,
    setCardInvoiceMonth,
    shiftCardInvoiceMonth,
    cardReconciledBalance,
    cardOpenBalance,
    creditCardCurrency,
  };
}
