export function registerAuthView(context) {
  const {
    api,
    elements,
    formData,
    resetSessionState,
    setFormBusy,
    setMessage,
    state,
    onAuthenticated,
    onShowAuth,
  } = context;

  function switchAuthMode(mode) {
    const isLogin = mode === "login";
    const isRegister = mode === "register";
    const isResetRequest = mode === "reset-request";
    const isResetConfirm = mode === "reset-confirm";
    elements.loginTab.classList.toggle("active", isLogin);
    elements.registerTab.classList.toggle("active", isRegister);
    elements.loginForm.hidden = !isLogin;
    elements.registerForm.hidden = !isRegister;
    elements.passwordResetRequestForm.hidden = !isResetRequest;
    elements.passwordResetConfirmForm.hidden = !isResetConfirm;
    setMessage(elements.authMessage, "");
  }

  async function handleLogin(event) {
    event.preventDefault();
    setMessage(elements.authMessage, "");
    const data = formData(elements.loginForm);
    setFormBusy(elements.loginForm, true);
    try {
      const response = await api("/api/login", { method: "POST", body: data });
      state.user = response.user;
      await onAuthenticated();
    } catch (error) {
      setMessage(elements.authMessage, error.message, "error");
    } finally {
      setFormBusy(elements.loginForm, false);
    }
  }

  async function handleRegister(event) {
    event.preventDefault();
    setMessage(elements.authMessage, "");
    const data = formData(elements.registerForm);
    setFormBusy(elements.registerForm, true);
    try {
      const response = await api("/api/register", { method: "POST", body: data });
      state.user = response.user;
      await onAuthenticated();
    } catch (error) {
      setMessage(elements.authMessage, error.message, "error");
    } finally {
      setFormBusy(elements.registerForm, false);
    }
  }

  async function handlePasswordResetRequest(event) {
    event.preventDefault();
    setMessage(elements.authMessage, "");
    const data = formData(elements.passwordResetRequestForm);
    setFormBusy(elements.passwordResetRequestForm, true);
    try {
      const response = await api("/api/password-reset/request", {
        method: "POST",
        body: data,
      });
      elements.passwordResetConfirmForm.elements.token.value = "";
      switchAuthMode("reset-confirm");
      const message = `Se o email existir, o codigo de recuperacao sera enviado. Ele expira em ${response.expires_in_minutes} minutos.`;
      setMessage(elements.authMessage, message, "success");
    } catch (error) {
      setMessage(elements.authMessage, error.message, "error");
    } finally {
      setFormBusy(elements.passwordResetRequestForm, false);
    }
  }

  async function handlePasswordResetConfirm(event) {
    event.preventDefault();
    setMessage(elements.authMessage, "");
    const data = formData(elements.passwordResetConfirmForm);
    setFormBusy(elements.passwordResetConfirmForm, true);
    try {
      await api("/api/password-reset/confirm", {
        method: "POST",
        body: data,
      });
      elements.passwordResetRequestForm.reset();
      elements.passwordResetConfirmForm.reset();
      switchAuthMode("login");
      setMessage(elements.authMessage, "Senha redefinida. Entre com a nova senha.", "success");
    } catch (error) {
      setMessage(elements.authMessage, error.message, "error");
    } finally {
      setFormBusy(elements.passwordResetConfirmForm, false);
    }
  }

  async function handleLogout() {
    await api("/api/logout", { method: "POST" });
    resetSessionState();
    elements.loginForm.reset();
    elements.registerForm.reset();
    onShowAuth();
  }

  elements.loginTab.addEventListener("click", () => switchAuthMode("login"));
  elements.registerTab.addEventListener("click", () => switchAuthMode("register"));
  elements.loginForm.addEventListener("submit", handleLogin);
  elements.registerForm.addEventListener("submit", handleRegister);
  elements.passwordResetRequestForm.addEventListener("submit", handlePasswordResetRequest);
  elements.passwordResetConfirmForm.addEventListener("submit", handlePasswordResetConfirm);
  elements.forgotPasswordButton.addEventListener("click", () => switchAuthMode("reset-request"));
  elements.backToLoginFromRequest.addEventListener("click", () => switchAuthMode("login"));
  elements.backToLoginFromConfirm.addEventListener("click", () => switchAuthMode("login"));
  elements.logoutButton.addEventListener("click", handleLogout);

  return { switchAuthMode };
}
