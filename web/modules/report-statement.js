import { stateMarkup } from "./dom-utils.js";
import { renderChart } from "./chart-adapter.js";

export function createReportStatement({
  state, elements, api, renderReports, formatDate, formatMonthLabel,
  formatMoney, formatPercent, escapeHtml, chartColor, reportItemClassification,
}) {
  let statementDebtRequestId = 0;
  let statementDebts = null;
  const { statementScopeSelect, statementCurrencySelect, statementAccountSelect,
    statementCardSelect, printStatementButton, reportContent } = elements;

  statementScopeSelect.addEventListener("change", () => {
    state.statementScope = statementScopeSelect.value;
    normalizeStatementSelections();
    renderReports();
  });
  statementCurrencySelect.addEventListener("change", () => {
    state.statementCurrency = statementCurrencySelect.value;
    renderReports();
  });
  statementAccountSelect.addEventListener("change", () => {
    state.statementAccountIds = selectedValues(statementAccountSelect);
    renderReports();
  });
  statementCardSelect.addEventListener("change", () => {
    state.statementCardIds = selectedValues(statementCardSelect);
    renderReports();
  });
  printStatementButton.addEventListener("click", () => window.print());
  function renderStatementScopeOptions() {
    if (state.reportTab !== "statement") {
      return;
    }
    if (![...statementScopeSelect.options].some((option) => option.value === state.statementScope)) {
      state.statementScope = "consolidated";
    }
    statementScopeSelect.value = state.statementScope;
    const currencies = statementRegisteredCurrencies();
    statementCurrencySelect.innerHTML = [
      '<option value="all">Todas as moedas</option>',
      ...currencies.map((currency) => `<option value="${escapeHtml(currency)}">Consolidado ${escapeHtml(currency)}</option>`),
    ].join("");
    if (![...statementCurrencySelect.options].some((option) => option.value === state.statementCurrency)) {
      state.statementCurrency = "all";
    }
    statementCurrencySelect.value = state.statementCurrency;
    statementAccountSelect.innerHTML = state.accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("");
    statementCardSelect.innerHTML = state.creditCards.map((card) => (
      `<option value="${card.id}">${escapeHtml(card.name)} (${escapeHtml(card.currency)})</option>`
    )).join("");
    applyMultiSelectValues(statementAccountSelect, state.statementAccountIds);
    applyMultiSelectValues(statementCardSelect, state.statementCardIds);
    const selectedMode = state.statementScope === "selected";
    statementAccountSelect.disabled = !selectedMode || state.accounts.length === 0;
    statementCardSelect.disabled = !selectedMode || state.creditCards.length === 0;
    statementAccountSelect.closest("label").hidden = !selectedMode;
    statementCardSelect.closest("label").hidden = !selectedMode;
  }

  function statementRegisteredCurrencies() {
    return [...new Set([
      ...state.accounts.map((account) => account.currency || "BRL"),
      ...state.creditCards.map((card) => card.currency || "BRL"),
    ])].sort();
  }

  function selectedValues(select) {
    return [...select.selectedOptions].map((option) => option.value);
  }

  function applyMultiSelectValues(select, values) {
    const selected = new Set((values || []).map(String));
    for (const option of select.options) {
      option.selected = selected.has(String(option.value));
    }
  }

  function normalizeStatementSelections() {
    if (state.statementScope !== "selected") {
      return;
    }
    const validAccountIds = new Set(state.accounts.map((account) => String(account.id)));
    const validCardIds = new Set(state.creditCards.map((card) => String(card.id)));
    state.statementAccountIds = state.statementAccountIds.filter((id) => validAccountIds.has(String(id)));
    state.statementCardIds = state.statementCardIds.filter((id) => validCardIds.has(String(id)));
  }

  async function renderStatementReport() {
    const requestId = ++statementDebtRequestId;
    statementDebts = null;
    printStatementButton.disabled = true;
    reportContent.innerHTML = stateMarkup("Preparando demonstrativo…", { kind: "loading" });
    const query = new URLSearchParams({ month: state.reportMonth, currency: state.statementCurrency || "all" });
    if (state.statementScope === "selected") {
      query.set("account_ids", state.statementAccountIds.join(","));
      query.set("card_ids", state.statementCardIds.join(","));
    }
    try {
      const result = await api(`/api/reports/statement?${query}`);
      if (requestId !== statementDebtRequestId || state.reportTab !== "statement") return;
      if (!Array.isArray(result?.sections)) throw new Error("Atualize o servidor para consultar o demonstrativo.");
      statementDebts = result;
      paintStatementReport();
      printStatementButton.disabled = !result.sections.length;
    } catch (error) {
      if (requestId !== statementDebtRequestId || state.reportTab !== "statement") return;
      reportContent.innerHTML = stateMarkup(error.message || "Não foi possível consultar o demonstrativo.", { kind: "error" });
      printStatementButton.disabled = true;
    }
  }

  function paintStatementReport() {
    const sections = statementDebts.sections;
    if (!sections.length) {
      reportContent.innerHTML = `
        <article class="monthly-statement">
          ${statementHeader(statementScopeInfo(), "BRL", new Date())}
          ${stateMarkup("Selecione outro período ou amplie o escopo de contas e cartões.", { kind: "empty" })}
        </article>
      `;
      return;
    }
    const issuedAt = new Date();
    const scope = statementScopeInfo();
    reportContent.innerHTML = `
      <article class="monthly-statement">
        ${sections.map((section, index) => statementCurrencyReport(section, scope, issuedAt, index)).join("")}
        <footer class="statement-footer">
          <span>Sistema Financeiro</span>
          <span>Página <span class="statement-page-number"></span> de <span class="statement-page-total"></span></span>
        </footer>
      </article>
    `;
    renderStatementCharts(sections);
  }

  function statementCurrencyReport(section, scope, issuedAt, index) {
    const { currency, items, top_category: topCategory, top_transaction: topTransaction } = section;
    return `
      <section class="statement-currency-report ${index > 0 ? "statement-page-break" : ""}">
        ${statementHeader(scope, currency, issuedAt)}
        <section class="statement-kpis" aria-label="Resumo executivo">
          ${statementKpi("Total de Saídas", formatMoney(section.total, currency))}
          ${statementKpi("Média Diária", formatMoney(section.average, currency))}
          ${statementKpi("Saídas em Conta", formatMoney(section.account_total, currency))}
          ${statementKpi("Despesas em Cartão", formatMoney(section.card_total, currency))}
          ${statementKpi("Parcelas em aberto (estado atual)", formatMoney(section.open_debts, currency))}
          ${statementKpi("Maior Despesa", topCategory ? `${escapeHtml(topCategory.label)} · ${formatMoney(topCategory.amount, currency)}` : "Sem despesas")}
          ${statementKpi("Transação de Maior Impacto", topTransaction ? `${escapeHtml(topTransaction.description || topTransaction.category)} · ${formatMoney(topTransaction.amount, topTransaction.currency)}` : "Sem despesas")}
        </section>
        <section class="statement-visuals">
          <div class="statement-chart-card statement-donut-card">
            <h3>Distribuição por categoria</h3>
            ${statementDonutChart(section.distribution, section.total, currency, index)}
          </div>
          <div class="statement-chart-card">
            <h3>Gastos por dia do mês</h3>
            ${statementDailyBars(section.daily, currency, index)}
          </div>
        </section>
        <section class="statement-section">
          <h3>Composição de Despesas</h3>
          ${statementCompositionBySource(section.composition, currency)}
        </section>
        <section class="statement-section">
          <h3>Detalhamento de Lançamentos</h3>
          ${statementDetailTable(items)}
        </section>
      </section>
    `;
  }

  function statementHeader(scope, currencyLabel, issuedAt) {
    return `
      <header class="statement-header">
        <img src="assets/app-icon.png" alt="Sistema Financeiro">
        <div>
          <h2>Relatório de Despesas Mensal (${escapeHtml(formatMonthLabel(state.reportMonth))})</h2>
          <p>Escopo: ${escapeHtml(scope.label)}</p>
          <p>Moeda Base: ${escapeHtml(currencyLabel)}</p>
          <p>Data de Emissão: ${escapeHtml(formatStatementDateTime(issuedAt))}</p>
        </div>
      </header>
    `;
  }

  function statementKpi(label, value) {
    return `
      <div>
        <span>${escapeHtml(label)}</span>
        <strong>${value}</strong>
      </div>
    `;
  }

  function statementScopeInfo() {
    if (state.statementScope === "selected") {
      const accountNames = state.statementAccountIds.length
        ? state.accounts.filter((account) => state.statementAccountIds.map(String).includes(String(account.id))).map((account) => account.name)
        : state.accounts.map((account) => account.name);
      const cardNames = state.statementCardIds.length
        ? state.creditCards.filter((card) => state.statementCardIds.map(String).includes(String(card.id))).map((card) => card.name)
        : state.creditCards.map((card) => card.name);
      return { label: [...accountNames, ...cardNames].join(", ") || "Itens selecionados", currency: "" };
    }
    return { label: "Visão Consolidada", currency: "" };
  }

  function statementDonutChart(rows, total, currency, sectionIndex) {
    if (!rows.length || total <= 0) {
      return stateMarkup("Selecione outro período ou escopo para compor o gráfico.", { kind: "empty" });
    }
    const legend = rows.map((row, index) => {
      return `
        <li><i style="background:${chartColor(index)}"></i><span>${escapeHtml(row.label)}</span><strong>${formatPercent(row.share)}</strong></li>
      `;
    }).join("");
    return `
      <div class="statement-donut">
        <div class="statement-distribution-apex" data-statement-distribution-chart="${sectionIndex}" role="img" aria-label="Distribuição das despesas por categoria em ${escapeHtml(currency)}"></div>
      </div>
      <ul class="statement-chart-legend">${legend}</ul>
    `;
  }

  function statementDailyBars(days, currency, sectionIndex) {
    if (!days.length) {
      return stateMarkup("Não há gastos diários no período selecionado.", { kind: "empty" });
    }
    return `
      <div class="statement-daily-apex" data-statement-daily-chart="${sectionIndex}" role="img" aria-label="Gastos por dia do mês em ${escapeHtml(currency)}"></div>
    `;
  }

  function renderStatementCharts(sections) {
    sections.forEach((section, index) => {
      renderStatementDistributionChart(section, index);
      renderStatementDailyChart(section, index);
    });
  }

  function renderStatementDistributionChart(section, index) {
    const element = reportContent.querySelector(`[data-statement-distribution-chart="${index}"]`);
    if (!element) return;
    const rows = section.distribution || [];
    renderChart(element, {
      chart: { type: "donut", height: 190 },
      series: rows.map((row) => Number(row.amount || 0)),
      labels: rows.map((row) => row.label),
      colors: rows.map((_, colorIndex) => chartColor(colorIndex)),
      stroke: { width: 2 },
      legend: { show: false },
      tooltip: { y: { formatter: (value) => formatMoney(value, section.currency) } },
      plotOptions: {
        pie: {
          donut: {
            size: "72%",
            labels: {
              show: true,
              name: { show: true, offsetY: -5, formatter: () => "Total gasto" },
              value: {
                show: true,
                offsetY: 5,
                formatter: () => formatMoney(section.total, section.currency),
              },
              total: {
                show: true,
                showAlways: true,
                label: "Total gasto",
                fontSize: "11px",
                fontWeight: 800,
                formatter: () => formatMoney(section.total, section.currency),
              },
            },
          },
        },
      },
    });
  }

  function renderStatementDailyChart(section, index) {
    const element = reportContent.querySelector(`[data-statement-daily-chart="${index}"]`);
    if (!element) return;
    const days = section.daily || [];
    renderChart(element, {
      chart: { type: "bar", height: 190 },
      series: [{ name: "Gastos", data: days.map((day) => Number(day.amount || 0)) }],
      colors: [chartColor(0)],
      plotOptions: { bar: { borderRadius: 3, columnWidth: "68%" } },
      xaxis: {
        categories: days.map((day) => Number(day.date.slice(-2))),
        labels: { rotate: 0, hideOverlappingLabels: true },
      },
      yaxis: { labels: { formatter: (value) => formatMoney(value, section.currency) } },
      tooltip: {
        x: { formatter: (_, context) => formatDate(days[context.dataPointIndex]?.date || "") },
        y: { formatter: (value) => formatMoney(value, section.currency) },
      },
      legend: { show: false },
    });
  }

  function statementCompositionBySource(composition, currency) {
    return `
      <div class="statement-source-grid">
        <section>
          <h4>Despesas oriundas de Conta</h4>
          ${statementCompositionTable(composition.account, currency)}
        </section>
        <section>
          <h4>Despesas em Cartão de Crédito</h4>
          ${statementCompositionTable(composition.card, currency)}
        </section>
      </div>
    `;
  }

  function statementCompositionTable(rows, currency) {
    if (!rows.length) {
      return stateMarkup("Não há composição de despesas no período selecionado.", { kind: "empty" });
    }
    return `
      <div class="report-table-wrap">
        <table class="report-table statement-table">
          <thead><tr><th>Categoria / Subcategoria</th><th>Total Gasto</th><th>% do Mês</th></tr></thead>
          <tbody>
            ${rows.map((row) => {
              return `<tr><td>${escapeHtml(row.label.replace(" / ", " › "))}</td><td class="money-cell">${formatMoney(row.amount, currency)}</td><td class="money-cell">${formatPercent(row.share)}</td></tr>`;
            }).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  function statementDetailTable(items) {
    if (!items.length) {
      return stateMarkup("Selecione outro período ou registre lançamentos para gerar o demonstrativo.", { kind: "empty" });
    }
    const rows = items.map((item) => `
      <tr>
        <td>${formatDate(item.date)}</td>
        <td>${escapeHtml(item.description || item.category)}</td>
        <td>${escapeHtml(statementItemOriginLabel(item))}</td>
        <td>${escapeHtml(reportItemClassification(item).replace(" / ", " › "))}</td>
        <td><span class="statement-tags">${escapeHtml(item.tags.map((tag) => `#${tag}`).join(" "))}</span></td>
        <td class="money-cell">${formatMoney(item.amount, item.currency)}</td>
      </tr>
    `).join("");
    return `
      <div class="report-table-wrap">
        <table class="report-table statement-table">
          <thead><tr><th>Data</th><th>Descrição</th><th>Origem</th><th>Categoria / Subcategoria</th><th>Tags</th><th>Valor</th></tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    `;
  }

  function statementItemOriginLabel(item) {
    return `${item.source} · ${item.accountName || (item.source === "Cartão" ? "Cartão" : "Conta")}`;
  }




  function formatStatementDateTime(date) {
    return date.toLocaleString("pt-BR", {
      dateStyle: "short",
      timeStyle: "short",
    });
  }


  return {
    renderStatementScopeOptions,
    renderStatementReport,
    invalidate() { statementDebtRequestId += 1; statementDebts = null; },
  };
}
