import { registerTrendsView } from "./trends-view.js";

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
}) {
  const {
    monthIncome,
    monthExpense,
    monthInvestment,
    savingsRate,
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
  let financialHealthRequestId = 0;
  let calendarRequestId = 0;
  let versionAlertDismissed = false;
  let activeChartBreakdownClose = null;

  const trendsView = registerTrendsView({
    elements: { trendsPanel, trendsContent, trendsMeta },
    api,
    formatMoney,
    formatPercent,
    escapeHtml,
    formatMonthLabel: formatMonthLabel || formatMonthShortLabel,
  });

  cockpitTabs?.forEach((button) => {
    button.addEventListener("click", () => setCockpitTab(button.dataset.cockpitTab || "summary"));
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
      renderFinancialHealth();
    }
    if (activeCockpitTab() === "trends") {
      trendsView.renderTrends(cockpitMonthValue());
    }
    if (activeCockpitTab() === "calendar") {
      renderCockpitCalendar();
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
    state.cockpitTab = nextTab;
    renderCockpitTabs();
    if (nextTab === "calendar") {
      renderCockpitCalendar();
    }
    if (nextTab === "health") {
      renderFinancialHealth();
    }
    if (nextTab === "trends") {
      trendsView.renderTrends(cockpitMonthValue());
    }
  }

  function activeCockpitTab() {
    const allowedTabs = new Set(["summary", "calendar", "trends", "health"]);
    return allowedTabs.has(state.cockpitTab) ? state.cockpitTab : "summary";
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
    state.financialHealthMonth = month;
    state.cockpit = null;
    state.financialHealth = null;
    state.financialHealthError = "";
    state.trendsData = null;
    state.trendsError = "";
    renderCockpit();
    if (typeof onCockpitMonthChanged === "function") {
      onCockpitMonthChanged().catch((error) => {
        state.financialHealthLoading = false;
        state.financialHealthError = error.message;
        renderCockpit();
      });
    }
  }

  async function loadFinancialHealth() {
    const requestId = ++financialHealthRequestId;
    state.financialHealthLoading = true;
    state.financialHealthError = "";
    renderFinancialHealth();
    const month = cockpitMonthValue();
    state.financialHealthMonth = month;
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
    if (!financialHealthContent) {
      return;
    }
    renderCockpitTabs();
    state.financialHealthMonth = cockpitMonthValue();
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
      ${financialHealthGauge(data)}

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

  function financialHealthGauge(data) {
    const score = Math.max(0, Math.min(1000, Number(data.score_total || 0)));
    const ratio = score / 1000;
    const rotation = -90 + ratio * 180;
    const zone = financialHealthScoreZone(score);
    return `
      <section class="financial-health-gauge-card ${zone.className}" aria-label="Score de saúde financeira">
        <div class="financial-health-gauge-shell">
          <div
            class="financial-health-gauge"
            role="img"
            aria-label="Score ${score.toLocaleString("pt-BR")} de 1000. Status ${escapeHtml(zone.label)}."
            style="--score-ratio:${ratio.toFixed(4)}; --needle-rotation:${rotation.toFixed(2)}deg"
          >
            <div class="financial-health-gauge-arc" aria-hidden="true"></div>
            <div class="financial-health-gauge-needle" aria-hidden="true"></div>
          </div>
          <div class="financial-health-gauge-scale" aria-hidden="true">
            <span>0</span>
            <span>300</span>
            <span>500</span>
            <span>750</span>
            <span>1000</span>
          </div>
        </div>
        <div class="financial-health-gauge-copy">
          <p class="eyebrow">Diagnóstico do mês</p>
          <strong class="financial-health-gauge-score">${score.toLocaleString("pt-BR")}</strong>
          <span class="financial-health-gauge-status">${escapeHtml(zone.label)}</span>
          <h3>${escapeHtml(zone.title)}</h3>
          <p>${escapeHtml(zone.meaning)}</p>
          <div class="financial-health-zone-legend" aria-label="Faixas do score">
            <span><i class="zone-critico"></i>0–299 Crítico</span>
            <span><i class="zone-atencao"></i>300–499 Atenção</span>
            <span><i class="zone-bom"></i>500–749 Moderado</span>
            <span><i class="zone-excelente"></i>750–1000 Excelente</span>
          </div>
        </div>
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
    const levelLabel = financialHealthLevelLabel(pillar.nivel);
    const score = Number(pillar.score || 0).toLocaleString("pt-BR");
    const maxScore = Number(pillar.max_score || 0).toLocaleString("pt-BR");
    return `
      <details class="financial-health-detail-card ${financialHealthLevelClass(pillar.nivel)}">
        <summary>
          <span class="financial-health-status-icon">${financialHealthLevelIcon(pillar.nivel)}</span>
          <div>
            <h4>
              ${escapeHtml(pillar.label || "Pilar")}
              ${help ? inlineHelpIcon(help) : ""}
            </h4>
            <small>${escapeHtml(levelLabel)}</small>
          </div>
          <strong>${score} / ${maxScore} pts</strong>
        </summary>
        <div class="financial-health-detail-body">
          <p>Sua pontuação: <strong>${score} / ${maxScore} pts</strong>.</p>
          ${extra ? `<p>${extra}</p>` : ""}
          <p>${escapeHtml(pillar.mensagem || "Indicador calculado com base nos dados cadastrados.")}</p>
        </div>
      </details>
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
    const confidence = financialPeaceConfidenceLabel(data.paz_financeira_confianca);
    const base = formatCents(data.paz_financeira_base_receita_cents);
    const cards = [
      ["🎯", "Independência mensal", data.paz_independencia_cents, "Receita de referência × 175", peace.independencia_mensal_legenda || "Patrimônio estimado para gerar renda passiva mensal equivalente à receita de referência, usando heurística simplificada."],
      ["🛡️", "Reserva estimada", data.paz_reserva_estimada_cents, "Receita de referência × 6", "Referência simples de reserva baseada na receita recorrente; o pilar Reserva continua usando despesas reais e posições marcadas."],
      ["🏠", "Recorrentes saudáveis", data.paz_recorrentes_saudaveis_cents, "Receita de referência × 0,5", "Referência para observar o peso das despesas recorrentes mensais dentro da renda de base."],
      ["🎉", "Lazer saudável", data.paz_lazer_saudavel_cents, "Receita de referência × 0,3", "Referência aproximada para lazer mensal sem perder de vista o planejamento geral."],
    ];
    return `
      <div class="financial-peace-grid">
        ${cards.map(([icon, title, cents, formula, description]) => `
          <details class="financial-peace-card">
            <summary>
              <span>${icon}</span>
              <div>
                <h4>${escapeHtml(title)}</h4>
                <strong>${formatCents(cents)}</strong>
              </div>
            </summary>
            <div>
              <small>${escapeHtml(formula)}</small>
              <p>${escapeHtml(description)}</p>
              <p>Base usada: <strong>${base}</strong> · confiança ${escapeHtml(confidence)}.</p>
            </div>
          </details>
        `).join("")}
      </div>
      <p class="financial-peace-note">ⓘ Valores baseados na receita de referência (${base}) · confiança ${escapeHtml(confidence)}. ${escapeHtml(peace.aviso || "")} ${escapeHtml(peace.mensagem || "")}</p>
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
      atencao: "Vulnerável / Atenção",
      bom: "Moderado / Em construção",
      excelente: "Excelente / Sólido",
    })[level] || "Atenção";
  }

  function financialHealthLevelIcon(level) {
    return ({
      critico: "🔴",
      atencao: "🟠",
      bom: "🟡",
      excelente: "🟢",
    })[level] || "•";
  }

  function financialHealthLevelClass(level) {
    return `level-${["critico", "atencao", "bom", "excelente"].includes(level) ? level : "atencao"}`;
  }

  function financialHealthScoreZone(score) {
    if (score < 300) {
      return {
        className: "level-critico",
        label: "Crítico",
        title: "Risco elevado",
        meaning: "Risco elevado de endividamento, ausência de reserva ou orçamento no vermelho. Pede ação imediata nos pilares mais fracos.",
      };
    }
    if (score < 500) {
      return {
        className: "level-atencao",
        label: "Vulnerável / Atenção",
        title: "Situação instável",
        meaning: "Há pouca margem de manobra; um imprevisto pode comprometer o mês. Priorize reserva, limites e redução de pressão financeira.",
      };
    }
    if (score < 750) {
      return {
        className: "level-bom",
        label: "Moderado / Em construção",
        title: "Orçamento sob controle",
        meaning: "A situação está equilibrada, com oportunidades claras para aumentar reserva, poupança ou consistência dos limites.",
      };
    }
    return {
      className: "level-excelente",
      label: "Excelente / Sólido",
      title: "Saúde financeira sólida",
      meaning: "Reserva, dívidas, limites e aportes indicam uma base financeira consistente para manter e acompanhar ao longo dos meses.",
    };
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
          <div class="empty-state compact">Nenhuma compra parcelada em aberto.</div>
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

  function renderCockpitCalendar() {
    if (!cockpitCalendarPanel) {
      return;
    }
    if (!state.cockpitCalendar) {
      if (state.cockpitCalendarError) {
        const message = state.cockpitCalendarError || "Falha ao carregar dados do calendário.";
        [overdueReceivablesList, overduePayablesList, maturity30DaysList, maturity60DaysList].forEach((container) => {
          if (container) {
            container.innerHTML = "";
            container.append(emptyState(message, true));
          }
        });
        return;
      }
      if (overdueReceivablesList) {
        overdueReceivablesList.innerHTML = "";
        overdueReceivablesList.append(emptyState("Carregando dados do calendário...", true));
      }
      if (overduePayablesList) {
        overduePayablesList.innerHTML = "";
        overduePayablesList.append(emptyState("Carregando dados do calendário...", true));
      }
      if (maturity30DaysList) {
        maturity30DaysList.innerHTML = "";
        maturity30DaysList.append(emptyState("Carregando dados do calendário...", true));
      }
      if (maturity60DaysList) {
        maturity60DaysList.innerHTML = "";
        maturity60DaysList.append(emptyState("Carregando dados do calendário...", true));
      }
      if (!state.cockpitCalendarLoading) {
        loadCockpitCalendar().catch((error) => {
          state.cockpitCalendarError = error.message;
          renderCockpitCalendar();
        });
      }
      return;
    }
    const payload = state.cockpitCalendar;
    renderCalendarCard(
      overdueReceivablesList,
      payload.overdue_receivables || [],
      "Nenhuma conta a receber atrasada.",
      "overdue_receivables_cents",
      (item) => renderOverdueItem(item, "receivable"),
    );
    renderCalendarCard(
      overduePayablesList,
      payload.overdue_payables || [],
      "Nenhuma conta a pagar atrasada.",
      "overdue_payables_cents",
      (item) => renderOverdueItem(item, "payable"),
    );
    renderCalendarCard(
      maturity30DaysList,
      payload.maturity_30_days || [],
      "Nenhum vencimento em 30 dias.",
      "maturity_30_days_cents",
      (item) => renderMaturityItem(item),
    );
    renderCalendarCard(
      maturity60DaysList,
      payload.maturity_60_days || [],
      "Nenhum vencimento em 60 dias.",
      "maturity_60_days_cents",
      (item) => renderMaturityItem(item),
    );
  }

  async function loadCockpitCalendar() {
    calendarRequestId += 1;
    const requestId = calendarRequestId;
    state.cockpitCalendarLoading = true;
    state.cockpitCalendarError = "";
    try {
      state.cockpitCalendar = await api("/api/cockpit/calendar");
    } finally {
      if (requestId !== calendarRequestId) {
        return;
      }
      state.cockpitCalendarLoading = false;
      renderCockpitCalendar();
    }
  }

  function renderCalendarCard(container, items, emptyMessage, totalsKey, itemRenderer) {
    if (!container) {
      return;
    }
    const payload = state.cockpitCalendar || {};
    const totals = buildTotalsByCurrency(payload, totalsKey);
    if (!items.length) {
      container.innerHTML = "";
      container.append(emptyState(emptyMessage, true));
      return;
    }
    container.innerHTML = `
      ${totals.size ? `<div class="calendar-card-totals">${[...totals.entries()].map(([currency, amount]) => `<span>${escapeHtml(currency)}: <strong>${formatMoney(amount, currency)}</strong></span>`).join(" ")}</div>` : ""}
      <div class="calendar-card-items">${items.map((item) => itemRenderer(item)).join("")}</div>
    `;
    container.querySelectorAll("[data-calendar-transaction-id]").forEach((button) => {
      button.addEventListener("click", () => {
        if (typeof onNavigateToTransaction === "function") {
          onNavigateToTransaction(button.dataset.calendarTransactionId);
        }
      });
    });
    container.querySelectorAll("[data-calendar-position-id]").forEach((button) => {
      button.addEventListener("click", () => onNavigateToPortfolio(button.dataset.calendarPositionId));
    });
  }

  function buildTotalsByCurrency(payload, totalsKey) {
    const totalsByCurrency = new Map();
    for (const item of payload.totals_by_currency || []) {
      const amount = Number(item[totalsKey] || 0);
      if (amount === 0) {
        continue;
      }
      totalsByCurrency.set(item.currency || "BRL", amount / 100);
    }
    return totalsByCurrency;
  }

  function renderOverdueItem(item, kind) {
    const label = kind === "receivable" ? "Receber" : "Pagar";
    const description = item.description || "Sem descrição";
    const detail = `${formatDate(item.date)} · ${escapeHtml(item.account_name || "Conta")} · ${escapeHtml(String(item.days_overdue))} dias de atraso`;
    return `
      <button class="calendar-item-row" type="button" data-calendar-transaction-id="${escapeHtml(String(item.id))}">
        <div>
          <strong>${escapeHtml(description)}</strong>
          <small>${escapeHtml(detail)}</small>
        </div>
        <div>
          <span>${escapeHtml(label)}</span>
          <strong>${formatMoney(Number(item.amount_cents || 0) / 100, item.currency || "BRL")}</strong>
        </div>
      </button>
    `;
  }

  function renderMaturityItem(item) {
    const description = item.asset_name || item.asset_identifier || "Ativo sem identificação";
    const detail = `${formatDate(item.maturity_date)} · ${escapeHtml(item.account_name || "Carteira")} · ${escapeHtml(String(item.days_to_maturity))} dias`;
    return `
      <button class="calendar-item-row" type="button" data-calendar-position-id="${escapeHtml(String(item.position_id))}">
        <div>
          <strong>${escapeHtml(description)}</strong>
          <small>${escapeHtml(detail)}</small>
        </div>
        <div>
          <span>Valor</span>
          <strong>${formatMoney(Number(item.current_value_cents || 0) / 100, item.currency || "BRL")}</strong>
        </div>
      </button>
    `;
  }
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
      const content = `
        <span><i style="background:${chartColor(index)}"></i>${escapeHtml(item.label)}</span>
        <strong>${formatMoney(item.total, "BRL")} · ${formatPercent(percent)}</strong>
      `;
      if (Array.isArray(item.items) && item.items.length > 0) {
        return `
          <button class="chart-row chart-row-button" type="button" data-chart-breakdown-index="${index}">
            ${content}
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
