export function registerImportsView({
  state,
  elements,
  upload,
  setFormBusy,
  setMessage,
  escapeHtml,
  onImportCompleted = async () => {},
}) {
  const {
    importForm,
    importTarget,
    importAccount,
    importAccountLabel,
    importCreditCard,
    importCardLabel,
    downloadImportTemplateButton,
    importMessage,
    importResult,
  } = elements;

  importForm.addEventListener("submit", handleImportSubmit);
  importTarget.addEventListener("change", renderImportTargets);
  downloadImportTemplateButton.addEventListener("click", downloadImportTemplate);

  async function handleImportSubmit(event) {
    event.preventDefault();
    setMessage(importMessage, "");
    importResult.innerHTML = "";
    const target = importTarget.value;
    if (target === "account" && state.accounts.length === 0) {
      setMessage(importMessage, "Cadastre uma conta antes de importar lançamentos.", "error");
      return;
    }
    if (target === "card" && state.creditCards.length === 0) {
      setMessage(importMessage, "Cadastre um cartão antes de importar lançamentos.", "error");
      return;
    }
    const data = new FormData(importForm);
    data.set("target", target);
    data.set("target_id", target === "card" ? importCreditCard.value : importAccount.value);
    setFormBusy(importForm, true);
    try {
      const response = await upload("/api/import/system-template", data);
      importForm.reset();
      importTarget.value = target;
      renderImportTargets();
      await onImportCompleted();
      renderImportResult(response);
      setMessage(importMessage, `${response.imported} lançamento(s) importado(s).`, "success");
    } catch (error) {
      setMessage(importMessage, error.message, "error");
    } finally {
      setFormBusy(importForm, false);
    }
  }

  function downloadImportTemplate() {
    const target = importTarget.value || "account";
    window.location.href = `/api/import/template?target=${encodeURIComponent(target)}`;
  }

  function renderImportTargets() {
    const isCard = importTarget.value === "card";
    importAccountLabel.hidden = isCard;
    importCardLabel.hidden = !isCard;
    importAccount.disabled = isCard;
    importCreditCard.disabled = !isCard;
    importAccount.name = isCard ? "" : "target_id";
    importCreditCard.name = isCard ? "target_id" : "";
    importAccount.innerHTML = state.accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("") || '<option value="">Cadastre uma conta</option>';
    importCreditCard.innerHTML = state.creditCards.map((card) => (
      `<option value="${card.id}">${escapeHtml(card.name)} (${escapeHtml(card.currency)})</option>`
    )).join("") || '<option value="">Cadastre um cartão</option>';
    importForm.querySelector('button[type="submit"]').disabled = isCard ? state.creditCards.length === 0 : state.accounts.length === 0;
  }

  function renderImportResult(result) {
    const errors = result.errors || [];
    importResult.innerHTML = `
      <div class="import-summary">
        <div><span>Total lido</span><strong>${result.total_rows}</strong></div>
        <div><span>Importados</span><strong>${result.imported}</strong></div>
        <div><span>Ignorados</span><strong>${result.skipped}</strong></div>
      </div>
      ${errors.length ? `
        <div class="import-errors">
          ${errors.map((error) => `
            <article>
              <strong>Linha ${error.row}</strong>
              <span>${escapeHtml(error.description || "Sem descrição")}</span>
              <p>${escapeHtml(error.reason)}</p>
            </article>
          `).join("")}
        </div>
      ` : '<div class="empty-state compact">Nenhuma linha ignorada.</div>'}
    `;
  }

  return {
    renderImportTargets,
    renderImportResult,
  };
}
