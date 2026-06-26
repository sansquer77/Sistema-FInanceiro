export function registerUserAdminView(context) {
  const {
    api,
    elements,
    formData,
    loadAll,
    resetSessionState,
    setMessage,
    state,
    onShowAuth,
  } = context;
  let emailConfigPresets = [];

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
  elements.clearLaunchesForm.addEventListener("submit", handleClearLaunchesSubmit);
  elements.deleteUserForm.addEventListener("submit", handleDeleteUserSubmit);

  return {
    loadEmailConfigStatus,
  };
}
