# Spec: Relatórios

## Problema

O usuário precisa transformar lançamentos em leitura financeira por período, categoria, subcategoria, conta e tag.

## Jornada

1. O usuário abre Relatórios.
2. Escolhe um tipo de relatório.
3. Seleciona período e filtros.
4. Visualiza totais, percentuais e detalhes.
5. Imprime ou exporta quando necessário.

## Tipos

- Categorias.
- Subcategorias.
- Entradas x Saídas.
- Contas.
- Tags.

## Regras

- Filtros devem afetar totais e detalhes.
- Despesas e receitas devem aparecer separadas no relatório de categorias.
- O relatório de subcategorias agrupa por `Categoria / Subcategoria`; lançamentos sem subcategoria aparecem como `Categoria / Sem subcategoria`.
- O relatório de categorias deve considerar lançamentos classificados apenas na categoria principal, mesmo sem subcategoria.
- O relatório de tags deve considerar lançamentos de contas e cartões com tag, mesmo quando não houver subcategoria.
- Lançamentos de cartão entram nos relatórios pela competência da fatura (`invoice_month`), não pela data da compra.
- Relatórios exibem totais por moeda quando houver movimentações multimoeda.
- Percentuais devem ser calculados contra o total da seção.
- Relatório detalhado mostra lançamentos.
- Relatório sintético mostra apenas agregados.

## Critérios de aceite

- O usuário alterna tipo de relatório mantendo o período.
- O usuário escolhe períodos rápidos e período personalizado.
- O relatório de categorias mostra total e percentual por categoria.
- O relatório de subcategorias mostra total e percentual por categoria/subcategoria.
- O relatório de tags agrega lançamentos por tag.
