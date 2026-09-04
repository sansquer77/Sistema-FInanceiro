import { stateMarkup } from "./dom-utils.js";

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
    container.innerHTML = `${notice}
      <div class="report-table-wrap">
        <table class="report-table portfolio-events-table">
          <thead><tr><th>Data</th><th>Ativo</th><th>Evento</th><th>Valor por cota/ação</th><th>Fonte</th><th>Confirmação</th></tr></thead>
          <tbody>${events.map(eventRow).join("")}</tbody>
        </table>
      </div>
      <p class="portfolio-footnote">Eventos detectados pelo provedor. O app não estima o valor total e não substitui comunicados oficiais do emissor.</p>
    `;
  }

  function eventRow(event) {
    return `<tr>
      <td>${formatDate(event.date)}</td>
      <td><strong>${escapeHtml(event.asset_identifier)}</strong><span>${escapeHtml(event.asset_name)}</span></td>
      <td>${escapeHtml(event.event_label)}</td>
      <td class="money-cell">${formatUnitAmount(event.amount_per_share_micros, event.currency)}</td>
      <td>${escapeHtml(event.source)}</td>
      <td><span class="portfolio-event-confirmation">${escapeHtml(event.confirmation_label)}</span></td>
    </tr>`;
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
    container?.replaceChildren();
    container?.setAttribute("aria-busy", "false");
  }

  return { load, render, invalidate, clearPresentation };
}
