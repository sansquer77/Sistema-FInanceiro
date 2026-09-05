---
tipo: spec
area: investimentos
status: implementado
versao: 2.9
atualizado: 2026-09-04
relacionados:
  - "[[investimentos-portfolio]]"
  - "[[arquitetura]]"
tags: [spec, "area/investimentos", "status/implementado"]
aliases: ["Rentabilidade do Portfólio"]
---

# Rentabilidade do Portfólio

> [!info] Status
> **implementado** · área: `investimentos` · atualizado em 2026-09-04 · relacionados: [[investimentos-portfolio]], [[adr/0017-snapshots-rentabilidade-portfolio]]

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
- `snapshot_coverage.observed_months`: competências calculadas a partir de snapshots persistidos.
- `snapshot_coverage.approximate_months`: competências históricas sem snapshot, calculadas pelo fallback aproximado.
- `snapshot_coverage.future_months`: competências futuras ainda não observadas.
- `snapshot_coverage.coverage_percent`: percentual de competências do eixo com snapshot persistido.

## Regras

- O gráfico é **de linhas** (não barras), baseado em **percentuais**, sem valores numéricos fixos no desenho; os valores aparecem em tooltip ao passar o mouse sobre os pontos.
- As linhas são **suavizadas** (interpolação por curvas Catmull-Rom) e o gráfico exibe **eixos X e Y** com gridlines e rótulos percentuais no eixo vertical.
- As linhas do gráfico devem ser finas e discretas, com pontos menores e destaque apenas no hover, para evitar aparência pesada no card de rentabilidade.
- O flyover de rentabilidade ocupa aproximadamente metade da viewport em desktop, sem ultrapassar a largura disponível; em telas estreitas, ocupa a tela com as margens usuais.
- A área de desenho é ampliada para **420px** de altura em desktop, com grid e eixo zero mais legíveis; séries da carteira usam preenchimento sutil sob a curva e benchmarks usam traço pontilhado para leitura rápida.
- A rentabilidade é **consolidada por moeda** (carteira inteira em R$ / carteira inteira em US$), nunca por produto individual.
- Cada moeda é calculada **na própria moeda** (valores nativos em centavos da moeda), sem efeito de câmbio na série.
- O gráfico mostra sempre janeiro a dezembro do ano corrente; meses futuros permanecem no eixo, com retorno zerado até serem observados.
- A partir da implantação, cada competência encerrada pode persistir um snapshot por ativo; períodos anteriores sem snapshot permanecem explicitamente aproximados.
- A inicialização do app reconcilia de forma idempotente a tabela de snapshots também em bancos já identificados como v2, antes de aceitar requisições.
- Na primeira captura após a implantação, posições iniciadas antes da competência corrente formam o baseline e não são registradas integralmente como aporte do mês; somente posições efetivamente iniciadas na competência entram no fluxo inicial.
- Quando um ativo possui vários lotes na mesma carteira, a captura soma quantidade, custo e valor desses lotes antes da gravação única por ativo, sem substituir lotes anteriores.
- Cada mês usa o valor do patrimônio no último dia do mês (limitado a hoje).
- Posição que **entra no mês corrente** conta pelo custo (baseline), sem retorno sintético de entrada; a valorização começa nos meses seguintes.
- Mês cujo mês anterior tinha patrimônio zero (baseline vazio) não gera retorno sintético; vira o novo baseline.
- Renda fixa e poupança têm valor mensal calculado pelos indexadores do Banco Central.
- Renda variável, cripto, fundos, previdência e "outros" usam snapshots persistidos quando disponíveis; na ausência deles, usam o valor atual conhecido como aproximação e essa limitação é indicada no drawer.
- O CDI é calculado como fator acumulado da série SGS 12 entre o primeiro e o último dia de cada mês (com cache por mês, compartilhado entre as posições da mesma geração de série).
- O IPCA é calculado como fator acumulado da série SGS 433 (indexador mensal) entre o primeiro e o último dia de cada mês (com cache por mês, compartilhado entre as posições da mesma geração de série).
- Séries com todos os meses em 0% (moeda sem posições no período ou baseline) aparecem como linha plana; moedas sem posições abertas não geram linha própria.
- O gráfico usa ApexCharts 4.7.0, com linhas, pontos e paleta do design system.
- A série de rentabilidade deve ser carregada sob demanda quando o usuário abrir o drawer/gráfico, não junto com o carregamento inicial da aba **Posição**.
- Quando um chamador backend já tiver posições do Portfólio calculadas no mesmo fluxo, `get_portfolio_returns` pode receber essa lista e evitar recalcular/cotar o Portfólio inteiro.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/portfolio/returns` |

Tabelas: `investment_opening_positions`, `investment_operations`, `investment_redemptions`, `investment_value_overrides`, `investment_monthly_snapshots`, `checking_accounts`, `quote_cache`.

## Critérios de aceite

- Dado o usuário abrindo o Portfólio, quando a seção "Resumo da Carteira" é exibida, então o card "Rentabilidade" mantém o percentual consolidado e exibe um botão para abrir o gráfico mensal vs CDI/IPCA.
- Dado o usuário clicando no botão de gráfico do card "Rentabilidade", quando o drawer é aberto, então ele exibe um gráfico de linhas com as séries R$, US$, CDI e IPCA (as que tiverem dados).
- Dado o gráfico exibido, quando o usuário passa o mouse sobre um ponto mensal, então um tooltip mostra o valor percentual daquele mês e série.
- Dado o gráfico exibido, quando há valores positivos e negativos, então as linhas atravessam o eixo zero sem truncamento.
- Dado uma carteira com posições somente em BRL, quando o gráfico é exibido, então há linha R$ (e CDI/IPCA), sem linha US$ vazia.
- Dado uma carteira com posições em BRL e USD, quando o gráfico é exibido, então há linhas R$, US$, CDI e IPCA.
- Dado o gráfico aberto em qualquer mês do ano, quando a série é exibida, então o eixo contém janeiro a dezembro do ano corrente.
- Dado um mês futuro sem fechamento, quando a série é exibida, então o retorno do mês é zero e não é apresentado como dado histórico observado.
- Dado um mês encerrado com snapshots disponíveis, quando o retorno é calculado, então a variação usa os valores de fechamento por ativo e desconta aportes, resgates e proventos líquidos.
- Dado um mês sem snapshots históricos, quando o retorno é calculado, então a resposta marca o período como aproximado sem impedir a exibição agregada por moeda.
- Dado o retorno da API, quando existem e não existem snapshots no período, então `snapshot_coverage` separa competências observadas, aproximadas e futuras sem remover `series`.
- Dado o usuário sem investimentos cadastrados, quando o card é exibido, então aparece estado vazio com mensagem amigável em vez de gráfico.
- Dado um erro ao consultar o CDI/IPCA ou ao montar o resumo, quando o drawer é aberto, então o app exibe mensagem de erro sem travar o Portfólio.
- Dado uma posição que entrou no mês atual, quando o gráfico calcula aquele mês, então o aporte não é tratado como retorno (marca baseline).
- Dado o usuário abrindo o gráfico em desktop, quando o flyover é exibido, então ocupa aproximadamente metade da viewport e o gráfico tem área de desenho de 420px de altura, sem prejudicar a adaptação para telas estreitas.
- Dado o cabeçalho global fixo, quando o drawer de rentabilidade é aberto, então overlay, cabeçalho e gráfico permanecem integralmente acima do conteúdo e do cabeçalho da aplicação.

- Dado o gráfico de rentabilidade, quando o tooltip aparece em tema claro ou escuro, então texto, fundo, cabeçalho e indicador de mês usam cores do tema ativo sem alterar as séries. Contrato CSS automatizado; aparência no Safari requer validação manual.

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

## Fora de escopo

- Armazenamento de cotações históricas de renda variável/cripto.
- Cálculo de rentabilidade TWR (Time-Weighted Return) ou MWR (Money-Weighted Return) complexos.
- Rentabilidade por produto individual no gráfico.
- Benchmarks além de CDI e IPCA nesta versão.

## Plano de implementação

- [x] Passo 1 — Criar migração idempotente para snapshots mensais por ativo em `financeiro/database_schema.py`/`database_migrations.py`. Fecha: critérios 3 e 4.
- [x] Passo 2 — Implementar leitura e persistência transacional dos snapshots em `financeiro/portfolio_snapshots.py`, sem chamadas externas dentro da transação. Fecha: critérios 3 e 4.
- [x] Passo 3 — Integrar valorização por data e fontes de cotação existentes, preservando fallback aproximado e origem da cotação em `PositionValuation.position_value_snapshot_metadata`. Fecha: critérios 3 e 4.
- [x] Passo 4 — Integrar `portfolio_returns.py` ao repositório de snapshots, priorizando valores persistidos e mantendo o cálculo aproximado como fallback; a saída continua agregada por moeda. Fecha: critérios 1, 3, 4 e 5.
- [x] Passo 5 — Ajustar rota e contrato de retorno para informar cobertura histórica, sem listar ativos no flyover. Fecha: critérios 1, 2 e 4.
- [x] Passo 6 — Ajustar flyover para ano civil Jan–Dez e nota explicativa baseada na cobertura, preservando as quatro séries agregadas. Fecha: critérios 1, 2 e 5.
- [x] Passo 7 — Adicionar testes de migração, snapshots, moedas, meses futuros, fallback aproximado e apresentação da cobertura. Fecha: todos os critérios.

- [x] Aplicar ao gráfico de rentabilidade as regras de contraste já usadas em Tendências e verificar o contrato CSS. Fecha: critério 13. Teste estrutural aprovado; validação visual no Safari pendente.
- [x] Passo 1 — Reescrever `get_portfolio_returns` em `financeiro/portfolio.py` para série mensal **por moeda** (BRL e USD em %) com CDI e IPCA por mês, com cache de fator por mês. Fecha: critérios 2, 6, 7, 8, 12.
- [x] Passo 2 — Adicionar `_position_value_native_as_of`, `_cdi_factor_for_month` e `_ipca_factor_for_month` em `financeiro/portfolio.py`, limitando a série a 12 meses. Fecha: critérios 3, 4, 5, 7, 8.
- [x] Passo 3 — Manter endpoint `GET /api/portfolio/returns` retornando `series` mensal por moeda + CDI + IPCA. Fecha: critérios 1, 2, 9, 10.
- [x] Passo 4 — Renderizar no drawer linhas R$/US$/CDI/IPCA com pontos e tooltip em `web/modules/portfolio-view.js`. Fecha: critérios 3, 4, 5, 6.
- [x] Passo 5 — Ajustar estilos do gráfico em `web/styles.css` (reuso das classes existentes). Fecha: critérios 3, 4.
- [x] Passo 6 — Escrever testes automatizados para o cálculo mensal por moeda e CDI/IPCA por mês. Fecha: critérios 2, 3, 4, 5, 6, 7, 8, 12.
- [x] Passo 7 — Ampliar o flyover e refinar o SVG nativo com preenchimento sutil das séries da carteira e traços pontilhados para benchmarks, sem dependência externa. Fecha: critérios 2, 12.
- [x] Passo 8 — Hospedar o drawer no nível global de overlays para que seu contexto de empilhamento permaneça acima do cabeçalho sticky. Fecha: critério 13.

## Changelog

- `2.9` — 2026-09-04 — Captura consolida lotes de identidade igual antes do UPSERT, preservando quantidade, custo e valor totais do ativo no fechamento.
- `2.8` — 2026-09-04 — Primeira captura deixa de classificar o estoque histórico da carteira como aporte da competência, eliminando a queda artificial de rentabilidade na implantação.
- `2.7` — 2026-09-04 — Inicialização passa a reconciliar o baseline aditivo em bancos v2 existentes, evitando falha da rentabilidade quando a tabela de snapshots foi introduzida após a criação do banco.
- `2.6` — 2026-09-04 — Captura passa a ocorrer antes da resposta do primeiro acesso, classifica cobertura parcial corretamente e usa fluxos persistidos de aporte, resgate e provento no retorno mensal.
- `2.5` — 2026-09-04 — Flyover passa a explicar cobertura observada, aproximação e meses futuros; testes de integração e documentação encerram a implantação do ADR-0017.
- `2.4` — 2026-09-04 — API passa a retornar `snapshot_coverage` com competências observadas, aproximadas, futuras e percentual de cobertura, preservando o contrato de `series`.
- `2.3` — 2026-09-04 — Série de rentabilidade passa a priorizar snapshots persistidos por competência e usar a valorização aproximada somente quando não houver cobertura.
- `2.2` — 2026-09-04 — Valorização passou a expor valor por data, fonte e status observado/aproximado para alimentar snapshots sem recotação insegura.
- `2.1` — 2026-09-04 — Repositório idempotente de snapshots adicionado, com filtros por competência/moeda e índices de leitura.
- `1.9` — 2026-09-04 — Série do flyover passa a cobrir sempre janeiro a dezembro do ano corrente; meses futuros ficam zerados e a nota explica aportes, aproximações e a variação mensal.

- `1.8` — 2026-08-31 — Corrigido contraste do tooltip, cabeçalho e indicador de mês com as regras compartilhadas de Tendências, preservando séries e percentuais. Contrato CSS coberto por teste.
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
- [[adr/0017-snapshots-rentabilidade-portfolio]]
- [[arquitetura]]
