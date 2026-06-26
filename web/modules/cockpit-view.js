export function registerCockpitView({
  state,
  elements,
  currentMonthValue,
  formatMoney,
  formatPercent,
  emptyState,
  escapeHtml,
  formatCategoryPath,
  isInstallmentTransaction,
  isInvestmentTransaction,
  chartColor,
  getCurrencyTotals,
  renderLimitAlerts,
  loadPortfolio,
  portfolioTotalsByCurrency,
}) {
  const {
    monthIncome,
    monthExpense,
    monthInvestment,
    savingsRate,
    currencyList,
    monthlyPlanningList,
    installmentDebtList,
    topExpensesChart,
    cashDistributionChart,
    cockpitPortfolioByType,
  } = elements;

  function renderCockpit() {
    const totals = getCurrencyTotals();
    const monthTotals = state.cockpit?.month_totals || getCurrentMonthTotals();
    monthIncome.textContent = formatMoney(monthTotals.income, "BRL");
    monthExpense.textContent = formatMoney(monthTotals.expense, "BRL");
    monthInvestment.textContent = formatMoney(monthTotals.investment, "BRL");
    savingsRate.textContent = formatPercent(monthTotals.savings_rate ?? monthTotals.savingsRate);
    renderCurrencyTotals(totals);
    renderCockpitPortfolioByType();
    renderMonthlyPlanning();
    renderInstallmentDebts();
    renderLimitAlerts();
    renderTopExpensesChart();
    renderTopIncomeChart();
  }

  function getCurrentMonthTotals() {
    const prefix = currentMonthValue();
    return state.transactions.reduce((totals, transaction) => {
      if (!transaction.date.startsWith(prefix)) {
        return totals;
      }
      const amountBrl = Number(transaction.amount_brl || transaction.amount);
      if (transaction.type === "income") {
        totals.income += amountBrl;
      }
      if (transaction.type === "expense") {
        totals.expense += amountBrl;
      }
      if (isInvestmentTransaction(transaction)) {
        totals.investment += amountBrl;
      }
      return totals;
    }, { income: 0, expense: 0, investment: 0, get savingsRate() {
      return this.income > 0 ? this.investment / this.income : 0;
    } });
  }

  function renderCurrencyTotals(totals) {
    currencyList.innerHTML = "";
    if (totals.size === 0) {
      currencyList.append(emptyState("Nenhuma moeda cadastrada ainda.", true));
      return;
    }
    for (const [currency, amounts] of totals.entries()) {
      const section = document.createElement("section");
      section.className = "currency-section";
      const accountRows = amounts.accounts.map((account) => currencyTableRow(
        account.name,
        account.type,
        account.amount,
        account.reconciled,
        currency,
        "account",
      )).join("");
      const cardRows = amounts.cards.map((card) => currencyTableRow(
        card.name,
        card.issuer || "Cartão",
        card.amount,
        card.reconciled,
        currency,
        "card",
      )).join("");
      section.innerHTML = `
        <div class="currency-section-header">
          <div>
            <span>${escapeHtml(currency)}</span>
            <em>Previsto</em>
          </div>
          <strong>${formatMoney(amounts.current, currency)}</strong>
        </div>
        <div class="currency-table" role="table" aria-label="Saldos em ${escapeHtml(currency)}">
          <div class="currency-table-head" role="row">
            <span>Conta</span>
            <span>Tipo</span>
            <span>Saldo</span>
            <span>Conciliado</span>
          </div>
          ${accountRows || '<div class="currency-empty-row">Nenhuma conta ativa nesta moeda.</div>'}
          ${cardRows ? `<div class="currency-subgroup">Cartões de crédito</div>${cardRows}` : ""}
        </div>
      `;
      currencyList.append(section);
    }
  }

  function currencyTableRow(name, detail, amount, reconciled, currency, kind = "account") {
    const amountClass = amount < 0 ? "danger-text" : amount > 0 ? "positive-text" : "";
    const reconciledClass = reconciled < 0 ? "danger-text" : reconciled > 0 ? "positive-text" : "";
    return `
      <div class="currency-table-row ${kind}" role="row">
        <span><b>${escapeHtml(name)}</b></span>
        <span>${escapeHtml(detail)}</span>
        <strong class="${amountClass}">${formatMoney(amount, currency)}</strong>
        <strong class="${reconciledClass}">${formatMoney(reconciled || 0, currency)}</strong>
      </div>
    `;
  }

  function renderMonthlyPlanning() {
    if (state.cockpit?.planning) {
      monthlyPlanningList.innerHTML = "";
      monthlyPlanningList.append(
        planningSectionFromRows("Receitas recorrentes", state.cockpit.planning.income || [], "income"),
        planningSectionFromRows("Investimentos planejados", state.cockpit.planning.investment || [], "investment"),
        planningSectionFromRows("Despesas recorrentes", state.cockpit.planning.expense || [], "expense"),
      );
      return;
    }
    const prefix = currentMonthValue();
    const sections = [
      ["Receitas recorrentes", "income", (transaction) => transaction.type === "income" && transaction.series_kind === "recurring"],
      ["Investimentos planejados", "investment", (transaction) => isInvestmentTransaction(transaction) && transaction.series_kind !== "single"],
      ["Despesas recorrentes", "expense", (transaction) => transaction.type === "expense" && transaction.series_kind === "recurring"],
    ];
    monthlyPlanningList.innerHTML = "";
    for (const [title, kind, predicate] of sections) {
      monthlyPlanningList.append(planningSection(title, state.transactions.filter((transaction) => (
        transaction.date.startsWith(prefix) && predicate(transaction)
      )), kind));
    }
  }

  function planningSectionFromRows(title, rows, kind = "neutral") {
    const section = document.createElement("section");
    section.className = `planning-section planning-section-${kind}`;
    const total = rows.reduce((sum, item) => sum + Number(item.total || 0), 0);
    const content = rows.length
      ? rows.map((item) => `
        <div class="planning-row">
          <span>${escapeHtml(item.label)}</span>
          <strong>${formatMoney(item.total, "BRL")}</strong>
        </div>
      `).join("")
      : '<div class="empty-state compact">Nada previsto neste mês.</div>';
    section.innerHTML = `
      <div class="planning-section-header">
        <h3>${title}</h3>
        <strong>${formatMoney(total, "BRL")}</strong>
      </div>
      ${content}
    `;
    return section;
  }

  function planningSection(title, transactions, kind = "neutral") {
    const section = document.createElement("section");
    section.className = `planning-section planning-section-${kind}`;
    const grouped = groupTransactionsByCategory(transactions);
    const total = grouped.reduce((sum, item) => sum + item.total, 0);
    const rows = grouped.length
      ? grouped.map((item) => `
        <div class="planning-row">
          <span>${escapeHtml(item.label)}</span>
          <strong>${formatMoney(item.total, "BRL")}</strong>
        </div>
      `).join("")
      : '<div class="empty-state compact">Nada previsto neste mês.</div>';
    section.innerHTML = `
      <div class="planning-section-header">
        <h3>${title}</h3>
        <strong>${formatMoney(total, "BRL")}</strong>
      </div>
      ${rows}
    `;
    return section;
  }

  function renderInstallmentDebts() {
    if (!installmentDebtList) {
      return;
    }
    const currentMonth = currentMonthValue();
    const rows = new Map();
    for (const transaction of state.transactions) {
      const transactionMonth = transaction.date.slice(0, 7);
      if (!isOpenInstallmentDebt(transaction, transactionMonth, currentMonth)) {
        continue;
      }
      const key = `account:${transaction.account_id}`;
      const row = rows.get(key) || { label: transaction.account_name || "Conta", detail: "Conta", currency: transaction.account_currency || "BRL", total: 0, debts: new Map() };
      addInstallmentDebt(row, transaction, "account");
      rows.set(key, row);
    }
    for (const transaction of state.cardTransactions) {
      if (!isOpenInstallmentDebt(transaction, transaction.invoice_month, currentMonth)) {
        continue;
      }
      const key = `card:${transaction.credit_card_id}`;
      const row = rows.get(key) || { label: transaction.credit_card_name || "Cartão", detail: "Cartão", currency: transaction.card_currency || "BRL", total: 0, debts: new Map() };
      addInstallmentDebt(row, transaction, "card");
      rows.set(key, row);
    }
    const debts = [...rows.values()].sort((a, b) => b.total - a.total);
    if (debts.length === 0) {
      installmentDebtList.innerHTML = `
        <section class="planning-section">
          <div class="planning-section-header">
            <h3>Total em aberto</h3>
            <strong class="danger-text">${formatMoney(0, "BRL")}</strong>
          </div>
          <div class="empty-state compact">Nenhuma compra parcelada em aberto.</div>
        </section>
      `;
      return;
    }
    const debtTotals = summarizeDebtTotals(debts);
    installmentDebtList.innerHTML = `
      <section class="planning-section">
        <div class="planning-section-header">
          <h3>Total em aberto</h3>
          <strong class="danger-text">${formatDebtTotals(debtTotals)}</strong>
        </div>
        ${debts.map((row) => `
          <div class="debt-group">
            <div class="debt-group-header">
              <span>${escapeHtml(row.label)}</span>
              <strong>${formatMoney(row.total, row.currency)}</strong>
            </div>
            <div class="debt-items">
              ${[...row.debts.values()].sort((a, b) => b.total - a.total).map((debt) => `
                <div class="debt-item">
                  <span>${escapeHtml(debt.description)} - ${installmentDebtCountLabel(debt.count)}</span>
                  <strong>${formatMoney(debt.total, row.currency)}</strong>
                </div>
              `).join("")}
            </div>
          </div>
        `).join("")}
      </section>
    `;
  }

  function summarizeDebtTotals(debts) {
    return debts.reduce((totals, row) => {
      totals.set(row.currency, (totals.get(row.currency) || 0) + row.total);
      return totals;
    }, new Map());
  }

  function formatDebtTotals(totals) {
    if (!totals.size) {
      return formatMoney(0, "BRL");
    }
    return [...totals.entries()].map(([currency, total]) => formatMoney(total, currency)).join(" · ");
  }

  function addInstallmentDebt(row, transaction, origin) {
    const amount = Number(transaction.amount || 0);
    const debtKey = transaction.series_id
      ? `${origin}:series:${transaction.series_id}`
      : `${origin}:single:${transaction.description}`;
    const debt = row.debts.get(debtKey) || { description: transaction.description || "Lançamento parcelado", total: 0, count: 0 };
    row.total += amount;
    debt.total += amount;
    debt.count += 1;
    row.debts.set(debtKey, debt);
  }

  function installmentDebtCountLabel(count) {
    return `${count} ${count === 1 ? "parcela restante" : "parcelas restantes"}`;
  }

  function isOpenInstallmentDebt(transaction, transactionMonth, currentMonth) {
    if (!isInstallmentTransaction(transaction) || transaction.type !== "expense" || transactionMonth < currentMonth) {
      return false;
    }
    return transactionMonth > currentMonth || !transaction.reconciled_at;
  }

  function renderTopExpensesChart() {
    if (state.cockpit?.top_expenses) {
      renderDonutListChart(topExpensesChart, state.cockpit.top_expenses, {
        empty: "Nenhuma despesa neste mês.",
        totalLabel: "Despesas",
      });
      return;
    }
    const prefix = currentMonthValue();
    const grouped = groupTransactionsByCategory(state.transactions.filter((transaction) => (
      transaction.date.startsWith(prefix) && transaction.type === "expense"
    )));
    renderDonutListChart(topExpensesChart, rankedChartItems(grouped, 5), {
      empty: "Nenhuma despesa neste mês.",
      totalLabel: "Despesas",
    });
  }

  function renderTopIncomeChart() {
    if (state.cockpit?.top_income) {
      renderDonutListChart(cashDistributionChart, state.cockpit.top_income, {
        empty: "Nenhuma receita neste mês.",
        totalLabel: "Receitas",
      });
      return;
    }
    const prefix = currentMonthValue();
    const grouped = groupTransactionsByCategory(state.transactions.filter((transaction) => (
      transaction.date.startsWith(prefix) && transaction.type === "income"
    )));
    renderDonutListChart(cashDistributionChart, rankedChartItems(grouped, 3), {
      empty: "Nenhuma receita neste mês.",
      totalLabel: "Receitas",
    });
  }

  function groupTransactionsByCategory(transactions) {
    const totals = new Map();
    for (const transaction of transactions) {
      const label = formatCategoryPath(transaction);
      totals.set(label, (totals.get(label) || 0) + Number(transaction.amount_brl || transaction.amount));
    }
    return [...totals.entries()]
      .map(([label, total]) => ({ label, total }))
      .sort((a, b) => b.total - a.total);
  }

  function rankedChartItems(items, visibleCount) {
    const validItems = items.filter((item) => item.total > 0);
    if (validItems.length <= visibleCount) {
      return validItems;
    }
    const visible = validItems.slice(0, visibleCount);
    const othersTotal = validItems.slice(visibleCount).reduce((sum, item) => sum + item.total, 0);
    if (othersTotal > 0) {
      visible.push({ label: "Outros", total: othersTotal });
    }
    return visible;
  }

  function renderDonutListChart(container, items, options) {
    container.innerHTML = "";
    const total = options.total ?? items.reduce((sum, item) => sum + item.total, 0);
    if (!total || items.length === 0) {
      container.append(emptyState(options.empty, true));
      return;
    }
    const chart = document.createElement("div");
    chart.className = "donut-chart";
    chart.innerHTML = `
      ${donutSvg(items, total)}
      <div class="donut-center">
        <span>${escapeHtml(options.totalLabel)}</span>
        <strong>${formatMoney(total, "BRL")}</strong>
      </div>
    `;
    const list = document.createElement("div");
    list.className = "chart-list";
    list.innerHTML = items.map((item, index) => {
      const percent = total ? item.total / total : 0;
      return `
        <div class="chart-row">
          <span><i style="background:${chartColor(index)}"></i>${escapeHtml(item.label)}</span>
          <strong>${formatMoney(item.total, "BRL")} · ${formatPercent(percent)}</strong>
        </div>
      `;
    }).join("");
    container.append(chart, list);
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
    return `<svg viewBox="0 0 120 120" role="img" aria-label="Gráfico de distribuição">${circles}</svg>`;
  }

  function renderCockpitPortfolioByType() {
    if (!cockpitPortfolioByType) {
      return;
    }
    if (!state.portfolio && state.portfolioDirty) {
      cockpitPortfolioByType.innerHTML = '<div class="empty-state compact">Atualizando portfólio...</div>';
      loadPortfolio();
      return;
    }
    if (state.portfolioLoading) {
      cockpitPortfolioByType.innerHTML = '<div class="empty-state compact">Atualizando portfólio...</div>';
      return;
    }
    if (state.portfolioError) {
      cockpitPortfolioByType.innerHTML = `<div class="empty-state compact">${escapeHtml(state.portfolioError)}</div>`;
      return;
    }
    if (state.portfolio && state.portfolioDirty && !state.portfolioLoading) {
      loadPortfolio();
    }
    const rows = state.portfolio && state.portfolio.summary ? state.portfolio.summary.by_type || [] : [];
    if (rows.length === 0) {
      cockpitPortfolioByType.innerHTML = '<div class="empty-state compact">Nenhum investimento em carteira.</div>';
      return;
    }
    const totalsByCurrency = portfolioTotalsByCurrency(rows);
    cockpitPortfolioByType.innerHTML = rows.map((row, index) => {
      const current = Number(row.current_brl || 0);
      const result = Number(row.result_brl || 0);
      const currency = row.currency || "BRL";
      const total = totalsByCurrency.get(currency) || 0;
      const percent = total > 0 ? current / total : 0;
      return `
        <article class="portfolio-cockpit-row">
          <div>
            <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
            <span>${row.count} posição(ões) · ${formatPercent(percent)}</span>
          </div>
          <div>
            <strong>${formatMoney(current, currency)}</strong>
            <span class="${result < 0 ? "danger-text" : "positive-text"}">${formatMoney(result, currency)}</span>
          </div>
        </article>
      `;
    }).join("");
  }

  return {
    renderCockpit,
    renderLimitAlerts,
    renderCockpitPortfolioByType,
  };
}
