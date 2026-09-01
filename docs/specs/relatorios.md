---
tipo: spec
area: relatorios
status: implementado
versao: 2.20
atualizado: 2026-08-31
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
> **implementado** · área: `relatorios` · atualizado em 2026-08-31 · relacionados: [[lancamentos]], [[cartoes]], [[categorias-tags-gestao]], [[limites-gastos]]

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
| Tags | Por tag, mostrando receitas, despesas, saldo (receitas menos despesas) e investimentos vinculados à tag; considera lançamentos de contas e cartões, mesmo sem subcategoria. |
| Evolução de categoria | Série mensal por categoria ou subcategoria, com períodos rápidos (`3m`, `6m`, `12m`, `ytd`, `all`). |
| Demonstrativo mensal | Relatório imprimível/exportável por múltiplas contas, múltiplos cartões ou visão consolidada de contas e cartões ativos, com opção de moeda. |

## Regras

- Filtros afetam totais e detalhes simultaneamente.
- Despesas e receitas aparecem separadas no relatório de categorias.
- O relatório de categorias considera lançamentos classificados apenas na categoria principal, mesmo sem subcategoria.
- O relatório de subcategorias agrupa por `Categoria / Subcategoria`.
- O relatório de tags considera lançamentos de contas e cartões com tag, mesmo quando não houver subcategoria.
- O relatório de tags agrupa por tag e exibe, para cada uma, quatro totais separados por moeda: **Receitas**, **Despesas**, **Saldo** (receitas menos despesas) e **Investimentos**.
- Um lançamento com múltiplas tags contribui com o mesmo valor para o total de cada uma das tags.
- Investimentos e aportes aparecem na linha própria de Investimentos do relatório de tags e não são misturados com despesas.
- Transferências, câmbio e pagamentos de fatura não entram no relatório de tags.
- **Lançamentos de cartão entram nos relatórios pela competência da fatura (`invoice_month`), não pela data da compra.** Ver [[cartoes]].
- O KPI **Aportes do mês** da aba Situação do mês exibe a soma dos lançamentos do tipo Investimento/Aporte do mês selecionado (compras, aplicações e aportes registrados em Lançamentos de Contas), com valores de contas em moeda estrangeira convertidos para BRL; posições iniciais cadastradas diretamente no Portfólio e transferências entre contas não entram no valor. O rótulo deve exibir o indicador `i` de ajuda explicando essa origem, no mesmo padrão do KPI Taxa de poupança.
- Pagamentos de fatura gerados em conta-corrente reduzem o saldo da conta, mas não entram em análises de despesa, relatórios por categoria/subcategoria/tag, evolução de categoria nem totais do Cockpit, pois os lançamentos detalhados do cartão já representam o consumo.
- Relatórios exibem totais por moeda quando houver movimentações multimoeda.
- O planejamento do Cockpit separa receitas recorrentes, investimentos planejados e despesas recorrentes por moeda, exibindo os valores originais sem somar moedas distintas.
- O Cockpit deve separar a visão operacional **Situação do mês**, a visão de calendário de vencimentos e atrasos **Calendário**, a visão comparativa **Tendências** e a visão diagnóstica **Saúde Financeira** em abas internas no topo do módulo, evitando que o usuário precise rolar todo o resumo mensal para acessar análises complementares.
- As abas do Cockpit devem aparecer na ordem **Situação**, **Calendário**, **Tendências** e **Saúde Financeira**.
- A aba **Situação do mês** é a visão inicial do Cockpit e mantém KPIs, alertas, saldos por moeda, portfólio por tipo, planejamento, dívidas e gráficos de maiores receitas/despesas.
- A aba **Calendário** é uma visão de vencimentos e atrasos baseada na data atual do servidor, não no mês selecionado no Cockpit.
- O Cockpit deve ter um seletor de mês no topo do módulo, compartilhado pelas abas internas que dependem de competência mensal, começando por **Situação do mês**, **Calendário**, **Tendências** e **Saúde Financeira**.
- O seletor de mês do Cockpit deve seguir o mesmo padrão visual dos seletores mensais de Lançamentos, com botões compactos por ícone para mês anterior, mês atual e próximo mês.
- Rótulos de seletores mensais devem usar o formato compacto `MM/AAAA` para manter largura visual estável.
- Ao trocar o mês do Cockpit, a aba **Situação do mês** deve recalcular KPIs, maiores receitas/despesas, limites, planejamento e totais por moeda com base no mês selecionado. Parcelas em aberto representam o estado atual de liquidação, não uma fotografia histórica; apenas o componente mensal usa a competência selecionada.
- O mês inicial do Cockpit deve ser o mês corrente.
- A leitura do Cockpit para meses passados deve funcionar como fotografia analítica do período, sem esconder despesas de cartão apenas porque a fatura foi paga posteriormente.
- Faturas de cartão devem impactar o Cockpit pela competência da fatura (`invoice_month`) do mês selecionado, preservando o valor da fatura daquele mês tanto em leituras previstas quanto conciliadas quando aplicável.
- Faturas pagas devem continuar aparecendo nos totais analíticos do mês de competência por meio dos lançamentos detalhados do cartão; o pagamento agregado gerado na conta permanece excluído das despesas analíticas para evitar duplicidade.
- O status de pagamento da fatura afeta o saldo operacional da conta de pagamento na data do pagamento, mas não altera retroativamente o consumo analítico do mês da fatura.
- No saldo operacional previsto por moeda do Cockpit, uma fatura paga não produz impacto adicional na linha do cartão: seu pagamento já está refletido no lançamento da conta pagadora. Faturas ainda não pagas continuam reservadas uma única vez, pela conta preferencial quando compatível ou diretamente pelo cartão nos demais casos.
- Os rótulos do Cockpit devem deixar claro quando os valores representam o mês selecionado, usando textos como `Saldo previsto em Julho/2026`, `Saldo conciliado em Julho/2026` ou equivalente, para reduzir ambiguidade com o saldo atual.
- Quando o usuário selecionar mês futuro, o Cockpit deve priorizar planejamento, recorrências, parcelas futuras e faturas previstas; dados realizados inexistentes devem aparecer como zero ou estado vazio, sem simular lançamentos não existentes fora das regras já cadastradas.
- Quando o gráfico **Maiores despesas do mês** exibir a linha agregada `Outros`, essa linha deve permitir abrir um detalhamento com as categorias/subcategorias ocultas no agrupamento e seus respectivos valores. A linha deve exibir, ao lado do rótulo, o indicador `i` discreto (mesmo padrão dos KPIs Taxa de poupança/Aportes do mês) sinalizando que a linha abre o detalhamento em pop-up.
- Percentuais são calculados contra o total da seção.
- Relatório **detalhado** mostra lançamentos individuais.
- Relatório **sintético** mostra apenas agregados.
- A evolução temporal usa `category_id`, `subcategory_id` opcional e período para retornar a série mensal em BRL, total, variação percentual entre primeiro e último ponto e projeção SMA de até 12 meses, calculados no Python. A variação é indisponível se há menos de dois pontos ou o primeiro é zero. A SMA usa até três últimos pontos, incorpora cada previsão na janela seguinte e arredonda para centavos a cada passo (empates para cima, preservando a regra anterior). Os horizontes de 3/6/12 meses e a alternância da projeção apenas selecionam dados já calculados.
- Na falha da evolução, esta versão usa erro explícito: limpa gráfico, total e modelo anterior, sem recalcular pelo histórico local, sem reaproveitar outra categoria/período e sem retry automático. Respostas atrasadas após trocar filtro ou fechar o drawer são descartadas. O fechamento destrói o gráfico e libera os dados do drawer.
- O demonstrativo mensal é calculado no Python a partir dos dados persistidos, respeitando a exclusão de pagamentos de fatura para evitar duplicidade. O navegador recebe seções por moeda, KPIs, rankings, percentuais, composição, série diária e detalhes prontos; não recalcula esses valores nem usa o histórico global em memória como fallback.
- A média diária divide as despesas pelos dias transcorridos no mês corrente, por todos os dias em meses anteriores e por um em meses futuros, preservando a regra vigente; o valor exibido é arredondado para centavos. O relógio de referência é o do servidor local.
- Distribuição por categoria apresenta as cinco maiores e agrupa as restantes em Outros. Percentuais da composição de cada origem usam o total de despesas da seção/moeda, não o subtotal da origem. O detalhamento é ordenado por data crescente e valor decrescente.
- No histograma diário, a seleção continua por competência da fatura, mas a posição é pela data original do lançamento. Compras de outro mês permanecem nos KPIs/composição/detalhes sem serem deslocadas artificialmente para um dia do mês selecionado. A escala considera os totais por data de todos os itens selecionados, preservando a apresentação vigente.
- O demonstrativo pode ser gerado para uma ou mais contas ativas, um ou mais cartões ativos ou a visão consolidada de contas e cartões ativos.
- O usuário pode escolher uma moeda específica cadastrada ou todas as moedas. Quando a visão consolidada usa todas as moedas e há movimentações em mais de uma moeda, o demonstrativo deve gerar seções independentes por moeda, funcionando como múltiplos relatórios no mesmo documento impresso/exportado.
- O demonstrativo deve separar despesas oriundas de conta-corrente e despesas em cartão de crédito nas leituras sintéticas e na composição.
- O detalhamento do demonstrativo deve indicar explicitamente a origem de cada lançamento, incluindo nome da conta ou do cartão.
- O resumo executivo do demonstrativo e o Cockpit exibem **Parcelas em aberto (estado atual)**, calculadas pelo mesmo serviço Python. Inclui despesas parceladas (`series_kind=installment` ou índice/quantidade de parcelas positivos), ativas e de contas/cartões ativos, sem somar moedas distintas.
- Em contas, parcela conciliada é liquidada; parcela não conciliada continua aberta mesmo vencida ou anterior ao mês escolhido. Em cartões, conciliação não liquida a dívida: a existência de pagamento da fatura a encerra, independentemente da data de compra ou do mês escolhido. Pagamentos agregados em conta nunca entram novamente.
- A competência é `date[:7]` em contas e `invoice_month` em cartões. O mês consultado identifica as parcelas daquela competência, mas o estoque aberto inclui competências anteriores e futuras. O estado é o atualmente registrado, não uma reconstrução de pagamentos/conciliações passadas. Atraso usa a data atual do servidor e o vencimento do cartão, limitado ao último dia do mês.
- Pagamento parcial encerra a fatura original e gera saldo avulso na próxima fatura. Sem vínculo estruturado desse saldo com cada compra, o indicador de **parcelas** não o redistribui nem o identifica por descrição. Não representa a dívida total/rotativa; parcelas futuras continuam incluídas até suas respectivas faturas serem pagas.
- Filtros de contas/cartões/moeda são aplicados no backend com isolamento por usuário. Seleção vazia mantém o comportamento de todas as contas/cartões ativos. Falha de consulta não produz zero fictício nem recálculo local; impressão aguarda uma resposta válida.
- Valores monetários do demonstrativo devem usar números tabulares, alinhamento à direita quando em tabela e tamanho de fonte equivalente ao texto descritivo, para manter densidade sem pesar visualmente.
- O demonstrativo deve priorizar impressão/exportação: cabeçalho minimalista com logo, título do mês, escopo, moeda base e data/hora de emissão; KPIs de saídas, média diária, saídas em conta, despesas em cartão, endividamento atual, maior categoria e maior lançamento; gráficos simples para categoria e gastos por dia; tabela de composição por categoria/subcategoria separada por origem; detalhamento com zebra e valores à direita; rodapé com nome do app e página; tipografia e espaçamentos mais densos para papel sem prejudicar leitura.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/cockpit?month=AAAA-MM` |
| `GET` | `/api/reports/open-debts?month=AAAA-MM&account_ids=1,2&card_ids=3&currency=BRL` |
| `GET` | `/api/reports/statement?month=AAAA-MM&account_ids=1,2&card_ids=3&currency=BRL` |
| `GET` | `/api/reports/category-evolution?category_id={id}&subcategory_id={id}&period={periodo}` |

Dados de origem: `transactions`, `credit_card_transactions`, `categories`, `subcategories`, `tags`, `transaction_tags`, `credit_card_transaction_tags`, `checking_accounts`.

Parâmetro do Cockpit:

| Parâmetro | Formato | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Opcional. Quando ausente, usa o mês corrente. Quando informado, orienta todas as leituras mensais do Cockpit. |

Valores aceitos para `periodo`: `3m`, `6m`, `12m`, `ytd` e `all`.

## Proposta em revisão — Cockpit mensal

> Inspiração visual/UX: referência externa indicada pelo usuário em vídeo do YouTube, aproximadamente entre 12:00 e 12:08. Como a referência externa pode não estar disponível para consulta textual permanente, a decisão registrada aqui é descrita pelo comportamento desejado no app, não pelo conteúdo do vídeo.

A proposta é transformar o Cockpit em uma visão mensal navegável por seletor de mês, mantendo a aba **Situação do mês** como leitura operacional do período escolhido e sincronizando **Tendências** e **Saúde Financeira** ao mesmo mês. Essa mudança deve reduzir a dependência do “agora” e permitir revisitar meses fechados com a mesma consistência dos Relatórios.

O ponto crítico é cartão de crédito: a fatura pertence ao mês de competência (`invoice_month`) e deve continuar representando o consumo daquele mês mesmo depois de paga. Portanto, a quitação da fatura não deve apagar nem reduzir a despesa analítica do mês selecionado; ela deve apenas aparecer como efeito operacional no saldo da conta de pagamento.

## Plano de implementação

- [x] Entregar total, tendência e SMA pelo backend preservando a série de competência existente e o contrato `evolution`.
- [x] Remover agregação e projeção local, limpar instâncias/dados na troca ou fechamento e mostrar erro explícito nas falhas.
- [x] Testar série vazia/zero, arredondamento recursivo, horizontes e descarte de respostas obsoletas.

- [x] Montar demonstrativo mensal no Python com filtros de proprietários ativos, competência, moedas e exclusão de pagamentos, reutilizando o serviço de parcelas abertas.
- [x] Transferir KPIs, agrupamentos, percentuais, ranking, série diária e ordenação de detalhes; manter JS apenas como consumidor do modelo, sem fallback financeiro.
- [x] Testar filtros, moedas, precisão, competências e impressão bloqueada durante consulta/falha; verificar remoção dos agregadores do demonstrativo no JS.

- [x] Centralizar leitura, elegibilidade, pagamento, atraso e agregação por moeda em `open_debts.py`, sem rede ou escrita.
- [x] Compartilhar o serviço entre Cockpit e demonstrativo, remover os dois classificadores JS e proteger carregamento/erro/impressão contra respostas obsoletas.
- [x] Testar competência de fatura, conciliação distinta por origem, pagamentos integral/parcial, vencidas, filtros, isolamento e centavos; registrar dívida técnica de SMA/fallback separadamente.

- [x] Identificar pagamentos de fatura em lançamentos de conta pelo vínculo `credit_card_payments.transaction_id`.
- [x] Excluir esses lançamentos apenas das visões analíticas, preservando o impacto no saldo da conta.
- [x] Atualizar Cockpit, Relatórios, evolução de categoria e limites para usar a regra analítica sem duplicidade.
- [x] Cobrir a regra com testes automatizados onde a agregação acontece no backend e validar manualmente as telas.
- [x] Criar aba de demonstrativos no módulo de Relatórios.
- [x] Reaproveitar dados carregados para composição do demonstrativo; parcelas em aberto são consultadas no serviço Python compartilhado, conforme contrato atual.
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
- Dado uma tag com receitas e despesas no mês, quando o relatório de tags é exibido, então a linha da tag mostra Receitas, Despesas, Saldo (receitas menos despesas) e Investimentos separados por moeda.
- Dado um lançamento de investimento com tag, quando o relatório de tags é exibido, então o valor aparece na linha Investimentos da tag e não soma às Despesas.
- Dado uma tag com despesas em BRL e receitas em USD, quando o relatório de tags é exibido, então cada moeda mantém seus próprios totais e o Saldo é calculado dentro de cada moeda.
- Dado uma transferência entre contas com tag, quando o relatório de tags é exibido, então o lançamento não aparece no relatório.
- Dado uma fatura paga no mês, quando relatórios e Cockpit somam despesas do período, então o pagamento da fatura não é somado como despesa analítica e apenas as despesas detalhadas do cartão entram no total.
- Dado movimentações em múltiplas moedas, quando exibidas, os totais são separados por moeda.
- Dado um planejamento mensal com lançamentos em moedas distintas, quando o Cockpit é exibido, cada seção apresenta subtotal e itens por moeda, sem rotular valores estrangeiros como reais.
- Dado uma categoria com histórico, quando o usuário abre a evolução, o sistema retorna a série mensal do período selecionado.
- Dado uma linha `Categoria / Sem subcategoria`, quando o usuário abre sua evolução, então a série considera somente lançamentos com `subcategory_id IS NULL`, preserva a competência da fatura para cartões e apresenta valores normalizados em BRL.
- Dado o usuário abrindo Demonstrativos, quando escolhe contas, cartões ou visão consolidada e opcionalmente uma moeda, então o relatório mostra apenas despesas daquele escopo no mês, com cabeçalho, KPIs, gráficos, composição, detalhamento e ação de imprimir/exportar.
- Dado o usuário gerando um demonstrativo consolidado com todas as moedas, quando houver despesas em mais de uma moeda, então o documento separa o conteúdo em uma seção por moeda, cada uma com seus próprios KPIs, gráficos e tabelas.
- Dado o demonstrativo exibido, quando há despesas de conta e cartão, então o resumo e a composição distinguem as duas origens e o detalhamento mostra a conta ou cartão de cada lançamento.
- Dado o usuário gerando um demonstrativo, quando existem compras parceladas em aberto, então o resumo executivo exibe o endividamento atual da moeda/seção seguindo a mesma regra do Cockpit.
- Dado o demonstrativo exibido ou impresso, quando valores monetários aparecem em KPIs, tabelas e legendas, então a fonte dos valores tem tamanho equivalente ao texto descritivo e não domina visualmente o layout.
- Dado o usuário abrindo o Cockpit, quando a tela é exibida, então vê abas internas para alternar entre **Situação do mês**, **Calendário**, **Tendências** e **Saúde Financeira**, com **Situação do mês** ativa por padrão e nessa ordem.
- Dado o usuário alternando para **Saúde Financeira**, quando a aba é ativada, então o score fica acessível sem exigir rolagem pelo resumo mensal.
- Dado o usuário abrindo o Cockpit, quando a tela é exibida, então o seletor de mês inicia no mês corrente.
- Dado o usuário navegando para outro mês no Cockpit, quando aciona o botão de mês atual, então o Cockpit retorna ao mês corrente.
- Dado o usuário visualizando seletores mensais, quando os botões de navegação aparecem, então usam ícones compactos com rótulo acessível em vez de palavras longas.
- Dado o usuário visualizando o seletor mensal, quando o mês é exibido, então o rótulo usa o formato `MM/AAAA`.
- Dado o usuário selecionando outro mês no Cockpit, quando a aba **Situação do mês** é exibida, então KPIs, saldos, limites, planejamento e gráficos refletem o mês selecionado; parcelas em aberto mantêm o estado atual de liquidação explicitado no rótulo.
- Dado o usuário selecionando outro mês no Cockpit, quando alterna para **Saúde Financeira**, então o score é calculado para o mesmo mês selecionado.
- Dado uma fatura de cartão pertencente ao mês selecionado, quando ela já tiver sido paga, então o Cockpit continua considerando os lançamentos detalhados do cartão como despesa analítica daquele mês.
- Dado uma fatura de cartão paga por lançamento em conta-corrente, quando o Cockpit calcula despesas analíticas do mês, então o pagamento agregado da fatura permanece excluído para evitar duplicidade.
- Dado uma fatura paga em mês posterior ao da competência, quando o usuário consulta o mês da competência, então o consumo da fatura continua aparecendo naquele mês e o pagamento aparece apenas como efeito de saldo na conta pagadora.
- Dado o usuário visualizando saldos no Cockpit com mês diferente do mês corrente, quando os saldos forem exibidos, então os rótulos indicam claramente o mês selecionado.
- Dado o usuário visualizando o Cockpit ou Relatórios em telas de 14 polegadas ou menores, quando os painéis de KPIs, demonstrativos e gráficos são exibidos, então os grids de 4 ou 6 colunas se reorganizam em 2 ou 3 colunas e os gráficos do demonstrativo empilham verticalmente para evitar compressão e quebra de layout.
- Dado o usuário visualizando **Maiores despesas do mês** com a linha `Outros`, quando clica nessa linha, então um pop-up mostra as categorias/subcategorias que compõem `Outros`, com valor de cada item e total agregado, sem alterar os totais do Cockpit.
- Dado o usuário abrindo o gráfico de evolução de uma categoria/subcategoria, quando o drawer é exibido, então a área do gráfico é aproximadamente 20% maior que o tamanho anterior.
- Dado o gráfico de evolução exibido, quando há pontos de dados históricos ou projeção SMA, então cada ponto exibe o respectivo valor formatado, mesmo quando a linha de tendência está ativada.
- Dado uma fatura paga por uma conta em BRL, quando o Cockpit calcula o saldo previsto após a data do pagamento, então considera somente o débito registrado na conta e não subtrai novamente a mesma fatura pela linha do cartão.

### Critérios complementares — dívida aberta

- Parcela de conta não conciliada e vencida continua aberta; conciliada sai do estoque, inclusive se futura.
- Compra parcelada conciliada no cartão continua aberta até o pagamento da fatura; pagamento não duplica a dívida pela conta pagadora.
- Compra antiga com fatura de outra competência usa `invoice_month`; seleção de mês não simula um estado histórico de liquidação.
- Pagamento parcial exclui as parcelas da fatura encerrada, preserva parcelas futuras e não classifica o saldo avulso como parcelamento.
- Contas/cartões de outro usuário, arquivados ou fora dos filtros não contribuem; moedas têm totais independentes em centavos.
- Relatórios e Cockpit usam o mesmo serviço; resposta atrasada de outro filtro não substitui o demonstrativo atual, e falha bloqueia impressão sem repetir a consulta automaticamente.

Validação automatizada: `tests/test_open_debts.py` cobre o domínio e o compartilhamento dos handlers; `tests/frontend_open_debts.test.mjs` cobre respostas obsoletas, troca de abas e falha sem impressão ou retry automático. A conferência visual no Safari e a impressão física permanecem manuais, não executadas nesta etapa. A suíte geral apresentou uma falha independente deste escopo: limite de linhas revisado de `portfolio-view.js` (1.668 versus 1.663).

### Validação do demonstrativo calculado no servidor

- Dadas despesas em BRL e USD, quando o demonstrativo é consultado, então cada seção mantém seus próprios totais em centavos, sem conversão ou soma multimoeda.
- Dados filtros de contas/cartões/moeda, quando aplicados, então KPIs, gráficos e detalhes recebem o mesmo recorte; seleção vazia significa todos os proprietários ativos daquele tipo.
- Dada compra de cartão de outro mês com fatura na competência selecionada, quando a fatura está paga, então o consumo continua no demonstrativo sem somar o pagamento em conta; o histograma preserva a data original.
- Dadas categorias e origens distintas, quando agregadas, então top cinco/Outros, média diária, percentuais da seção e detalhes ordenados são entregues pelo Python.
- Dada falha, payload incompatível ou resposta obsoleta, quando o demonstrativo aguarda dados, então não calcula fallback nem libera impressão de dados inválidos; resposta vazia válida mostra estado vazio.

Cobertura: `tests/test_statement_report.py` e `tests/frontend_open_debts.test.mjs`. Conferência visual no Safari e impressão física permanecem manuais, não executadas nesta etapa. Agregações das demais abas permanecem dívida técnica separada; evolução não usa mais cálculo/fallback local.

## Changelog

<!-- Validação automatizada desta etapa: tests/test_evolution_presentation.py e tests/frontend_evolution.test.mjs. Validação visual no Safari não executada. -->

- `2.20` — 2026-08-31 — Total, tendência e SMA da evolução no Python; erro explícito substitui recálculo local, com descarte do modelo e gráfico anteriores.

- `2.19` — 2026-08-31 — Demonstrativo mensal passa a receber agregações e detalhes do Python; contrato de filtros, moedas, média diária, distribuição e datas do histograma explicitado.


- `2.18` — 2026-08-31 — Definido contrato compartilhado de parcelas em aberto, distinguindo conciliação e pagamento, incluindo vencidas e preservando moedas. Removida autorização de cálculos financeiros em JS; SMA/fallback legados registrados como migração pendente.

- `2.17` — 2026-08-30 — Corrigida a composição do saldo previsto do Cockpit para que faturas já pagas não sejam novamente subtraídas pela linha do cartão após o débito ter sido registrado na conta pagadora.
- `2.16` — 2026-08-28 — Consolidada a correção do relatório de subcategorias: nomes são normalizados antes do agrupamento, linhas sem subcategoria preservam o sentinela `null` até a API, a evolução filtra `subcategory_id IS NULL` e contas/cartões são somados pelos valores normalizados em BRL. Adicionados testes de regressão do filtro nulo, competência de fatura e conversão monetária.
- `2.15` — 2026-08-26 — API de evolução de categoria (`/api/reports/category-evolution`) passou a aceitar `subcategory_id=null|none|-1` para filtrar por `subcategory_id IS NULL`.
- `2.14` — 2026-08-26 — Registrada a investigação da regressão no agrupamento do relatório de subcategorias, consolidada e validada na versão 2.16.
- `2.13` — 2026-08-23 — Relatório de Tags reformulado: cada tag exibe as linhas Receitas, Despesas, Saldo (receitas menos despesas) e Investimentos, separadas por moeda, facilitando o controle de projetos e bens.
- `2.12` — 2026-08-23 — Corrigido agrupamento do relatório de subcategorias: lançamentos sem subcategoria passam a ser separados por categoria, evitando que categorias distintas como Compras e Lazer apareçam sob uma única linha `Assinaturas e Serviços / Sem subcategoria`.
- `2.11` — 2026-08-20 — Sincronizada a data do callout de status com o frontmatter; sem alteração de comportamento.
- `2.10` — 2026-08-07 — A linha agregada `Outros` do gráfico **Maiores despesas do mês** ganha o indicador `i` ao lado do rótulo (mesmo padrão dos KPIs de Taxa de poupança/Aportes do mês), sinalizando que a linha abre o detalhamento em pop-up; o pop-up continua acessível por clique em toda a linha e por teclado.
- `2.9` — 2026-08-07 — KPI **Aportes do mês** da aba Situação do mês ganha indicador `i` de ajuda (mesmo padrão do KPI Taxa de poupança) explicando a origem do valor: soma dos lançamentos do tipo Investimento/Aporte do mês selecionado, com conversão para BRL quando a conta é em outra moeda, excluindo posições iniciais cadastradas no Portfólio e transferências entre contas.
- `2.8` — 2026-08-06 — Drawer de evolução de categoria ampliado em aproximadamente 20%; gráfico passa a exibir o valor formatado em cada ponto, inclusive nos pontos projetados pela linha de tendência SMA.
- `2.7` — 2026-08-04 — Adicionada aba **Calendário** ao Cockpit na ordem **Situação**, **Calendário**, **Tendências** e **Saúde Financeira**. A nova aba é documentada na spec [[cockpit-calendario]].
- `2.6` — 2026-08-04 — Linha `Outros` em Maiores despesas do mês passa a abrir detalhamento em pop-up com os itens agregados.
- `2.5` — 2026-08-02 — Ordem das abas do Cockpit documentada como Situação, Tendências e Saúde Financeira, alinhando Relatórios/Cockpit à spec de Tendências.
- `2.4` — 2026-08-02 — Cockpit e Relatórios ganham ajustes responsivos para telas de 14 polegadas (e breakpoints intermediários): KPIs de 4/6 colunas passam para 2/3 colunas, gráficos do demonstrativo empilham verticalmente e o demonstrativo evita compressão em viewports intermediárias.
- `2.3` — 2026-08-02 — Rótulos dos seletores mensais passam a usar formato fixo `MM/AAAA` para manter largura visual estável.
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
