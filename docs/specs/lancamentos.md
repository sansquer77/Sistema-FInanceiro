# Lancamentos

## Objetivo

Permitir que o usuario registre movimentacoes financeiras manuais e mantenha os saldos das contas atualizados.

## Estado

Implementado para receitas, despesas, transferencias, exclusao e listagem simples. Filtros por periodo, busca, recorrencia, previsao e parcelamento ainda estao fora do escopo atual.

## Jornada

1. Usuario abre a area de lancamentos.
2. Escolhe tipo: receita, despesa ou transferencia.
3. Informa conta, valor, data, descricao, categoria e tags.
4. Para transferencia, informa tambem a conta de destino.
5. O sistema grava o lancamento e atualiza os saldos das contas afetadas.

## Regras

- Despesa reduz o saldo da conta de origem.
- Receita aumenta o saldo da conta de origem.
- Transferencia reduz o saldo da origem e aumenta o saldo do destino.
- Transferencia exige contas diferentes e com a mesma moeda.
- Valor deve ser maior que zero.
- Data deve ser valida em formato ISO.
- Categoria e ao menos uma tag sao obrigatorias.
- Subcategoria e observacoes sao opcionais.
- Excluir lancamento reverte o impacto no saldo.

## API e dados

- `GET /api/transactions`
- `POST /api/transactions`
- `DELETE /api/transactions/{id}`
- Tabelas: `transactions`, `transaction_tags`, `checking_accounts`, `categories`, `subcategories`, `tags`.

## Criterios de aceite

- Ao criar receita, o saldo da conta aumenta.
- Ao criar despesa, o saldo da conta diminui.
- Ao criar transferencia, origem e destino sao atualizados corretamente.
- Ao excluir lancamento, o saldo volta ao estado anterior.
- A listagem exibe conta, tipo, valor, data, categoria, subcategoria e tags.
