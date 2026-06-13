# Referência: Relatórios

Análise feita em 13/06/2026 com conta de teste autorizada.

## Papel do módulo

Relatórios transformam lançamentos em leitura financeira: distribuição por categoria, comparação entre entradas e saídas, evolução por conta e análise por tags.

## Tipos observados

- Categorias.
- Entradas x Saídas.
- Contas.
- Tags.

## Estrutura comum

- Cabeçalho "Relatórios".
- Período selecionado.
- Atalhos de período:
  - Hoje.
  - Esta semana.
  - Este mês.
  - Últimos 3 meses.
  - Últimos 6 meses.
  - Últimos 12 meses.
  - Este ano.
  - Escolher período.
- Navegação entre tipos de relatório.
- Filtros avançados.
- Impressão detalhada.
- Impressão sintética.

## Relatório de categorias

Estrutura observada:

- Separação entre despesas e receitas.
- Lista de categorias com valor e percentual.
- Total por seção.
- Possibilidade de visualização sintética ou detalhada.

Regras:

- Despesas e receitas não devem ser somadas no mesmo total.
- Percentuais são calculados em relação ao total da seção.
- Subcategorias devem poder compor a categoria principal.

## Relatório Entradas x Saídas

Objetivo esperado:

- Comparar receitas e despesas por período.
- Evidenciar resultado líquido.
- Permitir leitura mensal ou por intervalo.

Métricas:

- Total de entradas.
- Total de saídas.
- Saldo do período.
- Variação entre períodos, quando houver histórico.

## Relatório de contas

Objetivo esperado:

- Mostrar distribuição e movimentação por conta.
- Ajudar a entender origem e destino do dinheiro.

Métricas:

- Saldo inicial do período.
- Entradas.
- Saídas.
- Transferências.
- Saldo final.

## Relatório de tags

Objetivo esperado:

- Agrupar lançamentos por marcador livre.
- Permitir análises que categorias não cobrem, como projetos, pessoas, viagens ou investimentos.

Métricas:

- Total por tag.
- Percentual por tag.
- Detalhe dos lançamentos associados.

## Filtros esperados

- Período.
- Conta.
- Cartão.
- Categoria.
- Tag.
- Tipo de lançamento.
- Estado realizado/previsto.

## Saídas esperadas

- Visualização em tela.
- Impressão detalhada: agrupamento e lançamentos.
- Impressão sintética: apenas totais agregados.
- Exportação futura em CSV ou XLSX.

## Critérios de aceite futuros

- O usuário alterna entre relatórios sem perder o período selecionado.
- O relatório de categorias separa despesas e receitas.
- Filtros avançados afetam todos os totais apresentados.
- O modo sintético omite lançamentos individuais.
- O modo detalhado mostra lançamentos que compõem cada total.
