import test from 'node:test';
import assert from 'node:assert/strict';
import { createPortfolioPreview } from '../web/modules/portfolio-preview.js';
const tick = () => new Promise(resolve => setTimeout(resolve, 210));
function form() {
  const button = { disabled: false };
  const input = { validity: '', setCustomValidity(value) { this.validity = value; } };
  return { isConnected: true, button, input, querySelector(selector) {
    return selector === '[type="submit"]' ? button : input;
  }, elements: Object.fromEntries(['gross_amount', 'amount', 'remaining_quantity'].map(key => [key, { value: 'old' }])) };
}

test('preview debounces edits, disables confirmation and discards stale results', async () => {
  const target = form();
  const calls = [], values = [];
  const preview = createPortfolioPreview((path, options) => new Promise(resolve => calls.push({ path, options, resolve })), assert.fail);
  preview.request(target, { kind: 'redemption', quantity: '1' }, value => values.push(value));
  assert.equal(target.button.disabled, true);
  assert.equal(target.elements.amount.value, '');
  await tick();
  preview.request(target, { kind: 'redemption', quantity: '2' }, value => values.push(value));
  preview.request(target, { kind: 'redemption', quantity: '3' }, value => values.push(value));
  await tick();
  assert.equal(calls.length, 1);
  calls[0].resolve('stale');
  await tick();
  assert.deepEqual(values, []);
  assert.equal(calls.length, 2);
  assert.equal(calls[1].options.body.quantity, '3');
  calls[1].resolve('current');
  await tick();
  assert.deepEqual(values, ['current']);
  assert.equal(target.button.disabled, false);
  assert.equal(target.input.validity, '');
  preview.clear();
});

test('failure blocks confirmation; a later edit can recover', async () => {
  const target = form();
  const errors = [];
  let fail = true;
  const preview = createPortfolioPreview(async () => { if (fail) throw new Error('offline'); return {}; }, error => errors.push(error.message));
  preview.request(target, { kind: 'goals' }, () => {});
  await tick();
  assert.equal(target.button.disabled, true);
  assert.deepEqual(errors, ['offline']);
  fail = false;
  preview.request(target, { kind: 'goals' }, () => {});
  await tick();
  assert.equal(target.button.disabled, false);
});

test('leaving view or closing modal prevents late presentation', async () => {
  const target = form();
  let resolve;
  const values = [];
  const preview = createPortfolioPreview(() => new Promise(done => { resolve = done; }), assert.fail);
  preview.request(target, { kind: 'goals' }, value => values.push(value));
  await tick();
  preview.clear();
  resolve({});
  await tick();
  assert.deepEqual(values, []);
  target.isConnected = false;
  preview.request(target, { kind: 'goals' }, assert.fail);
  await tick();
  preview.clear();
});
