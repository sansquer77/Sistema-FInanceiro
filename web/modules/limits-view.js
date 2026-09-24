export function registerLimitsView({
  state,
  elements,
  navButtons,
  api,
  currentMonthValue,
  shiftMonth,
  formatMonthLabel,
  formatMonthShortLabel,
  formatMoney,
  formatPercent,
  formData,
  setFormBusy,
  setMessage,
  emptyState,
  escapeHtml,
  onLimitsChanged = () => {},
  goToLimits = () => {},
}) {
  const {
    limitForm,
    limitFormTitle,
    limitCategory,
    limitSubcategory,
    limitMonthInput,
    limitMonthLabel,
    limitConsumedSummary,
    limitDefinedSummary,
    limitAvailableSummary,
    limitMessage,
    spendingLimitList,
    previousLimitMonthButton,
    nextLimitMonthButton,
    cancelLimitEditButton,
    cockpitLimitAlert,
    limitsTabButtons,
    limitsTabPanels,
    goalForm,
    goalFormPanel,
    newGoalButton,
    goalFormTitle,
    goalTargetDateField,
    goalYieldMode,
    goalYieldPercentageField,
    cancelGoalEditButton,
    goalMessage,
    financialGoalList,
    emergencyReserveTotal,
    emergencyReserveComponents,
    activeGoalsCount,
    goalsReservedTotal,
    goalsMonthlyTotal,
    uncoveredGoalsCount,
    goalActionPanel,
    goalActionEyebrow,
    goalActionTitle,
    closeGoalActionButton,
    goalMovementForm,
    goalFundingForm,
    goalFundingSource,
    goalActionMessage,
  } = elements;

  limitForm.addEventListener("submit", handleLimitSubmit);
  limitCategory.addEventListener("change", renderLimitSubcategories);
  previousLimitMonthButton.addEventListener("click", () => shiftLimitMonth(-1));
  nextLimitMonthButton.addEventListener("click", () => shiftLimitMonth(1));
  cancelLimitEditButton.addEventListener("click", resetLimitForm);
  limitsTabButtons.forEach((button, index) => {
    button.addEventListener("click", () => selectLimitsTab(button.dataset.limitsTab));
    button.addEventListener("keydown", (event) => {
      if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) return;
      event.preventDefault();
      let next = event.key === "Home" ? 0 : event.key === "End" ? limitsTabButtons.length - 1 : index + (event.key === "ArrowRight" ? 1 : -1);
      next = (next + limitsTabButtons.length) % limitsTabButtons.length;
      limitsTabButtons[next].focus();
      selectLimitsTab(limitsTabButtons[next].dataset.limitsTab);
    });
  });
  goalForm.addEventListener("submit", handleGoalSubmit);
  newGoalButton.addEventListener("click", openNewGoalForm);
  goalForm.elements.objective_type.addEventListener("change", updateGoalDateRequirement);
  goalYieldMode.addEventListener("change", updateGoalYieldFields);
  cancelGoalEditButton.addEventListener("click", () => resetGoalForm({ restoreFocus: true }));
  goalMovementForm.addEventListener("submit", handleGoalMovementSubmit);
  goalFundingForm.addEventListener("submit", handleGoalFundingSubmit);
  closeGoalActionButton.addEventListener("click", closeGoalAction);

  let goalDataLoaded = false;
  let goalDataRequest = null;
  const goalCharts = new Map();
  resetGoalForm();

  async function loadSpendingLimits() {
    const response = await api(`/api/spending-limits?month=${encodeURIComponent(state.limitMonth)}`);
    state.spendingLimits = response.limits;
  }

  async function loadCurrentSpendingLimits(month = currentMonthValue()) {
    const response = await api(`/api/spending-limits?month=${encodeURIComponent(month)}`);
    state.currentSpendingLimits = response.limits;
  }

  async function loadGoalData({ force = false } = {}) {
    if (goalDataLoaded && !force) return;
    if (goalDataRequest) return goalDataRequest;
    goalDataRequest = (async () => {
      const [goalsResult, reserveResult] = await Promise.allSettled([
        api("/api/financial-goals"),
        api("/api/financial-goals/emergency-reserve"),
      ]);
      if (reserveResult.status === "fulfilled") {
        state.emergencyReserve = reserveResult.value.emergency_reserve || { total_brl: "0.00", components: [] };
      } else {
        state.emergencyReserve ||= { total_brl: "0.00", components: [] };
      }
      renderEmergencyReserve();
      if (goalsResult.status === "fulfilled") {
        state.financialGoals = goalsResult.value.goals || [];
        renderGoalsOverview();
        renderGoalList();
        updateGoalDateRequirement();
      }
      const failedResult = [reserveResult, goalsResult].find((result) => result.status === "rejected");
      goalDataLoaded = !failedResult;
      if (failedResult) throw failedResult.reason;
    })();
    try {
      await goalDataRequest;
    } finally {
      goalDataRequest = null;
    }
  }

  async function loadGoalDataIfNeeded() {
    if (state.limitsTab === "goals") await loadGoalData({ force: true });
  }

  function selectLimitsTab(tab) {
    state.limitsTab = tab === "goals" ? "goals" : "spending";
    limitsTabButtons.forEach((button) => {
      const active = button.dataset.limitsTab === state.limitsTab;
      button.classList.toggle("active", active);
      button.setAttribute("aria-selected", String(active));
      button.tabIndex = active ? 0 : -1;
    });
    limitsTabPanels.forEach((panel) => { panel.hidden = panel.dataset.limitsPanel !== state.limitsTab; });
    if (state.limitsTab === "goals") {
      renderEmergencyReserve();
      loadGoalData().catch((error) => setMessage(goalMessage, error.message, "error"));
    }
  }

  async function handleGoalSubmit(event) {
    event.preventDefault();
    const data = formData(goalForm);
    const isEditing = Boolean(data.id);
    if (data.objective_type === "continuous_reserve") data.target_date = "";
    setFormBusy(goalForm, true);
    setMessage(goalMessage, "");
    try {
      await api(isEditing ? `/api/financial-goals/${data.id}` : "/api/financial-goals", {
        method: isEditing ? "PUT" : "POST",
        body: data,
      });
      resetGoalForm({ restoreFocus: true });
      await loadGoalData({ force: true });
      setMessage(goalMessage, isEditing ? "Objetivo atualizado." : "Objetivo criado.", "success");
    } catch (error) {
      setMessage(goalMessage, error.message, "error");
    } finally {
      setFormBusy(goalForm, false);
    }
  }

  async function handleGoalMovementSubmit(event) {
    event.preventDefault();
    const data = formData(goalMovementForm);
    const goalId = data.goal_id;
    delete data.goal_id;
    setFormBusy(goalMovementForm, true);
    try {
      await api(`/api/financial-goals/${goalId}/movements`, { method: "POST", body: data });
      closeGoalAction();
      await loadGoalData({ force: true });
      setMessage(goalMessage, "Saldo reservado atualizado.", "success");
    } catch (error) {
      setMessage(goalActionMessage, error.message, "error");
    } finally {
      setFormBusy(goalMovementForm, false);
    }
  }

  async function handleGoalFundingSubmit(event) {
    event.preventDefault();
    const data = formData(goalFundingForm);
    const goalId = data.goal_id;
    const [sourceType, sourceId] = String(data.source_key || "").split(":");
    setFormBusy(goalFundingForm, true);
    try {
      await api(`/api/financial-goals/${goalId}/funding-sources`, {
        method: "POST", body: { source_type: sourceType, source_id: sourceId },
      });
      closeGoalAction();
      await loadGoalData({ force: true });
      setMessage(goalMessage, "Origem vinculada com exclusividade.", "success");
    } catch (error) {
      setMessage(goalActionMessage, error.message, "error");
    } finally {
      setFormBusy(goalFundingForm, false);
    }
  }

  function renderGoals() {
    renderEmergencyReserve();
    renderGoalsOverview();
    renderGoalList();
    updateGoalDateRequirement();
  }

  function renderEmergencyReserve() {
    const reserve = state.emergencyReserve || { total_brl: "0.00", components: [] };
    emergencyReserveTotal.textContent = formatMoney(Number(reserve.total_brl || 0), "BRL");
    const portfolios = reserve.portfolios || (reserve.components?.length ? [{
      account_name: "Investimentos",
      total_brl: reserve.total_brl,
      components: reserve.components,
    }] : []);
    emergencyReserveComponents.innerHTML = portfolios.map((portfolio, index) => {
      const components = portfolio.components || [];
      const hiddenCount = Math.max(0, components.length - 3);
      const rows = components.map((component, componentIndex) => `
        <article class="reserve-component${componentIndex >= 3 ? " reserve-component-extra" : ""}"${componentIndex >= 3 ? ` data-reserve-extra="${index}" hidden` : ""}>
          <span class="reserve-component-icon" aria-hidden="true">◆</span>
          <div><strong>${escapeHtml(component.asset_name)}</strong><small>${escapeHtml(component.asset_type_label || "Investimento")}</small></div>
          <b>${formatMoney(Number(component.current_value_brl || 0), "BRL")}</b>
        </article>
      `).join("");
      return `
        <section class="reserve-portfolio">
          <header class="reserve-portfolio-heading">
            <div><strong>${escapeHtml(portfolio.account_name || "Carteira não identificada")}</strong><small>${components.length} ${components.length === 1 ? "investimento" : "investimentos"}</small></div>
            <b>${formatMoney(Number(portfolio.total_brl || 0), "BRL")}</b>
          </header>
          <div class="reserve-portfolio-components">${rows}</div>
          ${hiddenCount ? `<button class="reserve-expand-button" type="button" data-reserve-expand="${index}" aria-expanded="false">+ ${hiddenCount} ${hiddenCount === 1 ? "título" : "títulos"}</button>` : ""}
        </section>`;
    }).join("") || '<p class="empty-inline">Nenhum investimento foi marcado como Reserva de Emergência no Portfólio.</p>';
    emergencyReserveComponents.querySelectorAll("[data-reserve-expand]").forEach((button) => {
      button.addEventListener("click", () => {
        const expanded = button.getAttribute("aria-expanded") === "true";
        button.parentElement.querySelectorAll(`[data-reserve-extra="${button.dataset.reserveExpand}"]`).forEach((component) => { component.hidden = expanded; });
        button.setAttribute("aria-expanded", String(!expanded));
        const count = button.parentElement.querySelectorAll("[data-reserve-extra]").length;
        button.textContent = expanded ? `+ ${count} ${count === 1 ? "título" : "títulos"}` : "Mostrar menos";
      });
    });
  }

  function renderGoalsOverview() {
    const active = state.financialGoals.filter((goal) => goal.status !== "completed");
    const reserved = state.financialGoals.reduce((total, goal) => total + Number(goal.reserved_balance || 0), 0);
    const monthly = active.reduce((total, goal) => total + Number(goal.recommended_monthly_contribution || 0), 0);
    activeGoalsCount.textContent = String(active.length);
    goalsReservedTotal.textContent = formatMoney(reserved, "BRL");
    goalsMonthlyTotal.textContent = formatMoney(monthly, "BRL");
    uncoveredGoalsCount.textContent = String(state.financialGoals.filter((goal) => goal.coverage_status === "unlinked").length);
  }

  function renderGoalList() {
    goalCharts.forEach((chart) => chart.destroy());
    goalCharts.clear();
    financialGoalList.innerHTML = "";
    if (!state.financialGoals.length) {
      financialGoalList.append(emptyState("Crie seu primeiro objetivo para transformar uma intenção em um plano mensal."));
      return;
    }
    state.financialGoals.forEach((goal) => {
      const progress = Math.max(0, Math.min(Number(goal.progress_percentage || 0), 100));
      const item = document.createElement("article");
      item.className = `financial-goal-card pace-${goal.pace_status}`;
      item.innerHTML = `
        <div class="goal-card-visual">
          <div class="goal-progress-ring" style="--goal-progress:${progress * 3.6}deg" role="img" aria-label="${progress.toLocaleString("pt-BR")}% da meta atendida">
            <strong>${progress.toLocaleString("pt-BR", { maximumFractionDigits: 0 })}%</strong><span>atendido</span>
          </div>
        </div>
        <div class="goal-card-content">
          <div class="goal-card-heading">
            <div><span class="goal-type">${goalTypeLabel(goal.objective_type)}</span><h3>${escapeHtml(goal.name)}</h3></div>
            <span class="goal-status ${goal.pace_status}">${paceLabel(goal.pace_status)}</span>
          </div>
          <div class="goal-money-line"><strong>${formatMoney(Number(goal.reserved_balance), "BRL")}</strong><span>de ${formatMoney(Number(goal.effective_target_amount), "BRL")}</span></div>
          <div class="goal-balance-breakdown"><span>Manual: ${formatMoney(Number(goal.manual_reserved_balance || 0), "BRL")}</span><span>Investimentos: ${formatMoney(Number(goal.linked_reserved_balance || 0), "BRL")}</span></div>
          <div class="goal-details">
            <span><small>Falta</small><b>${formatMoney(Number(goal.remaining_amount), "BRL")}</b></span>
            <span><small>Aporte sugerido</small><b>${formatMoney(Number(goal.recommended_monthly_contribution), "BRL")}/mês</b></span>
            <span><small>Prazo</small><b>${formatGoalDate(goal.target_date)}</b></span>
          </div>
          <div class="goal-projection-block">
            <div class="goal-projection-heading"><strong>Composição projetada</strong><small>${escapeHtml(goal.projection?.rate_label || "Sem rendimento")} · ref. ${formatGoalDate(goal.projection?.reference_date)}</small></div>
            <div class="goal-projection-chart" data-goal-chart="${goal.id}" role="img" aria-label="Comparação entre cenário conservador e cenário com rendimento para ${escapeHtml(goal.name)}"></div>
            <div class="goal-projection-legend" data-goal-legend="${goal.id}"></div>
          </div>
          <div class="goal-coverage ${goal.coverage_status}">
            <span>${goal.coverage_status === "linked" ? "Cobertura vinculada" : "Saldo sem cobertura conferível"}</span>
            ${(goal.funding_sources || []).map((source) => `<button type="button" class="coverage-chip" data-unlink="${source.id}" title="Desvincular ${escapeHtml(source.label)}">${escapeHtml(source.label)} · ${formatMoney(Number(source.current_value_brl || 0), "BRL")} ×</button>`).join("")}
          </div>
          <div class="card-actions goal-card-actions">
            <button class="primary small-button" type="button" data-action="movement">Atualizar saldo</button>
            <button class="ghost small-button" type="button" data-action="funding">Vincular investimento</button>
            <button class="ghost small-button" type="button" data-action="edit">Editar</button>
            <button class="danger small-button" type="button" data-action="archive">Arquivar</button>
          </div>
        </div>`;
      item.querySelector('[data-action="movement"]').addEventListener("click", () => openMovementAction(goal));
      item.querySelector('[data-action="funding"]').addEventListener("click", () => openFundingAction(goal));
      item.querySelector('[data-action="edit"]').addEventListener("click", () => editGoal(goal));
      item.querySelector('[data-action="archive"]').addEventListener("click", () => archiveGoal(goal));
      item.querySelectorAll("[data-unlink]").forEach((button) => button.addEventListener("click", () => unlinkFunding(goal, button.dataset.unlink)));
      financialGoalList.append(item);
      renderGoalProjectionChart(goal, item);
    });
  }

  function renderGoalProjectionChart(goal, item) {
    const projection = goal.projection;
    const host = item.querySelector(`[data-goal-chart="${goal.id}"]`);
    const legend = item.querySelector(`[data-goal-legend="${goal.id}"]`);
    if (!projection || !host) return;
    const scenarios = [projection.conservative, projection.with_yield];
    const values = (key) => scenarios.map((scenario) => Number(scenario[key] || 0));
    legend.innerHTML = `
      <span><i class="reserved"></i>Reservado</span><span><i class="contributions"></i>Aportes futuros</span>
      <span><i class="yield"></i>Rendimento projetado</span><span><i class="uncovered"></i>Ainda descoberto</span>`;
    if (typeof window.ApexCharts !== "function") {
      host.innerHTML = `<p class="muted-copy">Conservador: ${formatMoney(Number(projection.conservative.projected_total), "BRL")} · Com rendimento: ${formatMoney(Number(projection.with_yield.projected_total), "BRL")}</p>`;
      return;
    }
    const css = getComputedStyle(document.documentElement);
    const compactCurrency = (value) => new Intl.NumberFormat("pt-BR", {
      style: "currency", currency: "BRL", notation: "compact", maximumFractionDigits: 1,
    }).format(Number(value || 0));
    const chart = new window.ApexCharts(host, {
      chart: { type: "bar", height: 190, stacked: true, toolbar: { show: false }, animations: { enabled: !window.matchMedia("(prefers-reduced-motion: reduce)").matches } },
      series: [
        { name: "Reservado", data: values("reserved") },
        { name: "Aportes futuros", data: values("future_contributions") },
        { name: "Rendimento projetado", data: values("projected_yield") },
        { name: "Ainda descoberto", data: values("uncovered") },
      ],
      colors: [css.getPropertyValue("--primary").trim() || "#00328a", css.getPropertyValue("--chart-6").trim() || "#3b82f6", css.getPropertyValue("--color-success").trim() || "#10b981", css.getPropertyValue("--color-warning").trim() || "#f59e0b"],
      plotOptions: { bar: { horizontal: true, borderRadius: 4, barHeight: "58%" } },
      xaxis: { categories: ["Conservador", "Com rendimento"], tickAmount: 3, labels: { formatter: compactCurrency } },
      dataLabels: { enabled: false }, legend: { show: false }, grid: { borderColor: css.getPropertyValue("--outline-variant").trim() || "#c3c6d6" },
      tooltip: { y: { formatter: (value) => formatMoney(value, "BRL") } },
      theme: { mode: document.documentElement.dataset.theme === "dark" ? "dark" : "light" },
    });
    chart.render();
    goalCharts.set(goal.id, chart);
  }

  function editGoal(goal) {
    Object.entries(goal).forEach(([key, value]) => { if (goalForm.elements[key]) goalForm.elements[key].value = value ?? ""; });
    goalForm.elements.target_amount.value = String(goal.target_amount || "").replace(".", ",");
    goalFormTitle.textContent = "Editar objetivo";
    showGoalForm();
    updateGoalDateRequirement();
    updateGoalYieldFields();
    goalForm.scrollIntoView({ behavior: "smooth", block: "start" });
    goalForm.elements.name.focus({ preventScroll: true });
  }

  async function archiveGoal(goal) {
    if (!window.confirm(`Arquivar o objetivo “${goal.name}”? O histórico será preservado.`)) return;
    try {
      await api(`/api/financial-goals/${goal.id}`, { method: "DELETE" });
      await loadGoalData({ force: true });
      setMessage(goalMessage, "Objetivo arquivado e origem liberada.", "success");
    } catch (error) { setMessage(goalMessage, error.message, "error"); }
  }

  function openMovementAction(goal) {
    goalActionPanel.hidden = false;
    goalMovementForm.hidden = false;
    goalFundingForm.hidden = true;
    goalActionEyebrow.textContent = "Atualização manual";
    goalActionTitle.textContent = `Atualizar ${goal.name}`;
    goalMovementForm.reset();
    goalMovementForm.elements.goal_id.value = goal.id;
    goalMovementForm.elements.movement_date.value = localIsoDate();
    setMessage(goalActionMessage, "");
    goalActionPanel.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  async function openFundingAction(goal) {
    goalActionPanel.hidden = false;
    goalMovementForm.hidden = true;
    goalFundingForm.hidden = false;
    goalActionEyebrow.textContent = "Cobertura exclusiva";
    goalActionTitle.textContent = `Vincular origem a ${goal.name}`;
    goalFundingForm.elements.goal_id.value = goal.id;
    setMessage(goalActionMessage, "");
    try {
      if (!state.portfolio) state.portfolio = await api("/api/portfolio");
      renderFundingOptions();
    } catch (error) { setMessage(goalActionMessage, error.message, "error"); }
    goalActionPanel.scrollIntoView({ behavior: "smooth", block: "center" });
  }

  function renderFundingOptions() {
    const used = new Set(state.financialGoals.flatMap((goal) => (goal.funding_sources || []).map((source) => `${source.source_type}:${source.source_id}`)));
    const assets = new Map();
    (state.portfolio?.positions || []).forEach((position) => {
      const fixedIncome = position.asset_type === "fixed_income";
      const identity = [
        position.account_id,
        String(position.currency || "BRL").toUpperCase(),
        position.asset_type || "other",
        String(position.asset_identifier || "").toUpperCase(),
        String(position.asset_name || position.asset_identifier || "").trim().toLowerCase(),
        String(position.cnpj || "").replace(/\D/g, ""),
        fixedIncome ? String(position.fixed_income_indexer || "").trim().toLowerCase() : "",
        fixedIncome ? String(position.fixed_income_maturity_date || "").trim() : "",
      ].join("\u001f");
      const asset = assets.get(identity) || { position, sources: [], emergency: false, currentValueBrlCents: 0 };
      asset.emergency ||= Boolean(position.emergency_reserve_eligible);
      asset.currentValueBrlCents += Number(position.current_value_brl_cents || 0);
      asset.sources.push(...(position.sources || []));
      if (!(position.sources || []).length && ["opening", "operation"].includes(position.source_type) && position.source_id) {
        asset.sources.push({ source_type: position.source_type, source_id: position.source_id, emergency_reserve_eligible: position.emergency_reserve_eligible });
      }
      asset.emergency ||= (position.sources || []).some((source) => source.emergency_reserve_eligible);
      assets.set(identity, asset);
    });
    const options = [];
    for (const asset of assets.values()) {
      const candidates = [...new Map(asset.sources
        .filter((source) => ["opening", "operation"].includes(source.source_type) && source.source_id)
        .map((source) => [`${source.source_type}:${source.source_id}`, source])).values()];
      if (asset.emergency || !candidates.length) continue;
      candidates.sort((left, right) => (left.source_type === "opening" ? 0 : 1) - (right.source_type === "opening" ? 0 : 1) || Number(left.source_id) - Number(right.source_id));
      const canonical = candidates[0];
      const type = canonical.source_type === "opening" ? "investment_opening" : "investment_operation";
      const name = asset.position.asset_name || asset.position.asset_identifier || "Investimento";
      const value = asset.currentValueBrlCents ? asset.currentValueBrlCents / 100 : Number(asset.position.current_value_brl || asset.position.current_value || 0);
      options.push({ key: `${type}:${canonical.source_id}`, label: `Investimento · ${name} · ${formatMoney(value, "BRL")}` });
    }
    const available = options.filter((option) => !used.has(option.key));
    goalFundingSource.innerHTML = available.map((option) => `<option value="${option.key}">${escapeHtml(option.label)}</option>`).join("") || '<option value="">Nenhuma origem disponível</option>';
    goalFundingSource.disabled = !available.length;
    goalFundingForm.querySelector('button[type="submit"]').disabled = !available.length;
  }

  async function unlinkFunding(goal, linkId) {
    try {
      await api(`/api/financial-goals/${goal.id}/funding-sources/${linkId}`, { method: "DELETE" });
      await loadGoalData({ force: true });
      setMessage(goalMessage, "Origem desvinculada; as movimentações foram preservadas.", "success");
    } catch (error) { setMessage(goalMessage, error.message, "error"); }
  }

  function closeGoalAction() {
    goalActionPanel.hidden = true;
    setMessage(goalActionMessage, "");
  }

  function openNewGoalForm() {
    resetGoalForm();
    showGoalForm();
    goalForm.elements.name.focus({ preventScroll: true });
    goalFormPanel.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function showGoalForm() {
    goalFormPanel.hidden = false;
    newGoalButton.setAttribute("aria-expanded", "true");
  }

  function resetGoalForm({ restoreFocus = false } = {}) {
    goalForm.reset();
    goalForm.elements.id.value = "";
    goalForm.elements.start_date.value = localIsoDate();
    goalFormTitle.textContent = "Novo objetivo";
    goalFormPanel.hidden = true;
    newGoalButton.setAttribute("aria-expanded", "false");
    updateGoalDateRequirement();
    updateGoalYieldFields();
    if (restoreFocus) newGoalButton.focus();
  }

  function updateGoalDateRequirement() {
    const continuous = goalForm.elements.objective_type.value === "continuous_reserve";
    goalTargetDateField.hidden = continuous;
    goalForm.elements.target_date.required = !continuous;
  }

  function updateGoalYieldFields() {
    const mode = goalYieldMode.value;
    goalYieldPercentageField.hidden = mode === "none";
    goalYieldPercentageField.querySelector("input").disabled = mode === "none";
    goalYieldPercentageField.querySelector("input").placeholder = mode === "cdi_percentage" ? "100,00" : "12,00";
  }

  function goalTypeLabel(type) { return ({ target: "Meta", annual_provision: "Provisão anual", continuous_reserve: "Reserva contínua" })[type] || "Objetivo"; }
  function paceLabel(status) { return ({ on_track: "No ritmo", attention: "Atenção", late: "Atrasado", overdue: "Prazo vencido", paused: "Pausado", completed: "Concluído" })[status] || "Em andamento"; }
  function formatGoalDate(value) { return value ? new Date(`${value}T12:00:00`).toLocaleDateString("pt-BR", { month: "short", year: "numeric" }) : "Contínuo"; }
  function localIsoDate() { const now = new Date(); now.setMinutes(now.getMinutes() - now.getTimezoneOffset()); return now.toISOString().slice(0, 10); }

  async function handleLimitSubmit(event) {
    event.preventDefault();
    setMessage(limitMessage, "");
    const data = formData(limitForm);
    data.month = state.limitMonth;
    const isEditing = Boolean(data.id);
    setFormBusy(limitForm, true);
    try {
      await api(isEditing ? `/api/spending-limits/${data.id}` : "/api/spending-limits", {
        method: isEditing ? "PUT" : "POST",
        body: data,
      });
      resetLimitForm();
      await loadSpendingLimits();
      await loadCurrentSpendingLimits();
      renderLimits();
      onLimitsChanged();
      setMessage(limitMessage, "Limite salvo.", "success");
    } catch (error) {
      setMessage(limitMessage, error.message, "error");
    } finally {
      setFormBusy(limitForm, false);
      renderLimitCategories();
    }
  }

  function editSpendingLimit(limit) {
    limitFormTitle.textContent = "Editar limite";
    limitForm.elements.id.value = limit.id;
    limitForm.elements.limit_amount.value = limit.limit_amount.replace(".", ",");
    limitForm.elements.notes.value = limit.notes || "";
    limitCategory.value = String(limit.category_id);
    renderLimitSubcategories();
    limitSubcategory.value = limit.subcategory_id ? String(limit.subcategory_id) : "";
    cancelLimitEditButton.hidden = false;
    limitForm.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  async function deleteSpendingLimit(id) {
    try {
      await api(`/api/spending-limits/${id}`, { method: "DELETE" });
      await loadSpendingLimits();
      await loadCurrentSpendingLimits();
      renderLimits();
      onLimitsChanged();
      setMessage(limitMessage, "Limite excluído.", "success");
    } catch (error) {
      setMessage(limitMessage, error.message, "error");
    }
  }

  function resetLimitForm() {
    limitForm.reset();
    limitForm.elements.id.value = "";
    limitFormTitle.textContent = "Novo limite";
    cancelLimitEditButton.hidden = true;
    limitMonthInput.value = state.limitMonth;
    renderLimitCategories();
    setMessage(limitMessage, "");
  }

  async function shiftLimitMonth(delta) {
    state.limitMonth = shiftMonth(state.limitMonth, delta);
    resetLimitForm();
    await loadSpendingLimits();
    renderLimits();
  }

  function renderLimits() {
    selectLimitsTab(state.limitsTab);
    limitMonthLabel.textContent = formatMonthShortLabel(state.limitMonth);
    limitMonthInput.value = state.limitMonth;
    renderLimitCategories();
    renderSpendingLimitList();
  }

  function renderLimitCategories() {
    const selectedCategory = limitCategory.value;
    const expenseCategories = state.categories.filter((category) => category.group_type === "expense");
    limitCategory.innerHTML = expenseCategories.map((category) => (
      `<option value="${category.id}">${escapeHtml(category.name)}</option>`
    )).join("") || '<option value="">Cadastre uma categoria de despesa</option>';
    if (expenseCategories.some((category) => String(category.id) === selectedCategory)) {
      limitCategory.value = selectedCategory;
    }
    limitCategory.disabled = expenseCategories.length === 0;
    limitForm.querySelector('button[type="submit"]').disabled = expenseCategories.length === 0;
    renderLimitSubcategories();
  }

  function renderLimitSubcategories() {
    const category = state.categories.find((entry) => String(entry.id) === limitCategory.value);
    const subcategories = category ? category.subcategories || [] : [];
    const selectedSubcategory = limitSubcategory.value;
    limitSubcategory.innerHTML = '<option value="">Categoria inteira</option>' + subcategories.map((subcategory) => (
      `<option value="${subcategory.id}">${escapeHtml(subcategory.name)}</option>`
    )).join("");
    if (subcategories.some((subcategory) => String(subcategory.id) === selectedSubcategory)) {
      limitSubcategory.value = selectedSubcategory;
    }
    limitSubcategory.disabled = subcategories.length === 0;
  }

  function renderSpendingLimitList() {
    spendingLimitList.innerHTML = "";
    const rows = spendingLimitRows();
    renderLimitSummary(rows);
    if (rows.length === 0) {
      spendingLimitList.append(emptyState("Nenhum limite vigente para este mês."));
      return;
    }
    rows.forEach((row) => {
      const item = document.createElement("article");
      item.className = `spending-limit-item ${row.percent > 1 ? "over-limit" : row.percent >= 0.8 ? "near-limit" : ""}`;
      item.innerHTML = `
        <div class="limit-item-main">
          <div>
            <strong>${escapeHtml(row.categoryLabel)}</strong>
            ${row.subcategoryLabel ? `<small class="limit-subcategory">${escapeHtml(row.subcategoryLabel)}</small>` : '<small class="limit-subcategory">Categoria inteira</small>'}
            <span>${formatMoney(row.spent, "BRL")} de ${formatMoney(row.limit, "BRL")}</span>
          </div>
          <strong>${formatPercent(row.percent)}</strong>
          ${row.percent >= 0.8 && row.percent <= 1 ? '<small class="limit-attention-label">Atenção: próximo do limite</small>' : ""}
        </div>
        <div class="limit-progress" aria-label="${escapeHtml(row.label)} consumido">
          <span style="width:${Math.min(row.percent * 100, 100)}%"></span>
        </div>
        <div class="limit-item-footer">
          <span>${row.remaining >= 0 ? "Disponível" : "Excedido"}: ${formatMoney(Math.abs(row.remaining), "BRL")}</span>
          <div class="card-actions">
            <button class="ghost small-button" type="button" data-action="edit">Editar</button>
            <button class="danger small-button" type="button" data-action="delete">Excluir</button>
          </div>
        </div>
      `;
      item.querySelector('[data-action="edit"]').addEventListener("click", () => editSpendingLimit(row.limitRecord));
      item.querySelector('[data-action="delete"]').addEventListener("click", () => deleteSpendingLimit(row.limitRecord.id));
      spendingLimitList.append(item);
    });
  }

  function renderLimitSummary(rows) {
    const totals = rows.reduce((summary, row) => {
      summary.spent += row.spent;
      summary.limit += row.limit;
      return summary;
    }, { spent: 0, limit: 0 });
    limitConsumedSummary.textContent = formatMoney(totals.spent, "BRL");
    limitDefinedSummary.textContent = formatMoney(totals.limit, "BRL");
    limitAvailableSummary.textContent = formatMoney(totals.limit - totals.spent, "BRL");
    limitAvailableSummary.classList.toggle("danger-text", totals.spent > totals.limit && totals.limit > 0);
  }

  function renderLimitAlerts(month = currentMonthValue()) {
    const exceededRows = exceededCurrentLimitRows(month);
    navButtons.forEach((button) => {
      if (button.dataset.view === "limits") {
        button.classList.toggle("has-alert", exceededRows.length > 0);
      }
    });
    if (!cockpitLimitAlert) {
      return;
    }
    if (exceededRows.length === 0) {
      cockpitLimitAlert.hidden = true;
      cockpitLimitAlert.innerHTML = "";
      return;
    }
    const worst = exceededRows[0];
    const overflowTotal = exceededRows.reduce((total, row) => total + Math.abs(row.remaining), 0);
    cockpitLimitAlert.hidden = false;
    cockpitLimitAlert.innerHTML = `
      <button class="limit-alert-card" type="button" data-go-limits>
        <span class="limit-alert-beacon" aria-hidden="true"></span>
        <span>
          <strong>${exceededRows.length} limite(s) estourado(s)</strong>
          <small>Maior desvio: ${escapeHtml(worst.label)} em ${formatMoney(Math.abs(worst.remaining), "BRL")}. Total excedido: ${formatMoney(overflowTotal, "BRL")}.</small>
        </span>
        <b>Ver limites</b>
      </button>
    `;
    cockpitLimitAlert.querySelector("[data-go-limits]").addEventListener("click", goToLimits);
  }

  function exceededCurrentLimitRows(month = currentMonthValue()) {
    return spendingLimitRows(state.currentSpendingLimits, month)
      .filter((row) => row.percent > 1)
      .sort((a, b) => Math.abs(b.remaining) - Math.abs(a.remaining));
  }

  function spendingLimitRows(limits = state.spendingLimits, targetMonth = state.limitMonth) {
    return limits.map((limit) => {
      const spent = Number(limit.spent_amount || 0);
      const limitAmount = Number(limit.limit_amount);
      return {
        limitRecord: limit,
        label: limit.subcategory_name ? `${limit.category_name} / ${limit.subcategory_name}` : limit.category_name,
        categoryLabel: limit.category_name,
        subcategoryLabel: limit.subcategory_name || "",
        spent,
        limit: limitAmount,
        percent: limitAmount > 0 ? spent / limitAmount : 0,
        remaining: limitAmount - spent,
      };
    }).sort((a, b) => b.percent - a.percent || b.spent - a.spent);
  }

  function buildSpendingLimitSpentIndex(targetMonth = state.limitMonth) {
    const index = new Map();
    const addSpent = (month, categoryId, subcategoryId, amount) => {
      const categoryKey = spendingLimitSpentKey(month, categoryId, "");
      index.set(categoryKey, (index.get(categoryKey) || 0) + amount);
      if (subcategoryId) {
        const subcategoryKey = spendingLimitSpentKey(month, categoryId, subcategoryId);
        index.set(subcategoryKey, (index.get(subcategoryKey) || 0) + amount);
      }
    };
    state.transactions.forEach((transaction) => {
      const month = transaction.date ? transaction.date.slice(0, 7) : "";
      if (transaction.type !== "expense" || month !== targetMonth || isCreditCardPaymentTransaction(transaction)) {
        return;
      }
      addSpent(month, transaction.category_id, transaction.subcategory_id, Number(transaction.amount_brl || transaction.amount));
    });
    state.cardTransactions.forEach((transaction) => {
      const month = transaction.invoice_month || (transaction.date ? transaction.date.slice(0, 7) : "");
      if (transaction.type !== "expense" || month !== targetMonth) {
        return;
      }
      addSpent(month, transaction.category_id, transaction.subcategory_id, Number(transaction.amount_brl || transaction.amount));
    });
    return index;
  }

  function spendingLimitSpentFromIndex(index, limit, targetMonth = state.limitMonth) {
    return index.get(spendingLimitSpentKey(targetMonth, limit.category_id, limit.subcategory_id || "")) || 0;
  }

  function spendingLimitSpentKey(month, categoryId, subcategoryId) {
    return `${month || ""}|${categoryId || ""}|${subcategoryId || ""}`;
  }

  function isCreditCardPaymentTransaction(transaction) {
    return Boolean(transaction?.is_credit_card_payment);
  }

  return {
    loadSpendingLimits,
    loadCurrentSpendingLimits,
    renderLimits,
    renderLimitAlerts,
    resetLimitForm,
    loadGoalDataIfNeeded,
  };
}
