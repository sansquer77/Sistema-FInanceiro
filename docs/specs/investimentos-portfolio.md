# Spec: Investimentos e Portfólio

## Status

**Implementado**

## Problema

O usuário precisa consolidar e acompanhar a valorização de seus ativos de investimento (Renda Fixa, Ações, Criptoativos, Fundos, Previdência Privada e Poupança) em um portfólio unificado, com atualização automática de preços quando disponível e cálculo de taxas e tributos quando aplicável.

## Usuário

Qualquer usuário autenticado localmente que possua investimentos e queira monitorar o patrimônio consolidado.

## Jornada

1. O usuário cadastra posições iniciais históricas (`opening positions`) de seus investimentos especificando ativo, quantidade, custo de aquisição, indexadores (no caso de renda fixa), taxa e data de aquisição.
2. Registra aportes associados a lançamentos normais do sistema, inclusive recorrentes.
3. Acompanha o portfólio com custo, valor atual, resultado, rentabilidade, variação diária e posições agrupáveis.
4. Atualiza manualmente o valor atual de posições sem cotação/indexador confiável.
5. Efetua resgates e encerramentos para devolver valor à conta de origem e mover posições finalizadas para histórico.

## Regras

- **Tipos de ativos**: Ações/ETFs/BDRs (`stock`), Criptoativos (`crypto`), Fundos (`fund`), Renda Fixa (`fixed_income`), Previdência Privada (`private_pension`), Poupança (`savings`) e Outros (`other`).
- **Moedas**: cada ativo é mantido e exibido na moeda da conta/carteira onde está custodiado. Conversões entre moedas ocorrem nos lançamentos de câmbio, não dentro do ativo.
- **Resumo e agrupamentos**: o módulo exibe cards por classe, indexador/moeda, carteira e posição atual. O agrupamento padrão da posição atual é por carteira, com opção de colapsar carteiras e abrir ativos com múltiplas origens.
- **Renda Fixa**:
  - Pós-fixados ou híbridos utilizam indexadores (CDI, SELIC, IPCA, IGP-M, TR) cujas taxas acumuladas são buscadas dinamicamente das APIs do Banco Central (SGS).
  - Pré-fixados utilizam a taxa acordada anual.
  - Na tabela do portfólio, o resumo de ativos pré-fixados deve exibir a modalidade `Préfixado` e a taxa anual cadastrada antes do vencimento.
  - O sistema calcula e deduz estimativas de IOF (até 30 dias de retenção) e de Imposto de Renda (tabela regressiva de 22,5% a 15% por dias de retenção).
  - Tesouro Direto IPCA+/Prefixado usa a premissa atual de carregamento até vencimento pelo indexador/taxa contratada. O app não tenta reproduzir marcação a mercado diária do extrato do Tesouro.
- **Previdência Privada**:
  - Lançamentos de investimento classificados como `Previdência Privada`, `PGBL` ou `VGBL` geram operações do tipo `private_pension`.
  - O usuário pode cadastrar posições iniciais de PGBL/VGBL e editar valor atual manualmente quando não houver indexador/cotação confiável.
- **Poupança**:
  - Poupança é um tipo próprio de ativo (`savings`) e não deve aparecer como subcategoria de Renda Fixa no formulário de Portfólio.
  - Posições iniciais podem informar uma lista de aniversários no formato data/valor.
  - Lançamentos de conta do tipo Investimento classificados como Poupança geram automaticamente um aniversário na data do lançamento, somando o valor a um aniversário existente quando a data for a mesma.
  - O cálculo considera apenas ciclos mensais completos e aplica TR + 0,5% a.m. quando a Selic estiver acima de 8,5% a.a.; quando a Selic estiver em 8,5% a.a. ou abaixo, aplica TR + 70% da Selic em equivalente mensal.
  - Não há cálculo de IR/IOF para Poupança.
- **Renda Variável / Criptos**:
  - Busca cotações de mercado automáticas via APIs públicas (Yahoo Finance para ações/fundos e CoinGecko/Yahoo para criptoativos).
  - Criptos usam pares de cotação na moeda do ativo/carteira quando disponíveis (por exemplo BTC/BRL ou BTC/USD).
- **Posições iniciais x operações**:
  - Posição inicial cadastrada no Portfólio não movimenta conta.
  - Operação de investimento criada por lançamento de conta afeta o saldo da conta.
  - Quando um ativo possui múltiplas origens, a tabela pode ser expandida para editar a posição inicial ou o lançamento de origem correspondente.
- **Resgates e encerramentos**:
  - Resgates retornam valor para a conta da carteira. Em posições com múltiplas origens, o consumo deve seguir FIFO.
  - Encerramento move a posição para Histórico com os valores no momento do resgate/fechamento.
  - Valor atual manual pode ser usado para PGBLs, fundos ou posições sem cálculo automático confiável.

## API e Dados

- Rotas:
  - `GET /api/portfolio` (obtenção do portfólio consolidado, sumário e taxas)
  - `POST /api/portfolio/positions` (criação de posição inicial)
  - `PUT /api/portfolio/positions/{id}` (atualização de posição inicial)
  - `DELETE /api/portfolio/positions/{id}` (remoção de posição inicial)
  - `POST /api/portfolio/redeem` (resgate de posição)
  - `POST /api/portfolio/close` (encerramento de posição)
  - `POST /api/portfolio/value` (ajuste manual do valor atual)
- Tabelas: `investment_opening_positions`, `investment_operations`, `investment_redemptions`, `investment_closed_positions`, `investment_value_overrides`, `transactions`, `checking_accounts`, `quote_cache`.

## Critérios de Aceite

- O usuário visualiza seus ativos agrupados por classe com as respectivas cotações atualizadas.
- O resumo da linha de Renda Fixa exibe indexador e taxa para pós-fixados/híbridos, e exibe `Préfixado` com a taxa para pré-fixados.
- O rendimento bruto e líquido de Renda Fixa reflete a incidência regressiva de impostos com base na data de aquisição.
- Ativos com moedas estrangeiras são exibidos na própria moeda, sem conversão visual redundante dentro da posição.
- O Cockpit e os cards do Portfólio respeitam a moeda de cada agrupamento.
- Posições com múltiplas origens permitem abrir os lançamentos/posições que compõem o ativo.
