import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { hasPortfolioPresentation, canReusePortfolioSnapshot } from '../web/modules/portfolio-lifecycle.js';

const source = readFileSync(new URL('../web/modules/portfolio-view.js', import.meta.url), 'utf8');
function body(name) {
  const start = source.indexOf(`  function ${name}(`);
  const end = source.indexOf('\n  }', start) + 4;
  return source.slice(start, end);
}

test('old cached snapshots are rejected, including fresh and clean ones', () => {
  const state = { portfolio: { positions: [], summary: {} }, portfolioLoadedAt: 100, portfolioDirty: false };
  assert.equal(canReusePortfolioSnapshot(state, {}, 101), false);
  assert.equal(hasPortfolioPresentation(null), false);
  state.portfolio.presentation = { sections: {}, asset_groups: {}, compositions: {}, analysis: {}, allocation: [] };
  assert.equal(canReusePortfolioSnapshot(state, {}, 101), true);
  assert.equal(canReusePortfolioSnapshot(state, { force: true }, 101), false);
});

test('ten thousand portfolio rows remain lazy until the virtual window renders', () => {
  const positions = Array.from({ length: 10000 }, (_, id) => ({ id, sources: [] }));
  let rendered = 0;
  const rowsFor = new Function('portfolioAssetGroups', 'state', 'portfolioPositionRow',
    `${body('portfolioPositionRows')}; return portfolioPositionRows;`)(
    items => items.map(position => ({ positions: [position] })),
    { portfolioExpandedGroups: new Set() }, () => { rendered++; return '<tr></tr>'; });
  const rows = rowsFor(positions);
  assert.equal(rendered, 0);
  rows.slice(0, 18).forEach(render => render());
  assert.equal(rendered, 18);
});

test('expanded source rows also defer copies and HTML until visible', () => {
  let rendered = 0, copied = 0;
  const position = { sources: Array.from({ length: 1000 }, (_, id) => ({ id })) };
  const rowsFor = new Function('portfolioAssetGroups', 'state', 'portfolioPositionRow', 'portfolioSourcePosition',
    `${body('portfolioPositionRows')}; return portfolioPositionRows;`)(
    () => [{ key: 'a', positions: [position] }], { portfolioExpandedGroups: new Set(['a']) },
    () => { rendered++; return ''; }, () => { copied++; return {}; });
  const rows = rowsFor([position]);
  assert.equal(copied, 0);
  assert.equal(rendered, 0);
  rows.slice(0, 10).forEach(render => render());
  assert.equal(copied, 9);
  assert.equal(rendered, 10);
});

test('failed loads are latched before cockpit can request again', () => {
  assert.ok(source.includes('state.portfolioError = portfolioErrorMessage'));
  const cockpit = readFileSync(new URL('../web/modules/cockpit-view.js', import.meta.url), 'utf8');
  const renderer = cockpit.slice(cockpit.indexOf('  function renderCockpitPortfolioByType()'));
  assert.ok(renderer.indexOf('if (state.portfolioError)') < renderer.indexOf('loadPortfolio()'));
  assert.ok(source.includes('destroyVirtualLists(portfolioPositions)'));
});
