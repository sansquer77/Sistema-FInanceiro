import { renderChart, destroyChart } from "./chart-adapter.js";

export function createReportEvolution({
  reportContent, api, formatMoney, formatMonthShortLabel,
  document = globalThis.document,
}) {
  // --- Evolution Drawer Logic ---
  
  const drawer = document.getElementById("evolutionDrawer");
  const drawerOverlay = document.getElementById("evolutionDrawerCloseOverlay");
  const drawerCloseBtn = document.getElementById("evolutionDrawerCloseBtn");
  const drawerTitle = document.getElementById("evolutionDrawerTitle");
  const chartTrend = document.getElementById("evolutionChartTrend");
  const chartTotal = document.getElementById("evolutionChartTotal");
  const svgEl = document.getElementById("evolutionSvg");
  const xLabelsEl = document.getElementById("evolutionXLabels");
  const filterBtns = document.querySelectorAll(".evolution-filter-btn");
  const smaToggle = document.getElementById("evolutionSmaToggle");
  const forecastMonthsSelect = document.getElementById("evolutionForecastMonths");
  
  let currentEvolutionContext = null;
  let currentEvolutionData = null;
  let currentEvolutionColor = "";
  let evolutionRequestId = 0;

  if (drawerOverlay && drawerCloseBtn) {
    drawerOverlay.addEventListener("click", closeEvolutionDrawer);
    drawerCloseBtn.addEventListener("click", closeEvolutionDrawer);
  }

  filterBtns.forEach(btn => {
    btn.addEventListener("click", () => {
      filterBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      if (currentEvolutionContext) {
        loadEvolutionChart(currentEvolutionContext, btn.dataset.period);
      }
    });
  });

  if (smaToggle) {
    smaToggle.addEventListener("change", redrawCurrentEvolutionChart);
  }

  if (forecastMonthsSelect) {
    forecastMonthsSelect.addEventListener("change", redrawCurrentEvolutionChart);
  }

  reportContent.addEventListener("click", (e) => {
    const btn = e.target.closest(".report-rank-evolution-btn");
    if (btn) {
      e.preventDefault();
      e.stopPropagation();
      openEvolutionDrawer({
        categoryId: btn.dataset.evolutionCategory,
        subcategoryId: btn.dataset.evolutionSubcategory,
        name: btn.dataset.evolutionName,
        color: btn.dataset.evolutionColor
      });
    }
  });

  function openEvolutionDrawer(context) {
    if (!drawer || !drawerTitle) {
      return;
    }
    currentEvolutionContext = context;
    drawerTitle.textContent = context.name;
    drawer.hidden = false;
    drawer.setAttribute("aria-hidden", "false");
    
    const activeBtn = document.querySelector(".evolution-filter-btn.active");
    loadEvolutionChart(context, activeBtn ? activeBtn.dataset.period : "12m");
  }

  function closeEvolutionDrawer() {
    if (!drawer) {
      return;
    }
    drawer.hidden = true;
    drawer.setAttribute("aria-hidden", "true");
    evolutionRequestId += 1;
    currentEvolutionData = null;
    destroyChart(svgEl);
  }

  async function loadEvolutionChart(context, period) {
    if (!svgEl || !xLabelsEl || !chartTotal || !chartTrend) {
      return;
    }
    destroyChart(svgEl);
    currentEvolutionData = null;
    svgEl.innerHTML = "";
    xLabelsEl.innerHTML = "";
    chartTotal.textContent = "Carregando...";
    chartTrend.textContent = "";
    const requestId = ++evolutionRequestId;

    try {
      const url = new URL("/api/reports/category-evolution", window.location.origin);
      if (context.categoryId) url.searchParams.set("category_id", context.categoryId);
      if (context.subcategoryId) url.searchParams.set("subcategory_id", context.subcategoryId);
      url.searchParams.set("period", period);
      
      const res = await api(url.pathname + url.search);
      if (requestId !== evolutionRequestId || context !== currentEvolutionContext) {
        return;
      }
      if (!Array.isArray(res.evolution) || !Array.isArray(res.forecast)
          || !Number.isFinite(res.total_cents)
          || !(res.trend_percent === null || Number.isFinite(res.trend_percent))) {
        throw new Error("Resposta incompatível. Atualize o servidor para consultar a evolução.");
      }
      drawEvolutionChart(res, context.color);
    } catch (err) {
      if (requestId !== evolutionRequestId || context !== currentEvolutionContext) {
        return;
      }
      currentEvolutionData = null;
      destroyChart(svgEl);
      svgEl.innerHTML = "";
      xLabelsEl.innerHTML = "";
      chartTotal.textContent = "Erro ao carregar";
      chartTrend.textContent = err.message || "Nao foi possivel carregar a evolucao.";
    }
  }

  function formatChartValue(cents) {
    const value = Number(cents || 0) / 100;
    const abs = Math.abs(value);
    const signal = value < 0 ? "-" : "";
    if (abs >= 1000000) {
      return `${signal}${(abs / 1000000).toFixed(1).replace(".", ",")}M`;
    }
    if (abs >= 1000) {
      return `${signal}${(abs / 1000).toFixed(1).replace(".", ",")}k`;
    }
    return `${signal}${abs.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}`;
  }

  function drawEvolutionChart(model, color) {
    currentEvolutionData = model;
    const data = model.evolution;
    currentEvolutionColor = color;
    chartTrend.textContent = "";
    if (data.length === 0) {
      chartTotal.textContent = "Sem dados";
      return;
    }

    chartTotal.textContent = formatMoney(model.total_cents / 100, "BRL");
    if (model.trend_percent !== null) {
      const diff = model.trend_percent;
      chartTrend.textContent = `${diff > 0 ? '+' : ''}${diff.toFixed(1)}% em relação ao início`;
    }
    const forecastMonths = Number(forecastMonthsSelect?.value || 3);
    const forecast = smaToggle?.checked ? model.forecast.slice(0, forecastMonths) : [];
    if (forecast.length) {
      chartTrend.textContent = [chartTrend.textContent, `SMA projetando ${forecastMonths} meses`].filter(Boolean).join(" · ");
    }
    const categories = [...data.map((entry) => entry.month), ...forecast.map((entry) => entry.month)];
    renderChart(svgEl, {
      chart: { type: "area", height: 300 },
      series: [
        { name: "Realizado", data: [...data.map((entry) => Number(entry.total_cents || 0)), ...forecast.map(() => null)] },
        { name: "Projeção SMA", data: [
          ...data.map((entry, index) => index === data.length - 1 ? Number(entry.total_cents || 0) : null),
          ...forecast.map((entry) => Number(entry.total_cents || 0)),
        ] },
      ],
      colors: [color, color],
      stroke: { curve: "smooth", width: [3, 2], dashArray: [0, 6] },
      fill: { type: "gradient", gradient: { opacityFrom: 0.28, opacityTo: 0.01 } },
      markers: { size: [4, 3] },
      xaxis: { categories, labels: { formatter: (month) => formatMonthShortLabel(month) } },
      yaxis: { labels: { formatter: formatChartValue } },
      tooltip: { y: { formatter: (value) => formatMoney(value / 100, "BRL") } },
      legend: { show: false },
    });

    if (data.length > 0) {
      const formatMonth = (m) => {
        const [yy, mm] = m.split("-");
        const date = new Date(parseInt(yy), parseInt(mm) - 1, 1);
        return date.toLocaleString('pt-BR', { month: 'short', year: '2-digit' }).replace('.', '');
      };
      
      const labels = [];
      labels.push(`<span>${formatMonth(data[0].month)}</span>`);
      if (data.length > 2) {
        const mid = Math.floor(data.length / 2);
        labels.push(`<span>${formatMonth(data[mid].month)}</span>`);
      }
      if (data.length > 1) {
        labels.push(`<span>${formatMonth(data[data.length - 1].month)}</span>`);
      }
      if (forecast.length > 0) {
        labels.push(`<span>${formatMonth(forecast[forecast.length - 1].month)}</span>`);
      }
      xLabelsEl.innerHTML = labels.join("");
    }
  }

  function redrawCurrentEvolutionChart() {
    if (!currentEvolutionData || !currentEvolutionColor) {
      return;
    }
    drawEvolutionChart(currentEvolutionData, currentEvolutionColor);
  }


  return { openEvolutionDrawer, closeEvolutionDrawer };
}
