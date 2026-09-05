export function createTransactionForm({ state, elements, api }) {
  const {
    transactionForm, transactionType, transactionAccount, destinationAccount,
    destinationAmount, transferExchangeRate, exchangeRate, exchangeRateLabel,
    exchangeRateLabelText,
  } = elements;

  destinationAccount.addEventListener("change", updateTransferExchangeRateState);
  transactionForm.elements.date.addEventListener("change", updateExchangeRateState);
  transactionForm.elements.date.addEventListener("change", updateTransferExchangeRateState);
  transactionForm.elements.amount.addEventListener("input", updateDestinationAmountFromRate);
  transferExchangeRate.addEventListener("input", updateDestinationAmountFromRate);

  async function updateExchangeRateState() {
    exchangeRateLabel.hidden = true;
    exchangeRate.type = "hidden";
    exchangeRate.disabled = false;
    exchangeRate.placeholder = "";
    exchangeRate.value = "1,000000";
    const account = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    const dateValue = transactionForm.elements.date.value;
    if (transactionForm.elements.id.value || !account || account.currency === "BRL" || !dateValue) return;
    try {
      const preview = await exchangePreview(account.currency, "BRL", dateValue);
      exchangeRate.value = formatNumber(preview.rate, 6);
    } catch {
      exchangeRateLabelText.textContent = `Cotação (${account.currency} → BRL)`;
      exchangeRate.type = "text";
      exchangeRate.value = "";
      exchangeRate.placeholder = "Informe a cotação manualmente (ex.: 5,900000)";
      exchangeRateLabel.hidden = false;
    }
  }

  async function updateTransferExchangeRateState() {
    if (transactionType.value !== "exchange") return;
    const source = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    const destination = state.accounts.find((entry) => String(entry.id) === destinationAccount.value);
    if (!source || !destination || source.currency === destination.currency || !transactionForm.elements.date.value) return;
    transferExchangeRate.placeholder = "Buscando cotação...";
    try {
      const preview = await exchangePreview(source.currency, destination.currency, transactionForm.elements.date.value, transactionForm.elements.amount.value);
      transferExchangeRate.value = formatNumber(preview.rate, 6);
      setDestinationAmount(preview.destination_amount);
    } catch {
      transferExchangeRate.placeholder = "Informe a cotação manual";
    }
  }

  async function updateDestinationAmountFromRate() {
    if (transactionType.value !== "exchange" || !transactionForm.elements.amount.value || !transferExchangeRate.value) return;
    const source = state.accounts.find((entry) => String(entry.id) === transactionAccount.value);
    const destination = state.accounts.find((entry) => String(entry.id) === destinationAccount.value);
    if (!source || !destination) return;
    try {
      const preview = await exchangePreview(source.currency, destination.currency, transactionForm.elements.date.value, transactionForm.elements.amount.value, transferExchangeRate.value);
      setDestinationAmount(preview.destination_amount);
    } catch {
      // Entradas parciais permanecem editáveis enquanto o usuário digita.
    }
  }

  function setDestinationAmount(value) {
    destinationAmount.value = formatNumber(value, 2);
  }

  async function exchangePreview(sourceCurrency, targetCurrency, dateValue, amount = "", transferRate = "") {
    const params = new URLSearchParams({ currency: sourceCurrency, target_currency: targetCurrency, date: dateValue });
    if (amount) params.set("amount", amount);
    if (transferRate) params.set("transfer_rate", transferRate);
    return api(`/api/exchange-rate?${params.toString()}`);
  }

  function formatNumber(value, digits) {
    return Number(value || 0).toLocaleString("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits });
  }

  return { updateExchangeRateState, updateTransferExchangeRateState, updateDestinationAmountFromRate };
}
