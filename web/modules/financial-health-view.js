// spec: score-saude-financeira v3.6 — critérios 15, 16, 17, 22, 23, 24, 25, 26, 27, 28, 29, 30 e 31
export function registerFinancialHealthView({
  elements,
  api,
  formatMoney,
  formatPercentValue,
  escapeHtml,
}) {
  const { financialHealthContent } = elements;
  let financialHealthRequestId = 0;
  let currentMonth = null;
  let currentData = null;
  let loading = false;
  let error = "";

  function renderFinancialHealth(month) {
    if (!financialHealthContent) {
      return;
    }
    if (currentMonth !== month) {
      currentMonth = month;
      currentData = null;
      error = "";
      if (loading) {
        financialHealthRequestId += 1;
        loading = false;
      }
    }
    if (!currentData || currentData.month !== month) {
      if (!loading && !error) {
        loadFinancialHealth(month);
      }
      financialHealthContent.innerHTML = `<div class="empty-state compact">${escapeHtml(error || "Carregando score de saúde financeira...")}</div>`;
      return;
    }
    const data = currentData;
    financialHealthContent.innerHTML = `
      ${financialHealthGauge(data)}

      <section class="financial-health-section">
        <h3>Seus Pilares</h3>
        <div class="financial-health-pillars" role="list" aria-label="Pontuação dos pilares de saúde financeira">
          ${(data.pilares || []).map((pillar) => financialHealthPillarBar(pillar)).join("")}
        </div>
      </section>

      <section class="financial-health-section">
        <h3>🔍 Análise detalhada dos pilares</h3>
        <div class="financial-health-detail-grid">
          ${(data.pilares || []).map((pillar) => financialHealthPillarDetail(pillar, data)).join("")}
        </div>
      </section>

      <section class="financial-health-section financial-peace-section">
        <h3>💡 Planeje sua Paz Financeira <span>(referências)</span></h3>
        ${financialPeaceCards(data)}
      </section>
    `;
  }

  async function loadFinancialHealth(month) {
    const requestId = ++financialHealthRequestId;
    loading = true;
    financialHealthContent.setAttribute("aria-busy", "true");
    error = "";
    renderFinancialHealth(month);
    try {
      const response = await api(`/api/financial-health-score?month=${encodeURIComponent(month)}`);
      if (requestId !== financialHealthRequestId) {
        return;
      }
      currentData = response;
      loading = false;
      error = "";
    } catch (err) {
      if (requestId !== financialHealthRequestId) {
        return;
      }
      loading = false;
      error = err.message || "Não foi possível carregar o score de saúde financeira.";
    }
    if (requestId === financialHealthRequestId) financialHealthContent.setAttribute("aria-busy", "false");
    renderFinancialHealth(month);
  }

  function invalidateFinancialHealth() {
    financialHealthRequestId += 1;
    currentMonth = null;
    currentData = null;
    loading = false;
    error = "";
    financialHealthContent.setAttribute("aria-busy", "false");
  }

  function financialHealthGauge(data) {
    const score = Math.max(0, Math.min(1000, Number(data.score_total || 0)));
    const ratio = score / 1000;
    const rotation = -90 + ratio * 180;
    const zone = financialHealthScoreZone(score);
    return `
      <section class="financial-health-gauge-card ${zone.className}" aria-label="Score de saúde financeira">
        <div class="financial-health-gauge-shell">
          <div
            class="financial-health-gauge"
            role="img"
            aria-label="Score ${score.toLocaleString("pt-BR")} de 1000. Status ${escapeHtml(zone.label)}."
            style="--score-ratio:${ratio.toFixed(4)}; --needle-rotation:${rotation.toFixed(2)}deg"
          >
            <div class="financial-health-gauge-arc" aria-hidden="true"></div>
            <div class="financial-health-gauge-needle" aria-hidden="true"></div>
          </div>
          <div class="financial-health-gauge-scale" aria-hidden="true">
            <span>0</span>
            <span>300</span>
            <span>500</span>
            <span>750</span>
            <span>1000</span>
          </div>
        </div>
        <div class="financial-health-gauge-copy">
          <p class="eyebrow">Diagnóstico do mês</p>
          <strong class="financial-health-gauge-score">${score.toLocaleString("pt-BR")}</strong>
          <span class="financial-health-gauge-status">${escapeHtml(zone.label)}</span>
          <h3>${escapeHtml(zone.title)}</h3>
          <p>${escapeHtml(zone.meaning)}</p>
          <div class="financial-health-zone-legend" aria-label="Faixas do score">
            <span><i class="zone-critico"></i>0–299 Crítico</span>
            <span><i class="zone-atencao"></i>300–499 Atenção</span>
            <span><i class="zone-bom"></i>500–749 Moderado</span>
            <span><i class="zone-excelente"></i>750–1000 Excelente</span>
          </div>
        </div>
      </section>
    `;
  }

  function financialHealthPillarBar(pillar) {
    const score = Number(pillar.score || 0);
    const maxScore = Number(pillar.max_score || 0);
    const percent = maxScore > 0 ? Math.max(0, Math.min(100, (score / maxScore) * 100)) : 0;
    const help = financialHealthPillarHelp(pillar);
    return `
      <article class="financial-health-pillar-row ${financialHealthLevelClass(pillar.nivel)}" role="listitem">
        <div>
          <strong class="pillar-label-with-help">
            ${escapeHtml(pillar.label || "Pilar")}
            ${help ? inlineHelpIcon(help) : ""}
          </strong>
          <span>${Number(pillar.peso_pct || 0).toLocaleString("pt-BR")}%</span>
        </div>
        <div class="financial-health-bar" aria-hidden="true">
          <i style="width:${percent.toFixed(2)}%"></i>
        </div>
        <strong>${score.toLocaleString("pt-BR")}/${maxScore.toLocaleString("pt-BR")} pts</strong>
        <small class="sr-only">${escapeHtml(pillar.label || "Pilar")}: ${score} de ${maxScore} pontos, ${percent.toFixed(1)}%.</small>
      </article>
    `;
  }

  function financialHealthPillarDetail(pillar, data) {
    const extra = financialHealthPillarExtra(pillar, data);
    const help = financialHealthPillarHelp(pillar);
    const levelLabel = financialHealthLevelLabel(pillar.nivel);
    const score = Number(pillar.score || 0).toLocaleString("pt-BR");
    const maxScore = Number(pillar.max_score || 0).toLocaleString("pt-BR");
    return `
      <details class="financial-health-detail-card ${financialHealthLevelClass(pillar.nivel)}">
        <summary>
          <span class="financial-health-status-icon">${financialHealthLevelIcon(pillar.nivel)}</span>
          <div>
            <h4>
              ${escapeHtml(pillar.label || "Pilar")}
              ${help ? inlineHelpIcon(help) : ""}
            </h4>
            <small>${escapeHtml(levelLabel)}</small>
          </div>
          <strong>${score} / ${maxScore} pts</strong>
        </summary>
        <div class="financial-health-detail-body">
          <p>Sua pontuação: <strong>${score} / ${maxScore} pts</strong>.</p>
          ${extra ? `<p>${extra}</p>` : ""}
          <p>${escapeHtml(pillar.mensagem || "Indicador calculado com base nos dados cadastrados.")}</p>
        </div>
      </details>
    `;
  }

  function inlineHelpIcon(help) {
    return `<button class="inline-help-icon" type="button" aria-label="${escapeHtml(help)}" title="${escapeHtml(help)}" data-tooltip="${escapeHtml(help)}">i</button>`;
  }

  function financialHealthPillarHelp(pillar) {
    if (pillar.id === "poupanca") {
      return "Taxa de poupança = (receitas do mês - despesas de consumo do mês) / receitas do mês. Investimentos/aportes, transferências, câmbio e pagamentos de fatura não entram como despesa de consumo.";
    }
    return "";
  }

  function financialHealthPillarExtra(pillar, data) {
    if (pillar.id === "reserva") {
      const months = Number(data.meses_reserva || pillar.meses_reserva || 0).toLocaleString("pt-BR", { maximumFractionDigits: 1 });
      return `Reserva marcada cobre <strong>${months} mês(es)</strong> de despesas médias. Valor elegível: <strong>${formatCents(data.reserva_elegivel_cents)}</strong>.`;
    }
    if (pillar.id === "endividamento") {
      return `Parcelas do mês: <strong>${formatCents(data.dividas_parcelas_mes_cents)}</strong> · comprometimento: <strong>${formatPercentValue(data.comprometimento_divida_mes_pct)}</strong>.`;
    }
    if (pillar.id === "concentracao_portfolio") {
      return `Maior concentração: <strong>${formatPercentValue(data.maior_concentracao_portfolio_pct)}</strong> · Poupança: <strong>${formatPercentValue(data.concentracao_poupanca_pct)}</strong>.`;
    }
    if (pillar.id === "poupanca") {
      return `Receitas: <strong>${formatCents(data.receitas_cents)}</strong> · despesas de consumo: <strong>${formatCents(data.despesas_consumo_cents)}</strong>.`;
    }
    return "";
  }

  function financialPeaceCards(data) {
    const peace = data.paz_financeira || {};
    const confidence = financialPeaceConfidenceLabel(data.paz_financeira_confianca);
    const base = formatCents(data.paz_financeira_base_receita_cents);
    const cards = [
      ["🎯", "Independência mensal", data.paz_independencia_cents, "Receita de referência × 175", peace.independencia_mensal_legenda || "Patrimônio estimado para gerar renda passiva mensal equivalente à receita de referência, usando heurística simplificada."],
      ["🛡️", "Reserva estimada", data.paz_reserva_estimada_cents, "Receita de referência × 6", "Referência simples de reserva baseada na receita recorrente; o pilar Reserva continua usando despesas reais e posições marcadas."],
      ["🏠", "Recorrentes saudáveis", data.paz_recorrentes_saudaveis_cents, "Receita de referência × 0,5", "Referência para observar o peso das despesas recorrentes mensais dentro da renda de base."],
      ["🎉", "Lazer saudável", data.paz_lazer_saudavel_cents, "Receita de referência × 0,3", "Referência aproximada para lazer mensal sem perder de vista o planejamento geral."],
    ];
    return `
      <div class="financial-peace-grid">
        ${cards.map(([icon, title, cents, formula, description]) => `
          <details class="financial-peace-card">
            <summary>
              <span>${icon}</span>
              <div>
                <h4>${escapeHtml(title)}</h4>
                <strong>${formatMoney(Number(cents || 0) / 100, "BRL")}</strong>
              </div>
            </summary>
            <div>
              <small>${escapeHtml(formula)}</small>
              <p>${escapeHtml(description)}</p>
              <p>Base usada: <strong>${base}</strong> · confiança ${escapeHtml(confidence)}.</p>
            </div>
          </details>
        `).join("")}
      </div>
      <p class="financial-peace-note">ⓘ Valores baseados na receita de referência (${base}) · confiança ${escapeHtml(confidence)}. ${escapeHtml(peace.aviso || "")} ${escapeHtml(peace.mensagem || "")}</p>
    `;
  }

  function formatCents(cents) {
    return formatMoney(Number(cents || 0) / 100, "BRL");
  }

  function financialHealthLevelLabel(level) {
    return ({
      critico: "Crítico",
      atencao: "Vulnerável / Atenção",
      bom: "Moderado / Em construção",
      excelente: "Excelente / Sólido",
    })[level] || "Atenção";
  }

  function financialHealthLevelIcon(level) {
    return ({
      critico: "🔴",
      atencao: "🟠",
      bom: "🟡",
      excelente: "🟢",
    })[level] || "•";
  }

  function financialHealthLevelClass(level) {
    return `level-${["critico", "atencao", "bom", "excelente"].includes(level) ? level : "atencao"}`;
  }

  function financialHealthScoreZone(score) {
    if (score < 300) {
      return {
        className: "level-critico",
        label: "Crítico",
        title: "Risco elevado",
        meaning: "Risco elevado de endividamento, ausência de reserva ou orçamento no vermelho. Pede ação imediata nos pilares mais fracos.",
      };
    }
    if (score < 500) {
      return {
        className: "level-atencao",
        label: "Vulnerável / Atenção",
        title: "Situação instável",
        meaning: "Há pouca margem de manobra; um imprevisto pode comprometer o mês. Priorize reserva, limites e redução de pressão financeira.",
      };
    }
    if (score < 750) {
      return {
        className: "level-bom",
        label: "Moderado / Em construção",
        title: "Orçamento sob controle",
        meaning: "A situação está equilibrada, com oportunidades claras para aumentar reserva, poupança ou consistência dos limites.",
      };
    }
    return {
      className: "level-excelente",
      label: "Excelente / Sólido",
      title: "Saúde financeira sólida",
      meaning: "Reserva, dívidas, limites e aportes indicam uma base financeira consistente para manter e acompanhar ao longo dos meses.",
    };
  }

  function financialPeaceConfidenceLabel(value) {
    if (value === "alta") {
      return "alta";
    }
    if (value === "menor") {
      return "menor";
    }
    if (value === "intermediaria") {
      return "intermediária";
    }
    return "indisponível";
  }

  return {
    renderFinancialHealth,
    invalidateFinancialHealth,
  };
}
