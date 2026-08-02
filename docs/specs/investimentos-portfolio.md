---
tipo: spec
area: investimentos
status: implementado
versao: 2.7
atualizado: 2026-07-31
relacionados:
  - "[[contas-correntes]]"
  - "[[lancamentos]]"
  - "[[relatorios]]"
  - "[[arquitetura]]"
tags: [spec, "area/investimentos"]
aliases: ["Investimentos", "Portfólio"]
---

# Investimentos e Portfólio

> [!info] Status
> **implementado** · área: `investimentos` · atualizado em 2026-07-29 · relacionados: [[contas-correntes]], [[lancamentos]], [[relatorios]]

## Problema

O usuário precisa consolidar e acompanhar a valorização de seus ativos de investimento em um portfólio unificado, com atualização automática de preços quando disponível e cálculo de taxas e tributos quando aplicável.

## Usuário

Qualquer usuário autenticado localmente que possua investimentos e queira monitorar o patrimônio consolidado.

## Jornada

1. Cadastra posições iniciais históricas (`opening positions`) especificando ativo, quantidade, custo de aquisição, indexadores (renda fixa), taxa e data de aquisição.
2. Registra aportes como lançamentos normais do sistema (inclusive recorrentes). Ver [[lancamentos]].
3. Acompanha o portfólio com custo, valor atual, resultado, rentabilidade, variação diária e posições agrupáveis.
4. Atualiza manualmente o valor atual de posições sem cotação/indexador confiável.
5. Efetua resgates e encerramentos para devolver valor à conta de origem e mover posições para histórico.

## Tipos de ativos

| Tipo | Código |
|---|---|
| Ações / ETFs / BDRs | `stock` |
| Criptoativos | `crypto` |
| Fundos | `fund` |
| Renda Fixa | `fixed_income` |
| Previdência Privada | `private_pension` |
| Poupança | `savings` |
| Outros | `other` |

## Regras

**Geral:**
- Cada ativo é mantido e exibido na moeda da conta/carteira onde está custodiado.
- Conversões entre moedas ocorrem nos lançamentos de câmbio, não dentro do ativo. Ver [[lancamentos]].
- Cards de consolidação por classe, indexador, moeda e carteira exibem valores na moeda original do grupo.
- As barras dos cards de consolidação usam sempre o valor atual normalizado para BRL apenas para escala visual; para moedas diferentes de BRL, a normalização usa a cotação do fechamento anterior.
- Posição inicial cadastrada no Portfólio não movimenta conta.
- Operação de investimento criada por lançamento de conta afeta o saldo da conta.
- Posições iniciais e operações de aporte elegíveis podem ser marcadas explicitamente como parte da reserva de emergência para uso analítico pelo [[score-saude-financeira]]; nenhuma posição ou aporte entra automaticamente nessa reserva.

**Renda Fixa:**
- Pós-fixados/híbridos usam indexadores (CDI, SELIC, IPCA, IGP-M, TR) via API do Banco Central (SGS).
- Pré-fixados usam a taxa acordada anual nominal/efetiva informada no campo de taxa; exibem `Pré-fixado` e a taxa antes do vencimento.
- No cadastro de renda fixa, a interface deve diferenciar claramente: `Pré-fixada` usa taxa em `% a.a.`; `Pós-fixada` usa percentual do indexador (ex.: `123` com CDI significa `123% do CDI`, enquanto vazio/zero representa `100% do CDI`); `Híbrida` usa indexador mais taxa adicional em `% a.a.`.
- Para aplicações como CDB `123% do CDI`, a interface deve orientar o usuário a selecionar modalidade `Pós-fixada`, indexador `CDI` e percentual `123`, evitando cadastrar como `Pré-fixada` ou `Híbrida`; essa orientação deve ficar em helper contextual acionado por ícone discreto para preservar espaço e alinhamento do formulário, com exemplos objetivos de pré-fixada, pós-fixada e híbrida.
- Campos de quantidade e preço médio/unitário não devem ser exibidos para renda fixa, pois o custo total/aporte é a base de cálculo relevante.
- O sistema calcula e deduz estimativas de IOF (até 30 dias) e IR (tabela regressiva de 22,5% a 15%).
- Para títulos do Tesouro Direto, o sistema mantém o cálculo de rentabilidade **na curva**, usando a taxa contratada cadastrada, sem tentar igualar a marcação a mercado exibida pelo site do Tesouro em resgate antecipado.
- Para títulos do Tesouro Direto padrão (Prefixado, IPCA+ e Selic), o sistema calcula e deduz uma **Taxa B3 estimada** de 0,20% a.a. pro rata sobre o valor da posição estimado na curva. Para Tesouro Selic, aplica isenção simplificada até R$ 10.000,00 sobre a posição; acima desse valor, a estimativa incide apenas sobre o excedente. Para Tesouro RendA+ e Tesouro Educa+, o sistema não calcula automaticamente a taxa B3 na primeira versão, pois essas modalidades possuem regras específicas por prazo, resgate antecipado e faixa de recebimento.
- O módulo Portfólio deve exibir nota discreta informando que diferenças frente ao site do Tesouro podem ocorrer por marcação a mercado em resgate antecipado, provisão oficial de taxas e regras específicas do título.
- Posições de renda fixa com vencimento igual ou anterior à data atual devem gerar alerta visual no menu Portfólio e aviso no Cockpit até que sejam encerradas.
- Posições iniciais e aportes de renda fixa podem ser marcados explicitamente como reserva de emergência quando o usuário entender que têm liquidez compatível, sem inferência automática pelo sistema.

**Poupança (`savings`):**
- Não aparece como subcategoria de Renda Fixa no formulário.
- Posições iniciais podem informar lista de aniversários (data/valor).
- Lançamentos classificados como Poupança geram automaticamente um aniversário na data do lançamento.
- Cálculo: TR + 0,5% a.m. quando Selic > 8,5% a.a.; TR + 70% da Selic equivalente mensal quando Selic ≤ 8,5% a.a.
- Não há cálculo de IOF/IR para Poupança.
- Posições e aportes de Poupança podem ser marcados explicitamente como reserva de emergência, mas a marcação deve ser decisão do usuário.
- A marcação de reserva de emergência deve ser visualmente discreta no formulário, com peso menor que campos financeiros principais.
- Em aportes de Poupança criados por Lançamentos de Contas, o formulário deve ocultar campos não aplicáveis como quantidade, preço unitário, renda fixa, CNPJ, corretagem, emolumentos, impostos e outros custos.

**Previdência Privada (`private_pension`):**
- Lançamentos classificados como `Previdência Privada`, `PGBL` ou `VGBL` geram operações do tipo `private_pension`.
- Valor atual pode ser ajustado manualmente quando não houver indexador/cotação confiável.

**Renda Variável / Criptos:**
- Cotações via Yahoo Finance (ações/fundos) e CoinGecko/Yahoo (criptoativos).
- Criptos usam pares de cotação na moeda do ativo/carteira (ex.: BTC/BRL ou BTC/USD).

**Resgates e encerramentos:**
- Resgates retornam valor para a conta da carteira. Em posições com múltiplas origens, consumo segue FIFO.
- Resgates e atualização manual de valor atual devem usar modais internos do app, com campos rotulados, valor padrão preenchido e ação secundária de cancelamento, evitando prompts nativos do navegador.
- Encerramento move a posição para Histórico com os valores no momento do resgate/fechamento.
- No encerramento, o usuário informa data, valor final e pode optar por registrar o valor final como receita na conta da carteira em um modal único de decisão.
- A opção de registrar crédito deve ficar desmarcada por padrão para evitar duplicidade com resgates ou créditos já lançados.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/portfolio` |
| `POST` | `/api/portfolio/positions` |
| `PUT` | `/api/portfolio/positions/{id}` |
| `DELETE` | `/api/portfolio/positions/{id}` |
| `POST` | `/api/portfolio/redeem` |
| `POST` | `/api/portfolio/close` |
| `PUT` | `/api/portfolio/value` |

Tabelas: `investment_opening_positions` e `investment_operations` (incluem `emergency_reserve_eligible` para posições/aportes elegíveis), `investment_redemptions`, `investment_closed_positions`, `investment_value_overrides`, `transactions`, `checking_accounts`, `quote_cache`.

## Plano de implementação

- [x] Atualizar rótulos e dicas dos campos de renda fixa no lançamento de investimento.
- [x] Atualizar rótulos e dicas dos campos de renda fixa na posição inicial do Portfólio.
- [x] Sincronizar as dicas quando o usuário altera a modalidade.
- [x] Preservar a fórmula e os dados persistidos, alterando apenas a comunicação visual.
- [x] Validar sintaxe e conferir manualmente os textos no formulário.
- [x] Ocultar quantidade e preço médio/unitário para renda fixa.
- [x] Substituir dicas fixas por helper contextual acionado por ícone no cadastro de renda fixa.
- [x] Explicitar que pós-fixado usa percentual do indexador, com vazio/zero representando 100%, enquanto híbrido usa taxa adicional.
- [x] Incluir exemplos de pré-fixada, pós-fixada e híbrida no helper contextual.

## Critérios de aceite

- Dado ativos de diferentes classes cadastrados, quando o portfólio é exibido, aparecem agrupados por classe com cotações atualizadas.
- Dado consolidações por classe, indexador, moeda ou carteira com moedas distintas, quando as barras são exibidas, seu tamanho é calculado pelo valor atual convertido para BRL, enquanto o texto mantém a moeda original.
- Dado um ativo de renda fixa pós-fixado, quando listado, exibe indexador, taxa e rendimento bruto/líquido com impostos regressivos.
- Dado um ativo pré-fixado, quando listado, exibe `Pré-fixado` e a taxa anual.
- Dado o usuário cadastrando renda fixa, quando alterna entre pré-fixada, pós-fixada e híbrida, então o campo explica a unidade correta e orienta que `123% do CDI` deve ser cadastrado como pós-fixado com indexador CDI e percentual 123, enquanto CDI puro pode ficar vazio/zero para representar 100%.
- Dado o usuário cadastrando renda fixa, quando precisa de orientação sobre pré-fixada, pós-fixada ou híbrida, então um ícone discreto abre um helper contextual sem ocupar espaço permanente no formulário.
- Dado o helper contextual de renda fixa aberto, quando exibido, então apresenta exemplos de preenchimento para pré-fixada, pós-fixada e híbrida.
- Dado o usuário cadastrando renda fixa, quando seleciona esse tipo de ativo, então campos de quantidade e preço médio/unitário ficam ocultos e não são enviados no formulário.
- Dado uma posição de renda fixa vencendo hoje ou vencida, quando o usuário navega pelo app, o item Portfólio no menu aparece em estado de alerta e o Cockpit exibe um aviso acionável.
- Dado uma posição vencida já encerrada, quando o portfólio é recarregado, o alerta de menu e o aviso do Cockpit deixam de considerar essa posição.
- Dado um ativo em moeda estrangeira, quando listado, é exibido na própria moeda sem conversão visual redundante.
- Dado um ativo em moeda estrangeira com valor atual informado manualmente, quando o resultado e a rentabilidade são exibidos, então a diferença entre valor atual e custo é calculada na moeda original do ativo; valores normalizados em BRL podem aparecer apenas como informação secundária ou escala visual.
- Dado uma posição com múltiplas origens, quando expandida, exibe os lançamentos/posições que a compõem.
- Dado um resgate realizado, quando executado, o valor retorna à conta de origem e a posição é atualizada via FIFO.
- Dado o usuário clicando em `Resgatar`, quando o formulário é aberto, então o sistema exibe um modal interno com data e valor do resgate preenchidos por padrão, além de ação de cancelar sem alterar a posição.
- Dado o usuário clicando em `Atualizar valor atual`, quando o formulário é aberto, então o sistema exibe um modal interno com data e valor atual preenchidos por padrão, além de ação de cancelar sem alterar a posição.
- Dado um encerramento sem a opção de crédito, quando executado, a posição vai para o histórico sem criar lançamento financeiro.
- Dado um encerramento com a opção de crédito marcada, quando executado, o sistema cria uma receita na conta da carteira e soma o valor final ao saldo da conta.
- Dado o modal de encerramento aberto, quando o usuário escolhe `Voltar`, a posição permanece aberta e nenhum lançamento é criado.
- Dado o usuário cadastrando ou editando uma posição inicial de Poupança ou Renda Fixa, quando marca `Usar esta posição como reserva de emergência`, então a posição é persistida com `emergency_reserve_eligible = 1` e essa marcação volta preenchida ao editar.
- Dado o usuário cadastrando outro tipo de ativo, quando envia o formulário, então o sistema ignora qualquer valor de `emergency_reserve_eligible` e persiste a posição como não elegível para reserva.
- Dado o formulário de posição inicial com opção de reserva visível, quando exibido, então a marcação aparece como controle compacto/discreto e não compete visualmente com os campos principais.
- Dado o usuário cadastrando ou editando um aporte de Poupança ou Renda Fixa em Lançamentos de Contas, quando marca `Usar este aporte como reserva de emergência`, então a operação é persistida com `emergency_reserve_eligible = 1`, aparece marcada ao editar o lançamento e passa a compor a reserva elegível do Portfólio/Score.
- Dado o usuário cadastrando ou editando um aporte de Poupança em Lançamentos de Contas, quando o formulário é exibido, então os campos não aplicáveis à Poupança ficam ocultos/desabilitados e não competem com os campos essenciais.
- Dado uma posição de Tesouro Prefixado, IPCA+ ou Selic padrão com cálculo na curva, quando o Portfólio calcula o valor líquido, então deduz a Taxa B3 estimada de 0,20% a.a. pro rata, aplicando isenção simplificada de R$ 10.000,00 apenas para Tesouro Selic.
- Dado uma posição de Tesouro Direto exibida no Portfólio, quando o usuário lê a listagem, então há nota discreta informando que o cálculo é na curva e pode divergir da marcação a mercado do site do Tesouro.

## Changelog

- `2.7` — 2026-07-31 — Tesouro Direto mantém rentabilidade na curva pela taxa contratada, passa a deduzir Taxa B3 estimada em títulos padrão e exibe nota sobre diferenças frente à marcação a mercado oficial.
- `2.6` — 2026-07-29 — Resgate e atualização manual de valor atual passam a ser documentados como modais internos consistentes com a identidade visual do app.
- `2.5` — 2026-07-29 — Resultado e rentabilidade de ativos em moeda estrangeira com valor manual ficam explicitamente calculados na moeda original; BRL permanece apenas como referência secundária/escala visual.
- `2.4` — 2026-07-29 — Aportes de Poupança em Lançamentos de Contas passam a ocultar campos não aplicáveis no formulário de investimento.
- `2.3` — 2026-07-29 — Operações de aporte de Poupança e Renda Fixa criadas por Lançamentos de Contas também podem ser marcadas como reserva de emergência.
- `2.2` — 2026-07-29 — Checkbox de reserva de emergência no Portfólio passa a usar apresentação compacta e discreta.
- `2.1` — 2026-07-28 — Posições iniciais de Poupança e Renda Fixa podem ser marcadas explicitamente como elegíveis para reserva de emergência, com persistência em `investment_opening_positions`.
- `2.0` — 2026-07-26 — Helper contextual de renda fixa passa a trazer exemplos explícitos para pré-fixada, pós-fixada e híbrida.
- `1.9` — 2026-07-26 — Texto de renda fixa clarifica que pós-fixado usa percentual do indexador, vazio/zero representa 100% e híbrido usa taxa adicional.
- `1.8` — 2026-07-26 — Orientações de renda fixa passam a ficar em helper contextual acionado por ícone, preservando espaço e alinhamento dos campos.
- `1.7` — 2026-07-26 — Campos de quantidade e preço médio/unitário deixam de aparecer nos cadastros de renda fixa.
- `1.6` — 2026-07-26 — Formulários de renda fixa passam a explicitar a diferença entre taxa pré-fixada em `% a.a.` e percentual do indexador em pós-fixados.
- `1.5` — 2026-07-20 — UX de encerramento documentado como modal único com data, valor final e opção de crédito.
- `1.4` — 2026-07-20 — Opção de registrar crédito na conta no encerramento de posição, desmarcada por padrão.
- `1.3` — 2026-07-20 — Alertas de vencimento de renda fixa no menu Portfólio e no Cockpit documentados.
- `1.2` — 2026-06-30 — Regra das barras de consolidação documentada: escala por valor atual normalizado em BRL e exibição na moeda original.
- `1.1` — 2026-06-30 — Método do ajuste manual de valor corrigido para refletir a API real (`PUT /api/portfolio/value`).
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[contas-correntes]]
- [[lancamentos]]
- [[relatorios]]
- [[arquitetura]]
