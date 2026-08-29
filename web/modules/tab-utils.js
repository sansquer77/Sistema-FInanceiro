export function prefersReducedMotion() {
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export function transitionView(update) {
  if (typeof document.startViewTransition === "function" && !prefersReducedMotion()) {
    document.startViewTransition(update);
    return;
  }
  update();
}

export function bindRovingTablist(buttons, { valueFor, onSelect }) {
  const tabs = Array.from(buttons || []);
  if (!tabs.length) {
    return;
  }
  const select = (button) => onSelect(valueFor(button));
  tabs.forEach((button) => {
    button.addEventListener("click", () => select(button));
    button.addEventListener("keydown", (event) => {
      const currentIndex = tabs.indexOf(event.currentTarget);
      let nextIndex = null;
      if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % tabs.length;
      if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + tabs.length) % tabs.length;
      if (event.key === "Home") nextIndex = 0;
      if (event.key === "End") nextIndex = tabs.length - 1;
      if (nextIndex === null) return;
      event.preventDefault();
      tabs[nextIndex].focus();
      select(tabs[nextIndex]);
    });
  });
}

export function syncRovingTabState(buttons, activeValue, valueFor) {
  Array.from(buttons || []).forEach((button) => {
    const active = valueFor(button) === activeValue;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
    button.tabIndex = active ? 0 : -1;
  });
}
