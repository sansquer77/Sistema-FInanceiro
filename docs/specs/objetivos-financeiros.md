---
tipo: spec
area: objetivos-financeiros
status: em-revisao
versao: 0.10
atualizado: 2026-09-24
relacionados:
  - "[[limites-gastos]]"
  - "[[investimentos-portfolio]]"
  - "[[score-saude-financeira]]"
  - "[[cockpit-calendario]]"
  - "[[historico-operacoes]]"
  - "[[arquitetura]]"
tags: [spec, "area/objetivos-financeiros", "status/em-revisao"]
aliases: ["Objetivos Financeiros", "Fundos de Provisão", "Cofrinhos"]
---

# Objetivos Financeiros e Fundos de Provisão

> [!info] Status
> **em-revisao** · área: `objetivos-financeiros` · atualizado em 2026-09-24 · relacionados: [[limites-gastos]], [[investimentos-portfolio]], [[score-saude-financeira]], [[cockpit-calendario]], [[historico-operacoes]]

## Problema

Os limites de gastos respondem quanto o usuário pode gastar por mês, mas o app ainda não permite separar dinheiro para finalidades futuras, acompanhar metas de poupança nem provisionar despesas previsíveis. O usuário precisa saber para que está guardando, quanto já reservou, quanto ainda falta e qual aporte periódico é necessário, sem confundir reserva financeira com despesa ou contar o mesmo recurso em mais de uma finalidade.

## Usuário

Usuário autenticado localmente que deseja formar reserva de emergência, guardar para uma meta ou provisionar despesas futuras como IPVA, seguro, manutenção, matrícula, viagem, entrada de imóvel ou troca de equipamento.

## Jornada

1. O usuário abre **Limites** e seleciona a aba **Objetivos**; a aba **Gastos** mantém os limites atuais.
2. Cria uma meta, provisão com vencimento ou reserva contínua, informando valor-alvo, data desejada e rendimento projetado opcional.
3. Registra manualmente aportes, retiradas ou ajustes no saldo reservado, sem gerar automaticamente receita, despesa ou transferência.
4. Acompanha progresso, aporte recomendado, previsão de conclusão e estado do objetivo.
5. Vincula ao objetivo um investimento consolidado — por exemplo, Tesouro Prefixado 2027 — e reserva seu saldo atual considerando todos os movimentos/lotes daquele ativo.
6. Consulta, no topo da aba, o resumo da Reserva de Emergência com valor total e investimentos que a compõem.
7. Ao tentar usar em outro objetivo um investimento que já compõe a Reserva de Emergência, recebe alerta de sobreposição e precisa escolher outra origem ou remover antes a marcação anterior.

## Dados

### Objetivo

| Campo | Tipo | Regra |
|---|---|---|
| `name` | texto | Obrigatório e não vazio. |
| `objective_type` | enum | `target`, `annual_provision` ou `continuous_reserve`. |
| `target_amount_cents` | inteiro | Obrigatório e maior que zero. |
| `target_date` | ISO `YYYY-MM-DD` | Obrigatório para meta e provisão; opcional para reserva contínua. |
| `start_date` | ISO `YYYY-MM-DD` | Data a partir da qual o plano de aportes é calculado. |
| `status` | enum | `active`, `paused`, `completed` ou `archived`. |
| `yield_mode` | enum | `none`, `cdi_percentage` ou `custom_annual_rate`. |
| `yield_percentage` | decimal | Percentual do CDI ou taxa anual; padrão `100` quando o modo for CDI. |
| `tax_treatment` | enum | `conservative`, `taxable` ou `exempt`; padrão conservador. |
| `safety_margin_bps` | inteiro | Margem opcional sobre o valor-alvo, em pontos-base. |
| `preferred_contribution_day` | inteiro | Opcional, de 1 a 28. |
| `notes` | texto | Opcional. |

### Movimentação manual do objetivo

| Campo | Tipo | Regra |
|---|---|---|
| `objective_id` | FK | Obrigatório; deve pertencer ao usuário autenticado. |
| `movement_type` | enum | `contribution`, `withdrawal` ou `adjustment`. |
| `amount_cents` | inteiro | Obrigatório e maior que zero para aporte/retirada; ajuste informa o novo saldo desejado. |
| `movement_date` | ISO `YYYY-MM-DD` | Obrigatório. |
| `funding_source_type` | enum | Opcional: investimento consolidado (`investment_asset`); contas correntes não são origens elegíveis. |
| `funding_source_id` | inteiro | Obrigatório quando uma origem for vinculada. |
| `notes` | texto | Opcional. |

### Resumo calculado

| Campo | Tipo | Regra |
|---|---|---|
| `reserved_balance_cents` | inteiro | Soma determinística das movimentações manuais vigentes do objetivo. |
| `remaining_amount_cents` | inteiro | Alvo com margem menos saldo reservado, nunca menor que zero. |
| `recommended_monthly_contribution_cents` | inteiro | Aporte projetado para atingir o alvo na data. |
| `projected_yield_cents` | inteiro | Rendimento estimado; não altera o saldo reservado. |
| `progress_percentage` | decimal | Proporção entre saldo reservado e alvo com margem. |
| `pace_status` | enum | `on_track`, `attention`, `late`, `paused`, `completed` ou `overdue`. |
| `projection.scenarios` | objeto | Compara o cenário conservador e o cenário com rendimento, sempre discriminando saldo reservado, aportes futuros, rendimento projetado e valor descoberto em centavos. |

### Reserva de Emergência

O resumo reutiliza as posições e aportes de Poupança/Renda Fixa já marcados com `emergency_reserve_eligible` no Portfólio. Para cada componente, apresenta ativo, tipo, carteira/conta, moeda, valor atual na moeda de origem, valor normalizado em BRL, liquidez ou vencimento disponível e fonte da cotação.

Um vínculo de cobertura representa o ativo financeiro inteiro na carteira selecionada, não um lote ou lançamento isolado. O app consolida compras/aportes e posições iniciais que compartilham a identidade do ativo (conta/carteira, moeda, tipo, identificador, nome e, para renda fixa, indexador e vencimento) e acompanha o valor atual consolidado. A identidade inclui o vencimento para distinguir títulos diferentes, mas não inclui a taxa de compra, pois aportes do mesmo título podem ter taxas distintas.

## Regras

### Navegação e tipos

- **Limites** passa a ter as abas **Gastos** e **Objetivos**; nenhuma regra dos limites de gastos existentes é alterada.
- `target` representa uma meta com valor e data, como viagem ou entrada de imóvel.
- `annual_provision` representa uma despesa previsível com vencimento, como IPVA, seguro ou matrícula.
- `continuous_reserve` representa uma reserva sem data final obrigatória, como manutenção ou colchão financeiro adicional.
- Objetivos concluídos podem ser reabertos; objetivos arquivados permanecem no histórico e não recebem novas movimentações.

### Saldo e atualização manual

- O saldo reservado exibido e usado nas projeções é a soma do saldo manual (aportes, retiradas e ajustes auditáveis) com o valor atual, convertido para BRL, dos investimentos vinculados. A API discrimina os dois componentes.
- Vincular ou desvincular um investimento não cria movimentação manual. A valorização do ativo atualiza a parcela vinculada sem alterar o histórico de movimentações do objetivo.
- Criar uma movimentação de objetivo não cria automaticamente lançamento, transferência, aporte de investimento nem alteração de saldo bancário.
- Somente investimentos podem ser vinculados; contas correntes não aparecem como opção e sua tentativa de vínculo pela API é rejeitada.
- O vínculo agrega todos os movimentos/lotes do mesmo ativo financeiro e acompanha seu valor atual consolidado; novos movimentos compatíveis passam a compor o mesmo ativo.
- Cotações, CDI e valores atuais do Portfólio podem ser atualizados automaticamente pelas integrações existentes, mas são exibidos apenas como referência de cobertura e projeção.
- Rendimento projetado nunca é incorporado automaticamente ao saldo reservado; para reconhecer rendimento efetivamente disponível, o usuário registra um ajuste manual.
- Aportes, retiradas e ajustes geram Histórico de Operações sem expor notas sensíveis além do necessário.

### Projeção de aportes e CDI

- Sem rendimento, o aporte recomendado corresponde ao valor restante dividido pela quantidade de aportes mensais até a data, em centavos, distribuindo eventual resto sem perda de centavos.
- No modo CDI, o app usa a referência de CDI já disponível no núcleo de investimentos e o percentual configurado, com padrão de 100% do CDI.
- Aportes mensais são projetados no início de cada mês; cada aporte acumula rendimento pelo prazo remanescente até o vencimento.
- Como o CDI futuro é desconhecido, o resultado deve ser identificado como projeção e deve mostrar taxa, data de referência e premissas usadas.
- O tratamento `conservative` calcula o aporte sem descontar rendimento e exibe o ganho potencial separadamente.
- O tratamento `taxable` pode estimar IOF e IR regressivo com as mesmas regras já usadas em Renda Fixa; `exempt` não desconta tributos.
- Mudanças de CDI ou da taxa personalizada recalculam projeção, aporte recomendado e estado, sem alterar movimentações manuais já registradas.
- A margem de segurança aumenta somente o alvo efetivo de cálculo, sem alterar o valor nominal informado pelo usuário.
- O gráfico de projeção apenas apresenta valores calculados pelo núcleo Python; o frontend não recalcula juros, aportes ou cobertura.
- O cenário conservador desconsidera rendimento. O cenário com rendimento preserva os mesmos aportes futuros e apresenta o rendimento potencial separadamente, sem incorporá-lo ao saldo manual.

### Reserva de Emergência e exclusividade

- A aba Objetivos exibe um resumo da Reserva de Emergência antes da lista de objetivos, contendo valor total em BRL e detalhamento dos investimentos componentes.
- A composição da Reserva de Emergência continua sendo definida exclusivamente pelas marcações explícitas do Portfólio; nenhum objetivo entra nela automaticamente.
- Um ativo com qualquer componente marcado como Reserva de Emergência não pode ser vinculado nem contabilizado como origem de outro objetivo.
- Uma origem vinculada a um objetivo não pode ser posteriormente marcada como Reserva de Emergência enquanto o vínculo estiver ativo.
- Uma mesma origem não pode cobrir simultaneamente dois objetivos ativos; o usuário deve desvinculá-la ou encerrar o objetivo anterior.
- Para o MVP, a exclusividade é por ativo consolidado inteiro, não por lote/fração. Um Tesouro Prefixado 2027 marcado como Reserva de Emergência fica integralmente indisponível para IPVA, viagem ou qualquer outro objetivo.
- Recursos sem origem vinculada são permitidos como reserva manual, mas a interface deve informar que o valor ainda não possui cobertura financeira conferível pelo app.
- O total reservado sem origem e o total coberto por origens vinculadas devem ser apresentados separadamente.
- A remoção de um vínculo não apaga as movimentações do objetivo; apenas muda o estado de cobertura para não vinculado.
- Componentes da Reserva são agrupados pela carteira do Portfólio; cada grupo mostra subtotal e até três títulos inicialmente, com expansão e recolhimento dos demais sob demanda.

### Estados

- `completed`: saldo reservado igual ou superior ao alvo efetivo.
- `overdue`: data desejada passou e o objetivo não foi concluído.
- `paused`: objetivo explicitamente suspenso; não cobra aporte enquanto pausado.
- `on_track`: saldo atual e aportes futuros recomendados permitem alcançar o alvo na data.
- `attention`: existe insuficiência recuperável com aumento de até 20% sobre o aporte planejado atual.
- `late`: exige aumento superior a 20% ou aporte imediato para atingir o alvo.
- Estados e projeções são recalculados automaticamente após movimentação, alteração do objetivo ou atualização das referências financeiras.

## API e dados

| Método | Rota | Finalidade |
|---|---|---|
| `GET` | `/api/financial-goals` | Lista objetivos com progresso, cobertura e projeções. |
| `POST` | `/api/financial-goals` | Cria objetivo. |
| `PUT` | `/api/financial-goals/{id}` | Edita, pausa, reabre ou conclui objetivo. |
| `DELETE` | `/api/financial-goals/{id}` | Arquiva objetivo, preservando histórico. |
| `GET` | `/api/financial-goals/{id}/movements` | Lista movimentações do objetivo. |
| `POST` | `/api/financial-goals/{id}/movements` | Registra aporte, retirada ou ajuste manual. |
| `DELETE` | `/api/financial-goals/{id}/movements/{movement_id}` | Estorna movimentação manual com auditoria. |
| `GET` | `/api/financial-goals/{id}/funding-sources` | Lista as origens vinculadas ao objetivo. |
| `POST` | `/api/financial-goals/{id}/funding-sources` | Vincula um investimento consolidado. |
| `DELETE` | `/api/financial-goals/{id}/funding-sources/{link_id}` | Remove o vínculo sem apagar as movimentações do objetivo. |
| `GET` | `/api/financial-goals/emergency-reserve` | Retorna total e componentes atuais da Reserva de Emergência. |

Tabelas propostas:

- `financial_goals`: definição, estado e premissas de projeção.
- `financial_goal_movements`: livro imutável de aportes, retiradas, ajustes e estornos.
- `financial_goal_funding_sources`: vínculos exclusivos com ativos de investimento consolidados, identificados por uma entrada canônica do ativo.

As tabelas devem ser criadas pela migração incremental idempotente do schema v2. Valores monetários são inteiros em centavos. Regras, projeções e validações de sobreposição pertencem ao núcleo Python, nunca ao frontend.

## Critérios de aceite

1. Dado o menu Limites, quando a tela é aberta, então são exibidas as abas **Gastos** e **Objetivos** sem alterar os limites existentes.
2. Dado um objetivo de R$ 12.000 com R$ 3.000 reservados, quando exibido, então mostra R$ 9.000 restantes e 25% de progresso.
3. Dado um aporte manual de R$ 500, quando confirmado, então o saldo reservado aumenta exatamente R$ 500 sem criar lançamento financeiro.
4. Dada uma retirada manual de R$ 200 com saldo manual suficiente, quando confirmada, então o saldo manual diminui exatamente R$ 200 sem alterar o investimento vinculado.
5. Dada uma retirada maior que o saldo manual, quando enviada, então é rejeitada com mensagem amigável.
6. Dado um ajuste manual, quando confirmado, então o novo saldo é atingido por movimentação auditável sem reescrever o histórico anterior.
7. Dada uma provisão sem rendimento, quando calculada, então a soma dos aportes recomendados em centavos cobre exatamente o valor restante na data.
8. Dada uma provisão configurada em 100% do CDI, quando calculada, então a projeção mostra a taxa e a data de referência utilizadas.
9. Dada uma projeção conservadora, quando exibida, então o rendimento potencial não reduz o aporte mensal necessário.
10. Dada uma projeção tributável, quando calculada, então usa IOF e IR regressivo conforme as regras existentes de Renda Fixa.
11. Dada uma atualização da referência do CDI, quando os objetivos são recarregados, então projeções são recalculadas sem alterar o saldo reservado.
12. Dado um objetivo pausado, quando exibido, então não apresenta aporte em atraso enquanto permanecer pausado.
13. Dado um objetivo cujo saldo alcançou o alvo, quando recalculado, então seu estado é `completed`.
14. Dado um objetivo não concluído após a data desejada, quando recalculado, então seu estado é `overdue`.
15. Dada uma posição de Poupança marcada como Reserva de Emergência, quando o usuário tenta vinculá-la à provisão do IPVA, então o vínculo é bloqueado e a sobreposição é explicada.
16. Dada uma origem já vinculada a um objetivo ativo, quando o usuário tenta vinculá-la a outro, então o segundo vínculo é bloqueado.
17. Dado um ativo vinculado a um objetivo, quando o usuário tenta marcar qualquer lote dele como Reserva de Emergência no Portfólio, então a marcação é bloqueada até a desvinculação.
18. Dada uma origem desvinculada de um objetivo, quando o objetivo é consultado, então suas movimentações são preservadas e a cobertura aparece como não vinculada.
19. Dado um valor reservado sem origem vinculada, quando exibido, então aparece separado do valor coberto e com aviso de ausência de cobertura conferível.
20. Dadas posições elegíveis marcadas como Reserva de Emergência, quando o resumo é aberto, então mostra o valor total normalizado em BRL e cada investimento componente.
21. Dada uma posição não marcada como Reserva de Emergência, quando o resumo é calculado, então ela não participa do total nem da lista de componentes.
22. Dado um componente da Reserva com cotação atualizada, quando o resumo é recarregado, então o valor de referência muda sem criar aporte ou ajuste no objetivo.
23. Dado um usuário tentando consultar ou alterar objetivo de outro usuário, quando a rota é acionada, então a operação é rejeitada sem revelar os dados existentes.
24. Dada uma mutação com Host ou Origin inválido, quando enviada, então é rejeitada antes de qualquer escrita.
25. Dado um objetivo arquivado, quando a listagem principal é aberta, então ele não aparece entre os ativos e suas movimentações permanecem disponíveis no histórico.
26. Dado um aporte, retirada, ajuste, pausa, conclusão, arquivamento ou mudança de vínculo, quando confirmado, então o Histórico de Operações registra a ação e alterações relevantes.
27. Dado um objetivo ativo, quando seu card é exibido, então o gráfico discrimina valor reservado, aportes futuros, rendimento projetado e valor ainda descoberto sem duplicar parcelas.
28. Dado um objetivo com rendimento configurado, quando a projeção é exibida, então o usuário compara lado a lado o cenário conservador e o cenário com rendimento, mantendo o aporte conservador como recomendação oficial.
29. Dada uma conta corrente, quando exibidas as opções de cobertura ou enviado um vínculo direto pela API, então a conta não é oferecida e o vínculo é rejeitado.
30. Dado um investimento vinculado, quando o saldo reservado e a projeção do objetivo são exibidos, então somam o saldo manual às posições atuais consolidadas do ativo em BRL e discriminam cada parcela.
31. Dados vários aportes/lotes do mesmo ativo (incluindo compras posteriores), quando o vínculo é criado ou atualizado, então o ativo aparece uma única vez com o valor agregado e não pode ser alocado a outro objetivo.
32. Dado qualquer lote de um ativo vinculado a um objetivo, quando marcado como Reserva de Emergência, então a marcação é bloqueada para impedir dupla alocação do ativo.
33. Dada uma carteira com mais de três investimentos marcados como Reserva de Emergência, quando o resumo é exibido, então o total da reserva permanece destacado, cada carteira mostra seu subtotal e até três títulos, e um controle acessível revela/recolhe os demais. Verificação visual manual.
34. Dada a aba Objetivos, quando não há criação ou edição em andamento, então o formulário fica recolhido e há uma ação **+ Novo objetivo** em destaque; ao criar ou editar, o formulário abre sob demanda e pode ser cancelado sem salvar.
35. Dada a aba Objetivos sem nenhum objetivo cadastrado, quando aberta, então a Reserva de Emergência é carregada e exibida normalmente, sem depender da criação de um objetivo.

## Pendências

> [!question] Pendências
> O vínculo por ativo consolidado aguarda validação em homologação. A possibilidade futura de dividir um mesmo ativo em frações destinadas a objetivos diferentes fica explicitamente fora deste MVP.

## Fora de escopo

- Movimentar dinheiro automaticamente entre contas, bancos, investimentos ou cofrinhos.
- Sincronizar saldos reservados por Open Finance.
- Reconhecer rendimento estimado como aporte efetivo sem confirmação do usuário.
- Permitir que a mesma origem componha simultaneamente a Reserva de Emergência e outro objetivo.
- Vincular contas correntes ou dividir uma posição de investimento em frações destinadas a objetivos diferentes no MVP.
- Recomendar produto financeiro específico para guardar o dinheiro.
- Garantir o CDI futuro ou o valor final de qualquer projeção.
- Enviar notificações externas, e-mail ou push no MVP.

## Plano de implementação

- [x] Passo 1 — Validar a modelagem final com os agregados atuais do Portfólio e documentar o novo fluxo em `docs/arquitetura.md` e `docs/requisitos.md`. Fecha: critérios 1, 20 a 22.
- [x] Passo 2 — Criar migrações idempotentes das três tabelas, índices, isolamento por usuário, arquivamento e restrições de vínculo. Fecha: critérios 15 a 19, 23 e 25.
- [x] Passo 3 — Implementar `financeiro/financial_goals.py` com CRUD, livro de movimentações em centavos, estados, cobertura e validações de domínio. Fecha: critérios 2 a 6, 12 a 19 e 23 a 25.
- [x] Passo 4 — Implementar projeções sem rendimento, CDI, margem e tributação, reutilizando referências e regras do núcleo de investimentos sem duplicar lógica financeira. Fecha: critérios 7 a 11 e 14.
- [x] Passo 5 — Expor o resumo de Reserva de Emergência com total BRL, componentes, origem dos valores e validação cruzada de exclusividade com o Portfólio. Fecha: critérios 15, 17 e 20 a 22.
- [x] Passo 6 — Adicionar rotas autenticadas em `app.py`, validação de propriedade e proteção Host/Origin em todas as mutações. Fecha: critérios 3 a 6, 23 a 25.
- [x] Passo 7 — Criar a aba **Objetivos** dentro de Limites, formulários, cards de progresso, estados, projeções, cobertura, resumo da Reserva de Emergência e comparação gráfica dos cenários. Fecha: critérios 1, 2, 7 a 16, 18 a 22, 27 e 28.
- [x] Passo 8 — Integrar ações ao Histórico de Operações com descrição segura e alterações estruturadas. Fecha: critério 26.
- [x] Passo 9 — Adicionar testes automatizados de domínio, persistência, API, isolamento, cálculos em centavos, CDI, tributação, dupla alocação e contratos do frontend. Fecha: critérios 1 a 28.
- [x] Passo 10 — Executar validação manual local da navegação, criação, projeção CDI, gráfico comparativo e resumo da Reserva; os demais fluxos críticos permanecem cobertos pelos testes automatizados de domínio. Fecha: critérios 1, 8, 12, 13, 15, 17 e 20.
- [x] Passo 11 — Restringir vínculos a investimentos, consolidar todos os lotes/movimentos pela identidade do ativo, incorporar o valor atual agregado ao saldo e à projeção e bloquear sobreposição com a Reserva de Emergência. Fecha: critérios 29 a 32.
- [x] Passo 12 — Agrupar visualmente os componentes da Reserva por carteira, calcular subtotais no núcleo em centavos e permitir expansão/recolhimento de títulos excedentes. Fecha: critério 33.
- [x] Passo 13 — Recolher o formulário de objetivo por padrão, abrir sob demanda pela ação primária e reutilizá-lo para edição com cancelamento acessível. Fecha: critério 34.
- [x] Passo 14 — Desacoplar a carga e a renderização da Reserva de Emergência da resposta da lista de objetivos, mantendo a reserva visível mesmo quando a lista está vazia. Fecha: critério 35.

## Changelog

- `0.10` — 2026-09-24 — A Reserva de Emergência carrega e aparece ao abrir Objetivos mesmo sem objetivos cadastrados; suas falhas de carregamento são isoladas da lista.
- `0.9` — 2026-09-24 — Formulário de criação deixa de ocupar espaço permanente; ação primária abre o formulário para criação e edição sob demanda.
- `0.8` — 2026-09-24 — Reserva de Emergência passa a exibir subtotais por carteira e revelar títulos excedentes sob demanda, mantendo o total geral em destaque.
- `0.7` — 2026-09-24 — A série de aportes futuros e sua legenda usam o token azul `--chart-6`, mantendo a semântica de projeção sem roxo e com suporte aos temas claro/escuro.
- `0.6` — 2026-09-23 — Ajuste solicitado durante homologação: origens de objetivos ficam restritas a investimentos consolidados; o valor atual de todos os movimentos do ativo passa a compor o saldo reservado e as projeções.

- `0.5` — 2026-09-23 — Portada a implantação para a arquitetura da V2, com migração incremental, rotas declarativas e gráfico ApexCharts comparando os cenários conservador e com rendimento por saldo reservado, aportes futuros, rendimento projetado e valor descoberto.
- `0.4` — 2026-09-23 — Implantada a aba Objetivos dentro de Limites com resumo da Reserva de Emergência, indicadores consolidados, formulário responsivo, cards com anel de progresso, atualização manual de saldo, estados, cobertura, vínculo/desvínculo de origens e testes de contrato do frontend.
- `0.3` — 2026-09-23 — Implementados vínculos de cobertura por conta ou componente de investimento, exclusividade entre objetivos, bloqueio bidirecional com a Reserva de Emergência, rotas de vínculo, auditoria e testes de sobreposição/desvinculação.
- `0.2` — 2026-09-23 — Implementação iniciada com schema idempotente, núcleo Python, CRUD de objetivos, movimentações manuais, resumo da Reserva de Emergência, rotas autenticadas e testes unitários da fundação.
- `0.1` — 2026-09-23 — Spec inicial de objetivos, provisões, projeção por CDI, movimentações manuais, resumo da Reserva de Emergência e prevenção de dupla alocação.

## Relacionados

- [[limites-gastos]]
- [[investimentos-portfolio]]
- [[score-saude-financeira]]
- [[cockpit-calendario]]
- [[historico-operacoes]]
- [[arquitetura]]
