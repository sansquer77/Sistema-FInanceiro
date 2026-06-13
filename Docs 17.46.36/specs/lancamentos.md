# Spec: Lançamentos

## Problema

O usuário precisa registrar movimentações financeiras e enxergar saldo realizado e previsto por período.

## Jornada

1. O usuário abre Lançamentos.
2. Escolhe um período.
3. Registra despesa, receita ou transferência.
4. Classifica com conta, categoria e tags.
5. Confere a lista agrupada por data e os saldos.

## Regras

- Despesa em conta reduz saldo da conta.
- Receita em conta aumenta saldo da conta.
- Transferência move saldo entre contas sem alterar patrimônio total.
- Despesa em cartão entra em fatura.
- Lançamento previsto só entra em saldo previsto.
- Lançamento realizado entra em saldo atual.

## Critérios de aceite

- A lista agrupa lançamentos por data.
- O filtro por período altera a lista e os totais.
- A busca encontra lançamentos por descrição.
- O saldo previsto considera lançamentos futuros do período.
