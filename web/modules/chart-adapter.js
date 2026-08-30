const chartInstances = new WeakMap();

function cssToken(name, fallback) {
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

export function chartPalette() {
  return [
    cssToken("--chart-1", "#5f7fff"),
    cssToken("--chart-2", "#36b37e"),
    cssToken("--chart-3", "#ffab00"),
    cssToken("--chart-4", "#ff7452"),
    cssToken("--chart-5", "#6554c0"),
  ];
}

export function chartToken(name, fallback) {
  return cssToken(name, fallback);
}

export function centeredMonthlyPoints(rows, valueFor) {
  return rows.map((row, index) => ({ x: index, y: valueFor(row) }));
}

export function centeredMonthlyAxis(rows) {
  return {
    type: "numeric",
    min: -0.5,
    max: Math.max(0.5, rows.length - 0.5),
    labels: { show: false },
    axisBorder: { show: false },
    axisTicks: { show: false },
    tooltip: { enabled: false },
  };
}

export function destroyChart(element) {
  const instance = element ? chartInstances.get(element) : null;
  if (instance) {
    instance.destroy();
    chartInstances.delete(element);
  }
  if (element) element.replaceChildren();
}

export function renderChart(element, options, { emptyMessage = "Sem dados para exibir." } = {}) {
  if (!element) return null;
  destroyChart(element);
  if (!globalThis.ApexCharts) {
    element.innerHTML = `<p class="muted-copy" role="status">${emptyMessage}</p>`;
    return null;
  }

  const reduceMotion = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches === true;
  const instance = new globalThis.ApexCharts(element, {
    ...options,
    chart: {
      background: "transparent",
      foreColor: cssToken("--muted", "#6b7280"),
      fontFamily: "inherit",
      animations: { enabled: !reduceMotion },
      toolbar: { show: false },
      zoom: { enabled: false },
      parentHeightOffset: 0,
      ...(options.chart || {}),
    },
    grid: {
      borderColor: cssToken("--line", "#d9dde7"),
      ...(options.grid || {}),
    },
    colors: options.colors || chartPalette(),
    dataLabels: { enabled: false, ...(options.dataLabels || {}) },
    noData: { text: emptyMessage, ...(options.noData || {}) },
  });
  chartInstances.set(element, instance);
  instance.render().catch(() => {
    if (chartInstances.get(element) !== instance) return;
    chartInstances.delete(element);
    element.innerHTML = `<p class="muted-copy" role="status">${emptyMessage}</p>`;
  });
  return instance;
}
