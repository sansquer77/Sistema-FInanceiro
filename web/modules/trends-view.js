// spec: tendencias-saude-financeira v2.34 — critérios 1, 2, 3, 4, 5, 6, 7, 10, 12, 13, 14, 16, 17, 20, 21, 25, 26, 27, 28, 32, 33, 34 e 74
import { stateMarkup } from "./dom-utils.js";
import { chartToken, renderChart } from "./chart-adapter.js";
import { runLocalInference } from "./webllm-client.js?v=185";
import { createSubscriptionsFlyover } from "./subscriptions-flyover.js?v=2";

export function splitSummarySentences(text) {
  const normalized = String(text || "")
    .replace(/\s+/g, " ")
    .trim();
  if (!normalized) return [];

  // Modelos podem devolver uma lista numerada apesar do prompt pedir frases.
  // O marcador deve permanecer unido ao item, em vez de virar uma frase isolada.
  const markers = [...normalized.matchAll(/(?:^|\s)\d+\\?\.\s+/g)];
  if (markers.length >= 2) {
    const items = markers.map((marker, index) => {
      const start = marker.index + marker[0].length;
      const end = index + 1 < markers.length ? markers[index + 1].index : normalized.length;
      return normalized.slice(start, end).trim();
    }).filter(Boolean);
    const intro = normalized.slice(0, markers[0].index).trim();
    return intro ? [intro, ...items] : items;
  }

  return normalized
    .split(/(?<=\.)\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function registerTrendsView({
  elements,
  api,
  formatMoney,
  formatPercent,
  escapeHtml,
  formatMonthLabel,
  formatDate,
}) {
  const {
    trendsPanel,
    trendsContent,
    trendsMeta,
    trendsTabs,
    cockpitTrendSummaryContent,
    monthlyBudgetSummary,
  } = elements;
  let trendsRequestId = 0;
  let currentMonth = null;
  let currentData = null;
  let loading = false;
  let error = "";
  let chartPeriod = "active";
  let activeTrendsTab = "overview";
  const subscriptionsFlyover = createSubscriptionsFlyover({ formatMoney, escapeHtml, formatDate });

  trendsPanel?.addEventListener("click", (event) => {
    const tab = event.target.closest("[data-trends-tab]");
    if (tab) {
      activeTrendsTab = tab.dataset.trendsTab || "overview";
      render();
      return;
    }
    const subscriptionTrigger = event.target.closest("[data-open-subscriptions]");
    if (subscriptionTrigger) {
      subscriptionsFlyover.open(currentData?.assinaturas_detalhadas || {});
      return;
    }
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
    renderTabState();
    if (activeTrendsTab === "subscriptions") {
      trendsContent.innerHTML = renderSubscriptionsTab();
      renderCompactSummary();
      return;
    }
    trendsContent.innerHTML = `
      ${renderSeriesChart()}
      ${renderFindings()}
      ${renderBudgetActualTable()}
      ${renderConfidenceNotes()}
    `;
    renderTrendsApexChart();
    renderCompactSummary();
  }

  function renderTabState() {
    trendsTabs?.forEach((tab) => {
      const active = tab.dataset.trendsTab === activeTrendsTab;
      tab.classList.toggle("active", active);
      tab.setAttribute("aria-selected", active ? "true" : "false");
      tab.tabIndex = active ? 0 : -1;
    });
  }

  function renderSubscriptionsTab() {
    const data = currentData.assinaturas_detalhadas || {};
    const items = Array.isArray(data.itens) ? data.itens : [];
    return `
      <section class="subscriptions-overview">
        <div class="subscriptions-overview-heading">
          <div>
            <span class="eyebrow">PAINEL ANALÍTICO</span>
            <h3>Assinaturas e serviços recorrentes</h3>
            <p>Consolidado do mês a partir dos lançamentos recorrentes já classificados em contas e cartões.</p>
          </div>
          <button class="primary" type="button" data-open-subscriptions>Ver detalhes completos</button>
        </div>
        <div class="subscriptions-overview-total">
          <div><span>Total mensal</span><strong>${formatMoney(Number(data.total_mensal_cents || 0) / 100, "BRL")}</strong></div>
          <div><span>Estimativa anual</span><strong>${formatMoney(Number(data.estimativa_anual_cents || 0) / 100, "BRL")}</strong></div>
          <div><span>Serviços identificados</span><strong>${items.length}</strong></div>
        </div>
        ${items.length ? `
          <div class="subscriptions-overview-list">
            ${items.map((item) => `
              <button class="subscription-overview-row" type="button" data-open-subscriptions>
                <span><strong>${escapeHtml(item.servico || "Cobrança recorrente")}</strong><small>${escapeHtml(item.subcategoria || "Geral")} · ${escapeHtml(item.confianca_label || "Intermediária")}</small></span>
                <strong>${formatMoney(Number(item.valor_mensal_cents || 0) / 100, "BRL")}</strong>
              </button>
            `).join("")}
          </div>
        ` : stateMarkup("Nenhum lançamento recorrente identificado neste mês.", { kind: "empty" })}
      </section>
    `;
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

  function renderSummaryMetrics() {
    const income = Number(currentData.receitas_mes_cents || 0);
    const expense = Number(currentData.despesas_mes_cents || 0);
    const balance = Number(currentData.saldo_mes_cents || 0);
    const baseIncome = Number(currentData.receitas_base_comparacao_cents || 0);
    const baseExpense = Number(currentData.despesas_base_comparacao_cents || 0);
    return `
      <div class="trends-summary" aria-label="Resumo financeiro do período">
        <div class="trends-summary-item income">
          <span>Receitas</span>
          <strong>${formatMoney(income / 100, "BRL")}</strong>
          <small>${baseIncome > 0 ? `base: ${formatMoney(baseIncome / 100, "BRL")}` : "&nbsp;"}</small>
        </div>
        <div class="trends-summary-item expense">
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
        </div>
        <div class="trends-summary-item balance">
          <span>Saldo</span>
          <strong class="${balance < 0 ? "danger-text" : ""}">${formatMoney(balance / 100, "BRL")}</strong>
          <small>&nbsp;</small>
        </div>
      </div>
    `;
  }

  function renderSeriesChart() {
    const filteredSeries = filterMonthlySeries(currentData.serie_mensal || []);
    const chartMarkup = filteredSeries.length === 0
      ? stateMarkup("Sem meses com movimento suficiente para formar uma evolução.", { kind: "empty" })
      : `
          <div class="trends-apex-chart" role="img" aria-label="Gráfico de evolução de receitas, despesas e saldo"></div>
          <div class="trends-chart-legend">
            <span class="income"><i></i> Receitas</span>
            <span class="expense"><i></i> Despesas</span>
            <span class="balance"><i></i> Saldo líquido</span>
          </div>
          <p class="trends-chart-insight">${escapeHtml(monthlyChartInsight(filteredSeries))}</p>
        `;
    return `
      <section class="trends-chart-section">
        <div class="trends-chart-heading">
          <div>
            <span class="trends-section-eyebrow">RESUMO DO PERÍODO</span>
            <h3>Evolução mensal</h3>
          </div>
          <div class="trends-chart-periods" aria-label="Período do gráfico">
            ${renderPeriodButton("active", "Com movimento")}
            ${renderPeriodButton("3", "3 meses")}
            ${renderPeriodButton("6", "6 meses")}
            ${renderPeriodButton("12", "12 meses")}
          </div>
        </div>
        <div class="trends-chart trends-hero">
          ${renderSummaryMetrics()}
          ${chartMarkup}
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
          <div class="trends-section-heading">
            <div>
              <span class="trends-section-eyebrow">ACOMPANHAMENTO</span>
              <h3>Orçamento do mês</h3>
            </div>
            <span class="trends-section-note">Limites cadastrados x realizado</span>
          </div>
          ${stateMarkup("Cadastre limites de gasto para comparar orçamento e realizado.", { kind: "empty" })}
        </section>
      `;
    }
    return `
      <section class="trends-budget-section">
        <div class="trends-section-heading">
          <div>
            <span class="trends-section-eyebrow">ACOMPANHAMENTO</span>
            <h3>Orçamento do mês</h3>
          </div>
          <span class="trends-section-note">Limites cadastrados x realizado</span>
        </div>
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
    const pointFindings = cardFindings.filter((finding) => finding.tipo === "evento_pontual");
    const limitFindings = cardFindings.filter((finding) => finding.tipo === "limite" || finding.tipo === "limite_recorrente");
    const individualFindings = cardFindings.filter((finding) => !pointFindings.includes(finding) && !limitFindings.includes(finding));
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
          <div class="trends-section-heading">
            <div>
              <span class="trends-section-eyebrow">LEITURA EXECUTIVA</span>
              <h3>Tendências e achados</h3>
            </div>
          </div>
          ${stateMarkup("Selecione outro mês ou aguarde novos dados para gerar achados.", { kind: "empty" })}
        </section>
      `;
    }
    return `
      <section class="trends-findings-section">
        <div class="trends-section-heading">
          <div>
            <span class="trends-section-eyebrow">LEITURA EXECUTIVA</span>
            <h3 class="trends-findings-title">Tendências e achados ${aiSummaryMarker}</h3>
          </div>
        </div>
        ${summaryText ? renderSummaryText(summaryText) : ""}
        ${(currentData.assinaturas_detalhadas?.itens || []).length ? `
          <button class="trends-subscription-link" type="button" data-open-subscriptions>
            <span>Assinaturas e serviços recorrentes</span><span aria-hidden="true">→</span>
          </button>
        ` : ""}
        ${sourceNotice}
        ${pointFindings.length ? `
          <article class="trends-finding trends-finding-group trends-finding-events info">
            <header>
              <strong>Eventos pontuais</strong>
              <span>${pointFindings.length} ocorrência${pointFindings.length === 1 ? "" : "s"}</span>
            </header>
            <ul class="trends-finding-bullets">
              ${pointFindings.map((finding) => {
                const title = String(finding.titulo || "Evento pontual")
                  .replace(/^Receita pontual:\s*/i, "")
                  .replace(/^Despesa pontual:\s*/i, "");
                const kind = /^Receita pontual:/i.test(finding.titulo || "") ? "Receita" : "Despesa";
                const value = Number(finding.valor_cents || 0);
                return `
                  <li>
                    <div><strong>${kind}</strong><span>${escapeHtml(title)}</span>${value ? `<b>${formatMoney(value / 100, "BRL")}</b>` : ""}</div>
                    <p>${escapeHtml(finding.descricao)}</p>
                  </li>
                `;
              }).join("")}
            </ul>
          </article>
        ` : ""}
        ${limitFindings.length ? `
          <article class="trends-finding trends-finding-group trends-finding-limits warning">
            <header>
              <strong>Limites de gastos</strong>
              <span>${limitFindings.length} item${limitFindings.length === 1 ? "" : "ns"}</span>
            </header>
            <ul class="trends-finding-bullets">
              ${limitFindings.map((finding) => {
                const value = Number(finding.valor_cents || 0);
                return `
                  <li>
                    <div><strong>${escapeHtml(finding.titulo)}</strong>${value ? `<b>${formatMoney(value / 100, "BRL")}</b>` : ""}</div>
                    <p>${escapeHtml(finding.descricao)}</p>
                    ${finding.tipo === "limite_recorrente" ? `<small class="trends-finding-action">Revisar limite</small>` : ""}
                  </li>
                `;
              }).join("")}
            </ul>
          </article>
        ` : ""}
        ${individualFindings.length ? `
          <div class="trends-findings-list">
            ${individualFindings.map((finding) => {
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
        <div class="trends-section-heading">
          <div>
            <span class="trends-section-eyebrow">CONTEXTO DA ANÁLISE</span>
            <h3>Confiança e limitações</h3>
          </div>
        </div>
        <div class="trends-confidence-list">
        ${confidenceFindings.map((finding) => `
          <article class="trends-confidence-card">
            <h3>${escapeHtml(finding.titulo)}</h3>
            <p>${escapeHtml(finding.descricao)}</p>
          </article>
        `).join("")}
        </div>
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

  return {
    renderTrends,
    renderCockpitSummary,
  };
}
