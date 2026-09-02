import { createReportStatement } from "./report-statement.js";
import { createReportEvolution } from "./report-evolution.js";
import { api, fetchAllListed } from "./api.js";
import { stateMarkup } from "./dom-utils.js";
import { bindRovingTablist, syncRovingTabState, transitionView } from "./tab-utils.js";
import { renderChart } from "./chart-adapter.js";
import { renderVirtualList } from "./virtual-list.js";

export function registerReportsView({
  state,
  elements,
  shiftMonth,
  formatDate,
  formatMonthLabel,
  formatMonthShortLabel,
  formatMoney,
  formatPercent,
  escapeHtml,
  isInvestmentTransaction,
  chartColor,
}) {
  let tagsRequestId = 0;
  const {
    reportMonthLabel,
    previousReportMonthButton,
    nextReportMonthButton,
    reportTabs,
    reportIncomeSummary,
    reportExpenseSummary,
    reportInvestmentSummary,
    reportResultSummary,
    reportAccountFilter,
    reportAccountSelect,
    statementControls,
    printStatementButton,
    reportContent,
  } = elements;

  const statement = createReportStatement({
    state, elements, api, renderReports, formatDate, formatMonthLabel,
    formatMoney, formatPercent, escapeHtml, chartColor, reportItemClassification,
  });
  createReportEvolution({
    reportContent, api, formatMoney, formatMonthShortLabel,
  });

  previousReportMonthButton.addEventListener("click", () => shiftReportMonth(-1));
  nextReportMonthButton.addEventListener("click", () => shiftReportMonth(1));
  bindRovingTablist(reportTabs, {
    valueFor: (button) => button.dataset.reportTab,
    onSelect: switchReportTab,
  });
  reportAccountSelect.addEventListener("change", () => {
    state.reportAccountId = reportAccountSelect.value;
    renderReports();
  });
  reportContent.addEventListener("click", handleReportContentClick);

  function renderReports() {
    statement.invalidate();
    if (state.reportTab !== "tags") tagsRequestId += 1;
    reportMonthLabel.textContent = formatMonthShortLabel(state.reportMonth);
    syncRovingTabState(reportTabs, state.reportTab, (button) => button.dataset.reportTab);
    renderReportAccountOptions();
    reportAccountFilter.hidden = state.reportTab !== "accounts";
    statementControls.hidden = state.reportTab !== "statement";
    statement.renderStatementScopeOptions();
    printStatementButton.hidden = state.reportTab !== "statement";
    printStatementButton.disabled = true;
    reportContent.classList.toggle("statement-print-area", state.reportTab === "statement");
    if (state.reportOverviewMonth !== state.reportMonth) {
      renderReportLoading();
      if (state.reportOverviewLoadingMonth !== state.reportMonth) loadReportOverview(state.reportMonth);
      if (!["tags", "statement"].includes(state.reportTab) && state.reportDataLoadingMonth !== state.reportMonth) {
        loadReportMonth(state.reportMonth);
      }
      return;
    }
    renderReportOverview();
    if (state.reportTab === "tags" || state.reportTab === "statement") {
      if (state.reportTab === "tags") renderTagsReport();
      else statement.renderStatementReport();
      return;
    }
    if (state.reportDataMonth !== state.reportMonth) {
      renderReportLoading();
      loadReportMonth(state.reportMonth);
      return;
    }
    const items = reportItemsForMonth(state.reportMonth);
    if (state.reportTab === "cashflow") {
      renderCashflowReport(items);
      return;
    }
    if (state.reportTab === "accounts") {
      renderAccountsReport();
      return;
    }
    if (state.reportTab === "subcategories") {
      renderSubcategoriesReport(items);
      return;
    }
    renderCategoriesReport(items);
  }

  function renderReportOverview() {
    const raw = state.reportOverview?.totals_by_type || {};
    const income = new Map(Object.entries(raw.income || {}).map(([currency, cents]) => [currency, Number(cents) / 100]));
    const expense = new Map(Object.entries(raw.expense || {}).map(([currency, cents]) => [currency, Number(cents) / 100]));
    const investment = new Map(Object.entries(raw.investment || {}).map(([currency, cents]) => [currency, Number(cents) / 100]));
    const result = new Map(income);
    mergeMoneyTotals(result, expense, -1);
    mergeMoneyTotals(result, investment, -1);
    reportIncomeSummary.innerHTML = formatMoneyTotals(income);
    reportExpenseSummary.innerHTML = formatMoneyTotals(expense);
    reportInvestmentSummary.innerHTML = formatMoneyTotals(investment);
    reportResultSummary.innerHTML = formatMoneyTotals(result);
    reportResultSummary.classList.toggle("danger-text", [...result.values()].some((total) => total < 0));
    reportResultSummary.classList.toggle("positive-text", [...result.values()].some((total) => total > 0) && ![...result.values()].some((total) => total < 0));
  }

  async function loadReportOverview(month) {
    const requestId = ++state.reportOverviewRequestId;
    state.reportOverviewLoadingMonth = month;
    try {
      const overview = await api(`/api/reports/overview?month=${encodeURIComponent(month)}`);
      if (requestId !== state.reportOverviewRequestId || state.reportMonth !== month) return;
      state.reportOverview = overview;
      state.reportOverviewMonth = month;
      renderReports();
    } catch (error) {
      if (requestId !== state.reportOverviewRequestId || state.reportMonth !== month) return;
      reportContent.innerHTML = stateMarkup(error.message, { kind: "error" });
    } finally {
      if (requestId === state.reportOverviewRequestId) state.reportOverviewLoadingMonth = "";
    }
  }

  function renderReportLoading() {
    reportIncomeSummary.textContent = "—";
    reportExpenseSummary.textContent = "—";
    reportInvestmentSummary.textContent = "—";
    reportResultSummary.textContent = "—";
    printStatementButton.disabled = true;
    reportContent.innerHTML = stateMarkup("Carregando o recorte mensal do relatório.", { kind: "loading" });
  }

  async function loadReportMonth(month) {
    const requestId = ++state.reportDataRequestId;
    state.reportDataLoadingMonth = month;
    try {
      const [transactions, cardTransactions] = await Promise.all([
        fetchAllListed(`/api/transactions?month=${encodeURIComponent(month)}`, "transactions"),
        fetchAllListed(`/api/credit-card-transactions?month=${encodeURIComponent(month)}`, "transactions"),
      ]);
      if (requestId !== state.reportDataRequestId || state.reportMonth !== month) return;
      state.reportTransactions = transactions;
      state.reportCardTransactions = cardTransactions;
      state.reportDataMonth = month;
      renderReports();
    } catch (error) {
      if (requestId !== state.reportDataRequestId || state.reportMonth !== month) return;
      reportContent.innerHTML = stateMarkup(error.message, { kind: "error" });
    } finally {
      if (requestId === state.reportDataRequestId) state.reportDataLoadingMonth = "";
    }
  }

  function renderReportAccountOptions() {
    const options = state.accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("");
    reportAccountSelect.innerHTML = options || '<option value="">Cadastre uma conta</option>';
    reportAccountSelect.disabled = state.accounts.length === 0;
    if (!state.accounts.some((account) => String(account.id) === String(state.reportAccountId))) {
      state.reportAccountId = state.accounts[0] ? String(state.accounts[0].id) : "";
    }
    reportAccountSelect.value = state.reportAccountId;
  }

  function renderCategoriesReport(items) {
    const sections = [
      ["Despesas", "expense"],
      ["Receitas", "income"],
      ["Investimentos", "investment"],
    ];
    reportContent.innerHTML = sections.map(([title, type]) => (
      reportRankedSection(title, groupReportItems(items.filter((item) => item.reportType === type), "category"), `Nenhum item em ${title.toLowerCase()} neste mês.`)
    )).join("");
    virtualizeReportLists();
  }

  function renderSubcategoriesReport(items) {
    const sections = [
      ["Despesas", "expense"],
      ["Receitas", "income"],
      ["Investimentos", "investment"],
    ];
    reportContent.innerHTML = sections.map(([title, type]) => (
      reportRankedSection(title, groupReportItems(items.filter((item) => item.reportType === type), "subcategory"), `Nenhuma subcategoria em ${title.toLowerCase()} neste mês.`)
    )).join("");
    virtualizeReportLists();
  }

  async function renderTagsReport() {
    // spec: relatorios/relatorios v2.22 — relatório de tags agrupado por tag com
    // Receitas, Despesas, Saldo e Investimentos, separados por moeda.
    const requestId = ++tagsRequestId;
    const requestedMonth = state.reportMonth;
    reportContent.setAttribute("aria-busy", "true");
    reportContent.classList.add("is-refreshing");
    reportContent.innerHTML = stateMarkup("Consolidando os lançamentos classificados com tags.", { kind: "loading" });
    try {
      const url = new URL("/api/reports/tags", window.location.origin);
      url.searchParams.set("month", state.reportMonth);
      const response = await api(url.pathname + url.search);
      if (requestId !== tagsRequestId || state.reportTab !== "tags" || state.reportMonth !== requestedMonth) return;
      const rows = response.tags || [];
      if (!rows.length) {
        reportContent.innerHTML = stateMarkup("Adicione tags aos lançamentos ou selecione outro mês.", { kind: "empty" });
        return;
      }
      const body = rows.map((row) => {
        const income = tagCurrencyTotals(row.income_by_currency);
        const expense = tagCurrencyTotals(row.expense_by_currency);
        const investment = tagCurrencyTotals(row.investment_by_currency);
        const balance = new Map();
        mergeMoneyTotals(balance, income);
        mergeMoneyTotals(balance, expense, -1);
        return `
          <tr>
            <td><strong>${escapeHtml(row.tag)}</strong><span>${row.count} lançamento(s)</span></td>
          <td class="money-cell positive-text">${formatTagMoneyTotals(income)}</td>
          <td class="money-cell negative-text">${formatTagMoneyTotals(expense)}</td>
          <td class="money-cell ${moneyTotalsSignalClass(balance)}">${formatTagMoneyTotals(balance)}</td>
          <td class="money-cell neutral-text">${formatTagMoneyTotals(investment)}</td>
          </tr>
        `;
      }).join("");
      reportContent.innerHTML = `
        <div class="report-table-wrap">
          <table class="report-table tags-report-table">
            <thead>
              <tr>
                <th>Tag</th>
                <th>Receitas</th>
                <th>Despesas</th>
                <th>Saldo</th>
                <th>Investimentos</th>
              </tr>
            </thead>
            <tbody>${body}</tbody>
          </table>
        </div>
      `;
    } catch (error) {
      if (requestId !== tagsRequestId) return;
      reportContent.innerHTML = stateMarkup(`Não foi possível carregar o relatório de tags: ${error.message}`, { kind: "error" });
    } finally {
      if (requestId === tagsRequestId) {
        reportContent.setAttribute("aria-busy", "false");
        reportContent.classList.remove("is-refreshing");
      }
    }
  }

  function tagCurrencyTotals(byCurrency) {
    const totals = new Map();
    for (const [currency, amountCents] of Object.entries(byCurrency || {})) {
      addMoneyTotal(totals, currency, (amountCents || 0) / 100);
    }
    return totals;
  }

  function formatTagMoneyTotals(totals) {
    const rows = [...totals.entries()].filter(([, amount]) => Number(amount) !== 0);
    if (!rows.length) {
      return formatMoney(0, "BRL");
    }
    return rows
      .sort(([currencyA], [currencyB]) => currencyA.localeCompare(currencyB))
      .map(([currency, amount]) => formatMoney(amount, currency))
      .join(" · ");
  }

  function renderCashflowReport(items) {
    const itemsByDate = new Map();
    for (const item of items) {
      const bucket = itemsByDate.get(item.date) || [];
      bucket.push(item);
      itemsByDate.set(item.date, bucket);
    }
    const rows = monthDayRows(state.reportMonth).map((dateKey) => {
      const dayItems = itemsByDate.get(dateKey) || [];
      const income = sumReportItems(dayItems, "income");
      const expense = sumReportItems(dayItems, "expense");
      const investment = sumReportItems(dayItems, "investment");
      const result = reportResultTotals({ income, expense, investment });
      return {
        date: dateKey,
        income,
        expense,
        investment,
        result,
      };
    });
    const running = new Map();
    const body = rows.map((row) => {
      mergeMoneyTotals(running, row.result);
      return `
        <tr>
          <td>${formatDate(row.date)}</td>
          <td class="money-cell positive-text">${formatMoneyTotals(row.income)}</td>
          <td class="money-cell negative-text">${formatMoneyTotals(row.expense)}</td>
          <td class="money-cell neutral-text">${formatMoneyTotals(row.investment)}</td>
          <td class="money-cell ${moneyTotalsSignalClass(row.result)}">${formatMoneyTotals(row.result)}</td>
          <td class="money-cell">${formatMoneyTotals(running)}</td>
        </tr>
      `;
    }).join("");
    reportContent.innerHTML = `
      <div class="report-table-wrap">
        <table class="report-table">
          <thead>
            <tr>
              <th>Dia</th>
              <th>Entradas</th>
              <th>Despesas</th>
              <th>Aportes</th>
              <th>Resultado</th>
              <th>Saldo do mês</th>
            </tr>
          </thead>
          <tbody>${body}</tbody>
        </table>
      </div>
    `;
  }

  function renderAccountsReport() {
    const account = state.accounts.find((entry) => String(entry.id) === String(state.reportAccountId));
    if (!account) {
      reportContent.innerHTML = stateMarkup("Cadastre uma conta para visualizar este relatório.", { kind: "empty", compact: false });
      return;
    }
    const items = state.reportTransactions
      .filter((transaction) => transaction.date.startsWith(state.reportMonth))
      .filter((transaction) => !isCreditCardPaymentTransaction(transaction))
      .filter((transaction) => String(transaction.account_id) === String(account.id));
    const reportItems = items.map(accountTransactionReportItem).filter(Boolean);
    const totals = reportTotals(reportItems);
    const rows = groupReportItems(reportItems, "category");
    reportContent.innerHTML = `
      <div class="account-report-header">
        <div>
          <span>Conta selecionada</span>
          <strong>${escapeHtml(account.name)}</strong>
        </div>
        <div>
          <span>Receitas</span>
          <strong>${formatMoneyTotals(totals.income)}</strong>
        </div>
        <div>
          <span>Saídas</span>
          <strong>${formatMoneyTotals(combineMoneyTotals(totals.expense, totals.investment))}</strong>
        </div>
        <div>
          <span>Resultado</span>
          <strong>${formatMoneyTotals(reportResultTotals(totals))}</strong>
        </div>
      </div>
      ${reportRankedSection("Movimentação por categoria", rows, "Nenhum lançamento nesta conta no mês.")}
    `;
  }

  function reportRankedSection(title, rows, emptyText) {
    const total = rows.reduce((sum, row) => {
      mergeMoneyTotals(sum, row.totals);
      return sum;
    }, new Map());
    const content = rows.length ? rows.map((row, index) => {
      const percent = reportRowPercent(row, total);
      const barPercent = percent ?? 0;
      const evolutionButton = row.type !== "account" && row.categoryId ? `
        <button class="report-rank-evolution-btn" type="button" aria-label="Ver evolução de ${escapeHtml(row.label)}" title="Evolução temporal" data-evolution-category="${escapeHtml(row.categoryId || "")}" data-evolution-subcategory="${escapeHtml(row.subcategoryId || "")}" data-evolution-name="${escapeHtml(row.label)}" data-evolution-color="${chartColor(index)}">
          <svg viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M3 17l6-6 4 4 8-8" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </button>
      ` : "";
      return `
        <article class="report-rank-row" data-report-row>
          <div class="report-rank-main">
            <div>
              <div class="report-rank-title-line">
                <button class="report-rank-toggle" type="button" data-report-toggle aria-expanded="false">
                  <i style="background:${chartColor(index)}"></i>
                  <span>${escapeHtml(row.label)}</span>
                </button>
                ${evolutionButton}
              </div>
              <span>${row.count} lançamento(s)</span>
            </div>
            <button class="report-rank-value" type="button" data-report-toggle aria-expanded="false">
              <strong>${formatMoneyTotals(row.totals)}</strong>
              <span>${percent === null ? "Multimoeda" : formatPercent(percent)}</span>
            </button>
          </div>
          <div class="report-bar"><span style="width:${Math.max(barPercent * 100, 2)}%; background:${chartColor(index)}"></span></div>
          <div class="report-detail" data-report-detail hidden>${reportItemDetails(row.items)}</div>
        </article>
      `;
    }).join("") : stateMarkup(emptyText, { kind: "empty" });
    return `
      <section class="report-section">
        <div class="section-heading">
          <h2>${escapeHtml(title)}</h2>
          <strong>${formatMoneyTotals(total)}</strong>
        </div>
        <div class="report-rank-list" data-virtualize-report>${content}</div>
      </section>
    `;
  }

  function virtualizeReportLists() {
    reportContent.querySelectorAll("[data-virtualize-report]").forEach((list) => {
      if (list.children.length <= 200) return;
      const items = [...list.children].map((item) => item.outerHTML);
      renderVirtualList(list, items, {
        rowHeight: 106,
        renderItem: (item) => item,
      });
    });
  }

  function reportItemsForMonth(month) {
    const accountItems = state.reportTransactions
      .filter((transaction) => transaction.date.startsWith(month))
      .filter((transaction) => !isCreditCardPaymentTransaction(transaction))
      .map(accountTransactionReportItem)
      .filter(Boolean);
    const cardItems = state.reportCardTransactions
      .filter((transaction) => (transaction.invoice_month || transaction.date.slice(0, 7)) === month)
      .map(cardTransactionReportItem)
      .filter(Boolean);
    return [...accountItems, ...cardItems];
  }

  function accountTransactionReportItem(transaction) {
    if (isCreditCardPaymentTransaction(transaction)) {
      return null;
    }
    const reportType = isInvestmentTransaction(transaction)
      ? "investment"
      : transaction.type === "income" || transaction.type === "expense"
        ? transaction.type
        : "";
    if (!reportType) {
      return null;
    }
    return {
      date: transaction.date,
      reportType,
      amount: Number(transaction.amount || 0),
      currency: transaction.account_currency || "BRL",
      description: transaction.description || "",
      category: transaction.category_name || "Sem categoria",
      subcategory: String(transaction.subcategory_name || "").trim(),
      tag: "",
      tags: Array.isArray(transaction.tags) ? transaction.tags : transaction.tag_name ? [transaction.tag_name] : [],
      categoryId: transaction.category_id || "",
      subcategoryId: transaction.subcategory_id == null ? "null" : transaction.subcategory_id,
      accountId: transaction.account_id,
      accountName: transaction.account_name,
      source: "Conta",
    };
  }

  function cardTransactionReportItem(transaction) {
    if (transaction.type !== "income" && transaction.type !== "expense") {
      return null;
    }
    return {
      date: transaction.date,
      reportType: transaction.type,
      amount: Number(transaction.amount),
      currency: transaction.card_currency || "BRL",
      description: transaction.description || "",
      category: transaction.category_name || "Sem categoria",
      subcategory: String(transaction.subcategory_name || "").trim(),
      tag: "",
      tags: Array.isArray(transaction.tags) ? transaction.tags : transaction.tag_name ? [transaction.tag_name] : [],
      categoryId: transaction.category_id || "",
      subcategoryId: transaction.subcategory_id == null ? "null" : transaction.subcategory_id,
      accountId: "",
      cardId: transaction.credit_card_id || "",
      accountName: transaction.credit_card_name || "Cartão",
      source: "Cartão",
    };
  }

  function reportTotals(items) {
    return items.reduce((totals, item) => {
      addMoneyTotal(totals[item.reportType], item.currency, item.amount);
      return totals;
    }, { income: new Map(), expense: new Map(), investment: new Map() });
  }

  function groupReportItems(items, dimension) {
    const groups = new Map();
    for (const item of items) {
      let key;
      let label;
      if (dimension === "tag") {
        key = item.tag || "Sem categoria";
        label = key;
      } else if (dimension === "subcategory") {
        const subcategory = String(item.subcategory || "").trim() || "Sem subcategoria";
        key = `${item.category || "Sem categoria"} / ${subcategory}`;
        label = key;
      } else {
        key = item.category || "Sem categoria";
        label = key;
      }
      if (!groups.has(key)) {
        groups.set(key, {
          label,
          categoryId: item.categoryId || "",
          subcategoryId: dimension === "subcategory"
            ? (item.subcategoryId == null || item.subcategoryId === "" ? "null" : item.subcategoryId)
            : "",
          type: dimension,
          count: 0,
          totals: new Map(),
          items: [],
          sortTotal: 0
        });
      }
      const group = groups.get(key);
      addMoneyTotal(group.totals, item.currency, item.amount);
      group.sortTotal += item.amount;
      group.count += 1;
      group.items.push(item);
    }
    return [...groups.values()].sort((a, b) => b.sortTotal - a.sortTotal || a.label.localeCompare(b.label));
  }

  function sumReportItems(items, type) {
    return items.reduce((total, item) => {
      if (item.reportType === type) {
        addMoneyTotal(total, item.currency, item.amount);
      }
      return total;
    }, new Map());
  }

  function addMoneyTotal(totals, currency, amount) {
    const key = currency || "BRL";
    totals.set(key, (totals.get(key) || 0) + Number(amount || 0));
    return totals;
  }

  function mergeMoneyTotals(target, source, signal = 1) {
    for (const [currency, amount] of source.entries()) {
      addMoneyTotal(target, currency, Number(amount) * signal);
    }
    return target;
  }

  function combineMoneyTotals(...sources) {
    return sources.reduce((target, source) => mergeMoneyTotals(target, source), new Map());
  }

  function reportResultTotals(totals) {
    const result = new Map();
    mergeMoneyTotals(result, totals.income);
    mergeMoneyTotals(result, totals.expense, -1);
    mergeMoneyTotals(result, totals.investment, -1);
    return result;
  }

  function formatMoneyTotals(totals) {
    const rows = [...totals.entries()].filter(([, amount]) => Number(amount) !== 0);
    if (!rows.length) {
      return formatMoney(0, "BRL");
    }
    return rows
      .sort(([currencyA], [currencyB]) => currencyA.localeCompare(currencyB))
      .map(([currency, amount]) => `<span class="money-stack-line"><b>${escapeHtml(currency)}</b><em>${formatMoney(amount, currency)}</em></span>`)
      .join("");
  }

  function isCreditCardPaymentTransaction(transaction) {
    return Boolean(transaction?.is_credit_card_payment);
  }

  function moneyTotalsSignalClass(totals) {
    const values = [...totals.values()];
    if (values.some((value) => value < 0)) {
      return "negative-text";
    }
    if (values.some((value) => value > 0)) {
      return "positive-text";
    }
    return "";
  }

  function reportRowPercent(row, totals) {
    const rowEntries = [...row.totals.entries()];
    if (rowEntries.length !== 1) {
      return null;
    }
    const [currency, amount] = rowEntries[0];
    const total = totals.get(currency) || 0;
    return total > 0 ? amount / total : 0;
  }

  function reportItemDetails(items) {
    const rows = items
      .slice()
      .sort((a, b) => a.date.localeCompare(b.date) || a.description.localeCompare(b.description))
      .map((item) => `
        <tr>
          <td>${formatDate(item.date)}</td>
          <td>
            <strong>${escapeHtml(item.description || item.category)}</strong>
            <span>${escapeHtml(reportItemClassification(item))}</span>
          </td>
          <td>${escapeHtml(item.accountName || item.source)}</td>
          <td class="money-cell">${formatMoney(item.amount, item.currency)}</td>
        </tr>
      `).join("");
    return `
      <div class="report-table-wrap">
        <table class="report-table compact-report-table">
          <thead>
            <tr>
              <th>Data</th>
              <th>Lançamento</th>
              <th>Origem</th>
              <th>Valor</th>
            </tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function reportItemClassification(item) {
    return [item.category, item.subcategory].filter(Boolean).join(" / ") || "Sem categoria";
  }

  function monthDayRows(month) {
    const [year, monthNumber] = month.split("-").map(Number);
    const lastDay = new Date(year, monthNumber, 0).getDate();
    return Array.from({ length: lastDay }, (_, index) => (
      `${year}-${String(monthNumber).padStart(2, "0")}-${String(index + 1).padStart(2, "0")}`
    ));
  }

  function shiftReportMonth(delta) {
    state.reportMonth = shiftMonth(state.reportMonth, delta);
    renderReports();
  }

  function switchReportTab(tab) {
    if (!tab || tab === state.reportTab) return;
    transitionView(() => {
      state.reportTab = tab;
      renderReports();
    });
  }

  function handleReportContentClick(event) {
    const toggle = event.target.closest("[data-report-toggle]");
    if (!toggle) {
      return;
    }
    const row = toggle.closest("[data-report-row]");
    const detail = row ? row.querySelector("[data-report-detail]") : null;
    if (!detail) {
      return;
    }
    const expanded = detail.hidden;
    detail.hidden = !expanded;
    row.querySelectorAll("[data-report-toggle]").forEach((entry) => {
      entry.setAttribute("aria-expanded", String(expanded));
    });
  }

  return {
    renderReports,
  };
}
