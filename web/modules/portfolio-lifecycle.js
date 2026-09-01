const REVALIDATE_AFTER_MS = 30_000;

export function hasPortfolioPresentation(portfolio) {
  const model = portfolio?.presentation;
  return Boolean(Array.isArray(portfolio?.positions) && portfolio?.summary && model
    && model.sections && model.asset_groups && model.compositions && model.analysis
    && Array.isArray(model.allocation));
}

export const PORTFOLIO_COMPATIBILITY_ERROR = "O servidor retornou um Portfólio sem os dados de apresentação necessários. Reinicie o servidor da versão atual do app e tente Atualizar novamente.";

export function canReusePortfolioSnapshot(state, options, now = Date.now()) {
  const fresh = state.portfolioLoadedAt > 0 && now - state.portfolioLoadedAt < REVALIDATE_AFTER_MS;
  return Boolean(hasPortfolioPresentation(state.portfolio) && !state.portfolioDirty && !options.force
    && !options.refreshMessage && (!options.revalidate || fresh));
}

export function clearPortfolioPresentation(...elements) {
  elements.forEach((element) => element?.replaceChildren());
}
