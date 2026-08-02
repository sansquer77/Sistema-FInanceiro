// spec: tendencias-saude-financeira v1.2 — critérios 1, 2, 3, 4, 5, 6, 7, 10, 20, 21, 25, 26, 27 e 28
export function registerTrendsView({
  elements,
  api,
  formatMoney,
  formatPercent,
  escapeHtml,
  formatMonthLabel,
}) {
  const {
    trendsPanel,
    trendsContent,
    trendsMeta,
  } = elements;
  let trendsRequestId = 0;
  let currentMonth = null;
  let currentData = null;
  let loading = false;
  let error = "";

  function renderTrends(month, force = false) {
    if (!trendsContent || !trendsPanel) {
      return;
    }
    if (currentMonth !== month || force) {
      currentMonth = month;
      currentData = null;
      error = "";
      loadTrends(month);
    }
    render();
  }

  async function loadTrends(month) {
    const requestId = ++trendsRequestId;
    loading = true;
    error = "";
    render();
    try {
      const response = await api(`/api/financial-health-trends?month=${encodeURIComponent(month)}`);
      if (requestId !== trendsRequestId) {
        return;
      }
      currentData = response;
      loading = false;
      error = "";
    } catch (err) {
      if (requestId !== trendsRequestId) {
        return;
      }
      loading = false;
      error = err.message || "Não foi possível carregar as tendências.";
    }
    render();
  }

  function render() {
    if (!trendsContent) {
      return;
    }
    renderMeta();
    if (loading && !currentData) {
      trendsContent.innerHTML = '<div class="empty-state compact">Carregando tendências...</div>';
      return;
    }
    if (error && !currentData) {
      trendsContent.innerHTML = `<div class="empty-state compact">${escapeHtml(error)}</div>`;
      return;
    }
    if (!currentData) {
      trendsContent.innerHTML = '<div class="empty-state compact">Selecione um mês para ver as tendências.</div>';
      return;
    }
    trendsContent.innerHTML = `
      ${renderSummaryCard()}
      ${renderSeriesChart()}
      <div class="trends-grid">
        ${renderBudgetActualTable()}
        ${renderFindings()}
      </div>
    `;
  }

  function renderMeta() {
    if (!trendsMeta) {
      return;
    }
    if (!currentData) {
      trendsMeta.innerHTML = "";
      return;
    }
    const confidenceLabel = {
      alta: "alta",
      intermediaria: "intermediária",
      baixa: "baixa",
    }[currentData.confianca] || currentData.confianca || "indisponível";
    const warning = currentData.multi_currency_warning
      ? `<span class="trends-warning">${escapeHtml(currentData.multi_currency_warning)}</span>`
      : "";
    trendsMeta.innerHTML = `
      <span>Mês de referência: <strong>${escapeHtml(formatMonthLabel(currentData.month))}</strong></span>
      <span>Confiança: <strong>${escapeHtml(confidenceLabel)}</strong></span>
      <span>Histórico: <strong>${Number(currentData.historico_meses_disponiveis || 0).toLocaleString("pt-BR")} mês(es)</strong></span>
      ${warning}
    `;
  }

  function renderSummaryCard() {
    const income = Number(currentData.receitas_mes_cents || 0);
    const expense = Number(currentData.despesas_mes_cents || 0);
    const balance = Number(currentData.saldo_mes_cents || 0);
    const baseIncome = Number(currentData.receitas_base_comparacao_cents || 0);
    const baseExpense = Number(currentData.despesas_base_comparacao_cents || 0);
    return `
      <section class="trends-summary">
        <article class="trends-summary-item income">
          <span>Receitas</span>
          <strong>${formatMoney(income / 100, "BRL")}</strong>
          <small>${baseIncome > 0 ? `base: ${formatMoney(baseIncome / 100, "BRL")}` : "&nbsp;"}</small>
        </article>
        <article class="trends-summary-item expense">
          <span>Despesas</span>
          <strong>${formatMoney(expense / 100, "BRL")}</strong>
          <small>${baseExpense > 0 ? `base: ${formatMoney(baseExpense / 100, "BRL")}` : "&nbsp;"}</small>
        </article>
        <article class="trends-summary-item balance">
          <span>Saldo</span>
          <strong class="${balance < 0 ? "danger-text" : ""}">${formatMoney(balance / 100, "BRL")}</strong>
          <small>&nbsp;</small>
        </article>
      </section>
    `;
  }

  function renderSeriesChart() {
    const series = currentData.serie_mensal || [];
    const months = series.map((item) => item.month);
    if (months.length === 0) {
      return "";
    }
    const incomes = series.map((item) => Number(item.income_cents || 0));
    const expenses = series.map((item) => Number(item.expense_cents || 0));
    const balances = series.map((item) => Number(item.balance_cents || 0));
    const maxAbs = Math.max(
      1,
      ...incomes.map((v) => Math.abs(v)),
      ...expenses.map((v) => Math.abs(v)),
      ...balances.map((v) => Math.abs(v)),
    );
    const width = 700;
    const height = 240;
    const padding = { top: 20, right: 16, bottom: 48, left: 56 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const stepX = chartWidth / Math.max(1, months.length - 1);
    const pointsFor = (values) => values.map((value, index) => {
      const x = padding.left + index * stepX;
      const y = padding.top + chartHeight - ((value / maxAbs) * (chartHeight / 2) + chartHeight / 2);
      return `${x},${y}`;
    }).join(" ");
    const linePath = (values) => `<polyline fill="none" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${pointsFor(values)}" />`;
    const yTicks = [-maxAbs, -maxAbs / 2, 0, maxAbs / 2, maxAbs];
    const yTickLabels = (value) => formatMoney(Math.abs(value) / 100, "BRL");
    return `
      <section class="trends-chart-section">
        <h3>Evolução mensal</h3>
        <div class="trends-chart">
          <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Gráfico de evolução de receitas, despesas e saldo">
            <g class="trends-grid-lines">
              ${yTicks.map((value) => {
                const y = padding.top + chartHeight - ((value / maxAbs) * (chartHeight / 2) + chartHeight / 2);
                return `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="currentColor" stroke-opacity="0.15" />`;
              }).join("")}
            </g>
            <g class="trends-axis-y">
              ${yTicks.map((value) => {
                const y = padding.top + chartHeight - ((value / maxAbs) * (chartHeight / 2) + chartHeight / 2);
                return `<text x="${padding.left - 8}" y="${y + 4}" text-anchor="end" font-size="10">${escapeHtml(yTickLabels(value))}</text>`;
              }).join("")}
            </g>
            <g class="trends-axis-x">
              ${months.map((month, index) => {
                const x = padding.left + index * stepX;
                const label = month.slice(5, 7) + "/" + month.slice(2, 4);
                return `<text x="${x}" y="${height - padding.bottom + 20}" text-anchor="${index === 0 ? "start" : index === months.length - 1 ? "end" : "middle"}" font-size="10">${escapeHtml(label)}</text>`;
              }).join("")}
            </g>
            <g class="trends-series income">${linePath(incomes)}</g>
            <g class="trends-series expense">${linePath(expenses)}</g>
            <g class="trends-series balance">${linePath(balances)}</g>
          </svg>
          <div class="trends-chart-legend">
            <span class="income"><i></i> Receitas</span>
            <span class="expense"><i></i> Despesas</span>
            <span class="balance"><i></i> Saldo</span>
          </div>
        </div>
      </section>
    `;
  }

  function renderBudgetActualTable() {
    const rows = currentData.orcamento_realizado || [];
    if (rows.length === 0) {
      return `
        <section class="trends-budget-section">
          <h3>Budget x Realizado</h3>
          <div class="empty-state compact">Nenhum limite de gasto configurado para este mês.</div>
        </section>
      `;
    }
    return `
      <section class="trends-budget-section">
        <h3>Budget x Realizado</h3>
        <div class="trends-budget-table" role="table" aria-label="Budget x Realizado">
          <div class="trends-budget-head" role="row">
            <span role="columnheader">Categoria</span>
            <span role="columnheader">Limite</span>
            <span role="columnheader">Realizado</span>
            <span role="columnheader">%</span>
            <span role="columnheader">Estado</span>
          </div>
          ${rows.map((row) => {
            const label = row.subcategory_name ? `${escapeHtml(row.category_name)} › ${escapeHtml(row.subcategory_name)}` : escapeHtml(row.category_name);
            const used = Number(row.percentual_usado || 0);
            const stateClass = row.estado === "Acima do limite" ? "danger" : row.estado === "Atenção" ? "warning" : "success";
            return `
              <div class="trends-budget-row ${stateClass}" role="row">
                <span role="cell">${label}</span>
                <span role="cell">${formatMoney(Number(row.limite_cents || 0) / 100, "BRL")}</span>
                <span role="cell">${formatMoney(Number(row.realizado_cents || 0) / 100, "BRL")}</span>
                <span role="cell">${formatPercent(used / 100)}</span>
                <span role="cell" class="trends-state ${stateClass}">${escapeHtml(row.estado)}</span>
              </div>
            `;
          }).join("")}
        </div>
      </section>
    `;
  }

  function renderFindings() {
    const findings = currentData.achados || [];
    if (findings.length === 0) {
      return `
        <section class="trends-findings-section">
          <h3>Tendências e achados</h3>
          <div class="empty-state compact">Nenhum achado para o mês selecionado.</div>
        </section>
      `;
    }
    return `
      <section class="trends-findings-section">
        <h3>Tendências e achados</h3>
        <div class="trends-findings-list">
          ${findings.map((finding) => {
            const severityClass = finding.severidade === "atencao" ? "warning" : "info";
            const value = Number(finding.valor_cents || 0);
            return `
              <article class="trends-finding ${severityClass}">
                <header>
                  <strong>${escapeHtml(finding.titulo)}</strong>
                  ${value ? `<span>${formatMoney(value / 100, "BRL")}</span>` : ""}
                </header>
                <p>${escapeHtml(finding.descricao)}</p>
              </article>
            `;
          }).join("")}
        </div>
        ${currentData.resumo_local ? `<p class="trends-local-summary">${escapeHtml(currentData.resumo_local)}</p>` : ""}
      </section>
    `;
  }

  return {
    renderTrends,
  };
}
