---
tipo: spec
area: relatorios
status: implementado
versao: 1.4
atualizado: 2026-07-26
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
> **implementado** · área: `relatorios` · atualizado em 2026-07-26 · relacionados: [[lancamentos]], [[cartoes]], [[categorias-tags-gestao]], [[limites-gastos]]

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
| Demonstrativo mensal | Relatório imprimível/exportável por conta, cartão ou visão consolidada de contas e cartões ativos. |

## Regras

- Filtros afetam totais e detalhes simultaneamente.
- Despesas e receitas aparecem separadas no relatório de categorias.
- O relatório de categorias considera lançamentos classificados apenas na categoria principal, mesmo sem subcategoria.
- O relatório de subcategorias agrupa por `Categoria / Subcategoria`.
- O relatório de tags considera lançamentos de contas e cartões com tag, mesmo quando não houver subcategoria.
- **Lançamentos de cartão entram nos relatórios pela competência da fatura (`invoice_month`), não pela data da compra.** Ver [[cartoes]].
- Pagamentos de fatura gerados em conta-corrente reduzem o saldo da conta, mas não entram em análises de despesa, relatórios por categoria/subcategoria/tag, evolução de categoria nem totais do Cockpit, pois os lançamentos detalhados do cartão já representam o consumo.
- Relatórios exibem totais por moeda quando houver movimentações multimoeda.
- O planejamento do Cockpit separa receitas recorrentes, investimentos planejados e despesas recorrentes por moeda, exibindo os valores originais sem somar moedas distintas.
- Percentuais são calculados contra o total da seção.
- Relatório **detalhado** mostra lançamentos individuais.
- Relatório **sintético** mostra apenas agregados.
- A evolução temporal usa `category_id`, `subcategory_id` opcional e período para retornar uma série mensal; o frontend pode aplicar média móvel e projeção visual sem persistir esses cálculos.
- O demonstrativo mensal usa os mesmos dados analíticos carregados para Relatórios e Cockpit, respeitando a exclusão de pagamentos de fatura para evitar duplicidade.
- O demonstrativo pode ser gerado para uma conta ativa, um cartão ativo ou a visão consolidada de contas e cartões ativos.
- O demonstrativo deve priorizar impressão/exportação: cabeçalho minimalista com logo, título do mês, escopo, moeda base e data/hora de emissão; KPIs de saídas, média diária, maior categoria e maior lançamento; gráficos simples para categoria e gastos por dia; tabela de composição por categoria/subcategoria; detalhamento com zebra e valores à direita; rodapé com nome do app e página.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/cockpit?month=AAAA-MM` |
| `GET` | `/api/reports/category-evolution?category_id={id}&subcategory_id={id}&period={periodo}` |

Dados de origem: `transactions`, `credit_card_transactions`, `categories`, `subcategories`, `tags`, `transaction_tags`, `credit_card_transaction_tags`, `checking_accounts`.

Valores aceitos para `periodo`: `3m`, `6m`, `12m`, `ytd` e `all`.

## Plano de implementação

- [x] Identificar pagamentos de fatura em lançamentos de conta pelo vínculo `credit_card_payments.transaction_id`.
- [x] Excluir esses lançamentos apenas das visões analíticas, preservando o impacto no saldo da conta.
- [x] Atualizar Cockpit, Relatórios, evolução de categoria e limites para usar a regra analítica sem duplicidade.
- [x] Cobrir a regra com testes automatizados onde a agregação acontece no backend e validar manualmente as telas.
- [x] Criar aba de demonstrativos no módulo de Relatórios.
- [x] Reaproveitar dados carregados de contas, cartões e relatórios para montar escopos conta/cartão/consolidado sem nova rota.
- [x] Gerar layout imprimível com cabeçalho, KPIs, gráficos simples, composição, detalhamento e rodapé.
- [x] Validar sintaxe dos módulos frontend alterados.

## Critérios de aceite

- Dado o usuário alternando o tipo de relatório, quando alterna, o período selecionado é mantido.
- Dado o usuário escolhendo período rápido ou personalizado, quando selecionado, os totais refletem exatamente o intervalo escolhido.
- Dado o relatório de categorias, quando exibido, mostra total e percentual por categoria.
- Dado o relatório de subcategorias, quando exibido, mostra total e percentual por categoria/subcategoria.
- Dado o relatório de tags, quando exibido, agrega lançamentos por tag, incluindo lançamentos de cartão.
- Dado uma fatura paga no mês, quando relatórios e Cockpit somam despesas do período, então o pagamento da fatura não é somado como despesa analítica e apenas as despesas detalhadas do cartão entram no total.
- Dado movimentações em múltiplas moedas, quando exibidas, os totais são separados por moeda.
- Dado um planejamento mensal com lançamentos em moedas distintas, quando o Cockpit é exibido, cada seção apresenta subtotal e itens por moeda, sem rotular valores estrangeiros como reais.
- Dado uma categoria com histórico, quando o usuário abre a evolução, o sistema retorna a série mensal do período selecionado.
- Dado o usuário abrindo Demonstrativos, quando escolhe conta, cartão ou visão consolidada, então o relatório mostra apenas despesas daquele escopo no mês, com cabeçalho, KPIs, gráficos, composição, detalhamento e ação de imprimir/exportar.

## Changelog

- `1.4` — 2026-07-26 — Incluída aba de demonstrativos mensais imprimíveis/exportáveis por conta, cartão ou visão consolidada.
- `1.3` — 2026-07-24 — Pagamentos de fatura passam a ser excluídos das análises de despesa para evitar duplicidade com lançamentos detalhados do cartão.
- `1.2` — 2026-07-09 — Planejamento mensal do Cockpit separado por moeda.
- `1.1` — 2026-06-30 — Documentação do endpoint de Cockpit e da evolução temporal por categoria/subcategoria.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[lancamentos]]
- [[cartoes]]
- [[categorias-tags-gestao]]
- [[limites-gastos]]
- [[arquitetura]]
