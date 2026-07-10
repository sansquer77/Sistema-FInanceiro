export const THEME_STORAGE_KEY = "sistemaFinanceiro.theme";

export const THEMES = Object.freeze({
  LIGHT: "light",
  DARK: "dark",
});

const THEME_VALUES = new Set(Object.values(THEMES));

export function normalizeTheme(value) {
  return THEME_VALUES.has(value) ? value : THEMES.LIGHT;
}

export function storedTheme() {
  try {
    return normalizeTheme(localStorage.getItem(THEME_STORAGE_KEY));
  } catch (error) {
    return THEMES.LIGHT;
  }
}

export function applyTheme(theme = storedTheme()) {
  const normalizedTheme = normalizeTheme(theme);
  const root = document.documentElement;
  root.dataset.theme = normalizedTheme;
  root.style.colorScheme = normalizedTheme;
  return normalizedTheme;
}

export function setTheme(theme) {
  const normalizedTheme = applyTheme(theme);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, normalizedTheme);
  } catch (error) {
    // Theme persistence is a UI preference; failing silently keeps the app usable.
  }
  return normalizedTheme;
}
