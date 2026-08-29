const overlayFocus = new WeakMap();

export function initializeOverlayUX(root = document) {
  root.querySelectorAll(".drawer").forEach((overlay) => {
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    overlay.tabIndex = -1;
  });
  document.addEventListener("keydown", handleOverlayKeydown);
  const observer = new MutationObserver((records) => records.forEach(({ target, attributeName }) => {
    if (attributeName !== "hidden" || !target.classList?.contains("drawer")) return;
    if (!target.hidden) {
      overlayFocus.set(target, document.activeElement);
      queueMicrotask(() => focusableElements(target)[0]?.focus() || target.focus());
    } else {
      overlayFocus.get(target)?.focus?.();
      overlayFocus.delete(target);
    }
  }));
  root.querySelectorAll(".drawer").forEach((overlay) => observer.observe(overlay, { attributes: true }));
}

function handleOverlayKeydown(event) {
  const overlay = [...document.querySelectorAll(".drawer:not([hidden])")].at(-1);
  if (!overlay) return;
  if (event.key === "Escape") {
    event.preventDefault();
    (overlay.querySelector(".drawer-close-button") || overlay.querySelector(".drawer-overlay"))?.click();
    return;
  }
  if (event.key !== "Tab") return;
  const focusable = focusableElements(overlay);
  if (!focusable.length) {
    event.preventDefault();
    overlay.focus();
    return;
  }
  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && document.activeElement === first) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && document.activeElement === last) {
    event.preventDefault();
    first.focus();
  }
}

function focusableElements(container) {
  return [...container.querySelectorAll("button, input, select, textarea, a[href], [tabindex]:not([tabindex='-1'])")]
    .filter((element) => !element.disabled && !element.hidden);
}
