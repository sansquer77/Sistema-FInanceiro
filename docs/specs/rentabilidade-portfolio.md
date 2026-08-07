---
tipo: spec
area: investimentos
status: implementado
versao: 1.0
atualizado: 2026-08-06
relacionados:
  - "[[investimentos-portfolio]]"
  - "[[arquitetura]]"
tags: [spec, "area/investimentos", "status/rascunho"]
aliases: ["Rentabilidade do Portfólio"]
---

# Rentabilidade do Portfólio

> [!info] Status
> **rascunho** · área: `investimentos` · atualizado em 2026-08-06 · relacionados: [[investimentos-portfolio]]

## Problema

O usuário precisa visualizar a evolução da rentabilidade da carteira de investimentos mês a mês, comparada com um benchmark simples (CDI), para entender se o patrimônio está rendendo acima ou abaixo da renda fixa básica.

## Usuário

Investidor que acompanha o Portfólio e quer uma leitura rápida de performance ao longo do tempo, em cada moeda da carteira.

## Jornada

1. O usuário abre o menu Portfólio.
2. Na seção "Resumo da Carteira", visualiza o card "Rentabilidade" com o percentual total por moeda.
3. Ao clicar no botão de gráfico dentro do card "Rentabilidade", um drawer exibe barras mês a mês comparando a rentabilidade da carteira e do CDI.
4. O usuário identifica meses positivos/negativos e o acumulado do período disponível.

## Dados

- `month`: mês no formato `AAAA-MM`.
- `portfolio_return_pct`: rentabilidade percentual da carteira naquele mês (variação isolada do mês).
- `cdi_return_pct`: rentabilidade percentual do CDI naquele mês (variação isolada do mês).
- `currency`: moeda daquela série (ex.: `BRL`, `USD`).

## Regras

- O gráfico deve usar o mesmo estilo visual do gráfico de evolução de categoria (SVG puro, barras, labels de valor, paleta do design system).
- O período calculado começa no primeiro mês com posição ou aporte registrado e vai até o mês atual (quando o usuário pede YTD mas a base só tem dados parciais, usa-se 100% do período cadastrado).
- Para cada mês, o cálculo considera o valor da carteira no último dia do mês.
- Renda fixa e poupança têm valor mensal calculado pelos indexadores do Banco Central.
- Renda variável, cripto, fundos, previdência e "outros" usam o valor atual conhecido como aproximação para todo o período histórico, pois o app não armazena cotações passadas; essa limitação deve ser indicada visualmente.
- O CDI é calculado como fator acumulado da série SGS 12 entre o primeiro dia do período e o último dia de cada mês.
- A rentabilidade da carteira em cada mês é calculada sobre o patrimônio líquido (valor atual menos impostos estimados, quando aplicável).
- Multi-moeda: cada moeda com posição aberta gera sua própria série de barras; o CDI é exibido como benchmark em cada moeda (o fator percentual é o mesmo, mas o contexto é por moeda).

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/portfolio/returns` |

Tabelas: `investment_opening_positions`, `investment_operations`, `investment_redemptions`, `investment_value_overrides`, `checking_accounts`, `quote_cache`.

## Critérios de aceite

- Dado o usuário abrindo o Portfólio, quando a seção "Resumo da Carteira" é exibida, então o card "Rentabilidade" mantém o percentual total por moeda e exibe um botão para abrir o gráfico mês a mês.
- Dado o usuário clicando no botão de gráfico do card "Rentabilidade", quando o drawer é aberto, então ele exibe barras comparando a carteira e o CDI.
- Dado uma carteira com posições em BRL, quando o gráfico é exibido, então há uma série de barras para a rentabilidade da carteira em BRL e outra série para o CDI.
- Dado uma carteira com posições em USD (ou outra moeda), quando o gráfico é exibido, então há uma série adicional para essa moeda, mantendo o CDI como benchmark visível.
- Dado o primeiro investimento cadastrado em Jun/2026 e o mês atual Ago/2026, quando o usuário seleciona YTD, então o gráfico mostra os meses Jun, Jul e Ago (100% do período cadastrado), pois não há dados de Jan a Mai.
- Dado uma posição de renda fixa CDI, quando o cálculo mensal é executado, então o valor da posição é projetado pelo fator acumulado do CDI até o último dia de cada mês.
- Dado uma posição de ações/cripto sem cotação histórica, quando o cálculo mensal é executado, então o gráfico usa o valor atual como aproximação e exibe um aviso discreto sobre a limitação.
- Dado o gráfico de rentabilidade exibido, quando há valores positivos e negativos, então as barras crescem para cima (positivo) ou para baixo (negativo) a partir do eixo zero.
- Dado o gráfico exibido, quando o usuário passa o mouse ou foca uma barra, então o valor percentual daquele mês é legível (label ou tooltip).
- Dado o usuário sem investimentos cadastrados, quando o card é exibido, então aparece estado vazio com mensagem amigável em vez de gráfico.

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

## Fora de escopo

- Armazenamento de cotações históricas de renda variável/cripto.
- Cálculo de rentabilidade TWR (Time-Weighted Return) ou MWR (Money-Weighted Return) complexos.
- Benchmarks além do CDI nesta versão.

## Plano de implementação

- [ ] Passo 1 — Adicionar função em `financeiro/portfolio.py` para calcular o valor de uma posição de renda fixa/poupança em uma data arbitrária (reutilizando lógica existente). Fecha: critério 5.
- [ ] Passo 2 — Adicionar função em `financeiro/portfolio.py` para calcular CDI acumulado entre duas datas via SGS 12. Fecha: critérios 2, 3, 4.
- [ ] Passo 3 — Criar endpoint `GET /api/portfolio/returns` que monta série mensal por moeda (patrimônio histórico + CDI). Fecha: critérios 1, 2, 3, 4.
- [ ] Passo 4 — Adicionar card "Rentabilidade mês a mês" no HTML do Portfólio e renderizar gráfico de barras em `web/modules/portfolio-view.js`. Fecha: critérios 1, 6, 7, 8.
- [ ] Passo 5 — Adicionar estilos do gráfico em `web/styles.css`. Fecha: critérios 1, 7.
- [ ] Passo 6 — Escrever testes automatizados para o cálculo de série mensal e CDI acumulado. Fecha: critérios 2, 3, 4, 5.

## Changelog

- `1.0` — 2026-08-06 — Implementação do gráfico de rentabilidade mês a mês no Portfólio, com endpoint `/api/portfolio/returns`, cálculo de CDI acumulado e séries por moeda.
- `0.1` — 2026-08-06 — Spec inicial do gráfico de rentabilidade mês a mês no Portfólio.

## Relacionados

- [[investimentos-portfolio]]
- [[arquitetura]]
