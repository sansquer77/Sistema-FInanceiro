/**
 * Catálogo compartilhado de logos de instituições financeiras e bandeiras de cartão.
 *
 * Resolve um nome informado pelo usuário (banco/emissor ou bandeira) para um
 * asset em /assets/banks ou /assets/bandeiras, aplicando normalização de texto
 * e aliases explícitos.
 *
 * spec: bank-logos v1.2
 */

const BANK_ASSET_BASE = "/assets/banks";
const NETWORK_ASSET_BASE = "/assets/bandeiras";

const REMOVE_TERMS = [
  "banco",
  "bank",
  "s.a.",
  "s.a",
  "s/a",
  "s / a",
  "sa",
  "holding",
  "cooperativa",
  "credito",
  "financiamento",
  "investimento",
  "investimentos",
];

export const BANK_LOGOS = [
  { file: "abc.svg", title: "ABC Brasil", aliases: ["abc", "abc brasil"] },
  { file: "ailos.svg", title: "Ailos", aliases: ["ailos"] },
  { file: "avenue.jpeg", title: "Avenue", aliases: ["avenue", "avenue securities"] },
  { file: "banco-da-amazonia.svg", title: "Banco da Amazônia", aliases: ["banco da amazonia", "banco da amazônia", "amazonia"] },
  { file: "banco-do-brasil.svg", title: "Banco do Brasil", aliases: ["banco do brasil", "bb"] },
  { file: "banco-pan.svg", title: "Banco Pan", aliases: ["banco pan", "pan"] },
  { file: "bank-of-america.svg", title: "Bank of America", aliases: ["bank of america", "boa"] },
  { file: "banrisul.svg", title: "Banrisul", aliases: ["banrisul", "banco do estado do rio grande do sul"] },
  { file: "binance.svg", title: "Binance", aliases: ["binance"] },
  { file: "bmg.svg", title: "BMG", aliases: ["bmg", "banco bmg"] },
  { file: "bmp.svg", title: "BMP", aliases: ["bmp"] },
  { file: "bnp.svg", title: "BNP Paribas", aliases: ["bnp", "bnp paribas"] },
  { file: "bradesco.svg", title: "Bradesco", aliases: ["bradesco", "banco bradesco"] },
  { file: "brb.svg", title: "BRB", aliases: ["brb", "banco de brasilia", "banco de brasília"] },
  { file: "bs2.svg", title: "BS2", aliases: ["bs2", "banco bs2"] },
  { file: "btg.svg", title: "BTG Pactual", aliases: ["btg", "btg pactual"] },
  { file: "bv.svg", title: "BV", aliases: ["bv", "banco votorantim"] },
  { file: "c6.svg", title: "C6 Bank", aliases: ["c6", "c6 bank"] },
  { file: "caixa-economica.svg", title: "Caixa Econômica Federal", aliases: ["caixa", "caixa economica", "caixa econômica", "cef", "caixa economica federal", "caixa econômica federal"] },
  { file: "coinbase.svg", title: "Coinbase", aliases: ["coinbase"] },
  { file: "daycoval.svg", title: "Daycoval", aliases: ["daycoval", "banco daycoval"] },
  { file: "dock.svg", title: "Dock", aliases: ["dock"] },
  { file: "foxbit.svg", title: "Foxbit", aliases: ["foxbit"] },
  { file: "grafeno.svg", title: "Grafeno", aliases: ["grafeno", "banco grafeno"] },
  { file: "ifood-pago.svg", title: "iFood Pago", aliases: ["ifood pago", "ifood"] },
  { file: "infinite-pay.svg", title: "Infinite Pay", aliases: ["infinite pay", "infinitepay"] },
  { file: "inter.svg", title: "Banco Inter", aliases: ["inter", "banco inter", "inter medium"] },
  { file: "itau.png", title: "Itaú", aliases: ["itau", "itaú", "itau unibanco", "itaú unibanco"] },
  { file: "magalupay.svg", title: "MagaluPay", aliases: ["magalupay", "magalu pay", "magazine luiza pay"] },
  { file: "mercado-pago.svg", title: "Mercado Pago", aliases: ["mercado pago", "mercadopago"] },
  { file: "mercantil.svg", title: "Mercantil do Brasil", aliases: ["mercantil", "mercantil do brasil", "banco mercantil"] },
  { file: "neon.svg", title: "Neon", aliases: ["neon", "banco neon"] },
  { file: "nubank.svg", title: "Nubank", aliases: ["nubank", "nu", "nu bank"] },
  { file: "omie.svg", title: "Omie", aliases: ["omie"] },
  { file: "original.svg", title: "Banco Original", aliases: ["original", "banco original"] },
  { file: "pagbank.svg", title: "PagBank", aliases: ["pagbank", "pag bank", "pagseguro"] },
  { file: "paypal.svg", title: "PayPal", aliases: ["paypal", "pay pal"] },
  { file: "picpay.svg", title: "PicPay", aliases: ["picpay", "pic pay"] },
  { file: "porto-bank.svg", title: "Porto Bank", aliases: ["porto bank", "porto"] },
  { file: "recargapay-nome.svg", title: "RecargaPay", aliases: ["recargapay", "recarga pay"] },
  { file: "safra.svg", title: "Safra", aliases: ["safra", "banco safra"] },
  { file: "santander.svg", title: "Santander", aliases: ["santander", "banco santander"] },
  { file: "sicoob.svg", title: "Sicoob", aliases: ["sicoob", "sicoob unicentral"] },
  { file: "sicredi.svg", title: "Sicredi", aliases: ["sicredi"] },
  { file: "sofisa.svg", title: "Sofisa", aliases: ["sofisa", "banco sofisa"] },
  { file: "stone.svg", title: "Stone", aliases: ["stone", "banco stone"] },
  { file: "wise.png", title: "Wise", aliases: ["wise", "transferwise"] },
  { file: "xp.svg", title: "XP Investimentos", aliases: ["xp", "xp investimentos"] },
];

export const CARD_NETWORK_LOGOS = [
  { file: "american-express.svg", title: "American Express", aliases: ["american express", "amex", "americanexpress"] },
  { file: "apple-pay.svg", title: "Apple Pay", aliases: ["apple pay", "applepay"] },
  { file: "diners-club.svg", title: "Diners Club", aliases: ["diners club", "diners", "dinersclub"] },
  { file: "discover.svg", title: "Discover", aliases: ["discover"] },
  { file: "elo.svg", title: "Elo", aliases: ["elo"] },
  { file: "hipercard.svg", title: "Hipercard", aliases: ["hipercard"] },
  { file: "mastercard.svg", title: "Mastercard", aliases: ["mastercard", "master", "master card"] },
  { file: "visa.svg", title: "Visa", aliases: ["visa"] },
];

/**
 * Remove acentos e caracteres diacríticos, mantendo apenas ASCII.
 */
function removeAccents(value) {
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

/**
 * Normaliza um nome para comparação:
 * - caixa baixa;
 * - remove acentos;
 * - remove termos genéricos de instituição (Banco, Bank, S.A. etc.);
 * - remove pontuação e colapsa espaços.
 */
export function normalizeBankName(value) {
  if (!value) return "";
  let normalized = String(value).toLowerCase();
  normalized = removeAccents(normalized);
  for (const term of REMOVE_TERMS) {
    const pattern = term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    normalized = normalized.replace(new RegExp(`\\b${pattern}\\b`, "gi"), " ");
  }
  return normalized
    .replace(/[^a-z0-9]+/g, " ")
    .trim();
}

function aliasMatches(normalizedName, normalizedAlias) {
  if (normalizedName === normalizedAlias) return true;
  if (normalizedAlias.length > 2 && normalizedName.includes(normalizedAlias)) return true;
  return false;
}

function resolveLogo(name, catalog) {
  const normalized = normalizeBankName(name);
  if (!normalized) return null;

  for (const entry of catalog) {
    const normalizedAliases = entry.aliases.map(normalizeBankName).filter(Boolean);
    if (normalizedAliases.some((alias) => aliasMatches(normalized, alias))) {
      return { src: `${entry.base}/${entry.file}`, title: entry.title };
    }
  }
  return null;
}

/**
 * Resolve um nome para o logo de banco correspondente.
 * Retorna { src, title } ou null quando não houver match.
 */
export function resolveBankLogo(name) {
  const catalog = BANK_LOGOS.map((entry) => ({ ...entry, base: BANK_ASSET_BASE }));
  return resolveLogo(name, catalog);
}

/**
 * Resolve um nome para o logo de bandeira de cartão correspondente.
 * Retorna { src, title } ou null quando não houver match.
 */
export function resolveCardNetworkLogo(name) {
  const catalog = CARD_NETWORK_LOGOS.map((entry) => ({ ...entry, base: NETWORK_ASSET_BASE }));
  return resolveLogo(name, catalog);
}

function escapeBankLogoHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function imageLogoBadge({ src, title, type }) {
  const safeTitle = escapeBankLogoHtml(title);
  const safeSrc = escapeBankLogoHtml(src);
  const safeAlt = escapeBankLogoHtml(title);
  return `<div class="bank-logo-badge image-logo" title="${safeTitle}">
    <img src="${safeSrc}" alt="${safeAlt}" data-logo-fallback="${type}" title="${safeTitle}">
  </div>`;
}

function genericBankBadge(title) {
  const safeTitle = escapeBankLogoHtml(title);
  return `<div class="bank-logo-badge" style="background-color: var(--bank-logo-generic-surface);" title="${safeTitle}">
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="var(--bank-logo-generic-ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="10" width="20" height="11" rx="2"></rect>
      <path d="M6 6v4M10 6v4M14 6v4M18 6v4M2 6h20M12 2L2 6h20L12 2z"></path>
    </svg>
  </div>`;
}

function genericNetworkBadge(title) {
  const safeTitle = escapeBankLogoHtml(title);
  const initial = safeTitle.charAt(0).toUpperCase();
  return `<div class="bank-logo-badge card-network-badge" style="background-color: var(--bank-logo-generic-surface);" title="${safeTitle}">
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="var(--bank-logo-generic-ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="5" width="20" height="14" rx="2"></rect>
      <path d="M6 9h12M6 13h12"></path>
    </svg>
    ${initial ? `<span class="card-network-initial" aria-hidden="true">${initial}</span>` : ""}
  </div>`;
}

function walletBadge() {
  return `<div class="bank-logo-badge" style="background-color: var(--bank-logo-wallet-surface);" title="Carteira / Dinheiro">
    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="var(--bank-logo-generic-ink)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <rect x="2" y="4" width="20" height="16" rx="2" ry="2"></rect>
      <path d="M16 11h6v2h-6z"></path>
      <path d="M12 4v16"></path>
    </svg>
  </div>`;
}

/**
 * Retorna o HTML de um badge de logo de banco.
 *
 * Opções:
 * - `name`: nome da instituição financeira.
 * - `kind`: "bank" (padrão) ou "wallet".
 * - `fallbackTitle`: título usado no badge genérico quando não houver logo.
 */
export function renderBankLogo({ name, kind = "bank", fallbackTitle = "Banco / Outro" } = {}) {
  if (kind === "wallet") {
    return walletBadge();
  }

  const logo = resolveBankLogo(name);
  if (logo) {
    return imageLogoBadge({ src: logo.src, title: logo.title, type: "bank" });
  }

  return genericBankBadge(fallbackTitle);
}

/**
 * Retorna o HTML de um badge de logo de bandeira de cartão.
 *
 * Opções:
 * - `name`: nome da bandeira.
 * - `fallbackTitle`: título usado no badge genérico quando não houver logo.
 */
export function renderCardNetworkLogo({ name, fallbackTitle = "Bandeira" } = {}) {
  const logo = resolveCardNetworkLogo(name);
  if (logo) {
    return imageLogoBadge({ src: logo.src, title: logo.title, type: "network" });
  }

  return genericNetworkBadge(fallbackTitle);
}

/**
 * Anexa fallback visual em imagens de logo renderizadas por este módulo.
 * Deve ser chamada após inserir o HTML no DOM.
 */
export function attachBankLogoFallbacks(container) {
  if (!container) return;
  const images = container.querySelectorAll("img[data-logo-fallback]");
  images.forEach((img) => {
    if (img.complete && img.naturalWidth === 0) {
      replaceWithFallback(img);
      return;
    }
    img.addEventListener("error", () => replaceWithFallback(img), { once: true });
  });
}

function replaceWithFallback(img) {
  const wrapper = img.closest(".bank-logo-badge.image-logo");
  if (!wrapper) return;
  const type = img.getAttribute("data-logo-fallback");
  const title = img.getAttribute("title") || (type === "network" ? "Bandeira" : "Banco / Outro");
  const badge = type === "network" ? genericNetworkBadge(title) : genericBankBadge(title);
  wrapper.replaceWith(badge);
}
