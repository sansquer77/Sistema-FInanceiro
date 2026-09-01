// Refresh presentation after a confirmed write; never calculate financial values.
export function createTransactionRefresh({ state, api, fetchAllListed, loader, render,
  renderAuxiliary, markPortfolioDirty, reportError }) {
  return async function refresh({ transaction = null, deletedId = null } = {}) {
    loader.markDirty();
    const revision = loader.getRevision();
    const userId = state.user?.id;
    const current = () => userId === state.user?.id && revision === loader.getRevision();
    // spec: lancamentos/lancamentos v3.34 — resposta confirmada antes das recargas.
    for (const key of ["accountTransactions", "transactions"]) {
      const rows = (state[key] || []).filter(row => String(row.id) !== String(transaction?.id ?? deletedId));
      state[key] = transaction ? [...rows, transaction] : rows;
    }
    state.balanceProjection = null;
    state.transactionSliceLoading = false;
    state.transactionSliceError = "";
    state.cockpitLoadedMonth = "";
    markPortfolioDirty();
    render();
    try {
      await loader.load({ preserveRows: true });
    } catch (error) {
      if (current()) reportError(`Operação salva. Não foi possível atualizar os lançamentos: ${error.message}`);
    }
    if (!current()) return;
    render();
    // Other screens need the full dataset (including cascades), but the form does not.
    void Promise.all([
      api("/api/checking-accounts"), fetchAllListed("/api/transactions", "transactions"),
    ]).then(([accounts, transactions]) => {
      if (!current()) return;
      state.accounts = accounts.accounts || [];
      state.transactions = transactions;
      renderAuxiliary();
    }).catch(error => {
      if (current()) reportError(`Operação salva. Não foi possível atualizar os dados auxiliares: ${error.message}`);
    });
  };
}
