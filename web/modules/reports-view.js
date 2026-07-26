import { api } from "./api.js";

export function registerReportsView({
  state,
  elements,
  shiftMonth,
  formatDate,
  formatMonthLabel,
  formatMoney,
  formatPercent,
  escapeHtml,
  isInvestmentTransaction,
  chartColor,
}) {
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
    statementScopeSelect,
    printStatementButton,
    reportContent,
  } = elements;

  previousReportMonthButton.addEventListener("click", () => shiftReportMonth(-1));
  nextReportMonthButton.addEventListener("click", () => shiftReportMonth(1));
  reportTabs.forEach((button) => button.addEventListener("click", () => switchReportTab(button.dataset.reportTab)));
  reportAccountSelect.addEventListener("change", () => {
    state.reportAccountId = reportAccountSelect.value;
    renderReports();
  });
  statementScopeSelect.addEventListener("change", () => {
    state.statementScope = statementScopeSelect.value;
    renderReports();
  });
  printStatementButton.addEventListener("click", () => window.print());
  reportContent.addEventListener("click", handleReportContentClick);

  function renderReports() {
    reportMonthLabel.textContent = formatMonthLabel(state.reportMonth);
    reportTabs.forEach((button) => button.classList.toggle("active", button.dataset.reportTab === state.reportTab));
    renderReportAccountOptions();
    const items = reportItemsForMonth(state.reportMonth);
    const totals = reportTotals(items);
    const resultTotals = reportResultTotals(totals);
    reportIncomeSummary.innerHTML = formatMoneyTotals(totals.income);
    reportExpenseSummary.innerHTML = formatMoneyTotals(totals.expense);
    reportInvestmentSummary.innerHTML = formatMoneyTotals(totals.investment);
    reportResultSummary.innerHTML = formatMoneyTotals(resultTotals);
    reportResultSummary.classList.toggle("danger-text", [...resultTotals.values()].some((total) => total < 0));
    reportResultSummary.classList.toggle("positive-text", [...resultTotals.values()].some((total) => total > 0) && ![...resultTotals.values()].some((total) => total < 0));
    reportAccountFilter.hidden = state.reportTab !== "accounts";
    statementControls.hidden = state.reportTab !== "statement";
    renderStatementScopeOptions();
    printStatementButton.hidden = state.reportTab !== "statement";
    printStatementButton.disabled = state.reportTab === "statement" && !statementExpenseItems().length;
    reportContent.classList.toggle("statement-print-area", state.reportTab === "statement");
    if (state.reportTab === "cashflow") {
      renderCashflowReport(items);
      return;
    }
    if (state.reportTab === "accounts") {
      renderAccountsReport();
      return;
    }
    if (state.reportTab === "tags") {
      renderTagsReport(items);
      return;
    }
    if (state.reportTab === "subcategories") {
      renderSubcategoriesReport(items);
      return;
    }
    if (state.reportTab === "statement") {
      renderStatementReport();
      return;
    }
    renderCategoriesReport(items);
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

  function renderStatementScopeOptions() {
    if (state.reportTab !== "statement") {
      return;
    }
    const options = [
      '<option value="consolidated">Visão Consolidada</option>',
      ...state.accounts.map((account) => (
        `<option value="account:${account.id}">Conta · ${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
      )),
      ...state.creditCards.map((card) => (
        `<option value="card:${card.id}">Cartão · ${escapeHtml(card.name)} (${escapeHtml(card.currency)})</option>`
      )),
    ];
    statementScopeSelect.innerHTML = options.join("");
    if (![...statementScopeSelect.options].some((option) => option.value === state.statementScope)) {
      state.statementScope = "consolidated";
    }
    statementScopeSelect.value = state.statementScope;
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
  }

  function renderTagsReport(items) {
    const taggedItems = [];
    for (const item of items) {
      for (const tag of item.tags) {
        taggedItems.push({ ...item, tag });
      }
    }
    const sections = [
      ["Despesas", "expense"],
      ["Receitas", "income"],
      ["Investimentos", "investment"],
    ];
    reportContent.innerHTML = sections.map(([title, type]) => (
      reportRankedSection(title, groupReportItems(taggedItems.filter((item) => item.reportType === type), "tag"), `Nenhuma tag em ${title.toLowerCase()} neste mês.`)
    )).join("");
  }

  function renderCashflowReport(items) {
    const rows = monthDayRows(state.reportMonth).map((dateKey) => {
      const dayItems = items.filter((item) => item.date === dateKey);
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
      reportContent.innerHTML = '<div class="empty-state">Cadastre uma conta para visualizar este relatório.</div>';
      return;
    }
    const items = state.transactions
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
    }).join("") : `<div class="empty-state compact">${emptyText}</div>`;
    return `
      <section class="report-section">
        <div class="section-heading">
          <h2>${escapeHtml(title)}</h2>
          <strong>${formatMoneyTotals(total)}</strong>
        </div>
        <div class="report-rank-list">${content}</div>
      </section>
    `;
  }

  function reportItemsForMonth(month) {
    const accountItems = state.transactions
      .filter((transaction) => transaction.date.startsWith(month))
      .filter((transaction) => !isCreditCardPaymentTransaction(transaction))
      .map(accountTransactionReportItem)
      .filter(Boolean);
    const cardItems = state.cardTransactions
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
      subcategory: transaction.subcategory_name || "",
      tag: "",
      tags: Array.isArray(transaction.tags) ? transaction.tags : transaction.tag_name ? [transaction.tag_name] : [],
      categoryId: transaction.category_id || "",
      subcategoryId: transaction.subcategory_id || "",
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
      subcategory: transaction.subcategory_name || "",
      tag: "",
      tags: Array.isArray(transaction.tags) ? transaction.tags : transaction.tag_name ? [transaction.tag_name] : [],
      categoryId: transaction.category_id || "",
      subcategoryId: transaction.subcategory_id || "",
      accountId: "",
      cardId: transaction.credit_card_id || "",
      accountName: transaction.credit_card_name || "Cartão",
      source: "Cartão",
    };
  }

  function renderStatementReport() {
    const items = statementExpenseItems();
    const totalMap = sumStatementMoney(items);
    const total = items.reduce((sum, item) => sum + item.amount, 0);
    const monthDaysElapsed = statementElapsedDays(state.reportMonth);
    const averageMap = divideMoneyTotals(totalMap, Math.max(monthDaysElapsed, 1));
    const categoryRows = groupReportItems(items, "category").slice(0, 5);
    const compositionRows = groupReportItems(items, "subcategory");
    const topCategory = categoryRows[0] || null;
    const topTransaction = items.slice().sort((a, b) => b.amount - a.amount)[0] || null;
    const scope = statementScopeInfo();
    const currencyInfo = statementBaseCurrencyInfo(items, scope);
    const issuedAt = new Date();
    reportContent.innerHTML = `
      <article class="monthly-statement">
        <header class="statement-header">
          <img src="assets/app-icon.png" alt="Sistema Financeiro">
          <div>
            <h2>Relatório de Despesas Mensal (${escapeHtml(formatMonthLabel(state.reportMonth))})</h2>
            <p>Conta(s): ${escapeHtml(scope.label)}</p>
            <p>Moeda Base: ${escapeHtml(currencyInfo.label)}</p>
            <p>Data de Emissão: ${escapeHtml(formatStatementDateTime(issuedAt))}</p>
          </div>
        </header>
        <section class="statement-kpis" aria-label="Resumo executivo">
          ${statementKpi("Total de Saídas", formatMoneyTotals(totalMap))}
          ${statementKpi("Média Diária", formatMoneyTotals(averageMap))}
          ${statementKpi("Maior Despesa", topCategory ? `${escapeHtml(topCategory.label)} · ${formatMoneyTotals(topCategory.totals)}` : "Sem despesas")}
          ${statementKpi("Transação de Maior Impacto", topTransaction ? `${escapeHtml(topTransaction.description || topTransaction.category)} · ${formatMoney(topTransaction.amount, topTransaction.currency)}` : "Sem despesas")}
        </section>
        <section class="statement-visuals">
          <div class="statement-chart-card statement-donut-card">
            <h3>Distribuição por categoria</h3>
            ${statementDonutChart(categoryRows, total, currencyInfo)}
          </div>
          <div class="statement-chart-card">
            <h3>Gastos por dia do mês</h3>
            ${statementDailyBars(items, currencyInfo)}
          </div>
        </section>
        <section class="statement-section">
          <h3>Composição de Despesas</h3>
          ${statementCompositionTable(compositionRows, totalMap)}
        </section>
        <section class="statement-section">
          <h3>Detalhamento de Lançamentos</h3>
          ${statementDetailTable(items)}
        </section>
        <footer class="statement-footer">
          <span>Sistema Financeiro</span>
          <span>Página <span class="statement-page-number"></span> de <span class="statement-page-total"></span></span>
        </footer>
      </article>
    `;
  }

  function statementKpi(label, value) {
    return `
      <div>
        <span>${escapeHtml(label)}</span>
        <strong>${value}</strong>
      </div>
    `;
  }

  function statementExpenseItems() {
    return reportItemsForMonth(state.reportMonth)
      .filter((item) => item.reportType === "expense")
      .filter((item) => statementItemMatchesScope(item));
  }

  function statementItemMatchesScope(item) {
    const [kind, id] = String(state.statementScope || "consolidated").split(":");
    if (kind === "account") {
      return item.source === "Conta" && String(item.accountId) === String(id);
    }
    if (kind === "card") {
      return item.source === "Cartão" && String(item.cardId) === String(id);
    }
    return true;
  }

  function statementScopeInfo() {
    const [kind, id] = String(state.statementScope || "consolidated").split(":");
    if (kind === "account") {
      const account = state.accounts.find((entry) => String(entry.id) === String(id));
      return account ? { label: account.name, currency: account.currency || "BRL" } : { label: "Conta", currency: "BRL" };
    }
    if (kind === "card") {
      const card = state.creditCards.find((entry) => String(entry.id) === String(id));
      return card ? { label: card.name, currency: card.currency || "BRL" } : { label: "Cartão", currency: "BRL" };
    }
    return { label: "Visão Consolidada", currency: "" };
  }

  function statementBaseCurrencyInfo(items, scope) {
    if (scope.currency) {
      return { label: scope.currency, currency: scope.currency, single: true };
    }
    const currencies = [...new Set(items.map((item) => item.currency || "BRL"))].sort();
    if (currencies.length <= 1) {
      const currency = currencies[0] || "BRL";
      return { label: currency, currency, single: true };
    }
    return { label: currencies.join(" / "), currency: "", single: false };
  }

  function statementElapsedDays(month) {
    const [year, monthNumber] = month.split("-").map(Number);
    const lastDay = new Date(year, monthNumber, 0).getDate();
    const today = new Date();
    const currentMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
    if (month === currentMonth) {
      return Math.min(today.getDate(), lastDay);
    }
    return month < currentMonth ? lastDay : 0;
  }

  function singleCurrencyTotal(totals) {
    return [...totals.values()].reduce((sum, amount) => sum + amount, 0);
  }

  function sumStatementMoney(items) {
    return items.reduce((totals, item) => addMoneyTotal(totals, item.currency, item.amount), new Map());
  }

  function divideMoneyTotals(totals, divisor) {
    const result = new Map();
    for (const [currency, amount] of totals.entries()) {
      result.set(currency, amount / divisor);
    }
    return result;
  }

  function statementDonutChart(rows, total, currencyInfo) {
    if (!rows.length || total <= 0) {
      return '<div class="empty-state compact">Sem despesas no período.</div>';
    }
    if (!currencyInfo.single) {
      return '<div class="empty-state compact">Gráfico disponível quando o escopo usa uma única moeda.</div>';
    }
    const topRows = rows.slice(0, 5);
    const topTotal = topRows.reduce((sum, row) => sum + singleCurrencyTotal(row.totals), 0);
    const donutRows = topTotal < total
      ? [...topRows, { label: "Outros", totals: new Map([[currencyInfo.currency, total - topTotal]]), sortTotal: total - topTotal }]
      : topRows;
    let offset = 25;
    const segments = donutRows.map((row, index) => {
      const amount = singleCurrencyTotal(row.totals);
      const dash = Math.max((amount / total) * 100, 0);
      const segment = `<circle r="15.9155" cx="18" cy="18" style="stroke:${chartColor(index)}; stroke-dasharray:${dash.toFixed(2)} ${Math.max(100 - dash, 0).toFixed(2)}; stroke-dashoffset:${offset.toFixed(2)}"></circle>`;
      offset -= dash;
      return segment;
    }).join("");
    const legend = donutRows.map((row, index) => {
      const amount = singleCurrencyTotal(row.totals);
      return `
        <li><i style="background:${chartColor(index)}"></i><span>${escapeHtml(row.label)}</span><strong>${formatPercent(total > 0 ? amount / total : 0)}</strong></li>
      `;
    }).join("");
    return `
      <div class="statement-donut">
        <svg viewBox="0 0 36 36" aria-hidden="true">
          <circle r="15.9155" cx="18" cy="18" class="statement-donut-track"></circle>
          ${segments}
        </svg>
        <div class="statement-donut-center">
          <span>Total Gasto</span>
          <strong>${formatMoney(total, currencyInfo.currency)}</strong>
        </div>
      </div>
      <ul class="statement-chart-legend">${legend}</ul>
    `;
  }

  function statementDailyBars(items, currencyInfo) {
    if (!currencyInfo.single) {
      return '<div class="empty-state compact">Histograma disponível quando o escopo usa uma única moeda.</div>';
    }
    const days = monthDayRows(state.reportMonth);
    const totals = new Map(days.map((day) => [day, 0]));
    for (const item of items) {
      totals.set(item.date, (totals.get(item.date) || 0) + item.amount);
    }
    const max = Math.max(...totals.values(), 1);
    return `
      <div class="statement-daily-bars">
        ${days.map((day) => {
          const amount = totals.get(day) || 0;
          return `
            <div>
              <span style="height:${Math.max((amount / max) * 100, amount > 0 ? 4 : 0).toFixed(2)}%" title="${escapeHtml(formatDate(day))}: ${formatMoney(amount, currencyInfo.currency)}"></span>
              <small>${Number(day.slice(-2))}</small>
            </div>
          `;
        }).join("")}
      </div>
    `;
  }

  function statementCompositionTable(rows, totalMap) {
    if (!rows.length) {
      return '<div class="empty-state compact">Sem composição para o período.</div>';
    }
    return `
      <div class="report-table-wrap">
        <table class="report-table statement-table">
          <thead><tr><th>Categoria / Subcategoria</th><th>Total Gasto</th><th>% do Mês</th></tr></thead>
          <tbody>
            ${rows.map((row) => {
              const percent = reportRowPercent(row, totalMap);
              return `<tr><td>${escapeHtml(row.label.replace(" / ", " › "))}</td><td class="money-cell">${formatMoneyTotals(row.totals)}</td><td class="money-cell">${percent === null ? "Multimoeda" : formatPercent(percent)}</td></tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function statementDetailTable(items) {
    if (!items.length) {
      return '<div class="empty-state compact">Sem lançamentos no período.</div>';
    }
    const rows = items.slice().sort((a, b) => a.date.localeCompare(b.date) || b.amount - a.amount).map((item) => `
      <tr>
        <td>${formatDate(item.date)}</td>
        <td>${escapeHtml(item.description || item.category)}</td>
        <td>${escapeHtml(reportItemClassification(item).replace(" / ", " › "))}</td>
        <td><span class="statement-tags">${escapeHtml(item.tags.map((tag) => `#${tag}`).join(" "))}</span></td>
        <td class="money-cell">${formatMoney(item.amount, item.currency)}</td>
      </tr>
    `).join("");
    return `
      <div class="report-table-wrap">
        <table class="report-table statement-table">
          <thead><tr><th>Data</th><th>Descrição</th><th>Categoria / Subcategoria</th><th>Tags</th><th>Valor</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function formatStatementDateTime(date) {
    return date.toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
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
      const key = dimension === "tag" ? item.tag : (dimension === "subcategory" ? item.subcategory : item.category) || "Sem categoria";
      if (!groups.has(key)) {
        groups.set(key, {
          label: dimension === "subcategory" ? `${item.category || "Sem categoria"} / ${item.subcategory || "Sem subcategoria"}` : key,
          categoryId: item.categoryId || "",
          subcategoryId: dimension === "subcategory" ? item.subcategoryId || "" : "",
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

  function reportGroupLabel(item, key) {
    if (key === "tag") {
      return item.tag;
    }
    if (key === "subcategory") {
      return `${item.category || "Sem categoria"} / ${item.subcategory || "Sem subcategoria"}`;
    }
    return item.category || "Sem categoria";
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

  // --- Evolution Drawer Logic ---
  
  const drawer = document.getElementById("evolutionDrawer");
  const drawerOverlay = document.getElementById("evolutionDrawerCloseOverlay");
  const drawerCloseBtn = document.getElementById("evolutionDrawerCloseBtn");
  const drawerTitle = document.getElementById("evolutionDrawerTitle");
  const chartTrend = document.getElementById("evolutionChartTrend");
  const chartTotal = document.getElementById("evolutionChartTotal");
  const svgEl = document.getElementById("evolutionSvg");
  const xLabelsEl = document.getElementById("evolutionXLabels");
  const filterBtns = document.querySelectorAll(".evolution-filter-btn");
  const smaToggle = document.getElementById("evolutionSmaToggle");
  const forecastMonthsSelect = document.getElementById("evolutionForecastMonths");
  
  let currentEvolutionContext = null;
  let currentEvolutionData = [];
  let currentEvolutionColor = "";

  if (drawerOverlay && drawerCloseBtn) {
    drawerOverlay.addEventListener("click", closeEvolutionDrawer);
    drawerCloseBtn.addEventListener("click", closeEvolutionDrawer);
  }

  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      if (currentEvolutionContext) {
        loadEvolutionChart(currentEvolutionContext, btn.dataset.period);
      }
    });
  });

  if (smaToggle) {
    smaToggle.addEventListener("change", redrawCurrentEvolutionChart);
  }

  if (forecastMonthsSelect) {
    forecastMonthsSelect.addEventListener("change", redrawCurrentEvolutionChart);
  }

  reportContent.addEventListener("click", (e) => {
    const btn = e.target.closest(".report-rank-evolution-btn");
    if (btn) {
      e.preventDefault();
      e.stopPropagation();
      openEvolutionDrawer({
        categoryId: btn.dataset.evolutionCategory,
        subcategoryId: btn.dataset.evolutionSubcategory,
        name: btn.dataset.evolutionName,
        color: btn.dataset.evolutionColor
      });
    }
  });

  function openEvolutionDrawer(context) {
    if (!drawer || !drawerTitle) {
      return;
    }
    currentEvolutionContext = context;
    drawerTitle.textContent = context.name;
    drawer.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
    
    const activeBtn = document.querySelector(".evolution-filter-btn.active");
    loadEvolutionChart(context, activeBtn ? activeBtn.dataset.period : "12m");
  }

  function closeEvolutionDrawer() {
    if (!drawer) {
      return;
    }
    drawer.hidden = true;
    drawer.setAttribute("aria-hidden", "true");
  }

  async function loadEvolutionChart(context, period) {
    if (!svgEl || !xLabelsEl || !chartTotal || !chartTrend) {
      return;
    }
    svgEl.innerHTML = "";
    xLabelsEl.innerHTML = "";
    chartTotal.textContent = "Carregando...";
    chartTrend.textContent = "";

    try {
      const url = new URL("/api/reports/category-evolution", window.location.origin);
      if (context.categoryId) url.searchParams.set("category_id", context.categoryId);
      if (context.subcategoryId) url.searchParams.set("subcategory_id", context.subcategoryId);
      url.searchParams.set("period", period);
      
      const res = await api(url.pathname + url.search);
      drawEvolutionChart(res.evolution || [], context.color);
    } catch (err) {
      const fallback = localCategoryEvolution(context, period);
      if (fallback.length) {
        drawEvolutionChart(fallback, context.color);
        chartTrend.textContent = [chartTrend.textContent, "Dados locais"].filter(Boolean).join(" · ");
        return;
      }
      chartTotal.textContent = "Erro ao carregar";
      chartTrend.textContent = err.message || "Nao foi possivel carregar a evolucao.";
    }
  }

  function localCategoryEvolution(context, period) {
    if (!context.categoryId) {
      return [];
    }
    const months = evolutionMonths(period);
    const allowedMonths = new Set(months);
    const totals = new Map(months.map((month) => [month, 0]));
    for (const transaction of state.transactions) {
      if (isCreditCardPaymentTransaction(transaction)) {
        continue;
      }
      addLocalEvolutionTransaction(totals, allowedMonths, context, transaction, transaction.date?.slice(0, 7));
    }
    for (const transaction of state.cardTransactions) {
      addLocalEvolutionTransaction(totals, allowedMonths, context, transaction, transaction.invoice_month || transaction.date?.slice(0, 7));
    }
    if (period === "all") {
      return [...totals.entries()]
        .filter(([, total]) => total !== 0)
        .sort(([monthA], [monthB]) => monthA.localeCompare(monthB))
        .map(([month, total_cents]) => ({ month, total_cents }));
    }
    return months.map((month) => ({ month, total_cents: totals.get(month) || 0 }));
  }

  function addLocalEvolutionTransaction(totals, allowedMonths, context, transaction, month) {
    if (!month || String(transaction.category_id || "") !== String(context.categoryId || "")) {
      return;
    }
    if (context.subcategoryId && String(transaction.subcategory_id || "") !== String(context.subcategoryId)) {
      return;
    }
    if (!totals.has(month)) {
      if (!allowedMonths.size) {
        totals.set(month, 0);
      } else {
        return;
      }
    }
    totals.set(month, (totals.get(month) || 0) + moneyToCents(transaction.amount));
  }

  function isCreditCardPaymentTransaction(transaction) {
    return Boolean(transaction?.is_credit_card_payment);
  }

  function evolutionMonths(period) {
    if (period === "all") {
      return [];
    }
    const now = new Date();
    const currentMonth = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
    if (period === "ytd") {
      const months = [];
      for (let index = 1; index <= now.getMonth() + 1; index += 1) {
        months.push(`${now.getFullYear()}-${String(index).padStart(2, "0")}`);
      }
      return months;
    }
    const count = period === "3m" ? 3 : period === "6m" ? 6 : 12;
    return Array.from({ length: count }, (_, index) => shiftMonth(currentMonth, index - count + 1));
  }

  function moneyToCents(value) {
    return Math.round(Number(value || 0) * 100);
  }

  function drawEvolutionChart(data, color) {
    currentEvolutionData = data;
    currentEvolutionColor = color;
    chartTrend.textContent = "";
    if (data.length === 0) {
      chartTotal.textContent = "Sem dados";
      return;
    }

    const totalAmount = data.reduce((acc, pt) => acc + pt.total_cents, 0);
    chartTotal.textContent = formatMoney(totalAmount / 100, "BRL");
    
    if (data.length > 1) {
      const first = data[0].total_cents;
      const last = data[data.length - 1].total_cents;
      if (first !== 0) {
        const diff = ((last - first) / Math.abs(first)) * 100;
        chartTrend.textContent = `${diff > 0 ? '+' : ''}${diff.toFixed(1)}% em relação ao início`;
      }
    }

    const forecastMonths = Number(forecastMonthsSelect?.value || 3);
    const forecast = smaToggle?.checked ? smaForecast(data, forecastMonths) : [];
    if (forecast.length) {
      chartTrend.textContent = [chartTrend.textContent, `SMA projetando ${forecastMonths} meses`].filter(Boolean).join(" · ");
    }
    const allValues = [...data, ...forecast].map((entry) => Number(entry.total_cents || 0));
    const w = 100;
    const h = 50;
    const maxVal = Math.max(...allValues, 1);
    const minVal = Math.min(0, ...allValues);
    const range = Math.max(maxVal - minVal, 1);
    const denominator = Math.max(data.length + forecast.length - 1, 1);

    const points = data.map((d, i) => pointForEvolutionValue(d.total_cents, i, denominator, minVal, range, w, h));
    const forecastPoints = forecast.map((d, i) => pointForEvolutionValue(d.total_cents, data.length + i, denominator, minVal, range, w, h));

    const pathD = points.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ");
    const areaD = `${pathD} L ${w},${h} L 0,${h} Z`;
    const gradientId = "grad" + Math.random().toString(36).substring(2);
    const forecastPath = forecastPoints.length && points.length
      ? [points[points.length - 1], ...forecastPoints].map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(" ")
      : "";
    
    svgEl.innerHTML = `
      <defs>
        <linearGradient id="${gradientId}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="${color}" stop-opacity="0.3" />
          <stop offset="100%" stop-color="${color}" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      <path d="${areaD}" fill="url(#${gradientId})" />
      <path d="${pathD}" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
      ${forecastPath ? `<path d="${forecastPath}" class="evolution-sma-line" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />` : ""}
    `;
    
    points.forEach((p) => {
      svgEl.innerHTML += `<circle cx="${p.x.toFixed(2)}" cy="${p.y.toFixed(2)}" r="1.5" fill="${color}" />`;
    });
    forecastPoints.forEach((p) => {
      svgEl.innerHTML += `<circle cx="${p.x.toFixed(2)}" cy="${p.y.toFixed(2)}" r="1.2" fill="var(--panel)" stroke="${color}" stroke-width="0.8" />`;
    });

    if (data.length > 0) {
      const formatMonth = (m) => {
        const [yy, mm] = m.split("-");
        const date = new Date(parseInt(yy), parseInt(mm) - 1, 1);
        return date.toLocaleString('pt-BR', { month: 'short', year: '2-digit' }).replace('.', '');
      };
      
      const labels = [];
      labels.push(`<span>${formatMonth(data[0].month)}</span>`);
      if (data.length > 2) {
        const mid = Math.floor(data.length / 2);
        labels.push(`<span>${formatMonth(data[mid].month)}</span>`);
      }
      if (data.length > 1) {
        labels.push(`<span>${formatMonth(data[data.length - 1].month)}</span>`);
      }
      if (forecast.length > 0) {
        labels.push(`<span>${formatMonth(forecast[forecast.length - 1].month)}</span>`);
      }
      xLabelsEl.innerHTML = labels.join("");
    }
  }

  function redrawCurrentEvolutionChart() {
    if (!currentEvolutionData.length || !currentEvolutionColor) {
      return;
    }
    drawEvolutionChart(currentEvolutionData, currentEvolutionColor);
  }

  function pointForEvolutionValue(value, index, denominator, minVal, range, width, height) {
    const x = (index / denominator) * width;
    const y = height - ((Number(value || 0) - minVal) / range) * (height * 0.9);
    return { x, y };
  }

  function smaForecast(data, months) {
    const values = data.map((entry) => Number(entry.total_cents || 0));
    if (!values.length || months <= 0) {
      return [];
    }
    const windowSize = Math.min(3, values.length);
    const projected = [];
    for (let index = 0; index < months; index += 1) {
      const base = [...values, ...projected.map((entry) => entry.total_cents)];
      const averageSource = base.slice(-windowSize);
      const total = Math.round(averageSource.reduce((sum, value) => sum + value, 0) / averageSource.length);
      projected.push({
        month: shiftMonth(data[data.length - 1].month, index + 1),
        total_cents: total,
      });
    }
    return projected;
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
    state.reportTab = tab;
    renderReports();
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
