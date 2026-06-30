---
tipo: produto
area: meta
status: implementado
versao: 1.1
atualizado: 2026-06-29
relacionados:
  - "[[requisitos]]"
  - "[[roadmap]]"
  - "[[arquitetura]]"
tags: [produto, meta]
aliases: ["Visão do Produto"]
---

# Visão do Produto

> [!info] Status
> **implementado** (escopo vivo) · área: `meta` · atualizado em 2026-06-29 · relacionados: [[requisitos]], [[roadmap]], [[arquitetura]]

## Objetivo

Criar um sistema financeiro local, simples e confiável para organizar contas, movimentações e classificações pessoais sem depender de serviços externos para operar no dia a dia.

## Inspiração

O Organizze serve como referência de clareza: módulos financeiros separados, saldos fáceis de conferir, baixa fricção para cadastrar informações e relatórios por dimensões financeiras. O app deve seguir essa direção sem copiar interface, textos proprietários ou dados de contas.

## Princípios de experiência

- A tela inicial deve responder rapidamente *quanto existe, onde está e o que mudou*.
- Cada módulo deve ter uma responsabilidade clara.
- Valores monetários não devem aparecer duplicados quando representam o mesmo dado.
- A interface deve priorizar leitura, conferência e cadastro rápido.
- O usuário deve conseguir operar o app localmente, mesmo sem internet.
- A navegação deve separar visão geral, cadastros, lançamentos e relatórios.

## Módulos

### Implementados

| Módulo | Spec |
|---|---|
| Autenticação e conta do usuário | [[seguranca-autenticacao]], [[recuperacao-senha]] |
| Contas-correntes manuais (liquidez, carteira, investimentos) em múltiplas moedas | [[contas-correntes]] |
| Categorias, subcategorias e tags | [[categorias-tags-gestao]] |
| Lançamentos de receita, despesa, transferência e investimento | [[lancamentos]] |
| Lançamentos recorrentes e parcelamento de transações | [[lancamentos]] |
| Cartões de crédito, limites, faturas e fluxo de pagamentos de fatura | [[cartoes]] |
| Limites e metas de gastos mensais por categoria e subcategoria | [[limites-gastos]] |
| Cockpit com saldos, planejamento recorrente, dívidas, maiores receitas/despesas e portfólio | [[arquitetura]] |
| Relatórios por categoria, subcategoria, conta, tag e fluxo diário | [[relatorios]] |
| Portfólio de investimentos com cotações integradas, indexadores do BCB, poupança e previdência privada | [[investimentos-portfolio]] |
| Importação de lançamentos do Organizze e planilhas modelo `.xlsx` | [[importacao-organizze]] |
| Recuperação de senha por e-mail SMTP com assistente para Gmail e Outlook | [[recuperacao-senha]] |
| Modularização do frontend em ES Modules nativos | [[adr/0002-modularizacao-frontend]] |
| Segurança: bloqueio de tentativas, headers defensivos, validação de origem | [[seguranca-autenticacao]] |

### Planejados

- Conciliação automática de arquivos OFX bancários.
- Integração ou exportação direta de dados em outros formatos.

## Estado atual

O app cobre todo o ciclo avançado de controle financeiro local: usuário entra, configura recuperação de senha por e-mail quando desejar, cadastra contas e cartões, define limites, cria categorias/tags, registra lançamentos normais, parcelados ou recorrentes, acompanha faturas, relatórios e Cockpit, realiza acompanhamento de investimentos com precificação automática ou ajuste manual de ativos, e importa dados de planilhas locais.

As próximas evoluções devem priorizar automações de conciliação/importação e refinamentos de precisão para classes específicas de ativos. Ver [[roadmap]].

## Changelog

- `1.1` — 2026-06-29 — Frontmatter, tabela de módulos com links para specs e separação de "planejados".
- `1.0` — versão original.

## Relacionados

- [[requisitos]]
- [[roadmap]]
- [[arquitetura]]
- [[glossario]]
