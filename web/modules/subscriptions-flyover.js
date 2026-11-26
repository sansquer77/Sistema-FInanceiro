// spec: tendencias-saude-financeira v2.28 — critérios 56 a 60
export function createSubscriptionsFlyover({ formatMoney, escapeHtml, formatDate }) {
  const dialog = document.createElement("dialog");
  dialog.className = "subscription-flyover";
  dialog.setAttribute("aria-labelledby", "subscriptionFlyoverTitle");
  document.body.appendChild(dialog);
  let restoreFocus = null;

  dialog.addEventListener("close", () => {
    restoreFocus?.focus?.();
    restoreFocus = null;
  });

  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) dialog.close();
  });

  function open(payload = {}) {
    restoreFocus = document.activeElement;
    const items = Array.isArray(payload.itens) ? payload.itens : [];
    dialog.innerHTML = `
      <div class="subscription-flyover-shell">
        <header class="subscription-flyover-header">
          <div>
            <span class="eyebrow">TENDÊNCIAS · ASSINATURAS</span>
            <h2 id="subscriptionFlyoverTitle">Assinaturas e serviços recorrentes</h2>
            <p>Leitura analítica dos lançamentos recorrentes classificados no mês. Nenhum serviço é criado ou reclassificado aqui.</p>
          </div>
          <button class="icon-button" type="button" data-subscription-close aria-label="Fechar painel">×</button>
        </header>
        <section class="subscription-flyover-totals" aria-label="Resumo de assinaturas">
          <div><span>Total mensal</span><strong>${formatMoney(Number(payload.total_mensal_cents || 0) / 100, "BRL")}</strong></div>
          <div><span>Estimativa anual</span><strong>${formatMoney(Number(payload.estimativa_anual_cents || 0) / 100, "BRL")}</strong></div>
        </section>
        ${items.length ? `
          <section class="subscription-flyover-list" aria-label="Serviços recorrentes">
            ${items.map(renderItem).join("")}
          </section>
        ` : `<div class="subscription-flyover-empty">Não há lançamentos recorrentes identificáveis neste mês.</div>`}
        <footer class="subscription-flyover-footer">A identificação usa apenas descrição, recorrência, categoria e origem já registrados no sistema.</footer>
      </div>
    `;
    dialog.querySelector("[data-subscription-close]")?.addEventListener("click", () => dialog.close());
    if (!dialog.open) dialog.showModal();
  }

  function renderItem(item) {
    const origins = (item.origens || []).map((origin) => `${origin.tipo === "cartao" ? "Cartão" : "Conta"}: ${origin.nome}`).join(" · ") || "Origem não informada";
    const nextLaunch = item.proximo_lancamento ? formatDate(item.proximo_lancamento) : "Não disponível";
    const confidenceClass = item.confianca === "alta" ? "high" : item.confianca === "baixa" ? "low" : "medium";
    return `
      <article class="subscription-flyover-item">
        <div class="subscription-flyover-item-main">
          <div>
            <h3>${escapeHtml(item.servico || "Cobrança recorrente")}</h3>
            <span>${escapeHtml(item.categoria || "Assinaturas e Serviços")} · ${escapeHtml(item.subcategoria || "Geral")}</span>
          </div>
          <strong>${formatMoney(Number(item.valor_mensal_cents || 0) / 100, "BRL")}</strong>
        </div>
        <div class="subscription-flyover-item-meta">
          <span><b>Periodicidade</b>${escapeHtml(item.periodicidade_label || "Mensal")}</span>
          <span><b>Próximo lançamento</b>${escapeHtml(nextLaunch)}</span>
          <span><b>Origem</b>${escapeHtml(origins)}</span>
          <span><b>Confiança</b><em class="subscription-confidence ${confidenceClass}">${escapeHtml(item.confianca_label || "Intermediária")}</em></span>
        </div>
      </article>
    `;
  }

  return { open };
}
