# Lancamentos

## Objetivo

Permitir que o usuario registre movimentacoes financeiras manuais e mantenha os saldos das contas atualizados.

## Estado

**Implementado** (com suporte a lançamentos simples, transferências, conciliação bancária, recorrência periódica, parcelamentos e operações em cascata de edição/exclusão).

## Jornada

1. Usuario abre a area de lancamentos.
2. Escolhe tipo: receita, despesa ou transferencia.
3. Informa conta, valor, data, descricao, categoria e tags.
4. Para transferencia, informa tambem a conta de destino.
5. Para lançamentos recorrentes ou parcelados, define a frequência de recorrência ou a quantidade total de parcelas.
6. O sistema grava o lancamento e atualiza os saldos das contas afetadas.

## Regras de Negócio

- Despesa reduz o saldo da conta de origem.
- Receita aumenta o saldo da conta de origem.
- Transferencia reduz o saldo da origem e aumenta o saldo do destino.
- Transferencia exige contas diferentes e com a mesma moeda.
- Valor deve ser maior que zero.
- Data deve ser valida em formato ISO.
- Categoria e ao menos uma tag sao obrigatorias.
- Subcategoria e observacoes sao opcionais.
- Excluir lancamento reverte o impacto no saldo.
- **Edição em cascata**: Ao editar um lançamento que faz parte de uma recorrência ou parcelamento, o usuário pode optar por aplicar as alterações apenas ao lançamento atual ou também a todos os lançamentos futuros da série que ainda não foram conciliados (`reconciled_at IS NULL`).
- **Exclusão em cascata**: Ao excluir um lançamento de uma série com o parâmetro `scope=future`, o sistema remove recursivamente todos os lançamentos futuros da mesma série que não estejam conciliados, revertendo seus respectivos impactos nos saldos das contas.

## API e dados

- `GET /api/transactions`
- `POST /api/transactions`
- `PUT /api/transactions/{id}` (aceita parâmetro `apply_to_future` para cascata)
- `DELETE /api/transactions/{id}` (aceita query `scope=future` para cascata)
- `PUT /api/transactions/{id}/reconciliation` (atualiza status de conciliação)
- Tabelas: `transactions`, `transaction_tags`, `checking_accounts`, `categories`, `subcategories`, `tags`.

## Criterios de aceite

- Ao criar receita, o saldo da conta aumenta.
- Ao criar despesa, o saldo da conta diminui.
- Ao criar transferencia, origem e destino sao atualizados corretamente.
- Ao excluir lancamento, o saldo volta ao estado anterior.
- A exclusão com `scope=future` remove as parcelas/recorrências futuras não conciliadas.
- A edição com `apply_to_future` atualiza os dados e recalcula o saldo e câmbio das ocorrências futuras não conciliadas.
- A listagem exibe conta, tipo, valor, data, categoria, subcategoria, tags e se o lançamento é recorrente ou parcelado.
