let unauthorizedHandler = null;
let unauthorizedHandled = false;

export function configureApi({ onUnauthorized } = {}) {
  unauthorizedHandler = typeof onUnauthorized === "function" ? onUnauthorized : null;
  unauthorizedHandled = false;
}

export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      method: options.method || "GET",
      headers: options.body ? { "Content-Type": "application/json" } : {},
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
  } catch (error) {
    throw new Error(`Nao foi possivel falar com o servidor local. Abra pelo endereco ${window.location.origin}.`);
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    handleUnauthorized(response, path, options);
    throw new Error(payload.error || "Algo nao saiu como esperado.");
  }
  resetUnauthorizedStateOnAuthSuccess(path);
  return payload;
}

export async function upload(path, body) {
  let response;
  try {
    response = await fetch(path, {
      credentials: "same-origin",
      method: "POST",
      body,
    });
  } catch (error) {
    throw new Error(`Nao foi possivel falar com o servidor local. Abra pelo endereco ${window.location.origin}.`);
  }
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    handleUnauthorized(response, path, {});
    throw new Error(payload.error || "Algo nao saiu como esperado.");
  }
  return payload;
}

function handleUnauthorized(response, path, options) {
  if (
    response.status !== 401
    || options.skipUnauthorizedHandler
    || isPublicAuthPath(path)
    || !unauthorizedHandler
    || unauthorizedHandled
  ) {
    return;
  }
  unauthorizedHandled = true;
  unauthorizedHandler();
}

function isPublicAuthPath(path) {
  const publicPaths = new Set([
    "/api/login",
    "/api/register",
    "/api/password-reset/request",
    "/api/password-reset/confirm",
    "/api/me",
  ]);
  return publicPaths.has(String(path).split("?")[0]);
}

function resetUnauthorizedStateOnAuthSuccess(path) {
  const pathname = String(path).split("?")[0];
  if (pathname === "/api/login" || pathname === "/api/register" || pathname === "/api/me") {
    unauthorizedHandled = false;
  }
}
