(() => {
  const storageKey = "sistemaFinanceiro.theme";
  const themes = new Set(["light", "dark"]);
  let theme = "light";
  try {
    const storedTheme = localStorage.getItem(storageKey);
    theme = themes.has(storedTheme) ? storedTheme : "light";
  } catch (error) {
    theme = "light";
  }
  document.documentElement.dataset.theme = theme;
  document.documentElement.style.colorScheme = theme;
  try {
    document.documentElement.dataset.privacy = localStorage.getItem("sistemaFinanceiro.privacyMode") === "true" ? "true" : "false";
  } catch (error) {
    document.documentElement.dataset.privacy = "false";
  }
  try {
    const density = localStorage.getItem("sistemaFinanceiro.density");
    document.documentElement.dataset.density = density === "compact" ? "compact" : "comfortable";
  } catch (error) {
    document.documentElement.dataset.density = "comfortable";
  }
})();
