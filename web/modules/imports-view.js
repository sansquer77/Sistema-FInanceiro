import { stateMarkup } from "./dom-utils.js";

const PREVIEW_FIELDS = [
  "data",
  "tipo",
  "descricao_original",
  "descricao",
  "valor",
  "categoria",
  "subcategoria",
  "tags",
  "repeticao",
  "parcelas",
  "recorrencia",
  "media",
  "observacoes",
  "competencia_fatura",
  "conta_destino_id",
  "valor_destino",
  "cotacao_cambio",
  "cotacao_brl",
];

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
    importSource,
    importTarget,
    importAccount,
    importAccountLabel,
    importCreditCard,
    importCardLabel,
    downloadImportTemplateButton,
    importMessage,
    importResult,
  } = elements;

  const fileInput = importForm.querySelector('input[type="file"]');
  const fileLabel = elements.importFileLabel || fileInput.closest("label");
  const submitButton = importForm.querySelector('button[type="submit"]');
  let importPreviewRows = [];
  let previewFilter = "all";
  let previewErrors = [];
  let classificationOptions = { categories: [], tags: [] };
  let hasPreview = false;

  importForm.addEventListener("submit", handleImportSubmit);
  importSource.addEventListener("change", handleImportSourceChange);
  importTarget.addEventListener("change", renderImportTargets);
  downloadImportTemplateButton.addEventListener("click", downloadImportTemplate);
  fileInput.addEventListener("change", handleFileSelection);
  importResult.addEventListener("input", handlePreviewInput);
  importResult.addEventListener("change", handlePreviewInput);
  importResult.addEventListener("click", handlePreviewClick);
  importResult.innerHTML = stateMarkup("Baixe o modelo, preencha os lançamentos e selecione o arquivo para começar.", {
    kind: "info",
    title: "Pronto para importar",
  });
  handleImportSourceChange();

  async function handleFileSelection() {
    if (!fileInput.files || fileInput.files.length === 0) {
      return;
    }
    await previewImportFile();
  }

  async function handleImportSubmit(event) {
    event.preventDefault();
    const target = importTarget.value;
    if (target === "account" && state.accounts.length === 0) {
      setMessage(importMessage, "Cadastre uma conta antes de importar lançamentos.", "error");
      return;
    }
    if (target === "card" && state.creditCards.length === 0) {
      setMessage(importMessage, "Cadastre um cartão antes de importar lançamentos.", "error");
      return;
    }
    if (hasPreview) {
      await confirmImportSelection();
      return;
    }
    await previewImportFile();
  }

  async function confirmImportSelection() {
    const rows = collectSelectedRows();
    if (rows.length === 0) {
      setMessage(importMessage, "Selecione pelo menos uma linha para importar.", "error");
      return;
    }
    const isLegacy = importSource.value !== "template";
    const target = isLegacy ? "account" : importTarget.value;
    const data = new FormData(importForm);
    data.set("target", target);
    data.set(isLegacy ? "account_id" : "target_id", isLegacy || target === "account" ? importAccount.value : importCreditCard.value);
    data.set("preview_rows", JSON.stringify(rows));
    data.set("preview", "false");
    if (isLegacy) {
      data.set("source_filename", fileInput.files?.[0]?.name || "arquivo de importação");
    }
    data.delete("file");
    setMessage(importMessage, "");
    setFormBusy(importForm, true);
    try {
      const response = await upload(isLegacy ? "/api/import/legacy-transactions" : "/api/import/system-template", data);
      importForm.reset();
      importPreviewRows = [];
      previewErrors = [];
      previewFilter = "all";
      hasPreview = false;
      importTarget.value = target;
      importSource.value = "template";
      handleImportSourceChange();
      renderImportTargets();
      await onImportCompleted();
      renderImportResult(response);
      const replacedCount = (response.rows || []).filter((row) => row.replaced).length;
      const newCount = response.imported - replacedCount;
      setMessage(
        importMessage,
        `${newCount} lançamento(s) novo(s), ${replacedCount} substituído(s) e ${response.skipped} ignorado(s).`,
        response.imported ? "success" : "info",
      );
      updateSubmitLabel();
    } catch (error) {
      setMessage(importMessage, error.message, "error");
    } finally {
      setFormBusy(importForm, false);
      setReviewState(hasPreview);
      updateSubmitLabel();
    }
  }

  async function previewImportFile() {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      setMessage(importMessage, "Selecione um arquivo para visualizar antes da importação.", "error");
      return;
    }
    const target = importTarget.value;
    const data = new FormData(importForm);
    const isLegacy = importSource.value !== "template";
    data.set("target", isLegacy ? "account" : target);
    data.set(isLegacy ? "account_id" : "target_id", isLegacy || target === "account" ? importAccount.value : importCreditCard.value);
    data.set("preview", "true");
    setMessage(importMessage, "");
    importResult.innerHTML = stateMarkup("Validando o arquivo e montando pré-visualização.", {
      kind: "loading",
      title: "Revisando importação",
    });
    setFormBusy(importForm, true);
    try {
      const response = await upload(isLegacy ? "/api/import/legacy-transactions" : "/api/import/system-template", data);
      if (!response.preview || !Array.isArray(response.preview)) {
        renderImportResult(response);
        return;
      }
      previewErrors = response.errors || [];
      classificationOptions = response.classification_options || { categories: [], tags: [] };
      importPreviewRows = response.preview.map((row) => ({
        ...row,
        values: normalizePreviewValues(row),
        baselineValues: normalizeClassificationValues({ ...(row.values || {}) }),
        editedFields: [],
        duplicateMatches: row.duplicate_matches || [],
        duplicateAction: row.duplicate_matches?.length ? "ignore" : "",
        duplicateTargetId: row.duplicate_matches?.length === 1 ? String(row.duplicate_matches[0].id) : "",
        selected: row.selected !== false,
      }));
      hasPreview = true;
      setReviewState(true);
      renderPreviewTable(importPreviewRows);
      setMessage(importMessage, isLegacy
        ? "Revise os dados, escolha categoria e subcategoria nas opções existentes e confirme somente as linhas que deseja importar. Digite uma tag ou escolha uma sugestão."
        : "Revise os dados, escolha categoria e subcategoria nas opções existentes e selecione os itens que devem entrar. Digite uma tag ou escolha uma sugestão.", "info");
      updateSubmitLabel();
    } catch (error) {
      setMessage(importMessage, error.message, "error");
      importResult.innerHTML = stateMarkup(error.message, { kind: "error", title: "Não foi possível importar" });
    } finally {
      setFormBusy(importForm, false);
      setReviewState(hasPreview);
      updateSubmitLabel();
    }
  }

  function handlePreviewInput(event) {
    const rowElement = event.target.closest("[data-preview-row]");
    if (!rowElement) {
      return;
    }
    const rowNumber = Number(rowElement.dataset.previewRow);
    const targetRow = importPreviewRows.find((entry) => Number(entry.row) === rowNumber);
    if (!targetRow) {
      return;
    }
    if (event.target.matches('[data-preview-toggle]')) {
      targetRow.selected = event.target.checked;
      const hiddenByFilter = (previewFilter === "selected" && !targetRow.selected)
        || (previewFilter === "unselected" && targetRow.selected);
      if (hiddenByFilter) {
        renderPreviewTable(importPreviewRows);
        updateSubmitLabel();
        return;
      }
      rowElement.classList.toggle("import-preview-row--disabled", !targetRow.selected);
      rowElement.querySelector(".import-preview-status").textContent = targetRow.selected ? "Incluída" : "Ignorada";
      updateSubmitLabel();
      return;
    }
    if (event.target.matches("[data-duplicate-action]")) {
      targetRow.duplicateAction = event.target.value;
      return;
    }
    if (event.target.matches("[data-duplicate-target]")) {
      targetRow.duplicateTargetId = event.target.value;
      return;
    }
    const fieldName = event.target.dataset.field;
    if (!fieldName || !PREVIEW_FIELDS.includes(fieldName)) {
      return;
    }
    targetRow.values = { ...(targetRow.values || {}) };
    targetRow.values[fieldName] = event.target.value;
    if (fieldName === "categoria") {
      const subcategorySelect = rowElement.querySelector('[data-field="subcategoria"]');
      updateSubcategoryOptions(subcategorySelect, targetRow.values.categoria, "");
      targetRow.values.subcategoria = "";
      markFieldEdited(targetRow, "subcategoria", "");
    }
    if (["descricao", "categoria", "subcategoria", "tags"].includes(fieldName)) {
      markFieldEdited(targetRow, fieldName, targetRow.values[fieldName]);
      updateAdjustmentBadge(rowElement, targetRow);
    }
    if (["data", "valor", "categoria", "subcategoria"].includes(fieldName)) {
      refreshDuplicateMatches(targetRow, rowElement);
    }
  }

  function handlePreviewClick(event) {
    const actionButton = event.target.closest("[data-preview-action]");
    if (!actionButton) {
      return;
    }
    const action = actionButton.dataset.previewAction;
    if (action === "toggle-all") {
      const shouldSelectAll = !importPreviewRows.every((row) => row.selected !== false);
      importPreviewRows = importPreviewRows.map((row) => ({ ...row, selected: shouldSelectAll }));
      renderPreviewTable(importPreviewRows);
      updateSubmitLabel();
      return;
    }
    if (action === "filter") {
      previewFilter = actionButton.dataset.previewFilter || "all";
      renderPreviewTable(importPreviewRows);
      return;
    }
    if (action === "clear") {
      importPreviewRows = [];
      previewErrors = [];
      previewFilter = "all";
      hasPreview = false;
      importForm.reset();
      importTarget.value = importTarget.dataset.defaultValue || "account";
      importSource.value = "template";
      setReviewState(false);
      handleImportSourceChange();
      renderImportTargets();
      updateSubmitLabel();
      importResult.innerHTML = stateMarkup("Baixe o modelo, preencha os lançamentos e selecione o arquivo para começar.", {
        kind: "info",
        title: "Pronto para importar",
      });
      setMessage(importMessage, "Pré-visualização cancelada. Selecione outro arquivo para revisar os dados.", "info");
    }
  }

  function updateSubmitLabel() {
    const selectedCount = importPreviewRows.filter((row) => row.selected !== false).length;
    submitButton.textContent = hasPreview ? `Confirmar importação (${selectedCount})` : "Importar lançamentos";
    const count = importResult.querySelector(".import-preview-toolbar__meta span");
    if (count) {
      count.textContent = `${selectedCount} selecionadas`;
    }
  }

  function collectSelectedRows() {
    // spec: importacao-dados v1.14 — critério 40
    return importPreviewRows
      .filter((row) => row.selected !== false)
      .map((row) => {
        const values = { ...(row.values || {}) };
        const rowElement = [...importResult.querySelectorAll("[data-preview-row]")]
          .find((element) => element.dataset.previewRow === String(row.row));
        rowElement?.querySelectorAll("[data-field]").forEach((field) => {
          values[field.dataset.field] = field.value;
        });
        return {
          row: row.row,
          selected: true,
          raw: row.raw || {},
          values,
          edited_fields: row.editedFields || [],
          duplicate_action: row.duplicateAction || "",
          duplicate_target_id: row.duplicateTargetId || "",
        };
      });
  }

  function updateAdjustmentBadge(rowElement, row) {
    const badge = rowElement.querySelector("[data-adjustment-status]");
    const manuallyAdjusted = (row.editedFields || []).length > 0;
    badge.hidden = !row.learned_adjustment && !manuallyAdjusted;
    badge.textContent = row.learned_adjustment ? "Já ajustado" : "Ajustado nesta revisão";
    badge.title = row.learned_adjustment
      ? "Ajuste aprendido anteriormente para esta origem e descrição."
      : "Este ajuste será aprendido depois que a linha for importada com sucesso.";
  }

  function renderPreviewTable(previewRows) {
    const fields = importSource.value !== "template"
      ? ["data", "descricao_original", "descricao", "valor", "categoria", "subcategoria", "tags", "observacoes"]
      : PREVIEW_FIELDS;
    const filteredRows = previewRows.filter((row) => {
      if (previewFilter === "selected") return row.selected !== false;
      if (previewFilter === "unselected") return row.selected === false;
      return true;
    });
    const selectedCount = previewRows.filter((row) => row.selected !== false).length;
    importResult.innerHTML = `
      <div class="import-preview-toolbar">
        <div class="import-preview-toolbar__meta">
          <strong>${previewRows.length} linha(s) encontrada(s)</strong>
          <span>${selectedCount} selecionadas</span>
        </div>
        <div class="import-preview-toolbar__actions">
          <div class="segmented-control" role="group" aria-label="Filtro de linhas da pré-visualização">
            <button type="button" class="segment ${previewFilter === "all" ? "active" : ""}" aria-pressed="${previewFilter === "all"}" data-preview-action="filter" data-preview-filter="all">Todas</button>
            <button type="button" class="segment ${previewFilter === "selected" ? "active" : ""}" aria-pressed="${previewFilter === "selected"}" data-preview-action="filter" data-preview-filter="selected">Selecionadas</button>
            <button type="button" class="segment ${previewFilter === "unselected" ? "active" : ""}" aria-pressed="${previewFilter === "unselected"}" data-preview-action="filter" data-preview-filter="unselected">Ignoradas</button>
          </div>
          <button type="button" class="ghost small-button" data-preview-action="toggle-all">${selectedCount === previewRows.length ? "Desmarcar todas" : "Marcar todas"}</button>
        </div>
      </div>
      <div class="import-preview-list">
        ${filteredRows.map((row) => `
          <article class="import-preview-row ${row.selected === false ? "import-preview-row--disabled" : ""}" data-preview-row="${row.row}">
            <div class="import-preview-row__header">
              <label class="import-preview-toggle">
                <input type="checkbox" data-preview-toggle ${row.selected === false ? "" : "checked"}>
                <span>Linha ${row.row}</span>
              </label>
              <div class="import-preview-row__badges">
                <span class="import-preview-adjustment" data-adjustment-status ${row.learned_adjustment || row.editedFields?.length ? "" : "hidden"}>
                  ${row.learned_adjustment ? "Já ajustado" : "Ajustado nesta revisão"}
                </span>
                <span class="import-preview-status">${row.selected === false ? "Ignorada" : "Incluída"}</span>
              </div>
            </div>
            ${renderDuplicatePanel(row)}
            <div class="import-preview-fields">
              ${fields.map((field) => {
                const value = row.values?.[field] ?? "";
                const fieldLabel = {
                  data: "Data",
                  tipo: "Tipo",
                  descricao_original: "Descrição do arquivo (original)",
                  descricao: "Descrição Lançamento",
                  valor: "Valor",
                  categoria: "Categoria",
                  subcategoria: "Subcategoria",
                  tags: "Tags",
                  repeticao: "Repetição",
                  parcelas: "Parcelas",
                  recorrencia: "Recorrência",
                  media: "Média",
                  observacoes: "Observações",
                  competencia_fatura: "Competência",
                  conta_destino_id: "Destino",
                  valor_destino: "Valor destino",
                  cotacao_cambio: "Cotação",
                  cotacao_brl: "Cotação BRL",
                }[field] || field;
                if (field === "descricao_original") {
                  return `
                    <label>
                      <span>${fieldLabel}</span>
                      <input type="text" value="${escapeHtml(value || "")}" readonly aria-readonly="true">
                    </label>
                  `;
                }
                // spec: importacao-dados v1.14 — critério 33
                if (field === "categoria") {
                  const categoryGroup = categoryGroupForRow(row.values);
                  return `
                    <label>
                      <span>${fieldLabel}</span>
                      <select data-field="categoria">
                        <option value="">Selecione uma categoria</option>
                        ${classificationOptions.categories.filter((category) => category.group_type === categoryGroup).map((category) => `
                          <option value="${escapeHtml(category.name)}" ${category.name === value ? "selected" : ""}>${escapeHtml(category.name)}</option>
                        `).join("")}
                      </select>
                    </label>
                  `;
                }
                if (field === "subcategoria") {
                  return `
                    <label>
                      <span>${fieldLabel}</span>
                      <select data-field="subcategoria">
                        ${renderSubcategoryOptions(row.values?.categoria, value)}
                      </select>
                    </label>
                  `;
                }
                if (field === "tags") {
                  const tagListId = `import-preview-tags-${String(row.row).replace(/[^a-zA-Z0-9_-]/g, "")}`;
                  return `
                    <label>
                      <span>${fieldLabel}</span>
                      <input type="text" data-field="tags" list="${tagListId}" value="${escapeHtml(value || "")}" placeholder="Selecione ou digite uma tag">
                      <datalist id="${tagListId}">
                        ${classificationOptions.tags.map((tag) => `<option value="${escapeHtml(tag.name)}"></option>`).join("")}
                      </datalist>
                    </label>
                  `;
                }
                const isScalarField = ["data", "tipo", "descricao", "valor", "categoria", "subcategoria", "tags", "repeticao", "parcelas", "recorrencia", "media", "observacoes", "competencia_fatura", "conta_destino_id", "valor_destino", "cotacao_cambio", "cotacao_brl"].includes(field);
                return `
                  <label>
                    <span>${fieldLabel}</span>
                    <input type="text" data-field="${field}" value="${escapeHtml(value || "")}" ${isScalarField ? "" : "hidden"}>
                  </label>
                `;
              }).join("")}
            </div>
          </article>
        `).join("")}
      </div>
      ${previewErrors.length ? `
        <div class="import-errors import-preview-errors">
          ${previewErrors.map((error) => `
            <article>
              <strong>Linha ${escapeHtml(error.row)}</strong>
              <span>${escapeHtml(error.description || "Sem descrição")}</span>
              <p>${escapeHtml(error.reason)}</p>
            </article>
          `).join("")}
        </div>
      ` : ""}
      <div class="form-actions">
        <button class="primary" type="submit" form="importForm">Confirmar importação (${selectedCount})</button>
        <button class="ghost" type="button" data-preview-action="clear">Cancelar</button>
      </div>
    `;
  }

  function normalizeClassificationValues(values) {
    const categoryGroup = categoryGroupForRow(values);
    const category = classificationOptions.categories.find(
      (item) => item.group_type === categoryGroup
        && normalizeOptionName(item.name) === normalizeOptionName(values.categoria),
    );
    values.categoria = category?.name || "";
    const subcategory = category?.subcategories?.find(
      (item) => normalizeOptionName(item.name) === normalizeOptionName(values.subcategoria),
    );
    values.subcategoria = subcategory?.name || "";
    values.tags = String(values.tags || "")
      .split(/[;,|]/)
      .map((tag) => tag.trim())
      .filter(Boolean)
      .map((tag) => classificationOptions.tags.find(
        (item) => normalizeOptionName(item.name) === normalizeOptionName(tag),
      )?.name || tag)
      .join("; ");
    return values;
  }

  function normalizePreviewValues(row) {
    // spec: importacao-dados v1.14 — critério 39
    const values = { ...(row.values || {}) };
    if (!String(values.descricao_original || "").trim()) {
      values.descricao_original = row.raw?.original_description
        || row.raw?._original_description
        || row.raw?.description
        || row.raw?.descricao
        || "";
    }
    return normalizeClassificationValues(values);
  }

  function categoryGroupForRow(values) {
    const type = String(values.tipo || "").trim().toLowerCase();
    if (type === "income" || type === "receita") return "income";
    if (type === "investment" || type === "investimento") return "investment";
    if (type === "expense" || type === "despesa") return "expense";
    const amount = String(values.valor || "")
      .replace(/[^\d,.-]/g, "")
      .replace(/\./g, "")
      .replace(",", ".");
    return Number(amount) > 0 ? "income" : "expense";
  }

  function renderSubcategoryOptions(categoryName, selectedName) {
    const category = classificationOptions.categories.find(
      (item) => normalizeOptionName(item.name) === normalizeOptionName(categoryName),
    );
    const subcategories = category?.subcategories || [];
    return `
      <option value="">Sem subcategoria</option>
      ${subcategories.map((subcategory) => `
        <option value="${escapeHtml(subcategory.name)}" ${subcategory.name === selectedName ? "selected" : ""}>${escapeHtml(subcategory.name)}</option>
      `).join("")}
    `;
  }

  function updateSubcategoryOptions(select, categoryName, selectedName) {
    if (!select) return;
    select.innerHTML = renderSubcategoryOptions(categoryName, selectedName);
  }

  function markFieldEdited(row, fieldName, value) {
    const baselineValue = String(row.baselineValues?.[fieldName] ?? "");
    const currentValue = String(value ?? "");
    const editedFields = new Set(row.editedFields || []);
    if (currentValue === baselineValue) {
      editedFields.delete(fieldName);
    } else {
      editedFields.add(fieldName);
    }
    row.editedFields = [...editedFields];
  }

  function normalizeOptionName(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .trim()
      .toLocaleLowerCase();
  }

  // spec: importacao-dados v1.14 — critérios 34 a 38
  function renderDuplicatePanel(row) {
    if (!row.duplicateMatches?.length) {
      return "";
    }
    const candidates = row.duplicateMatches;
    const selectedId = String(row.duplicateTargetId || "");
    const targetControl = candidates.length === 1
      ? `<p>Correspondência: ${escapeHtml(candidates[0].description)} · ${escapeHtml(candidates[0].date)}</p>`
      : `
        <label>
          <span>Escolha qual lançamento substituir</span>
          <select data-duplicate-target>
            <option value="">Selecione um lançamento</option>
            ${candidates.map((candidate) => `
              <option value="${candidate.id}" ${String(candidate.id) === selectedId ? "selected" : ""}>
                ${escapeHtml(candidate.date)} · ${escapeHtml(candidate.description)} · ${escapeHtml(formatDuplicateAmount(candidate.amount_cents))}
              </option>
            `).join("")}
          </select>
        </label>
      `;
    return `
      <div class="import-preview-duplicate" role="alert">
        <strong>Possível duplicidade (${candidates.length})</strong>
        ${targetControl}
        <label>
          <span>O que fazer com esta linha?</span>
          <select data-duplicate-action>
            <option value="ignore" ${row.duplicateAction !== "replace" ? "selected" : ""}>Ignorar esta linha</option>
            <option value="replace" ${row.duplicateAction === "replace" ? "selected" : ""}>Substituir campos do lançamento existente</option>
          </select>
        </label>
        <p>Data, valor, categoria e subcategoria correspondem a um lançamento existente.</p>
      </div>
    `;
  }

  async function refreshDuplicateMatches(row, rowElement) {
    const token = (row.duplicateCheckToken || 0) + 1;
    row.duplicateCheckToken = token;
    const isLegacy = importSource.value !== "template";
    const target = isLegacy ? "account" : importTarget.value;
    const data = new FormData(importForm);
    data.set("target", target);
    data.set(isLegacy ? "account_id" : "target_id", isLegacy || target === "account" ? importAccount.value : importCreditCard.value);
    data.set("duplicate_check", "true");
    data.set("preview_rows", JSON.stringify([{
      row: row.row,
      raw: row.raw || {},
      values: row.values || {},
      selected: row.selected !== false,
    }]));
    data.delete("file");
    try {
      const response = await upload(isLegacy ? "/api/import/legacy-transactions" : "/api/import/system-template", data);
      if (row.duplicateCheckToken !== token) return;
      const matches = response.duplicate_matches?.[0]?.matches || [];
      const previousAction = row.duplicateAction;
      const previousTargetId = String(row.duplicateTargetId || "");
      row.duplicateMatches = matches;
      row.duplicateAction = matches.length
        ? previousAction === "replace" ? "replace" : "ignore"
        : "";
      row.duplicateTargetId = matches.some((candidate) => String(candidate.id) === previousTargetId)
        ? previousTargetId
        : matches.length === 1 ? String(matches[0].id) : "";
      const panel = rowElement.querySelector(".import-preview-duplicate");
      const replacement = document.createElement("div");
      replacement.innerHTML = renderDuplicatePanel(row);
      if (panel) {
        if (replacement.firstElementChild) {
          panel.replaceWith(replacement.firstElementChild);
        } else {
          panel.remove();
        }
      } else if (replacement.firstElementChild) {
        rowElement.insertBefore(replacement.firstElementChild, rowElement.querySelector(".import-preview-fields"));
      }
    } catch (error) {
      setMessage(importMessage, `Não foi possível verificar duplicidades: ${error.message}`, "error");
    }
  }

  function formatDuplicateAmount(amountCents) {
    return (Number(amountCents || 0) / 100).toLocaleString("pt-BR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function downloadImportTemplate() {
    const target = importTarget.value || "account";
    window.location.href = `/api/import/template?target=${encodeURIComponent(target)}`;
  }

  function renderImportTargets() {
    const isLegacy = importSource.value !== "template";
    const cardOption = importTarget.querySelector('option[value="card"]');
    cardOption.disabled = isLegacy;
    if (isLegacy && importTarget.value === "card") {
      importTarget.value = "account";
    }
    const targetIsCard = importTarget.value === "card";
    importAccountLabel.hidden = targetIsCard;
    importCardLabel.hidden = !targetIsCard;
    importAccount.disabled = targetIsCard;
    importCreditCard.disabled = !targetIsCard;
    importAccount.name = targetIsCard ? "" : "target_id";
    importCreditCard.name = targetIsCard ? "target_id" : "";
    importAccount.innerHTML = state.accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)} (${escapeHtml(account.currency)})</option>`
    )).join("") || '<option value="">Cadastre uma conta</option>';
    importCreditCard.innerHTML = state.creditCards.map((card) => (
      `<option value="${card.id}">${escapeHtml(card.name)} (${escapeHtml(card.currency)})</option>`
    )).join("") || '<option value="">Cadastre um cartão</option>';
    submitButton.disabled = targetIsCard ? state.creditCards.length === 0 : state.accounts.length === 0;
    importTarget.dataset.defaultValue = importTarget.value;
    updateSubmitLabel();
  }

  function renderImportResult(result) {
    const errors = result.errors || [];
    const importedRows = (result.rows || []).map((row) => ({
      ...row,
      status: row.replaced ? "Substituído" : "Importado",
      reason: "",
    }));
    const skippedRows = errors.map((row) => ({
      ...row,
      status: "Ignorado",
    }));
    const rowResults = [...importedRows, ...skippedRows].sort((left, right) => (
      Number(left.row) - Number(right.row) || String(left.row).localeCompare(String(right.row))
    ));
    const replacedCount = importedRows.filter((row) => row.replaced).length;
    importResult.innerHTML = `
      <div class="import-summary">
        <div><span>Total lido</span><strong>${result.total_rows}</strong></div>
        <div><span>Novos</span><strong>${result.imported - replacedCount}</strong></div>
        <div><span>Substituídos</span><strong>${replacedCount}</strong></div>
        <div><span>Ignorados</span><strong>${result.skipped}</strong></div>
      </div>
      ${rowResults.length ? `
        <ul class="import-result-list" aria-label="Resultado por linha">
          ${rowResults.map((row) => {
            const description = row.description || "Sem descrição";
            const reason = row.reason || "";
            const fullText = `Linha ${row.row} · ${description} · ${row.status}${reason ? ` · ${reason}` : ""}`;
            return `
              <li title="${escapeHtml(fullText)}">
                <strong>Linha ${escapeHtml(row.row)}</strong>
                <span class="import-result-list__description">${escapeHtml(description)}</span>
                <span class="import-result-list__status">${escapeHtml(row.status)}</span>
                ${reason ? `<span class="import-result-list__reason">${escapeHtml(reason)}</span>` : ""}
              </li>
            `;
          }).join("")}
        </ul>
      ` : stateMarkup("Todas as linhas válidas foram processadas sem descarte.", { kind: "info", title: "Importação concluída" })}
    `;
    importPreviewRows = [];
    previewErrors = [];
    hasPreview = false;
    setReviewState(false);
  }

  function handleImportSourceChange() {
    const source = importSource.value;
    const isOfx = source === "ofx";
    const isLegacy = source !== "template";
    fileInput.value = "";
    fileInput.accept = isOfx ? ".ofx,.qfx" : isLegacy ? ".xls,.csv" : ".xlsx,.csv";
    fileLabel.querySelector("span").textContent = isOfx
      ? "Extrato bancário OFX"
      : isLegacy ? "Planilha externa" : "Modelo preenchido";
    downloadImportTemplateButton.hidden = isLegacy;
    renderImportTargets();
  }

  function setReviewState(isReviewing) {
    importSource.disabled = isReviewing;
    importTarget.disabled = isReviewing;
    const targetIsCard = importTarget.value === "card";
    importAccount.disabled = isReviewing || targetIsCard;
    importCreditCard.disabled = isReviewing || !targetIsCard;
    fileInput.disabled = isReviewing;
  }

  return {
    renderImportTargets,
    renderImportResult,
  };
}
