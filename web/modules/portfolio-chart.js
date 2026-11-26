import { chartToken, destroyChart, renderChart } from "./chart-adapter.js";

export function createPortfolioChart({ state, elements, api, formatPercentValue, chartColor }) {
  const {
    portfolioEvolutionChart,
    portfolioEvolutionLegend,
    portfolioEvolutionStatus,
  } = elements;

  let evolutionRequest = null;

  async function loadEvolution() {
    if (!portfolioEvolutionChart) return;
    if (evolutionRequest) return evolutionRequest;
    setEvolutionPlaceholder("Carregando evolução...");
    if (!state.portfolioReturns || state.portfolioReturns.error) {
      evolutionRequest = Promise.resolve(api("/api/portfolio/returns"))
        .then((data) => {
          state.portfolioReturns = data;
          renderEvolution();
        })
        .catch((error) => {
          state.portfolioReturns = { error: error.message || "Erro ao carregar" };
          renderEvolution();
        })
        .finally(() => {
          evolutionRequest = null;
        });
      return evolutionRequest;
    }
    renderEvolution();
  }

  function renderEvolution() {
    if (!portfolioEvolutionChart) return;
    const returns = state.portfolioReturns;
    if (!returns || returns.error) {
      destroyEvolution();
      setEvolutionPlaceholder("A evolução ainda não está disponível.");
      if (portfolioEvolutionStatus) portfolioEvolutionStatus.textContent = "Evolução indisponível";
      return;
    }
    const currencies = portfolioEvolutionReturnCurrencies(returns.series || []);
    const seriesConfig = [
      ...currencies.map((currency, index) => ({
        key: `${currency}_return_pct`,
        label: currency,
        color: chartColor(index),
        dash: 0,
        width: 2.5,
      })),
      { key: "cdi_return_pct", label: "CDI", color: chartToken("--muted", "#6b7280"), dash: 5, width: 2 },
      { key: "ipca_return_pct", label: "IPCA", color: chartToken("--accent", "#ffab00"), dash: 5, width: 2 },
    ];
    const futureMonths = returns.snapshot_coverage?.future_months || [];
    const hasPoints = seriesConfig.some((series) => returns.series.some((entry) => (
      !futureMonths.includes(entry.month) && entry[series.key] != null
    )));
    if (!hasPoints) {
      destroyEvolution();
      setEvolutionPlaceholder("Ainda não há histórico suficiente para este gráfico.");
      if (portfolioEvolutionStatus) portfolioEvolutionStatus.textContent = "Sem histórico suficiente";
      return;
    }
    renderChart(portfolioEvolutionChart, {
      chart: { type: "area", height: 218, toolbar: { show: false }, sparkline: { enabled: false } },
      series: seriesConfig.map((series) => ({
        name: series.label,
        data: returns.series.map((entry) => futureMonths.includes(entry.month) || entry[series.key] == null
          ? null
          : Number(entry[series.key])),
      })),
      colors: seriesConfig.map((series) => series.color),
      stroke: {
        curve: "smooth",
        width: seriesConfig.map((series) => series.width),
        dashArray: seriesConfig.map((series) => series.dash),
      },
      fill: { type: "gradient", gradient: { opacityFrom: 0.16, opacityTo: 0.02 } },
      markers: { size: 0, hover: { size: 4 } },
      xaxis: { categories: returns.series.map((entry) => shortMonthLabel(entry.month)), labels: { trim: true } },
      yaxis: { labels: { formatter: signedPercent } },
      tooltip: { y: { formatter: signedPercent } },
      legend: { show: false },
      grid: { borderColor: chartToken("--content-line", "#e1e5ec"), strokeDashArray: 4 },
      dataLabels: { enabled: false },
      annotations: { yaxis: [{ y: 0, borderColor: chartToken("--ink", "#111827") }] },
    });
    if (portfolioEvolutionLegend) {
      portfolioEvolutionLegend.innerHTML = seriesConfig.map((series) => (
        `<span><i style="background:${series.color}"></i>${series.label}</span>`
      )).join("");
    }
    if (portfolioEvolutionStatus) {
      const coverage = returns.snapshot_coverage || {};
      portfolioEvolutionStatus.textContent = coverage.approximate_months?.length
        ? "Inclui estimativas históricas"
        : "Rentabilidade mensal disponível";
    }
  }

  function clearEvolution() {
    destroyEvolution();
    setEvolutionPlaceholder("A evolução aparece após o primeiro período observado.");
    if (portfolioEvolutionStatus) portfolioEvolutionStatus.textContent = "Últimos meses disponíveis";
  }

  function setEvolutionPlaceholder(message) {
    if (portfolioEvolutionChart) {
      portfolioEvolutionChart.innerHTML = `<span class="portfolio-evolution-empty">${message}</span>`;
    }
  }

  function destroyEvolution() {
    destroyChart(portfolioEvolutionChart);
    portfolioEvolutionLegend?.replaceChildren();
  }

  function signedPercent(value) {
    return `${value > 0 ? "+" : ""}${formatPercentValue(value)}`;
  }

  return { clearEvolution, loadEvolution, renderEvolution };
}

function portfolioEvolutionReturnCurrencies(series) {
  const currencies = [];
  series.forEach((entry) => {
    Object.keys(entry).filter((key) => key.endsWith("_return_pct") && !["cdi_return_pct", "ipca_return_pct"].includes(key)).forEach((key) => {
      const currency = key.slice(0, -11);
      if (!currencies.includes(currency) && series.some((item) => item[key] != null)) currencies.push(currency);
    });
  });
  return currencies.slice(0, 3);
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
