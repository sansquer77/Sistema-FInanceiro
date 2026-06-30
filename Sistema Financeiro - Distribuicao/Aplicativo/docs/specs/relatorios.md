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
6. Acompanha a evolução temporal de categorias/subcategorias por meio de gráfico (sob demanda).

## Tipos de relatório

| Tipo | Agrupamento |
|---|---|
| Categorias | Por categoria principal, separando receitas e despesas. |
| Subcategorias | Por `Categoria / Subcategoria`; lançamentos sem subcategoria aparecem como `Categoria / Sem subcategoria`. |
| Entradas × Saídas | Receita total vs. despesa total no período. |
| Contas | Por conta-corrente. |
| Tags | Por tag, considerando lançamentos de contas e cartões mesmo sem subcategoria. |

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
- Nos cartões de categoria e subcategoria, o usuário pode acionar a visualização da **evolução temporal** daquele agrupamento.
- A evolução temporal busca agregados mensais sob demanda (3m, 6m, 12m, ytd, all), garantindo que não sobrecarregue o processamento inicial.

## Critérios de aceite

- Dado o usuário alternando o tipo de relatório, quando alterna, o período selecionado é mantido.
- Dado o usuário escolhendo período rápido ou personalizado, quando selecionado, os totais refletem exatamente o intervalo escolhido.
- Dado o relatório de categorias, quando exibido, mostra total e percentual por categoria.
- Dado o relatório de subcategorias, quando exibido, mostra total e percentual por categoria/subcategoria.
- Dado o relatório de tags, quando exibido, agrega lançamentos por tag, incluindo lançamentos de cartão.
- Dado movimentações em múltiplas moedas, quando exibidas, os totais são separados por moeda.
- Dado um cartão de categoria ou subcategoria, ao solicitar evolução temporal (ex: 6m), exibe um gráfico de linha contendo o somatório mês a mês (inclusive lançamentos de faturas).

## Changelog

- `1.1` — 2026-06-30 — Adição da regra de evolução temporal (gráfico de linha sob demanda) para categorias/subcategorias.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[lancamentos]]
- [[cartoes]]
- [[categorias-tags-gestao]]
- [[limites-gastos]]
- [[arquitetura]]
