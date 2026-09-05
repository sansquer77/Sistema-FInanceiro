export function createTransactionReconciliation({ state, api, markDirty, loadSlice, render, markPortfolioDirty, reportError }) {
  const pending = new Set();
  async function toggle(id, reconciled) {
    const key = String(id);
    const userId = state.user?.id;
    if (pending.has(key)) return;
    pending.add(key);
    render();
    try {
      const { transaction } = await api(`/api/transactions/${id}/reconciliation`, {
        method: "PUT", body: { reconciled },
      });
      if (state.user?.id !== userId) return;
      markDirty();
      for (const field of ["accountTransactions", "transactions"]) {
        state[field] = state[field].map((row) => String(row.id) === key ? transaction : row);
      }
      state.cockpitLoadedMonth = "";
      markPortfolioDirty();
      render();
      try {
        await loadSlice({ force: true });
      } catch (error) {
        reportError(`Conciliação salva. Não foi possível atualizar os saldos: ${error.message}`);
      }
    } catch (error) {
      reportError(error.message);
    } finally {
      pending.delete(key);
      render();
    }
  }
  return { toggle, isPending: (id) => pending.has(String(id)) };
}
