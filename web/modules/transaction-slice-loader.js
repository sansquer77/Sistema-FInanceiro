import { createLoadPolicy } from "./load-policy.js";

export function createTransactionSliceLoader({ state, api, fetchAllListed, ensureSelectedAccount }) {
  const policy = createLoadPolicy();

  async function load({ force = false, bypassPolicy = false } = {}) {
    ensureSelectedAccount();
    const accountId = String(state.selectedAccountId || "");
    const month = state.transactionMonth;
    if (!accountId) {
      state.accountTransactions = [];
      state.balanceProjection = null;
      return;
    }
    if (!bypassPolicy) {
      return policy.run(() => load({ force, bypassPolicy: true }), { force, key: `${accountId}:${month}` });
    }
    const requestId = ++state.transactionSliceRequestId;
    const [transactions, projection] = await Promise.all([
      fetchAllListed(`/api/transactions?month=${encodeURIComponent(month)}&account_id=${encodeURIComponent(accountId)}`, "transactions"),
      api(`/api/balance-projection?month=${encodeURIComponent(month)}&account_id=${encodeURIComponent(accountId)}`),
    ]);
    if (requestId !== state.transactionSliceRequestId || month !== state.transactionMonth
      || accountId !== String(state.selectedAccountId || "")) return;
    state.accountTransactions = transactions;
    state.balanceProjection = projection;
  }

  return { load, markDirty: policy.markDirty, reset: policy.reset };
}
