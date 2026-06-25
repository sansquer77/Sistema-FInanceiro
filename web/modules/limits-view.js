export function registerLimitsView({
  state,
  elements,
  navButtons,
  api,
  currentMonthValue,
  shiftMonth,
  formatMonthLabel,
  formatMoney,
  formatPercent,
  formData,
  setMessage,
  emptyState,
  escapeHtml,
  onLimitsChanged = () => {},
  goToLimits = () => {},
}) {
  const {
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
  } = elements;

  limitForm.addEventListener("submit", handleLimitSubmit);
  limitCategory.addEventListener("change", renderLimitSubcategories);
  previousLimitMonthButton.addEventListener("click", () => shiftLimitMonth(-1));
  nextLimitMonthButton.addEventListener("click", () => shiftLimitMonth(1));
  cancelLimitEditButton.addEventListener("click", resetLimitForm);

  async function loadSpendingLimits() {
    const response = await api(`/api/spending-limits?month=${encodeURIComponent(state.limitMonth)}`);
    state.spendingLimits = response.limits;
  }

  async function loadCurrentSpendingLimits() {
    const response = await api(`/api/spending-limits?month=${encodeURIComponent(currentMonthValue())}`);
    state.currentSpendingLimits = response.limits;
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
      await loadCurrentSpendingLimits();
      renderLimits();
      onLimitsChanged();
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
      await loadCurrentSpendingLimits();
      renderLimits();
      onLimitsChanged();
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

  async function shiftLimitMonth(delta) {
    state.limitMonth = shiftMonth(state.limitMonth, delta);
    resetLimitForm();
    await loadSpendingLimits();
    renderLimits();
  }

  function renderLimits() {
    limitMonthLabel.textContent = formatMonthLabel(state.limitMonth);
    limitMonthInput.value = state.limitMonth;
    renderLimitCategories();
    renderSpendingLimitList();
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

  function renderLimitAlerts() {
    const exceededRows = exceededCurrentLimitRows();
    navButtons.forEach((button) => {
      if (button.dataset.view === "limits") {
        button.classList.toggle("has-alert", exceededRows.length > 0);
      }
    });
    if (!cockpitLimitAlert) {
      return;
    }
    if (exceededRows.length === 0) {
      cockpitLimitAlert.hidden = true;
      cockpitLimitAlert.innerHTML = "";
      return;
    }
    const worst = exceededRows[0];
    const overflowTotal = exceededRows.reduce((total, row) => total + Math.abs(row.remaining), 0);
    cockpitLimitAlert.hidden = false;
    cockpitLimitAlert.innerHTML = `
      <button class="limit-alert-card" type="button" data-go-limits>
        <span class="limit-alert-beacon" aria-hidden="true"></span>
        <span>
          <strong>${exceededRows.length} limite(s) estourado(s)</strong>
          <small>Maior desvio: ${escapeHtml(worst.label)} em ${formatMoney(Math.abs(worst.remaining), "BRL")}. Total excedido: ${formatMoney(overflowTotal, "BRL")}.</small>
        </span>
        <b>Ver limites</b>
      </button>
    `;
    cockpitLimitAlert.querySelector("[data-go-limits]").addEventListener("click", goToLimits);
  }

  function exceededCurrentLimitRows() {
    return spendingLimitRows(state.currentSpendingLimits)
      .filter((row) => row.percent > 1)
      .sort((a, b) => Math.abs(b.remaining) - Math.abs(a.remaining));
  }

  function spendingLimitRows(limits = state.spendingLimits) {
    const spentIndex = buildSpendingLimitSpentIndex(limits);
    return limits.map((limit) => {
      const spent = spendingLimitSpentFromIndex(spentIndex, limit);
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

  function buildSpendingLimitSpentIndex(limits = state.spendingLimits) {
    const months = new Set(limits.map((limit) => limit.month).filter(Boolean));
    const index = new Map();
    const addSpent = (month, categoryId, subcategoryId, amount) => {
      const categoryKey = spendingLimitSpentKey(month, categoryId, "");
      index.set(categoryKey, (index.get(categoryKey) || 0) + amount);
      if (subcategoryId) {
        const subcategoryKey = spendingLimitSpentKey(month, categoryId, subcategoryId);
        index.set(subcategoryKey, (index.get(subcategoryKey) || 0) + amount);
      }
    };
    state.transactions.forEach((transaction) => {
      const month = transaction.date ? transaction.date.slice(0, 7) : "";
      if (transaction.type !== "expense" || (months.size && !months.has(month))) {
        return;
      }
      addSpent(month, transaction.category_id, transaction.subcategory_id, Number(transaction.amount_brl || transaction.amount));
    });
    state.cardTransactions.forEach((transaction) => {
      const month = transaction.invoice_month || (transaction.date ? transaction.date.slice(0, 7) : "");
      if (transaction.type !== "expense" || (months.size && !months.has(month))) {
        return;
      }
      addSpent(month, transaction.category_id, transaction.subcategory_id, Number(transaction.amount_brl || transaction.amount));
    });
    return index;
  }

  function spendingLimitSpentFromIndex(index, limit) {
    return index.get(spendingLimitSpentKey(limit.month, limit.category_id, limit.subcategory_id || "")) || 0;
  }

  function spendingLimitSpentKey(month, categoryId, subcategoryId) {
    return `${month || ""}|${categoryId || ""}|${subcategoryId || ""}`;
  }

  return {
    loadSpendingLimits,
    loadCurrentSpendingLimits,
    renderLimits,
    renderLimitAlerts,
    resetLimitForm,
  };
}
