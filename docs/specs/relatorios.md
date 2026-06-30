---
tipo: spec
area: relatorios
status: implementado
versao: 1.1
atualizado: 2026-06-30
relacionados:
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[categorias-tags-gestao]]"
  - "[[limites-gastos]]"
  - "[[arquitetura]]"
tags: [spec, "area/relatorios"]
aliases: ["Relatórios", "Cockpit"]
---

# Relatórios

> [!info] Status
> **implementado** · área: `relatorios` · atualizado em 2026-06-30 · relacionados: [[lancamentos]], [[cartoes]], [[categorias-tags-gestao]], [[limites-gastos]]

## Problema

O usuário precisa transformar lançamentos em leitura financeira por período, categoria, subcategoria, conta e tag — tanto em visão sintética quanto detalhada.

## Usuário

Qualquer usuário autenticado localmente que queira analisar seus gastos e receitas por diferentes dimensões financeiras.

## Jornada

1. O usuário abre Relatórios.
2. Escolhe um tipo de relatório.
3. Seleciona período e filtros.
4. Visualiza totais, percentuais e detalhes.
5. Imprime ou exporta quando necessário.
6. Abre a evolução temporal de uma categoria/subcategoria para analisar tendência, média móvel e projeção simples.

## Tipos de relatório

| Tipo | Agrupamento |
|---|---|
| Categorias | Por categoria principal, separando receitas e despesas. |
| Subcategorias | Por `Categoria / Subcategoria`; lançamentos sem subcategoria aparecem como `Categoria / Sem subcategoria`. |
| Entradas × Saídas | Receita total vs. despesa total no período. |
| Contas | Por conta-corrente. |
| Tags | Por tag, considerando lançamentos de contas e cartões mesmo sem subcategoria. |
| Evolução de categoria | Série mensal por categoria ou subcategoria, com períodos rápidos (`3m`, `6m`, `12m`, `ytd`, `all`). |

## Regras

- Filtros afetam totais e detalhes simultaneamente.
- Despesas e receitas aparecem separadas no relatório de categorias.
- O relatório de categorias considera lançamentos classificados apenas na categoria principal, mesmo sem subcategoria.
- O relatório de subcategorias agrupa por `Categoria / Subcategoria`.
- O relatório de tags considera lançamentos de contas e cartões com tag, mesmo quando não houver subcategoria.
- **Lançamentos de cartão entram nos relatórios pela competência da fatura (`invoice_month`), não pela data da compra.** Ver [[cartoes]].
- Relatórios exibem totais por moeda quando houver movimentações multimoeda.
- Percentuais são calculados contra o total da seção.
- Relatório **detalhado** mostra lançamentos individuais.
- Relatório **sintético** mostra apenas agregados.
- A evolução temporal usa `category_id`, `subcategory_id` opcional e período para retornar uma série mensal; o frontend pode aplicar média móvel e projeção visual sem persistir esses cálculos.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/cockpit?month=AAAA-MM` |
| `GET` | `/api/reports/category-evolution?category_id={id}&subcategory_id={id}&period={periodo}` |

Dados de origem: `transactions`, `credit_card_transactions`, `categories`, `subcategories`, `tags`, `transaction_tags`, `credit_card_transaction_tags`, `checking_accounts`.

Valores aceitos para `periodo`: `3m`, `6m`, `12m`, `ytd` e `all`.

## Critérios de aceite

- Dado o usuário alternando o tipo de relatório, quando alterna, o período selecionado é mantido.
- Dado o usuário escolhendo período rápido ou personalizado, quando selecionado, os totais refletem exatamente o intervalo escolhido.
- Dado o relatório de categorias, quando exibido, mostra total e percentual por categoria.
- Dado o relatório de subcategorias, quando exibido, mostra total e percentual por categoria/subcategoria.
- Dado o relatório de tags, quando exibido, agrega lançamentos por tag, incluindo lançamentos de cartão.
- Dado movimentações em múltiplas moedas, quando exibidas, os totais são separados por moeda.
- Dado uma categoria com histórico, quando o usuário abre a evolução, o sistema retorna a série mensal do período selecionado.

## Changelog

- `1.1` — 2026-06-30 — Documentação do endpoint de Cockpit e da evolução temporal por categoria/subcategoria.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[lancamentos]]
- [[cartoes]]
- [[categorias-tags-gestao]]
- [[limites-gastos]]
- [[arquitetura]]
