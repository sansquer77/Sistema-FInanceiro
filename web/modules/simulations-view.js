import { api } from "./api.js";
import { formatMoney } from "./money-utils.js";
import { escapeHtml, formData, setMessage } from "./dom-utils.js";
import { formatShortMonthName, todayLocalDateValue } from "./date-utils.js";

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
  simulationType.addEventListener("change", clearSimulationResult);
  simulationAccount.addEventListener("change", () => {
    const account = state.accounts.find((entry) => String(entry.id) === simulationAccount.value);
    if (account) {
      clearSimulationResult();
    }
  });

  async function loadSimulationFormData() {
    const accountsResponse = await api("/api/checking-accounts");
    state.accounts = accountsResponse.accounts || [];
    renderAccounts();
    if (state.selectedAccountId) {
      simulationAccount.value = String(state.selectedAccountId);
    }
    const account = state.accounts.find((entry) => String(entry.id) === simulationAccount.value);
    if (account) {
      clearSimulationResult();
    }
    simulationDate.value = todayLocalDateValue();
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
    simulationDate.value = todayLocalDateValue();
    simulationSeriesKind.value = "single";
    syncSeriesFields();
    clearSimulationResult();
    setMessage(simulationMessage, "", "");
  }

  function clearSimulationResult() {
    simulationCurrentBalance.textContent = "-";
    simulationProjectedBalance.textContent = "-";
    applyAmountTone(simulationProjectedBalance, 0);
    if (simulationDifference) {
      simulationDifference.textContent = "-";
    }
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
    const projectedBalanceCents = accountImpact.projected_balance_cents || 0;
    simulationProjectedBalance.textContent = formatMoney(projectedBalanceCents / 100, currency);
    applyAmountTone(simulationProjectedBalance, projectedBalanceCents);
    if (simulationDifference) {
      simulationDifference.textContent = formatMoney((accountImpact.difference_cents || 0) / 100, currency);
    }

    simulationChart.innerHTML = buildSimulationBalanceHistory(response.chart_series || [], currency);

    simulationVirtualItems.innerHTML = (response.virtual_items || []).map((item) => `
      <article class="simulation-item">
        <div>
          <strong>${escapeHtml(item.description || virtualItemLabel(response.scenario, item))}</strong>
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
    const forecastPath = balanceHistoryPath(rows, "forecastY");
    const simulatedPath = balanceHistoryPath(rows, "simulatedY");
    const areaPath = balanceHistoryAreaPath(rows, "simulatedY");
    const forecastPoints = rows.map((row) => `
      <span class="invoice-history-point simulation-point forecast" style="left: ${row.x}%; top: ${row.forecastY}%"></span>
    `).join("");
    const simulatedPoints = rows.map((row) => `
      <span class="invoice-history-point simulation-point ${row.index === 0 ? "current" : "future"}" style="left: ${row.x}%; top: ${row.simulatedY}%"></span>
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
          <path class="invoice-history-line simulation-forecast-line" d="${forecastPath}"></path>
          <path class="invoice-history-line future" d="${simulatedPath}"></path>
        </svg>
        ${forecastPoints}
        ${simulatedPoints}
        ${rows.map((row) => {
          const simulatedText = formatMoney(Math.abs(row.simulatedAmount), currency);
          const forecastText = formatMoney(Math.abs(row.forecastAmount), currency);
          return `
          <button class="invoice-history-card ${row.index === 0 ? "current" : ""}" type="button" role="listitem" aria-current="${row.index === 0 ? "true" : "false"}">
            <span>${escapeHtml(row.label)}</span>
            <strong class="${chartAmountSizeClass(simulatedText)} ${row.simulatedAmount < 0 ? "danger-text" : row.simulatedAmount > 0 ? "positive-text" : ""}">${simulatedText}</strong>
            <small class="${chartAmountSizeClass(forecastText)}">${forecastText}</small>
          </button>
        `;
        }).join("")}
      </div>
      <div class="simulation-chart-legend">
        <span><i class="legend-line forecast"></i>Saldo previsto da conta</span>
        <span><i class="legend-line simulated"></i>Saldo com simulação</span>
      </div>
    `;
  }

  function applyAmountTone(element, amountCents) {
    element.classList.toggle("danger-text", amountCents < 0);
    element.classList.toggle("positive-text", amountCents > 0);
    element.closest(".summary-card")?.classList.toggle("danger", amountCents < 0);
    element.closest(".summary-card")?.classList.toggle("positive", amountCents > 0);
  }

  function virtualItemLabel(scenario = {}, item = {}) {
    const base = scenario.type === "income" ? "Receita simulada" : "Despesa simulada";
    return item.occurrence_total > 1 ? `${base} (${item.occurrence_index}/${item.occurrence_total})` : base;
  }

  function chartAmountSizeClass(text) {
    const length = String(text || "").replace(/\s/g, "").length;
    if (length >= 18) {
      return "chart-amount-xxs";
    }
    if (length >= 13) {
      return "chart-amount-xs";
    }
    if (length >= 10) {
      return "chart-amount-sm";
    }
    return "";
  }

  function simulationBalanceHistoryRows(series, currency) {
    const rawRows = series.map((entry, index) => ({
      index,
      month: entry.month,
      label: formatShortMonthName(entry.month),
      forecastAmount: Number(entry.real_balance_cents || 0) / 100,
      simulatedAmount: Number(projectedBalanceCents(entry)) / 100,
      currency,
    }));
    const values = rawRows.flatMap((row) => [row.forecastAmount, row.simulatedAmount]);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min;
    const denominator = Math.max(rawRows.length - 1, 1);
    return rawRows.map((row, index) => ({
      ...row,
      x: rawRows.length === 1 ? 50 : 8 + (index / denominator) * 84,
      forecastY: chartY(row.forecastAmount, min, range),
      simulatedY: chartY(row.simulatedAmount, min, range),
    }));
  }

  function chartY(amount, min, range) {
    return range === 0
        ? balanceHistoryChartFlat
        : balanceHistoryChartBottom - ((amount - min) / range) * (balanceHistoryChartBottom - balanceHistoryChartTop);
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

  function balanceHistoryPath(rows, yKey = "simulatedY") {
    if (rows.length < 2) {
      return "";
    }
    return smoothBalancePath(rows.map((row) => ({ x: row.x, y: row[yKey] })));
  }

  function balanceHistoryAreaPath(rows, yKey = "simulatedY") {
    const points = rows.map((row) => ({ x: row.x, y: row[yKey] }));
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

  return { loadSimulationFormData, resetForm, renderSimulation };
}
