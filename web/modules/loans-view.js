import { renderChart, chartPalette, chartToken } from "./chart-adapter.js";
import { parseDecimalInput } from "./money-utils.js";
import { bindRovingTablist, syncRovingTabState } from "./tab-utils.js";

export function registerLoansView({ api, elements, escapeHtml }) {
  const {
    loanForm, loanMessage, loanList, loanCurrencyTotals, loanFormTitle, cancelLoanEdit,
    loanFormPanel, newLoanButton, decisionModal,
    revolvingLoanForm, revolvingLoanFormPanel, newRevolvingLoanButton, cancelRevolvingLoanForm,
    revolvingLoanList, revolvingLoanMessage,
    loanHistoryList, revolvingLoanHistoryList,
    simulationForm, simulationTarget, studyResult,
    strategyForm, strategyCurrency,
  } = elements;
  const money = (cents, currency) => new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format((Number(cents) || 0) / 100);
  let loansCache = [];
  let revolvingLoansCache = [];
  let conversionSourceId = null;
  const loanTabs = document.querySelectorAll("[data-loan-tab]");
  const loanTabPanels = Object.fromEntries(Array.from(document.querySelectorAll("[data-loan-panel]"), (panel) => [panel.dataset.loanPanel, panel]));

  function showLoanTab(name) {
    const selected = loanTabPanels[name] ? name : "active";
    syncRovingTabState(loanTabs, selected, (button) => button.dataset.loanTab);
    Object.entries(loanTabPanels).forEach(([key, panel]) => { panel.hidden = key !== selected; });
  }

  bindRovingTablist(loanTabs, { valueFor: (button) => button.dataset.loanTab, onSelect: showLoanTab });
  const revolvingSimulationFields = document.querySelector("#revolvingSimulationFields");
  const loanConversionPrefillNotice = document.querySelector("#loanConversionPrefillNotice");
  const cdiComparisonFields = document.querySelector("#loanCdiComparisonFields");
  const loanStudyActionFields = document.querySelector("#loanStudyActionFields");
  const loanAmortizeStudyFields = document.querySelector("#loanAmortizeStudyFields");
  const loanStudySubmit = document.querySelector("#loanStudySubmit");
  const loanStudyIntroHint = document.querySelector("#loanStudyIntroHint");

  function indexerAssumptionMetric(item, indexer) {
    if (!item) return null;
    const accumulated = (Number(item.accumulated_rate_micros) / 10000).toFixed(2).replace(".", ",");
    const monthly = (Number(item.monthly_rate_micros) / 10000).toFixed(4).replace(".", ",");
    const label = indexer === "POUPANCA" ? "poupança" : indexer;
    return [`Premissa futura · ${label}`, `${accumulated}% acumulada (${item.period_start} a ${item.period_end}) · equivalente a ${monthly}% a.m.`];
  }

  function cdiComparisonMetrics(comparison, currency) {
    if (!comparison) return [];
    if (!comparison.available) return [["Comparação com CDI", comparison.message]];
    const difference = Number(comparison.advantage_cents || 0);
    const comparisonText = difference > 0
      ? `O custo financeiro evitado supera o rendimento bruto estimado em ${money(difference, currency)}.`
      : difference < 0
        ? `O rendimento bruto estimado supera o custo financeiro evitado em ${money(Math.abs(difference), currency)}.`
        : "Custo financeiro evitado e rendimento bruto estimado são iguais neste cenário.";
    const daily = (Number(comparison.daily_rate_micros) / 10000).toFixed(4).replace(".", ",");
    const annual = (Number(comparison.annual_rate_micros) / 10000).toFixed(2).replace(".", ",");
    const monthly = (Number(comparison.monthly_rate_micros) / 10000).toFixed(4).replace(".", ",");
    return [
      ["Total aportado no cenário CDI", money(comparison.invested_cents, currency)],
      ["Saldo bruto estimado a 100% CDI", money(comparison.ending_balance_cents, currency)],
      ["Rendimento bruto estimado", money(comparison.gross_gain_cents, currency)],
      ["Custo financeiro estimado evitado", money(comparison.financing_cost_saved_cents ?? comparison.interest_saved_cents, currency)],
      ["Diferença indicativa", comparisonText],
      ["Premissa CDI", `Última taxa diária publicada: ${daily}% em ${comparison.rate_date}; equivalente a ${annual}% a.a. e ${monthly}% a.m. Mantida constante por ${comparison.horizon_months} meses como cenário hipotético, não previsão.`],
      ["Limitações", "Estimativa bruta; não considera IR, IOF, tarifas, liquidez ou o produto de investimento real. Não é recomendação financeira."],
    ];
  }

  async function loadLoans() {
    const [{ loans: allLoans = [] }, { loans: historicalLoans = [] }] = await Promise.all([
      api("/api/loans"), api("/api/loans?include_archived=true"),
    ]);
    await loadRevolvingLoans();
    const loans = allLoans.filter((loan) => Number(loan.remaining_installments) > 0 && !loan.archived_at);
    loansCache = loans;
    renderLoanHistory([...new Map([...historicalLoans, ...allLoans]
      .filter((loan) => loan.archived_at || Number(loan.remaining_installments) <= 0)
      .map((loan) => [Number(loan.id), loan])).values()]);
    const totals = new Map();
    for (const loan of loans) totals.set(loan.currency, (totals.get(loan.currency) || 0) + Number(loan.remaining_commitment_cents || 0));
    loanCurrencyTotals.innerHTML = [...totals.entries()].map(([currency, cents]) => `<p><strong>${escapeHtml(currency)} compromissos restantes:</strong> ${money(cents, currency)}</p>`).join("");

    loanList.innerHTML = loans.length ? loans.map((loan) => {
      const indexed = loan.indexer && loan.indexer !== "none";
      const indexerLabel = loan.indexer === "POUPANCA" ? "poupança" : loan.indexer;
      return `<article class="panel loan-card">
        <div class="loan-card-header">
          <strong>${escapeHtml(loan.name)}</strong>
          <div class="loan-card-actions" aria-label="Ações do contrato">
            <button class="ghost" type="button" data-edit-loan="${Number(loan.id)}">Editar / revisar</button>
            <button class="ghost" type="button" data-archive-loan="${Number(loan.id)}">Arquivar</button>
            <button class="danger" type="button" data-delete-loan="${Number(loan.id)}">Excluir</button>
          </div>
        </div>
        <p>${escapeHtml(loan.currency)} · ${Number(loan.remaining_installments)} parcelas restantes · ${loan.amortization_system === "sac" ? "SAC" : "Price"}${loan.indexer && loan.indexer !== "none" ? ` · corrigido por ${escapeHtml(loan.indexer === "POUPANCA" ? "poupança" : loan.indexer)}` : " prefixado"}</p>
        <div class="loan-debt-estimates" aria-label="Resumo do saldo do empréstimo">
          <div><small>Compromisso nominal restante</small><strong>${money(loan.remaining_commitment_cents, loan.currency)}</strong></div>
          <div><small>${indexed ? loan.principal_review_required ? "Principal informado · revisão pendente" : "Principal informado" : "Principal devedor estimado"}</small><strong>${indexed ? loan.principal_review_required ? "Atualize pelo demonstrativo" : hasEstimate(loan.principal_balance_cents) ? money(loan.principal_balance_cents, loan.currency) : "Informe no demonstrativo" : loan.monthly_rate_micros == null ? "Indisponível sem taxa" : hasEstimate(loan.estimated_principal_cents) ? money(loan.estimated_principal_cents, loan.currency) : "Estimativa não carregada; reinicie o app"}</strong></div>
          <div><small>Juros e encargos futuros estimados</small><strong>${indexed ? "Consulte o estudo de quitação" : loan.monthly_rate_micros == null ? "Indisponível sem taxa" : !hasEstimate(loan.estimated_principal_cents) ? "Estimativa não carregada; reinicie o app" : hasEstimate(loan.estimated_future_interest_cents) ? money(loan.estimated_future_interest_cents, loan.currency) : "Revise os dados do contrato"}</strong></div>
        </div>
        <p class="loan-debt-estimate-note">${indexed ? `Contrato corrigido por ${escapeHtml(indexerLabel)} · data-base ${escapeHtml(loan.principal_balance_date || "não informada")}. As projeções usam fatores publicados e, para períodos futuros, a taxa acumulada dos últimos 12 meses convertida em equivalente mensal.` : `Estimativas pelo modelo ${loan.amortization_system === "sac" ? "SAC prefixado" : "Price"}, com taxa e parcela cadastradas; podem divergir do saldo oficial do credor e incluir encargos embutidos na parcela.`}</p>
        <p>Parcela ${money(loan.installment_cents, loan.currency)} · próximo vencimento ${escapeHtml(loan.next_due_date)}${indexed ? ` · juros remuneratórios ${loan.remuneratory_rate_micros == null ? "não informados" : `${(Number(loan.remuneratory_rate_micros) / 10000).toFixed(4)}% a.m.`}` : loan.monthly_rate_micros === null ? " · taxa não informada" : ` · taxa ${(Number(loan.monthly_rate_micros) / 10000).toFixed(4)}% a.m.`}</p>
        <p><strong>Total pago:</strong> ${money(loan.total_paid_cents, loan.currency)} · ${loan.payments.length} pagamentos conciliados</p>
        ${loan.pending_payments?.length ? `<p role="status">${loan.pending_payments.length} pagamento(s) associado(s) aguardando conciliação; ainda não abatidos do empréstimo.</p>` : ""}
        <div class="loan-progress-heading"><h4>Jornada de quitação</h4><strong>${(Number(loan.paid_percentage_basis_points || 0) / 100).toFixed(2).replace(".", ",")}% pago</strong></div>
        <div class="loan-payment-evolution" id="loan-payment-chart-${Number(loan.id)}" aria-label="Progresso da quitação de ${escapeHtml(loan.name)}"></div>
        <details><summary>Ver pagamentos conciliados (${loan.payments.length})</summary><ul>${loan.payments.map((payment) => `<li>${escapeHtml(payment.date)} · ${escapeHtml(payment.description)} · ${money(payment.amount_cents, payment.currency)}</li>`).join("")}</ul></details>
        ${loan.pending_payments?.length ? `<details><summary>Pagamentos aguardando conciliação (${loan.pending_payments.length})</summary><ul>${loan.pending_payments.map((payment) => `<li>${escapeHtml(payment.date)} · ${escapeHtml(payment.description)} · ${money(payment.amount_cents, payment.currency)}</li>`).join("")}</ul></details>` : ""}
        ${loan.review_required ? '<p role="alert">Revise os dados deste empréstimo: um lançamento vinculado foi alterado.</p>' : ""}
        ${loan.principal_review_required ? '<p role="alert">Um pagamento conciliado ocorreu desde a data-base. O principal informado pode estar desatualizado; atualize-o com o demonstrativo do credor antes de executar simulações.</p>' : ""}
        ${loan.missed_payment_review ? '<p role="alert">Vencimento passado sem pagamento associado. Revise o compromisso e possíveis encargos manualmente.</p>' : ""}
      </article>`;
    }).join("") : '<p class="empty-state">Nenhum contrato ativo. Consulte a aba Histórico para ver contratos quitados ou arquivados.</p>';

    for (const loan of loans) renderPaymentEvolution(loan);

    renderLoanStudyOptions(loans, revolvingLoansCache);
  }

  async function loadRevolvingLoans() {
    const { revolving_loans: loans = [] } = await api("/api/revolving-loans");
    revolvingLoansCache = loans;
    revolvingLoanList.innerHTML = loans.filter((loan) => loan.status === "active").map((loan) => `
      <article class="panel loan-card revolving-loan-card">
        <div class="loan-card-header"><strong>${escapeHtml(loan.name)}</strong><div class="loan-card-actions">
          <button class="ghost" type="button" data-edit-revolving-loan="${Number(loan.id)}">Atualizar saldo / taxa</button>
          <button class="ghost" type="button" data-close-revolving-loan="${Number(loan.id)}">Encerrar acompanhamento</button>
        </div></div>
        <p>${loan.debt_type === "card_revolving" ? `Cartão · ${escapeHtml(loan.source_card_name || "Cartão arquivado")}` : "Cheque especial"} · ${escapeHtml(loan.currency)}</p>
        <div class="loan-debt-estimates"><div><small>Saldo informado</small><strong>${money(loan.balance_cents, loan.currency)}</strong></div>
        <div><small>Data-base</small><strong>${escapeHtml(loan.balance_date)}</strong></div>
        <div><small>Taxa</small><strong>${loan.rate_micros == null ? "Não informada" : `${(Number(loan.rate_micros) / 10000).toFixed(4).replace(".", ",")}% a.${loan.rate_period === "daily" ? "d." : "m."}`}</strong></div></div>
        <p class="loan-debt-estimate-note">Capitalização ${loan.capitalization === "daily" ? "diária" : "mensal"}. O saldo é informativo; consulte o credor para valores atualizados.${loan.rate_micros == null ? " Complete a taxa para habilitar projeções." : ""}</p>
        ${loan.review_required ? `<p role="alert">${loan.rate_micros == null ? "Informe a taxa contratual para habilitar a projeção de juros." : "Revise o saldo com o demonstrativo do credor; um pagamento, estorno ou alteração vinculada exige atualização manual."}</p>` : ""}
        ${loan.terms_history?.length > 1 ? `<details><summary>Histórico de saldo e condições (${loan.terms_history.length})</summary><ul>${loan.terms_history.map((item) => `<li>${escapeHtml(item.effective_date)} · ${money(item.balance_cents, loan.currency)}${item.rate_micros == null ? " · taxa não informada" : ` · ${(Number(item.rate_micros) / 10000).toFixed(4).replace(".", ",")}% a.${item.rate_period === "daily" ? "d." : "m."}`}</li>`).join("")}</ul></details>` : ""}
      </article>`).join("") || '<p class="empty-state">Nenhum crédito rotativo acompanhado.</p>';
    const ended = loans.filter((loan) => loan.status !== "active");
    revolvingLoanHistoryList.innerHTML = ended.map((loan) => {
      const status = loan.status === "paid" ? "Quitado" : loan.status === "swapped" ? "Trocado por outra dívida" : "Arquivado";
      const closingBalance = Number(loan.balance_cents || 0);
      const totalPaid = (loan.payments || []).reduce((sum, payment) => sum + Number(payment.amount_cents || 0), 0);
      return `<article class="panel loan-card revolving-loan-card loan-history-card">
        <div class="loan-card-header"><strong>${escapeHtml(loan.name)}</strong><span class="loan-history-status">${status}</span></div>
        <p>${loan.debt_type === "card_revolving" ? `Cartão · ${escapeHtml(loan.source_card_name || "Cartão arquivado")}` : "Cheque especial"} · ${escapeHtml(loan.currency)}</p>
        <div class="loan-debt-estimates"><div><small>${loan.status === "archived" && closingBalance > 0 ? "Saldo anotado ao arquivar" : "Saldo no encerramento"}</small><strong>${money(closingBalance, loan.currency)}</strong></div>
        <div><small>Pagamentos conciliados</small><strong>${money(totalPaid, loan.currency)}</strong></div>
        <div><small>Status</small><strong>${status}</strong></div></div>
        ${loan.status === "archived" && closingBalance > 0 ? '<p class="loan-debt-estimate-note">Este acompanhamento foi arquivado com saldo registrado; o valor pode estar desatualizado e não indica quitação.</p>' : ""}
        ${loan.payments?.length ? `<details><summary>Pagamentos preservados (${loan.payments.length})</summary><ul>${loan.payments.map((payment) => `<li>${escapeHtml(payment.date)} · ${escapeHtml(payment.description)} · ${money(payment.amount_cents, payment.currency || loan.currency)}</li>`).join("")}</ul></details>` : ""}
        ${loan.pending_payments?.length ? `<details><summary>Pagamentos pendentes preservados (${loan.pending_payments.length})</summary><ul>${loan.pending_payments.map((payment) => `<li>${escapeHtml(payment.date)} · ${escapeHtml(payment.description)} · ${money(payment.amount_cents, loan.currency)}</li>`).join("")}</ul></details>` : ""}
        ${loan.terms_history?.length > 1 ? `<details><summary>Histórico de saldo e condições (${loan.terms_history.length})</summary><ul>${loan.terms_history.map((item) => `<li>${escapeHtml(item.effective_date)} · ${money(item.balance_cents, loan.currency)}</li>`).join("")}</ul></details>` : ""}
      </article>`;
    }).join("") || '<p class="empty-state">Nenhum crédito rotativo encerrado.</p>';
  }

  function renderLoanHistory(history) {
    loanHistoryList.innerHTML = history.map((loan) => {
      const paid = Number(loan.remaining_installments) <= 0;
      const archived = Boolean(loan.archived_at);
      const status = archived ? paid ? "Quitado e arquivado" : "Arquivado · saldo em aberto" : "Quitado";
      return `<article class="panel loan-card loan-history-card">
        <div class="loan-card-header"><strong>${escapeHtml(loan.name)}</strong><span class="loan-history-status">${status}</span></div>
        <p>${escapeHtml(loan.currency)} · ${loan.amortization_system === "sac" ? "SAC" : "Price"}${loan.indexer && loan.indexer !== "none" ? ` · ${escapeHtml(loan.indexer)}` : " prefixado"}</p>
        <div class="loan-debt-estimates"><div><small>${archived && !paid ? "Compromisso nominal em aberto ao arquivar" : "Compromisso nominal restante"}</small><strong>${money(loan.remaining_commitment_cents, loan.currency)}</strong></div>
        <div><small>Total pago</small><strong>${money(loan.total_paid_cents, loan.currency)}</strong></div>
        <div><small>Pagamentos conciliados</small><strong>${loan.payments.length}</strong></div></div>
        ${archived && !paid ? '<p class="loan-debt-estimate-note">O contrato foi arquivado com parcelas restantes. O arquivamento não representa quitação nem atualiza o saldo com encargos posteriores.</p>' : ""}
        ${loan.archived_at ? `<p class="loan-debt-estimate-note">Arquivado em ${escapeHtml(String(loan.archived_at).slice(0, 10))}.</p>` : ""}
        <details><summary>Pagamentos conciliados preservados (${loan.payments.length})</summary>${loan.payments.length ? `<ul>${loan.payments.map((payment) => `<li>${escapeHtml(payment.date)} · ${escapeHtml(payment.description)} · ${money(payment.amount_cents, payment.currency)}</li>`).join("")}</ul>` : '<p>Nenhum pagamento conciliado associado.</p>'}</details>
        ${loan.pending_payments?.length ? `<details><summary>Pagamentos aguardando conciliação (${loan.pending_payments.length})</summary><ul>${loan.pending_payments.map((payment) => `<li>${escapeHtml(payment.date)} · ${escapeHtml(payment.description)} · ${money(payment.amount_cents, payment.currency)}</li>`).join("")}</ul></details>` : ""}
      </article>`;
    }).join("") || '<p class="empty-state">Nenhum empréstimo quitado ou arquivado.</p>';
  }

  newRevolvingLoanButton.addEventListener("click", () => {
    revolvingLoanForm.reset();
    revolvingLoanForm.elements.revolving_loan_id.value = "";
    revolvingLoanForm.elements.debt_type.value = "overdraft";
    revolvingLoanForm.elements.source_card_id.value = "";
    revolvingLoanForm.elements.balance_date.value = new Date().toISOString().slice(0, 10);
    revolvingLoanFormPanel.hidden = false;
    newRevolvingLoanButton.setAttribute("aria-expanded", "true");
    revolvingLoanFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    revolvingLoanForm.elements.name.focus({ preventScroll: true });
  });

  cancelRevolvingLoanForm.addEventListener("click", () => {
    revolvingLoanForm.reset();
    revolvingLoanFormPanel.hidden = true;
    newRevolvingLoanButton.setAttribute("aria-expanded", "false");
  });

  revolvingLoanForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(revolvingLoanForm).entries());
    const loanId = Number(data.revolving_loan_id);
    delete data.revolving_loan_id;
    try {
      await api(loanId ? `/api/revolving-loans/${loanId}` : "/api/revolving-loans", { method: loanId ? "PUT" : "POST", body: data });
      revolvingLoanFormPanel.hidden = true;
      revolvingLoanMessage.textContent = "Acompanhamento salvo. Nenhum lançamento foi criado.";
      await loadRevolvingLoans();
    } catch (error) { revolvingLoanMessage.textContent = error.message; }
  });

  revolvingLoanList.addEventListener("click", async (event) => {
    const editButton = event.target.closest("[data-edit-revolving-loan]");
    if (editButton) {
      const loan = revolvingLoansCache.find((item) => Number(item.id) === Number(editButton.dataset.editRevolvingLoan));
      if (!loan) return;
      const fields = revolvingLoanForm.elements;
      fields.revolving_loan_id.value = loan.id;
      fields.debt_type.value = loan.debt_type;
      fields.source_card_id.value = loan.source_card_id || "";
      fields.name.value = loan.name;
      fields.currency.value = loan.currency;
      fields.balance.value = (Number(loan.balance_cents) / 100).toFixed(2).replace(".", ",");
      fields.balance_date.value = loan.balance_date;
      fields.rate_percent.value = loan.rate_micros == null ? "" : (Number(loan.rate_micros) / 10000).toFixed(4).replace(".", ",");
      fields.rate_period.value = loan.rate_period || "monthly";
      fields.capitalization.value = loan.capitalization;
      revolvingLoanFormPanel.hidden = false;
      newRevolvingLoanButton.setAttribute("aria-expanded", "true");
      revolvingLoanFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    const closeButton = event.target.closest("[data-close-revolving-loan]");
    if (!closeButton) return;
    const loan = revolvingLoansCache.find((item) => Number(item.id) === Number(closeButton.dataset.closeRevolvingLoan));
    if (!loan) return;
    const resolution = await decisionModal.choose({
      title: "Encerrar acompanhamento da dívida?",
      message: "Esta ação só encerra o registro de monitoramento. Não cria nem altera lançamentos. Se ainda houver saldo, use arquivamento ou revise antes de encerrar.",
      actions: [
        { value: "paid", label: "Quitação definitiva", variant: "primary" },
        { value: "swapped", label: "Troca de dívida", variant: "ghost" },
        { value: "archived", label: "Arquivar", variant: "ghost" },
        { value: null, label: "Voltar", variant: "ghost" },
      ],
    });
    if (!resolution) return;
    try {
      await api(`/api/revolving-loans/${loan.id}/close`, { method: "POST", body: { resolution } });
      revolvingLoanMessage.textContent = "Acompanhamento encerrado sem criar lançamentos.";
      await loadRevolvingLoans();
    } catch (error) { revolvingLoanMessage.textContent = error.message; }
  });

  function renderPaymentEvolution(loan) {
    const element = document.querySelector(`#loan-payment-chart-${Number(loan.id)}`);
    if (!element) return;
    const paid = Number(loan.total_paid_cents || 0);
    renderChart(element, {
      chart: { type: "bar", height: 66, stacked: true, toolbar: { show: false }, animations: { enabled: false } },
      colors: [chartPalette()[0], chartToken("--outline-variant", "#c3c6d6")],
      plotOptions: { bar: { horizontal: true, barHeight: "46%", borderRadius: 5 } },
      series: [
        { name: "Pago", data: [Number(loan.paid_percentage_basis_points || 0) / 100] },
        { name: "Restante", data: [Number(loan.remaining_percentage_basis_points ?? 10_000) / 100] },
      ],
      xaxis: { categories: ["Quitação"], min: 0, max: 100, labels: { show: false }, axisBorder: { show: false }, axisTicks: { show: false } },
      yaxis: { show: false },
      grid: { show: false, padding: { top: -18, bottom: -18, left: -8, right: -8 } },
      legend: { show: false },
      tooltip: { custom: () => `<div class="loan-progress-tooltip"><strong>Total pago: ${money(paid, loan.currency)}</strong><span>Parcelas quitadas: ${Number(loan.paid_installments || 0)}</span><span>Compromisso total: ${money(loan.total_nominal_cents, loan.currency)}</span></div>` },
      dataLabels: { enabled: false },
    });
  }

  function openLoanForm() {
    loanFormPanel.hidden = false;
    newLoanButton.setAttribute("aria-expanded", "true");
    loanForm.elements.name.focus({ preventScroll: true });
    loanFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }
  newLoanButton.addEventListener("click", () => {
    conversionSourceId = null;
    loanForm.reset();
    loanForm.elements.loan_id.value = "";
    loanFormTitle.textContent = "Novo empréstimo";
    if (loanConversionPrefillNotice) loanConversionPrefillNotice.hidden = true;
    cancelLoanEdit.hidden = false;
    loanMessage.textContent = "";
    openLoanForm();
  });

  async function openPriceConversionDraft(revolvingLoanId) {
    const { revolving_loans: loans = [] } = await api("/api/revolving-loans");
    const source = loans.find((item) => Number(item.id) === Number(revolvingLoanId));
    if (!source || source.closure_reason !== "swapped") {
      loanMessage.textContent = "Não foi possível localizar a troca de dívida. Consulte o saldo e abra um novo cadastro manual.";
      return;
    }
    loanForm.reset();
    conversionSourceId = Number(source.id);
    const fields = loanForm.elements;
    fields.loan_id.value = "";
    fields.name.value = `Novo contrato Price — ${source.name}`;
    fields.loan_type.value = "other";
    fields.currency.value = source.currency;
    fields.amortization_system.value = "price";
    fields.indexer.value = "none";
    fields.principal_balance.value = (Number(source.balance_cents) / 100).toFixed(2).replace(".", ",");
    fields.principal_balance_date.value = source.balance_date;
    loanFormTitle.textContent = "Novo Price após troca de dívida";
    if (loanConversionPrefillNotice) loanConversionPrefillNotice.hidden = false;
    loanMessage.textContent = "Rascunho preparado. Confira o principal no demonstrativo e informe as condições do novo credor antes de salvar.";
    cancelLoanEdit.hidden = false;
    loanFormPanel.hidden = false;
    newLoanButton.setAttribute("aria-expanded", "true");
    loanFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
    fields.name.focus({ preventScroll: true });
  }

  async function loadLoanStudies() {
    const [{ loans = [] }, { revolving_loans: revolving = [] }] = await Promise.all([
      api("/api/loans"), api("/api/revolving-loans"),
    ]);
    revolvingLoansCache = revolving;
    renderLoanStudyOptions(loans, revolving);
  }

  function renderLoanStudyOptions(loans, revolving = []) {
    loansCache = loans;
    const activeLoans = loans.filter((loan) => Number(loan.remaining_installments) > 0);
    const activeRevolving = revolving.filter((loan) => loan.status === "active");
    const selectedLoan = simulationTarget.value;
    const options = [
      ...activeLoans.map((loan) => `<option value="loan:${Number(loan.id)}">${escapeHtml(loan.name)} · ${escapeHtml(loan.currency)}</option>`),
      ...activeRevolving.map((loan) => `<option value="revolving:${Number(loan.id)}">${escapeHtml(loan.name)} · Rotativo · ${escapeHtml(loan.currency)}</option>`),
    ];
    simulationTarget.innerHTML = options.join("") || '<option value="">Cadastre uma dívida ativa primeiro</option>';
    if ([...simulationTarget.options].some((option) => option.value === selectedLoan)) simulationTarget.value = selectedLoan;
    const selectedCurrency = strategyCurrency.value;
    const strategyCurrencies = [...new Set([
      ...activeLoans.map((loan) => loan.currency),
      ...activeRevolving.map((loan) => loan.currency),
    ])];
    const currencies = strategyCurrencies;
    strategyCurrency.innerHTML = currencies.length
      ? currencies.map((currency) => `<option value="${escapeHtml(currency)}">${escapeHtml(currency)}</option>`).join("")
      : '<option value="">Sem dívidas ativas</option>';
    if (currencies.includes(selectedCurrency)) strategyCurrency.value = selectedCurrency;
    updateRevolvingSimulationFields();
  }
  function updateRevolvingSimulationFields() {
    const isRevolving = simulationTarget.value.startsWith("revolving:");
    if (revolvingSimulationFields) revolvingSimulationFields.hidden = !isRevolving;
    const selectedId = Number(simulationTarget.value.split(":")[1]);
    const selectedLoan = loansCache.find((loan) => Number(loan.id) === selectedId);
    const studyType = simulationForm.querySelector('[name="loan_study_type"]:checked')?.value || "";
    const isIndexed = selectedLoan && selectedLoan.indexer && selectedLoan.indexer !== "none";
    const hasCompleteRate = selectedLoan && (isIndexed
      ? selectedLoan.principal_balance_cents != null && selectedLoan.principal_balance_date && selectedLoan.remuneratory_rate_micros != null && !selectedLoan.principal_review_required
      : selectedLoan.monthly_rate_micros != null);
    if (loanStudyActionFields) loanStudyActionFields.hidden = isRevolving || !selectedLoan;
    if (loanAmortizeStudyFields) loanAmortizeStudyFields.hidden = isRevolving || studyType !== "amortize";
    if (cdiComparisonFields) cdiComparisonFields.hidden = isRevolving || studyType !== "amortize" || !hasCompleteRate;
    if (loanStudySubmit) {
      loanStudySubmit.textContent = isRevolving ? "Simular estudo do rotativo"
        : studyType === "payoff" ? "Simular quitação"
          : studyType === "amortize" ? "Simular amortização" : "Escolha Quitar ou Amortizar";
    }
    if (loanStudyIntroHint) {
      loanStudyIntroHint.textContent = isRevolving
        ? "Informe o pagamento mensal planejado para estudar a evolução desta dívida rotativa."
        : "Selecione um contrato parcelado e depois escolha entre quitar o saldo estimado agora ou estudar pagamentos adicionais.";
    }
    if (!isRevolving) return;
    const id = Number(simulationTarget.value.split(":")[1]);
    const loan = revolvingLoansCache.find((item) => Number(item.id) === id);
    if (!loan) return;
    const fields = simulationForm.elements;
    if (!fields.revolving_first_payment_date.value) {
      const date = new Date(`${loan.balance_date}T12:00:00`);
      date.setDate(date.getDate() + 30);
      const now = new Date();
      const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
      const firstDue = date < today ? today : date;
      fields.revolving_first_payment_date.value = `${firstDue.getFullYear()}-${String(firstDue.getMonth() + 1).padStart(2, "0")}-${String(firstDue.getDate()).padStart(2, "0")}`;
    }
  }
  simulationTarget.addEventListener("change", () => {
    simulationForm.querySelectorAll('[name="loan_study_type"]').forEach((input) => { input.checked = false; });
    updateRevolvingSimulationFields();
  });
  simulationForm.querySelectorAll('[name="loan_study_type"]').forEach((input) => input.addEventListener("change", () => {
    studyResult.replaceChildren();
    updateRevolvingSimulationFields();
  }));

  loanForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(loanForm).entries());
    try {
      const loanId = Number(data.loan_id);
      delete data.loan_id;
      await api(loanId ? `/api/loans/${loanId}` : "/api/loans", { method: loanId ? "PUT" : "POST", body: data });
      if (!loanId && conversionSourceId) {
        try {
          await api("/api/cockpit/notifications/mark-seen", {
            method: "POST", body: { notification_ids: [`revolving_swap:${conversionSourceId}`] },
          });
        } catch { /* The saved contract is independent of this informational reminder. */ }
        conversionSourceId = null;
      }
      loanForm.reset();
      loanFormTitle.textContent = "Novo empréstimo";
      if (loanConversionPrefillNotice) loanConversionPrefillNotice.hidden = true;
      cancelLoanEdit.hidden = true;
      loanFormPanel.hidden = true;
      newLoanButton.setAttribute("aria-expanded", "false");
      loanMessage.textContent = "Empréstimo salvo.";
      await loadLoans();
    } catch (error) { loanMessage.textContent = error.message; }
  });

  loanList.addEventListener("click", async (event) => {
    const editButton = event.target.closest("[data-edit-loan]");
    if (editButton) {
      conversionSourceId = null;
      const loan = loansCache.find((item) => Number(item.id) === Number(editButton.dataset.editLoan));
      if (!loan) return;
      const fields = loanForm.elements;
      fields.loan_id.value = loan.id;
      fields.name.value = loan.name;
      fields.loan_type.value = loan.loan_type;
      fields.amortization_system.value = loan.amortization_system || "price";
      fields.indexer.value = loan.indexer || "none";
      fields.currency.value = loan.currency;
      fields.installment_amount.value = (Number(loan.installment_cents) / 100).toFixed(2).replace(".", ",");
      fields.remaining_installments.value = loan.remaining_installments;
      fields.remaining_commitment.value = (Number(loan.remaining_commitment_cents) / 100).toFixed(2).replace(".", ",");
      fields.monthly_rate_percent.value = loan.monthly_rate_micros === null ? "" : (Number(loan.monthly_rate_micros) / 10000).toFixed(4).replace(".", ",");
      fields.annual_cet_percent.value = loan.annual_cet_micros === null ? "" : (Number(loan.annual_cet_micros) / 10000).toFixed(4).replace(".", ",");
      fields.principal_balance.value = loan.principal_balance_cents == null ? "" : (Number(loan.principal_balance_cents) / 100).toFixed(2).replace(".", ",");
      fields.principal_balance_date.value = loan.principal_balance_date || "";
      fields.remuneratory_rate_percent.value = loan.remuneratory_rate_micros == null ? "" : (Number(loan.remuneratory_rate_micros) / 10000).toFixed(4).replace(".", ",");
      fields.next_due_date.value = loan.next_due_date;
      loanFormTitle.textContent = "Revisar empréstimo";
      if (loanConversionPrefillNotice) loanConversionPrefillNotice.hidden = true;
      cancelLoanEdit.hidden = false;
      loanFormPanel.hidden = false;
      newLoanButton.setAttribute("aria-expanded", "true");
      loanFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    const archiveButton = event.target.closest("[data-archive-loan]");
    if (archiveButton) {
      const confirmed = await decisionModal.choose({
        title: "Arquivar empréstimo?",
        message: "O contrato sairá da lista ativa e não aceitará novos pagamentos associados. O histórico e os lançamentos serão preservados.",
        actions: [{ value: "archive", label: "Arquivar empréstimo", variant: "danger" }, { value: null, label: "Cancelar", variant: "ghost" }],
      });
      if (confirmed !== "archive") return;
      try {
        await api(`/api/loans/${Number(archiveButton.dataset.archiveLoan)}/archive`, { method: "POST" });
        await loadLoans();
      } catch (error) { loanMessage.textContent = error.message; }
      return;
    }

    const deleteButton = event.target.closest("[data-delete-loan]");
    if (!deleteButton) return;
    const loan = loansCache.find((item) => Number(item.id) === Number(deleteButton.dataset.deleteLoan));
    if (!loan) return;
    const confirmation = await decisionModal.form({
      title: "Excluir contrato definitivamente?",
      message: `O contrato “${loan.name}” e ${loan.payments.length + loan.pending_payments.length} associação(ões) serão removidos. Os lançamentos permanecerão intactos na conta, com valores, datas, conciliação e categoria atuais. Esta ação não pode ser desfeita.`,
      fields: [{ name: "current_password", label: "Confirme com sua senha atual", type: "password", required: true }],
      primaryLabel: "Excluir contrato",
      primaryVariant: "danger",
    });
    if (!confirmation) return;
    try {
      await api(`/api/loans/${Number(loan.id)}`, { method: "DELETE", body: { current_password: confirmation.current_password } });
      confirmation.current_password = "";
      loanMessage.textContent = "Contrato excluído; os lançamentos da conta foram preservados.";
      await loadLoans();
    } catch (error) { loanMessage.textContent = error.message; }
  });

  cancelLoanEdit.addEventListener("click", () => {
    conversionSourceId = null;
    loanForm.reset();
    loanForm.elements.loan_id.value = "";
    loanFormTitle.textContent = "Novo empréstimo";
    if (loanConversionPrefillNotice) loanConversionPrefillNotice.hidden = true;
    cancelLoanEdit.hidden = true;
    loanFormPanel.hidden = true;
    newLoanButton.setAttribute("aria-expanded", "false");
    newLoanButton.focus();
  });

  simulationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(simulationForm);
    if (simulationTarget.value.startsWith("revolving:")) {
      const loanId = Number(simulationTarget.value.split(":")[1]);
      const loan = revolvingLoansCache.find((item) => Number(item.id) === loanId);
      if (!loan) return;
      const proposalValues = [formData.get("price_principal"), formData.get("price_rate_percent"), formData.get("price_installments")];
      const hasProposal = proposalValues.some((value) => String(value || "").trim());
      if (hasProposal && proposalValues.some((value) => !String(value || "").trim())) {
        studyResult.textContent = "Para comparar com Price, preencha principal, taxa mensal e prazo.";
        return;
      }
      try {
        const { result } = await api("/api/revolving-loans/simulate", { method: "POST", body: {
          revolving_loan_id: loan.id,
          monthly_payment: formData.get("revolving_monthly_payment"),
          first_payment_date: formData.get("revolving_first_payment_date"),
          extraordinary_payment: formData.get("revolving_extraordinary_payment"),
          extraordinary_payment_date: formData.get("revolving_extraordinary_date"),
          price_principal: formData.get("price_principal"),
          price_rate_percent: formData.get("price_rate_percent"),
          price_installments: formData.get("price_installments"),
        } });
        const revolving = result.revolving;
        const metrics = [
          ["Juros sem pagamentos", money(result.no_payment.interest_cents, result.currency)],
          [`Saldo sem pagamentos em ${result.horizon_months} meses`, money(result.no_payment.ending_balance_cents, result.currency)],
          ["Juros com o plano informado", money(revolving.interest_cents, result.currency)],
          ["Total pago no cenário", money(revolving.total_paid_cents, result.currency)],
          ["Saldo ao final do horizonte", money(revolving.ending_balance_cents, result.currency)],
          ...(revolving.paid_off ? [["Quitação estimada", `${revolving.months} meses · ${revolving.payoff_date}`]] : []),
          ...(result.price_offer ? [
            ["Parcela Price estimada", money(result.price_offer.installment_cents, result.currency)],
            ["Custo total Price", money(result.price_offer.total_paid_cents, result.currency)],
            ["Comparação", result.price_offer.cheaper == null ? "Indeterminada: o plano rotativo não quitou no horizonte." : result.price_offer.cheaper ? "A proposta Price tem menor custo estimado." : "A proposta Price não tem custo menor neste cenário."],
          ] : []),
        ];
        const summary = revolving.paid_off
          ? `Quitação em ${revolving.months} meses · ${revolving.payoff_date}`
          : `Saldo não quitado no horizonte de ${result.horizon_months} meses`;
        renderStudyResult(studyResult, `Estudo do rotativo · ${escapeHtml(loan.name)} · ${escapeHtml(result.currency)}`, summary, metrics);
      } catch (error) { studyResult.textContent = error.message; }
      return;
    }
    const loanId = Number(simulationTarget.value.split(":")[1]);
    const studyType = formData.get("loan_study_type");
    if (!studyType) {
      studyResult.textContent = "Escolha se deseja estudar a quitação ou a amortização.";
      return;
    }
    const loans = (await api("/api/loans")).loans;
    const loan = loans.find((item) => Number(item.id) === loanId);
    if (!loan) return;
    if (studyType === "amortize" && loan.monthly_rate_micros === null && (!loan.indexer || loan.indexer === "none")) { studyResult.textContent = "Informe uma taxa para simular juros e economia de prazo."; return; }
    try {
      const { result } = await api("/api/loans/simulate", { method: "POST", body: {
        installment_cents: loan.installment_cents, remaining_installments: loan.remaining_installments,
        loan_id: loan.id, indexer: loan.indexer || "none",
        study_type: studyType,
        monthly_rate_micros: loan.monthly_rate_micros, amortization_system: loan.amortization_system || "price",
        extra_monthly_payment: formData.get("extra_monthly_payment"),
        extraordinary_payment: formData.get("extraordinary_payment"), amortization_mode: formData.get("amortization_mode"),
        compare_cdi: studyType === "payoff" || Boolean(formData.get("compare_cdi")),
      } });
      if (studyType === "payoff") {
        renderStudyResult(studyResult, `Estudo: quitar ou investir · ${escapeHtml(loan.name)}`, `Comparação para o prazo restante de ${result.baseline_months} meses`, [
          ["Valor estimado para quitar hoje", money(result.payoff_amount_cents, loan.currency)],
          ...cdiComparisonMetrics(result.cdi_comparison, loan.currency),
        ]);
        return;
      }
      const extraMonthlyCents = Math.round(parseDecimalInput(formData.get("extra_monthly_payment")) * 100);
      const monthlyOutflowCents = Number(result.new_installment_cents || 0) + extraMonthlyCents;
      const extraordinaryCents = Number(result.extraordinary_cents || 0);
      const reduceTerm = result.amortization_mode !== "reduce_payment";
      const paymentLabel = loan.amortization_system === "sac" ? "Próxima parcela estimada" : "Parcela após a amortização";
      const initialPaymentText = extraordinaryCents > 0
        ? `Após amortizar ${money(extraordinaryCents, loan.currency)} agora, `
        : extraMonthlyCents > 0 ? "Com o adicional mensal informado, " : "";
      const planMessage = reduceTerm
        ? `${initialPaymentText}${loan.amortization_system === "sac" ? `as parcelas começam em ${money(result.new_installment_cents, loan.currency)} e diminuem` : `a parcela permanece em ${money(result.new_installment_cents, loan.currency)}`} por até ${result.months} meses. O prazo cai de ${result.baseline_months} para ${result.months} meses${extraMonthlyCents > 0 && extraordinaryCents > 0 ? `, com mais ${money(extraMonthlyCents, loan.currency)} por mês` : ""}. A última parcela pode ser menor.`
        : `${initialPaymentText}a parcela estimada fica em ${money(result.new_installment_cents, loan.currency)} por ${result.months} meses; o prazo original de ${result.baseline_months} meses é mantido${extraMonthlyCents > 0 && extraordinaryCents > 0 ? `, com mais ${money(extraMonthlyCents, loan.currency)} por mês` : ""}.`;
      renderStudyResult(studyResult, "Plano de amortização", "Como ficam os pagamentos depois da amortização", [
        [paymentLabel, money(result.new_installment_cents, loan.currency)],
        ["Adicional mensal", money(extraMonthlyCents, loan.currency)],
        ["Desembolso mensal estimado", money(monthlyOutflowCents, loan.currency)],
        ["Amortização extraordinária agora", money(extraordinaryCents, loan.currency)],
        ["Prazo sem amortização", `${result.baseline_months} meses`],
        ["Prazo com esta amortização", `${result.months} meses`],
        ["Juros totais estimados", money(result.interest_cents, loan.currency)],
        ...(result.indexation_cents == null ? [] : [["Correção acumulada estimada", money(result.indexation_cents, loan.currency)]]),
        ...(result.future_index_accumulated_rate_micros == null ? [] : [indexerAssumptionMetric({ accumulated_rate_micros: result.future_index_accumulated_rate_micros, monthly_rate_micros: result.future_index_monthly_rate_micros, period_start: result.future_index_period_start, period_end: result.future_index_period_end }, loan.indexer)]),
        ["Economia estimada em juros", money(result.interest_saved_cents, loan.currency)],
        ["Principal estimado", money(result.estimated_principal_cents, loan.currency)],
        ...cdiComparisonMetrics(result.cdi_comparison, loan.currency),
      ], planMessage);
    } catch (error) { studyResult.textContent = error.message; }
  });

  strategyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
      const data = Object.fromEntries(new FormData(strategyForm).entries());
    try {
      const { result } = await api("/api/loans/simulate-strategy", { method: "POST", body: data });
      const metrics = result.interest_cents === null ? [["Juros totais", "Complete as taxas das dívidas para estimar juros."]] : [
        ["Juros totais estimados", money(result.interest_cents, result.currency)],
        ["Economia estimada em juros", money(result.interest_saved_cents, result.currency)],
        ...(result.indexation_cents == null ? [] : [["Correção acumulada estimada", money(result.indexation_cents, result.currency)]]),
        ...Object.entries(result.future_index_assumptions || {}).map(([indexer, assumption]) => indexerAssumptionMetric(assumption, indexer)),
      ];
      renderStudyResult(
        studyResult,
        `Plano por estratégia · ${result.strategy === "avalanche" ? "Avalanche" : "Bola de neve"} · ${result.currency}`,
        result.baseline_months == null
          ? `${result.months} meses estimados com o orçamento adicional informado`
          : `${result.months} meses estimados · ${result.months_saved} meses economizados`,
        metrics,
      );
    } catch (error) { studyResult.textContent = error.message; }
  });

  return { loadLoans, loadLoanStudies, openPriceConversionDraft };
}

function hasEstimate(value) {
  return value !== null && value !== undefined && Number.isFinite(Number(value));
}

// spec: simulacoes/efeito-borboleta v2.16 — critérios 32–33
function renderStudyResult(host, headline, summary, metrics, primaryMessage = "") {
  const keyMetrics = metrics.filter(([label]) => label !== "Premissa CDI" && label !== "Limitações");
  const notes = metrics.filter(([label]) => label === "Premissa CDI" || label === "Limitações");
  host.innerHTML = `
    <div class="loan-study-result-lead"><strong>${headline}</strong><span>${summary}</span></div>
    ${primaryMessage ? `<p class="loan-study-result-primary">${primaryMessage}</p>` : ""}
    ${keyMetrics.length ? `<div class="loan-study-result-metrics">${keyMetrics.map(([label, value]) => `
      <div class="loan-study-result-metric"><small>${label}</small><strong>${value}</strong></div>
    `).join("")}</div>` : '<p class="muted-copy">Juros não calculados porque há empréstimos sem taxa informada.</p>'}
    ${notes.map(([label, value]) => `<p class="loan-study-result-footnote"><strong>${label}:</strong> ${value}</p>`).join("")}
    <p class="muted-copy loan-study-result-note">Estimativa teórica com base nos dados cadastrados. Simulações não alteram contratos, lançamentos ou saldos.</p>
  `;
}
