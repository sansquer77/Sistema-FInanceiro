# Referência: Cartões de Crédito

Análise feita em 13/06/2026 com conta de teste autorizada.

## Papel do módulo

Cartões de crédito organizam gastos que não afetam imediatamente o saldo da conta. Eles acumulam lançamentos em faturas, controlam limite disponível e geram pagamento futuro em uma conta padrão.

## Estrutura observada

- Página dedicada para cartões.
- Lista de cartões ativos.
- Lista separada de cartões arquivados.
- Ação para adicionar cartão.
- Diferenciação entre cartão manual e cartão conectado.
- Caminho para conexão bancária via Open Finance como evolução opcional.

## Cadastro de cartão manual

Campos observados:

- Nome do cartão.
- Ícone.
- Cor.
- Limite.
- Dia de fechamento da fatura.
- Dia de vencimento da fatura.
- Conta de pagamento padrão.

## Entidades sugeridas

### Cartão

- `id`
- `user_id`
- `name`
- `icon`
- `color`
- `limit_cents`
- `billing_cycle_day`
- `billing_due_day`
- `payment_account_id`
- `archived_at`
- `created_at`
- `updated_at`

### Fatura

- `id`
- `credit_card_id`
- `month`
- `year`
- `closing_date`
- `due_date`
- `status`
- `total_cents`
- `paid_at`
- `payment_account_id`

### Lançamento de cartão

Pode usar a mesma tabela de lançamentos com campos específicos:

- `credit_card_id`
- `invoice_id`
- `installment_number`
- `installment_count`

## Regras para a réplica local

- Gasto em cartão entra na fatura aberta conforme a data da compra e o fechamento.
- Limite disponível = limite total menos fatura aberta e compras ainda não pagas conforme regra escolhida.
- Pagamento de fatura cria saída na conta de pagamento e marca a fatura como paga.
- Cartão arquivado não aparece na seleção padrão para novos lançamentos.
- Alterar dia de fechamento/vencimento deve preservar faturas já fechadas.

## Telas esperadas

- Lista de cartões.
- Cadastro/edição de cartão.
- Detalhe de cartão.
- Lista de faturas.
- Detalhe de fatura com lançamentos.
- Pagamento de fatura.

## Critérios de aceite futuros

- O usuário cadastra cartão manual com limite, fechamento e vencimento.
- O usuário registra despesa no cartão e ela aparece na fatura correta.
- A fatura mostra total, vencimento e status.
- O pagamento da fatura afeta uma conta.
- Cartões arquivados ficam separados dos ativos.
