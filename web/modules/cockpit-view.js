export function registerCockpitView({
  state,
  elements,
  api,
  currentMonthValue,
  formatMonthLabel,
  shiftMonth,
  openMonthPicker,
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
  portfolioMaturityAlerts,
  goToPortfolio,
}) {
  const {
    monthIncome,
    monthExpense,
    monthInvestment,
    savingsRate,
    cockpitTabs,
    cockpitSummaryPanel,
    currencyList,
    monthlyPlanningList,
    installmentDebtList,
    topExpensesChart,
    cashDistributionChart,
    cockpitPortfolioByType,
    cockpitPortfolioMaturityAlert,
    financialHealthPanel,
    financialHealthMonthLabel,
    previousFinancialHealthMonthButton,
    nextFinancialHealthMonthButton,
    financialHealthContent,
  } = elements;
  let financialHealthRequestId = 0;

  cockpitTabs?.forEach((button) => {
    button.addEventListener("click", () => setCockpitTab(button.dataset.cockpitTab || "summary"));
  });
  previousFinancialHealthMonthButton?.addEventListener("click", () => setFinancialHealthMonth(shiftMonth(state.financialHealthMonth, -1)));
  nextFinancialHealthMonthButton?.addEventListener("click", () => setFinancialHealthMonth(shiftMonth(state.financialHealthMonth, 1)));
  financialHealthMonthLabel?.addEventListener("click", () => {
    openMonthPicker(financialHealthMonthLabel, state.financialHealthMonth, setFinancialHealthMonth);
  });

  function renderCockpit() {
    renderCockpitTabs();
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
      renderFinancialHealth();
    }
  }

  function setCockpitTab(tab) {
    const nextTab = tab === "health" ? "health" : "summary";
    if (state.cockpitTab === nextTab) {
      return;
    }
    state.cockpitTab = nextTab;
    renderCockpitTabs();
    if (nextTab === "health") {
      renderFinancialHealth();
    }
  }

  function activeCockpitTab() {
    return state.cockpitTab === "health" ? "health" : "summary";
  }

  function renderCockpitTabs() {
    const activeTab = activeCockpitTab();
    cockpitTabs?.forEach((button) => {
      const isActive = button.dataset.cockpitTab === activeTab;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
      button.tabIndex = isActive ? 0 : -1;
    });
    if (cockpitSummaryPanel) {
      cockpitSummaryPanel.hidden = activeTab !== "summary";
    }
    if (financialHealthPanel) {
      financialHealthPanel.hidden = activeTab !== "health";
    }
  }

  function setFinancialHealthMonth(month) {
    if (!month || month === state.financialHealthMonth) {
      return;
    }
    state.financialHealthMonth = month;
    state.financialHealth = null;
    state.financialHealthError = "";
    renderFinancialHealth();
    loadFinancialHealth().catch((error) => {
      state.financialHealthLoading = false;
      state.financialHealthError = error.message;
      renderFinancialHealth();
    });
  }

  async function loadFinancialHealth() {
    const requestId = ++financialHealthRequestId;
    state.financialHealthLoading = true;
    state.financialHealthError = "";
    renderFinancialHealth();
    const month = state.financialHealthMonth || currentMonthValue();
    const response = await api(`/api/financial-health-score?month=${encodeURIComponent(month)}`);
    if (requestId !== financialHealthRequestId) {
      return;
    }
    state.financialHealth = response;
    state.financialHealthLoading = false;
    state.financialHealthError = "";
    renderFinancialHealth();
  }

  function renderFinancialHealth() {
    if (!financialHealthContent || !financialHealthMonthLabel) {
      return;
    }
    renderCockpitTabs();
    if (!state.financialHealthMonth) {
      state.financialHealthMonth = currentMonthValue();
    }
    financialHealthMonthLabel.textContent = formatMonthLabel(state.financialHealthMonth);
    const data = state.financialHealth;
    if (!data || data.month !== state.financialHealthMonth) {
      if (!state.financialHealthLoading && !state.financialHealthError) {
        loadFinancialHealth().catch((error) => {
          state.financialHealthLoading = false;
          state.financialHealthError = error.message;
          renderFinancialHealth();
        });
      }
      financialHealthContent.innerHTML = `<div class="empty-state compact">${escapeHtml(state.financialHealthError || "Carregando score de saúde financeira...")}</div>`;
      return;
    }
    financialHealthContent.innerHTML = `
      <div class="financial-health-score-card ${financialHealthLevelClass(data.nivel)}">
        <strong>${Number(data.score_total || 0).toLocaleString("pt-BR")}</strong>
        <span>${escapeHtml(financialHealthLevelLabel(data.nivel))}</span>
        <small>Score de 0 a 1000</small>
      </div>

      <section class="financial-health-section">
        <h3>Seus Pilares</h3>
        <div class="financial-health-pillars" role="list" aria-label="Pontuação dos pilares de saúde financeira">
          ${(data.pilares || []).map((pillar) => financialHealthPillarBar(pillar)).join("")}
        </div>
      </section>

      <section class="financial-health-section">
        <h3>🔍 Análise detalhada dos pilares</h3>
        <div class="financial-health-detail-grid">
          ${(data.pilares || []).map((pillar) => financialHealthPillarDetail(pillar, data)).join("")}
        </div>
      </section>

      <section class="financial-health-section financial-peace-section">
        <h3>💡 Planeje sua Paz Financeira <span>(referências)</span></h3>
        ${financialPeaceCards(data)}
      </section>
    `;
  }

  function financialHealthPillarBar(pillar) {
    const score = Number(pillar.score || 0);
    const maxScore = Number(pillar.max_score || 0);
    const percent = maxScore > 0 ? Math.max(0, Math.min(100, (score / maxScore) * 100)) : 0;
    const help = financialHealthPillarHelp(pillar);
    return `
      <article class="financial-health-pillar-row ${financialHealthLevelClass(pillar.nivel)}" role="listitem">
        <div>
          <strong class="pillar-label-with-help">
            ${escapeHtml(pillar.label || "Pilar")}
            ${help ? inlineHelpIcon(help) : ""}
          </strong>
          <span>${Number(pillar.peso_pct || 0).toLocaleString("pt-BR")}%</span>
        </div>
        <div class="financial-health-bar" aria-hidden="true">
          <i style="width:${percent.toFixed(2)}%"></i>
        </div>
        <strong>${score.toLocaleString("pt-BR")}/${maxScore.toLocaleString("pt-BR")} pts</strong>
        <small class="sr-only">${escapeHtml(pillar.label || "Pilar")}: ${score} de ${maxScore} pontos, ${percent.toFixed(1)}%.</small>
      </article>
    `;
  }

  function financialHealthPillarDetail(pillar, data) {
    const extra = financialHealthPillarExtra(pillar, data);
    const help = financialHealthPillarHelp(pillar);
    return `
      <article class="financial-health-detail-card ${financialHealthLevelClass(pillar.nivel)}">
        <header>
          <span>${financialHealthLevelIcon(pillar.nivel)}</span>
          <div>
            <h4>
              ${escapeHtml(pillar.label || "Pilar")}
              ${help ? inlineHelpIcon(help) : ""}
            </h4>
            <small>${escapeHtml(financialHealthLevelLabel(pillar.nivel))}</small>
          </div>
        </header>
        <p>Sua pontuação: <strong>${Number(pillar.score || 0).toLocaleString("pt-BR")} / ${Number(pillar.max_score || 0).toLocaleString("pt-BR")} pts</strong>.</p>
        ${extra ? `<p>${extra}</p>` : ""}
        <p>${escapeHtml(pillar.mensagem || "Indicador calculado com base nos dados cadastrados.")}</p>
      </article>
    `;
  }

  function inlineHelpIcon(help) {
    return `<button class="inline-help-icon" type="button" aria-label="${escapeHtml(help)}" title="${escapeHtml(help)}" data-tooltip="${escapeHtml(help)}">i</button>`;
  }

  function financialHealthPillarHelp(pillar) {
    if (pillar.id === "poupanca") {
      return "Taxa de poupança = (receitas do mês - despesas de consumo do mês) / receitas do mês. Investimentos/aportes, transferências, câmbio e pagamentos de fatura não entram como despesa de consumo.";
    }
    return "";
  }

  function financialHealthPillarExtra(pillar, data) {
    if (pillar.id === "reserva") {
      const months = Number(data.meses_reserva || pillar.meses_reserva || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
      return `Reserva marcada cobre <strong>${months} mês(es)</strong> de despesas médias. Valor elegível: <strong>${formatCents(data.reserva_elegivel_cents)}</strong>.`;
    }
    if (pillar.id === "endividamento") {
      return `Parcelas do mês: <strong>${formatCents(data.dividas_parcelas_mes_cents)}</strong> · comprometimento: <strong>${formatDecimalPercent(data.comprometimento_divida_mes_pct)}</strong>.`;
    }
    if (pillar.id === "concentracao_portfolio") {
      return `Maior concentração: <strong>${formatDecimalPercent(data.maior_concentracao_portfolio_pct)}</strong> · Poupança: <strong>${formatDecimalPercent(data.concentracao_poupanca_pct)}</strong>.`;
    }
    if (pillar.id === "poupanca") {
      return `Receitas: <strong>${formatCents(data.receitas_cents)}</strong> · despesas de consumo: <strong>${formatCents(data.despesas_consumo_cents)}</strong>.`;
    }
    return "";
  }

  function financialPeaceCards(data) {
    const peace = data.paz_financeira || {};
    const cards = [
      ["🎯", "Independência mensal (Estimativa)", data.paz_independencia_cents, peace.independencia_mensal_legenda || "Referência aproximada de patrimônio para renda passiva mensal equivalente."],
      ["🛡️", "Reserva estimada", data.paz_reserva_estimada_cents, "Referência simples de 6 vezes a receita de base."],
      ["🏠", "Recorrentes saudáveis (Estimativa)", data.paz_recorrentes_saudaveis_cents, "Referência para despesas recorrentes mensais."],
      ["🎉", "Lazer saudável (Estimativa)", data.paz_lazer_saudavel_cents, "Referência para lazer mensal sem afetar planejamento."],
    ];
    return `
      <div class="financial-peace-grid">
        ${cards.map(([icon, title, cents, description]) => `
          <article class="financial-peace-card">
            <span>${icon}</span>
            <div>
              <h4>${escapeHtml(title)}</h4>
              <strong>${formatCents(cents)}</strong>
              <p>${escapeHtml(description)}</p>
            </div>
          </article>
        `).join("")}
      </div>
      <p class="financial-peace-note">ⓘ Valores baseados na receita de referência (${formatCents(data.paz_financeira_base_receita_cents)}) · confiança ${escapeHtml(financialPeaceConfidenceLabel(data.paz_financeira_confianca))}. ${escapeHtml(peace.aviso || "")} ${escapeHtml(peace.mensagem || "")}</p>
    `;
  }

  function formatCents(cents) {
    return formatMoney(Number(cents || 0) / 100, "BRL");
  }

  function formatDecimalPercent(value) {
    return `${Number(value || 0).toLocaleString("pt-BR", { maximumFractionDigits: 2 })}%`;
  }

  function financialHealthLevelLabel(level) {
    return ({
      critico: "Crítico",
      atencao: "Atenção",
      bom: "Bom",
      excelente: "Excelente",
    })[level] || "Atenção";
  }

  function financialHealthLevelIcon(level) {
    return ({
      critico: "●",
      atencao: "▲",
      bom: "✓",
      excelente: "✓",
    })[level] || "•";
  }

  function financialHealthLevelClass(level) {
    return `level-${["critico", "atencao", "bom", "excelente"].includes(level) ? level : "atencao"}`;
  }

  function financialPeaceConfidenceLabel(value) {
    if (value === "alta") {
      return "alta";
    }
    if (value === "menor") {
      return "menor";
    }
    if (value === "intermediaria") {
      return "intermediária";
    }
    return "indisponível";
  }

  function renderPortfolioMaturityAlerts() {
    const alerts = portfolioMaturityAlerts();
    if (alerts.length > 0) {
      setPortfolioNavAlert(true);
    }
    if (!cockpitPortfolioMaturityAlert) {
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
    const prefix = currentMonthValue();
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
      return '<div class="empty-state compact">Nada previsto neste mês.</div>';
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

  function isCreditCardPaymentTransaction(transaction) {
    return Boolean(transaction?.is_credit_card_payment);
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
    renderPortfolioMaturityAlerts,
    renderCockpitPortfolioByType,
  };
}
