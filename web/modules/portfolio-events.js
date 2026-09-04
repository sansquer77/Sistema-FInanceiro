import { stateMarkup } from "./dom-utils.js";
import { destroyVirtualLists, renderCollectionRows } from "./virtual-list.js";

const EVENTS_TTL_MS = 30 * 60 * 1000;

export function createPortfolioEvents({ state, container, refreshButton, api, escapeHtml, formatDate }) {
  let requestId = 0;

  refreshButton?.addEventListener("click", () => load({ force: true }));

  function assetFingerprint() {
    return (state.portfolio?.positions || [])
      .filter((position) => position.asset_type === "stock")
      .map((position) => [
        position.asset_identifier || "",
        position.currency || "BRL",
        position.first_operation_date || "",
      ].join(":"))
      .sort()
      .join("|");
  }

  async function load({ force = false } = {}) {
    const fingerprint = assetFingerprint();
    if (!fingerprint) {
      state.portfolioEvents = null;
      state.portfolioEventsFingerprint = "";
      render();
      return;
    }
    const fresh = state.portfolioEvents
      && state.portfolioEventsFingerprint === fingerprint
      && Date.now() - state.portfolioEventsLoadedAt < EVENTS_TTL_MS;
    if (!force && fresh) {
      render();
      return;
    }
    if (state.portfolioEventsLoading) return;
    const currentRequest = ++requestId;
    state.portfolioEventsLoading = true;
    if (refreshButton) refreshButton.disabled = true;
    container?.setAttribute("aria-busy", "true");
    if (container) container.innerHTML = stateMarkup("Consultando eventos dos ativos da carteira.", { kind: "loading" });
    try {
      const response = await api(`/api/portfolio/events${force ? "?refresh=1" : ""}`);
      if (currentRequest !== requestId) return;
      state.portfolioEvents = response;
      state.portfolioEventsFingerprint = fingerprint;
      state.portfolioEventsLoadedAt = Date.now();
      render();
    } catch (error) {
      if (currentRequest !== requestId || !container) return;
      container.innerHTML = stateMarkup(`Não foi possível carregar os eventos: ${error.message}`, { kind: "error" });
    } finally {
      if (currentRequest === requestId) {
        state.portfolioEventsLoading = false;
        if (refreshButton) refreshButton.disabled = false;
        container?.setAttribute("aria-busy", "false");
      }
    }
  }

  function render() {
    if (!container) return;
    destroyVirtualLists(container);
    const eligible = (state.portfolio?.positions || []).some((position) => position.asset_type === "stock");
    if (!eligible) {
      container.innerHTML = stateMarkup("Adicione uma ação, ETF ou BDR para consultar eventos históricos.", { kind: "empty", compact: false });
      return;
    }
    const payload = state.portfolioEvents;
    if (!payload) {
      container.innerHTML = stateMarkup("Abra esta aba para consultar os eventos históricos da carteira.", { kind: "info" });
      return;
    }
    const events = payload.events || [];
    const unavailable = payload.unavailable || [];
    const notice = unavailable.length ? `
      <p class="portfolio-events-warning" role="status">
        ${unavailable.length} ativo(s) com eventos temporariamente indisponíveis: ${unavailable.map((item) => escapeHtml(item.asset_identifier)).join(", ")}.
      </p>
    ` : "";
    if (!events.length) {
      container.innerHTML = `${notice}${stateMarkup("Nenhum provento histórico foi detectado para os ativos atuais desde a primeira aquisição.", { kind: "empty", compact: false })}`;
      return;
    }
    const groups = new Map();
    events.forEach((event) => {
      const key = String(event.date || event.payment_date || "").slice(0, 7) || "Sem competência";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(event);
    });
    container.innerHTML = `${notice}<div class="portfolio-events-scroll">${[...groups].map(([month, rows], index) => `
      <section class="portfolio-events-month" aria-labelledby="portfolio-events-month-${index}">
        <h3 id="portfolio-events-month-${index}">${formatMonth(month)}</h3>
        <div class="portfolio-events-grid" role="table" aria-label="Eventos de ${escapeHtml(formatMonth(month))}" aria-rowcount="${rows.length}">
          <div class="portfolio-events-grid-header" role="row">
            <span role="columnheader">Data ex</span><span role="columnheader">Pagamento</span>
            <span role="columnheader">Ativo</span><span role="columnheader">Carteira</span>
            <span role="columnheader">Evento</span><span role="columnheader">Valor por cota/ação</span>
            <span role="columnheader">Confirmação</span>
          </div>
          <div class="portfolio-events-list" role="rowgroup" data-month-index="${index}"></div>
        </div>
      </section>`).join("")}</div>
      <p class="portfolio-footnote">Fonte: Yahoo Finance. A data principal é a Data ex; o app não estima o valor total e não substitui comunicados oficiais do emissor.</p>
    `;
    [...groups.values()].forEach((rows, index) => renderCollectionRows(container.querySelector(`[data-month-index="${index}"]`), rows, {
      threshold: 60, rowHeight: 64, viewportHeight: 560, renderItem: eventRow,
    }));
  }

  function eventRow(event) {
    const paymentDate = event.payment_date ? formatDate(event.payment_date) : "Não informada";
    const amount = event.amount_per_share_micros == null ? `Não informado (${escapeHtml(event.currency || "BRL")})` : formatUnitAmount(event.amount_per_share_micros, event.currency);
    const portfolios = (event.portfolio_names || []).join(", ") || "Carteira não informada";
    return `<div class="portfolio-events-grid-row" role="row">
      <span role="cell">${formatDate(event.date)}</span>
      <span role="cell" class="portfolio-event-payment-date">${paymentDate}</span>
      <span role="cell" class="portfolio-event-asset"><strong>${escapeHtml(event.asset_identifier)}</strong><small>${escapeHtml(event.asset_name)}</small></span>
      <span role="cell">${escapeHtml(portfolios)}</span>
      <span role="cell">${escapeHtml(event.event_label)}</span>
      <span role="cell" class="money-cell">${amount}</span>
      <span role="cell"><span class="portfolio-event-confirmation">${escapeHtml(event.confirmation_label)}</span></span>
    </div>`;
  }

  function formatMonth(value) {
    if (!/^\d{4}-\d{2}$/.test(value)) return value;
    const [year, month] = value.split("-").map(Number);
    return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("pt-BR", { month: "long", year: "numeric", timeZone: "UTC" });
  }

  function formatUnitAmount(amountMicros, currency) {
    const value = Number(amountMicros || 0) / 1_000_000;
    return value.toLocaleString("pt-BR", {
      style: "currency",
      currency: currency || "BRL",
      minimumFractionDigits: 2,
      maximumFractionDigits: 6,
    });
  }

  function invalidate() {
    state.portfolioEventsLoadedAt = 0;
    state.portfolioEventsFingerprint = "";
  }

  function clearPresentation() {
    requestId += 1;
    state.portfolioEventsLoading = false;
    if (refreshButton) refreshButton.disabled = false;
    destroyVirtualLists(container);
    container?.replaceChildren();
    container?.setAttribute("aria-busy", "false");
  }

  return { load, render, invalidate, clearPresentation };
}
