import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const source = readFileSync(new URL('../web/modules/report-statement.js', import.meta.url), 'utf8');
const start = source.indexOf('  async function renderStatementReport()');
const end = source.indexOf('\n  function paintStatementReport()', start);
function harness() {
  const requests = [], paints = [];
  const state = { reportMonth: '2026-02', reportTab: 'statement', statementScope: 'all' };
  const button = {}, content = {};
  const render = new Function('api', 'state', 'printStatementButton', 'reportContent', 'stateMarkup', 'paints', `
    let statementDebtRequestId = 0, statementDebts;
    function paintStatementReport() { paints.push(statementDebts); }
    ${source.slice(start, end)}
    return renderStatementReport;
  `)(url => new Promise((resolve, reject) => requests.push({ url, resolve, reject })), state, button, content, text => text, paints);
  return { requests, paints, state, button, content, render };
}

test('only the latest filtered response paints and unlocks printing', async () => {
  const h = harness();
  const first = h.render();
  h.state.reportMonth = '2026-03';
  const second = h.render();
  assert.equal(h.button.disabled, true);
  assert.match(h.requests[1].url, /month=2026-03/);
  h.requests[1].resolve({ sections: [{ currency: 'BRL', total: '2.00' }] });
  await second;
  h.requests[0].resolve({ sections: [{ currency: 'BRL', total: '1.00' }] });
  await first;
  assert.deepEqual(h.paints, [{ sections: [{ currency: 'BRL', total: '2.00' }] }]);
  assert.equal(h.button.disabled, false);
});

test('failure blocks printing without fallback calculations or automatic retry', async () => {
  const h = harness();
  const pending = h.render();
  h.requests[0].reject(new Error('Falha de consulta'));
  await pending;
  assert.equal(h.button.disabled, true);
  assert.equal(h.content.innerHTML, 'Falha de consulta');
  assert.equal(h.requests.length, 1);
  assert.equal(h.paints.length, 0);
});

test('switching report tabs discards the pending response', async () => {
  const h = harness();
  const pending = h.render();
  h.state.reportTab = 'tags';
  h.requests[0].resolve({ sections: [] });
  await pending;
  assert.equal(h.paints.length, 0);
});

test('empty statement and old backend payload cannot enable printing', async () => {
  for (const result of [{ sections: [] }, { by_currency: {} }]) {
    const h = harness();
    const pending = h.render();
    h.requests[0].resolve(result);
    await pending;
    assert.equal(h.button.disabled, true);
  }
});

test('selected owner IDs and currency are forwarded without local financial fallback', async () => {
  const h = harness();
  Object.assign(h.state, { statementScope: 'selected', statementAccountIds: ['1', '2'], statementCardIds: ['3'], statementCurrency: 'USD' });
  const pending = h.render();
  const query = new URL(h.requests[0].url, 'http://local').searchParams;
  assert.equal(query.get('account_ids'), '1,2');
  assert.equal(query.get('card_ids'), '3');
  assert.equal(query.get('currency'), 'USD');
  h.requests[0].resolve({ sections: [] });
  await pending;
  for (const name of ['sumStatementMoney', 'divideMoneyTotals', 'statementExpenseItems', 'statementCurrencySections', 'statementElapsedDays']) {
    assert.equal(source.includes(`function ${name}(`), false);
  }
  const statement = source.slice(source.indexOf('  function statementCurrencyReport('), source.indexOf('  function formatStatementDateTime('));
  assert.doesNotMatch(statement, /\.reduce\(|groupReportItems\(|reportRowPercent\(/);
});

test('statement renders the server model without reading financial state', () => {
  const start = source.indexOf('  function statementCurrencyReport(');
  const end = source.indexOf('  return {\n    renderStatementScopeOptions', start);
  const render = new Function('state', 'formatMoney', 'formatPercent', 'escapeHtml', 'formatDate', 'formatMonthLabel', 'chartColor', 'stateMarkup', 'reportItemClassification', `
    ${source.slice(start, end)}
    return statementCurrencyReport;
  `)({ reportMonth: '2026-02' }, (value, currency) => `${currency} ${value}`, value => `${value * 100}%`, String, String, String, () => '#000', String, item => item.category);
  const item = { description: 'Compra', category: 'Casa', subcategory: '', date: '2026-02-10', amount: '1.23', currency: 'USD', source: 'Conta', accountName: 'Conta USD', tags: ['Casa'] };
  const row = { label: 'Casa', amount: '1.23', share: 1 };
  const html = render({ currency: 'USD', items: [item], total: '1.23', average: '0.06', account_total: '1.23', card_total: '0.00', open_debts: '2.00', top_category: row, top_transaction: item, distribution: [row], daily: [{ date: '2026-02-10', amount: '1.23', ratio: 1 }], composition: { account: [row], card: [] } }, { label: 'Consolidado' }, new Date('2026-02-20'), 0);
  assert.match(html, /USD 1.23/);
  assert.match(html, /USD 0.06/);
  assert.match(html, /Conta USD/);
  assert.doesNotMatch(html, /undefined|NaN/);
});
