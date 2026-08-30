import { registerTrendsView } from "./trends-view.js";
import { registerConsultorView } from "./consultor-view.js";
import { registerFinancialHealthView } from "./financial-health-view.js";
import { bindRovingTablist, syncRovingTabState, transitionView } from "./tab-utils.js";
import { stateMarkup } from "./dom-utils.js";
import { renderChart } from "./chart-adapter.js";

const COCKPIT_DISCLOSURE_KEY = "sf-cockpit-disclosures-v1";

export function registerCockpitView({
  state,
  elements,
  api,
  currentMonthValue,
  formatMonthLabel,
  formatMonthShortLabel,
  shiftMonth,
  openMonthPicker,
  formatMoney,
  formatPercent,
  formatPercentValue,
  emptyState,
  escapeHtml,
  formatCategoryPath,
  isInstallmentTransaction,
  isInvestmentTransaction,
  chartColor,
  getCurrencyTotals,
  renderLimitAlerts,
  onCockpitMonthChanged,
  loadPortfolio,
  portfolioTotalsByCurrency,
  portfolioMaturityAlerts,
  goToPortfolio,
  onNavigateToTransaction,
  onNavigateToPortfolio,
  formatDate,
}) {
  const {
    monthIncome,
    monthExpense,
    monthInvestment,
    savingsRate,
    cockpitRoot,
    cockpitTabs,
    cockpitSummaryPanel,
    cockpitMonthLabel,
    previousCockpitMonthButton,
    todayCockpitMonthButton,
    nextCockpitMonthButton,
    currencyList,
    monthlyPlanningList,
    installmentDebtList,
    topExpensesChart,
    cashDistributionChart,
    cockpitPortfolioByType,
    cockpitPortfolioMaturityAlert,
    cockpitVersionAlert,
    cockpitVersionAlertVersion,
    cockpitVersionAlertDismiss,
    cockpitCalendarPanel,
    cockpitCalendarMeta,
    consultorTabs,
    consultorAnalysesPanel,
    consultorHistoryPanel,
    consultorStatus,
    consultorCardGrid,
    consultorOutput,
    consultorHistoryList,
    consultorHistoryFilter,
    consultorHistoryRefreshButton,
    overdueReceivablesList,
    overduePayablesList,
    maturity30DaysList,
    maturity60DaysList,
    financialHealthPanel,
    financialHealthContent,
    trendsPanel,
    trendsContent,
    trendsMeta,
  } = elements;
  let versionAlertDismissed = false;
  let activeChartBreakdownClose = null;
  const cockpitDisclosures = Array.from(document.querySelectorAll("[data-cockpit-section]"));

  const trendsView = registerTrendsView({
    elements: { trendsPanel, trendsContent, trendsMeta },
    api,
    formatMoney,
    formatPercent,
    escapeHtml,
    formatMonthLabel: formatMonthLabel || formatMonthShortLabel,
  });

  const consultorView = registerConsultorView({
    elements: {
      cockpitCalendarPanel,
      cockpitCalendarMeta,
      consultorTabs,
      consultorAnalysesPanel,
      consultorHistoryPanel,
      consultorStatus,
      consultorCardGrid,
      consultorOutput,
      consultorHistoryList,
      consultorHistoryFilter,
      consultorHistoryRefreshButton,
      overdueReceivablesList,
      overduePayablesList,
      maturity30DaysList,
      maturity60DaysList,
    },
    api,
    formatMoney,
    formatDate,
    escapeHtml,
    emptyState,
    onNavigateToTransaction,
    onNavigateToPortfolio,
  });

  const financialHealthView = registerFinancialHealthView({
    elements: {
      financialHealthContent,
    },
    api,
    formatMoney,
    formatPercentValue,
    escapeHtml,
  });

  bindRovingTablist(cockpitTabs, {
    valueFor: (button) => button.dataset.cockpitTab || "summary",
    onSelect: setCockpitTab,
  });
  previousCockpitMonthButton?.addEventListener("click", () => setCockpitMonth(shiftMonth(cockpitMonthValue(), -1)));
  todayCockpitMonthButton?.addEventListener("click", () => setCockpitMonth(currentMonthValue()));
  nextCockpitMonthButton?.addEventListener("click", () => setCockpitMonth(shiftMonth(cockpitMonthValue(), 1)));
  cockpitMonthLabel?.addEventListener("click", () => {
    openMonthPicker(cockpitMonthLabel, cockpitMonthValue(), setCockpitMonth);
  });
  cockpitVersionAlertDismiss?.addEventListener("click", () => {
    versionAlertDismissed = true;
    renderVersionAlert();
  });
  initializeCockpitDisclosures();

  function initializeCockpitDisclosures() {
    let stored = {};
    try {
      stored = JSON.parse(localStorage.getItem(COCKPIT_DISCLOSURE_KEY) || "{}");
    } catch (_error) {
      stored = {};
    }
    cockpitDisclosures.forEach((disclosure) => {
      const key = disclosure.dataset.cockpitSection;
      if (typeof stored[key] === "boolean") disclosure.open = stored[key];
      disclosure.addEventListener("toggle", persistCockpitDisclosures);
    });
  }

  function persistCockpitDisclosures() {
    const stateBySection = Object.fromEntries(
      cockpitDisclosures.map((disclosure) => [disclosure.dataset.cockpitSection, disclosure.open]),
    );
    try {
      localStorage.setItem(COCKPIT_DISCLOSURE_KEY, JSON.stringify(stateBySection));
    } catch (_error) {
      // Preferência visual opcional: falhas de storage não bloqueiam o Cockpit.
    }
  }

  function renderCockpit() {
    renderCockpitTabs();
    renderCockpitMonthLabel();
    renderVersionAlert();
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
    renderPortfolioMaturityAlerts();
    renderTopExpensesChart();
    renderTopIncomeChart();
    if (activeCockpitTab() === "health") {
      financialHealthView.renderFinancialHealth(cockpitMonthValue());
    }
    if (activeCockpitTab() === "trends") {
      trendsView.renderTrends(cockpitMonthValue());
    }
    if (activeCockpitTab() === "calendar") {
      consultorView.renderCalendar();
    }
  }

  function renderVersionAlert() {
    if (!cockpitVersionAlert) {
      return;
    }
    const info = state.latestVersion;
    if (versionAlertDismissed || !info || !info.update_available || !info.latest_version) {
      cockpitVersionAlert.hidden = true;
      return;
    }
    if (cockpitVersionAlertVersion) {
      cockpitVersionAlertVersion.textContent = info.latest_version;
    }
    cockpitVersionAlert.hidden = false;
  }

  function setCockpitTab(tab) {
    const allowedTabs = new Set(["summary", "calendar", "trends", "health"]);
    const nextTab = allowedTabs.has(tab) ? tab : "summary";
    if (state.cockpitTab === nextTab) {
      return;
    }
    const updateActivePanel = () => {
      state.cockpitTab = nextTab;
      renderCockpitTabs();
    };
    transitionView(updateActivePanel);
    if (nextTab === "calendar") {
      consultorView.renderCalendar();
    }
    if (nextTab === "health") {
      financialHealthView.renderFinancialHealth(cockpitMonthValue());
    }
    if (nextTab === "trends") {
      trendsView.renderTrends(cockpitMonthValue());
    }
  }

  function setLoading(isLoading) {
    if (!cockpitRoot) {
      return;
    }
    cockpitRoot.setAttribute("aria-busy", isLoading ? "true" : "false");
    cockpitRoot.classList.toggle("is-refreshing", Boolean(isLoading));
  }

  function activeCockpitTab() {
    const allowedTabs = new Set(["summary", "calendar", "trends", "health"]);
    return allowedTabs.has(state.cockpitTab) ? state.cockpitTab : "summary";
  }

  function renderCockpitTabs() {
    const activeTab = activeCockpitTab();
    syncRovingTabState(cockpitTabs, activeTab, (button) => button.dataset.cockpitTab || "summary");
    if (cockpitSummaryPanel) {
      cockpitSummaryPanel.hidden = activeTab !== "summary";
    }
    if (cockpitCalendarPanel) {
      cockpitCalendarPanel.hidden = activeTab !== "calendar";
    }
    if (financialHealthPanel) {
      financialHealthPanel.hidden = activeTab !== "health";
    }
    if (trendsPanel) {
      trendsPanel.hidden = activeTab !== "trends";
    }
  }

  function renderCockpitMonthLabel() {
    if (cockpitMonthLabel) {
      cockpitMonthLabel.textContent = formatMonthShortLabel(cockpitMonthValue());
    }
  }

  function cockpitMonthValue() {
    if (!state.cockpitMonth) {
      state.cockpitMonth = currentMonthValue();
    }
    return state.cockpitMonth;
  }

  function setCockpitMonth(month) {
    if (!month || month === cockpitMonthValue()) {
      return;
    }
    state.cockpitMonth = month;
    state.cockpit = null;
    state.trendsError = "";
    renderCockpitTabs();
    renderCockpitMonthLabel();
    if (typeof onCockpitMonthChanged === "function") {
      onCockpitMonthChanged().catch(() => {
        renderCockpit();
      });
    }
  }

  function renderPortfolioMaturityAlerts() {
    const alerts = portfolioMaturityAlerts();
    if (!cockpitPortfolioMaturityAlert) {
      setPortfolioNavAlert(false);
      return;
    }
    if (!state.portfolio && state.portfolioDirty) {
      cockpitPortfolioMaturityAlert.hidden = true;
      cockpitPortfolioMaturityAlert.innerHTML = "";
      loadPortfolio();
      return;
    }
    if (state.portfolioLoading) {
      cockpitPortfolioMaturityAlert.hidden = true;
      cockpitPortfolioMaturityAlert.innerHTML = "";
      return;
    }
    setPortfolioNavAlert(alerts.length > 0);
    if (alerts.length === 0) {
      cockpitPortfolioMaturityAlert.hidden = true;
      cockpitPortfolioMaturityAlert.innerHTML = "";
      return;
    }
    const overdueCount = alerts.filter((alert) => alert.status === "overdue").length;
    const dueTodayCount = alerts.length - overdueCount;
    const headline = [
      overdueCount ? `${overdueCount} vencido(s)` : "",
      dueTodayCount ? `${dueTodayCount} vencendo hoje` : "",
    ].filter(Boolean).join(" e ");
    const first = alerts[0];
    cockpitPortfolioMaturityAlert.hidden = false;
    cockpitPortfolioMaturityAlert.innerHTML = `
      <button class="cockpit-alert-card portfolio-maturity-alert-card" type="button" data-go-portfolio>
        <span class="cockpit-alert-beacon" aria-hidden="true"></span>
        <span>
          <strong>${escapeHtml(headline || `${alerts.length} ativo(s) vencendo`)}</strong>
          <small>${escapeHtml(first.label)} · ${escapeHtml(first.accountName)} · venc. ${formatDate(first.maturityDate)}</small>
        </span>
        <b>Ver portfólio</b>
      </button>
    `;
    cockpitPortfolioMaturityAlert.querySelector("[data-go-portfolio]").addEventListener("click", goToPortfolio);
  }

  function setPortfolioNavAlert(active) {
    document.querySelectorAll('[data-view="portfolio"]').forEach((button) => {
      button.classList.toggle("has-alert", active);
    });
  }

  function getCurrentMonthTotals() {
    const prefix = cockpitMonthValue();
    return state.transactions.reduce((totals, transaction) => {
      if (!transaction.date.startsWith(prefix) || isCreditCardPaymentTransaction(transaction)) {
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
    const monthLabel = formatMonthLabel(cockpitMonthValue());
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
            <em>Previsto em ${escapeHtml(monthLabel)}</em>
          </div>
          <strong class="${amounts.current < 0 ? "danger-text" : ""}">${formatMoney(amounts.current, currency)}</strong>
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
    const amountClass = amount < 0 ? "danger-text" : "";
    const reconciledClass = reconciled < 0 ? "danger-text" : "";
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
    const monthLabel = formatMonthLabel(cockpitMonthValue());
    if (state.cockpit?.planning) {
      monthlyPlanningList.innerHTML = "";
      monthlyPlanningList.append(
        planningSectionFromRows(`Receitas recorrentes · ${monthLabel}`, state.cockpit.planning.income || [], "income"),
        planningSectionFromRows(`Investimentos planejados · ${monthLabel}`, state.cockpit.planning.investment || [], "investment"),
        planningSectionFromRows(`Despesas recorrentes · ${monthLabel}`, state.cockpit.planning.expense || [], "expense"),
      );
      return;
    }
    const prefix = cockpitMonthValue();
    const sections = [
      [`Receitas recorrentes · ${monthLabel}`, "income", (transaction) => transaction.type === "income" && transaction.series_kind === "recurring"],
      [`Investimentos planejados · ${monthLabel}`, "investment", (transaction) => isInvestmentTransaction(transaction) && transaction.series_kind !== "single"],
      [`Despesas recorrentes · ${monthLabel}`, "expense", (transaction) => transaction.type === "expense" && transaction.series_kind === "recurring"],
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
    const content = planningCurrencyGroups(rows);
    section.innerHTML = `
      <div class="planning-section-header">
        <h3>${title}</h3>
      </div>
      ${content}
    `;
    return section;
  }

  function planningSection(title, transactions, kind = "neutral") {
    const totals = new Map();
    for (const transaction of transactions) {
      const currency = transaction.account_currency || transaction.card_currency || "BRL";
      const label = formatCategoryPath(transaction);
      const key = `${currency}\u0000${label}`;
      const row = totals.get(key) || { currency, label, total: 0 };
      row.total += Number(transaction.amount || 0);
      totals.set(key, row);
    }
    return planningSectionFromRows(title, [...totals.values()], kind);
  }

  function planningCurrencyGroups(rows) {
    if (!rows.length) {
      return stateMarkup("Cadastre lançamentos previstos ou selecione outro mês.", { kind: "empty" });
    }
    const currencies = new Map();
    for (const item of rows) {
      const currency = item.currency || "BRL";
      const group = currencies.get(currency) || [];
      group.push(item);
      currencies.set(currency, group);
    }
    return [...currencies.entries()]
      .sort(([left], [right]) => left.localeCompare(right))
      .map(([currency, items]) => {
        const total = items.reduce((sum, item) => sum + Number(item.total || 0), 0);
        const itemRows = items.map((item) => `
          <div class="planning-row">
            <span>${escapeHtml(item.label)}</span>
            <strong>${formatMoney(item.total, currency)}</strong>
          </div>
        `).join("");
        return `
          <div class="planning-currency-group">
            <div class="planning-currency-header">
              <span>${escapeHtml(currency)}</span>
              <strong>${formatMoney(total, currency)}</strong>
            </div>
            ${itemRows}
          </div>
        `;
      }).join("");
  }

  function renderInstallmentDebts() {
    if (!installmentDebtList) {
      return;
    }
    const currentMonth = cockpitMonthValue();
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
            <h3>Total em aberto desde ${escapeHtml(formatMonthLabel(currentMonth))}</h3>
            <strong class="danger-text">${formatMoney(0, "BRL")}</strong>
          </div>
          ${stateMarkup("Compras parceladas em aberto aparecerão nesta seção.", { kind: "empty" })}
        </section>
      `;
      return;
    }
    const debtTotals = summarizeDebtTotals(debts);
    installmentDebtList.innerHTML = `
      <section class="planning-section">
        <div class="planning-section-header">
          <h3>Total em aberto desde ${escapeHtml(formatMonthLabel(currentMonth))}</h3>
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
    const prefix = cockpitMonthValue();
    const grouped = groupTransactionsByCategory(state.transactions.filter((transaction) => (
      transaction.date.startsWith(prefix) && transaction.type === "expense" && !isCreditCardPaymentTransaction(transaction)
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
    const prefix = cockpitMonthValue();
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

  function isCreditCardPaymentTransaction(transaction) {
    return Boolean(transaction?.is_credit_card_payment);
  }

  function rankedChartItems(items, visibleCount) {
    const validItems = items.filter((item) => item.total > 0);
    if (validItems.length <= visibleCount) {
      return validItems;
    }
    const visible = validItems.slice(0, visibleCount);
    const otherItems = validItems.slice(visibleCount);
    const othersTotal = otherItems.reduce((sum, item) => sum + item.total, 0);
    if (othersTotal > 0) {
      visible.push({ label: "Outros", total: othersTotal, items: otherItems });
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
      <div class="apex-donut-chart" role="img" aria-label="Gráfico de distribuição"></div>
      <div class="donut-center">
        <span>${escapeHtml(options.totalLabel)}</span>
        <strong>${formatMoney(total, "BRL")}</strong>
      </div>
    `;
    const list = document.createElement("div");
    list.className = "chart-list";
    list.innerHTML = items.map((item, index) => {
      const percent = total ? item.total / total : 0;
      const content = `
        <span><i style="background:${chartColor(index)}"></i>${escapeHtml(item.label)}</span>
        <strong>${formatMoney(item.total, "BRL")} · ${formatPercent(percent)}</strong>
      `;
      if (Array.isArray(item.items) && item.items.length > 0) {
        const helpLabel = `Ver o detalhamento das despesas agregadas em ${item.label}.`;
        return `
          <button class="chart-row chart-row-button" type="button" data-chart-breakdown-index="${index}" aria-label="${escapeHtml(helpLabel)}" title="${escapeHtml(helpLabel)}">
            <span><i style="background:${chartColor(index)}"></i>${escapeHtml(item.label)}<span class="inline-help-icon" data-tooltip="${escapeHtml(helpLabel)}" aria-hidden="true">i</span></span>
            <strong>${formatMoney(item.total, "BRL")} · ${formatPercent(percent)}</strong>
          </button>
        `;
      }
      return `
        <div class="chart-row">
          ${content}
        </div>
      `;
    }).join("");
    list.querySelectorAll("[data-chart-breakdown-index]").forEach((button) => {
      const item = items[Number(button.dataset.chartBreakdownIndex)];
      button.addEventListener("click", () => openChartBreakdownModal(item, total, options.totalLabel));
    });
    container.append(chart, list);
    renderChart(chart.querySelector(".apex-donut-chart"), {
      chart: { type: "donut", height: 184 },
      series: items.map((item) => Number(item.total || 0)),
      labels: items.map((item) => item.label),
      colors: items.map((_, index) => chartColor(index)),
      legend: { show: false },
      stroke: { width: 0 },
      tooltip: { y: { formatter: (value) => formatMoney(value, "BRL") } },
      plotOptions: { pie: { donut: { size: "72%", labels: { show: false } } } },
    });
  }

  function openChartBreakdownModal(item, chartTotal, totalLabel) {
    closeChartBreakdownModal();
    const rows = [...(item.items || [])].sort((a, b) => (b.total || 0) - (a.total || 0));
    const backdrop = document.createElement("div");
    backdrop.className = "decision-modal-backdrop";
    backdrop.innerHTML = `
      <section class="decision-modal cockpit-breakdown-modal" role="dialog" aria-modal="true" aria-labelledby="cockpit-breakdown-title">
        <div class="decision-modal-header">
          <h3 id="cockpit-breakdown-title">Detalhes de ${escapeHtml(item.label)}</h3>
          <p>${escapeHtml(totalLabel || "Total")}: ${formatMoney(item.total || 0, "BRL")} · ${formatPercent(chartTotal ? (item.total || 0) / chartTotal : 0)}</p>
        </div>
        <div class="decision-modal-body">
          <div class="cockpit-breakdown-list">
            ${rows.map((row) => `
              <div class="cockpit-breakdown-row">
                <span>${escapeHtml(row.label || "Sem categoria")}</span>
                <strong>${formatMoney(row.total || 0, "BRL")}</strong>
              </div>
            `).join("")}
          </div>
        </div>
        <div class="decision-modal-actions">
          <button class="secondary" type="button" data-close-chart-breakdown>Fechar</button>
        </div>
      </section>
    `;
    const closeButton = backdrop.querySelector("[data-close-chart-breakdown]");
    const close = () => {
      document.removeEventListener("keydown", onKeydown);
      backdrop.remove();
      activeChartBreakdownClose = null;
    };
    const onKeydown = (event) => {
      if (event.key === "Escape") {
        close();
      }
    };
    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) {
        close();
      }
    });
    closeButton?.addEventListener("click", close);
    document.addEventListener("keydown", onKeydown);
    document.body.append(backdrop);
    activeChartBreakdownClose = close;
    closeButton?.focus();
  }

  function closeChartBreakdownModal() {
    if (activeChartBreakdownClose) {
      activeChartBreakdownClose();
    }
  }

  function renderCockpitPortfolioByType() {
    if (!cockpitPortfolioByType) {
      return;
    }
    if (!state.portfolio && state.portfolioDirty) {
      cockpitPortfolioByType.innerHTML = stateMarkup("Atualizando posições e cotações do portfólio.", { kind: "loading" });
      loadPortfolio();
      return;
    }
    if (state.portfolioLoading) {
      cockpitPortfolioByType.innerHTML = stateMarkup("Atualizando posições e cotações do portfólio.", { kind: "loading" });
      return;
    }
    if (state.portfolioError) {
      cockpitPortfolioByType.innerHTML = stateMarkup(state.portfolioError, { kind: "error" });
      return;
    }
    if (state.portfolio && state.portfolioDirty && !state.portfolioLoading) {
      loadPortfolio();
    }
    const rows = state.portfolio && state.portfolio.summary ? state.portfolio.summary.by_type || [] : [];
    if (rows.length === 0) {
      cockpitPortfolioByType.innerHTML = stateMarkup("Adicione uma posição ou registre um aporte para acompanhar o portfólio.", { kind: "empty" });
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
    renderPortfolioMaturityAlerts,
    renderCockpitPortfolioByType,
    setLoading,
    invalidateFinancialHealth: () => financialHealthView.invalidateFinancialHealth(),
    invalidateCalendar: () => consultorView.invalidateCalendar(),
  };
}
