---
tipo: spec
area: contas
status: implementado
versao: 1.6
atualizado: 2026-09-04
relacionados:
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[investimentos-portfolio]]"
  - "[[arquitetura]]"
tags: [spec, "area/contas"]
aliases: ["Contas-correntes", "Contas"]
---

# Contas-correntes

> [!info] Status
> **implementado** · área: `contas` · atualizado em 2026-08-07 · relacionados: [[lancamentos]], [[cartoes]], [[investimentos-portfolio]]

## Problema

O usuário precisa cadastrar contas bancárias manuais e consultar saldos por moeda sem confusão visual entre naturezas distintas de conta.

## Usuário

Qualquer usuário autenticado localmente que mantenha contas em um ou mais bancos, em uma ou mais moedas.

## Jornada

1. Usuário entra no app e acessa a área de Contas.
2. Cadastra uma conta com banco, agência, número, moeda e saldo inicial.
3. Visualiza a conta na lista principal.
4. Confere os saldos agrupados por moeda.
5. Pode editar, arquivar ou restaurar a conta conforme necessário.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `nome` | texto | Obrigatório. Apelido da conta. |
| `banco` | texto | Obrigatório. Instituição financeira. |
| `agencia` | texto | Opcional. |
| `conta` | texto | Opcional. |
| `moeda` | enum | Obrigatório. `BRL`, `USD`, `EUR` ou `GBP`. |
| `natureza` | enum | Obrigatório. `liquidity` (liquidez), `wallet` (carteira física), `investment` (investimento). |
| `saldo_inicial` | inteiro (centavos) | Obrigatório. Valor base do saldo atual. |
| `observacoes` | texto | Opcional. |

## Regras

- Nome e banco são obrigatórios.
- O saldo é armazenado em centavos.
- Contas arquivadas não aparecem na lista principal.
- Contas arquivadas podem ser listadas (`?status=archived`) e restauradas.
- A moeda de uma conta com lançamentos ativos não pode ser alterada.
- Alterar o saldo inicial ajusta o saldo atual pela diferença.
- O ajuste de saldo atual por mudança de saldo inicial é aplicado dentro de uma transação imediata curta (reconciliação via soma dos lançamentos) que protege a leitura prévia e preserva escritas concorrentes.
- Contas do tipo `wallet` aceitam apenas receitas, despesas e transferências à vista; não exibem recorrência. Ver [[lancamentos]].
- Contas do tipo `investment` alimentam o portfólio de investimentos. Ver [[investimentos-portfolio]].
- O saldo previsto de uma conta usada como conta preferencial de pagamento de cartão deve abater despesas conciliadas de cartão em faturas não pagas, alocando o impacto no mês de vencimento da fatura.
- Quando o saldo previsto incluir despesas conciliadas de cartão, a interface deve indicar `Saldo previsto (inclui despesas conciliadas de cartão)`.
- O saldo atual é sempre calculado como `saldo inicial + soma dos deltas de lançamentos com data <= hoje`; lançamentos futuros não movem o saldo atual.
- O `current_balance_cents` armazenado é reconciliado a cada escrita de lançamento (criar, editar, excluir, cascata de série e importação), permanecendo igual ao saldo efetivo exibido na listagem — nunca há divergência persistente entre o valor armazenado e o calculado.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/checking-accounts` |
| `GET` | `/api/checking-accounts?status=archived` |
| `POST` | `/api/checking-accounts` |
| `PUT` | `/api/checking-accounts/{id}` |
| `DELETE` | `/api/checking-accounts/{id}` |
| `POST` | `/api/checking-accounts/{id}/restore` |

Tabela: `checking_accounts`.

## Critérios de aceite

- Dado uma conta BRL cadastrada, quando listada, ela aparece na lista principal e no agrupamento de saldos por moeda.
- Dado contas em moedas diferentes, quando listadas, cada moeda aparece uma vez no bloco de saldos.
- Dado uma conta arquivada, quando consultada, ela não aparece na lista principal, mas aparece em `?status=archived`.
- Dado uma conta restaurada, quando listada, ela volta para a lista principal com o saldo correto.
- Dado uma conta com lançamentos ativos, quando o usuário tenta alterar a moeda, a operação é bloqueada.
- Dado uma conta preferencial de pagamento com fatura conciliada e não paga, quando o saldo previsto ou gráfico de meses futuros é exibido, então o valor conciliado da fatura é abatido no mês de vencimento.
- Dado uma conta com lançamentos futuros, quando listada, o saldo armazenado reflete apenas lançamentos com data até hoje e é igual ao saldo efetivo (criar/editar/excluir um lançamento futuro não altera o saldo na data de hoje).

## Changelog

- `1.6` — 2026-09-04 — Área do gráfico passou a ser uma camada contínua sob as duas séries, sem quebra visual na transição para o saldo previsto.
- `1.5` — 2026-09-04 — Corrigido o renderer de listas para preservar elementos DOM e ajustado o gráfico de saldo para uma única paleta azul com degradê invertido.
- `1.4` — 2026-09-04 — Histórico de saldos usa preenchimento degradê horizontal sob as linhas do ApexCharts para reforçar a leitura visual da série.

- `1.3` — 2026-08-07 — Saldo atual passa a ser sempre efetivo (lançamentos com data > hoje não movem o saldo); `current_balance_cents` armazenado é reconciliado após criar, editar, excluir, cascata de série, importação, resgate/encerramento de investimentos e ajuste de saldo inicial.
- `1.2` — 2026-07-05 — Saldo previsto passa a considerar faturas conciliadas e não pagas de cartões vinculados como conta preferencial, pelo mês de vencimento.
- `1.1` — 2026-07-03 — Regra de ajuste de saldo inicial explicita delta atômico para uso concorrente leve.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[lancamentos]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[arquitetura]]
