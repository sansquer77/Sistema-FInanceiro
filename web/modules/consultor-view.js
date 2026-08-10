// spec: cockpit-calendario v0.7 — critérios 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17 e 18
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
    consultorStatus,
    consultorCardGrid,
    consultorOutput,
    consultorHistoryList,
    consultorHistoryRefreshButton,
    overdueReceivablesList,
    overduePayablesList,
    maturity30DaysList,
    maturity60DaysList,
  } = elements;
  let requestId = 0;
  let currentData = null;
  let consultorConfig = null;
  let consultorHistory = [];
  let consultorLoading = false;
  let runningAnalysisId = "";
  let loading = false;
  let error = "";

  function renderCalendar(force = false) {
    if (!cockpitCalendarPanel) {
      return;
    }
    if (!currentData || force) {
      loadCalendar();
    }
    if (!consultorConfig || force) {
      loadConsultor();
    }
    render();
  }

  async function loadConsultor() {
    consultorLoading = true;
    renderConsultor();
    try {
      const [config, history] = await Promise.all([
        api("/api/consultor/config"),
        api("/api/consultor/history?limit=20"),
      ]);
      consultorConfig = config;
      consultorHistory = history.history || [];
    } catch (err) {
      consultorConfig = { available: false, blocked_reason: "load_error", cards: [] };
      consultorHistory = [];
      if (consultorStatus) {
        consultorStatus.innerHTML = `<div class="empty-state compact">${escapeHtml(err.message || "Falha ao carregar Consultor.")}</div>`;
      }
    } finally {
      consultorLoading = false;
      renderConsultor();
    }
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
    renderConsultor();
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

  function renderConsultor() {
    if (!consultorCardGrid || !consultorStatus) {
      return;
    }
    if (consultorLoading && !consultorConfig) {
      consultorStatus.innerHTML = '<div class="empty-state compact">Carregando Consultor...</div>';
      consultorCardGrid.innerHTML = "";
      renderConsultorHistory();
      return;
    }
    const config = consultorConfig || {};
    consultorStatus.innerHTML = renderConsultorStatus(config);
    if (!config.available) {
      consultorCardGrid.innerHTML = "";
      if (consultorOutput) {
        consultorOutput.hidden = true;
        consultorOutput.innerHTML = "";
      }
      renderConsultorHistory();
      return;
    }
    const groups = groupCards(config.cards || []);
    consultorCardGrid.innerHTML = [...groups.entries()].map(([category, cards]) => `
      <section class="consultor-card-group">
        <h3>${escapeHtml(category)}</h3>
        <div class="consultor-analysis-grid">
          ${cards.map((card) => renderAnalysisCard(card)).join("")}
        </div>
      </section>
    `).join("");
    consultorCardGrid.querySelectorAll("[data-consultor-run]").forEach((button) => {
      button.addEventListener("click", () => runAnalysis(button.dataset.consultorRun));
    });
    renderConsultorHistory();
  }

  function renderConsultorStatus(config) {
    if (config.available) {
      return '<div class="consultor-status-ready">Consultor ativo. Escolha uma análise abaixo.</div>';
    }
    const messages = {
      ai_not_configured: "Configure e ative a IA em Preferências > APIs para usar o Consultor.",
      consultor_disabled: "Ative o Consultor em Preferências > APIs para liberar as análises.",
      consent_required: "Aceite o consentimento de dados em Preferências > APIs para usar o Consultor.",
      load_error: "Não foi possível carregar o Consultor agora.",
    };
    return `<div class="empty-state compact">${escapeHtml(messages[config.blocked_reason] || "Consultor indisponível.")}</div>`;
  }

  function groupCards(cards) {
    const groups = new Map();
    for (const card of cards) {
      const category = card.category || "Análises";
      if (!groups.has(category)) {
        groups.set(category, []);
      }
      groups.get(category).push(card);
    }
    return groups;
  }

  function renderAnalysisCard(card) {
    const isRunning = runningAnalysisId === card.analysis_id;
    const period = card.requires_period_window
      ? `<label class="consultor-period-select">Período
          <select data-consultor-period="${escapeHtml(card.analysis_id)}">
            <option value="3m">3 meses</option>
            <option value="6m">6 meses</option>
            <option value="12m">12 meses</option>
            <option value="ytd">YTD</option>
          </select>
        </label>`
      : "";
    return `
      <article class="consultor-analysis-card">
        <div>
          <strong>${escapeHtml(card.title || "Análise")}</strong>
          <p>${escapeHtml(card.short_description || "")}</p>
        </div>
        ${period}
        <button class="primary" type="button" data-consultor-run="${escapeHtml(card.analysis_id)}" ${isRunning ? "disabled" : ""}>
          ${isRunning ? "Gerando..." : "Gerar análise"}
        </button>
      </article>
    `;
  }

  async function runAnalysis(analysisId) {
    if (!analysisId || runningAnalysisId) {
      return;
    }
    runningAnalysisId = analysisId;
    renderConsultor();
    const periodSelect = [...(consultorCardGrid?.querySelectorAll("[data-consultor-period]") || [])]
      .find((select) => select.dataset.consultorPeriod === analysisId);
    const body = { analysis_id: analysisId };
    if (periodSelect) {
      body.period_window = periodSelect.value || "3m";
    }
    try {
      const result = await api("/api/consultor/analyze", { method: "POST", body });
      renderAnalysisOutput(result);
      await loadConsultor();
    } catch (err) {
      if (consultorOutput) {
        consultorOutput.hidden = false;
        consultorOutput.innerHTML = `<div class="empty-state compact">${escapeHtml(err.message || "O Consultor está indisponível no momento.")}</div>`;
      }
    } finally {
      runningAnalysisId = "";
      renderConsultor();
    }
  }

  function renderAnalysisOutput(result) {
    if (!consultorOutput) {
      return;
    }
    consultorOutput.hidden = false;
    consultorOutput.innerHTML = `
      <div class="calendar-card-heading">
        <h3>${escapeHtml(analysisTitle(result.analysis_id))}</h3>
        <span>${escapeHtml(result.created_at || "")}</span>
      </div>
      <div class="consultor-response">${formatConsultorText(result.output || "")}</div>
    `;
  }

  function renderConsultorHistory() {
    if (!consultorHistoryList) {
      return;
    }
    if (!consultorHistory.length) {
      consultorHistoryList.innerHTML = '<div class="empty-state compact">Nenhuma análise gerada ainda.</div>';
      return;
    }
    consultorHistoryList.innerHTML = consultorHistory.map((item) => `
      <button class="consultor-history-item" type="button" data-consultor-history-id="${escapeHtml(String(item.analysis_execution_id))}">
        <strong>${escapeHtml(analysisTitle(item.analysis_id))}</strong>
        <small>${escapeHtml(item.created_at || "")}</small>
      </button>
    `).join("");
    consultorHistoryList.querySelectorAll("[data-consultor-history-id]").forEach((button) => {
      button.addEventListener("click", () => {
        const item = consultorHistory.find((entry) => String(entry.analysis_execution_id) === button.dataset.consultorHistoryId);
        if (item) {
          renderAnalysisOutput({
            analysis_id: item.analysis_id,
            output: item.analysis_output,
            created_at: item.created_at,
          });
        }
      });
    });
  }

  function analysisTitle(analysisId) {
    const card = (consultorConfig?.cards || []).find((item) => item.analysis_id === analysisId);
    return card?.title || analysisId || "Análise";
  }

  function formatConsultorText(text) {
    const escaped = escapeHtml(String(text || ""));
    return escaped
      .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
      .replace(/\n{2,}/g, "</p><p>")
      .replace(/\n/g, "<br>")
      .replace(/^/, "<p>")
      .replace(/$/, "</p>");
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
    consultorConfig = null;
    consultorHistory = [];
    runningAnalysisId = "";
  }

  if (consultorHistoryRefreshButton) {
    consultorHistoryRefreshButton.addEventListener("click", loadConsultor);
  }

  return {
    renderCalendar,
    invalidateCalendar,
  };
}
