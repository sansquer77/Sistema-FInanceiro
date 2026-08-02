export function registerUserAdminView(context) {
  const {
    api,
    elements,
    formData,
    loadAll,
    resetSessionState,
    setMessage,
    theme,
    state,
    onShowAuth,
  } = context;
  let emailConfigPresets = [];
  let aiConfigPresets = [];

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

  function renderAIConfigFields() {
    if (!elements.aiConfigCustomFields) {
      return;
    }
    elements.aiConfigCustomFields.hidden = !isAICustomProvider();
  }

  function applyAIPreset() {
    if (!elements.aiConfigProvider) {
      return;
    }
    const preset = aiConfigPresets.find((item) => item.provider === elements.aiConfigProvider.value);
    if (!preset) {
      return;
    }
    if (elements.aiConfigBaseUrl && !elements.aiConfigBaseUrl.value) {
      elements.aiConfigBaseUrl.value = preset.base_url || "";
    }
    if (elements.aiConfigAuthType && !elements.aiConfigAuthType.value) {
      elements.aiConfigAuthType.value = preset.auth_type || "bearer";
    }
  }

  async function loadAIConfigStatus() {
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
      setMessage(elements.aiConfigMessage, "Configuração de IA salva.", "success");
    } catch (error) {
      setMessage(elements.aiConfigMessage, error.message, "error");
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
      renderAIConfigFields();
      if (isAICustomProvider()) {
        applyAIPreset();
      }
    });
  }
  if (elements.themePreference) {
    elements.themePreference.addEventListener("click", handleThemePreferenceClick);
    syncThemePreference();
  }
  elements.clearLaunchesForm.addEventListener("submit", handleClearLaunchesSubmit);
  elements.deleteUserForm.addEventListener("submit", handleDeleteUserSubmit);

  return {
    loadEmailConfigStatus,
    loadAIConfigStatus,
    syncThemePreference,
  };
}
