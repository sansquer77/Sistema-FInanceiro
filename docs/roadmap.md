---
tipo: roadmap
area: meta
status: implementado
versao: 1.1
atualizado: 2026-06-29
relacionados:
  - "[[visao-produto]]"
  - "[[requisitos]]"
  - "[[arquitetura]]"
tags: [roadmap, meta]
aliases: ["Roadmap", "Replicação Local"]
---

# Roadmap

> [!info] Status
> **implementado** (todos os módulos planejados concluídos) · área: `meta` · atualizado em 2026-06-29

Este documento organiza a evolução do Sistema Financeiro e serve de histórico de decisões de sequenciamento. Módulos planejados que ainda não iniciaram ficam com status `planejado`.

## Premissas

- O app local deve funcionar sem internet para operações financeiras básicas.
- A fonte de verdade é o SQLite local. Ver [[adr/0003-sqlite-fonte-de-verdade]].
- Cada módulo novo precisa de spec própria em `specs/` antes da implementação. Ver [[sdd]].
- Dados monetários são armazenados em centavos.
- Registros removidos pelo usuário devem ser arquivados sempre que houver valor histórico.
- A interface deve separar cadastros, lançamentos, relatórios e visão geral.

---

## Módulos e status

| # | Módulo | Status | Spec |
|---|---|---|---|
| 1 | Contas manuais, arquivamento e saldo por moeda. Naturezas: liquidez, carteira, investimentos. | ✅ Implementado | [[contas-correntes]] |
| 2 | Categorias e tags: taxonomia financeira e classificação transversal (múltiplas tags). | ✅ Implementado | [[categorias-tags-gestao]] |
| 3 | Lançamentos: despesas, receitas, transferências, recorrência, parcelamento e conciliação bancária. | ✅ Implementado | [[lancamentos]] |
| 4 | Cartões de crédito: cartões manuais, limite, fechamento, vencimento, conta preferencial de pagamento, recorrência/parcelamento, conciliação, movimentação entre faturas, pagamento e faturas mensais. | ✅ Implementado | [[cartoes]] |
| 5 | Limites de gastos: metas por categoria e subcategoria mensais. | ✅ Implementado | [[limites-gastos]] |
| 6 | Investimentos e Portfólio: consolidação de ativos, cotações integradas de mercado, indexadores de renda fixa (SGS/BCB), poupança, previdência privada, resgate, encerramento e ajuste manual de valor. | ✅ Implementado | [[investimentos-portfolio]] |
| 7 | Relatórios avançados e Cockpit integrando contas, cartões, limites, dívidas e portfólio. | ✅ Implementado | [[relatorios]] |
| 8 | Segurança: bloqueio de tentativas, cookie seguro, headers defensivos, validação de origem. | ✅ Implementado | [[seguranca-autenticacao]] |
| 9 | Recuperação de senha com configuração SMTP local criptografada e assistente para Gmail/Outlook. | ✅ Implementado | [[recuperacao-senha]] |
| 10 | Importação Organizze e planilhas modelo do sistema (`.xlsx`). | ✅ Implementado | [[importacao-organizze]] |
| 11 | Modularização do frontend em ES Modules nativos sem build step. | ✅ Implementado | [[adr/0002-modularizacao-frontend]] |
| 12 | Conciliação automática de arquivos OFX bancários. | 🔲 Planejado | — |
| 13 | Exportação direta de dados em outros formatos. | 🔲 Planejado | — |

---

## Sequência de evolução concluída

1. ✅ Consolidar filtros, busca e edição de lançamentos.
2. ✅ Implementar cartões de crédito e faturas.
3. ✅ Implementar limites de gastos (budgets).
4. ✅ Implementar portfólio de investimentos e precificação automática.
5. ✅ Implementar conciliação e recorrência.
6. ✅ Implementar relatórios sintéticos/analíticos interativos no frontend web.
7. ✅ Modularizar o frontend em ES Modules nativos.
8. ✅ Enrijecer autenticação (bloqueio de tentativas, headers defensivos).

## Próximas prioridades sugeridas

1. **Conciliação OFX** — permitir que arquivos exportados de bancos sejam conciliados automaticamente com os lançamentos existentes.
2. **Exportação de dados** — permitir exportar lançamentos, cartões ou portfólio em formatos como `.csv` ou `.xlsx`.

Antes de iniciar qualquer item acima, criar spec em `specs/` seguindo [[sdd]] e atualizar esta tabela.

---

## Modelo de dados conceitual

```text
users
sessions
password_resets
auth_attempts
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

Ver mapeamento completo de tabelas em [[arquitetura]].

---

## Critério de fidelidade

A implementação local não copia a interface de nenhum produto externo. Reproduz capacidades:

- Cadastrar estruturas financeiras.
- Registrar e consultar movimentações.
- Classificar por categoria, subcategoria e tags.
- Acompanhar saldo realizado.
- Acompanhar faturas e limites de cartão.
- Acompanhar portfólio de investimentos de renda variável, renda fixa e criptoativos com valorização real.
- Acompanhar poupança, previdência privada e ativos multimoeda na moeda da carteira.
- Acompanhar limites de gastos.
- Gerar relatórios por período, categoria, subcategoria, conta, tag e fluxo diário.
- Usar Cockpit para visualizar saldos, planejamento recorrente, dívidas, maiores receitas/despesas e portfólio por tipo.
- Distribuir o app sem banco, logs, chaves ou credenciais SMTP; cada instalação configura sua própria recuperação por e-mail.

## Changelog

- `1.1` — 2026-06-29 — Consolidação de `replicacao-local.md` neste arquivo; adição de frontmatter, status por módulo e próximas prioridades.
- `1.0` — versão original.

## Relacionados

- [[visao-produto]]
- [[requisitos]]
- [[arquitetura]]
- [[sdd]]
