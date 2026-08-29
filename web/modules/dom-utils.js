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
