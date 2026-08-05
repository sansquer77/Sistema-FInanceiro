---
tipo: spec
area: score-saude-financeira
status: implementado
versao: 3.2
atualizado: 2026-08-04
relacionados:
  - "[[relatorios]]"
  - "[[limites-gastos]]"
  - "[[investimentos-portfolio]]"
  - "[[cartoes]]"
  - "[[contas-correntes]]"
  - "[[arquitetura]]"
tags: [spec, "area/score-saude-financeira", "status/implementado"]
aliases: ["Score de Saúde Financeira", "Diagnóstico Financeiro", "Financial Health Score"]
---

# Score de Saúde Financeira

> [!info] Status
> **implementado** · área: `score-saude-financeira` · atualizado em 2026-08-04 · relacionados: [[relatorios]], [[limites-gastos]], [[investimentos-portfolio]], [[cartoes]], [[contas-correntes]]

## Problema

O usuário possui dados de contas, lançamentos, cartões, limites de gastos e investimentos espalhados pelo sistema, mas não conta com um indicador síntese (pontuação de 0 a 1000) que avalie seu estado financeiro geral nem orientações claras sobre quais pilares precisam de atenção.

## Usuário

Qualquer usuário autenticado localmente que deseje entender sua saúde financeira através de um diagnóstico consolidado e acionável.

## Jornada

1. O usuário acessa o **Cockpit** e clica na aba dedicada de **Saúde Financeira**.
2. O sistema calcula e exibe a pontuação total (0 a 1000) do mês consultado em um velocímetro/gauge de diagnóstico, categorizada em níveis (Crítico, Vulnerável/Atenção, Moderado/Em construção, Excelente/Sólido).
3. O usuário visualiza um gráfico compacto de pilares, permitindo perceber rapidamente quais dimensões puxam o score para cima ou para baixo.
4. O usuário visualiza o detalhamento dos 5 pilares do score com seus pesos aprovados (Poupança 25%, Reserva 25%, Endividamento 20%, Limites 15%, Concentração da Carteira 15%) em cards expansíveis, permitindo leitura em camadas.
5. O usuário visualiza a seção informativa **Paz Financeira**, com referências simples para nortear o planejamento de independência, reserva, despesas recorrentes e lazer em cards expansíveis.
6. O usuário pode consultar o histórico mensal da evolução do seu score e visualizar plano de ação com recomendações sem poluição visual do painel principal do Cockpit.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Obrigatório. Mês de referência da avaliação. |
| `score_total` | inteiro | Pontuação consolidada entre `0` e `1000`. |
| `nivel` | texto | Categoria visual normalizada: `critico` (0-299), `atencao` (300-499), `bom` (500-749), `excelente` (750-1000). |
| `pilar_poupanca` | inteiro | Pontuação da Taxa de Poupança (0 a 250 pontos; peso 25%). |
| `pilar_reserva` | inteiro | Pontuação da Reserva de Emergência (0 a 250 pontos; peso 25%). |
| `pilar_endividamento` | inteiro | Pontuação do Comprometimento de Renda (0 a 200 pontos; peso 20%). |
| `pilar_limites` | inteiro | Pontuação de Aderência aos Limites de Gastos (0 a 150 pontos; peso 15%). |
| `pilar_concentracao_portfolio` | inteiro | Pontuação de Concentração da Carteira Cadastrada (0 a 150 pontos; peso 15%). |
| `reserva_elegivel_cents` | inteiro | Soma em BRL dos ativos do Portfólio marcados explicitamente como reserva de emergência. |
| `meses_reserva` | decimal | Quantidade de meses cobertos pela reserva elegível frente à média de despesas de consumo dos últimos 3 meses. |
| `maior_concentracao_portfolio_pct` | decimal | Percentual da maior concentração por classe ou ativo na carteira cadastrada. |
| `concentracao_poupanca_pct` | decimal | Percentual da carteira cadastrada concentrado em Poupança. |
| `dividas_total_aberto_cents` | inteiro | Estoque total de dívidas parceladas abertas, como contexto informativo herdado do Cockpit. |
| `dividas_parcelas_mes_cents` | inteiro | Soma das parcelas de dívidas com competência/vencimento no mês consultado, usada no cálculo do pilar de Endividamento. |
| `comprometimento_divida_mes_pct` | decimal | Percentual `dividas_parcelas_mes_cents / receitas do mês`, usado para pontuar Endividamento. |
| `paz_financeira_base_receita_cents` | inteiro | Média mensal das receitas recorrentes dos últimos 12 meses usada como base para os cards informativos; se ausente, receita do mês com menor confiança. |
| `paz_financeira_confianca` | texto | `alta` quando há 12 meses com receitas recorrentes, `intermediaria` quando há histórico recorrente parcial e `menor` quando usa receita do mês como fallback. |
| `paz_financeira_meses_receita_recorrente` | inteiro | Quantidade de meses com receita recorrente positiva usada na média da Paz Financeira. |
| `paz_independencia_cents` | inteiro | Referência informativa de patrimônio para independência mensal: base de receita × 175. |
| `paz_reserva_estimada_cents` | inteiro | Referência informativa de reserva estimada: base de receita × 6. |
| `paz_recorrentes_saudaveis_cents` | inteiro | Referência informativa para despesas recorrentes saudáveis: base de receita × 0,5. |
| `paz_lazer_saudavel_cents` | inteiro | Referência informativa para lazer saudável: base de receita × 0,3. |
| `pilares` | lista | Lista ordenada dos 5 pilares com `id`, `label`, `score`, `max_score`, `percentual`, `peso_pct`, `nivel` e mensagem explicativa para renderização visual e acessível. |

## Regras

- **Cálculo dos Pilares (Núcleo Python em `financeiro/financial_health.py`)**:
  - **Taxa de Poupança / Aporte (250 pts / peso 25%)**: A taxa de poupança considera `(receitas do mês - despesas de consumo do mês) / receitas do mês`. Lançamentos do tipo investimento/aporte, transferências, câmbio e pagamentos de fatura de cartão não são tratados como despesa para este pilar. Pontuação máxima de 250 pts é alcançada ao poupar/aportar >= 30% da renda.
  - **Reserva de Emergência (250 pts / peso 25%)**: Considera apenas posições do Portfólio marcadas explicitamente pelo usuário como aptas à reserva de emergência, inclusive Poupança. Contas-correntes, carteiras, renda fixa sem marcação, renda variável, cripto, previdência privada e outros ativos não entram neste pilar. A fórmula é `valor elegível como reserva / média mensal de despesas de consumo dos últimos 3 meses`. Pontuação máxima de 250 pts para reserva >= 6 meses; 0 pts para reserva igual a 0; entre 0 e 6 meses a pontuação cresce proporcionalmente.
  - **Marcação de reserva no Portfólio**: O Portfólio deve oferecer um metadado explícito, como `emergency_reserve_eligible`, para que o usuário marque uma posição como parte da reserva. Essa marcação pode ser disponibilizada para Poupança, Renda Fixa com liquidez diária e Tesouro Selic quando representado no Portfólio, mas nenhuma posição entra automaticamente sem decisão explícita do usuário.
  - **Comprometimento de Renda / Endividamento (200 pts / peso 20%)**: Usa o conceito de dívida parcelada do card de **Dívidas** do Cockpit, mas calcula o comprometimento pela soma das parcelas com competência/vencimento no mês consultado, não pelo saldo total futuro em aberto. O percentual de comprometimento é `parcelas de dívidas do mês / receitas do mês`. O estoque total de dívidas parceladas abertas pode ser exibido como contexto informativo, mas não entra diretamente no percentual do pilar. Pontuação máxima de 200 pts quando o comprometimento mensal for <= 20%; cai linearmente para 0 pts se for >= 60%.
  - **Aderência aos Limites (150 pts / peso 15%)**: Calcula o percentual de categorias com limites cadastrados que não foram estourados no mês. Pontuação máxima de 150 pts se 100% das categorias estiverem dentro da meta. Se não houver limites cadastrados, o pilar recebe **0 pts** e exibe mensagem educativa indicando a oportunidade de melhoria no planejamento, por exemplo: "Você ainda não cadastrou limites de gastos. Definir metas mensais por categoria ajuda a acompanhar e equilibrar seus gastos."
  - **Concentração da Carteira Cadastrada (150 pts / peso 15%)**: Mede concentração objetiva do Portfólio cadastrado, sem emitir aconselhamento financeiro personalizado. O pilar avalia a concentração em duas dimensões separadas:
    - **Classe**: agrupamento das posições pelo campo `asset_type`, usando os mesmos valores do formulário de cadastro de lançamentos/posições (ex: `savings`, `fixed_income`, `stock`, `crypto`, `private_pension`, `other`). Uma classe está sobreconcentrada quando ultrapassa **70%** da carteira.
    - **Ativo**: identificador específico da posição, obtido de `asset_identifier`, `asset_name` ou `cnpj`, conforme já usado no Portfólio. Um ativo específico está sobreconcentrado quando ultrapassa **60%** da carteira.
    - A métrica usada no pilar é `max(maior_concentracao_classe, maior_concentracao_ativo)`, permitindo detectar, por exemplo, que um usuário com 80% em Renda Fixa (classe) é alertado pela classe, mas um usuário com 65% em um único CDB (ativo) é alertado pelo ativo específico.
    - A penalidade é aplicada quando a maior concentração ultrapassa o limite da sua dimensão (70% para classe, 60% para ativo). A interface deve apresentar mensagens textuais e explicativas, como `Você tem alta concentração do seu portfólio em Renda Fixa (xx%).`, sem prescrever compra ou venda de ativos.
  - **Concentração em Poupança**: Quando Poupança representar mais de 25% do Portfólio cadastrado, o pilar deve aplicar penalidade adicional e exibir mensagem explicativa, por exemplo: `Poupança representa xx% do seu portfólio; há produtos com melhor relação de rendimento e liquidez que podem ser avaliados conforme seu perfil.` Essa mensagem deve ser educativa, não uma recomendação personalizada de investimento.
- **Interface e Navegação**: O Score de Saúde Financeira e suas recomendações acionáveis são exibidos em uma aba dedicada dentro do módulo **Cockpit**, separada da aba **Situação do mês**, permitindo acesso direto ao diagnóstico sem exigir rolagem pelos KPIs, saldos, planejamento, dívidas e gráficos do resumo mensal.
- **Zonas do Score**: A classificação visual do score total e dos pilares deve usar quatro zonas normalizadas de 0 a 1000:
  - `0 a 299 pts` — **Crítico** / vermelho: risco elevado de endividamento, ausência de reserva ou orçamento no vermelho; exige atenção imediata.
  - `300 a 499 pts` — **Vulnerável / Atenção** / laranja: situação instável, com pouca margem de manobra para imprevistos.
  - `500 a 749 pts` — **Moderado / Em construção** / amarelo: orçamento sob controle, com oportunidades de aumentar poupança, reserva ou disciplina de limites.
  - `750 a 1000 pts` — **Excelente / Sólido** / verde: saúde financeira sólida, reserva consistente, dívidas controladas e aportes recorrentes.
- **Velocímetro/Gauge do Score**: A aba **Saúde Financeira** deve substituir o bloco textual central de pontuação por um velocímetro/gauge nativo em CSS/HTML, com escala de 0 a 1000, ponteiro proporcional ao score e legenda das quatro zonas. Para preservar clareza visual, o gauge deve ficar livre de score/status/texto no centro; pontuação, status e interpretação ficam no bloco textual lateral. O gauge deve ser uma melhoria visual sem biblioteca externa e sem alterar a fórmula do score.
- **Progressive disclosure dos pilares**: Os cards de **Análise detalhada dos pilares** devem ser expansíveis. Fechados, exibem apenas ícone de status, nome do pilar, nível sintético e pontuação (`score / max_score`). Abertos, exibem a explicação, métricas em reais/percentuais e orientação textual.
- **Progressive disclosure da Paz Financeira**: Os cards da seção **Paz Financeira** devem ser expansíveis. Fechados, exibem ícone, nome da referência e valor em reais. Abertos, exibem fórmula/heurística, base de receita, confiança e texto explicativo não prescritivo.
- **Ajuda contextual da Taxa de Poupança**: O KPI/card de **Taxa de poupança** na aba **Situação do mês**, a linha do pilar em **Seus Pilares** e o card detalhado do pilar **Taxa de Poupança** devem exibir um pequeno indicador `i` discreto e acessível. Ao receber hover, foco de teclado ou clique/foco, o indicador deve abrir uma caixa de ajuda visível explicando a fórmula `(receitas do mês - despesas de consumo do mês) / receitas do mês`, deixando claro que investimentos/aportes, transferências, câmbio e pagamentos de fatura não entram como despesa de consumo para este pilar.
- **Gráfico dos pilares**: A aba deve exibir um gráfico compacto de barras horizontais normalizadas por pilar, usando a lista `pilares`. Cada barra compara `score / max_score`, preserva o peso do pilar no rótulo e permite leitura imediata do desempenho relativo. O gráfico deve usar CSS/SVG nativo, sem biblioteca externa, respeitar os tokens do [[../design/design-system|design system]], usar algarismos tabulares nos números e evitar novas cores semânticas. O estado saudável usa o token semântico `var(--color-success, #10B981)` com texto `var(--color-success-text, #ffffff)` para garantir contraste acessível (WCAG AA) em ambos os temas; estados de atenção/crítico devem usar os tokens semânticos `var(--color-warning, #F59E0B)` e `var(--color-error, #EF4444)` com seus respectivos textos, ou variações neutras do design system quando apropriado.
- **Acessibilidade do gráfico**: O gráfico deve ter alternativa textual equivalente no próprio DOM, com nome do pilar, pontuação obtida, pontuação máxima e percentual. Em telas estreitas, as barras podem virar lista vertical densa, sem perder os valores.
- **Paz Financeira (informativo, sem pontuação)**: A aba dedicada deve exibir uma seção **Paz Financeira** que nunca altera o `score_total` nem qualquer pilar. A seção usa como base a **média mensal das receitas recorrentes dos últimos 12 meses**, considerando apenas lançamentos de receita com recorrência mensal (`series_kind = recurring`). Receitas não recorrentes ou pontuais, como PLR, bônus, venda de ativos, restituições ou eventos similares, não entram na base principal. Se houver histórico recorrente parcial, usa a média dos meses disponíveis com confiança intermediária. Se não houver receitas recorrentes, pode usar as receitas do mês consultado como fallback com aviso explícito de menor confiança. Os cards exibidos são apresentados como **estimativas / referências de planejamento**, nunca como metas, obrigações ou recomendações personalizadas de investimento:
  - **Independência mensal (Estimativa)**: `base de receita × 175`, patrimônio estimado para gerar renda passiva mensal equivalente à base de receita, usando uma heurística conservadora aproximada. A interface deve exibir a legenda explicativa: "Patrimônio estimado (usando heurística de 175x sua receita mensal) para gerar renda passiva mensal equivalente à sua receita atual."
  - **Reserva estimada (Estimativa)**: `base de receita × 6`, referência simples de reserva baseada na renda recorrente. Essa métrica difere do pilar de Reserva (que usa despesas reais e posições marcadas); se a reserva elegível atingir esse valor, em tese o pilar atinge nota máxima, e se não atingir é um indicativo de que as despesas médias superam a receita de referência.
  - **Recorrentes saudáveis (Estimativa)**: `base de receita × 0,5`, referência de valor máximo saudável para bancar despesas recorrentes.
  - **Lazer saudável (Estimativa)**: `base de receita × 0,3`, referência de valor máximo saudável para lazer.
- **Mensagens da Paz Financeira**: Todos os cards devem trazer mensagens explicativas e não prescritivas, deixando claro que são **estimativas para nortear o planejamento**, baseadas em heurísticas simplificadas e boas práticas gerais, e não regras fixas, metas financeiras ou recomendações que devem ser buscadas a todo custo. A interface deve usar termos como "Estimativa", "Referência" e "Aproximado" nos rótulos e legendas, e incluir um rodapé único consolidado. Quando houver 12 meses recorrentes, o rodapé deve indicar que os valores usam a média das receitas recorrentes mensais dos últimos 12 meses com confiança alta. Quando houver histórico parcial, deve indicar a quantidade de meses usada e confiança intermediária. Quando usar fallback mensal, deve indicar que a base veio da receita do mês consultado por ausência de receitas recorrentes suficientes e confiança menor. O texto explicativo deve manter o sentido: "Estimativas para nortear planejamento, baseadas em boas práticas gerais; não são regras fixas, metas ou recomendações personalizadas, sendo que a real necessidade varia conforme estilo de vida, localização e objetivos. Consulte um assessor para planejamento personalizado."
- **Normalização de Moedas**: Todos os cálculos utilizam os valores normalizados em BRL (centavos inteiros), conforme as regras já vigentes em [[investimentos-portfolio]] e [[relatorios]].
- **Isolamento por Usuário**: O score é calculado exclusivamente sobre os dados do usuário autenticado na sessão.
- **Sem Efeito Colateral**: A consulta do score é uma operação de leitura analítica idempotente que não altera saldos nem movimentações.
- **Dados insuficientes e proteção contra divisão por zero**: Se o denominador de qualquer indicador percentual ou relativo for zero ou negativo, o pilar afetado deve retornar nota neutra (metade da pontuação máxima do pilar) e mensagem explicativa, sem lançar exceção nem gerar divisão por zero:
  - **Taxa de Poupança**: quando `receitas do mês <= 0`, retornar `score = 125` (metade de 250), `taxa_poupanca_pct = 0.0`, `dados_insuficientes = true` e mensagem "Sem receitas no mês para calcular a taxa de poupança; nota neutra aplicada."
  - **Reserva de Emergência**: quando `média mensal de despesas de consumo dos últimos 3 meses <= 0`, retornar `score = 125` (metade de 250), `meses_reserva = 0.0`, `dados_insuficientes = true` e mensagem "Sem média de despesas de consumo suficiente; nota neutra aplicada."
  - **Endividamento**: quando `receitas do mês <= 0`, retornar `score = 100` (metade de 200), `comprometimento_divida_mes_pct = 0.0`, `dados_insuficientes = true` e mensagem "Sem receitas no mês para medir comprometimento de dívida; nota neutra aplicada."
  - A pontuação total (`score_total`) deve refletir a soma dos pilares, e a API deve retornar o campo `dados_insuficientes` como `true` quando receitas e despesas de consumo do mês forem zero ou inexistentes.
- **Validação do histórico de Score**: A função/rota de histórico deve validar o parâmetro `months` (int) entre 1 e 36 antes de realizar qualquer cálculo ou acesso ao banco. Valores inválidos devem retornar erro de domínio amigável (`HTTP 400`), sem expor detalhes internos. O limite de 36 meses (3 anos) equilibra utilidade analítica e proteção de performance.

## API e dados

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/financial-health-score?month=AAAA-MM` | Retorna a pontuação detalhada do mês, pilares e a seção informativa Paz Financeira. |
| `GET` | `/api/financial-health-score/history?months=6` | Retorna o histórico da pontuação dos últimos N meses. O parâmetro `months` deve ser validado entre `1` e `36` (máximo de 3 anos); valores fora desse intervalo devem retornar erro `400 Bad Request` com mensagem amigável. |

**Validação do histórico**: O parâmetro `months` é obrigatório e aceita apenas inteiros entre 1 e 36. Valores ausentes, não numéricos, menores que 1 ou maiores que 36 devem ser rejeitados antes de qualquer consulta ao banco, protegendo performance e definindo contrato claro da API.

Tabelas: consulta `transactions`, `credit_card_transactions`, `spending_limits`, `investment_opening_positions`, `investment_operations` e `checking_accounts`. O Portfólio deve persistir metadado booleano de elegibilidade para reserva de emergência nas posições ou estrutura equivalente.

## Critérios de aceite

- Dado um usuário com receita de R$ 10.000,00, despesas de consumo de R$ 6.000,00 e aportes/investimentos de R$ 2.000,00 no mês, quando o score é consultado, então a taxa de poupança considerada é 40% e o pilar retorna a pontuação máxima de 250 pontos, pois aportes não entram como despesa de consumo.
- Dado um usuário com média mensal de despesas de consumo de R$ 5.000,00 nos últimos 3 meses e posições do Portfólio marcadas explicitamente como reserva somando R$ 30.000,00, quando o score é consultado, então o pilar de Reserva considera 6 meses de cobertura e retorna a pontuação máxima de 250 pontos.
- Dado um usuário com saldo em conta-corrente de R$ 50.000,00 e nenhuma posição do Portfólio marcada explicitamente como reserva, quando o score é consultado, então o pilar de Reserva não considera o saldo da conta-corrente como reserva de emergência.
- Dado um usuário sem lançamentos no mês de referência, quando a API é acionada, então o sistema retorna `dados_insuficientes = true` e atribui nota neutra (metade da pontuação máxima) aos pilares que dependem de denominador zero: `pilar_poupanca = 125`, `pilar_reserva = 125` e `pilar_endividamento = 100`, sem gerar divisão por zero.
- Dado um usuário com 3 limites cadastrados sendo 1 estourado no mês, quando avaliado a aderência aos limites, então a nota do pilar corresponde a 66.6% da pontuação máxima do pilar (100 de 150 pts).
- Dado um usuário sem limites de gastos cadastrados no mês, quando avaliado a aderência aos limites, então o pilar retorna **0 pts** e exibe mensagem educativa indicando a oportunidade de melhoria no planejamento, incentivando o cadastro de limites mensais por categoria.
- Dado um usuário com receitas de R$ 10.000,00, dívida parcelada total aberta de R$ 80.000,00 e parcelas com competência/vencimento no mês somando R$ 3.000,00, quando o score é consultado, então o comprometimento de renda considerado para Endividamento é 30%, pois o estoque total de dívida é apenas contexto.
- Dado um usuário com 80% do Portfólio cadastrado concentrado na classe Renda Fixa (distribuído entre CDB, LCI e Tesouro), quando o score é consultado, então o pilar de Concentração da Carteira detecta sobreconcentração por classe (>70%) e retorna mensagem explicativa informando o percentual concentrado em Renda Fixa, sem recomendar compra ou venda de ativos.
- Dado um usuário com 65% do Portfólio cadastrado concentrado em um único ativo (CDB específico), quando o score é consultado, então o pilar de Concentração da Carteira detecta sobreconcentração por ativo (>60%) e retorna mensagem explicativa informando o percentual concentrado naquele ativo, sem recomendar compra ou venda.
- Dado um usuário com 30% do Portfólio cadastrado concentrado em Poupança, quando o score é consultado, então o pilar de Concentração da Carteira aplica penalidade adicional por Poupança acima de 25% e retorna mensagem educativa sobre avaliar alternativas conforme o perfil.
- Dado um usuário com receitas recorrentes mensais de R$ 10.000,00 em cada um dos últimos 12 meses, quando a seção Paz Financeira é exibida, então os cards são apresentados como estimativas (`Independência mensal (Estimativa)`, `Reserva estimada`, `Recorrentes saudáveis (Estimativa)`, `Lazer saudável (Estimativa)`), mostram Independência mensal de R$ 1.750.000,00, Reserva estimada de R$ 60.000,00, Recorrentes saudáveis de R$ 5.000,00 e Lazer saudável de R$ 3.000,00, e o rodapé informa que a base é a média das receitas recorrentes mensais dos últimos 12 meses com confiança alta, sem alterar a pontuação do score.
- Dado um usuário com receitas recorrentes mensais nos últimos 6 meses e sem receitas recorrentes nos 6 meses anteriores, quando a seção Paz Financeira é exibida, então a base usada é a média dos 6 meses disponíveis e a interface exibe confiança intermediária.
- Dado um usuário com receita pontual de PLR no mês consultado e receitas recorrentes históricas menores, quando a seção Paz Financeira é exibida, então a PLR não altera a base principal e os cards usam a média das receitas recorrentes.
- Dado um usuário sem receitas recorrentes cadastradas e com receitas de R$ 8.000,00 no mês, quando a seção Paz Financeira é exibida, então a base usada é a receita do mês, a interface exibe aviso de menor confiança da estimativa e os cards mantêm o mesmo tom de referência/estimativa (não meta).
- Dado um usuário autenticado A, quando tenta consultar a rota `/api/financial-health-score`, então somente os lançamentos e ativos associados ao `user_id` de A são considerados no cálculo.
- Dado um usuário autenticado que consulta `/api/financial-health-score/history?months=1000`, quando a API recebe o parâmetro, então retorna `400 Bad Request` com mensagem informando que `months` deve estar entre 1 e 36, sem consultar o banco de dados.
- Dado um usuário autenticado que consulta `/api/financial-health-score/history?months=12`, quando a API recebe o parâmetro válido, então retorna o histórico dos últimos 12 meses.
- Dado o Cockpit carregado, quando o usuário seleciona a aba dedicada de Saúde Financeira no tema claro ou escuro, o medidor do Score utiliza o token semântico `var(--color-success, #10B981)` para indicar status saudável, com texto `var(--color-success-text, #ffffff)` para garantir contraste acessível (WCAG AA) em ambos os temas, respeitando o design system.
- Dado o Cockpit carregado com a aba **Situação do mês** ativa, quando o usuário clica em **Saúde Financeira**, então a aba dedicada do score é exibida diretamente, sem o conteúdo do resumo financeiro acima dela.
- Dado o Cockpit carregado, quando a aba dedicada de Saúde Financeira exibe os pilares, então há um gráfico de barras horizontais com os 5 pilares, cada um exibindo pontuação obtida, pontuação máxima, percentual e peso, sem depender de biblioteca externa.
- Dado um usuário em viewport estreita ou usando leitor de tela, quando acessa o gráfico dos pilares, então os mesmos dados do gráfico ficam disponíveis em lista textual equivalente e sem overflow horizontal.
- Dado o Cockpit carregado na aba **Situação do mês**, quando o usuário visualiza o KPI/card **Taxa de poupança**, então há um pequeno indicador `i` que abre uma caixa de ajuda textual acessível em hover, foco ou clique/foco, explicando a fórmula e as exclusões do cálculo.
- Dado o Cockpit carregado na aba Saúde Financeira, quando o usuário visualiza a linha do pilar ou o card detalhado de **Taxa de Poupança**, então há um pequeno indicador `i` que abre uma caixa de ajuda textual acessível em hover, foco ou clique/foco, explicando a fórmula e as exclusões do cálculo.
- Dado um score total de 280, quando a aba Saúde Financeira é exibida, então o gauge classifica o diagnóstico como **Crítico** dentro da faixa 0–299.
- Dado um score total de 420, quando a aba Saúde Financeira é exibida, então o gauge classifica o diagnóstico como **Vulnerável / Atenção** dentro da faixa 300–499.
- Dado um score total de 680, quando a aba Saúde Financeira é exibida, então o gauge classifica o diagnóstico como **Moderado / Em construção** dentro da faixa 500–749.
- Dado um score total de 820, quando a aba Saúde Financeira é exibida, então o gauge classifica o diagnóstico como **Excelente / Sólido** dentro da faixa 750–1000.
- Dado a aba Saúde Financeira exibindo o gauge, quando o usuário observa o gráfico, então o centro do velocímetro não exibe texto que concorra com o ponteiro; score, status e interpretação aparecem no bloco lateral.
- Dado a seção **Análise detalhada dos pilares**, quando a tela carrega, então cada card de pilar aparece em estado recolhido com cabeçalho sintético e pode ser expandido para revelar as métricas e explicações.
- Dado a seção **Paz Financeira**, quando a tela carrega, então cada card aparece em estado recolhido com ícone, nome e valor, e pode ser expandido para revelar fórmula, base usada e confiança.

## Pendências

Nenhuma pendência conhecida.

## Fora de escopo

- Integração com órgãos de proteção ao crédito externos (Serasa, SPC, Registrato/Banco Central).
- Motor de inteligência artificial generativa externa para sugestões de investimento.

## Plano de implementação

- [x] Passo 1 — Adicionar metadado explícito de elegibilidade para reserva de emergência no Portfólio, com migração idempotente e campo de marcação na UI de posições elegíveis. Fecha: critérios 2 e 3.
- [x] Passo 2 — Criar módulo Python `financeiro/financial_health.py` implementando as funções atômicas de cálculo de cada pilar (com a distribuição 25/25/20/15/15), a lista `pilares` e a seção informativa Paz Financeira em centavos inteiros. Fecha: critérios 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 e 11.
- [x] Passo 3 — Adicionar as rotas `GET /api/financial-health-score` e `GET /api/financial-health-score/history` em `app.py` com validação de sessão e origem. Fecha: critérios 12, 13 e 14.
- [x] Passo 4 — Criar os testes unitários automatizados em `tests/test_financial_health.py` validando os pilares, Paz Financeira e casos de borda. Fecha: critérios 1, 2, 3, 4, 5, 6, 7, 8, 9 e 10.
- [x] Passo 5 — Implementar a aba dedicada de Saúde Financeira na view do Cockpit (`web/modules/cockpit-view.js` / sub-view dedicada), incluindo gráfico nativo de barras horizontais por pilar, fallback textual acessível e ajuda contextual da Taxa de Poupança. Fecha: critérios 15, 16, 17, 22 e 23.
- [ ] Passo 6 — Atualizar `docs/arquitetura.md` e `docs/requisitos.md` com as novas rotas, módulo e metadado de reserva no Portfólio.

## Changelog

- `3.2` — 2026-08-04 — Spec marcada como `implementado` no vault de documentação do app principal.
- `3.1` — 2026-08-02 — Gauge do Score passa a manter o centro livre de texto, movendo pontuação/status para o bloco lateral e removendo redundância visual com a escala.
- `3.0` — 2026-08-02 — Diagnóstico visual passa a usar gauge de 0 a 1000 com quatro zonas (vermelho, laranja, amarelo, verde) e cards expansíveis para pilares e Paz Financeira.
- `2.9` — 2026-07-31 — Indicador `i` da Taxa de Poupança passa a abrir caixa de ajuda visual em hover, foco de teclado ou clique/foco, em vez de depender apenas do tooltip nativo.
- `2.8` — 2026-07-31 — Ajuda contextual de Taxa de Poupança passa a aparecer também no KPI/card da aba "Situação do mês".
- `2.7` — 2026-07-31 — Ajuda contextual de Taxa de Poupança passa a aparecer também na linha do pilar em "Seus Pilares", além do card detalhado.
- `2.6` — 2026-07-31 — Adicionada ajuda contextual no card detalhado de Taxa de Poupança para explicar fórmula e exclusões do cálculo.
- `2.5` — 2026-07-31 — Referência da aba operacional do Cockpit atualizada para `Situação do mês`, mantendo Saúde Financeira como aba diagnóstica separada.
- `2.4` — 2026-07-31 — Saúde Financeira passa a ser acessada por aba interna separada do Resumo financeiro no Cockpit.
- `2.3` — 2026-07-29 — Paz Financeira passa a usar média mensal das receitas recorrentes dos últimos 12 meses como base principal, com confiança intermediária para histórico parcial e fallback mensal apenas quando não houver recorrências.
- `2.2` — 2026-07-29 — Especificado uso de tokens semânticos do design system (`--color-success`, `--color-success-text`, `--color-warning`, `--color-error`) no gráfico de pilares e medidor do Score para garantir contraste acessível em ambos os temas; critério de aceite do tema escuro atualizado.
- `2.1` — 2026-07-29 — Removido campo redundante de disclaimer separado da Paz Financeira, mantendo apenas o rodapé único consolidado.
- `2.0` — 2026-07-29 — Consolidado o rodapé da seção Paz Financeira para remover redundância entre mensagem e disclaimer, mantendo o caráter informativo e não prescritivo.
- `1.9` — 2026-07-29 — Implementada seção dedicada de Saúde Financeira no Cockpit seguindo o wireframe aprovado, com seletor mensal, score central, barras nativas dos pilares, cards de análise detalhada, seção Paz Financeira e fallback textual acessível.
- `1.8` — 2026-07-29 — Detalhada distinção entre concentração por classe (`asset_type`) e por ativo (`asset_name`/`asset_identifier`/`cnpj`), com limites diferentes (70% para classe, 60% para ativo) e origem dos valores vinda do formulário de cadastro; critérios de aceite ajustados.
- `1.7` — 2026-07-29 — Formalizado passo 4 com testes unitários e integrado do Score cobrindo pilares, Paz Financeira, dados insuficientes, validação de histórico e payload calculado sobre SQLite temporário.
- `1.6` — 2026-07-29 — Implementadas rotas `GET /api/financial-health-score` e `GET /api/financial-health-score/history` em `app.py`, com sessão obrigatória, validação de origem/host e erro amigável para `months` inválido.
- `1.5` — 2026-07-29 — Definida validação do parâmetro `months` da rota de histórico (`/api/financial-health-score/history`) entre 1 e 36, com erro amigável para valores fora do intervalo; regra e critérios de aceite adicionados.
- `1.4` — 2026-07-29 — Ajustado pilar de Aderência aos Limites: sem limites cadastrados retorna 0 pts (antes 75 pts neutros) com mensagem educativa sobre oportunidade de melhoria no planejamento; critério de aceite adicionado.
- `1.3` — 2026-07-29 — Reforçada a linguagem da seção Paz Financeira como "Estimativa" / "Referência" (não meta), detalhada a heurística de 175x no card de Independência, adicionado disclaimer orientando consulta a assessor e ajustados critérios de aceite 9 e 10.
- `1.2` — 2026-07-29 — Especificada regra de dados insuficientes e proteção contra divisão por zero para `pilar_poupanca`, `pilar_reserva` e `pilar_endividamento`, incluindo valores neutros e mensagens esperadas; critério de aceite #4 detalhado.
- `1.1` — 2026-07-28 — Criado núcleo `financeiro/financial_health.py` com funções atômicas dos 5 pilares, montagem da lista `pilares`, seção informativa Paz Financeira em centavos inteiros e testes unitários focados.
- `1.0` — 2026-07-28 — Iniciada implantação: Portfólio passa a persistir metadado explícito de elegibilidade para reserva de emergência em posições iniciais elegíveis.
- `0.9` — 2026-07-28 — Pilar de Endividamento passa a calcular comprometimento por serviço mensal da dívida (`parcelas do mês / receitas`), mantendo o estoque total de dívidas parceladas apenas como contexto informativo.
- `0.8` — 2026-07-28 — Incluído gráfico nativo de barras horizontais para tornar os 5 pilares mais visuais, com lista de dados `pilares`, fallback textual acessível e alinhamento ao design system; status/tag alinhados como rascunho.
- `0.7` — 2026-07-27 — Incluída seção informativa Paz Financeira, sem impacto no score, baseada em receitas recorrentes ou receita do mês com menor confiança, com quatro cards de referência para planejamento.
- `0.6` — 2026-07-27 — Pilar de Diversificação reformulado como Concentração da Carteira Cadastrada, com mensagens explicativas não prescritivas e penalidade adicional para Poupança acima de 25% do Portfólio.
- `0.5` — 2026-07-27 — Pilar de Reserva passa a considerar somente posições do Portfólio explicitamente marcadas como reserva de emergência, inclusive Poupança; conta-corrente deixa de ser elegível e plano passa a prever metadado novo no Portfólio.
- `0.4` — 2026-07-27 — Pilar de Endividamento alinhado ao mesmo agregado do card de Dívidas do Cockpit, considerando compras parceladas futuras em aberto sobre receitas do mês.
- `0.3` — 2026-07-27 — Taxa de poupança alinhada para considerar receitas menos despesas de consumo, excluindo aportes/investimentos, transferências, câmbio e pagamentos de fatura; status textual/tag ajustados para rascunho.
- `0.2` — 2026-07-27 — Aprovada a distribuição de pesos dos 5 pilares (25/25/20/15/15) e definida a localização da interface como aba dedicada no Cockpit para permitir recomendações futuras sem poluir a visualização principal. Pendências resolvidas.
- `0.1` — 2026-07-27 — Especificação inicial em status `em-implementacao`.

## Relacionados

- [[relatorios]]
- [[limites-gastos]]
- [[investimentos-portfolio]]
- [[cartoes]]
- [[contas-correntes]]
- [[arquitetura]]
