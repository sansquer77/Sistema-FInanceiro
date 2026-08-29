const formControlStates = new WeakMap();

export function setFormBusy(form, busy) {
  const button = form.querySelector('button[type="submit"]');
  if (busy) {
    if (form.getAttribute("aria-busy") === "true") {
      return;
    }
    formControlStates.set(form, [...form.elements].map((element) => ({
      element,
      disabled: element.disabled,
    })));
    form.setAttribute("aria-busy", "true");
    for (const element of form.elements) {
      element.disabled = true;
    }
    if (button) {
      button.dataset.label = button.textContent;
      button.textContent = "Aguarde...";
    }
    return;
  }

  for (const { element, disabled } of formControlStates.get(form) || []) {
    element.disabled = disabled;
  }
  formControlStates.delete(form);
  form.removeAttribute("aria-busy");
  if (button?.dataset.label) {
    button.textContent = button.dataset.label;
    delete button.dataset.label;
  }
}

export function initializeFormUX(root = document) {
  const forms = [...root.querySelectorAll("form")];
  for (const form of forms) {
    if (form.dataset.formUx === "true") {
      continue;
    }
    form.dataset.formUx = "true";
    form.addEventListener("invalid", handleInvalidControl, true);
    form.addEventListener("input", handleControlCorrection);
    form.addEventListener("change", handleControlCorrection);
    form.addEventListener("reset", () => queueMicrotask(() => clearFormValidation(form)));
    initializeProgressiveForm(form);
  }
}

function handleInvalidControl(event) {
  const control = event.target;
  if (!(control instanceof HTMLElement)) {
    return;
  }
  event.preventDefault();
  showControlValidation(control);
  const form = control.closest("form");
  if (form && !form.querySelector('[aria-invalid="true"]:focus')) {
    control.focus({ preventScroll: true });
    control.scrollIntoView({ behavior: "smooth", block: "center" });
  }
}

function handleControlCorrection(event) {
  const control = event.target;
  if (control instanceof HTMLElement && "validity" in control && control.validity.valid) {
    clearControlValidation(control);
  }
}

function showControlValidation(control) {
  const validationId = control.id
    ? `${control.id}-validation`
    : `field-validation-${crypto.randomUUID()}`;
  let message = document.getElementById(validationId);
  if (!message) {
    message = document.createElement("small");
    message.id = validationId;
    message.className = "field-validation";
    message.setAttribute("role", "alert");
    (control.closest("label") || control.parentElement)?.append(message);
  }
  message.textContent = control.validationMessage || "Revise este campo.";
  control.setAttribute("aria-invalid", "true");
  const describedBy = new Set((control.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean));
  describedBy.add(validationId);
  control.setAttribute("aria-describedby", [...describedBy].join(" "));
}

function clearControlValidation(control) {
  const describedBy = (control.getAttribute("aria-describedby") || "").split(/\s+/).filter(Boolean);
  const validationIds = describedBy.filter((id) => id.endsWith("-validation") || id.startsWith("field-validation-"));
  for (const id of validationIds) {
    document.getElementById(id)?.remove();
  }
  const remainingIds = describedBy.filter((id) => !validationIds.includes(id));
  if (remainingIds.length) {
    control.setAttribute("aria-describedby", remainingIds.join(" "));
  } else {
    control.removeAttribute("aria-describedby");
  }
  control.removeAttribute("aria-invalid");
}

function clearFormValidation(form) {
  form.querySelectorAll('[aria-invalid="true"]').forEach(clearControlValidation);
}

export function formData(form) {
  return Object.fromEntries(new FormData(form).entries());
}

export function setMessage(element, text, tone = "") {
  if (tone === "success" && text) {
    element.textContent = "";
    element.className = "message";
    showToast(text);
    return;
  }
  element.textContent = text;
  element.className = `message ${tone}`.trim();
}

export function showToast(text) {
  let region = document.querySelector("#toastRegion");
  if (!region) {
    region = document.createElement("div");
    region.id = "toastRegion";
    region.className = "toast-region";
    region.setAttribute("aria-live", "polite");
    region.setAttribute("aria-atomic", "true");
    document.body.append(region);
  }
  const toast = document.createElement("div");
  toast.className = "toast success";
  toast.setAttribute("role", "status");
  toast.textContent = text;
  region.append(toast);
  window.setTimeout(() => toast.remove(), 4200);
}

export function setLastUpdated(element, date = new Date()) {
  if (!element) return;
  element.dateTime = date.toISOString();
  element.textContent = `Atualizado às ${date.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}`;
}

function initializeProgressiveForm(form) {
  if (form.hasAttribute("data-progressive-form")) {
    form.querySelectorAll('textarea[name="notes"]').forEach((control) => {
      control.closest("label")?.setAttribute("data-progressive-secondary", "");
    });
  }
  const secondary = [...form.querySelectorAll("[data-progressive-secondary]")];
  const actions = form.querySelector(".form-actions");
  if (secondary.length) {
    const details = document.createElement("details");
    details.className = "form-progressive-section";
    const summary = document.createElement("summary");
    summary.textContent = "Detalhes adicionais";
    const content = document.createElement("div");
    content.className = "form-progressive-content";
    secondary.forEach((element) => content.append(element));
    details.append(summary, content);
    form.insertBefore(details, actions);
  }
  if (!form.hasAttribute("data-operation-summary") || !actions) return;
  const summary = document.createElement("details");
  summary.className = "form-operation-summary";
  const summaryToggle = document.createElement("summary");
  summaryToggle.textContent = "Resumo antes de salvar";
  const summaryContent = document.createElement("div");
  summaryContent.setAttribute("aria-live", "polite");
  summary.append(summaryToggle, summaryContent);
  form.insertBefore(summary, actions);
  let interacted = false;
  let previousSimpleState = null;
  const update = () => {
    const entries = interacted ? [...form.elements].filter((control) => (
      control.name
      && control.value
      && !control.disabled
      && !control.hidden
      && !["hidden", "password"].includes(control.type)
      && !control.closest("[hidden]")
    ))
      .slice(0, 6).map((control) => {
        const label = control.closest("label")?.childNodes[0]?.textContent.trim() || control.name;
        const value = control.selectedOptions?.[0]?.textContent || control.value;
        return `<span><b>${escapeHtml(label)}</b>${escapeHtml(value)}</span>`;
      }) : [];
    summaryContent.innerHTML = entries.join("");
    summary.hidden = !entries.length;
    const seriesKind = form.elements.namedItem("series_kind")?.value;
    const isSimple = seriesKind === "single";
    if (entries.length && previousSimpleState !== isSimple) {
      summary.open = !isSimple;
      previousSimpleState = isSimple;
    }
  };
  const handleInteraction = (event) => {
    if (event.isTrusted) interacted = true;
    // Aguarda os handlers da view sincronizarem campos condicionais antes do resumo.
    queueMicrotask(update);
  };
  form.addEventListener("input", handleInteraction);
  form.addEventListener("change", handleInteraction);
  form.addEventListener("reset", () => {
    interacted = false;
    previousSimpleState = null;
    queueMicrotask(update);
  });
  update();
}

const UI_STATE_CONFIG = Object.freeze({
  loading: { title: "Carregando", icon: "↻", role: "status", live: "polite" },
  error: { title: "Não foi possível concluir", icon: "!", role: "alert", live: "assertive" },
  empty: { title: "Nada por aqui ainda", icon: "○", role: "status", live: "polite" },
  info: { title: "Informação", icon: "i", role: "status", live: "polite" },
});

export function stateMarkup(text, { kind = "empty", compact = true, title = "" } = {}) {
  const normalizedKind = UI_STATE_CONFIG[kind] ? kind : "info";
  const config = UI_STATE_CONFIG[normalizedKind];
  const busyAttribute = normalizedKind === "loading" ? ' aria-busy="true"' : "";
  return `
    <div class="ui-state empty-state state-${normalizedKind}${compact ? " compact" : ""}" role="${config.role}" aria-live="${config.live}"${busyAttribute}>
      <span class="ui-state-icon" aria-hidden="true">${config.icon}</span>
      <span class="ui-state-copy"><strong>${escapeHtml(title || config.title)}</strong><span>${escapeHtml(text)}</span></span>
    </div>
  `;
}

export function emptyState(text, compact = false, kind = "empty") {
  const empty = document.createElement("div");
  const normalizedKind = UI_STATE_CONFIG[kind] ? kind : "empty";
  const config = UI_STATE_CONFIG[normalizedKind];
  empty.className = `ui-state empty-state state-${normalizedKind}${compact ? " compact" : ""}`;
  empty.setAttribute("role", config.role);
  empty.setAttribute("aria-live", config.live);
  if (normalizedKind === "loading") empty.setAttribute("aria-busy", "true");
  const icon = document.createElement("span");
  icon.className = "ui-state-icon";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = config.icon;
  const copy = document.createElement("span");
  copy.className = "ui-state-copy";
  const heading = document.createElement("strong");
  heading.textContent = config.title;
  const message = document.createElement("span");
  message.textContent = text;
  copy.append(heading, message);
  empty.append(icon, copy);
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
