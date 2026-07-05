import { api } from "./api.js";
import { formatMoney, moneyInputValue, parseDecimalInput } from "./money-utils.js";
import { escapeHtml, formData, setMessage } from "./dom-utils.js";

export function registerSimulationsView({
  state,
  elements,
  formatMoney,
  formatDate,
  onSimulationsChanged = () => {},
}) {
  const {
    simulationForm,
    simulationType,
    simulationAmount,
    simulationDate,
    simulationAccount,
    simulationDescription,
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
      simulationCurrentBalance.textContent = formatMoney(account.current_balance || account.current_balance_cents || 0, account.currency || "BRL");
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
      simulationCurrentBalance.textContent = formatMoney(account.current_balance || account.current_balance_cents || 0, account.currency || "BRL");
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
    simulationCurrentBalance.textContent = "R$ 0,00";
    simulationProjectedBalance.textContent = "R$ 0,00";
    simulationDifference.textContent = "R$ 0,00";
    simulationChart.innerHTML = '<p class="muted-copy">Preencha o formulário e clique em Simular.</p>';
    simulationVirtualItems.innerHTML = "";
    simulationWarnings.innerHTML = "";
    setMessage(simulationMessage, "", "");
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage(simulationMessage, "", "");
    const payload = formData(simulationForm);
    payload.amount = payload.amount.replace(".", "").replace(",", ".");
    try {
      const response = await api("/api/simulations/butterfly-effect", { method: "POST", body: payload });
      renderSimulation(response);
      setMessage(simulationMessage, "Simulação pronta.", "success");
      onSimulationsChanged();
    } catch (error) {
      setMessage(simulationMessage, error.message, "error");
    }
  }

  function renderSimulation(response) {
    const accountImpact = response.account_impact || {};
    const account = state.accounts.find((entry) => String(entry.id) === String(response.scenario?.account_id));
    const currency = account?.currency || "BRL";
    simulationCurrentBalance.textContent = formatMoney(accountImpact.current_balance_cents || 0, currency);
    simulationProjectedBalance.textContent = formatMoney(accountImpact.projected_balance_cents || 0, currency);
    simulationDifference.textContent = formatMoney(accountImpact.difference_cents || 0, currency);

    const chartItems = buildSimulationChartItems(accountImpact, currency);
    simulationChart.innerHTML = chartItems;

    simulationVirtualItems.innerHTML = (response.virtual_items || []).map((item) => `
      <article class="simulation-item">
        <div>
          <strong>${escapeHtml(item.description)}</strong>
          <small>${escapeHtml(item.date)} · ${item.occurrence_index}/${item.occurrence_total}</small>
        </div>
        <strong>${item.impact_sign}${formatMoney(Math.abs(item.impact_cents || 0), currency)}</strong>
      </article>
    `).join("");

    simulationWarnings.innerHTML = (response.warnings || []).map((warning) => `
      <div class="simulation-warning">${escapeHtml(warning)}</div>
    `).join("");
  }

  function buildSimulationChartItems(accountImpact, currency) {
    const currentBalance = Math.abs(accountImpact.current_balance_cents || 0);
    const difference = Math.abs(accountImpact.difference_cents || 0);
    const chartParts = [
      {
        label: "Saldo atual",
        total: currentBalance || 1,
        kind: "base",
      },
      {
        label: accountImpact.difference_cents >= 0 ? "Impacto positivo" : "Impacto negativo",
        total: difference || 1,
        kind: accountImpact.difference_cents >= 0 ? "positive" : "negative",
      },
    ];
    const total = chartParts.reduce((sum, item) => sum + item.total, 0);
    if (!total) {
      return '<div class="empty-state compact">Sem dados para exibir no gráfico.</div>';
    }
    return `
      <div class="donut-chart">
        ${donutSvg(chartParts, total)}
        <div class="donut-center">
          <span>Saldo projetado</span>
          <strong>${formatMoney(accountImpact.projected_balance_cents || 0, currency)}</strong>
        </div>
      </div>
      <div class="chart-list">
        ${chartParts.map((item, index) => `
          <div class="chart-row">
            <span><i style="background:${impactColor(item.kind, index)}"></i>${escapeHtml(item.label)}</span>
            <strong>${formatMoney(item.total, currency)}</strong>
          </div>
        `).join("")}
      </div>
    `;
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
    return `<svg viewBox="0 0 120 120" role="img" aria-label="Gráfico da simulação">${circles}</svg>`;
  }

  function impactColor(kind, index) {
    if (kind === "positive") {
      return "var(--positive)";
    }
    if (kind === "negative") {
      return "var(--danger)";
    }
    return chartColor(index);
  }

  function chartColor(index) {
    const fallbackPalette = ["#14b8a6", "#6366f1", "#f97316", "#ec4899", "#22c55e", "#3b82f6"];
    const tokenName = `--chart-${(index % fallbackPalette.length) + 1}`;
    const tokenColor = getComputedStyle(document.documentElement).getPropertyValue(tokenName).trim();
    return tokenColor || fallbackPalette[index % fallbackPalette.length];
  }

  return { loadSimulationFormData, resetForm, renderSimulation };
}
