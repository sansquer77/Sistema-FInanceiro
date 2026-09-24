import { renderChart, chartPalette, chartToken } from "./chart-adapter.js";

export function registerLoansView({ api, elements, escapeHtml }) {
  const {
    loanForm, loanMessage, loanList, loanCurrencyTotals, loanFormTitle, cancelLoanEdit,
    loanFormPanel, newLoanButton, decisionModal,
    simulationForm, simulationTarget, simulationResult,
    strategyForm, strategyCurrency, strategyResult,
  } = elements;
  const money = (cents, currency) => new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format((Number(cents) || 0) / 100);
  let loansCache = [];

  async function loadLoans() {
    const { loans = [] } = await api("/api/loans");
    loansCache = loans;
    const totals = new Map();
    for (const loan of loans) totals.set(loan.currency, (totals.get(loan.currency) || 0) + Number(loan.remaining_commitment_cents || 0));
    loanCurrencyTotals.innerHTML = [...totals.entries()].map(([currency, cents]) => `<p><strong>${escapeHtml(currency)} compromissos restantes:</strong> ${money(cents, currency)}</p>`).join("");

    loanList.innerHTML = loans.length ? loans.map((loan) => {
      return `<article class="panel">
        <strong>${escapeHtml(loan.name)}</strong>
        <p>${escapeHtml(loan.currency)} · ${Number(loan.remaining_installments)} parcelas · ${money(loan.remaining_commitment_cents, loan.currency)} restantes</p>
        <p>Parcela ${money(loan.installment_cents, loan.currency)} · próximo vencimento ${escapeHtml(loan.next_due_date)}${loan.monthly_rate_micros === null ? " · taxa não informada" : ` · taxa ${(Number(loan.monthly_rate_micros) / 10000).toFixed(4)}% a.m.`}</p>
        <p><strong>Total pago:</strong> ${money(loan.total_paid_cents, loan.currency)} · ${loan.payments.length} pagamentos associados</p>
        <div class="loan-progress-heading"><h4>Jornada de quitação</h4><strong>${(Number(loan.paid_percentage_basis_points || 0) / 100).toFixed(2).replace(".", ",")}% pago</strong></div>
        <div class="loan-payment-evolution" id="loan-payment-chart-${Number(loan.id)}" aria-label="Progresso da quitação de ${escapeHtml(loan.name)}"></div>
        <details><summary>Ver pagamentos associados (${loan.payments.length})</summary><ul>${loan.payments.map((payment) => `<li>${escapeHtml(payment.date)} · ${escapeHtml(payment.description)} · ${money(payment.amount_cents, payment.currency)}</li>`).join("")}</ul></details>
        ${loan.review_required ? '<p role="alert">Revise os dados deste empréstimo: um lançamento vinculado foi alterado.</p>' : ""}
        ${loan.missed_payment_review ? '<p role="alert">Vencimento passado sem pagamento associado. Revise o compromisso e possíveis encargos manualmente.</p>' : ""}
        <div class="actions">
          <button class="ghost" type="button" data-edit-loan="${Number(loan.id)}">Editar / revisar</button>
          <button class="danger" type="button" data-archive-loan="${Number(loan.id)}">Arquivar empréstimo</button>
        </div>
      </article>`;
    }).join("") : '<p class="empty-state">Nenhum empréstimo cadastrado.</p>';

    for (const loan of loans) renderPaymentEvolution(loan);

    renderLoanStudyOptions(loans);
  }

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
    loanForm.reset();
    loanForm.elements.loan_id.value = "";
    loanFormTitle.textContent = "Novo empréstimo";
    cancelLoanEdit.hidden = false;
    loanMessage.textContent = "";
    openLoanForm();
  });

  async function loadLoanStudies() {
    const { loans = [] } = await api("/api/loans");
    renderLoanStudyOptions(loans);
  }

  function renderLoanStudyOptions(loans) {
    const activeLoans = loans.filter((loan) => Number(loan.remaining_installments) > 0);
    const selectedLoan = simulationTarget.value;
    simulationTarget.innerHTML = activeLoans.length
      ? activeLoans.map((loan) => `<option value="${Number(loan.id)}">${escapeHtml(loan.name)} (${escapeHtml(loan.currency)})</option>`).join("")
      : '<option value="">Cadastre um empréstimo ativo primeiro</option>';
    if (activeLoans.some((loan) => String(loan.id) === selectedLoan)) simulationTarget.value = selectedLoan;
    const selectedCurrency = strategyCurrency.value;
    const currencies = [...new Set(activeLoans.map((loan) => loan.currency))];
    strategyCurrency.innerHTML = currencies.length
      ? currencies.map((currency) => `<option value="${escapeHtml(currency)}">${escapeHtml(currency)}</option>`).join("")
      : '<option value="">Sem empréstimos ativos</option>';
    if (currencies.includes(selectedCurrency)) strategyCurrency.value = selectedCurrency;
  }

  loanForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(loanForm).entries());
    try {
      const loanId = Number(data.loan_id);
      delete data.loan_id;
      await api(loanId ? `/api/loans/${loanId}` : "/api/loans", { method: loanId ? "PUT" : "POST", body: data });
      loanForm.reset();
      loanFormTitle.textContent = "Novo empréstimo";
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
      const loan = loansCache.find((item) => Number(item.id) === Number(editButton.dataset.editLoan));
      if (!loan) return;
      const fields = loanForm.elements;
      fields.loan_id.value = loan.id;
      fields.name.value = loan.name;
      fields.loan_type.value = loan.loan_type;
      fields.currency.value = loan.currency;
      fields.installment_amount.value = (Number(loan.installment_cents) / 100).toFixed(2).replace(".", ",");
      fields.remaining_installments.value = loan.remaining_installments;
      fields.remaining_commitment.value = (Number(loan.remaining_commitment_cents) / 100).toFixed(2).replace(".", ",");
      fields.monthly_rate_percent.value = loan.monthly_rate_micros === null ? "" : (Number(loan.monthly_rate_micros) / 10000).toFixed(4).replace(".", ",");
      fields.annual_cet_percent.value = loan.annual_cet_micros === null ? "" : (Number(loan.annual_cet_micros) / 10000).toFixed(4).replace(".", ",");
      fields.next_due_date.value = loan.next_due_date;
      loanFormTitle.textContent = "Revisar empréstimo";
      cancelLoanEdit.hidden = false;
      loanFormPanel.hidden = false;
      newLoanButton.setAttribute("aria-expanded", "true");
      loanFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
      return;
    }
    const archiveButton = event.target.closest("[data-archive-loan]");
    if (!archiveButton) return;
    const confirmed = await decisionModal.choose({
      title: "Arquivar empréstimo?",
      message: "O empréstimo sairá da lista de ativos e não aceitará novos pagamentos associados. Os lançamentos e pagamentos já registrados serão preservados.",
      actions: [{ value: "archive", label: "Arquivar empréstimo", variant: "danger" }, { value: null, label: "Cancelar", variant: "ghost" }],
    });
    if (confirmed !== "archive") return;
    try { await api(`/api/loans/${Number(archiveButton.dataset.archiveLoan)}`, { method: "DELETE" }); await loadLoans(); }
    catch (error) { loanMessage.textContent = error.message; }
  });

  cancelLoanEdit.addEventListener("click", () => {
    loanForm.reset();
    loanForm.elements.loan_id.value = "";
    loanFormTitle.textContent = "Novo empréstimo";
    cancelLoanEdit.hidden = true;
    loanFormPanel.hidden = true;
    newLoanButton.setAttribute("aria-expanded", "false");
    newLoanButton.focus();
  });

  simulationForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const loans = (await api("/api/loans")).loans;
    const loan = loans.find((item) => Number(item.id) === Number(simulationTarget.value));
    if (!loan) return;
    if (loan.monthly_rate_micros === null) { simulationResult.textContent = "Informe uma taxa para simular juros e economia de prazo."; return; }
    try {
      const formData = new FormData(simulationForm);
      const { result } = await api("/api/loans/simulate", { method: "POST", body: {
        installment_cents: loan.installment_cents, remaining_installments: loan.remaining_installments,
        monthly_rate_micros: loan.monthly_rate_micros, extra_monthly_payment: formData.get("extra_monthly_payment"),
        extraordinary_payment: formData.get("extraordinary_payment"), amortization_mode: formData.get("amortization_mode"),
      } });
      simulationResult.textContent = `${result.months} meses · ${result.months_saved} meses economizados · nova parcela ${money(result.new_installment_cents, loan.currency)} · juros estimados ${money(result.interest_cents, loan.currency)} · juros economizados ${money(result.interest_saved_cents, loan.currency)} · principal estimado ${money(result.estimated_principal_cents, loan.currency)}`;
    } catch (error) { simulationResult.textContent = error.message; }
  });

  strategyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(strategyForm).entries());
    try {
      const { result } = await api("/api/loans/simulate-strategy", { method: "POST", body: data });
      const interestSummary = result.interest_cents === null ? "juros não calculados (taxa ausente)" : `juros ${money(result.interest_cents, result.currency)} · juros economizados ${money(result.interest_saved_cents, result.currency)}`;
      strategyResult.textContent = `${result.strategy === "avalanche" ? "Avalanche" : "Bola de neve"} · ${result.currency} · ${result.months} meses · ${result.months_saved} meses economizados · ${interestSummary}.`;
    } catch (error) { strategyResult.textContent = error.message; }
  });

  return { loadLoans, loadLoanStudies };
}
