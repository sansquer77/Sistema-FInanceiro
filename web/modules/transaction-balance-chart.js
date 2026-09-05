import { stateMarkup } from "./dom-utils.js";
import { centeredMonthlyAxis, centeredMonthlyPoints, chartToken, renderChart } from "./chart-adapter.js";

export function createTransactionBalanceChart({
  state,
  element,
  formatMoney,
  formatShortMonthName,
  escapeHtml,
  shiftMonth,
  monthEndDate,
  getBalanceUntil,
  selectedAccountTransactions,
  setTransactionMonth,
}) {
  element?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-transaction-balance-month]");
    if (button) await setTransactionMonth(button.dataset.transactionBalanceMonth);
  });

  function render() {
    if (!element) return;
    const account = state.accounts.find((entry) => String(entry.id) === String(state.selectedAccountId));
    if (!account) {
      element.innerHTML = stateMarkup("Selecione uma conta para visualizar a projeção de saldo.", { kind: "info" });
      return;
    }
    const transactions = selectedAccountTransactions(state.transactions.length ? state.transactions : state.accountTransactions);
    const rows = [-1, 0, 1, 2, 3].map((offset) => {
      const month = shiftMonth(state.transactionMonth, offset);
      const balance = getBalanceUntil(monthEndDate(month), transactions, offset < 0);
      return {
        offset,
        month,
        label: formatShortMonthName(month),
        amount: balanceAmountForCurrency(balance, account.currency),
        currency: account.currency,
        isCurrent: offset === 0,
      };
    });
    element.innerHTML = `<div class="invoice-history-rail" role="list">
      ${rows.map((row) => {
        const amountText = formatMoney(Math.abs(row.amount), row.currency);
        return `<button class="invoice-history-card ${row.isCurrent ? "current" : ""} ${row.offset > 0 ? "future" : ""}" type="button" data-transaction-balance-month="${escapeHtml(row.month)}" role="listitem" aria-current="${row.isCurrent ? "true" : "false"}">
          <span>${escapeHtml(row.label)}</span>
          <strong class="${amountSizeClass(amountText)} ${row.amount < 0 ? "danger-text" : row.amount > 0 ? "positive-text" : ""}">${amountText}</strong>
        </button>`;
      }).join("")}
      <div class="invoice-history-plot" aria-hidden="true"><div class="invoice-history-apex"></div></div>
    </div>`;
    renderChart(element.querySelector(".invoice-history-apex"), {
      chart: { type: "area", height: 92, sparkline: { enabled: true } },
      series: [
        { name: "Conciliado", data: centeredMonthlyPoints(rows, (row) => row.offset <= 0 ? row.amount : null) },
        { name: "Previsto", data: centeredMonthlyPoints(rows, (row) => row.offset >= 0 ? row.amount : null) },
      ],
      colors: [chartToken("--accent", "#5f7fff"), chartToken("--accent", "#5f7fff")],
      stroke: { curve: "smooth", width: [3, 2], dashArray: [0, 5] },
      fill: { type: "solid", opacity: 0 },
      markers: { size: 4 },
      xaxis: centeredMonthlyAxis(rows),
      tooltip: { enabled: false },
    });
  }

  return { render };
}

function amountSizeClass(text) {
  const length = String(text || "").replace(/\s/g, "").length;
  if (length >= 18) return "chart-amount-xxs";
  if (length >= 13) return "chart-amount-xs";
  if (length >= 10) return "chart-amount-sm";
  return "";
}

function balanceAmountForCurrency(balance, currency) {
  if (balance instanceof Map) {
    if (balance.has(currency)) return Number(balance.get(currency) || 0);
    return [...balance.values()].reduce((total, value) => total + Number(value || 0), 0);
  }
  return Number(balance || 0);
}
