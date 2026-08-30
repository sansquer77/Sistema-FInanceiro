export function createDecisionModal() {
  let activeModal = null;

  function choose({ title, message, actions = [] }) {
    return openModal({
      title,
      message,
      renderBody: () => null,
      actions,
    });
  }

  function form({
    title,
    message,
    fields = [],
    primaryLabel,
    primaryVariant = "primary",
    secondaryLabel = "Voltar",
    onChange,
  }) {
    return openModal({
      title,
      message,
      renderBody: (body) => renderFormFields(body, fields),
      actions: [
        { value: "__submit__", label: primaryLabel, variant: primaryVariant, type: "submit" },
        { value: null, label: secondaryLabel, variant: "ghost" },
      ],
      onSubmit: (formElement) => collectFormValues(formElement, fields),
      onChange,
    });
  }

  function openModal({ title, message, renderBody, actions, onSubmit, onChange }) {
    closeActiveModal();
    let resolveModal;
    const pending = new Promise((resolve) => {
      resolveModal = resolve;
    });
    const previousFocus = document.activeElement;
    const titleId = `decision-modal-title-${Date.now()}`;
    const backdrop = document.createElement("div");
    backdrop.className = "decision-modal-backdrop";

    const modal = document.createElement("form");
    modal.className = "decision-modal";
    modal.setAttribute("role", "dialog");
    modal.setAttribute("aria-modal", "true");
    modal.setAttribute("aria-labelledby", titleId);
    modal.noValidate = false;

    const header = document.createElement("div");
    header.className = "decision-modal-header";

    const heading = document.createElement("h3");
    heading.id = titleId;
    heading.textContent = title;
    header.appendChild(heading);

    if (message) {
      const description = document.createElement("p");
      description.textContent = message;
      header.appendChild(description);
    }

    const body = document.createElement("div");
    body.className = "decision-modal-body";
    const firstField = renderBody(body);

    const footer = document.createElement("div");
    footer.className = "decision-modal-actions";
    actions.forEach((action) => {
      const button = document.createElement("button");
      button.type = action.type || "button";
      button.className = decisionButtonClass(action.variant);
      button.textContent = action.label;
      if (action.value !== "__submit__") {
        button.addEventListener("click", () => finish(action.value));
      }
      footer.appendChild(button);
    });

    modal.append(header, body, footer);
    backdrop.appendChild(modal);
    document.body.appendChild(backdrop);

    function handleKeydown(event) {
      if (event.key === "Escape") {
        event.preventDefault();
        finish(null);
      } else if (event.key === "Tab") {
        const focusable = [...modal.querySelectorAll("button, input, select, textarea")].filter((element) => !element.disabled);
        const first = focusable[0];
        const last = focusable.at(-1);
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    }

    activeModal = { backdrop, previousFocus, resolveModal, handleKeydown };

    function finish(value) {
      if (!activeModal || activeModal.backdrop !== backdrop) {
        return;
      }
      activeModal.value = value;
      closeActiveModal();
    }

    backdrop.addEventListener("click", (event) => {
      if (event.target === backdrop) {
        finish(null);
      }
    });
    modal.addEventListener("submit", (event) => {
      event.preventDefault();
      if (!onSubmit) {
        return;
      }
      const values = onSubmit(modal);
      if (values) {
        finish(values);
      }
    });
    if (onChange) {
      modal.addEventListener("input", () => onChange(modal));
      modal.addEventListener("change", () => onChange(modal));
      onChange(modal);
    }
    document.addEventListener("keydown", handleKeydown);

    requestAnimationFrame(() => {
      const focusTarget = firstField || modal.querySelector("button");
      focusTarget?.focus();
    });

    return pending;
  }

  function closeActiveModal() {
    if (!activeModal) {
      return;
    }
    const { backdrop, previousFocus, resolveModal, handleKeydown, value } = activeModal;
    document.removeEventListener("keydown", handleKeydown);
    backdrop.remove();
    activeModal = null;
    resolveModal(value === undefined ? null : value);
    if (previousFocus && typeof previousFocus.focus === "function") {
      previousFocus.focus();
    }
  }

  function renderFormFields(body, fields) {
    let firstField = null;
    fields.forEach((field) => {
      const wrapper = document.createElement("label");
      wrapper.className = field.type === "checkbox" ? "decision-modal-check" : "decision-modal-field";

      const input = document.createElement("input");
      input.name = field.name;
      input.type = field.type || "text";
      input.required = Boolean(field.required);
      input.readOnly = Boolean(field.readOnly);
      if (field.inputMode) {
        input.inputMode = field.inputMode;
      }
      if (field.placeholder) {
        input.placeholder = field.placeholder;
      }
      if (field.type === "checkbox") {
        input.checked = Boolean(field.value);
      } else {
        input.value = field.value || "";
      }

      if (field.type === "checkbox") {
        const text = document.createElement("span");
        text.textContent = field.label;
        wrapper.append(input, text);
      } else {
        const label = document.createElement("span");
        label.textContent = field.label;
        wrapper.append(label, input);
      }

      if (field.help) {
        const help = document.createElement("small");
        help.textContent = field.help;
        wrapper.appendChild(help);
      }

      body.appendChild(wrapper);
      firstField = firstField || input;
    });
    return firstField;
  }

  function collectFormValues(formElement, fields) {
    if (!formElement.reportValidity()) {
      return null;
    }
    return fields.reduce((values, field) => {
      const input = formElement.elements[field.name];
      values[field.name] = input.type === "checkbox" ? input.checked : input.value;
      return values;
    }, {});
  }

  function decisionButtonClass(variant) {
    if (variant === "danger") {
      return "danger";
    }
    if (variant === "primary") {
      return "primary";
    }
    return "ghost";
  }

  return {
    choose,
    form,
  };
}
