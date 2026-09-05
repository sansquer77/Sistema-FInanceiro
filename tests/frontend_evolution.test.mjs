import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source = readFileSync(new URL('../web/modules/report-evolution.js', import.meta.url), 'utf8');
const start = source.indexOf('  async function loadEvolutionChart(');
const end = source.indexOf('  function formatChartValue(', start);
function harness() {
  const requests = [], paints = [], destroyed = [];
  const context = { categoryId: '1', color: 'red' };
  const total = {}, trend = {}, svg = {}, labels = {};
  const render = new Function('api', 'window', 'svgEl', 'xLabelsEl', 'chartTotal', 'chartTrend', 'destroyChart', 'drawEvolutionChart', 'currentEvolutionContext', `
    let evolutionRequestId = 0, currentEvolutionData = null;
    ${source.slice(start, end)}
    return { load: loadEvolutionChart, close() { evolutionRequestId++; currentEvolutionData = null; } };
  `)(url => new Promise((resolve,reject) => requests.push({url,resolve,reject})), {location:{origin:'http://local'}}, svg, labels, total, trend, () => destroyed.push(1), result => paints.push(result), context);
  return { ...render, requests, paints, destroyed, context, total, trend };
}
const result = { evolution: [], forecast: [], total_cents: 0, trend_percent: null };
test('stale period response and response after closing are discarded', async () => {
  const h = harness();
  const first = h.load(h.context, '3m');
  const second = h.load(h.context, '6m');
  h.requests[1].resolve(result); await second;
  h.requests[0].resolve(result); await first;
  assert.equal(h.paints.length, 1);
  const third = h.load(h.context, '12m'); h.close();
  h.requests[2].resolve(result); await third;
  assert.equal(h.paints.length, 1);
});
test('failure or legacy payload displays error, never recalculates or retries', async () => {
  for (const legacy of [false, true]) {
    const h = harness(); const pending = h.load(h.context, '3m');
    if (legacy) h.requests[0].resolve({evolution: []});
    else h.requests[0].reject(new Error('Offline'));
    await pending;
    assert.equal(h.total.textContent, 'Erro ao carregar');
    assert.equal(h.paints.length, 0);
    assert.equal(h.requests.length, 1);
    assert.equal(h.destroyed.length, 2);
  }
  assert.doesNotMatch(source, /function (smaForecast|localCategoryEvolution|addLocalEvolutionTransaction|evolutionMonths|moneyToCents)\(/);
});
