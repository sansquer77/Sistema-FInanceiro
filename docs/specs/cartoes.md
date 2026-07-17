---
tipo: spec
area: cartoes
status: implementado
versao: 1.3
atualizado: 2026-07-17
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
> **implementado** · área: `cartoes` · atualizado em 2026-07-17 · relacionados: [[contas-correntes]], [[lancamentos]], [[limites-gastos]], [[relatorios]]

## Problema

O usuário precisa controlar gastos de cartão, limites, faturas e vencimentos sem misturar compras de cartão com o saldo imediato de sua conta-corrente.

## Usuário

Qualquer usuário autenticado localmente que utilize cartões de crédito para despesas pessoais.

## Jornada

1. O usuário cria um cartão manual com limite, dia de fechamento, dia de vencimento, emissor, bandeira, moeda e conta preferencial de pagamento.
2. Registra despesas e receitas no cartão, associadas a uma fatura mensal (`AAAA-MM`).
3. Acompanha a fatura em aberto com lançamentos e saldo consolidado.
4. Realiza a conciliação (`reconciled_at`) de transações contra a fatura oficial.
5. Filtra a lista da fatura por todos, não conciliados ou conciliados, e busca lançamentos por texto.
6. Move lançamentos entre faturas anterior/próxima quando necessário.
7. Paga a fatura escolhendo uma conta-corrente de mesma moeda; o sistema gera automaticamente uma despesa na conta de pagamento.

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
- Quando a fatura calculada pela data já estiver paga/fechada, o lançamento deve ser registrado automaticamente na próxima fatura aberta.
- Não é permitido adicionar ou editar lançamentos diretamente em faturas já pagas (fechadas); nesses casos o sistema deve avançar a competência para a próxima fatura aberta quando a operação vier de um lançamento por data.
- É possível mover uma transação para a fatura anterior ou posterior desde que a fatura de destino não esteja paga.
- O sistema não deve perder silenciosamente lançamentos de cartão quando a competência original estiver fechada.
- Moedas do cartão e da conta de pagamento da fatura devem ser idênticas.
- A conta preferencial de pagamento, quando informada, deve ter a mesma moeda do cartão.
- Lançamentos de cartão podem ser únicos, parcelados ou recorrentes.
- O formulário manual de lançamento no cartão deve oferecer o campo `Tag`, com as mesmas sugestões de tags usadas em lançamentos de contas e suporte a múltiplas tags separadas por vírgula.
- Em lançamentos parcelados de cartão, o valor informado é o total da compra e deve ser dividido pela quantidade de parcelas. Ex.: R$ 500 em 5x gera 5 lançamentos/faturas de R$ 100.
- Em lançamentos recorrentes de cartão, cada ocorrência deve manter exatamente o valor informado. Ex.: R$ 500 recorrente por 5 ocorrências gera 5 lançamentos de R$ 500.
- A fatura exibe total atual, total conciliado e contador de lançamentos não conciliados.
- A lista de lançamentos da fatura permite busca por descrição, categoria, subcategoria, tag, observação, data, tipo ou valor.
- O filtro de conciliação da fatura alterna entre todos, não conciliados e conciliados sem alterar os totais da fatura.
- Cartões arquivados não podem receber novos lançamentos, mas podem ser restaurados.
- Lançamentos de cartão entram em relatórios e limites pela competência da fatura (`invoice_month`), não pela data da compra. Ver [[relatorios]], [[limites-gastos]].
- Faturas não pagas com lançamentos conciliados devem entrar como abatimento no saldo previsto da conta preferencial de pagamento, no mês de vencimento da fatura.
- Faturas já pagas não devem ser abatidas novamente no saldo previsto da conta preferencial.

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
- Dado uma compra com data antes do fechamento de uma fatura já paga, quando registrada, então ela aparece na próxima fatura aberta.
- Dado uma fatura em aberto, quando consultada, o total soma seus lançamentos.
- Dado uma fatura paga, quando o usuário registra um lançamento cuja data cairia nela, então o sistema preserva o lançamento e ajusta a competência para a próxima fatura aberta.
- Dado um lançamento conciliado, quando exibido, o status de verificado persiste.
- Dado uma fatura com lançamentos, quando o usuário busca por texto, a lista exibe apenas os lançamentos correspondentes sem alterar o total da fatura.
- Dado uma fatura com lançamentos conciliados e não conciliados, quando o usuário troca o filtro de conciliação, a lista exibe apenas o status escolhido.
- Dado um lançamento de cartão criado ou editado com tags, quando a fatura é exibida, então as tags aparecem no lançamento e podem ser usadas na busca.
- Dado o pagamento de uma fatura, quando executado, o saldo da conta escolhida é reduzido pelo valor da fatura e a fatura é marcada como paga.
- Dado lançamentos recorrentes de cartão, quando listados no Cockpit, aparecem pela competência da fatura.
- Dado uma fatura conciliada e não paga com conta preferencial configurada, quando a conta exibe saldo previsto, então a fatura é considerada pelo vencimento sem duplicar faturas já pagas.

## Changelog

- `1.3` — 2026-07-17 — Lançamentos com competência calculada em fatura paga passam automaticamente para a próxima fatura aberta.
- `1.2` — 2026-07-05 — Faturas conciliadas e não pagas passam a impactar o saldo previsto da conta preferencial no mês de vencimento.
- `1.1` — 2026-06-30 — Busca textual e filtro de conciliação na lista da fatura.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[contas-correntes]]
- [[lancamentos]]
- [[limites-gastos]]
- [[relatorios]]
- [[importacao-organizze]]
- [[arquitetura]]
