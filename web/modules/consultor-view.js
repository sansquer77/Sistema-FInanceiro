// spec: cockpit-calendario v0.6 — critérios 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17 e 18
export function registerConsultorView({
  elements,
  api,
  formatMoney,
  formatDate,
  escapeHtml,
  emptyState,
  onNavigateToTransaction,
  onNavigateToPortfolio,
}) {
  const {
    cockpitCalendarPanel,
    cockpitCalendarMeta,
    overdueReceivablesList,
    overduePayablesList,
    maturity30DaysList,
    maturity60DaysList,
  } = elements;
  let requestId = 0;
  let currentData = null;
  let loading = false;
  let error = "";

  function renderCalendar(force = false) {
    if (!cockpitCalendarPanel) {
      return;
    }
    if (!currentData || force) {
      loadCalendar();
    }
    render();
  }

  async function loadCalendar() {
    const callId = ++requestId;
    loading = true;
    error = "";
    render();
    try {
      const response = await api("/api/cockpit/calendar");
      if (callId !== requestId) {
        return;
      }
      currentData = response;
      loading = false;
    } catch (err) {
      if (callId !== requestId) {
        return;
      }
      loading = false;
      error = err.message || "Falha ao carregar dados do calendário.";
    }
    render();
  }

  function render() {
    if (!cockpitCalendarPanel) {
      return;
    }
    renderAIActiveBadge();
    if (!currentData) {
      if (error) {
        setAllContainers(emptyState(error, true));
        return;
      }
      setAllContainers(emptyState("Carregando dados do calendário...", true));
      return;
    }
    const cards = [
      {
        container: overdueReceivablesList,
        items: currentData.overdue_receivables || [],
        empty: "Nenhuma conta a receber atrasada.",
        totalsKey: "overdue_receivables_cents",
        renderItem: (item) => renderOverdueItem(item, "receivable"),
      },
      {
        container: overduePayablesList,
        items: currentData.overdue_payables || [],
        empty: "Nenhuma conta a pagar atrasada.",
        totalsKey: "overdue_payables_cents",
        renderItem: (item) => renderOverdueItem(item, "payable"),
      },
      {
        container: maturity30DaysList,
        items: currentData.maturity_30_days || [],
        empty: "Nenhum vencimento em 30 dias.",
        totalsKey: "maturity_30_days_cents",
        renderItem: (item) => renderMaturityItem(item),
      },
      {
        container: maturity60DaysList,
        items: currentData.maturity_60_days || [],
        empty: "Nenhum vencimento em 60 dias.",
        totalsKey: "maturity_60_days_cents",
        renderItem: (item) => renderMaturityItem(item),
      },
    ];
    cards.forEach((card) => {
      try {
        renderCalendarCard(card);
      } catch (err) {
        if (card.container) {
          card.container.innerHTML = "";
          card.container.append(emptyState(card.empty, true));
          const totalsEl = card.container.closest(".calendar-card")?.querySelector(".calendar-card-totals");
          if (totalsEl) {
            totalsEl.innerHTML = "";
          }
        }
      }
    });
  }

  function renderAIActiveBadge() {
    if (!cockpitCalendarMeta) {
      return;
    }
    const active = currentData && currentData.ia_ativa === true;
    cockpitCalendarMeta.innerHTML = active
      ? '<span class="trends-ai-badge">IA ativa</span>'
      : "";
  }

  function setAllContainers(element) {
    [overdueReceivablesList, overduePayablesList, maturity30DaysList, maturity60DaysList].forEach((container) => {
      if (container) {
        container.innerHTML = "";
        container.append(element.cloneNode(true));
        const totalsEl = container.closest(".calendar-card")?.querySelector(".calendar-card-totals");
        if (totalsEl) {
          totalsEl.innerHTML = "";
        }
      }
    });
  }

  function renderCalendarCard({ container, items, empty, totalsKey, renderItem }) {
    if (!container) {
      return;
    }
    const totals = buildTotalsByCurrency(currentData, totalsKey);
    const totalsEl = container.closest(".calendar-card")?.querySelector(".calendar-card-totals");
    if (totalsEl) {
      totalsEl.innerHTML = totals.size
        ? [...totals.entries()].map(([currency, amount]) => `<span>${escapeHtml(currency)}: <strong>${formatMoney(amount, currency)}</strong></span>`).join("")
        : "";
    }
    if (!items.length) {
      container.innerHTML = "";
      container.append(emptyState(empty, true));
      return;
    }
    container.innerHTML = `
      <div class="calendar-card-items">${items.map((item) => renderItem(item)).join("")}</div>
    `;
    container.querySelectorAll("[data-calendar-transaction-id]").forEach((button) => {
      button.addEventListener("click", () => {
        if (typeof onNavigateToTransaction === "function") {
          onNavigateToTransaction(
            button.dataset.calendarTransactionId,
            button.dataset.calendarAccountId,
            button.dataset.calendarTransactionDate,
          );
        }
      });
    });
    container.querySelectorAll("[data-calendar-position-id]").forEach((button) => {
      button.addEventListener("click", () => onNavigateToPortfolio(button.dataset.calendarPositionId));
    });
  }

  function buildTotalsByCurrency(payload, totalsKey) {
    const totalsByCurrency = new Map();
    for (const item of payload.totals_by_currency || []) {
      const amount = Number(item[totalsKey] || 0);
      if (amount === 0) {
        continue;
      }
      totalsByCurrency.set(item.currency || "BRL", amount / 100);
    }
    return totalsByCurrency;
  }

  function renderOverdueItem(item, kind) {
    const label = kind === "receivable" ? "Receber" : "Pagar";
    const description = item.description || "Sem descrição";
    const detail = `${formatDate(item.date)} · ${item.account_name || "Conta"} · ${item.days_overdue} dias de atraso`;
    return `
      <button class="calendar-item-row" type="button" data-calendar-transaction-id="${escapeHtml(String(item.id))}" data-calendar-account-id="${escapeHtml(String(item.account_id || ""))}" data-calendar-transaction-date="${escapeHtml(String(item.date || ""))}">
        <div>
          <strong>${escapeHtml(description)}</strong>
          <small>${escapeHtml(detail)}</small>
        </div>
        <div>
          <span>${escapeHtml(label)}</span>
          <strong>${formatMoney(Number(item.amount_cents || 0) / 100, item.currency || "BRL")}</strong>
        </div>
      </button>
    `;
  }

  function renderMaturityItem(item) {
    const description = item.asset_name || item.asset_identifier || "Ativo sem identificação";
    const detail = `${formatDate(item.maturity_date)} · ${item.account_name || "Carteira"} · ${item.days_to_maturity} dias`;
    return `
      <button class="calendar-item-row" type="button" data-calendar-position-id="${escapeHtml(String(item.position_id))}">
        <div>
          <strong>${escapeHtml(description)}</strong>
          <small>${escapeHtml(detail)}</small>
        </div>
        <div>
          <span>Valor</span>
          <strong>${formatMoney(Number(item.current_value_cents || 0) / 100, item.currency || "BRL")}</strong>
        </div>
      </button>
    `;
  }

  function invalidateCalendar() {
    requestId += 1;
    currentData = null;
    loading = false;
    error = "";
  }

  return {
    renderCalendar,
    invalidateCalendar,
  };
}
