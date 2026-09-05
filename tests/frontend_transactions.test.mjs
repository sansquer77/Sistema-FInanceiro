import test from "node:test";
import assert from "node:assert/strict";
import { createTransactionSliceLoader } from "../web/modules/transaction-slice-loader.js";
import { createTransactionReconciliation } from "../web/modules/transaction-reconciliation.js";
import { createTransactionList } from "../web/modules/transaction-list.js";
import { createTransactionRefresh } from "../web/modules/transaction-refresh.js";

function refreshFixture() {
  const f = fixture();
  f.state.transactionSliceKey = "A:2026-08";
  f.state.user = { id: 1 };
  f.state.transactions = f.state.accountTransactions = [{ id: 1, amount: "10" }];
  const auxiliary = [], frames = [], errors = [];
  const request = () => { const d = deferred(); auxiliary.push(d); return d.promise; };
  const refresh = createTransactionRefresh({ state: f.state, loader: f.loader,
    api: request, fetchAllListed: request,
    render: () => frames.push(structuredClone(f.state)), renderAuxiliary() {},
    markPortfolioDirty() {}, reportError: message => errors.push(message),
  });
  return { ...f, refresh, auxiliary, frames, errors };
}

test("edição aparece antes da projeção e não espera histórico global", async () => {
  const f = refreshFixture();
  const pending = f.refresh({ transaction: { id: 1, amount: "25" } });
  assert.equal(f.frames[0].accountTransactions[0].amount, "25");
  assert.equal(f.state.transactionSliceLoading, false);
  assert.equal(f.state.balanceProjection, null);
  f.calls[0].resolve([{ id: 1, amount: "25" }, { id: 2, amount: "25" }]);
  f.calls[1].resolve({ balances: {} });
  await pending;
  assert.equal(f.state.accountTransactions.length, 2); // cascade from the server
  assert.equal(f.auxiliary.length, 2); // still unresolved; refresh already returned
  f.auxiliary[0].resolve({ accounts: [] });
  f.auxiliary[1].resolve(f.state.accountTransactions);
});

test("exclusão aplica confirmação e falha de recarga não vira falha de gravação", async () => {
  const f = refreshFixture();
  const pending = f.refresh({ deletedId: 1 });
  assert.deepEqual(f.frames[0].accountTransactions, []);
  f.calls[0].reject(new Error("offline"));
  f.calls[1].resolve({});
  await pending;
  assert.match(f.errors[0], /Operação salva/);
  f.auxiliary[0].reject(new Error("auxiliary offline"));
  f.auxiliary[1].resolve([]);
  await new Promise(resolve => setImmediate(resolve));
  assert.match(f.errors[1], /Operação salva.*auxiliares/);
});

test("resposta auxiliar anterior à nova mutação ou sessão é descartada", async () => {
  for (const invalidate of [f => f.loader.markDirty(), f => { f.state.user = { id: 2 }; }]) {
    const f = refreshFixture();
    const pending = f.refresh({ transaction: { id: 1, amount: "25" } });
    f.finish(0, 1);
    await pending;
    invalidate(f);
    f.state.transactions = [{ id: "newer" }];
    f.auxiliary[0].resolve({ accounts: [{ id: "stale" }] });
    f.auxiliary[1].resolve([{ id: "stale" }]);
    await new Promise(resolve => setImmediate(resolve));
    assert.deepEqual(f.state.transactions, [{ id: "newer" }]);
  }
});

test("mudança de mês independe do anterior e restaura cache recente", async () => {
  const f = fixture();
  const august = f.loader.load();
  f.state.transactionMonth = "2026-09";
  const september = f.loader.load();
  f.finish(2, "September");
  await september;
  f.finish(0, "August");
  await august;
  assert.equal(f.state.accountTransactions[0].id, "September");
  f.state.transactionMonth = "2026-08";
  await f.loader.load();
  assert.equal(f.calls.length, 4);
  assert.equal(f.state.accountTransactions[0].id, "August");
});

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function fixture(options = {}) {
  const state = { selectedAccountId: "A", transactionMonth: "2026-08", accountTransactions: [], balanceProjection: null };
  const calls = [];
  const request = (path) => {
    const value = deferred();
    calls.push({ path, ...value });
    return value.promise;
  };
  const loader = createTransactionSliceLoader({ state, api: request, fetchAllListed: request, ensureSelectedAccount() {}, ...options });
  const finish = (offset, id) => {
    calls[offset].resolve([{ id }]);
    calls[offset + 1].resolve({ id });
  };
  return { state, calls, loader, finish };
}

test("troca de conta não espera a anterior nem aceita sua resposta atrasada", async () => {
  const f = fixture();
  const first = f.loader.load();
  f.state.selectedAccountId = "B";
  const second = f.loader.load();
  assert.equal(f.calls.length, 4);
  f.finish(2, "B");
  await second;
  f.finish(0, "A");
  await first;
  assert.equal(f.state.accountTransactions[0].id, "B");
  f.state.selectedAccountId = "A";
  await f.loader.load();
  assert.equal(f.calls.length, 4);
  assert.equal(f.state.accountTransactions[0].id, "A");
});

test("mesma chave compartilha requisição em andamento", async () => {
  const f = fixture();
  const a = f.loader.load(), b = f.loader.load();
  assert.equal(f.calls.length, 2);
  f.finish(0, "A");
  await Promise.all([a, b]);
});

test("forçar após mutação não reutiliza resposta anterior", async () => {
  const f = fixture();
  const old = f.loader.load();
  f.loader.markDirty();
  const fresh = f.loader.load({ force: true });
  f.finish(2, "confirmed");
  await fresh;
  f.finish(0, "stale");
  await old;
  assert.equal(f.state.accountTransactions[0].id, "confirmed");
});

test("reset impede reaproveitamento de resposta da sessão anterior", async () => {
  const f = fixture();
  const old = f.loader.load();
  f.loader.reset();
  f.finish(0, "stale");
  await old;
  assert.deepEqual(f.state.accountTransactions, []);
  const fresh = f.loader.load();
  assert.equal(f.calls.length, 4);
  f.finish(2, "new-session");
  await fresh;
});

test("cache limitado remove a chave menos recente", async () => {
  const f = fixture({ maxEntries: 2 });
  for (const [index, key] of ["A", "B", "C"].entries()) {
    f.state.selectedAccountId = key;
    const pending = f.loader.load();
    f.finish(index * 2, key);
    await pending;
  }
  f.state.selectedAccountId = "A";
  const again = f.loader.load();
  assert.equal(f.calls.length, 8);
  f.finish(6, "A");
  await again;
});

test("cache expirado é revalidado e falha permite nova tentativa", async () => {
  const f = fixture({ maxAgeMs: 0 });
  const first = f.loader.load();
  f.finish(0, "A");
  await first;
  const failed = f.loader.load();
  f.calls[2].reject(new Error("offline"));
  f.calls[3].resolve({});
  await assert.rejects(failed, /offline/);
  assert.equal(f.state.transactionSliceLoading, false);
  const retry = f.loader.load();
  f.finish(4, "recovered");
  await retry;
  assert.equal(f.state.transactionSliceError, "");
});

test("falha de conta anterior não bloqueia seleção atual", async () => {
  const f = fixture();
  const old = f.loader.load();
  f.state.selectedAccountId = "B";
  const current = f.loader.load();
  f.calls[0].reject(new Error("old-error"));
  f.calls[1].resolve({});
  await old;
  f.finish(2, "B");
  await current;
  assert.equal(f.state.transactionSliceError, "");
});

test("conciliação reflete resposta antes da projeção e impede clique duplicado", async () => {
  const mutation = deferred(), projection = deferred();
  const row = { id: 1, reconciled_at: null };
  const state = { accountTransactions: [row], transactions: [row] };
  let calls = 0, renders = 0;
  const controller = createTransactionReconciliation({
    state, api: () => { calls++; return mutation.promise; },
    markDirty() {}, markPortfolioDirty() {}, render() { renders++; },
    loadSlice: () => projection.promise, reportError: assert.fail,
  });
  const pending = controller.toggle(1, true);
  await controller.toggle(1, true);
  assert.equal(calls, 1);
  assert.equal(controller.isPending(1), true);
  mutation.resolve({ transaction: { ...row, reconciled_at: "confirmed" } });
  await new Promise(setImmediate);
  assert.equal(state.accountTransactions[0].reconciled_at, "confirmed");
  assert.equal(state.transactions[0].reconciled_at, "confirmed");
  assert.ok(renders >= 2);
  assert.equal(state.cockpitLoadedMonth, "");
  projection.resolve();
  await pending;
  assert.equal(controller.isPending(1), false);
});

test("falha ao gravar não altera estado confirmado", async () => {
  const row = { id: 1, reconciled_at: null };
  const state = { accountTransactions: [row], transactions: [row] };
  const errors = [];
  const controller = createTransactionReconciliation({
    state, api: async () => { throw new Error("falhou"); },
    markDirty: assert.fail, markPortfolioDirty: assert.fail, render() {},
    loadSlice: assert.fail, reportError: (message) => errors.push(message),
  });
  await controller.toggle(1, true);
  assert.equal(state.accountTransactions[0].reconciled_at, null);
  assert.deepEqual(errors, ["falhou"]);
  assert.equal(controller.isPending(1), false);
});

test("desconciliação permanece salva mesmo se projeção falhar", async () => {
  const row = { id: 1, reconciled_at: "before" };
  const state = { accountTransactions: [row], transactions: [row] };
  const errors = [];
  const controller = createTransactionReconciliation({
    state, api: async () => ({ transaction: { ...row, reconciled_at: null } }),
    markDirty() {}, markPortfolioDirty() {}, render() {},
    loadSlice: async () => { throw new Error("offline"); },
    reportError: (message) => errors.push(message),
  });
  await controller.toggle(1, false);
  assert.equal(state.accountTransactions[0].reconciled_at, null);
  assert.match(errors[0], /Conciliação salva/);
});

test("lista aplica filtro e contador após confirmação e não mostra saldo antigo durante troca", () => {
  const element = () => ({ value: "", textContent: "", hidden: false, addEventListener() {}, setAttribute() {}, classList: { toggle() {} } });
  const elements = Object.fromEntries(["transactionAccount", "transactionMonthLabel", "transactionSearch",
    "clearTransactionSearchButton", "transactionContextCount", "currentBalanceSummary",
    "forecastBalanceLabel", "forecastBalanceSummary", "transactionList", "transactionBalanceHistoryChart"].map((key) => [key, element()]));
  elements.transactionStatusFilterButtons = [];
  const state = { selectedAccountId: "A", transactionMonth: "2026-08", transactionStatusFilter: "pending",
    accountTransactions: [{ id: 1, date: "2026-08-01", reconciled_at: null }], accounts: [] };
  let visible;
  const list = createTransactionList({
    state, elements, formatMonthShortLabel: String, formatCurrencySummary: () => "100",
    todayLocalDateValue: () => "2026-08-31", monthEndDate: () => "2026-08-31",
    ensureSelectedAccount() {}, selectedAccountTransactions: (rows) => rows, getBalanceUntil: () => new Map(),
    accountHasPreferredCardForecast: () => false, balanceChart: { render() {} },
    renderCollection: (_, rows) => { visible = rows; }, matchesSearch: () => true,
  });
  list.render();
  assert.equal(visible.length, 1);
  state.accountTransactions = [{ ...state.accountTransactions[0], reconciled_at: "confirmed" }];
  list.render();
  assert.equal(visible.length, 0);
  assert.match(elements.transactionContextCount.textContent, /1 conciliado/);
  state.transactionSliceLoading = true;
  list.render();
  assert.equal(elements.currentBalanceSummary.textContent, "—");
  assert.equal(elements.transactionBalanceHistoryChart.hidden, true);
});
