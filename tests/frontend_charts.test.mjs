import test from "node:test";
import assert from "node:assert/strict";
import { renderChart, destroyChart, destroyDisconnectedCharts, syncChartVisibility, destroyAllCharts } from "../web/modules/chart-adapter.js";

globalThis.document = { documentElement: {} };
globalThis.getComputedStyle = () => ({ getPropertyValue: () => "" });
let observerCallback, observerOptions, observerCount = 0;
globalThis.MutationObserver = class {
  constructor(callback) { observerCallback = callback; observerCount++; }
  observe(root, options) { observerOptions = options; }
};
let active = new Set();
class FakeChart {
  constructor(element, options) {
    this.options = options;
    this.element = element;
    this.destroyCount = 0;
    active.add(this);
  }
  render() { return Promise.resolve(); }
  destroy() { this.destroyCount++; active.delete(this); }
}
globalThis.ApexCharts = FakeChart;
const element = () => ({ isConnected: true, hiddenAncestor: null,
  closest() { return this.hiddenAncestor; }, replaceChildren() {} });

test("hidden views suspend instances and restore only latest local data", () => {
  const target = element();
  const first = renderChart(target, { series: [{ data: [1] }] });
  for (let index = 0; index < 100; index++) {
    target.hiddenAncestor = {};
    syncChartVisibility();
    assert.equal(active.size, 0);
    assert.equal(renderChart(target, { series: [{ data: [index] }] }), null);
    assert.equal(active.size, 0);
    target.hiddenAncestor = null;
    syncChartVisibility();
    assert.equal(active.size, 1);
    assert.deepEqual([...active][0].options.series, [{ data: [index] }]);
    const restored = [...active][0];
    syncChartVisibility();
    assert.equal([...active][0], restored);
  }
  assert.equal(first.destroyCount, 1);
  destroyAllCharts();
});

test("removed hidden charts and session reset cannot revive previous data", () => {
  const removed = element(), logout = element();
  removed.hiddenAncestor = logout.hiddenAncestor = {};
  renderChart(removed, { series: [{ data: [99] }] });
  renderChart(logout, { series: [{ data: [100] }] });
  removed.isConnected = false;
  destroyDisconnectedCharts();
  removed.isConnected = true;
  removed.hiddenAncestor = null;
  syncChartVisibility();
  assert.equal(active.size, 0);
  destroyAllCharts();
  logout.hiddenAncestor = null;
  syncChartVisibility();
  assert.equal(active.size, 0);
  removed.isConnected = false;
  assert.equal(renderChart(removed, {}), null);
});

test("late rejection from suspended instance cannot remove its replacement", async () => {
  const target = element();
  let reject;
  globalThis.ApexCharts = class extends FakeChart {
    render() { return new Promise((_, no) => { reject = no; }); }
  };
  const old = renderChart(target, {});
  const rejectOld = reject;
  target.hiddenAncestor = {};
  syncChartVisibility();
  globalThis.ApexCharts = FakeChart;
  target.hiddenAncestor = null;
  syncChartVisibility();
  const fresh = [...active][0];
  rejectOld(new Error("render ended after suspension"));
  await Promise.resolve();
  assert.equal(old.destroyCount, 1);
  assert.equal([...active][0], fresh);
  destroyAllCharts();
});

test("single observer reacts to ancestor hidden changes without another view render", async () => {
  const target = element();
  renderChart(target, {});
  target.hiddenAncestor = {};
  observerCallback();
  await Promise.resolve();
  assert.equal(active.size, 0);
  target.hiddenAncestor = null;
  observerCallback();
  await Promise.resolve();
  assert.equal(active.size, 1);
  assert.equal(observerCount, 1);
  assert.deepEqual(observerOptions.attributeFilter, ["hidden"]);
  destroyAllCharts();
});

test("animations disabled regardless of motion preference and view overrides", () => {
  for (const reduced of [true, false]) {
    globalThis.matchMedia = () => ({ matches: reduced });
    const target = element();
    const formatter = value => `${value}%`;
    const options = { chart: { type: "line", height: 310,
      animations: { enabled: true, animateGradually: { enabled: true }, dynamicAnimation: { enabled: true } } },
      series: [{ name: "BRL", data: [1, -2, 3] }],
      tooltip: { y: { formatter } }, legend: { show: false },
    };
    const chart = renderChart(target, options);
    assert.deepEqual(chart.options.chart.animations, {
      enabled: false, animateGradually: { enabled: false }, dynamicAnimation: { enabled: false },
    });
    assert.equal(chart.options.series, options.series);
    assert.equal(chart.options.tooltip.y.formatter, formatter);
    assert.equal(chart.options.legend.show, false);
    assert.equal(chart.options.chart.height, 310);
    assert.equal(options.chart.animations.enabled, true);
    destroyChart(target);
  }
});

test("repeated rendering, closing and removal do not retain chart registrations", () => {
  for (let cycle = 0; cycle < 100; cycle++) {
    const target = element();
    const first = renderChart(target, {});
    const second = renderChart(target, {});
    assert.equal(first.destroyCount, 1);
    assert.equal(active.size, 1);
    if (cycle % 2) {
      target.isConnected = false;
      destroyDisconnectedCharts();
    } else {
      destroyChart(target);
    }
    assert.equal(second.destroyCount, 1);
    assert.equal(active.size, 0);
  }
});

test("disabled tooltips stay disabled and explicit destruction is idempotent", () => {
  const target = element();
  const chart = renderChart(target, { tooltip: { enabled: false } });
  assert.equal(chart.options.tooltip.enabled, false);
  destroyChart(target);
  destroyChart(target);
  destroyDisconnectedCharts();
  assert.equal(chart.destroyCount, 1);
  assert.equal(active.size, 0);
});
