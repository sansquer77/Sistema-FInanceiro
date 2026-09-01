// Request coordination only: financial arithmetic belongs to the backend.
export function createPortfolioPreview(api, onError) {
  const requests = new Map();

  function request(form, body, apply) {
    const previous = requests.get(form);
    if (previous) clearTimeout(previous.timer);
    const entry = { body, apply, pending: previous?.pending || null };
    requests.set(form, entry);
    const button = form.querySelector('[type="submit"]');
    if (button) button.disabled = true;
    const field = form.querySelector('input:not([readonly])');
    field?.setCustomValidity("Aguarde o cálculo da prévia.");
    // Do not display results from a previous edit while recomputing.
    for (const name of ["gross_amount", "amount", "remaining_quantity"]) {
      if (body.kind === "redemption") form.elements[name].value = "";
    }
    entry.timer = setTimeout(async () => {
      if (entry.pending) await entry.pending.catch(() => {});
      if (requests.get(form) !== entry) return;
      if (!form.isConnected) { requests.delete(form); return; }
      entry.pending = api("/api/portfolio/preview", { method: "POST", body });
      try {
        const result = await entry.pending;
        if (requests.get(form) !== entry || !form.isConnected) return;
        field?.setCustomValidity("");
        apply(result);
        if (button) button.disabled = false;
      } catch (error) {
        if (requests.get(form) === entry && form.isConnected) {
          field?.setCustomValidity(error.message);
          onError(error);
        }
      } finally {
        if (requests.get(form) === entry) requests.delete(form);
      }
    }, 180);
  }

  function clear() {
    for (const entry of requests.values()) clearTimeout(entry.timer);
    requests.clear();
  }
  return { request, clear };
}
