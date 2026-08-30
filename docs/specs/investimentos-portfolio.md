---
tipo: spec
area: investimentos
status: implementado
versao: 2.40
atualizado: 2026-08-29
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
> **implementado** · área: `investimentos` · atualizado em 2026-08-29 · relacionados: [[contas-correntes]], [[lancamentos]], [[relatorios]]

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
| Stablecoins | `stablecoin` |
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
- Formulários de Renda Fixa devem reduzir ruído visual: modalidade por combo com helper de ajuda sob demanda, rótulo/placeholder de taxa dinâmicos e preview compacto da configuração.
- O formulário de posição (Renda Fixa) do Portfólio segue a mesma linguagem do formulário de Lançamentos: modalidade em combo com o ícone de ajuda (?) ao lado do rótulo, sem controles segmentados, chips, presets ou checkboxes com moldura pill.
- Campos de quantidade e preço médio/unitário não devem ser exibidos para renda fixa, pois o custo total/aporte é a base de cálculo relevante.
- O sistema calcula e deduz estimativas de IOF (até 30 dias) e IR (tabela regressiva de 22,5% a 15%).
- Para títulos do Tesouro Direto, o sistema mantém o cálculo de rentabilidade **na curva**, usando a taxa contratada cadastrada, sem tentar igualar a marcação a mercado exibida pelo site do Tesouro em resgate antecipado.
- Para títulos do Tesouro Direto padrão (Prefixado, IPCA+ e Selic), o sistema calcula e deduz uma **Taxa B3 estimada** de 0,20% a.a. pro rata sobre o valor da posição estimado na curva. Para Tesouro Selic, aplica isenção simplificada até R$ 10.000,00 sobre a posição; acima desse valor, a estimativa incide apenas sobre o excedente. Para Tesouro RendA+ e Tesouro Educa+, o sistema não calcula automaticamente a taxa B3 na primeira versão, pois essas modalidades possuem regras específicas por prazo, resgate antecipado e faixa de recebimento.
- O módulo Portfólio deve exibir nota discreta informando que diferenças frente ao site do Tesouro podem ocorrer por marcação a mercado em resgate antecipado, provisão oficial de taxas e regras específicas do título.
- Posições de renda fixa com vencimento igual ou anterior à data atual devem gerar alerta visual no menu Portfólio e aviso no Cockpit até que sejam encerradas.
- Posições iniciais e aportes de renda fixa podem ser marcados explicitamente como reserva de emergência quando o usuário entender que têm liquidez compatível, sem inferência automática pelo sistema.
- A variação do dia de renda fixa é a diferença entre o valor líquido na curva hoje e o valor líquido no dia anterior, com base de comparação limitada à data de aquisição (no dia da aquisição a variação exibida é zero). Pós-fixados/híbridos variam apenas em dias com taxa publicada (dias úteis); pré-fixados variam pro rata diário sobre calendário (365 dias), incluindo fins de semana.

**Poupança (`savings`):**
- Não aparece como subcategoria de Renda Fixa no formulário.
- Posições iniciais podem informar lista de aniversários (data/valor).
- Lançamentos classificados como Poupança geram automaticamente um aniversário na data do lançamento.
- Cálculo: TR + 0,5% a.m. quando Selic > 8,5% a.a.; TR + 70% da Selic equivalente mensal quando Selic ≤ 8,5% a.a.
- Resgates de Poupança consomem os aniversários por FIFO, dos aniversários mais antigos para os mais recentes; resgate total zera os aniversários remanescentes e remove a posição da carteira aberta.
- Não há cálculo de IOF/IR para Poupança.
- Posições e aportes de Poupança podem ser marcados explicitamente como reserva de emergência, mas a marcação deve ser decisão do usuário.
- A marcação de reserva de emergência deve ser visualmente discreta no formulário, com peso menor que campos financeiros principais.
- Em aportes de Poupança criados por Lançamentos de Contas, o formulário deve ocultar campos não aplicáveis como quantidade, preço unitário, renda fixa, CNPJ, corretagem, emolumentos, impostos e outros custos.
- A variação do dia de Poupança usa o mesmo método da renda fixa (diferença do valor atual entre hoje e o dia anterior, limitada à data do aniversário mais antigo); na prática a variação concentra-se no mês do aniversário, quando o adicional mensal é creditado.

**Previdência Privada (`private_pension`):**
- Lançamentos classificados como `Previdência Privada`, `PGBL` ou `VGBL` geram operações do tipo `private_pension`.
- Quando houver CNPJ preenchido, carteira em BRL e Mais Retorno configurada, o valor atual pode usar a última cota disponível pela mesma integração de fundos; sem isso, permanece ajustável manualmente.
- O formulário de posição inicial do Portfólio exibe o campo **CNPJ** opcional tanto para Fundos quanto para Previdência Privada (rótulo `CNPJ do fundo/plano`), pois ambos usam a mesma integração Mais Retorno; o CNPJ preenchido é persistido na posição.

**Renda Variável / Criptos:**
- Cotações via Yahoo Finance (ações/fundos) e CoinGecko/Yahoo (criptoativos).
- Criptos usam pares de cotação na moeda do ativo/carteira (ex.: BTC/BRL ou BTC/USD).
- Stablecoins usam classe própria (`stablecoin`), separada de criptoativos voláteis, mas reutilizam as mesmas fontes de cotação. A moeda contábil e o par de cotação continuam definidos pela conta/carteira: uma posição em carteira BRL usa USDC/BRL; em carteira USD usa USDC/USD.
- USDC, USDT, DAI, FDUSD, PYUSD, TUSD, USDP e USDE cadastrados anteriormente como `crypto` são classificados como Stablecoin na leitura, sem migração destrutiva; novas posições e aportes conhecidos persistem como `stablecoin`.
- Ativos internacionais cujo ticker operacional precisa de sufixo de bolsa podem usar alias explícito do provedor; `VWRA` em carteira USD resolve para `VWRA.L` (London Stock Exchange, listagem USD) no Yahoo Finance.
- A quantidade exibida em posições, origens e posições encerradas é normalizada com **até 2 casas decimais** (arredondamento `half-up`), independentemente da precisão cadastrada ou retornada pela cotação, para preservar o layout das tabelas.

**Fundos (`fund`):**
- Cotas dos fundos de investimento buscadas via **API Mais Retorno** quando a integração estiver ativada em Preferências (aba APIs — ver [[preferencias-abas]]), a posição tiver **CNPJ** preenchido e a carteira for em **BRL**.
- A mesma integração pode ser usada pelo formulário de Lançamentos de Contas para buscar a última cota disponível por CNPJ e preencher **Preço unitário** como sugestão editável no aporte de fundo ou previdência; essa busca não cria nem altera posição sozinha.
- Identificador da API: `{cnpj}:fi`, com o CNPJ **somente dígitos** (sem pontos e sem barra — ex.: `46.422.299/0001-73` vira `46422299000173:fi`); valor atual pela última cota do retorno e variação diária pela cota anterior.
- Requisição usa sempre `start_date` e `end_date` iguais à **data atual** (`GET /quotes/{identifier}?start_date=AAAA-MM-DD&end_date=AAAA-MM-DD`).
- O preço da cota (`c`) chega como numeral JSON com separador decimal `.` (ex.: `1.601637`) e é convertido para centavos inteiros; o app nunca exibe o valor cru da API.
- Respostas cacheadas em `quote_cache` (TTL até o **fim do dia corrente**, para não re-consumir a API ao entrar na tela várias vezes no mesmo dia) via `cached_json_url`; chamadas externas nunca ocorrem com transação de escrita aberta.
- O cache em memória das cotações deve ter limite de entradas e limpar itens expirados para evitar crescimento indefinido em instalações de longa duração.
- Em dias sem cota publicada (fins de semana e feriados), a consulta da data atual retorna lista vazia e o app refaz automaticamente a consulta com janela retroativa de **7 dias** (`start_date` = hoje − 7, `end_date` = hoje), usando a última cota publicada; somente se a janela inteira vier vazia a posição mantém o erro amigável.
- Sem integração ativada, sem CNPJ ou em moeda não-BRL, a posição mantém o valor de custo com status `Cotacao manual pendente` (comportamento anterior).
- Falha da API (indisponível, chave inválida ou cota do plano esgotada) mantém o valor de custo com status amigável, sem bloquear o Portfólio.
- A cotação de múltiplas posições independentes deve ocorrer em paralelo com limite pequeno de workers, para evitar que 10+ ativos sem cache bloqueiem a renderização pela soma serial dos timeouts externos.
- Consultas do Portfólio não devem ordenar em SQL quando a ordenação final já é feita em memória após consolidar operações e posições iniciais; listagens ordenadas diretamente pelo banco, como histórico de posições encerradas, devem ter índice compatível.

**Resgates e encerramentos:**
- Resgates retornam valor para a conta da carteira. Em posições com múltiplas origens, consumo segue FIFO.
- Resgates e atualização manual de valor atual devem usar modais internos do app, com campos rotulados, valor padrão preenchido e ação secundária de cancelamento, evitando prompts nativos do navegador.
- Encerramento move a posição para Histórico com os valores no momento do resgate/fechamento.
- No encerramento, o usuário informa data, valor final e pode optar por registrar o valor final como receita na conta da carteira em um modal único de decisão.
- A opção de registrar crédito deve ficar desmarcada por padrão para evitar duplicidade com resgates ou créditos já lançados.

**Estrutura em abas:**
- A tela Portfólio é dividida em **três abas** (padrão de pílulas do design system): **Posição** (Resumo da carteira, formulário de ativo e posição atual), **Análise** (consolidações Por classe, Por indexador, Por moeda e Por carteira) e **Histórico** (posições encerradas).
- Apenas o painel da aba ativa fica visível; a navegação preserva o estado das demais abas e não altera filtros nem dados.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/portfolio` |
| `GET` | `/api/portfolio/returns` |
| `GET` | `/api/portfolio/fund-quote?cnpj={cnpj}` |
| `POST` | `/api/portfolio/positions` |
| `PUT` | `/api/portfolio/positions/{id}` |
| `DELETE` | `/api/portfolio/positions/{id}` |
| `POST` | `/api/portfolio/redeem` |
| `POST` | `/api/portfolio/close` |
| `PUT` | `/api/portfolio/value` |
| `DELETE` | `/api/portfolio/value` |

Tabelas: `investment_opening_positions` e `investment_operations` (incluem `emergency_reserve_eligible` para posições/aportes elegíveis), `investment_redemptions`, `investment_redemption_summaries` (snapshot por resgate com bruto, líquido, taxas, custo FIFO, resultado realizado e posição remanescente), `investment_closed_positions`, `investment_value_overrides`, `transactions`, `checking_accounts`, `quote_cache`. A configuração da integração Mais Retorno vive em `secure_configs` (ver [[preferencias-abas]]).

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
- [x] Reduzir ruído visual dos formulários de renda fixa com chips, microcopy dinâmica, presets e preview.
- [x] Reutilizar ativos existentes por autocomplete nos formulários de Portfólio e Lançamentos, preservando digitação livre.
- [x] Adicionar resgate por quantidade com cotação, valor bruto, taxas, crédito líquido e saldo remanescente sincronizados.
- [x] Consumir quantidade e custo dos lotes por FIFO e manter compatibilidade com ativos sem quantidade.
- [x] Cobrir baixa quantitativa, custo FIFO e crédito líquido com teste automatizado.
- [x] Persistir snapshot imutável do resultado realizado e da posição remanescente por resgate.
- [x] Exibir resgates parciais e posições encerradas em seções próprias da aba Histórico.

## Critérios de aceite

- Dado ativos de diferentes classes cadastrados, quando o portfólio é exibido, aparecem agrupados por classe com cotações atualizadas.
- Dado consolidações por classe, indexador, moeda ou carteira com moedas distintas, quando as barras são exibidas, seu tamanho é calculado pelo valor atual convertido para BRL, enquanto o texto mantém a moeda original.
- Dado um ativo de renda fixa pós-fixado, quando listado, exibe indexador, taxa e rendimento bruto/líquido com impostos regressivos.
- Dado um ativo pré-fixado, quando listado, exibe `Pré-fixado` e a taxa anual.
- Dado o usuário cadastrando renda fixa, quando alterna entre pré-fixada, pós-fixada e híbrida, então o campo explica a unidade correta e orienta que `123% do CDI` deve ser cadastrado como pós-fixado com indexador CDI e percentual 123, enquanto CDI puro pode ficar vazio/zero para representar 100%.
- Dado o usuário cadastrando renda fixa, quando precisa de orientação sobre pré-fixada, pós-fixada ou híbrida, então um ícone discreto abre um helper contextual sem ocupar espaço permanente no formulário.
- Dado o helper contextual de renda fixa aberto, quando exibido, então apresenta exemplos de preenchimento para pré-fixada, pós-fixada e híbrida.
- Dado o usuário cadastrando renda fixa, quando escolhe modalidade por chips, então o valor submetido permanece compatível com a API existente.
- Dado o usuário cadastrando renda fixa, quando altera modalidade, indexador ou taxa, então a interface atualiza rótulo, placeholder e preview compacto da configuração.
- Dado o usuário cadastrando renda fixa, quando usa um atalho comum, então modalidade, indexador e taxa são preenchidos automaticamente sem alterar a regra financeira persistida.
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
- Dado uma posição de Poupança com múltiplos aniversários, quando ocorre resgate parcial, então o valor resgatado consome primeiro o saldo dos aniversários mais antigos.
- Dado uma posição de Poupança com resgate total, quando o Portfólio é recalculado, então a posição deixa de aparecer como aberta.
- Dado uma posição de Tesouro Prefixado, IPCA+ ou Selic padrão com cálculo na curva, quando o Portfólio calcula o valor líquido, então deduz a Taxa B3 estimada de 0,20% a.a. pro rata, aplicando isenção simplificada de R$ 10.000,00 apenas para Tesouro Selic.
- Dado uma posição de Tesouro Direto exibida no Portfólio, quando o usuário lê a listagem, então há nota discreta informando que o cálculo é na curva e pode divergir da marcação a mercado do site do Tesouro.
- Dado o usuário abrindo o Portfólio, quando a seção "Resumo da Carteira" é exibida, então o card "Rentabilidade" mantém o percentual total por moeda e exibe um botão para abrir o gráfico mês a mês.
- Dado o usuário clicando no botão de gráfico do card "Rentabilidade", quando o drawer é aberto, então ele exibe barras comparando a carteira e o CDI.
- Dado uma carteira com posições em BRL e USD, quando o gráfico de rentabilidade é exibido, então há séries separadas para cada moeda, mantendo o CDI como benchmark visível.
- Dado o primeiro investimento cadastrado em Jun/2026, quando o usuário consulta rentabilidade em Ago/2026, então o gráfico mostra os meses disponíveis (Jun, Jul, Ago), usando 100% do período cadastrado.
- Dado uma posição de fundo com CNPJ em carteira BRL e a integração Mais Retorno ativada nas Preferências, quando o Portfólio é carregado, então a posição usa a última cota da API como valor atual, com fonte e data da cota.
- Dado um CNPJ de fundo ou previdência e Mais Retorno configurada, quando o formulário de Lançamentos consulta `/api/portfolio/fund-quote`, então recebe a última cota disponível, data e fonte sem persistir alterações.
- Dado uma posição de Previdência Privada com CNPJ em carteira BRL e a integração Mais Retorno ativada, quando o Portfólio é carregado, então a posição usa a última cota da API como valor atual, com fonte e data da cota.
- Dado uma posição de fundo sem integração ativada, sem CNPJ ou em carteira não-BRL, quando o Portfólio é carregado, então a posição mantém o valor de custo com status `Cotacao manual pendente` e nenhuma chamada à API Mais Retorno é feita.
- Dado uma posição de fundo com a API Mais Retorno indisponível, quando o Portfólio é carregado, então a posição mantém o valor de custo com status amigável e o restante do portfólio segue funcionando.
- Dado posições com quantidade de alta precisão (ex.: `94,65389`), quando o Portfólio é exibido, então a quantidade aparece com no máximo 2 casas decimais para preservar o layout das tabelas.
- Dado o módulo Portfólio aberto, quando o usuário navega entre as abas **Posição**, **Análise** e **Histórico**, então apenas o painel da aba ativa é exibido e os dados das demais abas permanecem preservados.
- Dado um ativo de renda fixa com taxa cadastrada, quando listado no Portfólio, então a variação do dia é a diferença entre o valor líquido na curva de hoje e o do dia anterior, zerada no dia da aquisição.
- Dado um ativo de renda fixa pós-fixado em dia sem taxa publicada (fim de semana/feriado), quando listado no Portfólio, então a variação do dia exibe zero, sem crescimento artificial do indexador.
- Dado um ativo de Poupança com aniversários cadastrados, quando listado no Portfólio, então a variação do dia reflete a diferença de valor entre hoje e o dia anterior, concentrada no mês do aniversário.
- Dado o usuário cadastrando posição inicial no Portfólio, quando seleciona **Previdência Privada**, então o campo CNPJ opcional aparece com o mesmo comportamento dos Fundos de investimento e o valor preenchido é persistido na posição.
- Dado uma posição marcada como reserva de emergência, quando a aba **Posição** é exibida, então a coluna **Tipo** mostra um ícone pequeno de escudo ao lado do tipo do ativo, com tooltip "Reserva de emergência", sem alterar a largura nem a área da tabela.
- Dado uma posição inicial em moeda estrangeira sem cotação manual, quando criada, então a taxa de conversão é a última PTAX de venda disponível até a data de aquisição (comportamento igual a Lançamentos), sem gravar taxa fixa `1,0`; o formulário de posição não envia mais o valor padrão `1,0`.
- Dado USDC, USDT ou outra stablecoin reconhecida em uma conta BRL ou USD, quando o Portfólio é carregado, então a posição aparece na classe Stablecoin e usa o par de cotação da moeda da conta, mantendo a consolidação secundária em BRL.
- Dado uma posição legada de stablecoin persistida como `crypto`, quando ela é lida, então o sistema a reclassifica de forma compatível como `stablecoin`, sem alterar BTC, ETH ou outros criptoativos voláteis.
- Dado uma posição com ajuste manual, quando exibida, então a célula de cotação oferece uma ação contextual pequena para voltar à fonte automática; após confirmação, o override é removido e a cotação disponível é consultada novamente.
- Dado uma posição sem ajuste manual, quando exibida, então a ação de voltar à cotação automática não ocupa espaço na tabela.
- Dado VWRA em uma carteira USD, quando a cotação automática é consultada ou restaurada, então o resolvedor usa `VWRA.L` e preserva USD como moeda contábil da posição.
- Dado o usuário confirmando o retorno à cotação automática, enquanto a consulta é processada, então o botão muda para `Atualizando...`, fica desabilitado e a célula anuncia estado ocupado; ao concluir, o botão desaparece e um toast confirma a restauração sem recarregar a página inteira.
- Dado o usuário saindo do Portfólio e retornando à tela, quando o módulo é reaberto, então o app revalida os dados persistidos no backend sem forçar nova consulta externa de cotações, mantendo removido o botão de retorno automático após a restauração.
- Dado uma carteira válida selecionada no formulário de posição inicial, quando o usuário salva um ativo de qualquer categoria, inclusive Stablecoin, então o identificador da carteira é enviado antes de os controles entrarem em estado ocupado e a posição é cadastrada sem falso erro de carteira ausente.
- Dado ativos existentes no Portfólio, quando o usuário digita o código no cadastro de posição inicial ou em um lançamento de investimento, então recebe sugestões, pode selecionar um ativo para preencher seu nome e continua podendo informar um código novo livremente.
- Dado um ativo com quantidade positiva, quando o usuário abre **Resgatar**, então o formulário mostra quantidade disponível/a resgatar, cotação unitária, valor bruto, taxas, crédito líquido e quantidade remanescente.
- Dado o usuário alterando quantidade, cotação ou taxas no resgate quantitativo, quando o formulário é atualizado, então valor bruto, saldo líquido e quantidade remanescente são recalculados antes da confirmação.
- Dado uma posição formada por múltiplos aportes, quando ocorre um resgate quantitativo parcial, então os lotes mais antigos são consumidos primeiro (FIFO), preservando quantidade e custo dos lotes restantes.
- Dado um resgate quantitativo com taxas, quando confirmado, então a baixa registra o valor bruto realizado e a conta recebe somente o saldo líquido; quantidades acima do disponível e taxas acima do bruto são rejeitadas.
- Dado um resgate confirmado, quando consultado posteriormente na aba Histórico, então exibe quantidade baixada, valor bruto, taxas, valor líquido, custo FIFO, ganho/perda realizado e quantidade/custo remanescentes conforme o snapshot do momento da operação.
- Dado operações posteriores sobre o mesmo ativo, quando um resgate antigo é consultado, então seus valores realizados e remanescentes históricos não são recalculados nem alterados retroativamente.
- Dado a aba Histórico aberta, quando há resgates parciais e/ou posições encerradas, então eles aparecem em seções distintas e o estado vazio orienta que ambos os eventos serão registrados ali.

## Changelog

- `2.40` — 2026-08-29 — Aba Histórico passa a exibir resgates com ganho/perda realizado, custo FIFO consumido e quantidade/custo remanescentes em snapshot imutável.
- `2.39` — 2026-08-29 — Botão Resgatar preserva a quantidade da posição no payload do modal, ativando os campos quantitativos para ativos como AOM, ETH e ISAE4.
- `2.38` — 2026-08-29 — Autocomplete reutiliza ativos existentes nos cadastros e resgate quantitativo sincroniza quantidade, cotação, bruto, taxas, líquido e remanescente com baixa FIFO por lote.
- `2.37` — 2026-08-29 — Formulário de posição inicial captura o payload antes de desabilitar os controles durante o salvamento, preservando a carteira selecionada para Stablecoins e demais categorias.
- `2.36` — 2026-08-29 — Entrada no Portfólio passa a revalidar o estado persistido sem atualizar forçadamente as fontes externas, eliminando dados antigos após navegar para outro módulo e voltar.
- `2.35` — 2026-08-29 — Restauração da cotação automática ganha feedback localizado durante a consulta, atualização do horário e confirmação por toast sem perder o contexto da rolagem.
- `2.34` — 2026-08-29 — Correção do retorno automático de VWRA: ticker em carteira USD passa a resolver para a listagem `VWRA.L` da London Stock Exchange no Yahoo Finance.
- `2.33` — 2026-08-29 — Posições com valor manual ganham ação contextual na célula de cotação para remover o override e restaurar imediatamente a fonte automática.
- `2.32` — 2026-08-29 — Stablecoins ganham classe própria no Portfólio, herdam a moeda de cotação da carteira e posições legadas conhecidas são reclassificadas em leitura sem migração destrutiva.
- `2.31` — 2026-08-22 — Flyover de rentabilidade mensal ampliado e refinado visualmente em SVG nativo; ver [[rentabilidade-portfolio]] v1.7.
- `2.30` — 2026-08-20 — Sincronizada a data do callout de status com o frontmatter; sem alteração de comportamento.
- `2.29` — 2026-08-11 — Posição inicial em moeda estrangeira sem cotação manual passa a usar a última PTAX de venda até a data de aquisição (antes gravava taxa fixa `1,0`, distorcendo valores em BRL do Portfólio); formulário de posição deixa de enviar `1,0` como padrão.
- `2.28` — 2026-08-11 — Coluna **Tipo** da aba Posição ganha ícone pequeno de escudo (verde, indicador de saúde financeira) ao lado do tipo do ativo para posições marcadas como reserva de emergência, com tooltip; sem aumento de área do gráfico/tabela.
- `2.27` — 2026-08-11 — Helper (?) de modalidade da renda fixa alinhado inline ao rótulo (`field-label-title`), corrigindo a quebra de layout no formulário do Portfólio (mesma correção aplicada em Lançamentos).
- `2.26` — 2026-08-11 — Formulário de posição do Portfólio equalizado com o de Lançamentos: modalidade (Pós/Pré/Híbrida) em combo com helper (?); controles segmentados, chips e presets removidos do app.
- `2.25` — 2026-08-11 — Formulário de Renda Fixa do Portfólio: removidos os presets (100% do CDI, 120% do CDI, IPCA + 6,5%); opção selecionada da modalidade destacada em cor de accent; marcador de reserva de emergência sem moldura.
- `2.24` — 2026-08-11 — Formulário de Renda Fixa do Portfólio alinhado ao de Lançamentos: escolha de modalidade (Pós/Pré/Híbrida) em lista segmentada centralizada em linha própria, sempre visível; removida a frase "Atalhos comuns:" dos presets.
- `2.23` — 2026-08-10 — Formulário de posição inicial do Portfólio passa a exibir o campo CNPJ opcional também para Previdência Privada (rótulo `CNPJ do fundo/plano`), alinhado aos Fundos, que usam a mesma integração Mais Retorno.
- `2.22` — 2026-08-10 — Renda fixa e Poupança passam a exibir variação do dia no Portfólio: diferença do valor na curva entre hoje e o dia anterior, limitada à data de aquisição (zero no dia da aquisição); pós-fixados variam apenas em dias úteis com taxa publicada, pré-fixados variam pro rata diário.
- `2.21` — 2026-08-10 — Resgates de Poupança passam a consumir saldos de aniversários por FIFO; resgate total remove a posição aberta automaticamente.
- `2.20` — 2026-08-10 — Previdência Privada com CNPJ passa a usar Mais Retorno para cotação no Portfólio e no preenchimento assistido de lançamentos.
- `2.19` — 2026-08-10 — Integração Mais Retorno exposta também como busca assistida de cota por CNPJ para o formulário de Lançamentos de Contas, sem persistência automática.
- `2.18` — 2026-08-09 — Consulta principal do Portfólio remove ordenação SQL redundante antes da consolidação em memória; histórico de posições encerradas passa a ter índice compatível com a ordenação por usuário/data/id.
- `2.17` — 2026-08-09 — Cache em memória de cotações/câmbio passa a ter limite de entradas e limpeza de expirados; referência da configuração Mais Retorno atualizada para `secure_configs`.
- `2.16` — 2026-08-09 — Cotações de posições independentes passam a ser aplicadas em paralelo com limite de workers, reduzindo bloqueio de Portfólio quando vários ativos precisam consultar APIs externas sem cache.
- `2.15` — 2026-08-08 — Tela Portfólio dividida em três abas (Posição, Análise, Histórico) seguindo o padrão de pílulas do design system.
- `2.14` — 2026-08-08 — Cotações Mais Retorno resilientes a dias sem cota publicada: quando a data atual retorna lista vazia (fim de semana/feriado), o app re-consulta com janela retroativa de 7 dias e usa a última cota disponível; cache diário preservado.
- `2.13` — 2026-08-08 — Integração Mais Retorno corrigida: identificador com CNPJ somente dígitos + `:fi`, requisição sempre com `start_date`/`end_date` = data atual, cache diário (até o fim do dia) em vez de 90 minutos e conversão explícita do separador decimal `.` para centavos.
- `2.12` — 2026-08-08 — Quantidade exibida em posições, origens e posições encerradas normalizada para no máximo 2 casas decimais (arredondamento `half-up`), preservando o layout das tabelas.
- `2.11` — 2026-08-08 — Posições de fundos (`fund`) passam a cotar pela API Mais Retorno quando a integração está ativada em Preferências (aba APIs), a posição tem CNPJ e a carteira é BRL; cache em `quote_cache` e fallback de custo sem bloquear o Portfólio. Ver [[preferencias-abas]] e ADR-0009.
- `2.10` — 2026-08-07 — Resgate e encerramento de posições recalculam valor disponível e posições dentro da transação SQLite de escrita (via `begin_immediate`), eliminando janela TOCTOU entre a leitura das posições e os inserts. Cotação continua pré-cacheada fora do lock para não reter conexão durante chamadas externas.
- `2.9` — 2026-08-06 — Adicionado card "Rentabilidade mês a mês" no Resumo da Carteira com gráfico de barras por moeda e benchmark CDI, via endpoint `GET /api/portfolio/returns`.
- `2.8` — 2026-08-02 — Formulários de Renda Fixa no Portfólio e Lançamentos ganham redução de ruído visual com chips, microcopy dinâmica, presets e preview.
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
