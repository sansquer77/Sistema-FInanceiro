---
tipo: spec
area: score-saude-financeira
status: em-implementacao
versao: 1.0
atualizado: 2026-07-28
relacionados:
  - "[[relatorios]]"
  - "[[limites-gastos]]"
  - "[[investimentos-portfolio]]"
  - "[[cartoes]]"
  - "[[contas-correntes]]"
  - "[[arquitetura]]"
tags: [spec, "area/score-saude-financeira", "status/em-implementacao"]
aliases: ["Score de Saúde Financeira", "Diagnóstico Financeiro", "Financial Health Score"]
---

# Score de Saúde Financeira

> [!info] Status
> **em-implementacao** · área: `score-saude-financeira` · atualizado em 2026-07-28 · relacionados: [[relatorios]], [[limites-gastos]], [[investimentos-portfolio]], [[cartoes]], [[contas-correntes]]

## Problema

O usuário possui dados de contas, lançamentos, cartões, limites de gastos e investimentos espalhados pelo sistema, mas não conta com um indicador síntese (pontuação de 0 a 1000) que avalie seu estado financeiro geral nem orientações claras sobre quais pilares precisam de atenção.

## Usuário

Qualquer usuário autenticado localmente que deseje entender sua saúde financeira através de um diagnóstico consolidado e acionável.

## Jornada

1. O usuário acessa o **Cockpit** e clica na aba dedicada de **Saúde Financeira**.
2. O sistema calcula e exibe a pontuação total (0 a 1000) do mês consultado, categorizada em níveis (Crítico, Atenção, Bom, Excelente).
3. O usuário visualiza um gráfico compacto de pilares, permitindo perceber rapidamente quais dimensões puxam o score para cima ou para baixo.
4. O usuário visualiza o detalhamento dos 5 pilares do score com seus pesos aprovados (Poupança 25%, Reserva 25%, Endividamento 20%, Limites 15%, Concentração da Carteira 15%), acompanhados de recomendações práticas para melhorar cada indicador.
5. O usuário visualiza a seção informativa **Paz Financeira**, com referências simples para nortear o planejamento de independência, reserva, despesas recorrentes e lazer.
6. O usuário pode consultar o histórico mensal da evolução do seu score e visualizar plano de ação com recomendações sem poluição visual do painel principal do Cockpit.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Obrigatório. Mês de referência da avaliação. |
| `score_total` | inteiro | Pontuação consolidada entre `0` e `1000`. |
| `nivel` | texto | Categoria: `critico` (0-399), `atencao` (400-599), `bom` (600-799), `excelente` (800-1000). |
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
| `paz_financeira_base_receita_cents` | inteiro | Receita recorrente mensal usada como base para os cards informativos; se ausente, receita do mês com menor confiança. |
| `paz_financeira_confianca` | texto | `alta` quando usa receitas recorrentes mensais; `menor` quando usa receita do mês como fallback. |
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
  - **Aderência aos Limites (150 pts / peso 15%)**: Calcula o percentual de categorias com limites cadastrados que não foram estourados no mês. Pontuação máxima de 150 pts se 100% das categorias estiverem dentro da meta. Se não houver limites cadastrados, atribui nota neutra proporcional (75 pts).
  - **Concentração da Carteira Cadastrada (150 pts / peso 15%)**: Mede concentração objetiva do Portfólio cadastrado, sem emitir aconselhamento financeiro personalizado. O pilar avalia a maior concentração por classe ou ativo e penaliza sobreconcentração, especialmente quando uma única classe ou ativo ultrapassa 70% da carteira. A interface deve apresentar mensagens textuais e explicativas, como `Você tem alta concentração do seu portfólio em Renda Fixa (xx%).`, sem prescrever compra ou venda de ativos.
  - **Concentração em Poupança**: Quando Poupança representar mais de 25% do Portfólio cadastrado, o pilar deve aplicar penalidade adicional e exibir mensagem explicativa, por exemplo: `Poupança representa xx% do seu portfólio; há produtos com melhor relação de rendimento e liquidez que podem ser avaliados conforme seu perfil.` Essa mensagem deve ser educativa, não uma recomendação personalizada de investimento.
- **Interface e Navegação**: O Score de Saúde Financeira e suas recomendações acionáveis são exibidos em uma aba dedicada dentro do módulo **Cockpit**, permitindo visualização expandida dos pilares e histórico sem sobrecarregar a visão sintética inicial.
- **Gráfico dos pilares**: A aba deve exibir um gráfico compacto de barras horizontais normalizadas por pilar, usando a lista `pilares`. Cada barra compara `score / max_score`, preserva o peso do pilar no rótulo e permite leitura imediata do desempenho relativo. O gráfico deve usar CSS/SVG nativo, sem biblioteca externa, respeitar os tokens do [[../design/design-system|design system]], usar algarismos tabulares nos números e evitar novas cores semânticas. Verde (`#10B981`) só pode indicar estado saudável; estados de atenção/crítico devem usar tokens existentes de texto, borda, superfície, erro ou variações neutras já previstas.
- **Acessibilidade do gráfico**: O gráfico deve ter alternativa textual equivalente no próprio DOM, com nome do pilar, pontuação obtida, pontuação máxima e percentual. Em telas estreitas, as barras podem virar lista vertical densa, sem perder os valores.
- **Paz Financeira (informativo, sem pontuação)**: A aba dedicada deve exibir uma seção **Paz Financeira** que nunca altera o `score_total` nem qualquer pilar. A seção usa receitas recorrentes mensais como base; se não houver receitas recorrentes, pode usar as receitas do mês como fallback com aviso explícito de menor confiança. Os cards exibidos são:
  - **Independência mensal**: `base de receita × 175`, referência de patrimônio investido para gerar renda passiva mensal equivalente à base de receita, usando uma heurística conservadora aproximada.
  - **Reserva estimada**: `base de receita × 6`, referência simples de reserva baseada na renda recorrente. Essa métrica difere do pilar de Reserva (que usa despesas reais e posições marcadas); se a reserva elegível atingir esse valor, em tese o pilar atinge nota máxima, e se não atingir é um indicativo de que as despesas médias superam a receita de referência.
  - **Recorrentes saudáveis**: `base de receita × 0,5`, referência de valor máximo saudável para bancar despesas recorrentes.
  - **Lazer saudável**: `base de receita × 0,3`, referência de valor máximo saudável para lazer.
- **Mensagens da Paz Financeira**: Os cards devem trazer mensagens explicativas e não prescritivas, deixando claro que são estimativas para nortear o planejamento, baseadas em boas práticas gerais, e não regras fixas que devem ser buscadas a todo custo.
- **Normalização de Moedas**: Todos os cálculos utilizam os valores normalizados em BRL (centavos inteiros), conforme as regras já vigentes em [[investimentos-portfolio]] e [[relatorios]].
- **Isolamento por Usuário**: O score é calculado exclusivamente sobre os dados do usuário autenticado na sessão.
- **Sem Efeito Colateral**: A consulta do score é uma operação de leitura analítica idempotente que não altera saldos nem movimentações.

## API e dados

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/financial-health-score?month=AAAA-MM` | Retorna a pontuação detalhada do mês, pilares e a seção informativa Paz Financeira. |
| `GET` | `/api/financial-health-score/history?months=6` | Retorna o histórico da pontuação dos últimos N meses. |

Tabelas: consulta `transactions`, `credit_card_transactions`, `spending_limits`, `investment_opening_positions`, `investment_operations` e `checking_accounts`. O Portfólio deve persistir metadado booleano de elegibilidade para reserva de emergência nas posições ou estrutura equivalente.

## Critérios de aceite

- Dado um usuário com receita de R$ 10.000,00, despesas de consumo de R$ 6.000,00 e aportes/investimentos de R$ 2.000,00 no mês, quando o score é consultado, então a taxa de poupança considerada é 40% e o pilar retorna a pontuação máxima de 250 pontos, pois aportes não entram como despesa de consumo.
- Dado um usuário com média mensal de despesas de consumo de R$ 5.000,00 nos últimos 3 meses e posições do Portfólio marcadas explicitamente como reserva somando R$ 30.000,00, quando o score é consultado, então o pilar de Reserva considera 6 meses de cobertura e retorna a pontuação máxima de 250 pontos.
- Dado um usuário com saldo em conta-corrente de R$ 50.000,00 e nenhuma posição do Portfólio marcada explicitamente como reserva, quando o score é consultado, então o pilar de Reserva não considera o saldo da conta-corrente como reserva de emergência.
- Dado um usuário sem lançamentos no mês de referência, quando a API é acionada, então o sistema retorna um indicador com status neutro/dados insuficientes sem gerar divisão por zero.
- Dado um usuário com 3 limites cadastrados sendo 1 estourado no mês, quando avaliado a aderência aos limites, então a nota do pilar corresponde a 66.6% da pontuação máxima do pilar (100 de 150 pts).
- Dado um usuário com receitas de R$ 10.000,00, dívida parcelada total aberta de R$ 80.000,00 e parcelas com competência/vencimento no mês somando R$ 3.000,00, quando o score é consultado, então o comprometimento de renda considerado para Endividamento é 30%, pois o estoque total de dívida é apenas contexto.
- Dado um usuário com 80% do Portfólio cadastrado concentrado em Renda Fixa, quando o score é consultado, então o pilar de Concentração da Carteira registra sobreconcentração e retorna mensagem explicativa informando o percentual concentrado, sem recomendar compra ou venda de ativos.
- Dado um usuário com 30% do Portfólio cadastrado concentrado em Poupança, quando o score é consultado, então o pilar de Concentração da Carteira aplica penalidade adicional por Poupança acima de 25% e retorna mensagem educativa sobre avaliar alternativas conforme o perfil.
- Dado um usuário com receitas recorrentes mensais de R$ 10.000,00, quando a seção Paz Financeira é exibida, então os cards informativos mostram Independência mensal de R$ 1.750.000,00, Reserva estimada de R$ 60.000,00, Recorrentes saudáveis de R$ 5.000,00 e Lazer saudável de R$ 3.000,00, sem alterar a pontuação do score.
- Dado um usuário sem receitas recorrentes cadastradas e com receitas de R$ 8.000,00 no mês, quando a seção Paz Financeira é exibida, então a base usada é a receita do mês e a interface exibe aviso de menor confiança da estimativa.
- Dado um usuário autenticado A, quando tenta consultar a rota `/api/financial-health-score`, então somente os lançamentos e ativos associados ao `user_id` de A são considerados no cálculo.
- Dado o Cockpit carregado, quando o usuário seleciona a aba dedicada de Saúde Financeira no tema claro ou escuro, o medidor do Score utiliza a cor verde `#10B981` exclusivamente para indicar status saudável, respeitando o design system.
- Dado o Cockpit carregado, quando a aba dedicada de Saúde Financeira exibe os pilares, então há um gráfico de barras horizontais com os 5 pilares, cada um exibindo pontuação obtida, pontuação máxima, percentual e peso, sem depender de biblioteca externa.
- Dado um usuário em viewport estreita ou usando leitor de tela, quando acessa o gráfico dos pilares, então os mesmos dados do gráfico ficam disponíveis em lista textual equivalente e sem overflow horizontal.

## Pendências

Nenhuma pendência conhecida.

## Fora de escopo

- Integração com órgãos de proteção ao crédito externos (Serasa, SPC, Registrato/Banco Central).
- Motor de inteligência artificial generativa externa para sugestões de investimento.

## Plano de implementação

- [x] Passo 1 — Adicionar metadado explícito de elegibilidade para reserva de emergência no Portfólio, com migração idempotente e campo de marcação na UI de posições elegíveis. Fecha: critérios 2 e 3.
- [ ] Passo 2 — Criar módulo Python `financeiro/financial_health.py` implementando as funções atômicas de cálculo de cada pilar (com a distribuição 25/25/20/15/15), a lista `pilares` e a seção informativa Paz Financeira em centavos inteiros. Fecha: critérios 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 e 11.
- [ ] Passo 3 — Adicionar as rotas `GET /api/financial-health-score` e `GET /api/financial-health-score/history` em `app.py` com validação de sessão e origem. Fecha: critério 11.
- [ ] Passo 4 — Criar os testes unitários automatizados em `tests/test_financial_health.py` validando os pilares, Paz Financeira e casos de borda. Fecha: critérios 1, 2, 3, 4, 5, 6, 7, 8, 9 e 10.
- [ ] Passo 5 — Implementar a aba dedicada de Saúde Financeira na view do Cockpit (`web/modules/cockpit-view.js` / sub-view dedicada), incluindo gráfico nativo de barras horizontais por pilar e fallback textual acessível. Fecha: critérios 12, 13 e 14.
- [ ] Passo 6 — Atualizar `docs/arquitetura.md` e `docs/requisitos.md` com as novas rotas, módulo e metadado de reserva no Portfólio.

## Changelog

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
