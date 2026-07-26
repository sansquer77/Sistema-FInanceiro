---
tipo: spec
area: relatorios
status: implementado
versao: 1.7
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
| Demonstrativo mensal | Relatório imprimível/exportável por múltiplas contas, múltiplos cartões ou visão consolidada de contas e cartões ativos, com opção de moeda. |

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
- O demonstrativo pode ser gerado para uma ou mais contas ativas, um ou mais cartões ativos ou a visão consolidada de contas e cartões ativos.
- O usuário pode escolher uma moeda específica cadastrada ou todas as moedas. Quando a visão consolidada usa todas as moedas e há movimentações em mais de uma moeda, o demonstrativo deve gerar seções independentes por moeda, funcionando como múltiplos relatórios no mesmo documento impresso/exportado.
- O demonstrativo deve separar despesas oriundas de conta-corrente e despesas em cartão de crédito nas leituras sintéticas e na composição.
- O detalhamento do demonstrativo deve indicar explicitamente a origem de cada lançamento, incluindo nome da conta ou do cartão.
- O resumo executivo do demonstrativo deve incluir endividamento atual, seguindo a mesma regra do Cockpit para compras parceladas em aberto.
- Valores monetários do demonstrativo devem usar números tabulares, alinhamento à direita quando em tabela e tamanho de fonte equivalente ao texto descritivo, para manter densidade sem pesar visualmente.
- O demonstrativo deve priorizar impressão/exportação: cabeçalho minimalista com logo, título do mês, escopo, moeda base e data/hora de emissão; KPIs de saídas, média diária, saídas em conta, despesas em cartão, endividamento atual, maior categoria e maior lançamento; gráficos simples para categoria e gastos por dia; tabela de composição por categoria/subcategoria separada por origem; detalhamento com zebra e valores à direita; rodapé com nome do app e página; tipografia e espaçamentos mais densos para papel sem prejudicar leitura.

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
- [x] Permitir seleção múltipla de contas e cartões para demonstrativos específicos.
- [x] Permitir filtro por moeda cadastrada ou todas as moedas.
- [x] Quebrar o demonstrativo consolidado multimoeda em seções independentes por moeda.
- [x] Densificar tipografia e espaçamento do demonstrativo para impressão.
- [x] Separar despesas de conta e cartão na composição e nos KPIs do demonstrativo.
- [x] Incluir origem detalhada com nome da conta/cartão no detalhamento.
- [x] Incluir endividamento atual no resumo executivo usando a regra de parcelados em aberto do Cockpit.
- [x] Igualar o tamanho visual dos valores ao texto descritivo no demonstrativo.

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
- Dado o usuário abrindo Demonstrativos, quando escolhe contas, cartões ou visão consolidada e opcionalmente uma moeda, então o relatório mostra apenas despesas daquele escopo no mês, com cabeçalho, KPIs, gráficos, composição, detalhamento e ação de imprimir/exportar.
- Dado o usuário gerando um demonstrativo consolidado com todas as moedas, quando houver despesas em mais de uma moeda, então o documento separa o conteúdo em uma seção por moeda, cada uma com seus próprios KPIs, gráficos e tabelas.
- Dado o demonstrativo exibido, quando há despesas de conta e cartão, então o resumo e a composição distinguem as duas origens e o detalhamento mostra a conta ou cartão de cada lançamento.
- Dado o usuário gerando um demonstrativo, quando existem compras parceladas em aberto, então o resumo executivo exibe o endividamento atual da moeda/seção seguindo a mesma regra do Cockpit.
- Dado o demonstrativo exibido ou impresso, quando valores monetários aparecem em KPIs, tabelas e legendas, então a fonte dos valores tem tamanho equivalente ao texto descritivo e não domina visualmente o layout.

## Changelog

- `1.7` — 2026-07-26 — Valores monetários do demonstrativo passam a usar tamanho de fonte equivalente ao texto descritivo para melhorar densidade visual.
- `1.6` — 2026-07-26 — Demonstrativos passam a separar despesas de conta e cartão, mostrar origem no detalhamento e incluir endividamento atual.
- `1.5` — 2026-07-26 — Demonstrativos passam a aceitar múltiplas contas/cartões, filtro por moeda e seções independentes por moeda no consolidado multimoeda, com layout de impressão mais denso.
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
