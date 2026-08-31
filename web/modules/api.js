let unauthorizedHandler = null;
let unauthorizedHandled = false;
let mutationHandler = null;

export function configureApi({ onUnauthorized, onMutation } = {}) {
  unauthorizedHandler = typeof onUnauthorized === "function" ? onUnauthorized : null;
  mutationHandler = typeof onMutation === "function" ? onMutation : null;
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
  const payload = await parseResponsePayload(response);
  if (!response.ok) {
    handleUnauthorized(response, path, options);
    throw new Error(payload.error || `Erro ${response.status}: ${response.statusText || "falha na requisicao"}.`);
  }
  resetUnauthorizedStateOnAuthSuccess(path);
  notifyMutation(path, options.method);
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
  const payload = await parseResponsePayload(response);
  if (!response.ok) {
    handleUnauthorized(response, path, {});
    throw new Error(payload.error || `Erro ${response.status}: ${response.statusText || "falha na requisicao"}.`);
  }
  notifyMutation(path, "POST");
  return payload;
}

function notifyMutation(path, method = "GET") {
  const normalizedMethod = String(method || "GET").toUpperCase();
  if (normalizedMethod !== "GET" && mutationHandler) mutationHandler(path, normalizedMethod);
}

const PAGE_SIZE = 2000;

export async function fetchAllListed(path, key, pageSize = PAGE_SIZE) {
  const items = [];
  let offset = 0;
  for (;;) {
    const separator = path.includes("?") ? "&" : "?";
    const payload = await api(`${path}${separator}limit=${pageSize}&offset=${offset}`);
    const batch = payload[key] || [];
    items.push(...batch);
    if (!payload.has_more || batch.length < pageSize) {
      break;
    }
    offset += pageSize;
  }
  return items;
}

async function parseResponsePayload(response) {
  const text = await response.text().catch(() => "");
  if (!text) {
    return {};
  }
  try {
    return JSON.parse(text);
  } catch (error) {
    return { error: text.trim() };
  }
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
