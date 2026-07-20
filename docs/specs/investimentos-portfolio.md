---
tipo: spec
area: investimentos
status: implementado
versao: 1.5
atualizado: 2026-07-20
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
> **implementado** · área: `investimentos` · atualizado em 2026-07-20 · relacionados: [[contas-correntes]], [[lancamentos]], [[relatorios]]

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

**Renda Fixa:**
- Pós-fixados/híbridos usam indexadores (CDI, SELIC, IPCA, IGP-M, TR) via API do Banco Central (SGS).
- Pré-fixados usam a taxa acordada anual; exibem `Pré-fixado` e a taxa antes do vencimento.
- O sistema calcula e deduz estimativas de IOF (até 30 dias) e IR (tabela regressiva de 22,5% a 15%).
- Posições de renda fixa com vencimento igual ou anterior à data atual devem gerar alerta visual no menu Portfólio e aviso no Cockpit até que sejam encerradas.

**Poupança (`savings`):**
- Não aparece como subcategoria de Renda Fixa no formulário.
- Posições iniciais podem informar lista de aniversários (data/valor).
- Lançamentos classificados como Poupança geram automaticamente um aniversário na data do lançamento.
- Cálculo: TR + 0,5% a.m. quando Selic > 8,5% a.a.; TR + 70% da Selic equivalente mensal quando Selic ≤ 8,5% a.a.
- Não há cálculo de IOF/IR para Poupança.

**Previdência Privada (`private_pension`):**
- Lançamentos classificados como `Previdência Privada`, `PGBL` ou `VGBL` geram operações do tipo `private_pension`.
- Valor atual pode ser ajustado manualmente quando não houver indexador/cotação confiável.

**Renda Variável / Criptos:**
- Cotações via Yahoo Finance (ações/fundos) e CoinGecko/Yahoo (criptoativos).
- Criptos usam pares de cotação na moeda do ativo/carteira (ex.: BTC/BRL ou BTC/USD).

**Resgates e encerramentos:**
- Resgates retornam valor para a conta da carteira. Em posições com múltiplas origens, consumo segue FIFO.
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

Tabelas: `investment_opening_positions`, `investment_operations`, `investment_redemptions`, `investment_closed_positions`, `investment_value_overrides`, `transactions`, `checking_accounts`, `quote_cache`.

## Critérios de aceite

- Dado ativos de diferentes classes cadastrados, quando o portfólio é exibido, aparecem agrupados por classe com cotações atualizadas.
- Dado consolidações por classe, indexador, moeda ou carteira com moedas distintas, quando as barras são exibidas, seu tamanho é calculado pelo valor atual convertido para BRL, enquanto o texto mantém a moeda original.
- Dado um ativo de renda fixa pós-fixado, quando listado, exibe indexador, taxa e rendimento bruto/líquido com impostos regressivos.
- Dado um ativo pré-fixado, quando listado, exibe `Pré-fixado` e a taxa anual.
- Dado uma posição de renda fixa vencendo hoje ou vencida, quando o usuário navega pelo app, o item Portfólio no menu aparece em estado de alerta e o Cockpit exibe um aviso acionável.
- Dado uma posição vencida já encerrada, quando o portfólio é recarregado, o alerta de menu e o aviso do Cockpit deixam de considerar essa posição.
- Dado um ativo em moeda estrangeira, quando listado, é exibido na própria moeda sem conversão visual redundante.
- Dado uma posição com múltiplas origens, quando expandida, exibe os lançamentos/posições que a compõem.
- Dado um resgate realizado, quando executado, o valor retorna à conta de origem e a posição é atualizada via FIFO.
- Dado um encerramento sem a opção de crédito, quando executado, a posição vai para o histórico sem criar lançamento financeiro.
- Dado um encerramento com a opção de crédito marcada, quando executado, o sistema cria uma receita na conta da carteira e soma o valor final ao saldo da conta.
- Dado o modal de encerramento aberto, quando o usuário escolhe `Voltar`, a posição permanece aberta e nenhum lançamento é criado.

## Changelog

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
