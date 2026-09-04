const chartInstances = new Map();
const chartDefinitions = new Map();
let cleanupObserver = null;
let cleanupScheduled = false;

function destroyChartInstance(element, { clear = true } = {}) {
  const instance = element ? chartInstances.get(element) : null;
  if (instance) {
    try {
      instance.destroy();
    } catch {
      // A remoção do DOM pode ocorrer enquanto o ApexCharts finaliza o render.
      // Remover o registro ainda impede que uma instância inválida seja reutilizada.
    } finally {
      chartInstances.delete(element);
    }
  }
  if (clear && element) element.replaceChildren();
}

export function destroyDisconnectedCharts() {
  for (const element of chartDefinitions.keys()) {
    if (!element.isConnected) {
      chartDefinitions.delete(element);
      destroyChartInstance(element, { clear: false });
    }
  }
}

export function syncChartVisibility() {
  destroyDisconnectedCharts();
  // spec: frontend-v2/frontend-fundacao-v2 v1.0 — critérios 26 e 27
  for (const [element, definition] of [...chartDefinitions]) {
    if (element.closest("[hidden]")) {
      if (chartInstances.has(element)) destroyChartInstance(element);
    } else if (!chartInstances.has(element)) {
      renderChart(element, definition.options, definition.presentation);
    }
  }
}

export function destroyAllCharts() {
  for (const element of chartDefinitions.keys()) destroyChartInstance(element);
  chartDefinitions.clear();
}

function scheduleDisconnectedChartCleanup() {
  if (cleanupScheduled) return;
  cleanupScheduled = true;
  queueMicrotask(() => {
    cleanupScheduled = false;
    syncChartVisibility();
  });
}

function ensureChartCleanupObserver() {
  if (cleanupObserver || !globalThis.MutationObserver || !document.documentElement) return;
  cleanupObserver = new MutationObserver(scheduleDisconnectedChartCleanup);
  cleanupObserver.observe(document.documentElement, {
    childList: true, subtree: true, attributes: true, attributeFilter: ["hidden"],
  });
}

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
  chartDefinitions.delete(element);
  destroyChartInstance(element);
}

export function renderChart(element, options, { emptyMessage = "Sem dados para exibir." } = {}) {
  if (!element) return null;
  ensureChartCleanupObserver();
  destroyDisconnectedCharts();
  destroyChart(element);
  if (!element.isConnected) return null;
  chartDefinitions.set(element, { options, presentation: { emptyMessage } });
  if (element.closest("[hidden]")) return null;
  if (!globalThis.ApexCharts) {
    chartDefinitions.delete(element);
    element.innerHTML = `<p class="muted-copy" role="status">${emptyMessage}</p>`;
    return null;
  }

  const instance = new globalThis.ApexCharts(element, {
    ...options,
    chart: {
      background: "transparent",
      foreColor: cssToken("--muted", "#6b7280"),
      fontFamily: "inherit",
      toolbar: { show: false },
      zoom: { enabled: false },
      parentHeightOffset: 0,
      ...(options.chart || {}),
      // spec: frontend-v2/frontend-fundacao-v2 v1.0 — critério 25
      // Apply last so a view cannot accidentally restore expensive transitions.
      animations: {
        enabled: false,
        animateGradually: { enabled: false },
        dynamicAnimation: { enabled: false },
      },
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
    chartDefinitions.delete(element);
    destroyChartInstance(element, { clear: false });
    element.innerHTML = `<p class="muted-copy" role="status">${emptyMessage}</p>`;
  });
  return instance;
}
