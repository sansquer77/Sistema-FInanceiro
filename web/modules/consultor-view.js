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
    consultorTabs,
    consultorAnalysesPanel,
    consultorHistoryPanel,
    consultorStatus,
    consultorCardGrid,
    consultorOutput,
    consultorHistoryList,
    consultorHistoryFilter,
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
  let selectedAnalysisId = "";
  let selectedPeriodWindow = "3m";
  let activeConsultorTab = "analyses";
  let historyFilter = "";
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
    const cards = config.cards || [];
    if (!cards.some((card) => card.analysis_id === selectedAnalysisId)) {
      selectedAnalysisId = cards[0]?.analysis_id || "";
    }
    consultorCardGrid.innerHTML = renderAnalysisSelector(cards);
    consultorCardGrid.querySelector("[data-consultor-analysis]")?.addEventListener("change", (event) => {
      selectedAnalysisId = event.target.value || "";
      renderConsultor();
    });
    consultorCardGrid.querySelector("[data-consultor-period]")?.addEventListener("change", (event) => {
      selectedPeriodWindow = event.target.value || "3m";
    });
    consultorCardGrid.querySelectorAll("[data-consultor-run]").forEach((button) => {
      button.addEventListener("click", () => runAnalysis());
    });
    renderConsultorHistory();
  }

  function setConsultorTab(tab) {
    activeConsultorTab = tab === "history" ? "history" : "analyses";
    renderConsultorTabs();
  }

  function renderConsultorTabs() {
    consultorTabs?.forEach((button) => {
      const isActive = button.dataset.consultorTab === activeConsultorTab;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-selected", String(isActive));
    });
    if (consultorAnalysesPanel) {
      consultorAnalysesPanel.hidden = activeConsultorTab !== "analyses";
    }
    if (consultorHistoryPanel) {
      consultorHistoryPanel.hidden = activeConsultorTab !== "history";
    }
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

  function renderAnalysisSelector(cards) {
    // spec: consultor/consultor v1.6 — critérios 3, 5 e 14
    // (o catálogo permanece fechado; a interface apenas concentra a escolha
    // em um seletor e mantém o período restrito ao card de ralos)
    const card = cards.find((item) => item.analysis_id === selectedAnalysisId);
    if (!card) {
      return '<div class="empty-state compact">Nenhuma análise disponível.</div>';
    }
    const isRunning = runningAnalysisId === card.analysis_id;
    const period = card.requires_period_window
      ? `<label class="consultor-period-select">Período
          <select data-consultor-period>
            <option value="3m" ${selectedPeriodWindow === "3m" ? "selected" : ""}>3 meses</option>
            <option value="6m" ${selectedPeriodWindow === "6m" ? "selected" : ""}>6 meses</option>
            <option value="12m" ${selectedPeriodWindow === "12m" ? "selected" : ""}>12 meses</option>
            <option value="ytd" ${selectedPeriodWindow === "ytd" ? "selected" : ""}>YTD</option>
          </select>
        </label>`
      : "";
    return `
      <section class="consultor-analysis-selector" aria-label="Gerar análise">
        <div class="consultor-analysis-controls">
          <label class="consultor-analysis-select">Análise
            <select data-consultor-analysis>
              ${cards.map((item) => `<option value="${escapeHtml(item.analysis_id)}" ${item.analysis_id === selectedAnalysisId ? "selected" : ""}>${escapeHtml(`${item.category || "Análises"} — ${item.title || "Análise"}`)}</option>`).join("")}
            </select>
          </label>
          ${period}
          <button class="primary" type="button" data-consultor-run ${isRunning ? "disabled" : ""}>
            ${isRunning ? "Gerando..." : "Gerar"}
          </button>
        </div>
        <p class="consultor-analysis-description">${escapeHtml(card.short_description || "")}</p>
      </section>
    `;
  }

  async function runAnalysis() {
    const analysisId = selectedAnalysisId;
    if (!analysisId || runningAnalysisId) {
      return;
    }
    runningAnalysisId = analysisId;
    renderConsultor();
    const card = (consultorConfig?.cards || []).find((item) => item.analysis_id === analysisId);
    const body = { analysis_id: analysisId };
    if (card?.requires_period_window) {
      body.period_window = selectedPeriodWindow;
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
    const filteredHistory = filteredConsultorHistory();
    if (!consultorHistory.length) {
      consultorHistoryList.innerHTML = '<div class="empty-state compact">Nenhuma análise gerada ainda.</div>';
      return;
    }
    if (!filteredHistory.length) {
      consultorHistoryList.innerHTML = '<div class="empty-state compact">Nenhuma análise encontrada para o filtro.</div>';
      return;
    }
    consultorHistoryList.innerHTML = filteredHistory.map((item) => `
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
          setConsultorTab("analyses");
        }
      });
    });
  }

  function filteredConsultorHistory() {
    const query = normalizeSearch(historyFilter);
    if (!query) {
      return consultorHistory;
    }
    return consultorHistory.filter((item) => {
      const haystack = normalizeSearch([
        analysisTitle(item.analysis_id),
        item.analysis_id,
        item.period_window,
        item.created_at,
        item.analysis_output,
      ].join(" "));
      return haystack.includes(query);
    });
  }

  function normalizeSearch(value) {
    return String(value || "")
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .toLowerCase()
      .trim();
  }

  function analysisTitle(analysisId) {
    const card = (consultorConfig?.cards || []).find((item) => item.analysis_id === analysisId);
    return card?.title || analysisId || "Análise";
  }

  function formatConsultorText(text) {
    const escaped = escapeHtml(String(text || ""));
    const lines = escaped.split("\n");
    let html = "";
    let tableRows = [];
    const flushTable = () => {
      if (!tableRows.length) {
        return;
      }
      html += `<table class="consultor-table">${tableRows
        .map((cells, index) => {
          const tag = index === 0 ? "th" : "td";
          return `<tr>${cells.map((cell) => `<${tag}>${cell}</${tag}>`).join("")}</tr>`;
        })
        .join("")}</table>`;
      tableRows = [];
    };
    for (const line of lines) {
      if (/^\|.*\|$/.test(line)) {
        const cells = line.slice(1, -1).split("|").map((cell) => cell.trim());
        if (cells.every((cell) => /^:?-+:?$/.test(cell))) {
          continue;
        }
        tableRows.push(cells);
        continue;
      }
      flushTable();
      html += line + "\n";
    }
    flushTable();
    return html
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
  consultorTabs?.forEach((button) => {
    button.addEventListener("click", () => setConsultorTab(button.dataset.consultorTab));
  });
  consultorHistoryFilter?.addEventListener("input", () => {
    historyFilter = consultorHistoryFilter.value || "";
    renderConsultorHistory();
  });
  window.addEventListener("consultor:settings-changed", () => {
    invalidateCalendar();
    loadConsultor();
  });
  renderConsultorTabs();

  return {
    renderCalendar,
    invalidateCalendar,
  };
}
