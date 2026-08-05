// spec: docs/specs/instrucoes-app.md v1.3 — view da central de ajuda
// View pura de apresentação: não realiza chamadas de API nem altera dados financeiros.

import {
  findTopicById,
  getInstructionGroups,
  searchInstructions,
} from "./instructions-content.js";

const INTRO_TEXT = "Use a busca abaixo para encontrar rapidamente um tópico, ou navegue pelos grupos para explorar as instruções. Clique em um tópico para expandir e ler os passos.";

function debounce(fn, delay) {
  let timer = null;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), delay);
  };
}

export function registerInstructionsView({
  elements,
  escapeHtml,
  emptyState,
  onNavigateToModule,
}) {
  const {
    instructionsSearch,
    instructionsClearSearch,
    instructionsGroups,
    instructionsEmpty,
  } = elements;

  let searchQuery = "";
  let expandedTopicId = null;
  let expandedGroups = new Set();

  instructionsSearch?.addEventListener(
    "input",
    debounce((event) => {
      searchQuery = event.target.value;
      renderInstructions();
    }, 120)
  );

  instructionsClearSearch?.addEventListener("click", () => {
    searchQuery = "";
    if (instructionsSearch) {
      instructionsSearch.value = "";
      instructionsSearch.focus();
    }
    renderInstructions();
  });

  instructionsGroups?.addEventListener("click", (event) => {
    const groupToggle = event.target.closest("[data-instructions-group-toggle]");
    if (groupToggle) {
      toggleGroup(groupToggle.dataset.instructionsGroupToggle);
      return;
    }

    const topicToggle = event.target.closest("[data-instructions-toggle]");
    if (topicToggle) {
      toggleTopic(topicToggle.dataset.instructionsToggle);
      return;
    }

    const navigateButton = event.target.closest("[data-instructions-navigate]");
    if (navigateButton) {
      const route = navigateButton.dataset.instructionsNavigate;
      if (route && onNavigateToModule) {
        onNavigateToModule(route);
      }
    }
  });

  function renderInstructions() {
    if (!instructionsGroups || !instructionsEmpty) {
      return;
    }

    if (instructionsSearch) {
      instructionsSearch.value = searchQuery;
    }
    if (instructionsClearSearch) {
      instructionsClearSearch.hidden = !searchQuery;
    }

    const groups = searchInstructions(searchQuery);

    if (groups.length === 0) {
      instructionsGroups.innerHTML = "";
      instructionsGroups.hidden = true;
      instructionsEmpty.hidden = false;
      instructionsEmpty.innerHTML = "";
      instructionsEmpty.append(emptyState("Nenhum tópico encontrado para esta busca."));
      return;
    }

    instructionsGroups.hidden = false;
    instructionsEmpty.hidden = true;

    const hasSearch = searchQuery.trim().length > 0;
    if (hasSearch) {
      // Durante uma busca, expande automaticamente todos os grupos com resultados.
      for (const group of groups) {
        expandedGroups.add(group.id);
      }
    }

    const fragment = document.createDocumentFragment();

    const intro = document.createElement("p");
    intro.className = "instructions-intro";
    intro.textContent = INTRO_TEXT;
    fragment.append(intro);

    for (const group of groups) {
      fragment.append(renderGroup(group, hasSearch));
    }

    instructionsGroups.innerHTML = "";
    instructionsGroups.append(fragment);
  }

  function renderGroup(group, hasSearch) {
    const isExpanded = expandedGroups.has(group.id) || hasSearch;
    const contentId = `instructions-group-content-${escapeHtml(group.id)}`;

    const section = document.createElement("section");
    section.className = "instructions-group";
    section.dataset.groupId = group.id;

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "instructions-group-toggle";
    toggle.dataset.instructionsGroupToggle = group.id;
    toggle.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    toggle.setAttribute("aria-controls", contentId);
    toggle.innerHTML = `
      <span class="instructions-group-title">${escapeHtml(group.title)}</span>
      <span class="instructions-group-count">${group.topics.length} tópico${group.topics.length === 1 ? "" : "s"}</span>
      <span class="instructions-group-chevron" aria-hidden="true">${isExpanded ? "−" : "+"}</span>
    `;

    const content = document.createElement("div");
    content.id = contentId;
    content.className = "instructions-group-content";
    if (!isExpanded) {
      content.hidden = true;
    }

    const list = document.createElement("div");
    list.className = "instructions-topic-list";
    for (const topic of group.topics) {
      list.append(renderTopic(topic, group.id));
    }
    content.append(list);

    section.append(toggle, content);
    return section;
  }

  function renderTopic(topic, groupId) {
    const isExpanded = expandedTopicId === topic.id;
    const contentId = `instructions-topic-content-${escapeHtml(topic.id)}`;
    const hasRoute = Boolean(topic.route);

    const article = document.createElement("article");
    article.className = "instructions-topic";
    article.dataset.topicId = topic.id;
    article.dataset.groupId = groupId;

    const toggle = document.createElement("button");
    toggle.type = "button";
    toggle.className = "instructions-topic-toggle";
    toggle.dataset.instructionsToggle = topic.id;
    toggle.setAttribute("aria-expanded", isExpanded ? "true" : "false");
    toggle.setAttribute("aria-controls", contentId);
    toggle.innerHTML = `
      <span class="instructions-topic-title">${escapeHtml(topic.title)}</span>
      <span class="instructions-topic-summary">${escapeHtml(topic.summary)}</span>
      <span class="instructions-topic-chevron" aria-hidden="true">${isExpanded ? "−" : "+"}</span>
    `;

    const content = document.createElement("div");
    content.id = contentId;
    content.className = "instructions-topic-content";
    if (!isExpanded) {
      content.hidden = true;
    }

    for (const paragraph of topic.content) {
      const p = document.createElement("p");
      p.textContent = paragraph;
      content.append(p);
    }

    if (hasRoute) {
      const actions = document.createElement("div");
      actions.className = "instructions-topic-actions";
      actions.innerHTML = `
        <button type="button" class="primary small-button" data-instructions-navigate="${escapeHtml(topic.route)}">
          Ir para o módulo
        </button>
      `;
      content.append(actions);
    }

    article.append(toggle, content);
    return article;
  }

  function toggleGroup(groupId) {
    const willExpand = !expandedGroups.has(groupId);
    if (willExpand) {
      expandedGroups.add(groupId);
    } else {
      expandedGroups.delete(groupId);
    }

    const section = instructionsGroups?.querySelector(`[data-group-id="${CSS.escape(groupId)}"]`);
    if (!section) return;

    const toggle = section.querySelector("[data-instructions-group-toggle]");
    const content = section.querySelector(".instructions-group-content");
    if (toggle && content) {
      toggle.setAttribute("aria-expanded", willExpand ? "true" : "false");
      const chevron = toggle.querySelector(".instructions-group-chevron");
      if (chevron) chevron.textContent = willExpand ? "−" : "+";
      content.hidden = !willExpand;
    }
  }

  function toggleTopic(topicId) {
    const willExpand = expandedTopicId !== topicId;
    const previousTopicId = expandedTopicId;
    expandedTopicId = willExpand ? topicId : null;

    // Fecha o tópico anterior sem re-renderizar tudo.
    if (previousTopicId && previousTopicId !== topicId) {
      updateTopicVisualState(previousTopicId, false);
    }

    updateTopicVisualState(topicId, willExpand);

    if (willExpand) {
      const topicElement = instructionsGroups?.querySelector(`[data-topic-id="${CSS.escape(topicId)}"]`);
      topicElement?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  function updateTopicVisualState(topicId, isExpanded) {
    const article = instructionsGroups?.querySelector(`[data-topic-id="${CSS.escape(topicId)}"]`);
    if (!article) return;

    const toggle = article.querySelector("[data-instructions-toggle]");
    const content = article.querySelector(".instructions-topic-content");
    if (toggle && content) {
      toggle.setAttribute("aria-expanded", isExpanded ? "true" : "false");
      const chevron = toggle.querySelector(".instructions-topic-chevron");
      if (chevron) chevron.textContent = isExpanded ? "−" : "+";
      content.hidden = !isExpanded;
    }
  }

  function openTopic(topicId) {
    if (!findTopicById(topicId)) {
      return;
    }
    expandedTopicId = topicId;
    searchQuery = "";
    if (instructionsSearch) {
      instructionsSearch.value = "";
    }
    // Expande o grupo do tópico aberto.
    for (const group of getInstructionGroups()) {
      if (group.topics.some((topic) => topic.id === topicId || topic.contextualTopicId === topicId)) {
        expandedGroups.add(group.id);
      }
    }
    renderInstructions();
    const topicElement = instructionsGroups?.querySelector(`[data-topic-id="${CSS.escape(topicId)}"]`);
    topicElement?.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  return {
    renderInstructions,
    openTopic,
  };
}
