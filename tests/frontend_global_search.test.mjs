import test from "node:test";
import assert from "node:assert/strict";

globalThis.document = { addEventListener() {}, activeElement: null };

const { registerGlobalSearch } = await import("../web/modules/global-search.js");

function element() {
  const handlers = new Map();
  return {
    handlers,
    value: "",
    innerHTML: "",
    addEventListener(type, handler) { handlers.set(type, handler); },
    emit(type, event = {}) { return handlers.get(type)?.({ target: this, ...event }); },
    focus() {},
    closest() { return null; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
    isConnected: true,
  };
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

test("global search discards stale history and does not read monthly transaction state", async () => {
  const trigger = element();
  const input = element();
  const results = element();
  const closeButton = element();
  const dialog = element();
  dialog.open = false;
  dialog.showModal = () => { dialog.open = true; };
  dialog.close = () => { dialog.open = false; };
  const requests = [];
  const api = (url) => {
    const pending = deferred();
    requests.push({ url, pending });
    return pending.promise;
  };
  const state = { transactions: [{ description: "Não deve aparecer" }], cardTransactions: [] };

  registerGlobalSearch({
    state,
    elements: { trigger, dialog, input, results, closeButton },
    viewTitles: {},
    normalizeSearch: (value) => String(value || "").toLowerCase(),
    escapeHtml: (value) => String(value || ""),
    api,
    onNavigate() {},
  });
  trigger.emit("click");
  input.value = "antigo";
  input.emit("input");
  await new Promise((resolve) => setTimeout(resolve, 210));
  input.value = "novo";
  input.emit("input");
  await new Promise((resolve) => setTimeout(resolve, 210));
  assert.equal(requests.length, 2);

  requests[1].pending.resolve({ results: [{ kind: "account_transaction", id: 2, title: "Resultado novo", month: "2026-08" }] });
  await Promise.resolve();
  assert.match(results.innerHTML, /Resultado novo/);
  requests[0].pending.resolve({ results: [{ kind: "account_transaction", id: 1, title: "Resultado antigo", month: "2020-01" }] });
  await Promise.resolve();
  assert.doesNotMatch(results.innerHTML, /Resultado antigo|Não deve aparecer/);
});
