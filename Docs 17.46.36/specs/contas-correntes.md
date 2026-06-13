# Contas-correntes

## Problema

O usuário precisa cadastrar contas bancárias e consultar saldos sem confusão visual.

## Usuário

Pessoa que usa o app localmente para organizar contas, cartões, investimentos e movimentações pessoais.

## Jornada atual

1. O usuário entra no app.
2. Acessa a tela de contas-correntes.
3. Cadastra uma conta com banco, agência, número, moeda e saldo inicial.
4. Visualiza a conta na lista.
5. Confere os saldos agrupados por moeda.

## Dados

- Nome: apelido da conta.
- Banco: instituição financeira.
- Agência: campo opcional.
- Conta: campo opcional.
- Moeda: uma das moedas aceitas no módulo inicial.
- Saldo inicial: valor monetário usado também como saldo atual enquanto não houver movimentações.
- Observações: campo opcional.

## Regras

- Nome e banco são obrigatórios.
- O saldo deve ser armazenado em centavos.
- Contas arquivadas não aparecem na lista principal.
- O saldo em BRL não deve aparecer duplicado quando já estiver presente em "Saldos por moeda".
- Contas conectadas a bancos ficam fora do módulo inicial; o cadastro atual é manual.

## Critérios de aceite

- Ao cadastrar uma conta BRL, o valor aparece na lista da conta e no bloco "Saldos por moeda".
- A tela não exibe um cartão separado com o mesmo total em BRL.
- Ao cadastrar contas em moedas diferentes, cada moeda aparece uma vez no bloco de saldos.
- Ao arquivar uma conta, os totais são recalculados.

## Fora de escopo

- Conciliação bancária.
- Importação automática.
- Movimentações e transferências.
- Contas conectadas por Open Finance.
