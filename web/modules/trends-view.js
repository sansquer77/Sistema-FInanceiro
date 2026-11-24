// spec: tendencias-saude-financeira v2.26 — critérios 1, 2, 3, 4, 5, 6, 7, 10, 12, 13, 14, 16, 17, 20, 21, 25, 26, 27, 28, 32, 33 e 34
import { stateMarkup } from "./dom-utils.js";
import { chartToken, renderChart } from "./chart-adapter.js";
import { runLocalInference } from "./webllm-client.js?v=182";
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
    cockpitTrendSummaryContent,
    monthlyBudgetSummary,
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

  function renderCockpitSummary(month, force = false) {
    if (!cockpitTrendSummaryContent && !monthlyBudgetSummary) {
      return;
    }
    if (currentMonth !== month || force) {
      currentMonth = month;
      currentData = null;
      error = "";
      loadTrends(month);
    }
    renderCompactSummary();
  }

  async function loadTrends(month) {
    const requestId = ++trendsRequestId;
    loading = true;
    trendsContent.setAttribute("aria-busy", "true");
    error = "";
    render();
    try {
      const response = await api(`/api/financial-health-trends?month=${encodeURIComponent(month)}`);
      if (requestId !== trendsRequestId) {
        return;
      }
      currentData = response;
      if ((currentData.ia_execution?.order || []).some((source) => source !== "deterministica")) {
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
    if (requestId === trendsRequestId) trendsContent.setAttribute("aria-busy", "false");
    render();
    renderCompactSummary();
  }

  async function loadAISummary(requestId, month) {
    const order = currentData.ia_execution?.order || ["deterministica"];
    try {
      for (const source of order) {
        if (source === "deterministica") break;
        if (source === "local") {
          try {
            const prepared = await api("/api/financial-health-trends/prepare-local-summary", {
              method: "POST", body: { month },
            });
            if (!prepared.available) continue;
            const output = await runLocalInference(prepared.messages, prepared, () => {});
            if (output?.trim()) {
              currentData.ia_usada = true;
              currentData.ia_resumo = output.trim();
              currentData.ia_origem = "local";
              return;
            }
          } catch (localError) {
            currentData.ia_local_error = localError.message || "A IA local não está disponível neste dispositivo.";
            continue;
          }
        }
        if (source === "remota") {
          const aiResponse = await api("/api/financial-health-trends/ai-summary", {
            method: "POST", body: { month },
          });
          if (requestId !== trendsRequestId) return;
          if (aiResponse.ia_usada && aiResponse.resumo_ia) {
            currentData.ia_usada = true;
            currentData.ia_resumo = aiResponse.resumo_ia;
            currentData.ia_origem = aiResponse.ia_origem || "remota";
            return;
          }
        }
      }
      currentData.ia_usada = false;
      currentData.ia_resumo = null;
      currentData.ia_origem = "deterministica";
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
      trendsContent.innerHTML = stateMarkup("Analisando receitas, despesas e limites do período.", { kind: "loading" });
      renderCompactSummary();
      return;
    }
    if (error && !currentData) {
      trendsContent.innerHTML = stateMarkup(error, { kind: "error" });
      renderCompactSummary();
      return;
    }
    if (!currentData) {
      trendsContent.innerHTML = stateMarkup("Selecione um mês para visualizar tendências e comparações.", { kind: "info" });
      renderCompactSummary();
      return;
    }
    trendsContent.innerHTML = `
      ${renderSummaryCard()}
      ${renderSeriesChart()}
      ${renderFindings()}
      ${renderBudgetActualTable()}
      ${renderConfidenceNotes()}
    `;
    renderTrendsApexChart();
    renderCompactSummary();
  }

  function renderTrendsApexChart() {
    const chartElement = trendsContent.querySelector(".trends-apex-chart");
    if (!chartElement) return;
    const rows = filterMonthlySeries(currentData.serie_mensal || []);
    renderChart(chartElement, monthlyChartOptions(rows, 260));
  }

  function renderCompactSummary() {
    if (!cockpitTrendSummaryContent && !monthlyBudgetSummary) {
      return;
    }
    if (loading && !currentData) {
      cockpitTrendSummaryContent && (cockpitTrendSummaryContent.innerHTML = stateMarkup("Analisando a evolução mensal.", { kind: "loading" }));
      monthlyBudgetSummary && (monthlyBudgetSummary.innerHTML = stateMarkup("Calculando limites e realizado.", { kind: "loading" }));
      return;
    }
    if (error && !currentData) {
      cockpitTrendSummaryContent && (cockpitTrendSummaryContent.innerHTML = stateMarkup(error, { kind: "error" }));
      monthlyBudgetSummary && (monthlyBudgetSummary.innerHTML = stateMarkup(error, { kind: "error" }));
      return;
    }
    if (!currentData) {
      cockpitTrendSummaryContent && (cockpitTrendSummaryContent.innerHTML = stateMarkup("Selecione um mês para visualizar a evolução.", { kind: "info" }));
      monthlyBudgetSummary && (monthlyBudgetSummary.innerHTML = stateMarkup("Selecione um mês para comparar limites e realizado.", { kind: "info" }));
      return;
    }
    // spec: frontend/frontend-modularizacao v4.40 — critérios 2 e 3
    const rows = filterMonthlySeries(currentData.serie_mensal || [], "6");
    const insight = monthlyChartInsight(rows);
    if (cockpitTrendSummaryContent) {
      cockpitTrendSummaryContent.innerHTML = rows.length === 0
        ? stateMarkup("Sem movimento suficiente para formar uma evolução mensal.", { kind: "empty" })
        : `
          <div class="cockpit-trend-meta"><span>Últimos seis meses com movimento</span><strong>${escapeHtml(formatMonthLabel(currentData.month))}</strong></div>
          <div class="trends-chart cockpit-trends-chart">
            <div class="trends-apex-chart cockpit-trends-apex-chart" role="img" aria-label="Evolução compacta de receitas, despesas e saldo líquido"></div>
            <div class="trends-chart-legend">
              <span class="income"><i></i> Receitas</span>
              <span class="expense"><i></i> Despesas</span>
              <span class="balance"><i></i> Saldo líquido</span>
            </div>
            <p class="trends-chart-insight">${escapeHtml(insight)}</p>
          </div>
        `;
      const chartElement = cockpitTrendSummaryContent.querySelector(".cockpit-trends-apex-chart");
      if (chartElement && rows.length > 0) {
        renderChart(chartElement, monthlyChartOptions(rows, 190));
      }
    }
    if (monthlyBudgetSummary) {
      monthlyBudgetSummary.innerHTML = renderBudgetSummary(currentData.orcamento_realizado || []);
    }
  }

  function monthlyChartOptions(rows, height) {
    return {
      chart: { type: "line", height, stacked: false, toolbar: { show: false }, zoom: { enabled: false } },
      series: [
        { name: "Receitas", type: "column", data: rows.map((row) => Number(row.income_cents || 0)) },
        { name: "Despesas", type: "column", data: rows.map((row) => Number(row.expense_cents || 0)) },
        { name: "Saldo líquido", type: "line", data: rows.map((row) => Number(row.balance_cents || 0)) },
      ],
      colors: [
        chartToken("--positive", "#36b37e"),
        chartToken("--danger", "#ff7452"),
        chartToken("--accent", "#5f7fff"),
      ],
      stroke: { width: [0, 0, 3], curve: "smooth" },
      fill: { opacity: [0.72, 0.72, 1] },
      markers: { size: 3, strokeWidth: 2, hover: { size: 5 } },
      plotOptions: { bar: { borderRadius: 5, columnWidth: "48%" } },
      xaxis: { categories: rows.map((row) => row.month.slice(5, 7) + "/" + row.month.slice(2, 4)) },
      yaxis: { labels: { formatter: formatCompactSignedMoney } },
      tooltip: { y: { formatter: formatCompactSignedMoney } },
      legend: { show: false },
      grid: { borderColor: chartToken("--line", "#d9deea"), strokeDashArray: 4, padding: { left: 4, right: 8, top: 0, bottom: 0 } },
    };
  }

  function renderBudgetSummary(rows) {
    if (!rows.length) {
      return stateMarkup("Cadastre limites de gasto para acompanhar o orçamento do mês.", { kind: "empty" });
    }
    const ordered = [...rows].sort((left, right) => Number(right.percentual_usado || 0) - Number(left.percentual_usado || 0));
    const totalLimit = ordered.reduce((sum, row) => sum + Number(row.limite_cents || 0), 0);
    const totalUsed = ordered.reduce((sum, row) => sum + Number(row.realizado_cents || 0), 0);
    const totalPercent = totalLimit > 0 ? totalUsed / totalLimit : 0;
    const visibleRows = ordered.slice(0, 4);
    return `
      <div class="budget-summary-total">
        <div><span>Realizado</span><strong>${formatMoney(totalUsed / 100, "BRL")}</strong></div>
        <div><span>Limite total</span><strong>${formatMoney(totalLimit / 100, "BRL")}</strong></div>
        <b class="budget-summary-percent ${totalPercent > 1 ? "over" : totalPercent >= .8 ? "warning" : "success"}">${formatPercent(totalPercent)}</b>
      </div>
      <div class="budget-summary-list">
        ${visibleRows.map((row) => {
          const used = Number(row.percentual_usado || 0);
          const stateClass = row.estado === "Acima do limite" ? "over" : row.estado === "Atenção" ? "warning" : "success";
          const label = row.subcategory_name ? `${escapeHtml(row.category_name)} › ${escapeHtml(row.subcategory_name)}` : escapeHtml(row.category_name);
          return `
            <div class="budget-summary-row ${stateClass}">
              <div><span>${label}</span><strong>${formatPercent(used / 100)}</strong></div>
              <div class="budget-summary-bar" aria-hidden="true"><i style="width:${Math.min(100, Math.max(0, used)).toFixed(1)}%"></i></div>
              <small>${formatMoney(Number(row.realizado_cents || 0) / 100, "BRL")} de ${formatMoney(Number(row.limite_cents || 0) / 100, "BRL")}</small>
            </div>
          `;
        }).join("")}
      </div>
      ${rows.length > visibleRows.length ? `<small class="budget-summary-more">${rows.length - visibleRows.length} categorias adicionais em Tendências.</small>` : ""}
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
          <span class="trends-summary-label-with-info">
            Despesas
            <button
              class="trends-info-button"
              type="button"
              aria-label="Fonte do valor de despesas"
              title="Despesas analíticas do mês em BRL: despesas de contas pela data do lançamento + lançamentos de cartão pela competência da fatura. Pagamentos de fatura são excluídos para evitar duplicidade."
            >i</button>
          </span>
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
    const filteredSeries = filterMonthlySeries(currentData.serie_mensal || []);
    if (filteredSeries.length === 0) {
      return "";
    }
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
          <div class="trends-apex-chart" role="img" aria-label="Gráfico de evolução de receitas, despesas e saldo"></div>
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

  function filterMonthlySeries(series, period = chartPeriod) {
    const normalized = Array.isArray(series) ? series : [];
    if (period === "active") {
      const activeMonths = normalized.filter((item) => (
        Number(item.income_cents || 0) !== 0
        || Number(item.expense_cents || 0) !== 0
        || Number(item.balance_cents || 0) !== 0
      ));
      return activeMonths.length > 0 ? activeMonths : normalized;
    }
    const count = Number(period || 12);
    return normalized.slice(Math.max(0, normalized.length - count));
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
          ${stateMarkup("Cadastre limites de gasto para comparar orçamento e realizado.", { kind: "empty" })}
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
    const textOnlyTypes = new Set(["confianca", "receita", "despesa", "assinatura_servico", "oportunidade_caixa"]);
    const cardFindings = findings.filter((finding) => !textOnlyTypes.has(finding.tipo));
    const hasIaSummary = currentData.ia_usada && currentData.ia_resumo;
    const summaryText = hasIaSummary ? currentData.ia_resumo : currentData.resumo_local;
    const aiSummaryMarker = hasIaSummary
      ? `<span class="trends-ai-summary-marker" title="Resumo reescrito por IA ${escapeHtml(currentData.ia_origem || "")}" aria-label="Resumo reescrito por IA">✨ IA</span>`
      : "";
    const sourceNotice = hasIaSummary
      ? `<small class="trends-ai-notice">${currentData.ia_local_error ? `${escapeHtml(currentData.ia_local_error)} Foi usado o fallback remoto. ` : ""}Resumo gerado com IA ${escapeHtml(currentData.ia_origem === "local" ? "local" : "remota")}.</small>`
      : `<small class="trends-ai-notice">Resumo determinístico local.</small>`;
    if (cardFindings.length === 0 && !summaryText) {
      return `
        <section class="trends-findings-section">
          <h3>Tendências e achados</h3>
          ${stateMarkup("Selecione outro mês ou aguarde novos dados para gerar achados.", { kind: "empty" })}
        </section>
      `;
    }
    return `
      <section class="trends-findings-section">
        <h3 class="trends-findings-title">Tendências e achados ${aiSummaryMarker}</h3>
        ${summaryText ? renderSummaryText(summaryText) : ""}
        ${sourceNotice}
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
    renderCockpitSummary,
  };
}
