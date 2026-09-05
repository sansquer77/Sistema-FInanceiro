import { bindRovingTablist, syncRovingTabState, transitionView } from "./tab-utils.js";
import { createLoadPolicy } from "./load-policy.js";

export function registerUserAdminView(context) {
  const {
    api,
    elements,
    formData,
    loadAll,
    resetSessionState,
    setMessage,
    decisionModal,
    theme,
    density,
    state,
    onShowAuth,
  } = context;
  let emailConfigPresets = [];
  let aiConfigPresets = [];
  let consultorSettings = null;
  let backupRestoreToken = "";
  let backupRestorePasswordInMemory = "";
  const preferencesLoadPolicy = createLoadPolicy();

  function loadPreferences({ force = false } = {}) {
    return preferencesLoadPolicy.run(() => Promise.all([
      loadEmailConfigStatus(),
      loadAIConfigStatus({ loadConsultor: false }),
      loadConsultorConfigStatus(),
      loadConsultorProfile(),
      loadMaisRetornoConfigStatus(),
      loadBackupSettings(),
    ]), { force });
  }

  function switchUserTab(tabName) {
    if (!elements.userPrefTabs) {
      return;
    }
    const buttons = elements.userPrefTabs.querySelectorAll(".user-pref-tab");
    syncRovingTabState(buttons, tabName, (button) => button.dataset.userTab);
    const tabButton = elements.userPrefTabs.querySelector(`[data-user-tab="${tabName}"]`);
    const panelId = tabButton ? tabButton.getAttribute("aria-controls") : "";
    transitionView(() => {
      document.querySelectorAll(".user-pref-panel").forEach((panel) => {
        panel.hidden = true;
      });
      const panel = document.getElementById(panelId);
      if (panel) panel.hidden = false;
    });
  }

  function syncThemePreference() {
    if (!elements.themePreference || !theme) {
      return;
    }
    const currentTheme = theme.storedTheme();
    elements.themePreference.querySelectorAll("[data-theme-option]").forEach((button) => {
      const isActive = button.dataset.themeOption === currentTheme;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  }

  function handleThemePreferenceClick(event) {
    const button = event.target.closest("[data-theme-option]");
    if (!button || !elements.themePreference?.contains(button) || !theme) {
      return;
    }
    theme.setTheme(button.dataset.themeOption);
    syncThemePreference();
  }

  function syncDensityPreference() {
    if (!elements.densityPreference || !density) {
      return;
    }
    const currentDensity = density.storedDensity();
    elements.densityPreference.querySelectorAll("[data-density-option]").forEach((button) => {
      const isActive = button.dataset.densityOption === currentDensity;
      button.classList.toggle("active", isActive);
      button.setAttribute("aria-pressed", String(isActive));
    });
  }

  function handleDensityPreferenceClick(event) {
    const button = event.target.closest("[data-density-option]");
    if (!button || !elements.densityPreference?.contains(button) || !density) {
      return;
    }
    density.setDensity(button.dataset.densityOption);
    syncDensityPreference();
  }

  async function loadEmailConfigStatus() {
    if (!elements.emailConfigForm) {
      return;
    }
    try {
      const status = await api("/api/email-config");
      emailConfigPresets = status.presets || [];
      elements.emailConfigProvider.value = status.provider || "gmail";
      elements.emailConfigForm.elements.sender.value = status.sender || state.user?.email || "";
      elements.emailConfigForm.elements.password.value = "";
      if (elements.emailConfigForm.elements.smtp_server) {
        elements.emailConfigForm.elements.smtp_server.value = status.smtp_server || "";
      }
      if (elements.emailConfigForm.elements.smtp_port) {
        elements.emailConfigForm.elements.smtp_port.value = status.smtp_port || 587;
      }
      if (elements.emailConfigForm.elements.use_tls) {
        elements.emailConfigForm.elements.use_tls.checked = status.use_tls !== false;
      }
      renderEmailConfigHelp(status);
    } catch (error) {
      setMessage(elements.emailConfigMessage, error.message, "error");
    }
  }

  function renderEmailConfigHelp(status = null) {
    if (!elements.emailConfigForm) {
      return;
    }
    const provider = elements.emailConfigProvider.value;
    const preset = emailConfigPresets.find((item) => item.provider === provider);
    elements.emailConfigManualFields.hidden = provider !== "manual";
    if (preset) {
      elements.emailConfigPreset.innerHTML = `
        <strong>${preset.label}</strong>
        <span>${preset.smtp_server}:${preset.smtp_port} · STARTTLS</span>
      `;
    } else {
      elements.emailConfigPreset.innerHTML = `
        <strong>Configuração manual</strong>
        <span>Informe servidor, porta e uso de STARTTLS conforme seu provedor.</span>
      `;
    }
    if (status?.configured) {
      setMessage(elements.emailConfigMessage, `Recuperação configurada para ${status.sender}.`, "success");
    } else if (!elements.emailConfigMessage.textContent) {
      setMessage(elements.emailConfigMessage, "Recuperação por email ainda não configurada neste Mac.", "");
    }
  }

  function isAICustomProvider() {
    if (!elements.aiConfigProvider) {
      return false;
    }
    const value = elements.aiConfigProvider.value;
    return value === "custom" || value === "local";
  }

  function currentAIPreset() {
    if (!elements.aiConfigProvider) {
      return null;
    }
    return aiConfigPresets.find((item) => item.provider === elements.aiConfigProvider.value) || null;
  }

  function setAIFieldVisibility(element, visible) {
    if (!element) {
      return;
    }
    element.hidden = !visible;
  }

  function renderAIConfigFields() {
    if (!elements.aiConfigCustomFields) {
      return;
    }
    const customProvider = isAICustomProvider();
    const preset = currentAIPreset();
    const authType = elements.aiConfigAuthType?.value || preset?.auth_type || "bearer";
    const requiresApiKey = authType === "bearer";
    elements.aiConfigCustomFields.hidden = false;
    setAIFieldVisibility(elements.aiConfigBaseUrlField, customProvider);
    setAIFieldVisibility(elements.aiConfigAuthTypeField, customProvider);
    setAIFieldVisibility(elements.aiConfigModelField, true);
    setAIFieldVisibility(elements.aiConfigApiKeyField, requiresApiKey);
    setAIFieldVisibility(elements.aiConfigTimeoutField, customProvider);
    setAIFieldVisibility(elements.aiConfigTemperatureField, customProvider);
    setAIFieldVisibility(elements.aiConfigMaxTokensField, customProvider);
  }

  function applyAIPreset() {
    if (!elements.aiConfigProvider) {
      return;
    }
    const preset = aiConfigPresets.find((item) => item.provider === elements.aiConfigProvider.value);
    if (!preset) {
      return;
    }
    if (elements.aiConfigBaseUrl) {
      elements.aiConfigBaseUrl.value = preset.base_url || "";
    }
    if (elements.aiConfigAuthType) {
      elements.aiConfigAuthType.value = preset.auth_type || "bearer";
    }
  }

  async function loadAIConfigStatus({ loadConsultor = true } = {}) {
    if (!elements.aiConfigForm) {
      return;
    }
    try {
      const status = await api("/api/ai-settings");
      aiConfigPresets = status.presets || [];
      elements.aiConfigEnabled.checked = status.enabled === true;
      elements.aiConfigProvider.value = status.provider || "custom";
      elements.aiConfigBaseUrl.value = status.base_url || "";
      elements.aiConfigModel.value = status.model || "";
      elements.aiConfigAuthType.value = status.auth_type || "bearer";
      elements.aiConfigApiKey.value = "";
      if (elements.aiConfigTimeout) {
        elements.aiConfigTimeout.value = String(status.timeout_seconds || 10);
      }
      if (elements.aiConfigTemperature) {
        elements.aiConfigTemperature.value = String(status.temperature || 0.2);
      }
      if (elements.aiConfigMaxTokens) {
        elements.aiConfigMaxTokens.value = String(status.max_tokens || 700);
      }
      renderAIConfigFields();
      if (status.configured && status.enabled) {
        setMessage(elements.aiConfigMessage, "IA ativada para reescrita de resumo.", "success");
      } else if (status.configured) {
        setMessage(elements.aiConfigMessage, "IA configurada, mas desligada. Ative para usar a reescrita.", "");
      } else {
        setMessage(elements.aiConfigMessage, "IA não configurada.", "");
      }
      if (loadConsultor) await loadConsultorConfigStatus();
    } catch (error) {
      setMessage(elements.aiConfigMessage, error.message, "error");
    }
  }

  async function handleAIConfigSubmit(event) {
    event.preventDefault();
    setMessage(elements.aiConfigMessage, "");
    const data = {
      enabled: elements.aiConfigEnabled ? elements.aiConfigEnabled.checked : false,
      provider: elements.aiConfigProvider ? elements.aiConfigProvider.value : "custom",
      base_url: elements.aiConfigBaseUrl ? elements.aiConfigBaseUrl.value : "",
      model: elements.aiConfigModel ? elements.aiConfigModel.value : "",
      auth_type: elements.aiConfigAuthType ? elements.aiConfigAuthType.value : "bearer",
      api_key: elements.aiConfigApiKey ? elements.aiConfigApiKey.value : "",
      timeout_seconds: elements.aiConfigTimeout ? parseInt(elements.aiConfigTimeout.value, 10) || 10 : 10,
      temperature: elements.aiConfigTemperature ? parseFloat(elements.aiConfigTemperature.value) || 0.2 : 0.2,
      max_tokens: elements.aiConfigMaxTokens ? parseInt(elements.aiConfigMaxTokens.value, 10) || 700 : 700,
    };
    const customProvider = isAICustomProvider();
    if (!customProvider && aiConfigPresets.length > 0) {
      data.base_url = "";
      data.auth_type = aiConfigPresets.find((item) => item.provider === data.provider)?.auth_type || "bearer";
    }
    try {
      const status = await api("/api/ai-settings", { method: "PUT", body: data });
      elements.aiConfigApiKey.value = "";
      aiConfigPresets = status.presets || aiConfigPresets;
      await loadAIConfigStatus();
      await loadConsultorConfigStatus();
      setMessage(elements.aiConfigMessage, "Configuração de IA salva.", "success");
    } catch (error) {
      setMessage(elements.aiConfigMessage, error.message, "error");
    }
  }

  async function loadConsultorConfigStatus() {
    if (!elements.consultorConfigForm) {
      return;
    }
    try {
      const status = await api("/api/consultor/config");
      consultorSettings = status;
      const aiReady = status.ai_configured && status.ai_enabled;
      elements.consultorEnabled.checked = status.consultor_enabled === true;
      elements.consultorInvestorProfile.value = status.investor_profile || "moderado";
      setConsultorConfigEnabled(aiReady);
      if (status.available) {
        setMessage(elements.consultorConfigMessage, "Consultor ativado.", "success");
      } else if (!aiReady) {
        setMessage(elements.consultorConfigMessage, "Configure e ative a IA antes de habilitar o Consultor.", "");
      } else if (!status.consultor_enabled) {
        setMessage(elements.consultorConfigMessage, "Consultor desligado.", "");
      } else if (!status.data_access_consent) {
        setMessage(elements.consultorConfigMessage, "Consentimento de dados pendente.", "");
      } else {
        setMessage(elements.consultorConfigMessage, "Consultor indisponível.", "");
      }
    } catch (error) {
      setMessage(elements.consultorConfigMessage, error.message, "error");
    }
  }

  function setConsultorConfigEnabled(enabled) {
    if (elements.consultorEnabled) {
      elements.consultorEnabled.disabled = !enabled;
    }
    if (elements.consultorInvestorProfile) {
      elements.consultorInvestorProfile.disabled = !enabled;
    }
    const submitButton = elements.consultorConfigForm?.querySelector('button[type="submit"]');
    if (submitButton) {
      submitButton.disabled = !enabled;
    }
  }

  async function consultorConsentAccepted() {
    if (consultorSettings?.data_access_consent) {
      return true;
    }
    if (!decisionModal?.choose) {
      return false;
    }
    const choice = await decisionModal.choose({
      title: "Habilitar Consultor",
      message: (
        "O Consultor enviará para a IA configurada apenas dados financeiros agregados e minimizados do app, "
        + "como carteira, score, tendências, vencimentos e limites relevantes ao card escolhido. "
        + "Senhas, chaves de API e o Perfil Complementar criptografado em repouso não são enviados integralmente. "
        + "As respostas têm caráter educacional e não executam alterações nos seus dados."
      ),
      actions: [
        { value: true, label: "Aceitar e habilitar", variant: "primary" },
        { value: false, label: "Cancelar", variant: "ghost" },
      ],
    });
    return choice === true;
  }

  async function handleConsultorConfigSubmit(event) {
    event.preventDefault();
    setMessage(elements.consultorConfigMessage, "");
    if (!(consultorSettings?.ai_configured && consultorSettings?.ai_enabled)) {
      setMessage(elements.consultorConfigMessage, "Configure e ative a IA antes de habilitar o Consultor.", "error");
      return;
    }
    const wantsEnabled = elements.consultorEnabled ? elements.consultorEnabled.checked : false;
    if (!wantsEnabled && consultorSettings?.consultor_enabled) {
      const confirmed = await confirmConsultorDisable();
      if (!confirmed) {
        elements.consultorEnabled.checked = true;
        setMessage(elements.consultorConfigMessage, "Consultor mantido ativo.", "");
        return;
      }
    }
    const consent = wantsEnabled ? await consultorConsentAccepted() : false;
    if (wantsEnabled && !consent) {
      elements.consultorEnabled.checked = false;
      setMessage(elements.consultorConfigMessage, "Consultor não habilitado sem consentimento.", "error");
      return;
    }
    try {
      const status = await api("/api/consultor/config", {
        method: "POST",
        body: {
          consultor_enabled: wantsEnabled,
          investor_profile: elements.consultorInvestorProfile ? elements.consultorInvestorProfile.value : "moderado",
          data_access_consent: consent,
        },
      });
      consultorSettings = status;
      await loadConsultorConfigStatus();
      window.dispatchEvent(new CustomEvent("consultor:settings-changed"));
      setMessage(elements.consultorConfigMessage, status.available ? "Consultor ativado." : "Consultor salvo.", "success");
    } catch (error) {
      setMessage(elements.consultorConfigMessage, error.message, "error");
    }
  }

  async function confirmConsultorDisable() {
    if (!decisionModal?.choose) {
      return true;
    }
    const choice = await decisionModal.choose({
      title: "Desativar Consultor",
      message: (
        "Ao desativar o Consultor, o histórico de análises geradas será apagado deste usuário. "
        + "As configurações de IA permanecem salvas para Tendências e outros recursos."
      ),
      actions: [
        { value: false, label: "Manter ativo", variant: "ghost" },
        { value: true, label: "Desativar e apagar histórico", variant: "danger" },
      ],
    });
    return choice === true;
  }

  async function loadConsultorProfile() {
    if (!elements.consultorProfileForm) {
      return;
    }
    try {
      const status = await api("/api/consultor/perfil-complementar");
      const profile = status.profile || {};
      elements.consultorProfileAge.value = profile.idade || "";
      elements.consultorProfileHome.value = profileValue(profile.possui_imovel_proprio);
      elements.consultorProfileDependents.value = profileValue(profile.possui_dependentes);
      elements.consultorProfileDependentsCount.value = profile.numero_dependentes || "";
      elements.consultorProfileGoal.value = profile.objetivo_financeiro_principal || "";
      elements.consultorProfileHorizon.value = profile.horizonte_investimento_principal || "";
      elements.consultorProfileLossTolerance.value = profile.tolerancia_perdas || "";
      elements.consultorProfileIncome.value = profile.renda_mensal_aproximada || "";
      renderConsultorProfileFields();
      setMessage(
        elements.consultorProfileMessage,
        status.configured ? "Perfil complementar salvo." : "Perfil complementar ainda não preenchido.",
        status.configured ? "success" : "",
      );
    } catch (error) {
      setMessage(elements.consultorProfileMessage, error.message, "error");
    }
  }

  function profileValue(value) {
    if (value === true) {
      return "true";
    }
    if (value === false) {
      return "false";
    }
    return "";
  }

  function optionalBoolean(value) {
    if (value === "true") {
      return true;
    }
    if (value === "false") {
      return false;
    }
    return "";
  }

  function renderConsultorProfileFields() {
    if (!elements.consultorProfileDependentsCountField) {
      return;
    }
    const hasDependents = elements.consultorProfileDependents?.value === "true";
    elements.consultorProfileDependentsCountField.hidden = !hasDependents;
    if (!hasDependents && elements.consultorProfileDependentsCount) {
      elements.consultorProfileDependentsCount.value = "";
    }
  }

  async function handleConsultorProfileSubmit(event) {
    event.preventDefault();
    setMessage(elements.consultorProfileMessage, "");
    const data = {
      idade: elements.consultorProfileAge?.value || "",
      possui_imovel_proprio: optionalBoolean(elements.consultorProfileHome?.value || ""),
      possui_dependentes: optionalBoolean(elements.consultorProfileDependents?.value || ""),
      numero_dependentes: elements.consultorProfileDependentsCount?.value || "",
      objetivo_financeiro_principal: elements.consultorProfileGoal?.value || "",
      horizonte_investimento_principal: elements.consultorProfileHorizon?.value || "",
      tolerancia_perdas: elements.consultorProfileLossTolerance?.value || "",
      renda_mensal_aproximada: elements.consultorProfileIncome?.value || "",
    };
    try {
      await api("/api/consultor/perfil-complementar", { method: "POST", body: data });
      await loadConsultorProfile();
      setMessage(elements.consultorProfileMessage, "Perfil complementar salvo.", "success");
    } catch (error) {
      setMessage(elements.consultorProfileMessage, error.message, "error");
    }
  }

  async function handleConsultorProfileDelete() {
    setMessage(elements.consultorProfileMessage, "");
    try {
      await api("/api/consultor/perfil-complementar", { method: "DELETE" });
      elements.consultorProfileForm.reset();
      renderConsultorProfileFields();
      setMessage(elements.consultorProfileMessage, "Perfil complementar excluído.", "success");
    } catch (error) {
      setMessage(elements.consultorProfileMessage, error.message, "error");
    }
  }

  async function handleEmailSubmit(event) {
    event.preventDefault();
    setMessage(elements.emailMessage, "");
    try {
      const response = await api("/api/me/email", { method: "POST", body: formData(elements.emailForm) });
      state.user = response.user;
      elements.userName.textContent = state.user.name;
      elements.emailForm.elements.current_password.value = "";
      setMessage(elements.emailMessage, "Email atualizado.", "success");
    } catch (error) {
      setMessage(elements.emailMessage, error.message, "error");
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault();
    setMessage(elements.passwordMessage, "");
    try {
      await api("/api/me/password", { method: "POST", body: formData(elements.passwordForm) });
      elements.passwordForm.reset();
      setMessage(elements.passwordMessage, "Senha atualizada.", "success");
    } catch (error) {
      setMessage(elements.passwordMessage, error.message, "error");
    }
  }

  async function handleEmailConfigSubmit(event) {
    event.preventDefault();
    setMessage(elements.emailConfigMessage, "");
    const data = formData(elements.emailConfigForm);
    data.use_tls = elements.emailConfigForm.elements.use_tls ? elements.emailConfigForm.elements.use_tls.checked : true;
    try {
      const status = await api("/api/email-config", { method: "POST", body: data });
      elements.emailConfigForm.elements.password.value = "";
      emailConfigPresets = status.presets || emailConfigPresets;
      renderEmailConfigHelp(status);
      setMessage(elements.emailConfigMessage, `Recuperação configurada para ${status.sender}.`, "success");
    } catch (error) {
      setMessage(elements.emailConfigMessage, error.message, "error");
    }
  }

  async function loadMaisRetornoConfigStatus() {
    if (!elements.maisRetornoConfigForm) {
      return;
    }
    try {
      const status = await api("/api/mais-retorno-config");
      elements.maisRetornoEnabled.checked = status.enabled === true;
      elements.maisRetornoApiKey.value = "";
      if (status.configured && status.enabled) {
        setMessage(elements.maisRetornoConfigMessage, "API Mais Retorno ativada para cotas de fundos.", "success");
      } else if (status.configured) {
        setMessage(elements.maisRetornoConfigMessage, "Chave salva, mas busca desligada. Ative para usar.", "");
      } else {
        setMessage(elements.maisRetornoConfigMessage, "Mais Retorno não configurado.", "");
      }
    } catch (error) {
      setMessage(elements.maisRetornoConfigMessage, error.message, "error");
    }
  }

  async function handleMaisRetornoConfigSubmit(event) {
    event.preventDefault();
    setMessage(elements.maisRetornoConfigMessage, "");
    const data = {
      enabled: elements.maisRetornoEnabled ? elements.maisRetornoEnabled.checked : false,
      api_key: elements.maisRetornoApiKey ? elements.maisRetornoApiKey.value : "",
    };
    try {
      const status = await api("/api/mais-retorno-config", { method: "PUT", body: data });
      elements.maisRetornoApiKey.value = "";
      setMessage(elements.maisRetornoConfigMessage, status.enabled ? "API Mais Retorno ativada." : "API Mais Retorno desligada.", "success");
    } catch (error) {
      setMessage(elements.maisRetornoConfigMessage, error.message, "error");
    }
  }

  async function loadBackupSettings() {
    if (!elements.backupSettingsForm) return;
    try {
      const status = await api("/api/backup/settings");
      elements.backupDirectory.value = status.backup_directory || "";
      elements.backupFrequency.value = status.schedule_frequency || "weekly";
      elements.backupRetention.value = String(status.retention_count || 5);
      elements.backupRememberPassword.checked = status.remember_password === true;
      elements.backupPassword.value = "";
      elements.backupPasswordConfirmation.value = "";
      setBackupControlsEnabled(status.can_manage === true);
      renderBackupStatus(status);
      setMessage(
        elements.backupSettingsMessage,
        status.can_manage
          ? (status.configured ? "Política de backup configurada para esta instalação." : "Configure o primeiro backup completo.")
          : "Somente o responsável pela instalação pode alterar ou restaurar backups.",
        status.configured ? "success" : "",
      );
    } catch (error) {
      setMessage(elements.backupSettingsMessage, error.message, "error");
    }
  }

  function setBackupControlsEnabled(enabled) {
    [elements.backupSettingsForm, elements.backupRunForm, elements.backupRestoreForm].forEach((form) => {
      form?.querySelectorAll("input, select, button").forEach((control) => {
        control.disabled = !enabled;
      });
    });
  }

  function renderBackupStatus(status) {
    if (!elements.backupLastStatus) return;
    if (status.last_backup_status === "success" && status.last_backup_at) {
      const when = new Date(`${String(status.last_backup_at).replace(" ", "T")}Z`);
      const label = Number.isNaN(when.getTime()) ? status.last_backup_at : when.toLocaleString("pt-BR");
      elements.backupLastStatus.textContent = `Último backup concluído em ${label}: ${status.last_package_filename}.`;
    } else if (status.last_backup_status === "failed") {
      elements.backupLastStatus.textContent = `A última tentativa falhou. ${status.last_error || "Tente novamente."}`;
    } else {
      elements.backupLastStatus.textContent = "Nenhum backup executado.";
    }
  }

  async function handleBackupSettingsSubmit(event) {
    event.preventDefault();
    setMessage(elements.backupSettingsMessage, "");
    try {
      const status = await api("/api/backup/settings", {
        method: "PUT",
        body: {
          backup_directory: elements.backupDirectory.value,
          schedule_frequency: elements.backupFrequency.value,
          retention_count: Number(elements.backupRetention.value),
          remember_password: elements.backupRememberPassword.checked,
          password: elements.backupPassword.value,
          password_confirmation: elements.backupPasswordConfirmation.value,
        },
      });
      renderBackupStatus(status);
      elements.backupPassword.value = "";
      elements.backupPasswordConfirmation.value = "";
      setMessage(elements.backupSettingsMessage, "Política de backup salva.", "success");
    } catch (error) {
      setMessage(elements.backupSettingsMessage, error.message, "error");
    }
  }

  async function handleBackupRunSubmit(event) {
    event.preventDefault();
    setMessage(elements.backupRunMessage, "Gerando e validando o pacote…");
    try {
      const result = await api("/api/backup/run", {
        method: "POST", body: { password: elements.backupRunPassword.value },
      });
      elements.backupRunPassword.value = "";
      setMessage(elements.backupRunMessage, `Backup concluído: ${result.package_filename}.`, "success");
      await loadBackupSettings();
    } catch (error) {
      setMessage(elements.backupRunMessage, error.message, "error");
    }
  }

  async function handleBackupRestoreValidate(event) {
    event.preventDefault();
    backupRestoreToken = "";
    backupRestorePasswordInMemory = "";
    elements.backupRestoreConfirmButton.hidden = true;
    setMessage(elements.backupRestoreMessage, "Validando pacote sem alterar o ambiente…");
    try {
      const password = elements.backupRestorePassword.value;
      const result = await api("/api/backup/validate", {
        method: "POST",
        body: { package_path: elements.backupRestorePath.value, password },
      });
      backupRestoreToken = result.confirmation_token;
      backupRestorePasswordInMemory = password;
      elements.backupRestoreConfirmButton.hidden = false;
      setMessage(
        elements.backupRestoreMessage,
        `Pacote válido (${result.app_version}, schema ${result.schema_version}). Confirme para substituir o ambiente completo.`,
        "success",
      );
    } catch (error) {
      setMessage(elements.backupRestoreMessage, error.message, "error");
    }
  }

  async function handleBackupRestoreConfirm() {
    if (!backupRestoreToken || !backupRestorePasswordInMemory) return;
    const choice = await decisionModal?.choose({
      title: "Restaurar ambiente completo",
      message: "Todos os usuários e dados atuais serão substituídos pelo pacote validado. Antes da troca, o app criará um backup de segurança recuperável. Deseja continuar?",
      actions: [
        { value: false, label: "Cancelar", variant: "ghost" },
        { value: true, label: "Restaurar ambiente", variant: "danger" },
      ],
    });
    if (choice !== true) return;
    setMessage(elements.backupRestoreMessage, "Criando salvaguarda e restaurando…");
    try {
      const result = await api("/api/backup/restore", {
        method: "POST",
        body: { confirmation_token: backupRestoreToken, password: backupRestorePasswordInMemory },
      });
      backupRestoreToken = "";
      backupRestorePasswordInMemory = "";
      elements.backupRestorePassword.value = "";
      elements.backupRestoreConfirmButton.hidden = true;
      setMessage(
        elements.backupRestoreMessage,
        result.restart_required
          ? "Restauração concluída. Reinicie o Sistema Financeiro antes de continuar usando o app."
          : "Restauração concluída.",
        "success",
      );
    } catch (error) {
      setMessage(elements.backupRestoreMessage, error.message, "error");
    }
  }

  async function handleClearLaunchesSubmit(event) {
    event.preventDefault();
    setMessage(elements.clearLaunchesMessage, "");
    const data = formData(elements.clearLaunchesForm);
    if (data.confirm_clear !== "yes") {
      setMessage(elements.clearLaunchesMessage, "Confirme que entende a exclusao dos lancamentos.", "error");
      return;
    }
    try {
      await api("/api/me/clear-launches", { method: "POST", body: { current_password: data.current_password } });
      elements.clearLaunchesForm.reset();
      state.selectedAccountId = "";
      state.transactions = [];
      state.cardTransactions = [];
      state.cardPayments = [];
      state.cardInvoiceTransactions = [];
      state.cardInvoicePayments = [];
      state.portfolio = null;
      await loadAll();
      setMessage(elements.clearLaunchesMessage, "Lançamentos apagados. Categorias, subcategorias e tags foram preservadas.", "success");
    } catch (error) {
      setMessage(elements.clearLaunchesMessage, error.message, "error");
    }
  }

  async function handleDeleteUserSubmit(event) {
    event.preventDefault();
    setMessage(elements.deleteUserMessage, "");
    const data = formData(elements.deleteUserForm);
    if (data.confirm_delete !== "yes") {
      setMessage(elements.deleteUserMessage, "Confirme que entende a exclusao permanente dos dados.", "error");
      return;
    }
    try {
      await api("/api/me", { method: "DELETE", body: { current_password: data.current_password } });
      resetSessionState();
      elements.deleteUserForm.reset();
      onShowAuth();
    } catch (error) {
      setMessage(elements.deleteUserMessage, error.message, "error");
    }
  }

  elements.emailForm.addEventListener("submit", handleEmailSubmit);
  elements.passwordForm.addEventListener("submit", handlePasswordSubmit);
  if (elements.emailConfigForm) {
    elements.emailConfigForm.addEventListener("submit", handleEmailConfigSubmit);
    elements.emailConfigProvider.addEventListener("change", () => renderEmailConfigHelp());
  }
  if (elements.aiConfigForm) {
    elements.aiConfigForm.addEventListener("submit", handleAIConfigSubmit);
    elements.aiConfigProvider.addEventListener("change", () => {
      applyAIPreset();
      renderAIConfigFields();
    });
    if (elements.aiConfigAuthType) {
      elements.aiConfigAuthType.addEventListener("change", renderAIConfigFields);
    }
  }
  if (elements.consultorConfigForm) {
    elements.consultorConfigForm.addEventListener("submit", handleConsultorConfigSubmit);
  }
  if (elements.consultorProfileForm) {
    elements.consultorProfileForm.addEventListener("submit", handleConsultorProfileSubmit);
    elements.consultorProfileDependents?.addEventListener("change", renderConsultorProfileFields);
    elements.consultorProfileDeleteButton?.addEventListener("click", handleConsultorProfileDelete);
  }
  if (elements.themePreference) {
    elements.themePreference.addEventListener("click", handleThemePreferenceClick);
    syncThemePreference();
  }
  if (elements.densityPreference) {
    elements.densityPreference.addEventListener("click", handleDensityPreferenceClick);
    syncDensityPreference();
  }
  if (elements.userPrefTabs) {
    bindRovingTablist(elements.userPrefTabs.querySelectorAll(".user-pref-tab"), {
      valueFor: (button) => button.dataset.userTab,
      onSelect: switchUserTab,
    });
  }
  if (elements.maisRetornoConfigForm) {
    elements.maisRetornoConfigForm.addEventListener("submit", handleMaisRetornoConfigSubmit);
  }
  elements.backupSettingsForm?.addEventListener("submit", handleBackupSettingsSubmit);
  elements.backupRunForm?.addEventListener("submit", handleBackupRunSubmit);
  elements.backupRestoreForm?.addEventListener("submit", handleBackupRestoreValidate);
  elements.backupRestoreConfirmButton?.addEventListener("click", handleBackupRestoreConfirm);
  elements.clearLaunchesForm.addEventListener("submit", handleClearLaunchesSubmit);
  elements.deleteUserForm.addEventListener("submit", handleDeleteUserSubmit);

  return {
    loadPreferences,
    markPreferencesDirty: preferencesLoadPolicy.markDirty,
    resetPreferencesCache: preferencesLoadPolicy.reset,
    loadEmailConfigStatus,
    loadAIConfigStatus,
    loadConsultorConfigStatus,
    loadConsultorProfile,
    loadMaisRetornoConfigStatus,
    loadBackupSettings,
    syncThemePreference,
    syncDensityPreference,
  };
}
