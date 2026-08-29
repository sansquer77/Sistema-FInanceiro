const DENSITY_STORAGE_KEY = "sistemaFinanceiro.density";

const DENSITIES = Object.freeze({
  COMFORTABLE: "comfortable",
  COMPACT: "compact",
});

const DENSITY_VALUES = new Set(Object.values(DENSITIES));

function normalizeDensity(value) {
  return DENSITY_VALUES.has(value) ? value : DENSITIES.COMFORTABLE;
}

export function storedDensity() {
  try {
    return normalizeDensity(localStorage.getItem(DENSITY_STORAGE_KEY));
  } catch (error) {
    return DENSITIES.COMFORTABLE;
  }
}

export function applyDensity(density = storedDensity()) {
  const normalizedDensity = normalizeDensity(density);
  document.documentElement.dataset.density = normalizedDensity;
  return normalizedDensity;
}

export function setDensity(density) {
  const normalizedDensity = applyDensity(density);
  try {
    localStorage.setItem(DENSITY_STORAGE_KEY, normalizedDensity);
  } catch (error) {
    // Density is an optional local UI preference; persistence must never block the app.
  }
  return normalizedDensity;
}
