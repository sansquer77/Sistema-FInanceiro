# Contas-correntes

## Objetivo

Permitir que o usuario cadastre contas bancarias manuais e consulte saldos sem confusao visual.

## Estado

Implementado.

## Jornada

1. Usuario entra no app.
2. Acessa a area de contas-correntes.
3. Cadastra uma conta com banco, agencia, numero, moeda e saldo inicial.
4. Visualiza a conta na lista.
5. Confere os saldos agrupados por moeda.
6. Pode editar, arquivar ou restaurar a conta.

## Dados

- Nome: apelido da conta.
- Banco: instituicao financeira.
- Agencia: campo opcional.
- Conta: campo opcional.
- Moeda: `BRL`, `USD`, `EUR` ou `GBP`.
- Saldo inicial: valor monetario usado como base do saldo atual.
- Observacoes: campo opcional.

## Regras

- Nome e banco sao obrigatorios.
- O saldo deve ser armazenado em centavos.
- Contas arquivadas nao aparecem na lista principal.
- Contas arquivadas podem ser listadas e restauradas.
- A moeda de uma conta com lancamentos ativos nao pode ser alterada.
- Alterar saldo inicial ajusta o saldo atual pela diferenca.

## API e dados

- `GET /api/checking-accounts`
- `GET /api/checking-accounts?status=archived`
- `POST /api/checking-accounts`
- `PUT /api/checking-accounts/{id}`
- `DELETE /api/checking-accounts/{id}`
- `POST /api/checking-accounts/{id}/restore`
- Tabela: `checking_accounts`.

## Criterios de aceite

- Ao cadastrar uma conta BRL, o valor aparece na lista e no agrupamento de saldos.
- Ao cadastrar contas em moedas diferentes, cada moeda aparece uma vez no bloco de saldos.
- Ao arquivar uma conta, os totais sao recalculados.
- Ao restaurar uma conta, ela volta para a lista principal.
