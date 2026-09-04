// spec: frontend-fundacao-v2 v0.17 — critérios 7 a 11
// Command Palette nativa em ES Modules. Delega ações existentes e nunca executa
// operações destrutivas diretamente. Não envia consulta à rede.

export function registerCommandPalette({
  elements,
  viewTitles,
  normalizeSearch,
  escapeHtml,
  onNavigate,
  actions,
}) {
  const { trigger, dialog, input, results, closeButton, count } = elements;
  let visibleItems = [];
  let lastActiveElement = null;

  trigger?.addEventListener("click", open);
  closeButton?.addEventListener("click", close);
  input?.addEventListener("input", scheduleRender);
  input?.addEventListener("keydown", handleInputKeydown);
  results?.addEventListener("click", handleResultClick);
  results?.addEventListener("keydown", handleResultsKeydown);
  dialog?.addEventListener("click", (event) => {
    if (event.target === dialog) close();
  });

  function commands() {
    const moduleCommands = Object.entries(viewTitles).map(([view, labels]) => ({
      id: `nav-${view}`,
      label: labels[1],
      group: labels[0] || "Navegação",
      keywords: `${labels[1]} ${labels[0]} ${view}`,
      enabled: () => true,
      run: () => onNavigate(view),
    }));

    const utilityCommands = [
      {
        id: "global-search",
        label: "Buscar em todo o app",
        group: "Busca",
        keywords: "buscar pesquisar global /",
        enabled: () => true,
        run: () => actions.openGlobalSearch?.(),
      },
      {
        id: "toggle-privacy",
        label: () => (actions.getPrivacyMode?.() ? "Mostrar valores" : "Ocultar valores"),
        group: "Preferências",
        keywords: "privacidade ocultar mostrar valores",
        enabled: () => true,
        run: () => actions.togglePrivacy?.(),
      },
      {
        id: "toggle-theme",
        label: () => (actions.getTheme?.() === "dark" ? "Tema claro" : "Tema escuro"),
        group: "Preferências",
        keywords: "tema claro escuro",
        enabled: () => true,
        run: () => actions.toggleTheme?.(),
      },
      {
        id: "toggle-density",
        label: () => (actions.getDensity?.() === "compact" ? "Densidade confortável" : "Densidade compacta"),
        group: "Preferências",
        keywords: "densidade compacta confortável",
        enabled: () => true,
        run: () => actions.toggleDensity?.(),
      },
      {
        id: "contextual-help",
        label: "Ajuda sobre esta tela",
        group: "Ajuda",
        keywords: "ajuda instruções central tópico",
        enabled: () => Boolean(actions.openContextualHelp),
        run: () => actions.openContextualHelp?.(),
      },
      {
        id: "instructions",
        label: "Central de ajuda",
        group: "Ajuda",
        keywords: "ajuda instruções central documentação",
        enabled: () => true,
        run: () => onNavigate("instructions"),
      },
    ];

    return [...moduleCommands, ...utilityCommands].filter((command) => command.enabled());
  }

  function open() {
    if (dialog.open) return;
    lastActiveElement = document.activeElement;
    input.value = "";
    dialog.showModal();
    scheduleRender();
    queueMicrotask(() => input.focus());
  }

  function close() {
    if (!dialog.open) return;
    dialog.close();
    if (lastActiveElement && document.contains(lastActiveElement)) {
      lastActiveElement.focus();
    }
  }

  function scheduleRender() {
    const query = normalizeSearch(input.value);
    const all = commands();
    if (!query) {
      visibleItems = all;
    } else {
      visibleItems = all.filter((command) => {
        const label = typeof command.label === "function" ? command.label() : command.label;
        return normalizeSearch(`${label} ${command.keywords} ${command.group}`).includes(query);
      });
    }
    render();
  }

  function render() {
    const grouped = groupBy(visibleItems, (item) => item.group);
    let itemIndex = 0;
    results.innerHTML = Object.entries(grouped)
      .map(([group, items]) => `
        <div class="command-palette-group" role="group" aria-label="${escapeHtml(group)}">
          <p class="command-palette-group-title">${escapeHtml(group)}</p>
          ${items.map((item) => {
            const id = `command-palette-item-${itemIndex}`;
            const label = typeof item.label === "function" ? item.label() : item.label;
            const html = `
              <button class="command-palette-item" type="button" role="option" id="${id}" data-command-palette-index="${itemIndex}">
                <span class="command-palette-item-label">${escapeHtml(label)}</span>
              </button>
            `;
            itemIndex += 1;
            return html;
          }).join("")}
        </div>
      `).join("");

    if (count) {
      count.textContent = visibleItems.length
        ? `${visibleItems.length} resultado${visibleItems.length === 1 ? "" : "s"}`
        : "Nenhum resultado";
    }

    updateActivedescendant();
  }

  function updateActivedescendant() {
    const focused = results.querySelector("button:focus");
    if (focused) {
      results.setAttribute("aria-activedescendant", focused.id);
    } else {
      results.removeAttribute("aria-activedescendant");
    }
  }

  function handleInputKeydown(event) {
    if (event.key !== "ArrowDown") return;
    event.preventDefault();
    results.querySelector("button")?.focus();
  }

  function handleResultClick(event) {
    const button = event.target.closest("[data-command-palette-index]");
    if (!button) return;
    const item = visibleItems[Number(button.dataset.commandPaletteIndex)];
    if (!item) return;
    close();
    item.run();
  }

  function handleResultsKeydown(event) {
    const buttons = [...results.querySelectorAll("button")];
    const index = buttons.indexOf(event.target.closest("button"));
    if (event.key === "Enter") {
      const item = visibleItems[index];
      if (item) {
        close();
        item.run();
      }
      return;
    }
    if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
    event.preventDefault();
    const nextIndex = event.key === "ArrowDown"
      ? Math.min(index + 1, buttons.length - 1)
      : Math.max(index - 1, -1);
    if (nextIndex === -1) {
      input.focus();
    } else {
      buttons[nextIndex]?.focus();
    }
    updateActivedescendant();
  }

  function groupBy(array, keyFn) {
    const result = {};
    for (const item of array) {
      const key = keyFn(item);
      (result[key] ||= []).push(item);
    }
    return result;
  }

  return { open, close };
}
