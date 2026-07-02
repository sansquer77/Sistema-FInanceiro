import { isInstallmentTransaction } from "./transaction-kind.js";

export function transactionTypeLabel(type) {
  return {
    income: "Receita",
    expense: "Despesa",
    transfer: "Transferência",
    investment: "Investimento",
  }[type] || type;
}

export function cardTransactionTypeLabel(type) {
  return {
    income: "Receita",
    expense: "Despesa",
  }[type] || type;
}

export function accountTypeLabel(type) {
  return {
    liquidity: "Liquidez",
    wallet: "Carteira",
    investment: "Investimento",
  }[type] || "Liquidez";
}

export function classificationGroupLabel(type) {
  return {
    income: "Receitas",
    expense: "Despesas",
    investment: "Investimentos",
  }[type] || "Despesas";
}

export function formatCategoryPath(transaction) {
  if (!transaction.category_name) {
    return "Sem categoria";
  }
  if (!transaction.subcategory_name) {
    return transaction.category_name;
  }
  return `${transaction.category_name} / ${transaction.subcategory_name}`;
}

export function cardCategoryPath(transaction) {
  if (!transaction.category_name) {
    return "Sem categoria";
  }
  if (!transaction.subcategory_name) {
    return transaction.category_name;
  }
  return `${transaction.category_name} / ${transaction.subcategory_name}`;
}

export function recurrenceFrequencyLabel(frequency) {
  return {
    weekly: "Semanal",
    monthly: "Mensal",
    quarterly: "Trimestral",
    semiannual: "Semestral",
    annual: "Anual",
  }[frequency] || "Recorrente";
}

export function transactionSeriesLabel(transaction) {
  if (isInstallmentTransaction(transaction) && transaction.installment_index && transaction.installment_count) {
    return `Parcela ${transaction.installment_index}/${transaction.installment_count}`;
  }
  if (transaction.series_kind === "recurring") {
    return `Recorrente · ${recurrenceFrequencyLabel(transaction.recurrence_frequency)}`;
  }
  return "";
}
