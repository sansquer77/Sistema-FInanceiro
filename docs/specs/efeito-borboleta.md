---
tipo: spec
area: simulacoes
status: implementado
versao: 1.9
atualizado: 2026-09-04
relacionados:
  - "[[contas-correntes]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[limites-gastos]]"
  - "[[relatorios]]"
  - "[[arquitetura]]"
tags: [spec, "area/simulacoes", "status/implementado"]
aliases: ["Efeito Borboleta", "Simulador Financeiro"]
---

# Efeito Borboleta

> [!info] Status
> **implementado** · área: `simulacoes` · atualizado em 2026-09-04 · relacionados: [[contas-correntes]], [[lancamentos]], [[cartoes]], [[limites-gastos]], [[relatorios]]

## Problema

O usuário precisa avaliar o impacto de uma possível receita ou despesa antes de assumir o compromisso financeiro, sem criar lançamentos reais, alterar saldos, afetar faturas ou poluir relatórios históricos.

## Usuário

Qualquer usuário autenticado localmente que queira testar cenários financeiros hipotéticos, como uma compra planejada, uma renda extra, uma despesa emergencial ou a antecipação de uma decisão de consumo.

## Jornada

1. O usuário abre o módulo Efeito Borboleta a partir do Cockpit, Relatórios ou Lançamentos.
2. Informa um cenário hipotético com tipo, valor, data, conta e, quando necessário, parcelamento ou recorrência.
3. O sistema valida os dados usando as mesmas regras de domínio dos lançamentos reais.
4. O sistema calcula o impacto projetado sem gravar nenhum lançamento.
5. O usuário visualiza comparativos entre a situação atual e o cenário simulado.
6. O usuário descarta a simulação ao sair, limpar o formulário ou iniciar outro cenário.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `type` | enum | Obrigatório. Valores iniciais: `income` ou `expense`. |
| `amount` | inteiro (centavos) | Obrigatório. Deve ser maior que zero. |
| `date` | ISO `YYYY-MM-DD` | Obrigatório. Define o mês de competência da simulação. |
| `account_id` | FK | Obrigatório para simulações em conta-corrente. Deve pertencer ao usuário autenticado. |
| `series_kind` | enum | Obrigatório. Valores: `single`, `installment` ou `recurring`. |
| `installment_count` | inteiro | Obrigatório quando `series_kind = installment`. Deve ser maior que 1. |
| `recurrence_frequency` | enum | Obrigatório quando `series_kind = recurring`. Valores iniciais: `monthly`. |
| `recurrence_count` | inteiro | Opcional quando `series_kind = recurring`. Define a quantidade de ocorrências simuladas e deve ser maior que 1. Quando não informado, o sistema assume 120 ocorrências automaticamente. |

## Regras

- A simulação não cria, edita ou exclui registros financeiros.
- A simulação não altera `checking_accounts.current_balance_cents`.
- A simulação não cria registros em `transactions`, `credit_card_transactions`, `credit_card_payments` ou tabelas de vínculo de tags.
- O cálculo deve tratar o cenário como um lançamento virtual mantido apenas em memória.
- Receitas simuladas aumentam o saldo projetado da conta escolhida.
- Despesas simuladas reduzem o saldo projetado da conta escolhida.
- O saldo atual exibido deve permanecer igual ao saldo conciliado real da conta, sem somar valores simulados.
- O card **Saldo projetado no mês** deve partir do saldo previsto da conta no fim do mês de simulação e somar apenas o impacto virtual cujo mês de competência é o mês da simulação; ocorrências de meses futuros da série continuam refletidas no gráfico e nos totais por mês (`month_impact`), mas não no card.
- O cenário deve respeitar a moeda da conta selecionada.
- Totais multimoeda devem continuar separados por moeda, sem conversão implícita para somatórios financeiros.
- O formulário de simulação não deve solicitar descrição, categoria ou subcategoria, pois o cenário é efêmero e não é persistido como lançamento.
- Relatórios e gráficos simulados devem identificar visualmente os valores hipotéticos.
- O usuário deve conseguir descartar a simulação sem confirmação, pois nenhum dado real foi alterado.
- O módulo deve funcionar sem qualquer LLM, API externa ou interpretação por linguagem natural.
- A entrada principal deve ser um formulário estruturado com campos financeiros explícitos.
- Lançamentos parcelados simulados devem distribuir o impacto em parcelas mensais a partir da data inicial.
- Lançamentos recorrentes simulados devem distribuir o impacto mensalmente pelo horizonte informado.
- No formulário de simulação, o modo **Recorrente** não exibe campo de quantidade de ocorrências — a série assume 120 ocorrências automaticamente (mesma regra dos lançamentos reais); a contagem de repetições do formulário fica exclusiva do modo **Parcelada**, expressa como campo *Parcelas*.
- A primeira entrega aceita apenas recorrência mensal (`monthly`); outras frequências devem ser rejeitadas até serem implementadas explicitamente.
- Cada parcela ou ocorrência recorrente deve ser tratada como um item virtual independente na projeção.
- Os itens virtuais (parcelas e ocorrências) permanecem no contrato da API (`virtual_items`), mas **não devem ser listados na interface**: abaixo do gráfico o usuário vê a projeção diária e os alertas.
- O impacto de limites de gastos só deve ser calculado quando o payload legado informar categoria; a experiência principal sem classificação deve omitir alertas de limite.
- Gráficos e totais devem mostrar o efeito acumulado ao longo dos meses afetados pela série simulada.
- O horizonte do gráfico deve ser sempre de 5 meses, sendo o mês atual da simulação mais 4 meses projetados.
- A série do gráfico deve usar a mesma base de saldo previsto da conta-corrente, incluindo faturas conciliadas e não pagas de cartões vinculados como conta preferencial, e aplicar apenas os itens virtuais da simulação por cima dessa base.
- O gráfico deve comparar a linha de saldo previsto da conta com a linha de saldo com simulação, usando legenda visual e sem transformar valores simulados em lançamentos reais.
- Valores financeiros extensos no gráfico devem se adaptar ao espaço disponível reduzindo a tipografia, sem ampliar os cards nem truncar centavos.
- Abaixo do gráfico deve haver uma projeção diária com 15 pontos, permitindo identificar o dia exato em que o saldo previsto ou simulado fica negativo.
- Os cards mensais ocupam uma faixa acima do gráfico, sem sobreposição. A área cresce verticalmente para acomodar cards, gráfico, legenda e tabela diária nesta ordem. Em larguras menores, a comparação mensal permite rolagem horizontal interna.
- Quando a data do cenário estiver entre hoje e os próximos 14 dias, a janela diária deve cobrir hoje mais os 14 dias seguintes.
- Quando a data do cenário estiver além dos próximos 14 dias, a janela deve cobrir os 7 dias anteriores, a data do cenário e os 7 dias posteriores.
- Quando a data do cenário estiver no passado, a janela deve cobrir hoje mais os 14 dias seguintes e considerar o impacto virtual como já ocorrido.
- A projeção diária deve exibir **Previsto**, **Simulado** e **Diferença**, considerando em cada corte o impacto acumulado dos itens virtuais com data igual ou anterior.
- O resultado deve informar a primeira data negativa prevista, a primeira data negativa simulada e se o cenário **causa saldo negativo**, **evita saldo negativo** ou não altera essa condição dentro da janela.
- Quando o cenário for uma série parcelada ou recorrente, a projeção deve refletir cada ocorrência virtual que caia dentro da janela diária.
- A view deve resolver o contêiner da projeção diária por injeção e, como compatibilidade durante atualização de arquivos estáticos, tentar localizá-lo no DOM; sua ausência não pode interromper o restante da simulação.

## API e dados

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/api/simulations/butterfly-effect` | Recebe um cenário hipotético validado e retorna projeções comparativas sem persistir dados. |

Tabelas consultadas: `checking_accounts`, `transactions`, `categories`, `subcategories`, `spending_limits`, `credit_card_transactions`, `credit_card_payments`.

Tabelas criadas ou alteradas: nenhuma.

Resposta esperada:

| Campo | Descrição |
|---|---|
| `scenario` | Cenário normalizado usado no cálculo. |
| `account_impact` | Saldo conciliado atual, saldo previsto no fim do mês de simulação somado apenas ao impacto virtual do mês da simulação, diferença entre os dois e total virtual do mês. |
| `month_impact` | Totais reais, totais simulados e resultado projetado do mês. |
| `limit_impact` | Consumo real e consumo simulado quando o payload legado repassar classificação; vazio na experiência principal sem categoria. |
| `chart_series` | Série mensal comparando situação atual e cenário simulado. |
| `daily_projection` | Projeção diária com 15 pontos, contendo saldo previsto, simulado e diferença. |
| `daily_projection_summary` | Primeiras datas negativas nas duas trajetórias e efeito do cenário sobre o risco de caixa. |
| `weekly_projection` | Alias transitório de `daily_projection` para compatibilidade com arquivos estáticos anteriores. |
| `virtual_items` | Lista de parcelas ou ocorrências virtuais usadas para calcular a projeção. Permanência no contrato da API; não é listada na interface. |
| `warnings` | Alertas não bloqueantes, como saldo projetado negativo ou limite ultrapassado. |

## Critérios de aceite

- Dado uma conta com saldo de R$ 1.000,00, quando o usuário simula uma despesa de R$ 250,00, então o sistema mostra saldo projetado de R$ 750,00 sem alterar o saldo real da conta.
- Dado uma conta com saldo de R$ 1.000,00, quando o usuário simula uma receita de R$ 300,00, então o sistema mostra saldo projetado de R$ 1.300,00 sem criar lançamento.
- Dado uma simulação de despesa sem categoria, quando o usuário envia o cenário, então o sistema calcula o saldo projetado sem exigir classificação financeira.
- Dado uma simulação descartada, quando o usuário volta ao Cockpit, Contas, Lançamentos ou Relatórios, então nenhum dado real foi alterado.
- Dado uma conta em moeda estrangeira, quando o usuário simula uma despesa nessa conta, então o impacto é exibido na moeda da conta sem somar o valor a totais de outra moeda.
- Dado uma simulação com valor inválido ou conta inexistente, quando enviada, então a API retorna erro amigável e nenhuma projeção é calculada.
- Dado uma simulação válida, quando exibida em gráfico, então a série diferencia visualmente valores reais e valores simulados.
- Dado o app sem internet, quando o usuário abre o módulo, então a criação e visualização da simulação continuam disponíveis.
- Dado uma despesa parcelada de R$ 1.200,00 em 12 vezes, quando simulada, então o sistema distribui R$ 100,00 por mês na projeção e mostra o impacto acumulado nos meses afetados.
- Dado uma receita recorrente mensal de R$ 500,00 por 6 meses, quando simulada, então o sistema mostra seis ocorrências virtuais e atualiza o saldo projetado mês a mês.
- Dado uma simulação recorrente sem informar a quantidade de ocorrências, quando enviada, então o sistema assume 120 ocorrências automaticamente e não exibe erro.
- Dado um cenário **Recorrente** no formulário de simulação, quando o modo é selecionado, então o formulário não exibe campo de ocorrências e o campo *Parcelas* permanece exclusivo do modo **Parcelada**.
- Dado uma simulação com payload legado categorizado, quando há limites cadastrados nos meses afetados, então cada ocorrência impacta apenas o limite do seu mês de competência.
- Dado uma conta preferencial de pagamento com fatura de cartão conciliada e não paga, quando o usuário simula um cenário nessa conta, então o gráfico parte do saldo previsto da conta com a fatura abatida e adiciona somente os valores simulados.
- Dado qualquer cenário válido, quando o resultado é exibido, então o saldo atual permanece igual ao saldo conciliado real da conta.
- Dado qualquer cenário válido, quando o gráfico é exibido, então ele mostra 5 meses e compara saldo previsto da conta contra saldo com simulação.
- Dado uma simulação com valor projetado muito extenso, quando o gráfico é exibido, então os valores cabem nos cards do gráfico por ajuste responsivo de tipografia, mantendo o tamanho dos cards.
- Dado uma simulação recorrente de 120 ocorrências, quando o card **Saldo projetado no mês** é exibido, então o valor considera apenas o impacto virtual do mês da simulação, sem somar ocorrências dos meses futuros da série.
- Dado uma despesa única para daqui a 10 dias, quando a projeção diária é exibida, então previsto e simulado permanecem iguais nos 10 primeiros cortes e divergem a partir da data da despesa.
- Dado um cenário dentro dos próximos 14 dias, quando a projeção é calculada, então ela contém hoje e cada um dos 14 dias seguintes.
- Dado um cenário além dos próximos 14 dias, quando a projeção é calculada, então ela contém 7 dias antes e 7 dias depois da data do cenário.
- Dado uma despesa que torna o saldo negativo, quando a projeção é exibida, então a primeira data negativa simulada é informada e o efeito é `causes_negative`.
- Dado uma receita que evita um saldo negativo previsto, quando a projeção é exibida, então o efeito é `avoids_negative` e as duas primeiras datas negativas são informadas quando aplicável.
- Dado uma simulação válida, quando a projeção diária é renderizada, então ela possui 15 colunas e três linhas: Previsto, Simulado e Diferença.
- Dado `simulations-view.js` atualizado com um `app.js` ou HTML anterior ainda em cache, quando o contêiner semanal não é injetado ou não existe, então a simulação continua renderizando os demais resultados sem erro de JavaScript.
- Dado o módulo aberto sem simulação válida, quando a tela é exibida, então as seções de resultados, gráfico, projeção e alertas permanecem ocultas e um único estado informativo orienta o usuário.

- Dado um cenário exibido, quando o comparativo é renderizado, então os cards mensais ficam acima da área exclusiva do gráfico e a tabela diária permanece abaixo da legenda, sem sobreposição (estrutura automatizada; aparência em Safari requer validação manual).

## Fora de escopo

- Uso de LLM local, Gemini ou qualquer API externa para interpretar texto livre.
- Criação automática de lançamentos reais a partir de uma simulação.
- Persistência de cenários simulados, histórico de simulações ou comparação entre múltiplos cenários salvos.
- Simulações de transferências, câmbio, investimentos, resgates e encerramentos de posições.
- Simulações avançadas de cartão de crédito e fatura na primeira entrega.
- Recomendações financeiras automáticas ou aconselhamento financeiro personalizado.

## Plano de implementação

- [x] Passo 6 — Separar cards e plot em linhas de layout, manter tabela no fluxo e verificar o contrato de apresentação. Fecha: critério 26. Teste estrutural automatizado aprovado; validação visual no Safari pendente.
- [x] Passo 1 — Preservar o núcleo determinístico, isolamento, moedas, validações e projeção mensal existentes. Fecha: critérios 1–18.
- [x] Passo 2 — Substituir os cortes semanais por janela diária dinâmica e resumo de risco no backend. Fecha: critérios 19–24.
- [x] Passo 3 — Renderizar a linha do tempo diária e mensagens de causa/prevenção de saldo negativo no frontend. Fecha: critérios 19, 22–24.
- [x] Passo 4 — Manter fallback de arquivos estáticos e alias de payload durante atualização. Fecha: critério 25.
- [x] Passo 5 — Cobrir janelas próxima/distante, impacto na data e classificação do risco por testes automatizados. Fecha: critérios 19–25.

## Changelog

- `1.9` — 2026-09-04 — Resultado inicial usa um único estado informativo; conteúdo dependente fica oculto até simulação válida.

- `1.8` — 2026-08-31 — Comparativo mensal com cards acima do gráfico e tabela diária abaixo; rolagem horizontal interna em áreas estreitas. Corrigida descrição antiga que omitia a tabela abaixo do gráfico.
- `1.7` — 2026-08-30 — Dados auxiliares de contas passam a usar cache curto, in-flight compartilhado, invalidação após mutações e reset entre sessões.
- `1.6` — 2026-08-30 — Iniciado reaproveitamento dos dados auxiliares do formulário com invalidação após mutações.
- `1.5` — 2026-08-28 — Projeção semanal substituída por linha do tempo diária de 15 pontos, com janela deslocada para cenários distantes e identificação da primeira data negativa e do efeito de causar ou evitar saldo negativo.
- `1.4` — 2026-08-28 — A tabela semanal ganha resolução de elemento compatível com versões transitórias dos arquivos estáticos e deixa de interromper toda a simulação quando o contêiner não foi injetado.
- `1.3` — 2026-08-23 — Adicionada tabela de projeção semanal abaixo do gráfico: saldo atual mais 8 semanas, com linhas Previsto, Simulado e Diferença.
- `1.2` — 2026-08-09 — Spec promovida para **implementado** na documentação do app.
- `1.1` — 2026-08-07 — Tópico **Saúde Financeira** (comparativo nota atual vs projetada dos 5 pilares) retirado da interface e do backend por decisão de validação; permanece apenas o card **Saldo projetado no mês** com impacto do mês da simulação.
- `1.0` — 2026-08-07 — Resultado da simulação passa a ser um comparativo de cenário: o card **Saldo projetado no mês** passa a considerar apenas o impacto virtual do mês da simulação (séries de 120 ocorrências não mais inflam o card); a lista de itens virtuais é removida da interface (campo permanece no contrato da API); novo bloco **Saúde Financeira** compara a nota atual e a nota projetada dos 5 pilares no mês do cenário, recalculando com os valores simulados apenas os pilares sensíveis a receitas/despesas mensais.
- `0.9` — 2026-08-07 — Formulário de simulação: campo de ocorrências removido do modo **Recorrente** (série sempre assume 120 ocorrências, sem campo visível); a contagem de repetições fica exclusiva do modo **Parcelada** (campo *Parcelas*). O backend continua aceitando `recurrence_count` legado com default 120.
- `0.8` — 2026-08-06 — Simulações recorrentes passam a usar 120 ocorrências automaticamente quando a quantidade não é informada, evitando erro de campo obrigatório.
- `0.7` — 2026-07-24 — Gráfico da simulação passa a adaptar valores financeiros extensos ao espaço disponível sem ampliar a área visual.
- `0.6` — 2026-07-24 — Simulação passa a ser um cenário financeiro puro: formulário sem descrição, categoria ou subcategoria; classificação fica apenas como compatibilidade de payload legado.
- `0.5` — 2026-07-06 — Resultado separa saldo atual real de saldo projetado; gráfico passa a comparar previsão da conta e cenário simulado em horizonte fixo de 5 meses.
- `0.4` — 2026-07-06 — Gráfico da simulação passa a usar a mesma base de saldo previsto das contas, incluindo faturas conciliadas e não pagas de cartão.
- `0.3` — 2026-07-05 — Campo de recorrência alinhado à implementação (`recurrence_count`) e recorrência mensal definida como única frequência aceita na primeira entrega.
- `0.2` — 2026-07-05 — Parcelamento e recorrência entram no escopo principal da simulação por serem cenários de maior impacto financeiro.
- `0.1` — 2026-07-05 — Spec inicial em rascunho para o módulo Efeito Borboleta, com núcleo determinístico e sem LLM.

## Relacionados

- [[contas-correntes]]
- [[lancamentos]]
- [[cartoes]]
- [[limites-gastos]]
- [[relatorios]]
- [[arquitetura]]
