// Fatias limitadas por conta/mês; mutações invalidam também respostas em andamento.
export function createTransactionSliceLoader({ state, api, fetchAllListed, ensureSelectedAccount, maxAgeMs = 30_000, maxEntries = 4 }) {
  const snapshots = new Map();
  const requests = new Map();
  let revision = 0;

  function apply(snapshot) {
    state.accountTransactions = snapshot.transactions;
    state.balanceProjection = snapshot.projection;
    state.transactionSliceLoading = false;
    state.transactionSliceError = "";
  }

  async function load({ force = false, preserveRows = false } = {}) {
    ensureSelectedAccount();
    const accountId = String(state.selectedAccountId || "");
    const month = state.transactionMonth;
    const key = `${accountId}:${month}`;
    if (force) markDirty();
    const loadRevision = revision;
    const isCurrent = () => revision === loadRevision && key === `${state.selectedAccountId || ""}:${state.transactionMonth}`;
    if (!accountId) {
      apply({ transactions: [], projection: null });
      return;
    }
    const snapshot = snapshots.get(key);
    if (snapshot && Date.now() - snapshot.loadedAt < maxAgeMs) {
      state.transactionSliceKey = key;
      snapshots.delete(key);
      snapshots.set(key, snapshot);
      apply(snapshot);
      return;
    }
    const sameKey = state.transactionSliceKey === key;
    if (!sameKey) {
      state.accountTransactions = [];
      state.balanceProjection = null;
    }
    state.transactionSliceKey = key;
    state.transactionSliceLoading = !(preserveRows && sameKey);
    state.balanceProjection = null;
    state.transactionSliceError = "";
    let entry = requests.get(key);
    if (!entry || entry.revision !== revision) {
      entry = { revision };
      entry.promise = Promise.all([
        fetchAllListed(`/api/transactions?month=${encodeURIComponent(month)}&account_id=${encodeURIComponent(accountId)}`, "transactions"),
        api(`/api/balance-projection?month=${encodeURIComponent(month)}&account_id=${encodeURIComponent(accountId)}`),
      ]).then(([transactions, projection]) => {
        const result = { transactions, projection, loadedAt: Date.now() };
        if (revision === loadRevision) {
          snapshots.delete(key);
          snapshots.set(key, result);
          while (snapshots.size > maxEntries) snapshots.delete(snapshots.keys().next().value);
        }
        return result;
      }).finally(() => {
        if (requests.get(key) === entry) requests.delete(key);
      });
      requests.set(key, entry);
    }
    try {
      const result = await entry.promise;
      if (isCurrent()) apply(result);
    } catch (error) {
      if (!isCurrent()) return;
      state.transactionSliceLoading = false;
      state.transactionSliceError = error.message;
      throw error;
    }
  }

  function markDirty() { revision += 1; snapshots.clear(); }
  function reset() {
    markDirty();
    requests.clear();
    state.transactionSliceKey = "";
    apply({ transactions: [], projection: null });
  }
  return { load, markDirty, reset, getRevision: () => revision };
}
