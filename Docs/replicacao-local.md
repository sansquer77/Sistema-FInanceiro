# Replicação Local

Este roteiro organiza a evolução do Sistema Financeiro para reproduzir localmente as principais funcionalidades observadas no Organizze, mantendo o app offline-first, simples e controlado por specs.

## Premissas

- O app local deve funcionar sem internet.
- A fonte de verdade é o SQLite local.
- Cada módulo novo precisa de spec própria em `Docs/specs/`.
- Dados monetários devem ser armazenados em centavos.
- Registros removidos pelo usuário devem ser arquivados sempre que houver valor histórico.
- A interface deve separar cadastros, lançamentos, relatórios e visão geral.

## Mapa de módulos

1. Contas: contas manuais, contas arquivadas e saldo por moeda.
2. Cartões de crédito: cartões manuais, limite, fechamento, vencimento, conta padrão de pagamento e faturas.
3. Categorias: categorias de despesa e receita, subcategorias, arquivamento e exclusão controlada.
4. Tags: marcadores livres para cruzar relatórios e lançamentos.
5. Lançamentos: despesas, receitas, transferências, agendamentos, parcelas, filtros e busca.
6. Relatórios: categorias, entradas x saídas, contas e tags.
7. Limites de gastos: metas por categoria e período.
8. Visão geral: composição dos módulos anteriores em cards resumidos.

## Sequência recomendada

1. Consolidar contas manuais.
2. Implementar categorias e tags, pois são base para lançamentos e relatórios.
3. Implementar lançamentos simples: despesa, receita e transferência.
4. Implementar cartões de crédito e faturas.
5. Implementar filtros, busca, recorrência e parcelamento.
6. Implementar relatórios.
7. Implementar limites de gastos.
8. Criar visão geral final, usando dados reais dos módulos.

## Modelo de dados conceitual

```text
users
accounts
credit_cards
credit_card_invoices
categories
tags
transactions
transaction_tags
budgets
```

## Critério de fidelidade

A réplica local não precisa copiar a interface do Organizze. Ela deve reproduzir as capacidades:

- Cadastrar estruturas financeiras.
- Registrar e consultar movimentações.
- Classificar por categoria, subcategoria e tags.
- Acompanhar saldo realizado e previsto.
- Acompanhar faturas e limites de cartão.
- Gerar relatórios por período e dimensão.
