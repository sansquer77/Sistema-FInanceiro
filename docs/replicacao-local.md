# Replicacao Local

Este roteiro organiza a evolucao do Sistema Financeiro para reproduzir localmente capacidades comuns de organizadores financeiros, mantendo o app offline-first, simples e controlado por specs.

## Premissas

- O app local deve funcionar sem internet para operacoes financeiras basicas.
- A fonte de verdade e o SQLite local.
- Cada modulo novo precisa de spec propria em `docs/specs/`.
- Dados monetarios devem ser armazenados em centavos.
- Registros removidos pelo usuario devem ser arquivados sempre que houver valor historico.
- A interface deve separar cadastros, lancamentos, relatorios e visao geral.

## Mapa de modulos

1. Contas: contas manuais, contas arquivadas e saldo por moeda. Implementado.
2. Categorias e tags: taxonomia financeira e classificacao transversal. Implementado.
3. Lancamentos: despesas, receitas, transferencias e importacao. Implementado parcialmente.
4. Relatorios: categorias, entradas x saidas, contas e tags. Planejado.
5. Cartoes de credito: cartoes manuais, limite, fechamento, vencimento, conta de pagamento e faturas. Planejado.
6. Limites de gastos: metas por categoria e periodo. Planejado.
7. Visao geral: composicao dos modulos anteriores em resumo operacional. Planejado.

## Sequencia recomendada

1. Consolidar filtros, busca e edicao de lancamentos.
2. Implementar relatorios sobre os dados atuais.
3. Implementar cartoes de credito e faturas.
4. Implementar recorrencia, parcelamento e previsoes.
5. Implementar limites de gastos.
6. Criar visao geral consolidada com dados reais dos modulos.

## Modelo de dados conceitual

```text
users
sessions
password_resets
checking_accounts
categories
subcategories
tags
transactions
transaction_tags
credit_cards
credit_card_invoices
budgets
```

## Criterio de fidelidade

A replica local nao precisa copiar a interface de nenhum produto externo. Ela deve reproduzir capacidades:

- Cadastrar estruturas financeiras.
- Registrar e consultar movimentacoes.
- Classificar por categoria, subcategoria e tags.
- Acompanhar saldo realizado.
- Acompanhar faturas e limites de cartao.
- Gerar relatorios por periodo e dimensao.
