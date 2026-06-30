---
tipo: spec
area: cartoes
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[contas-correntes]]"
  - "[[lancamentos]]"
  - "[[limites-gastos]]"
  - "[[relatorios]]"
  - "[[importacao-organizze]]"
  - "[[arquitetura]]"
tags: [spec, "area/cartoes"]
aliases: ["Cartões de Crédito", "Faturas"]
---

# Cartões de Crédito

> [!info] Status
> **implementado** · área: `cartoes` · atualizado em 2026-06-29 · relacionados: [[contas-correntes]], [[lancamentos]], [[limites-gastos]], [[relatorios]]

## Problema

O usuário precisa controlar gastos de cartão, limites, faturas e vencimentos sem misturar compras de cartão com o saldo imediato de sua conta-corrente.

## Usuário

Qualquer usuário autenticado localmente que utilize cartões de crédito para despesas pessoais.

## Jornada

1. O usuário cria um cartão manual com limite, dia de fechamento, dia de vencimento, emissor, bandeira, moeda e conta preferencial de pagamento.
2. Registra despesas e receitas no cartão, associadas a uma fatura mensal (`AAAA-MM`).
3. Acompanha a fatura em aberto com lançamentos e saldo consolidado.
4. Realiza a conciliação (`reconciled_at`) de transações contra a fatura oficial.
5. Move lançamentos entre faturas anterior/próxima quando necessário.
6. Paga a fatura escolhendo uma conta-corrente de mesma moeda; o sistema gera automaticamente uma despesa na conta de pagamento.

## Dados

**Cartão:**

| Campo | Tipo | Regra |
|---|---|---|
| `nome` | texto | Obrigatório. |
| `limite` | inteiro (centavos) | Obrigatório. |
| `dia_fechamento` | inteiro (1-31) | Obrigatório. |
| `dia_vencimento` | inteiro (1-31) | Obrigatório. |
| `emissor` | texto | Opcional. |
| `bandeira` | texto | Opcional. |
| `moeda` | enum | Obrigatório. `BRL`, `USD`, `EUR` ou `GBP`. |
| `conta_preferencial_id` | FK | Opcional. Deve ter a mesma moeda do cartão. |

**Lançamento de cartão:**

| Campo | Tipo | Regra |
|---|---|---|
| `invoice_month` | `AAAA-MM` | Obrigatório. Calculado pela data e dia de fechamento. |
| `valor` | inteiro (centavos) | Obrigatório. |
| `data` | ISO `YYYY-MM-DD` | Obrigatório. |
| `descricao` | texto | Obrigatório. |
| `categoria_id` | FK | Obrigatório para despesas e receitas. |
| `subcategoria_id` | FK | Opcional. |
| `tags` | lista de FK | Opcional. N:M via `credit_card_transaction_tags`. |
| `parcelas` | inteiro | Opcional. Exibe `1/12`, `2/12` etc. |
| `reconciled_at` | timestamp | Opcional. Marcado na conciliação. |

## Regras

- Gasto em cartão pertence obrigatoriamente a uma fatura mensal (`AAAA-MM`).
- A fatura é calculada pela data do lançamento e pelo dia de fechamento do cartão. Compras após o fechamento entram na fatura posterior.
- Não é permitido adicionar ou editar lançamentos em faturas já pagas (fechadas).
- É possível mover uma transação para a fatura anterior ou posterior desde que a fatura de destino não esteja paga.
- O sistema deve alertar/bloquear lançamento com data anterior ou igual ao fechamento de uma fatura anterior já paga.
- Moedas do cartão e da conta de pagamento da fatura devem ser idênticas.
- A conta preferencial de pagamento, quando informada, deve ter a mesma moeda do cartão.
- Lançamentos de cartão podem ser únicos, parcelados ou recorrentes.
- A fatura exibe total atual, total conciliado e contador de lançamentos não conciliados.
- Cartões arquivados não podem receber novos lançamentos, mas podem ser restaurados.
- Lançamentos de cartão entram em relatórios e limites pela competência da fatura (`invoice_month`), não pela data da compra. Ver [[relatorios]], [[limites-gastos]].

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/credit-cards` |
| `GET` | `/api/credit-cards?status=archived` |
| `POST` | `/api/credit-cards` |
| `PUT` | `/api/credit-cards/{id}` |
| `DELETE` | `/api/credit-cards/{id}` |
| `POST` | `/api/credit-cards/{id}/restore` |
| `GET` | `/api/credit-card-invoice` |
| `GET` | `/api/credit-card-transactions` |
| `POST` | `/api/credit-card-transactions` |
| `PUT` | `/api/credit-card-transactions/{id}` |
| `DELETE` | `/api/credit-card-transactions/{id}` |
| `PUT` | `/api/credit-card-transactions/{id}/invoice` |
| `PUT` | `/api/credit-card-transactions/{id}/reconciliation` |
| `GET` | `/api/credit-card-payments` |
| `POST` | `/api/credit-card-invoice/pay` |

Tabelas: `credit_cards`, `credit_card_transactions`, `credit_card_payments`, `credit_card_transaction_tags`.

## Critérios de aceite

- Dado um cartão cadastrado, quando uma despesa é registrada, ela aparece na fatura correta calculada pelo dia de fechamento.
- Dado uma fatura em aberto, quando consultada, o total soma seus lançamentos.
- Dado uma fatura paga, quando o usuário tenta adicionar um lançamento a ela, a operação é bloqueada.
- Dado um lançamento conciliado, quando exibido, o status de verificado persiste.
- Dado o pagamento de uma fatura, quando executado, o saldo da conta escolhida é reduzido pelo valor da fatura e a fatura é marcada como paga.
- Dado lançamentos recorrentes de cartão, quando listados no Cockpit, aparecem pela competência da fatura.

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[contas-correntes]]
- [[lancamentos]]
- [[limites-gastos]]
- [[relatorios]]
- [[importacao-organizze]]
- [[arquitetura]]
