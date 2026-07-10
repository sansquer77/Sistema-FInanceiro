export function isInvestmentTransfer(transaction) {
  return transaction.type === "transfer" && transaction.destination_account_type === "investment";
}

export function isInvestmentTransaction(transaction) {
  return transaction.type === "investment" || isInvestmentTransfer(transaction);
}

export function isExchangeTransfer(transaction) {
  return transaction.type === "transfer"
    && transaction.destination_account_id
    && transaction.destination_account_currency
    && transaction.account_currency !== transaction.destination_account_currency;
}

export function isInstallmentTransaction(transaction) {
  return Boolean(transaction && (
    transaction.series_kind === "installment" ||
    (Number(transaction.installment_index) > 0 && Number(transaction.installment_count) > 0)
  ));
}
