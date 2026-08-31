import { api } from "./api.js";
import { formatMoney } from "./money-utils.js";
import { escapeHtml, formData, setFormBusy, setMessage, stateMarkup } from "./dom-utils.js";
import { formatDate, formatShortMonthName, todayLocalDateValue } from "./date-utils.js";
import { chartToken, renderChart } from "./chart-adapter.js";
import { createLoadPolicy } from "./load-policy.js";

export function registerSimulationsView({
  state,
  elements,
  formatMoney,
}) {
  const formDataLoadPolicy = createLoadPolicy();
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
    simulationMessage,
    simulationCurrentBalance,
    simulationProjectedBalance,
    simulationDifference,
    simulationChart,
    simulationWeeklyProjection,
    simulationWarnings,
    resetSimulationButton,
  } = elements;
  const weeklyProjectionElement = simulationWeeklyProjection
    || document.querySelector("#simulationWeeklyProjection");

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

  async function loadSimulationFormData({ force = false } = {}) {
    return formDataLoadPolicy.run(async () => {
      const accountsResponse = await api("/api/checking-accounts");
      state.accounts = accountsResponse.accounts || [];
      renderAccounts();
      if (state.selectedAccountId) simulationAccount.value = String(state.selectedAccountId);
      const account = state.accounts.find((entry) => String(entry.id) === simulationAccount.value);
      if (account) clearSimulationResult();
      simulationDate.value = todayLocalDateValue();
    }, { force });
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
    if (weeklyProjectionElement) {
      weeklyProjectionElement.innerHTML = "";
    }
    simulationWarnings.innerHTML = "";
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage(simulationMessage, "", "");
    const payload = formData(simulationForm);
    setFormBusy(simulationForm, true);
    try {
      const response = await api("/api/simulations/butterfly-effect", { method: "POST", body: payload });
      renderSimulation(response);
      setMessage(simulationMessage, "Simulação pronta.", "success");
    } catch (error) {
      setMessage(simulationMessage, error.message, "error");
    } finally {
      setFormBusy(simulationForm, false);
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

    renderSimulationBalanceHistory(response.chart_series || [], currency);
    if (weeklyProjectionElement) {
      const projection = response.daily_projection || response.weekly_projection || [];
      weeklyProjectionElement.innerHTML = buildDailyProjectionTable(
        projection,
        response.daily_projection_summary || {},
        currency,
        response.scenario?.date,
      );
    }

    simulationWarnings.innerHTML = (response.warnings || []).map((warning) => `
      <div class="simulation-warning">${escapeHtml(warning)}</div>
    `).join("");
  }

  function renderSimulationBalanceHistory(series, currency) {
    const rows = simulationBalanceHistoryRows(series, currency);
    if (!rows.length) {
      simulationChart.innerHTML = stateMarkup("Preencha o cenário e execute a simulação para gerar o gráfico.", { kind: "empty" });
      return;
    }
    simulationChart.innerHTML = `
      <div class="invoice-history-rail" role="list">
        <div class="invoice-history-apex"></div>
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
    renderChart(simulationChart.querySelector(".invoice-history-apex"), {
      chart: { type: "area", height: 170, sparkline: { enabled: true } },
      series: [
        { name: "Saldo previsto", data: rows.map((row) => row.forecastAmount) },
        { name: "Saldo com simulação", data: rows.map((row) => row.simulatedAmount) },
      ],
      colors: [chartToken("--muted", "#6b7280"), chartToken("--accent", "#5f7fff")],
      stroke: { curve: "smooth", width: [2, 3], dashArray: [5, 0] },
      fill: { type: "gradient", gradient: { opacityFrom: 0.18, opacityTo: 0.01 } },
      markers: { size: 3 },
      tooltip: { y: { formatter: (value) => formatMoney(value, currency) } },
    });
  }

  function buildDailyProjectionTable(projection, summary, currency, scenarioDate) {
    if (!projection.length) {
      return "";
    }
    const headerCells = projection.map((entry, index) => {
      const label = entry.date === scenarioDate ? "Cenário" : index === 0 ? "Hoje" : `Dia ${index}`;
      const dateText = formatDate(entry.date);
      return `<th scope="col"><span class="weekly-projection-label">${escapeHtml(label)}</span><span class="weekly-projection-date">${escapeHtml(dateText)}</span></th>`;
    }).join("");
    const buildRow = (label, key, isDifference) => {
      const cells = projection.map((entry) => {
        const cents = entry[key] || 0;
        const text = formatMoney(Math.abs(cents) / 100, currency);
        const toneClass = cents < 0 ? "danger-text" : cents > 0 && isDifference ? "positive-text" : "";
        return `<td class="${toneClass}">${escapeHtml(text)}</td>`;
      }).join("");
      return `<tr><th scope="row">${escapeHtml(label)}</th>${cells}</tr>`;
    };
    return `
      ${buildDailyProjectionSummary(summary)}
      <div class="weekly-projection-table-wrapper">
        <table class="weekly-projection-table">
          <thead>
            <tr>
              <th scope="col" class="weekly-projection-row-header"></th>
              ${headerCells}
            </tr>
          </thead>
          <tbody>
            ${buildRow("Previsto", "forecast_balance_cents", false)}
            ${buildRow("Simulado", "simulated_balance_cents", false)}
            ${buildRow("Diferença", "difference_cents", true)}
          </tbody>
        </table>
      </div>
    `;
  }

  function buildDailyProjectionSummary(summary) {
    const forecastDate = summary.forecast_first_negative_date;
    const simulatedDate = summary.simulated_first_negative_date;
    if (summary.effect === "causes_negative" && simulatedDate) {
      return `<div class="simulation-cash-flow-status danger">A simulação deixa a conta negativa em <strong>${escapeHtml(formatDate(simulatedDate))}</strong>.</div>`;
    }
    if (summary.effect === "avoids_negative" && forecastDate) {
      const complement = simulatedDate
        ? ` e adia o risco para ${escapeHtml(formatDate(simulatedDate))}`
        : " dentro desta janela";
      return `<div class="simulation-cash-flow-status positive">A simulação evita o saldo negativo previsto para <strong>${escapeHtml(formatDate(forecastDate))}</strong>${complement}.</div>`;
    }
    if (simulatedDate) {
      return `<div class="simulation-cash-flow-status danger">A conta permanece com risco de saldo negativo a partir de <strong>${escapeHtml(formatDate(simulatedDate))}</strong>.</div>`;
    }
    return '<div class="simulation-cash-flow-status positive">Nenhum saldo negativo projetado nos 15 dias exibidos.</div>';
  }

  function applyAmountTone(element, amountCents) {
    element.classList.toggle("danger-text", amountCents < 0);
    element.classList.toggle("positive-text", amountCents > 0);
    element.closest(".summary-card")?.classList.toggle("danger", amountCents < 0);
    element.closest(".summary-card")?.classList.toggle("positive", amountCents > 0);
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

  return {
    loadSimulationFormData,
    markFormDataDirty: formDataLoadPolicy.markDirty,
    resetFormDataCache: formDataLoadPolicy.reset,
    resetForm,
    renderSimulation,
  };
}
