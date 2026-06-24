# Spec: Investimentos e Portfólio

## Status

**Implementado**

## Problema

O usuário precisa consolidar e acompanhar a valorização de seus ativos de investimento (Renda Fixa, Ações, Criptoativos, Fundos) em um portfólio unificado, com atualização automática de preços e cálculo de taxas e tributos.

## Usuário

Qualquer usuário autenticado localmente que possua investimentos e queira monitorar o patrimônio consolidado.

## Jornada

1. O usuário cadastra posições iniciais históricas (`opening positions`) de seus investimentos especificando ativo, quantidade, custo de aquisição, indexadores (no caso de renda fixa), taxa e data de aquisição.
2. Registra operações de compra ou venda associadas a lançamentos normais do sistema.
3. Acompanha o portfólio com o valor total de custo, valor atual de mercado, lucros/perdas e variação diária.

## Regras

- **Tipos de ativos**: Ações (`stock`), Criptoativos (`crypto`), Fundos (`fund`), Renda Fixa (`fixed_income`), Poupança (`savings`) e Outros (`other`).
- **Moedas**: Contas de investimento podem ser em moedas estrangeiras (`USD`, `EUR`, `GBP`). O portfólio calcula a conversão histórica e atual para BRL.
- **Renda Fixa**:
  - Pós-fixados ou híbridos utilizam indexadores (CDI, SELIC, IPCA, IGP-M, TR) cujas taxas acumuladas são buscadas dinamicamente das APIs do Banco Central (SGS).
  - Pré-fixados utilizam a taxa acordada anual.
  - Na tabela do portfólio, o resumo de ativos pré-fixados deve exibir a modalidade `Préfixado` e a taxa anual cadastrada antes do vencimento.
  - O sistema calcula e deduz estimativas de IOF (até 30 dias de retenção) e de Imposto de Renda (tabela regressiva de 22,5% a 15% por dias de retenção).
- **Poupança**:
  - Posições iniciais podem informar uma lista de aniversários no formato data/valor.
  - Lançamentos de conta do tipo Investimento classificados como Poupança geram automaticamente um aniversário na data do lançamento, somando o valor a um aniversário existente quando a data for a mesma.
  - O cálculo considera apenas ciclos mensais completos e aplica TR + 0,5% a.m. quando a Selic estiver acima de 8,5% a.a.; quando a Selic estiver em 8,5% a.a. ou abaixo, aplica TR + 70% da Selic em equivalente mensal.
  - Não há cálculo de IR/IOF para Poupança.
- **Renda Variável / Criptos**:
  - Busca cotações de mercado automáticas via APIs públicas (Yahoo Finance para ações/fundos e CoinGecko/Yahoo para criptoativos).

## API e Dados

- Rotas:
  - `GET /api/portfolio` (obtenção do portfólio consolidado, sumário e taxas)
  - `POST /api/portfolio/positions` (criação de posição inicial)
  - `PUT /api/portfolio/positions/{id}` (atualização de posição inicial)
  - `DELETE /api/portfolio/positions/{id}` (remoção de posição inicial)
- Tabelas: `investment_opening_positions`, `investment_operations`, `transactions`, `checking_accounts`.

## Critérios de Aceite

- O usuário visualiza seus ativos agrupados por classe com as respectivas cotações atualizadas.
- O resumo da linha de Renda Fixa exibe indexador e taxa para pós-fixados/híbridos, e exibe `Préfixado` com a taxa para pré-fixados.
- O rendimento bruto e líquido de Renda Fixa reflete a incidência regressiva de impostos com base na data de aquisição.
- Ativos com moedas estrangeiras exibem os valores convertidos para BRL com base na taxa de câmbio informada ou obtida automaticamente.
