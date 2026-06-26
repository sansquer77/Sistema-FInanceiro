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

1. Contas: contas manuais, contas arquivadas e saldo por moeda. Naturezas de contas (liquidez, carteira, investimentos). Implementado.
2. Categorias e tags: taxonomia financeira e classificação transversal (múltiplas tags). Implementado.
3. Lançamentos: despesas, receitas, transferências, recorrência, parcelamento e conciliação bancária. Implementado.
4. Cartões de crédito: cartões manuais, limite, fechamento, vencimento, conta preferencial de pagamento, recorrência/parcelamento, conciliação, movimentação entre faturas, pagamento e faturas mensais. Implementado.
5. Limites de gastos: metas por categoria e subcategoria mensais. Implementado.
6. Investimentos e Portfólio: consolidação de ativos, cotações integradas de mercado, indexadores de renda fixa (SGS/BCB), poupança, previdência privada, resgate, encerramento e ajuste manual de valor. Implementado.
7. Relatórios avançados e Visão Geral: relatórios dinâmicos e Cockpit integrando contas, cartões, limites, dívidas e portfólio. Implementado.
8. Preferências e segurança: recuperação de senha com configuração SMTP local criptografada e assistente para Gmail/Outlook. Implementado.

## Sequencia recomendada de evolucao

1. Consolidar filtros, busca e edição de lançamentos. (Concluído)
2. Implementar cartões de crédito e faturas. (Concluído)
3. Implementar limites de gastos (budgets). (Concluído)
4. Implementar portfólio de investimentos e precificação automática. (Concluído)
5. Implementar conciliação e recorrência. (Concluído)
6. Implementar relatórios sintéticos/analíticos interativos de despesas/receitas e evolução patrimonial no frontend web. (Concluído)

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
credit_card_transactions
credit_card_payments
credit_card_transaction_tags
spending_limits
investment_opening_positions
investment_operations
investment_redemptions
investment_closed_positions
investment_value_overrides
quote_cache
```

## Criterio de fidelidade

A replica local nao precisa copiar a interface de nenhum produto externo. Ela deve reproduzir capacidades:

- Cadastrar estruturas financeiras.
- Registrar e consultar movimentacoes.
- Classificar por categoria, subcategoria e tags.
- Acompanhar saldo realizado.
- Acompanhar faturas e limites de cartao.
- Acompanhar portfólio de investimentos de renda variável, renda fixa e criptoativos com valorização real.
- Acompanhar poupança, previdência privada e ativos multimoeda na moeda da carteira.
- Acompanhar limites de gastos.
- Gerar relatorios por periodo, categoria, subcategoria, conta, tag e fluxo diário.
- Usar Cockpit para visualizar saldos por moeda, planejamento recorrente, dívidas, maiores receitas/despesas e portfólio por tipo.
- Distribuir o app sem banco, logs, chaves ou credenciais SMTP; cada instalação configura sua própria recuperação por e-mail.
