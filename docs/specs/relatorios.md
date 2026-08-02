---
tipo: spec
area: relatorios
status: implementado
versao: 2.2
atualizado: 2026-08-02
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
> **implementado** · área: `relatorios` · atualizado em 2026-08-02 · relacionados: [[lancamentos]], [[cartoes]], [[categorias-tags-gestao]], [[limites-gastos]]

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
- O Cockpit deve separar a visão operacional **Situação do mês** e a visão diagnóstica **Saúde Financeira** em abas internas no topo do módulo, evitando que o usuário precise rolar todo o resumo mensal para acessar o score.
- A aba **Situação do mês** é a visão inicial do Cockpit e mantém KPIs, alertas, saldos por moeda, portfólio por tipo, planejamento, dívidas e gráficos de maiores receitas/despesas.
- O Cockpit deve ter um seletor de mês no topo do módulo, compartilhado pelas abas internas que dependem de competência mensal, começando por **Situação do mês** e **Saúde Financeira**.
- O seletor de mês do Cockpit deve seguir o mesmo padrão visual dos seletores mensais de Lançamentos, com botões compactos por ícone para mês anterior, mês atual e próximo mês.
- Ao trocar o mês do Cockpit, a aba **Situação do mês** deve recalcular KPIs, maiores receitas/despesas, limites, planejamento, dívidas e totais por moeda com base no mês selecionado.
- O mês inicial do Cockpit deve ser o mês corrente.
- A leitura do Cockpit para meses passados deve funcionar como fotografia analítica do período, sem esconder despesas de cartão apenas porque a fatura foi paga posteriormente.
- Faturas de cartão devem impactar o Cockpit pela competência da fatura (`invoice_month`) do mês selecionado, preservando o valor da fatura daquele mês tanto em leituras previstas quanto conciliadas quando aplicável.
- Faturas pagas devem continuar aparecendo nos totais analíticos do mês de competência por meio dos lançamentos detalhados do cartão; o pagamento agregado gerado na conta permanece excluído das despesas analíticas para evitar duplicidade.
- O status de pagamento da fatura afeta o saldo operacional da conta de pagamento na data do pagamento, mas não altera retroativamente o consumo analítico do mês da fatura.
- Os rótulos do Cockpit devem deixar claro quando os valores representam o mês selecionado, usando textos como `Saldo previsto em Julho/2026`, `Saldo conciliado em Julho/2026` ou equivalente, para reduzir ambiguidade com o saldo atual.
- Quando o usuário selecionar mês futuro, o Cockpit deve priorizar planejamento, recorrências, parcelas futuras e faturas previstas; dados realizados inexistentes devem aparecer como zero ou estado vazio, sem simular lançamentos não existentes fora das regras já cadastradas.
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

Parâmetro do Cockpit:

| Parâmetro | Formato | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Opcional. Quando ausente, usa o mês corrente. Quando informado, orienta todas as leituras mensais do Cockpit. |

Valores aceitos para `periodo`: `3m`, `6m`, `12m`, `ytd` e `all`.

## Proposta em revisão — Cockpit mensal

> Inspiração visual/UX: referência externa indicada pelo usuário em vídeo do YouTube, aproximadamente entre 12:00 e 12:08. Como a referência externa pode não estar disponível para consulta textual permanente, a decisão registrada aqui é descrita pelo comportamento desejado no app, não pelo conteúdo do vídeo.

A proposta é transformar o Cockpit em uma visão mensal navegável por seletor de mês, mantendo a aba **Situação do mês** como leitura operacional do período escolhido e a aba **Saúde Financeira** sincronizada ao mesmo mês. Essa mudança deve reduzir a dependência do “agora” e permitir revisitar meses fechados com a mesma consistência dos Relatórios.

O ponto crítico é cartão de crédito: a fatura pertence ao mês de competência (`invoice_month`) e deve continuar representando o consumo daquele mês mesmo depois de paga. Portanto, a quitação da fatura não deve apagar nem reduzir a despesa analítica do mês selecionado; ela deve apenas aparecer como efeito operacional no saldo da conta de pagamento.

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
- [x] Avaliar e implementar seletor mensal no topo do Cockpit, com mês corrente como padrão.
- [x] Sincronizar **Situação do mês** e **Saúde Financeira** com o mês selecionado.
- [x] Revisar agregações do Cockpit para garantir que faturas de cartão pagas continuem consideradas por `invoice_month`.
- [x] Revisar rótulos de saldo para explicitar o mês selecionado e evitar ambiguidade com saldo atual.
- [x] Criar testes automatizados para Cockpit mensal, especialmente fatura paga em mês selecionado e exclusão do pagamento agregado.

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
- Dado o usuário abrindo o Cockpit, quando a tela é exibida, então vê abas internas para alternar entre **Situação do mês** e **Saúde Financeira**, com **Situação do mês** ativa por padrão.
- Dado o usuário alternando para **Saúde Financeira**, quando a aba é ativada, então o score fica acessível sem exigir rolagem pelo resumo mensal.
- Dado o usuário abrindo o Cockpit, quando a tela é exibida, então o seletor de mês inicia no mês corrente.
- Dado o usuário navegando para outro mês no Cockpit, quando aciona o botão de mês atual, então o Cockpit retorna ao mês corrente.
- Dado o usuário visualizando seletores mensais, quando os botões de navegação aparecem, então usam ícones compactos com rótulo acessível em vez de palavras longas.
- Dado o usuário selecionando outro mês no Cockpit, quando a aba **Situação do mês** é exibida, então KPIs, saldos, limites, planejamento, dívidas e gráficos refletem o mês selecionado.
- Dado o usuário selecionando outro mês no Cockpit, quando alterna para **Saúde Financeira**, então o score é calculado para o mesmo mês selecionado.
- Dado uma fatura de cartão pertencente ao mês selecionado, quando ela já tiver sido paga, então o Cockpit continua considerando os lançamentos detalhados do cartão como despesa analítica daquele mês.
- Dado uma fatura de cartão paga por lançamento em conta-corrente, quando o Cockpit calcula despesas analíticas do mês, então o pagamento agregado da fatura permanece excluído para evitar duplicidade.
- Dado uma fatura paga em mês posterior ao da competência, quando o usuário consulta o mês da competência, então o consumo da fatura continua aparecendo naquele mês e o pagamento aparece apenas como efeito de saldo na conta pagadora.
- Dado o usuário visualizando saldos no Cockpit com mês diferente do mês corrente, quando os saldos forem exibidos, então os rótulos indicam claramente o mês selecionado.

## Changelog

- `2.2` — 2026-08-02 — Seletor mensal do Cockpit padronizado com os seletores de Lançamentos, incluindo botão de mês atual e botões compactos por ícone.
- `2.1` — 2026-08-02 — Implementado seletor mensal no Cockpit, sincronizando Situação do mês e Saúde Financeira e preservando faturas por competência mesmo após pagamento.
- `2.0` — 2026-08-02 — Spec colocada em revisão para avaliar Cockpit com seletor mensal, mantendo faturas de cartão por competência mesmo após pagamento e exigindo rótulos de saldo vinculados ao mês selecionado.
- `1.9` — 2026-07-31 — Aba operacional do Cockpit renomeada de `Resumo financeiro` para `Situação do mês` para evitar repetição com o título da página.
- `1.8` — 2026-07-31 — Cockpit passa a separar Resumo financeiro e Saúde Financeira em abas internas no topo do módulo.
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
