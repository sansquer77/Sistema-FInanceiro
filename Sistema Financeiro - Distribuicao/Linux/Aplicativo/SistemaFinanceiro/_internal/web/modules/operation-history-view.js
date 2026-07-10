import { api } from "./api.js";
import { escapeHtml, formData, setMessage } from "./dom-utils.js";

const MODULE_LABELS = {
  accounts: "Contas",
  transactions: "Lancamentos",
  cards: "Cartoes",
  portfolio: "Portfolio",
  imports: "Importacao",
  classifications: "Categorias",
  limits: "Limites",
  user_admin: "Usuario",
};

const TYPE_LABELS = {
  create: "Criacao",
  update: "Atualizacao",
  delete: "Exclusao",
  archive: "Arquivamento",
  restore: "Restauracao",
  reconcile: "Conciliacao",
  unreconcile: "Desconciliacao",
  move: "Movimento",
  pay: "Pagamento",
  import: "Importacao",
  redeem: "Resgate",
  close: "Encerramento",
  value_update: "Atualizacao de valor",
  clear: "Limpeza",
};

export function registerOperationHistoryView({ state, elements, formatDate }) {
  const {
    operationHistoryForm,
    operationHistoryDateFrom,
    operationHistoryDateTo,
    operationHistoryModule,
    operationHistoryType,
    operationHistoryAccount,
    operationHistoryCard,
    operationHistoryGroupBy,
    operationHistoryList,
    operationHistoryMessage,
    operationHistoryLoadMoreButton,
  } = elements;
  const pageSize = 50;
  let offset = 0;
  let loading = false;
  let currentLogs = [];
  let hasMore = false;

  operationHistoryForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadOperationLogs({ reset: true });
  });
  operationHistoryLoadMoreButton.addEventListener("click", () => loadOperationLogs({ reset: false }));
  operationHistoryGroupBy.addEventListener("change", renderLogs);

  async function loadOperationLogs({ reset = true } = {}) {
    if (loading) {
      return;
    }
    loading = true;
    setMessage(operationHistoryMessage, "", "");
    if (reset) {
      offset = 0;
      currentLogs = [];
      operationHistoryList.innerHTML = "";
    }
    operationHistoryLoadMoreButton.disabled = true;
    try {
      const params = new URLSearchParams();
      const filters = formData(operationHistoryForm);
      for (const [key, value] of Object.entries(filters)) {
        if (value) {
          params.set(key, value);
        }
      }
      params.set("limit", String(pageSize));
      params.set("offset", String(offset));
      const response = await api(`/api/operation-logs?${params.toString()}`);
      const logs = response.logs || [];
      currentLogs = reset ? logs : [...currentLogs, ...logs];
      offset += logs.length;
      hasMore = Boolean(response.has_more);
      renderLogs();
    } catch (error) {
      setMessage(operationHistoryMessage, error.message, "error");
    } finally {
      loading = false;
      operationHistoryLoadMoreButton.disabled = !hasMore;
      operationHistoryLoadMoreButton.hidden = !hasMore;
    }
  }

  function renderFilters() {
    const accountValue = operationHistoryAccount.value;
    operationHistoryAccount.innerHTML = '<option value="">Todas</option>' + state.accounts.map((account) => (
      `<option value="${account.id}">${escapeHtml(account.name)}</option>`
    )).join("");
    operationHistoryAccount.value = state.accounts.some((account) => String(account.id) === accountValue) ? accountValue : "";

    const cardValue = operationHistoryCard.value;
    operationHistoryCard.innerHTML = '<option value="">Todos</option>' + state.creditCards.map((card) => (
      `<option value="${card.id}">${escapeHtml(card.name)}</option>`
    )).join("");
    operationHistoryCard.value = state.creditCards.some((card) => String(card.id) === cardValue) ? cardValue : "";
  }

  function renderLogs() {
    if (!currentLogs.length) {
      operationHistoryList.innerHTML = '<div class="empty-state compact">Nenhuma operacao encontrada.</div>';
      return;
    }
    const grouped = groupLogs(currentLogs, operationHistoryGroupBy.value);
    operationHistoryList.innerHTML = grouped.map((group) => `
      <section class="operation-log-group">
        <h3>${escapeHtml(group.label)}</h3>
        <div class="operation-log-list">
          ${group.logs.map(renderLog).join("")}
        </div>
      </section>
    `).join("");
  }

  function renderLog(log) {
    const metadata = log.metadata || {};
    const chips = [
      log.user_name ? `Usuario: ${log.user_name}` : "",
      moduleLabel(log.module),
      typeLabel(log.operation_type),
      log.account_name ? `Conta: ${log.account_name}` : "",
      log.credit_card_name ? `Cartao: ${log.credit_card_name}` : "",
      log.operation_batch_id ? `Lote: ${log.operation_batch_id}` : "",
    ].filter(Boolean);
    return `
      <article class="operation-log-item">
        <div class="operation-log-main">
          <strong>${escapeHtml(log.description)}</strong>
          <span>${escapeHtml(formatOperationTimestamp(log.created_at))}</span>
          <div class="operation-log-chips">${chips.map((chip) => `<small>${escapeHtml(chip)}</small>`).join("")}</div>
        </div>
        <details>
          <summary>Detalhes</summary>
          <dl>
            <div><dt>Usuario</dt><dd>${escapeHtml(userLabel(log))}</dd></div>
            <div><dt>Entidade</dt><dd>${escapeHtml(log.entity_type)} ${escapeHtml(log.entity_id || "")}</dd></div>
            ${Object.entries(metadata).map(([key, value]) => `
              <div><dt>${escapeHtml(metadataLabel(key))}</dt><dd>${escapeHtml(metadataValue(key, value))}</dd></div>
            `).join("")}
          </dl>
        </details>
      </article>
    `;
  }

  function groupLogs(logs, groupBy) {
    const groups = new Map();
    for (const log of logs) {
      const label = groupLabel(log, groupBy);
      if (!groups.has(label)) {
        groups.set(label, []);
      }
      groups.get(label).push(log);
    }
    return [...groups.entries()].map(([label, logs]) => ({ label, logs }));
  }

  function groupLabel(log, groupBy) {
    if (groupBy === "module") {
      return moduleLabel(log.module);
    }
    if (groupBy === "type") {
      return typeLabel(log.operation_type);
    }
    if (groupBy === "account") {
      return log.account_name || "Sem conta";
    }
    if (groupBy === "card") {
      return log.credit_card_name || "Sem cartao";
    }
    return formatDate(log.created_at?.slice(0, 10) || "");
  }

  function formatOperationTimestamp(value) {
    if (!value) {
      return "";
    }
    return `${formatDate(value.slice(0, 10))} ${value.slice(11, 16)}`;
  }

  return {
    loadOperationLogs,
    renderFilters,
  };
}

function moduleLabel(value) {
  return MODULE_LABELS[value] || value || "-";
}

function typeLabel(value) {
  return TYPE_LABELS[value] || value || "-";
}

function userLabel(log) {
  if (log.user_name && log.user_email) {
    return `${log.user_name} <${log.user_email}>`;
  }
  return log.user_name || log.user_email || String(log.user_id || "");
}

function metadataLabel(key) {
  const labels = {
    amount: "Valor",
    date: "Data",
    type: "Tipo",
    invoice_month: "Fatura",
    series_kind: "Serie",
    changed_fields: "Campos alterados",
    changes: "Alteracoes",
  };
  return labels[key] || key;
}

function metadataValue(key, value) {
  if (key === "changes" && Array.isArray(value)) {
    if (!value.length) {
      return "Nenhuma diferenca relevante identificada.";
    }
    return value.map((change) => (
      `${change.label || change.field}: ${emptyAuditValue(change.before)} -> ${emptyAuditValue(change.after)}`
    )).join("; ");
  }
  if (Array.isArray(value)) {
    return value.map((item) => (typeof item === "object" && item !== null ? JSON.stringify(item) : item)).join(", ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value);
  }
  return value ?? "";
}

function emptyAuditValue(value) {
  const text = String(value ?? "");
  return text || "(vazio)";
}
