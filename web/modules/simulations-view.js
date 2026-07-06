import { api } from "./api.js";
import { formatMoney } from "./money-utils.js";
import { escapeHtml, formData, setMessage } from "./dom-utils.js";

export function registerSimulationsView({
  state,
  elements,
  formatMoney,
}) {
  const balanceHistoryChartTop = 24;
  const balanceHistoryChartBottom = 48;
  const balanceHistoryChartBaseline = 54;
  const balanceHistoryChartFlat = 36;
  const {
    simulationForm,
    simulationType,
    simulationDate,
    simulationAccount,
    simulationCategory,
    simulationSubcategory,
    simulationSeriesKind,
    simulationInstallmentCountLabel,
    simulationInstallmentCount,
    simulationRecurrenceGroup,
    simulationRecurrenceFrequency,
    simulationRecurrenceCount,
    simulationMessage,
    simulationCurrentBalance,
    simulationProjectedBalance,
    simulationDifference,
    simulationChart,
    simulationVirtualItems,
    simulationWarnings,
    resetSimulationButton,
  } = elements;

  simulationForm.addEventListener("submit", handleSubmit);
  resetSimulationButton.addEventListener("click", resetForm);
  simulationSeriesKind.addEventListener("change", syncSeriesFields);
  simulationType.addEventListener("change", () => {
    loadSimulationCategoriesForCurrentType();
  });
  simulationCategory.addEventListener("change", renderSimulationSubcategories);
  simulationAccount.addEventListener("change", () => {
    const account = state.accounts.find((entry) => String(entry.id) === simulationAccount.value);
    if (account) {
      clearSimulationResult();
    }
  });

  async function loadSimulationFormData() {
    const [accountsResponse] = await Promise.all([
      api("/api/checking-accounts"),
      loadSimulationCategoriesForCurrentType(),
    ]);
    state.accounts = accountsResponse.accounts || [];
    renderAccounts();
    if (state.selectedAccountId) {
      simulationAccount.value = String(state.selectedAccountId);
    }
    const account = state.accounts.find((entry) => String(entry.id) === simulationAccount.value);
    if (account) {
      clearSimulationResult();
    }
    simulationDate.value = new Date().toISOString().slice(0, 10);
  }

  async function loadSimulationCategoriesForCurrentType() {
    const group = simulationType.value === "income" ? "income" : "expense";
    const categoriesResponse = await api(`/api/categories?group=${group}`);
    state.categories = categoriesResponse.categories || [];
    renderCategories();
    renderSimulationSubcategories();
  }

  function renderAccounts() {
    const selectedValue = simulationAccount.value;
    simulationAccount.innerHTML = state.accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} · ${escapeHtml(account.currency || "BRL")}</option>`
    )).join("");
    if (state.accounts.some((account) => String(account.id) === String(selectedValue))) {
      simulationAccount.value = String(selectedValue);
    } else if (state.accounts[0]) {
      simulationAccount.value = String(state.accounts[0].id);
    }
  }

  function renderCategories() {
    const selectedValue = simulationCategory.value;
    simulationCategory.innerHTML = state.categories.map((category) => (
      `<option value="${category.id}">${escapeHtml(category.name)}</option>`
    )).join("");
    if (state.categories.some((category) => String(category.id) === String(selectedValue))) {
      simulationCategory.value = String(selectedValue);
    } else if (state.categories[0]) {
      simulationCategory.value = String(state.categories[0].id);
    }
    renderSimulationSubcategories();
  }

  function renderSimulationSubcategories() {
    const selectedCategoryId = simulationCategory.value;
    const category = state.categories.find((entry) => String(entry.id) === String(selectedCategoryId));
    const subcategories = category ? category.subcategories || [] : [];
    const selectedValue = simulationSubcategory.value;
    simulationSubcategory.innerHTML = '<option value="">Sem subcategoria</option>' + subcategories.map((subcategory) => (
      `<option value="${subcategory.id}">${escapeHtml(subcategory.name)}</option>`
    )).join("");
    if (subcategories.some((subcategory) => String(subcategory.id) === String(selectedValue))) {
      simulationSubcategory.value = String(selectedValue);
    }
  }

  function syncSeriesFields() {
    const isInstallment = simulationSeriesKind.value === "installment";
    simulationInstallmentCountLabel.hidden = !isInstallment;
    simulationInstallmentCount.disabled = !isInstallment;
    simulationRecurrenceGroup.hidden = simulationSeriesKind.value !== "recurring";
    simulationRecurrenceFrequency.disabled = simulationSeriesKind.value !== "recurring";
    simulationRecurrenceCount.disabled = simulationSeriesKind.value !== "recurring";
  }

  function resetForm() {
    simulationForm.reset();
    simulationDate.value = new Date().toISOString().slice(0, 10);
    simulationSeriesKind.value = "single";
    syncSeriesFields();
    clearSimulationResult();
    setMessage(simulationMessage, "", "");
  }

  function clearSimulationResult() {
    simulationCurrentBalance.textContent = "-";
    simulationProjectedBalance.textContent = "-";
    simulationDifference.textContent = "-";
    simulationChart.innerHTML = '<p class="muted-copy">Preencha o formulário e clique em Simular.</p>';
    simulationVirtualItems.innerHTML = "";
    simulationWarnings.innerHTML = "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage(simulationMessage, "", "");
    const payload = formData(simulationForm);
    try {
      const response = await api("/api/simulations/butterfly-effect", { method: "POST", body: payload });
      renderSimulation(response);
      setMessage(simulationMessage, "Simulação pronta.", "success");
    } catch (error) {
      setMessage(simulationMessage, error.message, "error");
    }
  }

  function renderSimulation(response) {
    const accountImpact = response.account_impact || {};
    const account = state.accounts.find((entry) => String(entry.id) === String(response.scenario?.account_id));
    const currency = account?.currency || "BRL";
    simulationCurrentBalance.textContent = formatMoney((accountImpact.current_balance_cents || 0) / 100, currency);
    simulationProjectedBalance.textContent = formatMoney((accountImpact.projected_balance_cents || 0) / 100, currency);
    simulationDifference.textContent = formatMoney((accountImpact.difference_cents || 0) / 100, currency);

    simulationChart.innerHTML = buildSimulationBalanceHistory(response.chart_series || [], currency);

    simulationVirtualItems.innerHTML = (response.virtual_items || []).map((item) => `
      <article class="simulation-item">
        <div>
          <strong>${escapeHtml(item.description)}</strong>
          <small>${escapeHtml(item.date)} · ${item.occurrence_index}/${item.occurrence_total}</small>
        </div>
        <strong>${item.impact_sign}${formatMoney(Math.abs((item.impact_cents || 0) / 100), currency)}</strong>
      </article>
    `).join("");

    simulationWarnings.innerHTML = (response.warnings || []).map((warning) => `
      <div class="simulation-warning">${escapeHtml(warning)}</div>
    `).join("");
  }

  function buildSimulationBalanceHistory(series, currency) {
    const rows = simulationBalanceHistoryRows(series, currency);
    if (!rows.length) {
      return '<div class="empty-state compact">Sem dados para exibir no gráfico.</div>';
    }
    const path = balanceHistoryPath(rows);
    const areaPath = balanceHistoryAreaPath(rows);
    const points = rows.map((row) => `
      <span class="invoice-history-point ${row.index === 0 ? "current" : "future"}" style="left: ${row.x}%; top: ${row.y}%"></span>
    `).join("");
    return `
      <div class="invoice-history-rail" role="list">
        <svg class="invoice-history-svg" viewBox="0 0 100 100" aria-hidden="true" preserveAspectRatio="none">
          <defs>
            <linearGradient id="simulationBalanceHistoryAreaGradient" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0%" stop-color="var(--accent)" stop-opacity="0.18"></stop>
              <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"></stop>
            </linearGradient>
          </defs>
          <path class="invoice-history-area account-balance-history-area" d="${areaPath}"></path>
          <path class="invoice-history-line future" d="${path}"></path>
        </svg>
        ${points}
        ${rows.map((row) => `
          <button class="invoice-history-card ${row.index === 0 ? "current" : ""}" type="button" role="listitem" aria-current="${row.index === 0 ? "true" : "false"}">
            <span>${escapeHtml(row.label)}</span>
            <em>${escapeHtml(row.description)}</em>
            <small>Saldo projetado</small>
            <strong class="${row.amount < 0 ? "danger-text" : row.amount > 0 ? "positive-text" : ""}">${formatMoney(Math.abs(row.amount), currency)}</strong>
          </button>
        `).join("")}
      </div>
    `;
  }

  function simulationBalanceHistoryRows(series, currency) {
    const rawRows = series.map((entry, index) => ({
      index,
      month: entry.month,
      label: shortMonthLabel(entry.month),
      description: Number(entry.simulated_total_cents || 0)
        ? `Simulado ${formatSignedMoney(entry.simulated_total_cents, currency)}`
        : "Previsto",
      amount: Number(projectedBalanceCents(entry)) / 100,
      currency,
    }));
    const values = rawRows.map((row) => row.amount);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    const denominator = Math.max(rawRows.length - 1, 1);
    return rawRows.map((row, index) => ({
      ...row,
      x: rawRows.length === 1 ? 50 : 8 + (index / denominator) * 84,
      y: range === 0
        ? balanceHistoryChartFlat
        : balanceHistoryChartBottom - ((row.amount - min) / range) * (balanceHistoryChartBottom - balanceHistoryChartTop),
    }));
  }

  function projectedBalanceCents(entry) {
    if (entry.projected_balance_cents !== undefined && entry.projected_balance_cents !== null) {
      return entry.projected_balance_cents;
    }
    if (entry.real_balance_cents !== undefined && entry.real_balance_cents !== null) {
      return Number(entry.real_balance_cents || 0) + Number(entry.simulated_total_cents || 0);
    }
    return entry.projected_total_cents || 0;
  }

  function balanceHistoryPath(rows) {
    if (rows.length < 2) {
      return "";
    }
    return smoothBalancePath(rows.map((row) => ({ x: row.x, y: row.y })));
  }

  function balanceHistoryAreaPath(rows) {
    const points = rows.map((row) => ({ x: row.x, y: row.y }));
    if (points.length < 2) {
      return "";
    }
    const line = smoothBalancePath(points);
    const first = points[0];
    const last = points[points.length - 1];
    return `${line} L ${last.x} ${balanceHistoryChartBaseline} L ${first.x} ${balanceHistoryChartBaseline} Z`;
  }

  function smoothBalancePath(points) {
    return points.reduce((path, point, index) => {
      if (index === 0) {
        return `M ${point.x} ${point.y}`;
      }
      const previous = points[index - 1];
      const midX = (previous.x + point.x) / 2;
      return `${path} C ${midX} ${previous.y}, ${midX} ${point.y}, ${point.x} ${point.y}`;
    }, "");
  }

  function shortMonthLabel(month) {
    const [year, monthNumber] = String(month).split("-").map(Number);
    if (!year || !monthNumber) {
      return month;
    }
    const date = new Date(year, monthNumber - 1, 1);
    return date.toLocaleDateString("pt-BR", { month: "short" }).replace(".", "");
  }

  function formatSignedMoney(cents, currency) {
    const amount = Number(cents || 0) / 100;
    const prefix = amount >= 0 ? "+" : "-";
    return `${prefix}${formatMoney(Math.abs(amount), currency)}`;
  }

  return { loadSimulationFormData, resetForm, renderSimulation };
}
