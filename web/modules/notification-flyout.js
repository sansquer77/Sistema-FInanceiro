// spec: cockpit/alertas-cockpit v1.1 — critérios 2, 6, 8 e 9
const META = {
  critical: { title: "Alertas críticos", empty: "Nenhum alerta crítico pendente. Suas contas e limites estão em dia." },
  informational: { title: "Informativos", empty: "Nenhum novo evento ou provento registrado para esta semana." },
};

export const notificationSectionLabel = (section) => (META[section] || META.critical).title;
export const notificationEmptyMessage = (section) => (META[section] || META.critical).empty;

export function createNotificationFlyout({ onAction, onMarkSeen } = {}) {
  let trigger = null;
  let section = "critical";
  let payload = { critical: [], informational: [] };
  const dialog = document.createElement("dialog");
  dialog.id = "cockpitNotificationFlyout";
  dialog.className = "notification-flyout";
  dialog.setAttribute("aria-labelledby", "cockpitNotificationFlyoutTitle");
  const surface = document.createElement("section");
  surface.className = "notification-flyout-surface";
  const header = document.createElement("header");
  header.className = "notification-flyout-header";
  const title = document.createElement("h2");
  title.id = "cockpitNotificationFlyoutTitle";
  const closeButton = document.createElement("button");
  closeButton.type = "button";
  closeButton.className = "notification-flyout-close";
  closeButton.setAttribute("aria-label", "Fechar notificações");
  closeButton.textContent = "×";
  header.append(title, closeButton);
  const tabs = document.createElement("div");
  tabs.className = "notification-flyout-tabs";
  tabs.setAttribute("role", "tablist");
  tabs.setAttribute("aria-label", "Tipos de notificação");
  const criticalTab = makeTab("critical");
  const informationalTab = makeTab("informational");
  tabs.append(criticalTab, informationalTab);
  const body = document.createElement("div");
  body.id = "cockpitNotificationFlyoutPanel";
  body.className = "notification-flyout-body";
  body.setAttribute("role", "tabpanel");
  body.tabIndex = 0;
  const footer = document.createElement("footer");
  footer.className = "notification-flyout-footer";
  const markSeenButton = document.createElement("button");
  markSeenButton.type = "button";
  markSeenButton.className = "ghost small-button";
  markSeenButton.textContent = "Marcar como vistos";
  const status = document.createElement("span");
  status.className = "notification-flyout-status";
  status.setAttribute("role", "status");
  status.setAttribute("aria-live", "polite");
  footer.append(status, markSeenButton);
  surface.append(header, tabs, body, footer);
  dialog.append(surface);
  document.body.append(dialog);

  function makeTab(name) {
    const button = document.createElement("button");
    button.type = "button";
    button.id = `notification-tab-${name}`;
    button.className = "notification-flyout-tab";
    button.textContent = notificationSectionLabel(name);
    button.setAttribute("role", "tab");
    button.setAttribute("aria-controls", "cockpitNotificationFlyoutPanel");
    button.addEventListener("click", () => selectSection(name));
    return button;
  }

  function open(nextPayload, options = {}) {
    payload = {
      critical: Array.isArray(nextPayload?.critical) ? nextPayload.critical : [],
      informational: Array.isArray(nextPayload?.informational) ? nextPayload.informational : [],
    };
    section = META[options.section] ? options.section : "critical";
    trigger = options.trigger || document.activeElement;
    trigger?.setAttribute?.("aria-expanded", "true");
    render();
    if (!dialog.open) dialog.showModal();
    closeButton.focus();
  }

  function selectSection(next) { section = META[next] ? next : "critical"; render(); }
  function close() { if (dialog.open) dialog.close(); }
  function render() {
    status.textContent = "";
    title.textContent = notificationSectionLabel(section);
    for (const [tab, name] of [[criticalTab, "critical"], [informationalTab, "informational"]]) {
      const selected = name === section;
      tab.setAttribute("aria-selected", String(selected));
      tab.tabIndex = selected ? 0 : -1;
    }
    body.setAttribute("aria-labelledby", section === "critical" ? criticalTab.id : informationalTab.id);
    body.replaceChildren();
    const items = payload[section];
    if (!items.length) {
      const empty = document.createElement("p");
      empty.className = "notification-flyout-empty";
      empty.textContent = notificationEmptyMessage(section);
      body.append(empty);
    } else {
      const list = document.createElement("div");
      list.className = "notification-flyout-list";
      list.setAttribute("role", "list");
      items.forEach((item) => list.append(renderItem(item)));
      body.append(list);
    }
    markSeenButton.hidden = section === "critical" || !items.some((item) => !item.seen);
  }

  function renderItem(item) {
    const article = document.createElement("article");
    article.className = `notification-flyout-item notification-${section}`;
    article.setAttribute("role", "listitem");
    if (item.seen) article.dataset.seen = "true";
    const heading = document.createElement("h3"); heading.textContent = item.title || "Notificação";
    const description = document.createElement("p"); description.textContent = item.description || "";
    const time = document.createElement("time"); time.dateTime = item.date_or_period || ""; time.textContent = item.date_or_period || "";
    article.append(heading, description, time);
    if (item.action?.label) {
      const action = document.createElement("button");
      action.type = "button"; action.className = "ghost small-button notification-flyout-action";
      action.textContent = item.action.label;
      action.addEventListener("click", async () => {
        action.disabled = true;
        try {
          await onAction?.(item.action, item);
          close();
        } catch {
          status.textContent = "Não foi possível abrir o destino. Tente novamente.";
        } finally { action.disabled = false; }
      });
      article.append(action);
    }
    return article;
  }

  async function markSeen() {
    const unseen = payload.informational.filter((item) => !item.seen);
    if (!unseen.length) return;
    markSeenButton.disabled = true;
    try {
      await onMarkSeen?.(unseen.map((item) => item.id));
      unseen.forEach((item) => { item.seen = true; });
      render();
    } catch {
      status.textContent = "Não foi possível marcar os informativos. Tente novamente.";
    } finally { markSeenButton.disabled = false; }
  }

  closeButton.addEventListener("click", close);
  markSeenButton.addEventListener("click", markSeen);
  dialog.addEventListener("click", (event) => { if (event.target === dialog) close(); });
  dialog.addEventListener("cancel", (event) => { event.preventDefault(); close(); });
  dialog.addEventListener("close", () => {
    trigger?.setAttribute?.("aria-expanded", "false");
    trigger?.focus?.();
    trigger = null;
  });
  return { open, close, selectSection, destroy() { close(); dialog.remove(); }, element: dialog };
}
