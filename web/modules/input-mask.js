// spec: frontend-fundacao-v2 v1.0 — critérios 5 e 6
// Adaptador de máscaras de entrada. IMask é acessado como global vendorizado;
// este módulo isola views dos detalhes da biblioteca e garante que o valor
// submetido permaneça compatível com os parsers existentes (formato brasileiro
// para moeda, ISO AAAA-MM-DD para datas textuais).

const INSTANCES = new WeakMap();

export function applyMoneyMask(input, options = {}) {
  if (!globalThis.IMask) {
    return null;
  }
  destroyMask(input);
  const mask = globalThis.IMask(input, {
    mask: Number,
    thousandsSeparator: ".",
    radix: ",",
    mapToRadix: ["."],
    scale: options.scale ?? 2,
    signed: options.signed ?? true,
    normalizeZeros: true,
    padFractionalZeros: true,
    autofix: true,
    lazy: false,
    placeholderChar: "0",
  });
  INSTANCES.set(input, mask);
  return mask;
}

export function applyDateMask(input, options = {}) {
  if (!globalThis.IMask) {
    return null;
  }
  destroyMask(input);
  const mask = globalThis.IMask(input, {
    mask: "00/00/0000",
    lazy: false,
    autofix: true,
  });
  INSTANCES.set(input, mask);
  return mask;
}

export function applyMasks(container = document) {
  if (!globalThis.IMask) {
    return;
  }
  container.querySelectorAll('input[data-mask="money"]').forEach((input) => {
    if (INSTANCES.has(input)) return;
    const scale = Number(input.dataset.maskScale ?? 2);
    const signed = input.dataset.maskSigned !== "false";
    applyMoneyMask(input, { scale, signed });
  });

  container.querySelectorAll('input[data-mask="date"]').forEach((input) => {
    if (INSTANCES.has(input)) return;
    applyDateMask(input);
  });
}

export function destroyMask(input) {
  const mask = INSTANCES.get(input);
  if (mask) {
    mask.destroy();
    INSTANCES.delete(input);
  }
}

export function destroyMasks(container = document) {
  container.querySelectorAll("input[data-mask]").forEach(destroyMask);
}

export function getMask(input) {
  return INSTANCES.get(input) || null;
}

export function rawValue(input) {
  const mask = INSTANCES.get(input);
  if (!mask) {
    return input.value;
  }
  return mask.unmaskedValue;
}

export function typedValue(input) {
  const mask = INSTANCES.get(input);
  if (!mask) {
    return input.value;
  }
  return mask.typedValue;
}

export function isMasked(input) {
  return INSTANCES.has(input);
}

function observeMutations() {
  if (!globalThis.MutationObserver || !globalThis.document) {
    return;
  }
  const observer = new MutationObserver((mutations) => {
    let shouldScan = false;
    for (const mutation of mutations) {
      if (mutation.type === "childList") {
        for (const node of mutation.addedNodes) {
          if (node.nodeType === Node.ELEMENT_NODE) {
            if (
              node.matches?.('input[data-mask]') ||
              node.querySelector?.('input[data-mask]')
            ) {
              shouldScan = true;
              break;
            }
          }
        }
      }
      if (shouldScan) break;
    }
    if (shouldScan) {
      applyMasks();
    }
  });
  observer.observe(document.body, { childList: true, subtree: true });
}

if (globalThis.document) {
  applyMasks();
  observeMutations();
}
