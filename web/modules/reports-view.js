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
    reportContent,
  } = elements;

  previousReportMonthButton.addEventListener("click", () => shiftReportMonth(-1));
  nextReportMonthButton.addEventListener("click", () => shiftReportMonth(1));
  reportTabs.forEach((button) => button.addEventListener("click", () => switchReportTab(button.dataset.reportTab)));
  reportAccountSelect.addEventListener("change", () => {
    state.reportAccountId = reportAccountSelect.value;
    renderReports();
  });
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
      return `
        <article class="report-rank-row" data-report-row>
          <button class="report-rank-main" type="button" data-report-toggle aria-expanded="false">
            <div>
              <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
              <span>${row.count} lançamento(s)</span>
            </div>
            <div class="report-rank-value">
              <strong>${formatMoneyTotals(row.totals)}</strong>
              <span>${percent === null ? "Multimoeda" : formatPercent(percent)}</span>
            </div>
          </button>
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
      .map(accountTransactionReportItem)
      .filter(Boolean);
    const cardItems = state.cardTransactions
      .filter((transaction) => (transaction.invoice_month || transaction.date.slice(0, 7)) === month)
      .map(cardTransactionReportItem)
      .filter(Boolean);
    return [...accountItems, ...cardItems];
  }

  function accountTransactionReportItem(transaction) {
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
      accountId: "",
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

  function groupReportItems(items, key) {
    const grouped = new Map();
    for (const item of items) {
      const label = reportGroupLabel(item, key);
      if (!label) {
        continue;
      }
      const current = grouped.get(label) || { label, totals: new Map(), sortTotal: 0, count: 0, items: [] };
      addMoneyTotal(current.totals, item.currency, item.amount);
      current.sortTotal += item.amount;
      current.count += 1;
      current.items.push(item);
      grouped.set(label, current);
    }
    return [...grouped.values()].sort((a, b) => b.sortTotal - a.sortTotal || a.label.localeCompare(b.label));
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
    toggle.setAttribute("aria-expanded", String(expanded));
  }

  return {
    renderReports,
  };
}
