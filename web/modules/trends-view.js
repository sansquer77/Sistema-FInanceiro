// spec: tendencias-saude-financeira v2.14 — critérios 1, 2, 3, 4, 5, 6, 7, 10, 12, 13, 14, 16, 17, 20, 21, 25, 26, 27, 28, 32, 33 e 34
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
  let chartPeriod = "active";

  trendsContent?.addEventListener("click", (event) => {
    const button = event.target.closest("[data-trends-period]");
    if (!button) {
      return;
    }
    chartPeriod = button.dataset.trendsPeriod || "active";
    render();
  });

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
      if (currentData.ia_ativa) {
        await loadAISummary(requestId, month);
      } else {
        currentData.ia_usada = false;
        currentData.ia_resumo = null;
      }
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

  async function loadAISummary(requestId, month) {
    try {
      const aiResponse = await api("/api/financial-health-trends/ai-summary", {
        method: "POST",
        body: { month },
      });
      if (requestId !== trendsRequestId) {
        return;
      }
      currentData.ia_usada = aiResponse.ia_usada === true;
      currentData.ia_resumo = aiResponse.resumo_ia || null;
      if (aiResponse.resumo_local && !currentData.resumo_local) {
        currentData.resumo_local = aiResponse.resumo_local;
      }
    } catch (err) {
      if (requestId !== trendsRequestId) {
        return;
      }
      currentData.ia_usada = false;
      currentData.ia_resumo = null;
      currentData.ia_erro = err.message || "IA indisponível";
    }
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
      ${renderFindings()}
      ${renderBudgetActualTable()}
      ${renderConfidenceNotes()}
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
    const aiBadge = currentData.ia_ativa
      ? `<span class="trends-ai-badge">IA ${currentData.ia_usada ? "ativa" : "fallback"}</span>`
      : "";
    trendsMeta.innerHTML = `
      <span>Mês: <strong>${escapeHtml(formatMonthLabel(currentData.month))}</strong></span>
      <span>Confiança: <strong>${escapeHtml(confidenceLabel)}</strong></span>
      ${aiBadge}
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
    const filteredSeries = filterMonthlySeries(series);
    const months = filteredSeries.map((item) => item.month);
    if (filteredSeries.length === 0) {
      return "";
    }
    const incomes = filteredSeries.map((item) => Number(item.income_cents || 0));
    const expenses = filteredSeries.map((item) => Number(item.expense_cents || 0));
    const balances = filteredSeries.map((item) => Number(item.balance_cents || 0));
    const rawMaxValue = Math.max(
      1,
      ...incomes,
      ...expenses,
      ...balances,
    );
    const rawMinValue = Math.min(0, ...balances);
    const maxValue = niceAxisMax(rawMaxValue);
    const minValue = rawMinValue < 0 ? niceAxisMin(rawMinValue, maxValue) : 0;
    const range = Math.max(1, maxValue - minValue);
    const width = 700;
    const height = 260;
    const padding = { top: 24, right: 16, bottom: 56, left: 72 };
    const chartWidth = width - padding.left - padding.right;
    const chartHeight = height - padding.top - padding.bottom;
    const stepX = chartWidth / Math.max(1, months.length);
    const groupWidth = Math.max(26, Math.min(58, stepX * 0.58));
    const barGap = Math.max(3, groupWidth * 0.12);
    const barWidth = (groupWidth - barGap) / 2;
    const xCenter = (index) => padding.left + stepX * index + stepX / 2;
    const yFor = (value) => padding.top + chartHeight - ((value - minValue) / range) * chartHeight;
    const zeroY = yFor(0);
    const linePoints = balances.map((value, index) => `${xCenter(index)},${yFor(value)}`).join(" ");
    const yTicks = buildTicks(minValue, maxValue);
    const insight = monthlyChartInsight(filteredSeries);
    return `
      <section class="trends-chart-section">
        <div class="trends-chart-heading">
          <h3>Evolução mensal</h3>
          <div class="trends-chart-periods" aria-label="Período do gráfico">
            ${renderPeriodButton("active", "Com movimento")}
            ${renderPeriodButton("3", "3 meses")}
            ${renderPeriodButton("6", "6 meses")}
            ${renderPeriodButton("12", "12 meses")}
          </div>
        </div>
        <div class="trends-chart mixed">
          <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Gráfico de evolução de receitas, despesas e saldo">
            <g class="trends-grid-lines">
              ${yTicks.map((value) => {
                const y = yFor(value);
                return `<line x1="${padding.left}" y1="${y}" x2="${width - padding.right}" y2="${y}" stroke="currentColor" stroke-opacity="0.15" />`;
              }).join("")}
            </g>
            <g class="trends-axis-y">
              ${yTicks.map((value) => {
                const y = yFor(value);
                return `<text x="${padding.left - 8}" y="${y + 3}" text-anchor="end" font-size="8.5">${escapeHtml(formatCompactSignedMoney(value))}</text>`;
              }).join("")}
            </g>
            <g class="trends-axis-x">
              ${months.map((month, index) => {
                const x = xCenter(index);
                const label = month.slice(5, 7) + "/" + month.slice(2, 4);
                return `<text x="${x}" y="${height - padding.bottom + 26}" text-anchor="middle" font-size="10">${escapeHtml(label)}</text>`;
              }).join("")}
            </g>
            <line class="trends-zero-line" x1="${padding.left}" y1="${zeroY}" x2="${width - padding.right}" y2="${zeroY}" />
            <g class="trends-month-shading">
              ${filteredSeries.map((item, index) => {
                const income = Number(item.income_cents || 0);
                const expense = Number(item.expense_cents || 0);
                const x = padding.left + stepX * index + stepX * 0.08;
                return `<rect class="${income >= expense ? "surplus" : "deficit"}" x="${x}" y="${padding.top}" width="${stepX * 0.84}" height="${chartHeight}" rx="8" />`;
              }).join("")}
            </g>
            <g class="trends-bars">
              ${filteredSeries.map((item, index) => {
                const income = Number(item.income_cents || 0);
                const expense = Number(item.expense_cents || 0);
                const balance = Number(item.balance_cents || 0);
                const center = xCenter(index);
                const incomeHeight = Math.max(0, zeroY - yFor(income));
                const expenseHeight = Math.max(0, zeroY - yFor(expense));
                const incomeX = center - groupWidth / 2;
                const expenseX = incomeX + barWidth + barGap;
                const tooltip = monthlyTooltip(item, income, expense, balance);
                return `
                  <g class="trends-month-group">
                    <title>${escapeHtml(tooltip)}</title>
                    <rect class="income" x="${incomeX}" y="${zeroY - incomeHeight}" width="${barWidth}" height="${incomeHeight}" rx="3" />
                    <rect class="expense" x="${expenseX}" y="${zeroY - expenseHeight}" width="${barWidth}" height="${expenseHeight}" rx="3" />
                  </g>
                `;
              }).join("")}
            </g>
            <g class="trends-balance-line">
              <polyline fill="none" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" points="${linePoints}" />
              ${balances.map((value, index) => {
                const tooltip = monthlyTooltip(filteredSeries[index], incomes[index], expenses[index], value);
                return `<circle cx="${xCenter(index)}" cy="${yFor(value)}" r="4"><title>${escapeHtml(tooltip)}</title></circle>`;
              }).join("")}
            </g>
          </svg>
          <div class="trends-chart-legend">
            <span class="income"><i></i> Receitas</span>
            <span class="expense"><i></i> Despesas</span>
            <span class="balance"><i></i> Saldo líquido</span>
          </div>
          <p class="trends-chart-insight">${escapeHtml(insight)}</p>
        </div>
      </section>
    `;
  }

  function renderPeriodButton(value, label) {
    const active = chartPeriod === value;
    return `<button class="${active ? "active" : ""}" type="button" data-trends-period="${escapeHtml(value)}" aria-pressed="${active ? "true" : "false"}">${escapeHtml(label)}</button>`;
  }

  function filterMonthlySeries(series) {
    const normalized = Array.isArray(series) ? series : [];
    if (chartPeriod === "active") {
      const activeMonths = normalized.filter((item) => (
        Number(item.income_cents || 0) !== 0
        || Number(item.expense_cents || 0) !== 0
        || Number(item.balance_cents || 0) !== 0
      ));
      return activeMonths.length > 0 ? activeMonths : normalized;
    }
    const count = Number(chartPeriod || 12);
    return normalized.slice(Math.max(0, normalized.length - count));
  }

  function buildTicks(minValue, maxValue) {
    if (minValue >= 0) {
      return [maxValue, maxValue * 0.5, 0];
    }
    return [maxValue, maxValue * 0.5, 0, minValue];
  }

  function niceAxisMax(value) {
    return niceCeil(Math.max(1, value) * 1.08);
  }

  function niceAxisMin(value, maxValue) {
    const min = -niceCeil(Math.abs(value) * 1.25);
    const minimumVisibleNegative = -Math.max(niceCeil(maxValue * 0.12), niceCeil(Math.abs(value) * 1.25));
    return Math.min(min, minimumVisibleNegative);
  }

  function niceCeil(value) {
    if (value <= 0) {
      return 0;
    }
    const exponent = Math.floor(Math.log10(value));
    const base = 10 ** exponent;
    const normalized = value / base;
    const step = normalized <= 1 ? 1 : normalized <= 2 ? 2 : normalized <= 5 ? 5 : 10;
    return step * base;
  }

  function formatSignedMoney(cents) {
    const value = Number(cents || 0);
    if (value < 0) {
      return `-${formatMoney(Math.abs(value) / 100, "BRL")}`;
    }
    return formatMoney(value / 100, "BRL");
  }

  function formatCompactSignedMoney(cents) {
    const value = Number(cents || 0);
    if (value === 0) {
      return "R$ 0";
    }
    const sign = value < 0 ? "-" : "";
    const abs = Math.abs(value);
    if (abs >= 1_000_000_00) {
      return `${sign}R$ ${(abs / 100_000_000).toLocaleString("pt-BR", { maximumFractionDigits: 1 })} mi`;
    }
    if (abs >= 1_000_00) {
      return `${sign}R$ ${(abs / 100_000).toLocaleString("pt-BR", { maximumFractionDigits: 0 })} mil`;
    }
    return `${sign}${formatMoney(abs / 100, "BRL")}`;
  }

  function monthlyTooltip(item, income, expense, balance) {
    const monthLabel = formatMonthLabel(item.month);
    const margin = income > 0 ? (balance / income) : 0;
    const marginText = income > 0 ? ` (${formatPercent(margin)})` : "";
    return [
      `📅 ${monthLabel}`,
      `🟢 Receitas: ${formatMoney(income / 100, "BRL")}`,
      `🔴 Despesas: ${formatMoney(expense / 100, "BRL")}`,
      `🔵 Saldo: ${formatSignedMoney(balance)}${marginText}`,
    ].join("\n");
  }

  function monthlyChartInsight(series) {
    if (!Array.isArray(series) || series.length === 0) {
      return "Sem meses com movimento suficiente para destacar uma tendência.";
    }
    const best = series.reduce((selected, item) => Number(item.balance_cents || 0) > Number(selected.balance_cents || 0) ? item : selected, series[0]);
    const worst = series.reduce((selected, item) => Number(item.balance_cents || 0) < Number(selected.balance_cents || 0) ? item : selected, series[0]);
    const last = series[series.length - 1];
    const lastBalance = Number(last.balance_cents || 0);
    const previous = series.length > 1 ? series[series.length - 2] : null;
    const previousBalance = previous ? Number(previous.balance_cents || 0) : 0;
    const bestMonth = formatMonthLabel(best.month);
    const worstMonth = formatMonthLabel(worst.month);
    if (lastBalance < 0) {
      return `${formatMonthLabel(last.month)} fechou em déficit de ${formatSignedMoney(lastBalance)}; o melhor saldo do período foi em ${bestMonth}.`;
    }
    if (previous && lastBalance < previousBalance) {
      return `${formatMonthLabel(last.month)} ainda fechou positivo (${formatSignedMoney(lastBalance)}), mas perdeu força frente ao mês anterior.`;
    }
    if (Number(best.balance_cents || 0) > 0) {
      return `${bestMonth} teve o melhor saldo do período (${formatSignedMoney(Number(best.balance_cents || 0))}); o ponto mais pressionado foi ${worstMonth}.`;
    }
    return `O período não teve superávit; ${worstMonth} concentrou o maior déficit (${formatSignedMoney(Number(worst.balance_cents || 0))}).`;
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
            const stateClass = row.estado === "Acima do limite" ? "over" : row.estado === "Atenção" ? "warning" : "success";
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
    const textOnlyTypes = new Set(["confianca", "receita", "despesa", "assinatura_servico"]);
    const cardFindings = findings.filter((finding) => !textOnlyTypes.has(finding.tipo));
    const hasIaSummary = currentData.ia_usada && currentData.ia_resumo;
    const summaryText = hasIaSummary ? currentData.ia_resumo : currentData.resumo_local;
    const aiSummaryMarker = hasIaSummary
      ? `<span class="trends-ai-summary-marker" title="Resumo reescrito por IA" aria-label="Resumo reescrito por IA">✨ IA</span>`
      : "";
    const aiNotice = currentData.ia_ativa && !currentData.ia_usada
      ? `<small class="trends-ai-notice">Resumo local — IA não respondeu ou está desligada.</small>`
      : "";
    if (cardFindings.length === 0 && !summaryText) {
      return `
        <section class="trends-findings-section">
          <h3>Tendências e achados</h3>
          <div class="empty-state compact">Nenhum achado para o mês selecionado.</div>
        </section>
      `;
    }
    return `
      <section class="trends-findings-section">
        <h3 class="trends-findings-title">Tendências e achados ${aiSummaryMarker}</h3>
        ${summaryText ? renderSummaryText(summaryText) : ""}
        ${aiNotice}
        ${cardFindings.length ? `
          <div class="trends-findings-list">
            ${cardFindings.map((finding) => {
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
        ` : ""}
      </section>
    `;
  }

  function renderConfidenceNotes() {
    const confidenceFindings = (currentData.achados || []).filter((finding) => finding.tipo === "confianca");
    if (confidenceFindings.length === 0) {
      return "";
    }
    return `
      <section class="trends-confidence-section">
        ${confidenceFindings.map((finding) => `
          <article class="trends-confidence-card">
            <h3>${escapeHtml(finding.titulo)}</h3>
            <p>${escapeHtml(finding.descricao)}</p>
          </article>
        `).join("")}
      </section>
    `;
  }

  function renderSummaryText(text) {
    const sentences = splitSummarySentences(text);
    if (sentences.length === 0) {
      return "";
    }
    const intro = sentences[0];
    const items = sentences.slice(1);
    return `
      <div class="trends-summary-text">
        <p>${escapeHtml(intro)}</p>
        ${items.length ? `
          <ul>
            ${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
          </ul>
        ` : ""}
      </div>
    `;
  }

  function splitSummarySentences(text) {
    return String(text || "")
      .replace(/\s+/g, " ")
      .split(/(?<=\.)\s+/)
      .map((item) => item.trim())
      .filter(Boolean);
  }

  return {
    renderTrends,
  };
}
