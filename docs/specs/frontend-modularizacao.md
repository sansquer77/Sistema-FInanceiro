# Modularizacao do frontend

## Problema

O arquivo `web/app.js` concentra estado de tela, chamadas de API, formatadores, renderizacao, regras auxiliares e handlers de todos os modulos. Isso dificulta leitura, revisao e evolucao sem regressao.

## Usuario

Analistas e mantenedores do Sistema Financeiro que precisam evoluir a interface local com seguranca, mantendo o app simples e sem etapa de build.

## Jornada

1. O mantenedor abre a pasta `web/`.
2. Ele encontra responsabilidades comuns em `web/modules/`.
3. Ele evolui uma area funcional sem precisar percorrer todo o `app.js`.
4. O navegador carrega a interface por ES Modules nativos.

## Dados

- `web/app.js`: ponto de entrada e orquestracao geral.
- `web/modules/api.js`: chamadas HTTP JSON e upload.
- `web/modules/date-utils.js`: datas locais, meses e exibicao de datas.
- `web/modules/money-utils.js`: formatacao e parsing numerico/monetario.
- `web/modules/dom-utils.js`: helpers pequenos de formulario, mensagens, empty state e escaping.
- `web/modules/transaction-kind.js`: predicados de tipo de lancamento.
- `web/modules/labels.js`: labels de dominio usados pela interface.
- `web/modules/month-picker.js`: popover reutilizavel de selecao de mes.

## Regras

- Nao alterar comportamento observavel da interface nesta entrega.
- Nao introduzir framework, bundler ou dependencias de frontend.
- Modulos devem ter nomes em ingles e funcoes pequenas.
- Regras financeiras permanecem no dominio Python; o frontend apenas formata e orquestra.
- Novos modulos funcionais devem receber dependencias explicitamente quando forem extraidos.

## Fronteiras recomendadas

### Modulos ja extraidos

- `api`: comunicacao com o servidor local.
- `date-utils`: datas locais, competencia mensal e exibicao.
- `money-utils`: parsing e formatacao de valores.
- `dom-utils`: helpers pequenos e sem regra financeira.
- `transaction-kind`: predicados reutilizados por relatorios, cockpit e lancamentos.
- `labels`: labels e caminhos de categoria.
- `month-picker`: componente pequeno compartilhado entre lancamentos, cartoes, limites e relatorios.
- `auth-view`: login, cadastro, logout e recuperacao de senha.
- `user-admin-view`: troca de email/senha, configuracao assistida de recuperacao por email, limpeza de lancamentos e exclusao de usuario autenticado.
- `classifications-view`: categorias, subcategorias, tags, formularios, mensagens e CRUD.
- `limits-view`: limites de gastos, resumo mensal, indice de consumo e alerta de limite do cockpit.
- `reports-view`: filtros, abas, agrupamentos, totais multimoeda e tabelas de relatorio.
- `imports-view`: upload, download de modelo, selecao de conta/cartao e apresentacao do resultado.
- `cockpit-view`: resumo financeiro, saldos por moeda, graficos, planejamento mensal, dividas parceladas, visao resumida do portfolio e alerta de limites.
- `accounts-view`: cadastro, edicao, arquivamento, restauracao, estado de formulario por tipo de conta e logos de contas.
- `cards-view`: cadastro de cartoes, arquivamento, restauracao, faturas, pagamento de fatura, lancamentos de cartao, conciliacao e navegacao de competencia.
- `portfolio-view`: cadastro de ativos, posicoes, historico, agrupamentos, resgate, encerramento e atualizacao de valor.
- `transactions-view`: formulario de lancamentos, busca, agrupamento por data, recorrencia, parcelas, cambio e investimento.

### Proximos modulos funcionais

- Nenhum modulo funcional grande pendente nesta frente. Novas extracoes devem ser avaliadas por area quando surgirem evolucoes relevantes.

### Contrato sugerido para views

Cada view deve exportar uma funcao `create*View(context)` ou `register*View(context)` recebendo somente as dependencias que usa:

- `state`: estado centralizado da tela.
- `elements`: referencias DOM daquela area.
- `services`: `api`, `upload` e carregadores compartilhados.
- `formatters`: funcoes de data, dinheiro e labels.
- `actions`: callbacks de navegacao ou refresh global.

Esse contrato evita imports circulares e deixa claro o que cada modulo toca.

## API e dados

- Nenhum endpoint novo.
- Nenhuma tabela nova.
- `index.html` passa a carregar `app.js` como `type="module"`.

## Criterios de aceite

- Dado o app carregado, quando o navegador busca `app.js`, entao seus imports de `web/modules/` resolvem sem erro.
- Dado um fluxo existente de login, navegacao, lancamentos, cartoes, relatorios e portfolio, quando usado, entao as chamadas de API e formatacoes continuam iguais.
- Dado um mantenedor lendo o frontend, quando busca formatacao monetaria, datas ou API, entao encontra essas responsabilidades fora do arquivo principal.
- Dado um mantenedor lendo categorias, limites ou relatorios, quando busca seus formularios, handlers e renderizacao, entao encontra esses fluxos em `classifications-view`, `limits-view` e `reports-view`.
- Dado um mantenedor lendo importacao, quando busca upload, download de modelo ou resultado da importacao, entao encontra esse fluxo em `imports-view`.
- Dado um mantenedor lendo o cockpit, quando busca resumo financeiro, graficos, planejamento, dividas parceladas ou alerta de limites, entao encontra esse fluxo em `cockpit-view`.
- Dado um mantenedor lendo contas, quando busca cadastro, edicao, arquivamento, restauracao ou logos, entao encontra esse fluxo em `accounts-view`.
- Dado um mantenedor lendo cartoes, quando busca cadastro, faturas, pagamento, lancamentos ou conciliacao, entao encontra esse fluxo em `cards-view`.
- Dado um mantenedor lendo portfolio, quando busca cadastro de ativos, posicoes, historico, agrupamentos, resgate, encerramento ou atualizacao de valor, entao encontra esse fluxo em `portfolio-view`.
- Dado um mantenedor lendo lancamentos, quando busca formulario, busca, agrupamento por data, recorrencia, parcelas, cambio ou investimento, entao encontra esse fluxo em `transactions-view`.

## Fora de escopo

- Reescrever HTML/CSS.
- Criar build step.
- Alterar regras financeiras, endpoints ou banco.
- Refatorar regras de dominio do backend ou dividir utilitarios menores que ainda estejam coesos no ponto de entrada.
