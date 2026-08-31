import { chartToken, renderChart } from "./chart-adapter.js";

export function createPortfolioChart({ state, elements, formatPercentValue, chartColor }) {
  const {
    portfolioReturnChart,
    portfolioReturnXLabels,
    portfolioReturnYAxis,
    portfolioReturnLegend,
    portfolioReturnNotice,
    portfolioReturnDrawerTitle,
  } = elements;

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
    if (portfolioReturnNotice) portfolioReturnNotice.hidden = !returns.has_historical_approximation;

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

  return { renderReturns };
}

function monthLabel(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("pt-BR", { month: "long", year: "numeric" });
}

function shortMonthLabel(month) {
  const [year, monthNumber] = month.split("-").map(Number);
  return new Date(year, monthNumber - 1, 1).toLocaleDateString("pt-BR", { month: "short" }).replace(".", "").slice(0, 1).toUpperCase();
}
