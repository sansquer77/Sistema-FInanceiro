export function setFormBusy(form, busy) {
  const button = form.querySelector('button[type="submit"]');
  if (button && !button.dataset.label) {
    button.dataset.label = button.textContent;
  }
  for (const element of form.elements) {
    element.disabled = busy;
  }
  if (button) {
    button.textContent = busy ? "Aguarde..." : button.dataset.label;
  }
}

export function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

export function setMessage(element, text, tone = "") {
  element.textContent = text;
  element.className = `message ${tone}`.trim();
}

export function emptyState(text, compact = false) {
  const empty = document.createElement("div");
  empty.className = compact ? "empty-state compact" : "empty-state";
  empty.textContent = text;
  return empty;
}

export function normalizeSearch(value) {
  return String(value || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim();
}

export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
