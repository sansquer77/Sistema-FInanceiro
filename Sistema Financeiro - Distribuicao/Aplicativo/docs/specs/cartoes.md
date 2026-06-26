# Spec: Cartões de Crédito

## Status

**Implementado**

## Problema

O usuário precisa controlar gastos de cartão, limites, faturas e vencimentos sem misturar compras de cartão com o saldo imediato de sua conta-corrente.

## Jornada

1. O usuário cria um cartão manual, definindo limite, dia de fechamento, dia de vencimento, emissor, bandeira, moeda e opcionalmente a conta preferencial de pagamento.
2. Registra despesas e receitas no cartão de crédito, que são associadas a uma fatura mensal (`AAAA-MM`).
3. Acompanha a fatura em aberto com os lançamentos e saldo consolidado.
4. Realiza a conciliação (`reconciled_at`) de transações na fatura.
5. Move lançamentos entre fatura anterior/próxima quando houver ajuste de competência aceito pela fatura.
6. Paga a fatura do cartão utilizando uma das contas-correntes do sistema com a mesma moeda, gerando um lançamento automático de despesa na conta-corrente correspondente.

## Regras

- Gasto em cartão pertence obrigatoriamente a uma fatura mensal (`AAAA-MM`).
- Ao cadastrar ou editar uma compra, a fatura é calculada pela data do lançamento e pelo dia de fechamento do cartão. Compras após o fechamento entram na fatura posterior.
- Uma fatura pode ser paga, o que cria um lançamento de despesa na conta de pagamento escolhida com a mesma moeda.
- Não é permitido adicionar ou editar lançamentos em faturas já pagas (fechadas).
- É possível mover uma transação para a fatura anterior ou posterior desde que a fatura de destino não esteja paga.
- O sistema deve alertar/bloquear lançamento com data anterior ou igual ao fechamento de uma fatura anterior já paga.
- Moedas do cartão e da conta de pagamento da fatura devem ser idênticas.
- A conta preferencial de pagamento do cartão, quando informada, deve ter a mesma moeda do cartão e deve ser usada como padrão no pagamento da fatura.
- Lançamentos de cartão podem ser únicos, parcelados ou recorrentes. Parcelas exibem índice e total (`1/12`, `2/12` etc.).
- A fatura exibe total atual, total conciliado e contador de lançamentos não conciliados.
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
  - `PUT /api/credit-card-transactions/{id}/invoice`
  - `PUT /api/credit-card-transactions/{id}/reconciliation`
  - `GET /api/credit-card-payments`
  - `POST /api/credit-card-invoice/pay`
- Tabelas: `credit_cards`, `credit_card_transactions`, `credit_card_payments`, `credit_card_transaction_tags`.

## Critérios de aceite

- O usuário cadastra cartão com nome, limite, fechamento e vencimento.
- Uma despesa no cartão aparece na fatura correta.
- O total da fatura soma seus lançamentos.
- A fatura conciliada soma apenas lançamentos conferidos contra a fatura oficial.
- O pagamento altera o saldo da conta escolhida e fecha a fatura correspondente.
- A conciliação de uma transação de fatura persiste o status de verificado.
- Compras recorrentes de cartão entram no Cockpit e nos relatórios pela fatura de competência.
