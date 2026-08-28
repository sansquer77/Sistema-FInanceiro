const PRIVACY_STORAGE_KEY = "sistemaFinanceiro.privacyMode";

const PRIVACY_ENABLED = "true";
const PRIVACY_DISABLED = "false";
const MONEY_TEXT_PATTERN = /([+-]?\s?(?:R\$|US\$|€|¥|£)\s?\d[\d.,]*)/g;
const SKIP_SELECTOR = [
  "script",
  "style",
  "textarea",
  "input",
  "select",
  "option",
  "svg",
  ".money-value",
  ".privacy-skip",
].join(",");

function normalizePrivacyMode(value) {
  return value === PRIVACY_ENABLED ? PRIVACY_ENABLED : PRIVACY_DISABLED;
}

function storedPrivacyMode() {
  try {
    return normalizePrivacyMode(localStorage.getItem(PRIVACY_STORAGE_KEY));
  } catch (error) {
    return PRIVACY_DISABLED;
  }
}

export function applyPrivacyMode(mode = storedPrivacyMode()) {
  // spec: privacidade-valores v1.1 — critérios 1, 3 e 5
  const normalizedMode = normalizePrivacyMode(mode);
  document.documentElement.dataset.privacy = normalizedMode;
  return normalizedMode;
}

function setPrivacyMode(mode) {
  const normalizedMode = applyPrivacyMode(mode);
  if (normalizedMode === PRIVACY_ENABLED) {
    markPrivacyMoneyValues();
  }
  try {
    localStorage.setItem(PRIVACY_STORAGE_KEY, normalizedMode);
  } catch (error) {
    // Privacy mode is a local visual preference; failing silently keeps the app usable.
  }
  return normalizedMode;
}

export function togglePrivacyMode() {
  return setPrivacyMode(document.documentElement.dataset.privacy === PRIVACY_ENABLED ? PRIVACY_DISABLED : PRIVACY_ENABLED);
}

export function isTypingTarget(target) {
  const element = target instanceof Element ? target : null;
  if (!element) {
    return false;
  }
  return Boolean(element.closest("input, textarea, select, [contenteditable='true']"));
}

export function updatePrivacyToggleButton(button, mode = document.documentElement.dataset.privacy) {
  if (!button) {
    return;
  }
  const enabled = mode === PRIVACY_ENABLED;
  const label = enabled ? "Mostrar valores" : "Ocultar valores";
  button.setAttribute("aria-label", label);
  button.setAttribute("title", `${label} (P)`);
  button.setAttribute("aria-pressed", enabled ? "true" : "false");
  button.textContent = enabled ? "🙈" : "👁️";
}

function markPrivacyMoneyValues(root = document.body) {
  // spec: privacidade-valores v1.1 — critérios 1, 4 e 7
  if (!root || document.documentElement.dataset.privacy !== PRIVACY_ENABLED) {
    return;
  }
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode(node) {
      const parent = node.parentElement;
      if (!parent || parent.closest(SKIP_SELECTOR)) {
        return NodeFilter.FILTER_REJECT;
      }
      if (!MONEY_TEXT_PATTERN.test(node.nodeValue || "")) {
        MONEY_TEXT_PATTERN.lastIndex = 0;
        return NodeFilter.FILTER_SKIP;
      }
      MONEY_TEXT_PATTERN.lastIndex = 0;
      return NodeFilter.FILTER_ACCEPT;
    },
  });

  const nodes = [];
  while (walker.nextNode()) {
    nodes.push(walker.currentNode);
  }
  nodes.forEach(wrapMoneyTextNode);
}

export function observePrivacyMoneyValues(root = document.body) {
  if (!root) {
    return () => {};
  }
  let scheduled = false;
  const scheduleMarking = () => {
    if (scheduled || document.documentElement.dataset.privacy !== PRIVACY_ENABLED) {
      return;
    }
    scheduled = true;
    window.requestAnimationFrame(() => {
      scheduled = false;
      markPrivacyMoneyValues(root);
    });
  };
  markPrivacyMoneyValues(root);
  const observer = new MutationObserver(scheduleMarking);
  observer.observe(root, {
    childList: true,
    subtree: true,
    characterData: true,
  });
  return () => observer.disconnect();
}

function wrapMoneyTextNode(node) {
  const text = node.nodeValue || "";
  MONEY_TEXT_PATTERN.lastIndex = 0;
  if (!MONEY_TEXT_PATTERN.test(text)) {
    MONEY_TEXT_PATTERN.lastIndex = 0;
    return;
  }
  MONEY_TEXT_PATTERN.lastIndex = 0;
  const fragment = document.createDocumentFragment();
  let lastIndex = 0;
  for (const match of text.matchAll(MONEY_TEXT_PATTERN)) {
    const value = match[0];
    const index = match.index || 0;
    if (index > lastIndex) {
      fragment.append(document.createTextNode(text.slice(lastIndex, index)));
    }
    const span = document.createElement("span");
    span.className = "money-value";
    span.textContent = value;
    fragment.append(span);
    lastIndex = index + value.length;
  }
  if (lastIndex < text.length) {
    fragment.append(document.createTextNode(text.slice(lastIndex)));
  }
  node.parentNode?.replaceChild(fragment, node);
}
