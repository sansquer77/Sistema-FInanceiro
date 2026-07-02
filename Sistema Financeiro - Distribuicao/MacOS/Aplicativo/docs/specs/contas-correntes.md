---
tipo: spec
area: contas
status: implementado
versao: 1.0
atualizado: 2026-06-29
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
> **implementado** · área: `contas` · atualizado em 2026-06-29 · relacionados: [[lancamentos]], [[cartoes]], [[investimentos-portfolio]]

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
- Contas do tipo `wallet` aceitam apenas receitas, despesas e transferências à vista; não exibem recorrência. Ver [[lancamentos]].
- Contas do tipo `investment` alimentam o portfólio de investimentos. Ver [[investimentos-portfolio]].

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

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[lancamentos]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[arquitetura]]
