---
tipo: spec
area: investimentos
status: implementado
versao: 1.7
atualizado: 2026-08-22
relacionados:
  - "[[investimentos-portfolio]]"
  - "[[arquitetura]]"
tags: [spec, "area/investimentos", "status/implementado"]
aliases: ["Rentabilidade do Portfólio"]
---

# Rentabilidade do Portfólio

> [!info] Status
> **implementado** · área: `investimentos` · atualizado em 2026-08-22 · relacionados: [[investimentos-portfolio]]

## Problema

O usuário precisa visualizar a rentabilidade mensal da carteira em percentual, por moeda consolidada (R$ e US$), comparada com os benchmarks CDI e IPCA, para entender se o patrimônio rendeu acima da renda fixa básica e da inflação em cada mês disponível.

## Usuário

Investidor que acompanha o Portfólio e quer uma leitura rápida de performance mensal por moeda, nos últimos 12 meses (ou todo o período cadastrado, quando menor).

## Jornada

1. O usuário abre o menu Portfólio.
2. Na seção "Resumo da Carteira", visualiza o card "Rentabilidade" com o percentual consolidado.
3. Ao clicar no botão de gráfico dentro do card "Rentabilidade", um drawer exibe um **gráfico de linhas** mês a mês com as séries R$, US$, CDI e IPCA (todas em %).
4. Ao passar o mouse sobre um ponto mensal, um tooltip mostra o valor percentual daquele mês para cada série.
5. O usuário identifica meses acima/abaixo do CDI e da inflação e o maior/menor rendimento do período.

## Dados

- `month`: mês no formato `AAAA-MM`.
- `BRL_return_pct`: rentabilidade percentual mensal da carteira em reais (variação isolada do mês, calculada na própria moeda).
- `USD_return_pct`: rentabilidade percentual mensal da carteira em dólares (variação isolada do mês, calculada na própria moeda).
- `cdi_return_pct`: rentabilidade percentual mensal do CDI (variação isolada do mês).
- `ipca_return_pct`: rentabilidade percentual mensal do IPCA (variação isolada do mês).
- `start_month` / `end_month`: período da série (AAAA-MM).

## Regras

- O gráfico é **de linhas** (não barras), baseado em **percentuais**, sem valores numéricos fixos no desenho; os valores aparecem em tooltip ao passar o mouse sobre os pontos.
- As linhas são **suavizadas** (interpolação por curvas Catmull-Rom) e o gráfico exibe **eixos X e Y** com gridlines e rótulos percentuais no eixo vertical.
- As linhas do gráfico devem ser finas e discretas, com pontos menores e destaque apenas no hover, para evitar aparência pesada no card de rentabilidade.
- O flyover de rentabilidade ocupa aproximadamente metade da viewport em desktop, sem ultrapassar a largura disponível; em telas estreitas, ocupa a tela com as margens usuais.
- A área de desenho é ampliada para **420px** de altura em desktop, com grid e eixo zero mais legíveis; séries da carteira usam preenchimento sutil sob a curva e benchmarks usam traço pontilhado para leitura rápida.
- A rentabilidade é **consolidada por moeda** (carteira inteira em R$ / carteira inteira em US$), nunca por produto individual.
- Cada moeda é calculada **na própria moeda** (valores nativos em centavos da moeda), sem efeito de câmbio na série.
- O gráfico mostra **12 meses** fixos, ou todos os meses disponíveis quando a base tem menos de 12 meses.
- O período começa no primeiro mês com posição/operação cadastrada e vai até o mês atual.
- Cada mês usa o valor do patrimônio no último dia do mês (limitado a hoje).
- Posição que **entra no mês corrente** conta pelo custo (baseline), sem retorno sintético de entrada; a valorização começa nos meses seguintes.
- Mês cujo mês anterior tinha patrimônio zero (baseline vazio) não gera retorno sintético; vira o novo baseline.
- Renda fixa e poupança têm valor mensal calculado pelos indexadores do Banco Central.
- Renda variável, cripto, fundos, previdência e "outros" usam o valor atual conhecido como aproximação para todo o período histórico, pois o app não armazena cotações passadas; essa limitação é indicada no drawer.
- O CDI é calculado como fator acumulado da série SGS 12 entre o primeiro e o último dia de cada mês (com cache por mês, compartilhado entre as posições da mesma geração de série).
- O IPCA é calculado como fator acumulado da série SGS 433 (indexador mensal) entre o primeiro e o último dia de cada mês (com cache por mês, compartilhado entre as posições da mesma geração de série).
- Séries com todos os meses em 0% (moeda sem posições no período ou baseline) aparecem como linha plana; moedas sem posições abertas não geram linha própria.
- O gráfico usa o estilo visual do gráfico de evolução de categoria (SVG puro, linhas e pontos, paleta do design system).
- A série de rentabilidade deve ser carregada sob demanda quando o usuário abrir o drawer/gráfico, não junto com o carregamento inicial da aba **Posição**.
- Quando um chamador backend já tiver posições do Portfólio calculadas no mesmo fluxo, `get_portfolio_returns` pode receber essa lista e evitar recalcular/cotar o Portfólio inteiro.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/portfolio/returns` |

Tabelas: `investment_opening_positions`, `investment_operations`, `investment_redemptions`, `investment_value_overrides`, `checking_accounts`, `quote_cache`.

## Critérios de aceite

- Dado o usuário abrindo o Portfólio, quando a seção "Resumo da Carteira" é exibida, então o card "Rentabilidade" mantém o percentual consolidado e exibe um botão para abrir o gráfico mensal vs CDI/IPCA.
- Dado o usuário clicando no botão de gráfico do card "Rentabilidade", quando o drawer é aberto, então ele exibe um gráfico de linhas com as séries R$, US$, CDI e IPCA (as que tiverem dados).
- Dado o gráfico exibido, quando o usuário passa o mouse sobre um ponto mensal, então um tooltip mostra o valor percentual daquele mês e série.
- Dado o gráfico exibido, quando há valores positivos e negativos, então as linhas atravessam o eixo zero sem truncamento.
- Dado uma carteira com posições somente em BRL, quando o gráfico é exibido, então há linha R$ (e CDI/IPCA), sem linha US$ vazia.
- Dado uma carteira com posições em BRL e USD, quando o gráfico é exibido, então há linhas R$, US$, CDI e IPCA.
- Dado uma carteira com 12 meses ou mais de histórico, quando o gráfico é exibido, então são mostrados exatamente os últimos 12 meses.
- Dado uma carteira com menos de 12 meses de histórico, quando o gráfico é exibido, então são mostrados todos os meses disponíveis desde a primeira posição.
- Dado o usuário sem investimentos cadastrados, quando o card é exibido, então aparece estado vazio com mensagem amigável em vez de gráfico.
- Dado um erro ao consultar o CDI/IPCA ou ao montar o resumo, quando o drawer é aberto, então o app exibe mensagem de erro sem travar o Portfólio.
- Dado uma posição que entrou no mês atual, quando o gráfico calcula aquele mês, então o aporte não é tratado como retorno (marca baseline).
- Dado o usuário abrindo o gráfico em desktop, quando o flyover é exibido, então ocupa aproximadamente metade da viewport e o gráfico tem área de desenho de 420px de altura, sem prejudicar a adaptação para telas estreitas.

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

## Fora de escopo

- Armazenamento de cotações históricas de renda variável/cripto.
- Cálculo de rentabilidade TWR (Time-Weighted Return) ou MWR (Money-Weighted Return) complexos.
- Rentabilidade por produto individual no gráfico.
- Benchmarks além de CDI e IPCA nesta versão.

## Plano de implementação

- [x] Passo 1 — Reescrever `get_portfolio_returns` em `financeiro/portfolio.py` para série mensal **por moeda** (BRL e USD em %) com CDI e IPCA por mês, com cache de fator por mês. Fecha: critérios 2, 6, 7, 8, 12.
- [x] Passo 2 — Adicionar `_position_value_native_as_of`, `_cdi_factor_for_month` e `_ipca_factor_for_month` em `financeiro/portfolio.py`, limitando a série a 12 meses. Fecha: critérios 3, 4, 5, 7, 8.
- [x] Passo 3 — Manter endpoint `GET /api/portfolio/returns` retornando `series` mensal por moeda + CDI + IPCA. Fecha: critérios 1, 2, 9, 10.
- [x] Passo 4 — Renderizar no drawer linhas R$/US$/CDI/IPCA com pontos e tooltip em `web/modules/portfolio-view.js`. Fecha: critérios 3, 4, 5, 6.
- [x] Passo 5 — Ajustar estilos do gráfico em `web/styles.css` (reuso das classes existentes). Fecha: critérios 3, 4.
- [x] Passo 6 — Escrever testes automatizados para o cálculo mensal por moeda e CDI/IPCA por mês. Fecha: critérios 2, 3, 4, 5, 6, 7, 8, 12.
- [x] Passo 7 — Ampliar o flyover e refinar o SVG nativo com preenchimento sutil das séries da carteira e traços pontilhados para benchmarks, sem dependência externa. Fecha: critérios 2, 12.

## Changelog

- `1.7` — 2026-08-22 — Flyover de rentabilidade ampliado para aproximadamente metade da viewport em desktop; área do gráfico passa a 420px e o SVG nativo diferencia carteira (preenchimento sutil) de benchmarks (traço pontilhado), sem adicionar dependências.
- `1.6` — 2026-08-09 — Rentabilidade passa a ser carregada sob demanda no drawer e `get_portfolio_returns` aceita posições já calculadas para evitar segunda consolidação do Portfólio quando houver contexto disponível.
- `1.5` — 2026-08-09 — Refinamento visual do gráfico de rentabilidade: linhas mais finas/discretas e pontos menores com destaque apenas no hover.
- `1.4` — 2026-08-07 — Desempenho: o fator acumulado de indexador (CDI/IPCA) por mês é decomposto por mês-calendário e compartilhado entre todas as posições e ativos de uma mesma geração de série (`_accumulated_factor_by_month`), reduzindo chamadas ao BCB; valores observáveis não mudam.
- `1.3` — 2026-08-06 — Rework UX: gráfico de **barras → linhas** (R$, US$, CDI e IPCA em %), sem números fixos; valores em tooltip ao passar o mouse sobre os pontos; rentabilidade calculada **por moeda na própria moeda** (sem efeito de câmbio); adicionado benchmark **IPCA** (SGS 433 mensal). Ajuste visual posterior: **linhas suavizadas**, **eixos X/Y com grid e rótulos** e **área 15% maior**.
- `1.2` — 2026-08-06 — Rentabilidade mensal consolidada da carteira inteira em BRL vs CDI do mês (substituída pela visão por moeda).
- `1.1` — 2026-08-06 — Rentabilidade consolidada por moeda vs CDI acumulado do período (substituída pela visão mensal).
- `1.0` — 2026-08-06 — Implementação inicial com série mês a mês por posição por moeda (depois substituída pela visão mensal consolidada).
- `0.1` — 2026-08-06 — Spec inicial do gráfico de rentabilidade no Portfólio.

## Relacionados

- [[investimentos-portfolio]]
- [[arquitetura]]
