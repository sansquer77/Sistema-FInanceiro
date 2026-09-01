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
  assert.doesNotMatch(statement, /renderChart\(/);
  assert.match(evolution, /destroyChart\(svgEl\)/);
});
