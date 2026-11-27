import { registerTrendsView } from "./trends-view.js?v=187";
import { registerConsultorView } from "./consultor-view.js?v=185";
import { registerFinancialHealthView } from "./financial-health-view.js?v=2";
import { bindRovingTablist, syncRovingTabState, transitionView } from "./tab-utils.js";
import { stateMarkup } from "./dom-utils.js";
import { renderChart } from "./chart-adapter.js";
import { createNotificationFlyout } from "./notification-flyout.js?v=4";

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
  isInvestmentTransaction,
  chartColor,
  getCurrencyTotals,
  renderLimitAlerts,
  onCockpitMonthChanged,
  loadPortfolio,
  portfolioMaturityAlerts,
  goToPortfolio,
  onNavigateToTransaction,
  onNavigateToPortfolio,
  onNavigateToLimits,
  onNotificationAction,
  formatDate,
}) {
  const {
    monthIncome,
    monthExpense,
    monthInvestment,
    savingsRate,
    cockpitRoot,
    cockpitHealthSummary,
    cockpitTrendSummaryContent,
    monthlyBudgetSummary,
    cockpitTabs,
    cockpitSummaryPanel,
    cockpitMonthLabel,
    previousCockpitMonthButton,
    todayCockpitMonthButton,
    nextCockpitMonthButton,
    currencyList,
    installmentDebtList,
    topExpensesChart,
    cashDistributionChart,
    cockpitPortfolioByType,
    cockpitPortfolioMaturityAlert,
    cockpitVersionAlert,
    cockpitVersionAlertVersion,
    cockpitVersionAlertDismiss,
    cockpitNegativeBalanceNotice,
    cockpitNegativeBalanceNoticeTitle,
    cockpitNegativeBalanceNoticeDescription,
    cockpitNegativeBalanceNoticeAction,
    cockpitCriticalNotifications,
    cockpitInformationalNotifications,
    cockpitCombinedNotifications,
    cockpitCriticalNotificationCount,
    cockpitInformationalNotificationCount,
    cockpitCombinedNotificationCount,
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
    trendsTabs,
  } = elements;
  let versionAlertDismissed = false;
  let activeChartBreakdownClose = null;
  let notifications = { critical: [], informational: [], critical_count: 0, informational_count: 0 };
  let notificationsLoadedAt = 0;
  let notificationsInFlight = null;
  const notificationFlyout = createNotificationFlyout({
    onAction: (action, item) => onNotificationAction?.(action, item),
    onMarkSeen: markNotificationsSeen,
  });
  const cockpitDisclosures = Array.from(document.querySelectorAll("[data-cockpit-section]"));

  const trendsView = registerTrendsView({
    elements: {
      trendsPanel,
      trendsContent,
      trendsMeta,
      trendsTabs,
      cockpitTrendSummaryContent,
      monthlyBudgetSummary,
    },
    api,
    formatMoney,
    formatPercent,
    escapeHtml,
    formatMonthLabel: formatMonthLabel || formatMonthShortLabel,
    formatDate,
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
      financialHealthSummary: cockpitHealthSummary,
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
  cockpitNegativeBalanceNoticeAction?.addEventListener("click", () => {
    const notification = (notifications.critical || []).find((item) => item.type === "projected_negative_balance");
    if (notification?.action) onNotificationAction?.(notification.action, notification);
  });
  cockpitCriticalNotifications?.addEventListener("click", () => openNotifications("critical", cockpitCriticalNotifications));
  cockpitInformationalNotifications?.addEventListener("click", () => openNotifications("informational", cockpitInformationalNotifications));
  cockpitCombinedNotifications?.addEventListener("click", () => openNotifications("critical", cockpitCombinedNotifications));
  document.querySelector("[data-cockpit-tab-trigger='trends']")?.addEventListener("click", () => setCockpitTab("trends"));
  document.querySelector("[data-cockpit-tab-trigger='limits']")?.addEventListener("click", () => onNavigateToLimits?.(cockpitMonthValue()));
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
    loadNotifications();
    const totals = getCurrencyTotals();
    const monthTotals = state.cockpit?.month_totals || getCurrentMonthTotals();
    monthIncome.textContent = formatMoney(monthTotals.income, "BRL");
    monthExpense.textContent = formatMoney(monthTotals.expense, "BRL");
    monthInvestment.textContent = formatMoney(monthTotals.investment, "BRL");
    savingsRate.textContent = formatPercent(monthTotals.savings_rate ?? monthTotals.savingsRate);
    renderCurrencyTotals(totals);
    renderCockpitPortfolioByType();
    renderInstallmentDebts();
    renderLimitAlerts();
    renderPortfolioMaturityAlerts();
    renderTopExpensesChart();
    renderTopIncomeChart();
    trendsView.renderCockpitSummary(cockpitMonthValue());
    financialHealthView.renderCompactHealth(cockpitMonthValue());
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

  async function loadNotifications({ force = false } = {}) {
    if (!force && Date.now() - notificationsLoadedAt < 30000) return notifications;
    if (notificationsInFlight) return notificationsInFlight;
    notificationsInFlight = api("/api/cockpit/notifications")
      .then((result) => {
        notifications = result || notifications;
        notificationsLoadedAt = Date.now();
        renderNotificationIndicators();
        return notifications;
      })
      .catch(() => notifications)
      .finally(() => { notificationsInFlight = null; });
    return notificationsInFlight;
  }

  async function openNotifications(section, trigger) {
    await loadNotifications({ force: true });
    notificationFlyout.open(notifications, { section, trigger });
  }

  function renderNotificationIndicators() {
    const criticalCount = Number(notifications.critical_count || 0);
    const informationalCount = Number(notifications.informational_count || 0);
    updateNotificationButton(cockpitCriticalNotifications, cockpitCriticalNotificationCount, criticalCount, "alerta crítico", "alertas críticos");
    updateNotificationButton(cockpitInformationalNotifications, cockpitInformationalNotificationCount, informationalCount, "informativo novo", "informativos novos");
    updateNotificationButton(cockpitCombinedNotifications, cockpitCombinedNotificationCount, criticalCount + informationalCount, "notificação financeira", "notificações financeiras");
    cockpitCombinedNotifications?.classList.toggle("has-critical", criticalCount > 0);
    cockpitCombinedNotifications?.classList.toggle("has-informational", criticalCount === 0 && informationalCount > 0);
    renderNegativeBalanceNotice();
  }

  function renderNegativeBalanceNotice() {
    if (!cockpitNegativeBalanceNotice) return;
    const notification = (notifications.critical || []).find((item) => item.type === "projected_negative_balance");
    if (!notification) {
      cockpitNegativeBalanceNotice.hidden = true;
      return;
    }
    if (cockpitNegativeBalanceNoticeTitle) cockpitNegativeBalanceNoticeTitle.textContent = notification.title || "Saldo previsto ficará negativo";
    if (cockpitNegativeBalanceNoticeDescription) cockpitNegativeBalanceNoticeDescription.textContent = notification.description || "Revise os compromissos previstos desta conta.";
    cockpitNegativeBalanceNotice.hidden = false;
  }

  function updateNotificationButton(button, badge, count, singular, plural) {
    if (!button || !badge) return;
    badge.textContent = String(count);
    button.classList.toggle("has-items", count > 0);
    button.setAttribute("aria-label", count ? `${count} ${count === 1 ? singular : plural}` : `Nenhum ${singular}`);
  }

  async function markNotificationsSeen(notificationIds) {
    await api("/api/cockpit/notifications/mark-seen", {
      method: "POST",
      body: { notification_ids: notificationIds },
    });
    const ids = new Set(notificationIds);
    notifications.informational = (notifications.informational || []).map((item) => (
      ids.has(item.id) ? { ...item, seen: true } : item
    ));
    notifications.informational_count = notifications.informational.filter((item) => !item.seen).length;
    notificationsLoadedAt = Date.now();
    renderNotificationIndicators();
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
      // spec: frontend/frontend-modularizacao v4.40 — critério 4
      const reconciledTotal = [...amounts.accounts, ...amounts.cards].reduce(
        (total, item) => total + Number(item.reconciled || 0),
        0,
      );
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
            <em>Saldo conciliado · ${escapeHtml(monthLabel)}</em>
          </div>
          <strong class="${reconciledTotal < 0 ? "danger-text" : ""}">${formatMoney(reconciledTotal, currency)}</strong>
        </div>
        <div class="currency-table" role="table" aria-label="Saldos em ${escapeHtml(currency)}">
          <div class="currency-table-head" role="row">
            <span>Conta ou cartão</span>
            <span>Tipo</span>
            <span>Saldo conciliado</span>
          </div>
          ${accountRows || '<div class="currency-empty-row">Nenhuma conta ativa nesta moeda.</div>'}
          ${cardRows ? `<div class="currency-subgroup">Cartões de crédito</div>${cardRows}` : ""}
        </div>
      `;
      currencyList.append(section);
    }
  }

  function currencyTableRow(name, detail, amount, reconciled, currency, kind = "account") {
    const reconciledClass = reconciled < 0 ? "danger-text" : "";
    return `
      <div class="currency-table-row ${kind}" role="row">
        <span><b>${escapeHtml(name)}</b></span>
        <span>${escapeHtml(detail)}</span>
        <strong class="${reconciledClass}">${formatMoney(reconciled || 0, currency)}</strong>
      </div>
    `;
  }

  function renderInstallmentDebts() {
    if (!installmentDebtList) {
      return;
    }
    const data = state.cockpit?.open_debts;
    if (!data) {
      installmentDebtList.innerHTML = stateMarkup("Atualize o Cockpit para consultar as parcelas em aberto.", { kind: "loading" });
      return;
    }
    const debts = data.groups;
    if (debts.length === 0) {
      installmentDebtList.innerHTML = `
        <section class="planning-section">
          <div class="planning-section-header">
            <h3>Parcelas em aberto · estado atual</h3>
            <strong class="danger-text">${formatMoney(0, "BRL")}</strong>
          </div>
          ${stateMarkup("Compras parceladas em aberto aparecerão nesta seção.", { kind: "empty" })}
        </section>
      `;
      return;
    }
    const debtTotals = new Map(Object.entries(data.by_currency));
    installmentDebtList.innerHTML = `
      <section class="planning-section">
        <div class="planning-section-header">
          <h3>Parcelas em aberto · estado atual</h3>
          <div class="debt-total-block">
            <strong class="danger-text">${formatDebtTotals(debtTotals)}</strong>
            ${renderDebtTrend(data.trend_by_currency)}
          </div>
        </div>
        ${debts.map((row) => `
          <div class="debt-group">
            <div class="debt-group-header">
              <span>${escapeHtml(row.label)}</span>
              <strong>${formatMoney(row.total, row.currency)}</strong>
            </div>
            <div class="debt-items">
              ${row.debts.map((debt) => `
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


  function formatDebtTotals(totals) {
    if (!totals.size) {
      return formatMoney(0, "BRL");
    }
    return [...totals.entries()].map(([currency, total]) => formatMoney(total, currency)).join(" · ");
  }


  function renderDebtTrend(trends) {
    const entries = Object.entries(trends || {});
    if (!entries.length) return "";
    return `<div class="debt-trend-list" aria-label="Variação do endividamento por moeda">${entries.map(([currency, trend]) => {
      const direction = trend.direction || "stable";
      const arrow = direction === "up" ? "↑" : direction === "down" ? "↓" : "↔";
      const previousMonthLabel = formatMonthShortLabel(trend.previous_month);
      const label = direction === "up"
        ? `maior que ${previousMonthLabel}`
        : direction === "down"
          ? `menor que ${previousMonthLabel}`
          : `estável vs. ${previousMonthLabel}`;
      const amount = direction === "stable" ? "sem alteração" : formatMoney(trend.change, currency);
      return `<span class="debt-trend debt-trend-${direction}" aria-label="${escapeHtml(`Endividamento ${label}: ${amount}`)}"><span aria-hidden="true">${arrow}</span> ${escapeHtml(amount)} <small>vs. ${escapeHtml(previousMonthLabel)}</small></span>`;
    }).join("")}</div>`;
  }


  function installmentDebtCountLabel(count) {
    return `${count} ${count === 1 ? "parcela restante" : "parcelas restantes"}`;
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
      plotOptions: { pie: { donut: { size: "78%", labels: { show: false } } } },
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
    if (state.portfolioError) {
      cockpitPortfolioByType.innerHTML = stateMarkup(state.portfolioError, { kind: "error" });
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
    const rows = state.portfolio?.presentation?.analysis?.by_type || [];
    if (rows.length === 0) {
      cockpitPortfolioByType.innerHTML = stateMarkup("Adicione uma posição ou registre um aporte para acompanhar o portfólio.", { kind: "empty" });
      return;
    }
    cockpitPortfolioByType.innerHTML = rows.map((row, index) => {
      const current = Number(row.current_brl || 0);
      const result = Number(row.result_brl || 0);
      const currency = row.currency || "BRL";
      return `
        <article class="portfolio-cockpit-row">
          <div>
            <strong><i style="background:${chartColor(index)}"></i>${escapeHtml(row.label)}</strong>
            <span>${row.count} posição(ões) · ${Number(row.currency_participation_percent).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%</span>
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
