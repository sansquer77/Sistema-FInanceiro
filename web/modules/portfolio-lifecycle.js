const REVALIDATE_AFTER_MS = 30_000;

export function canReusePortfolioSnapshot(state, options, now = Date.now()) {
  const fresh = state.portfolioLoadedAt > 0 && now - state.portfolioLoadedAt < REVALIDATE_AFTER_MS;
  return Boolean(state.portfolio && !state.portfolioDirty && !options.force
    && !options.refreshMessage && (!options.revalidate || fresh));
}

export function clearPortfolioPresentation(...elements) {
  elements.forEach((element) => element?.replaceChildren());
}
