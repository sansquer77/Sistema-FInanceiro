import { chartToken, destroyChart, renderChart } from "./chart-adapter.js";

export function createPortfolioChart({ state, elements, api, formatPercentValue, chartColor }) {
  const {
    portfolioReturnChart,
    portfolioReturnXLabels,
    portfolioReturnYAxis,
    portfolioReturnLegend,
    portfolioReturnNotice,
    portfolioReturnDrawerTitle,
  } = elements;

  async function openReturns() {
    if (!elements.portfolioReturnDrawer) return;
    elements.portfolioReturnDrawer.hidden = false;
    elements.portfolioReturnDrawer.setAttribute("aria-hidden", "false");
    if (!state.portfolioReturns || state.portfolioReturns.error) {
      try {
        state.portfolioReturns = await api("/api/portfolio/returns");
      } catch (error) {
        state.portfolioReturns = { error: error.message || "Erro ao carregar" };
      }
    }
    renderReturns();
  }

  function closeReturns() {
    if (!elements.portfolioReturnDrawer) return;
    elements.portfolioReturnDrawer.hidden = true;
    elements.portfolioReturnDrawer.setAttribute("aria-hidden", "true");
    destroyReturns();
  }

  function renderReturns() {
    const returns = state.portfolioReturns;
    if (!returns) return;
    if (returns.error) {
      portfolioReturnChart?.replaceChildren();
      portfolioReturnXLabels?.replaceChildren();
      if (portfolioReturnLegend) portfolioReturnLegend.innerHTML = '<span class="error-text">Não foi possível carregar a rentabilidade.</span>';
      return;
    }
    if (!returns.series?.length) return;
    if (portfolioReturnDrawerTitle) {
      const start = monthLabel(returns.start_month);
      const end = monthLabel(returns.end_month);
      portfolioReturnDrawerTitle.textContent = start === end ? start : `${start} a ${end}`;
    }
    if (portfolioReturnNotice) {
      const copy = portfolioReturnNotice.querySelector("small") || portfolioReturnNotice;
      copy.textContent = portfolioCoverageNotice(returns.snapshot_coverage);
      portfolioReturnNotice.hidden = false;
    }

    const seriesConfig = [
      { key: "BRL_return_pct", label: "R$", color: chartColor(0) },
      { key: "USD_return_pct", label: "US$", color: chartColor(1) },
      { key: "cdi_return_pct", label: "CDI", color: "var(--muted)" },
      { key: "ipca_return_pct", label: "IPCA", color: "var(--accent)" },
    ];
    renderChart(portfolioReturnChart, {
      chart: { type: "area", height: 310 },
      series: seriesConfig.map((series) => ({
        name: series.label,
        data: returns.series.map((entry) => entry[series.key] == null ? null : Number(entry[series.key])),
      })),
      colors: [
        chartToken("--chart-1", "#5f7fff"), chartToken("--chart-2", "#36b37e"),
        chartToken("--muted", "#6b7280"), chartToken("--accent", "#ffab00"),
      ],
      stroke: { curve: "smooth", width: [3, 3, 2, 2], dashArray: [0, 0, 5, 5] },
      fill: { type: "gradient", gradient: { opacityFrom: 0.16, opacityTo: 0.01 } },
      markers: { size: 3 },
      xaxis: { categories: returns.series.map((entry) => shortMonthLabel(entry.month)) },
      yaxis: { labels: { formatter: signedPercent } },
      tooltip: { y: { formatter: signedPercent } },
      legend: { show: false },
      annotations: { yaxis: [{ y: 0, borderColor: chartToken("--ink", "#111827") }] },
    });
    portfolioReturnYAxis?.replaceChildren();
    portfolioReturnXLabels?.replaceChildren();
    if (portfolioReturnLegend) {
      portfolioReturnLegend.innerHTML = seriesConfig.map((series) => `<span><i style="background:${series.color}"></i>${series.label}</span>`).join("");
    }
  }

  function signedPercent(value) {
    return `${value > 0 ? "+" : ""}${formatPercentValue(value)}`;
  }

  function destroyReturns() {
    destroyChart(portfolioReturnChart);
    portfolioReturnXLabels?.replaceChildren();
    portfolioReturnYAxis?.replaceChildren();
    portfolioReturnLegend?.replaceChildren();
  }

  return { closeReturns, openReturns, renderReturns };
}

function monthLabel(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
}

function shortMonthLabel(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("pt-BR", { month: "short" }).replace(".", "").slice(0, 1).toUpperCase();
}

export function portfolioCoverageNotice(coverage = {}) {
  const observed = Array.isArray(coverage.observed_months) ? coverage.observed_months.length : 0;
  const approximate = Array.isArray(coverage.approximate_months) ? coverage.approximate_months.length : 0;
  const future = Array.isArray(coverage.future_months) ? coverage.future_months.length : 0;
  const elapsed = observed + approximate;
  const percent = Number.isFinite(Number(coverage.coverage_percent)) ? Number(coverage.coverage_percent) : 0;
  const coverageText = elapsed
    ? `${observed} de ${elapsed} ${elapsed === 1 ? "mês decorrido usa" : "meses decorridos usam"} snapshot observado (${percent.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%).`
    : "Ainda não há mês decorrido com snapshot observado.";
  const approximationText = approximate
    ? ` ${approximate} ${approximate === 1 ? "mês permanece aproximado" : "meses permanecem aproximados"} por ausência de fechamento histórico.`
    : "";
  const futureText = future ? ` ${future} ${future === 1 ? "mês futuro permanece zerado" : "meses futuros permanecem zerados"}.` : "";
  return `${coverageText}${approximationText}${futureText}`;
}
