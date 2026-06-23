# Spec: Cartões de Crédito

## Status

**Implementado**

## Problema

O usuário precisa controlar gastos de cartão, limites, faturas e vencimentos sem misturar compras de cartão com o saldo imediato de sua conta-corrente.

## Jornada

1. O usuário cria um cartão manual, definindo limite, dia de fechamento, dia de vencimento, emissor, bandeira e moeda.
2. Registra despesas e receitas no cartão de crédito, que são associadas a uma fatura mensal (`AAAA-MM`).
3. Acompanha a fatura em aberto com os lançamentos e saldo consolidado.
4. Realiza a conciliação (`reconciled_at`) de transações na fatura.
5. Paga a fatura do cartão utilizando uma das contas-correntes do sistema com a mesma moeda, gerando um lançamento automático de despesa na conta-corrente correspondente.

## Regras

- Gasto em cartão pertence obrigatoriamente a uma fatura mensal (`AAAA-MM`).
- Uma fatura pode ser paga, o que cria um lançamento de despesa na conta de pagamento escolhida com a mesma moeda.
- Não é permitido adicionar ou editar lançamentos em faturas já pagas (fechadas).
- Não é possível mover transações entre cartões diferentes ou faturas diferentes.
- Moedas do cartão e da conta de pagamento da fatura devem ser idênticas.
- Cartões arquivados não podem receber novos lançamentos, mas podem ser restaurados.

## API e Dados

- Rotas:
  - `GET /api/credit-cards` e `GET /api/credit-cards?status=archived`
  - `POST /api/credit-cards`
  - `PUT /api/credit-cards/{id}`
  - `DELETE /api/credit-cards/{id}` (arquivamento)
  - `POST /api/credit-cards/{id}/restore`
  - `GET /api/credit-card-invoice` (detalhes da fatura por mês)
  - `GET /api/credit-card-transactions`
  - `POST /api/credit-card-transactions`
  - `PUT /api/credit-card-transactions/{id}`
  - `DELETE /api/credit-card-transactions/{id}`
  - `PUT /api/credit-card-transactions/{id}/reconciliation`
  - `GET /api/credit-card-payments`
  - `POST /api/credit-card-invoice/pay`
- Tabelas: `credit_cards`, `credit_card_transactions`, `credit_card_payments`, `credit_card_transaction_tags`.

## Critérios de aceite

- O usuário cadastra cartão com nome, limite, fechamento e vencimento.
- Uma despesa no cartão aparece na fatura correta.
- O total da fatura soma seus lançamentos.
- O pagamento altera o saldo da conta escolhida e fecha a fatura correspondente.
- A conciliação de uma transação de fatura persiste o status de verificado.
