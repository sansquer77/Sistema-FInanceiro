import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const coordinator = readFileSync(new URL('../web/modules/reports-view.js', import.meta.url), 'utf8');
const statement = readFileSync(new URL('../web/modules/report-statement.js', import.meta.url), 'utf8');
const evolution = readFileSync(new URL('../web/modules/report-evolution.js', import.meta.url), 'utf8');

test('reports facade composes statement and evolution exactly once outside render', () => {
  assert.match(coordinator, /createReportStatement\(\{/);
  assert.match(coordinator, /createReportEvolution\(\{/);
  assert.equal((coordinator.match(/createReportStatement\(\{/g) || []).length, 1);
  assert.equal((coordinator.match(/createReportEvolution\(\{/g) || []).length, 1);
  const render = coordinator.slice(coordinator.indexOf('  function renderReports()'), coordinator.indexOf('  function renderReportAccountOptions()'));
  assert.match(render, /statement\.invalidate\(\)/);
  assert.match(render, /statement\.renderStatementScopeOptions\(\)/);
  assert.match(render, /statement\.renderStatementReport\(\)/);
  assert.doesNotMatch(render, /createReport/);
});

test('extracted responsibilities do not leak back into the coordinator', () => {
  for (const name of ['renderStatementReport', 'statementCurrencyReport', 'loadEvolutionChart', 'drawEvolutionChart']) {
    assert.equal(coordinator.includes(`function ${name}(`), false);
  }
  assert.match(statement, /export function createReportStatement/);
  assert.match(evolution, /export function createReportEvolution/);
  assert.match(statement, /import \{ renderChart \} from "\.\/chart-adapter\.js"/);
  assert.match(statement, /data-statement-distribution-chart/);
  assert.match(statement, /data-statement-daily-chart/);
  assert.match(statement, /chart: \{ type: "donut", height: 190 \}/);
  assert.match(statement, /size: "72%"/);
  assert.match(statement, /name: \{ show: true, offsetY: -5, formatter: \(\) => "Total gasto" \}/);
  assert.match(statement, /formatter: \(\) => formatMoney\(section\.total, section\.currency\)/);
  assert.match(statement, /showAlways: true/);
  assert.match(statement, /fontSize: "11px"/);
  assert.match(statement, /chart: \{ type: "bar", height: 190 \}/);
  assert.doesNotMatch(statement, /<svg/);
  assert.doesNotMatch(statement, /statement-daily-bars/);
  assert.match(evolution, /destroyChart\(svgEl\)/);
});

test('trends creates the Apex container directly without a legacy financial SVG', () => {
  const trends = readFileSync(new URL('../web/modules/trends-view.js', import.meta.url), 'utf8');
  assert.match(trends, /class="trends-apex-chart"/);
  assert.match(trends, /renderChart\(chartElement/);
  assert.doesNotMatch(trends, /legacySvg/);
  assert.doesNotMatch(trends, /<svg viewBox=/);
  assert.doesNotMatch(trends, /function buildTicks\(/);
  assert.doesNotMatch(trends, /function monthlyTooltip\(/);
});
