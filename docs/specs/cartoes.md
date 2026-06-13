# Spec: Cartões de Crédito

## Problema

O usuário precisa controlar gastos de cartão, limite, faturas e vencimentos sem misturar compras de cartão com saldo imediato de conta.

## Jornada

1. O usuário cria um cartão manual.
2. Define limite, fechamento, vencimento e conta de pagamento padrão.
3. Registra despesas no cartão.
4. Acompanha fatura aberta.
5. Paga a fatura usando uma conta.

## Regras

- Gasto em cartão pertence a uma fatura.
- Fatura tem status aberta, fechada ou paga.
- Pagamento de fatura cria saída na conta de pagamento.
- Cartão arquivado não aparece para novos lançamentos.

## Critérios de aceite

- O usuário cadastra cartão com nome, limite, fechamento e vencimento.
- Uma despesa no cartão aparece na fatura correta.
- O total da fatura soma seus lançamentos.
- O pagamento altera o saldo da conta escolhida.
