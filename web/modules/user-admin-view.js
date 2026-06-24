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
  elements.clearLaunchesForm.addEventListener("submit", handleClearLaunchesSubmit);
  elements.deleteUserForm.addEventListener("submit", handleDeleteUserSubmit);
}
