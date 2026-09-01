---
tipo: spec
area: frontend
status: implementado
versao: 4.22
atualizado: 2026-08-31
relacionados:
  - "[[adr/0002-modularizacao-frontend]]"
  - "[[arquitetura]]"
  - "[[../qualidade-codigo]]"
tags: [spec, "area/frontend", "status/implementado"]
aliases: ["Modularização Frontend", "ES Modules"]
---

# Modularização do Frontend

> [!info] Status
> **implementado** · área: `frontend` · atualizado em 2026-08-31 · relacionados: [[adr/0002-modularizacao-frontend]], [[arquitetura]], [[../qualidade-codigo]]

## Problema

O arquivo `web/app.js` concentrava estado de tela, chamadas de API, formatadores, renderização, regras auxiliares e handlers de todos os módulos. Isso dificultava leitura, revisão e evolução sem risco de regressão.

## Usuário

Mantenedores e agentes de IA em IDEs que precisam evoluir a interface local com segurança, mantendo o app simples e sem etapa de build.

## Jornada

1. O mantenedor abre a pasta `web/`.
2. Encontra responsabilidades comuns em `web/modules/`.
3. Evolui uma área funcional sem precisar percorrer todo o `app.js`.
4. O navegador carrega a interface por ES Modules nativos.

## Módulos utilitários

| Arquivo | Responsabilidade |
|---|---|
| `api.js` | Chamadas HTTP JSON e upload. |
| `date-utils.js` | Datas locais, meses e exibição. |
| `money-utils.js` | Formatação e parsing numérico/monetário. |
| `dom-utils.js` | Helpers de formulário, mensagens e empty state. |
| `chart-adapter.js` | Ciclo de vida, tokens, movimento reduzido e fallback dos gráficos ApexCharts locais. |
| `transaction-kind.js` | Predicados de tipo de lançamento. |
| `labels.js` | Labels de domínio usados pela interface. |
| `month-picker.js` | Popover reutilizável de seleção de mês. |
| `decision-modal.js` | Modal reutilizável para decisões, confirmações explícitas e pequenos formulários. |
| `theme-utils.js` | Preferência visual local e aplicação de tema no `documentElement`. |
| `privacy-utils.js` | Preferência visual local de privacidade, aplicação de `data-privacy` e marcação visual de valores monetários. |
| `tab-utils.js` | Transição progressiva e navegação roving por teclado compartilhadas por conjuntos de abas. |
| `global-search.js` | Busca local transversal em módulos e dados já carregados, com navegação contextual. |
| `density-utils.js` | Preferência visual local de densidade e aplicação de `data-density` no documento. |
| `overlay-utils.js` | Semântica, foco e teclado compartilhados por drawers e overlays persistentes. |
| `data-ux.js` | Ordenação local, contagem de linhas e chips removíveis para tabelas e filtros. |
| `virtual-list.js` | Janela visível com overscan para coleções extensas de altura fixa. |
| `asset-autocomplete.js` | Sugestões de ativos existentes por `datalist`, preenchimento de metadados e preservação da digitação livre. |
| `instructions-content.js` | Conteúdo estático, offline e versionado da central de ajuda. |
| `bank-logos.js` | Catálogo compartilhado de logos de instituições financeiras com normalização de nomes e fallback visual. |

## Views funcionais

| Arquivo | Responsabilidade |
|---|---|
| `auth-view.js` | Login, cadastro, logout e recuperação de senha. |
| `user-admin-view.js` | Preferência visual, troca de email/senha, config. SMTP, limpeza e exclusão. |
| `classifications-view.js` | Categorias, subcategorias e tags. |
| `limits-view.js` | Limites de gastos e índice de consumo. |
| `reports-view.js` | Fachada compatível e coordenação de Relatórios; demais abas legadas mantêm renderização/agregações existentes. |
| `report-statement.js` | Filtros, consulta, modelo e impressão do demonstrativo; sem cálculos financeiros locais. |
| `report-evolution.js` | Drawer, consulta, apresentação e ciclo de vida do gráfico de evolução; sem SMA/fallback local. |
| `imports-view.js` | Upload, download de modelo e resultado da importação. |
| `cockpit-view.js` | Resumo, saldos, planejamento, dívidas, portfólio e alertas. |
| `financial-health-view.js` | Aba Saúde Financeira do Cockpit: score/gauge, pilares, Paz Financeira e recomendações. |
| `trends-view.js` | Aba Tendências do Cockpit: gráfico de evolução mensal, Budget x Realizado e achados. |
| `consultor-view.js` | Aba Consultor/Calendário do Cockpit: vencimentos, atrasos e plano próximo. |
| `accounts-view.js` | Contas: cadastro, edição, arquivamento e restauração. |
| `cards-view.js` | Cartões: cadastro, faturas, busca/filtro da fatura, pagamento e conciliação. |
| `portfolio-view.js` | Fachada/coordenador da tela de Portfólio, carregamento, abas e integração dos submódulos. |
| `portfolio-chart.js` | Renderização e ciclo de vida do gráfico de rentabilidade do Portfólio. |
| `portfolio-grouping.js` | Identidade estável de agrupamentos visuais; cálculos e consolidações pertencem ao backend. |
| `portfolio-preview.js` | Coordenação das prévias no servidor: debounce, requisição em andamento, bloqueio de confirmação e descarte de respostas obsoletas, sem regras financeiras. |
| `portfolio-form.js` | Payloads e normalizações de entrada dos formulários e ações do Portfólio. |
| `portfolio-lifecycle.js` | Política pura de frescor do snapshot e limpeza seletiva da apresentação do Portfólio. |
| `app-state.js` | Fábrica do estado inicial e reset puro dos dados de sessão, sem DOM, API ou views. |
| `app-data-loader.js` | Coordenação dos carregamentos compartilhados, com serviços, views e ações recebidos explicitamente. |
| `load-policy.js` | Política compartilhada de snapshot recente, invalidação e promessa em andamento. |
| `transaction-slice-loader.js` | Cache limitado por conta+mês, requisições concorrentes por chave, invalidação e proteção contra respostas antigas no Extrato. |
| `transaction-reconciliation.js` | Estado ocupado, aplicação imediata da resposta confirmada e atualização independente dos saldos após conciliar. |
| `transaction-refresh.js` | Aplica confirmação de edição/criação/exclusão, revalida a fatia e atualiza dados auxiliares sem bloquear a tela; descarta respostas de revisões/sessões anteriores. |
| `transaction-balance-chart.js` | Apresentação e ciclo de vida do gráfico mensal de saldos do Extrato. |
| `classification-suggestion.js` | Classificação assistida reutilizável pelos formulários de Contas e Cartões. |
| `transaction-list.js` | Busca, filtros, agrupamento diário e renderização da lista do Extrato. |
| `transaction-form.js` | Fluxo base do formulário, séries, contas, categorias e câmbio assistido pelo backend. |
| `transaction-investment-form.js` | Campos e assistência específicos do aporte de investimento. |
| `transactions-view.js` | Fachada compatível de Lançamentos; compõe lista, gráfico, formulário base/investimento e carregador. |
| `operation-history-view.js` | Histórico de Operações: filtros, busca, agrupamentos e paginação incremental. |
| `simulations-view.js` | Efeito Borboleta: formulário de cenário hipotético e projeções retornadas pelo backend. |
| `instructions-view.js` | Central de ajuda: busca, grupos, tópicos expansíveis e navegação contextual. |

Views estáticas simples, como **Sobre**, podem permanecer declaradas no HTML e roteadas por `app.js` quando não possuem estado próprio, API ou lógica funcional dedicada.

## Contrato de fábrica para views

```js
export function createXxxView({ state, elements, services, formatters, actions }) {
  // state    → estado centralizado da tela
  // elements → referências DOM daquela área
  // services → api, upload e carregadores compartilhados
  // formatters → funções de data, dinheiro e labels
  // actions  → callbacks de navegação ou refresh global
}
```

## Regras

- Não alterar comportamento observável da interface.
- Não introduzir framework, bundler ou dependências de frontend.
- Módulos têm nomes em inglês e funções pequenas.
- Regras financeiras permanecem no domínio Python; o frontend apenas formata e orquestra.
- A raiz `app.js` segue as fronteiras e os sinais de alerta de [[../qualidade-codigo]].
- Novos módulos recebem dependências explicitamente via contrato de fábrica.
- `app.js` permanece o composition root: seleciona DOM, registra views, injeta dependências, controla boot, autenticação visual e navegação.
- `app-state.js` não exporta singleton nem chama formulários/views; cria o estado e limpa somente dados de sessão.
- `app-data-loader.js` usa acesso tardio às views injetadas para evitar imports circulares e não se torna autoridade de regras financeiras.
- Views pesadas podem expor `onEnter()`/`onLeave()`; o composition root aciona esse ciclo sem conhecer detalhes internos de desmontagem.
- Cores de UI e gráficos devem vir de tokens CSS compartilhados; literais ficam restritos a marcas/logos externos.
- Tema visual é uma preferência local: `theme-utils.js` aplica `data-theme` no elemento raiz e persiste em `localStorage`.
- Modo privacidade é uma preferência local: `privacy-utils.js` aplica `data-privacy` no elemento raiz, persiste em `localStorage` e não altera dados, cálculos ou chamadas de API.
- O modo escuro deve ser evoluído por tokens em CSS, mantendo views sem ramificações por tema.
- `user-admin-view.js` apenas orquestra o controle de Preferências; persistência e aplicação do tema permanecem em `theme-utils.js`.
- Fluxos com decisão financeira, destrutiva ou de cascata devem usar `decision-modal.js`, evitando `window.confirm()` e `window.prompt()` para escolhas de domínio.
- A navegação lateral deve usar rótulos desambiguados quando dois módulos compartilham o mesmo substantivo de domínio: em **Cadastro**, usar **Minhas Contas** e **Meus Cartões**; em **Lançamentos**, usar **Extrato de Contas** e **Fatura de Cartões**.
- A navegação lateral permite colapsar/expandir cada grupo (**Cadastro**, **Lançamentos**, **Gestão** e **Usuário**) pelo rótulo do grupo, que funciona como botão com indicador de seta e `aria-expanded` coerente; o estado colapsado é uma preferência local persistida, e o grupo da view ativa abre automaticamente ao navegar.
- O item **Cockpit** é de primeiro nível na navegação; não existe mais o grupo **Visão geral**.
- Com a sidebar inteira no modo ícones (recolhida), os rótulos de grupo ficam ocultos e todos os itens permanecem acessíveis, ignorando o estado colapsado individual dos grupos.
- Os títulos de página controlados por `app.js` devem acompanhar os rótulos desambiguados da navegação para reforçar a intenção da tela ativa.
- A troca entre módulos do dashboard deve usar `document.startViewTransition()` quando disponível, como melhoria progressiva, preservando fallback instantâneo em navegadores sem suporte.
- A transição de visão deve respeitar `prefers-reduced-motion: reduce` e nunca aguardar chamadas de API, carregamentos remotos ou cálculos de tela para iniciar a navegação.
- As subtabs do Cockpit devem usar View Transitions API como melhoria progressiva, com troca instantânea quando indisponível ou quando `prefers-reduced-motion: reduce` estiver ativo.
- Durante a atualização mensal do Cockpit, a região deve anunciar `aria-busy="true"` e manter a estrutura já renderizada suavemente atenuada até a resposta mais recente, sem substituir o conteúdo por uma tela vazia.
- As subtabs do Cockpit devem permitir navegação por teclado com setas esquerda/direita e teclas Home/End, movendo foco e seleção em conjunto.
- Cockpit, Portfólio, Relatórios, Consultor e Preferências devem compartilhar o mesmo controlador nativo de abas para clique, setas, Home/End, `aria-selected`, `tabIndex` e transição progressiva.
- Carregamentos assíncronos localizados devem expor `aria-busy`, preservar conteúdo útil sempre que possível e ignorar respostas obsoletas quando mês, filtro ou aba mudar antes da conclusão.
- O Cockpit deve priorizar leitura executiva: alertas visíveis aparecem antes dos quatro KPIs; Saldos e Portfólio permanecem expandidos; Planejamento, Dívidas e gráficos de maiores receitas/despesas usam disclosure nativo recolhível com preferência local persistida.
- Enquanto o Cockpit estiver visível, título do módulo e barra de abas/mês permanecem sticky, sem ocultar conteúdo ou bloquear navegação em telas intermediárias e móveis.
- As duas superfícies sticky do Cockpit devem ser totalmente opacas com `--bg`, contíguas e separadas do conteúdo por linha sólida; conteúdo rolado nunca pode permanecer visível ou misturado por transparência/desfoque atrás delas.
- Formulários devem expor uma hierarquia previsível: ação primária primeiro, ações secundárias com menor peso e ações destrutivas visualmente separadas no extremo oposto do rodapé.
- Campos inválidos devem receber mensagem contextual junto ao próprio campo, `aria-invalid` e `aria-describedby`; a mensagem desaparece quando o valor volta a ser válido, sem limpar os demais dados preenchidos.
- Durante um envio assíncrono, o formulário anuncia `aria-busy`, impede novo envio e restaura exatamente os estados desabilitados e o rótulo original dos controles ao concluir ou falhar.
- O cabeçalho global do módulo deve permanecer sticky e opaco em todas as views autenticadas; barras internas sticky usam o offset desse cabeçalho sem sobreposição.
- Filtros de listas e relatórios compartilham uma superfície de toolbar com borda, espaçamento e comportamento responsivo coerentes.
- Tabelas de dados usam contêiner com overflow horizontal, cabeçalho sticky, rótulos de coluna consistentes e realce discreto da linha, preservando a largura necessária para dados financeiros no mobile.
- Conjuntos principais de abas do Cockpit, Portfólio e Preferências permanecem sticky e opacos abaixo do cabeçalho global, com o mesmo offset e sem cobrir o painel ativo.
- Formulários laterais, busca de Instruções e cabeçalhos diários sticky respeitam a altura do cabeçalho global em vez de se posicionarem atrás dele.
- A busca global usa diálogo HTML nativo, abre pelo cabeçalho ou atalho `/`, pesquisa somente dados já carregados da sessão e nunca envia o termo a serviço externo.
- Alternar módulos preserva a posição de rolagem de cada view; filtros, mês e aba permanecem no estado mantido pelos respectivos módulos durante a sessão.
- Resultados de lançamentos, faturas e posições preparam conta/cartão, período ou destaque correspondente antes de navegar, sem abrir automaticamente formulários de edição.
- A densidade visual oferece os modos **Confortável** (padrão) e **Compacto**, aplica `data-density` no elemento raiz e persiste somente em `localStorage`.
- O modo compacto reduz espaços, paddings e altura de linhas em superfícies densas, preservando fonte legível, foco, contraste e alvos interativos com pelo menos 34px.
- Estados localizados usam o helper compartilhado de `dom-utils.js` com quatro tipos explícitos: `loading`, `error`, `empty` e `info`; carregamento anuncia `aria-busy`, erro usa `role="alert"` e vazio oferece orientação contextual sempre que houver próxima ação conhecida.
- Nenhum módulo deve representar falha ou carregamento apenas por texto neutro em `.empty-state`; ícone, título, mensagem e semântica acessível vêm do mesmo componente.
- Overlays compartilham foco inicial, confinamento de Tab, fechamento por Escape, restauração de foco e atributos `role="dialog"`/`aria-modal`.
- Sucessos operacionais usam toast não bloqueante; erros permanecem junto à operação que falhou.
- Cabeçalhos de cards usam ações agrupadas e podem anunciar a última atualização com horário local.
- Tabelas de dados oferecem ordenação local por coluna, primeira coluna sticky, contagem de linhas e filtros ativos removíveis quando os controles pertencem a `.filter-toolbar`.
- Formulários extensos marcados como progressivos agrupam campos opcionais e exibem, somente após interação, um resumo expansível dos valores visíveis e habilitados antes das ações; valores padrão de campos condicionais ocultos não entram no resumo. Em lançamentos à vista o resumo inicia recolhido; ao alternar para parcelamento ou recorrência ele abre automaticamente.
- Textos de interface usam português brasileiro acentuado e consistente.

## Plano de implementação

- [x] Extrair demonstrativo e evolução para fábricas com dependências explícitas, preservando o contrato `registerReportsView`/`renderReports`.
- [x] Manter isolamento das respostas assíncronas e destruir o gráfico ao fechar; preservar eventos, filtros e impressão sem registros duplicados nas renderizações.
- [x] Adaptar testes aos módulos extraídos e validar composição real das fábricas.

- [x] Extrair o gráfico de saldo sem alterar sua apresentação ou navegação mensal.
- [x] Compartilhar a classificação assistida entre Lançamentos de Contas e Cartões.
- [x] Extrair busca, filtros, agrupamento e renderização da lista mensal.
- [x] Separar o formulário base dos campos e assistências próprios de investimento.
- [x] Remover cálculos cambiais financeiros do JavaScript, consumindo valores derivados pelo backend.
- [x] Preservar `transactions-view.js` como fachada compatível com o composition root atual.
- [x] Atualizar contratos automatizados e executar a suíte completa.

- [x] Extrair fábrica/reset puro de estado para `app-state.js` sem dependência de DOM.
- [x] Extrair carregamentos coordenados para `app-data-loader.js` com dependências explícitas e views tardias.
- [x] Preservar `boot()`, sessão visual, navegação e composição em `app.js`.
- [x] Atualizar contratos automatizados e validar todos os fluxos existentes.
- [x] Unificar semântica e teclado de modais, dialogs e drawers.
- [x] Centralizar toasts de sucesso e manter erros inline.
- [x] Padronizar cabeçalhos de cards e última atualização.
- [x] Enriquecer tabelas, filtros e paginação incremental.
- [x] Adicionar progressão e resumo aos formulários extensos.
- [x] Revisar microcopy do Histórico de Operações.

## API e dados

- `GET /api/balance-projection?month=YYYY-MM&account_id={id}` entrega saldos conciliados/projetados por data calculados no núcleo Python.
- Nenhuma tabela nova.
- `index.html` carrega `app.js` como `type="module"`.

## Critérios de aceite

- Dado o app carregado, quando o navegador busca `app.js`, todos os imports de `web/modules/` resolvem sem erro.
- Dado um fluxo existente (login, navegação, lançamentos, cartões, relatórios, portfólio), quando usado, as chamadas de API e formatações continuam iguais ao comportamento anterior.
- Dado um mantenedor buscando formatação monetária ou de datas, quando procura, encontra em `money-utils.js` e `date-utils.js`.
- Dado um mantenedor buscando qualquer área funcional, quando procura, encontra no arquivo de view correspondente.
- Dado o usuário autenticado, quando alterna `Claro` ou `Escuro` em Preferências, o `data-theme` do documento muda imediatamente e persiste após reload.
- Dado o tema claro ou escuro ativo, quando navega por Cockpit, Contas, Cartões, Lançamentos, Portfólio, Limites, Relatórios, Categorias, Importação e Preferências, os módulos abrem sem erro de console e mantêm contraste legível.
- Dado viewport mobile, quando abre Preferências, o controle de tema ocupa a largura disponível sem overflow horizontal.
- Dado uma decisão de edição/exclusão em cascata ou encerramento de posição, quando a interface solicita confirmação, os botões exibem ações explícitas e `Voltar` aborta a operação.
- Dado o grupo Usuário, quando o item Sobre é acionado, então `app.js` exibe uma view estática sem criar módulo ou endpoint desnecessário.
- Dado o usuário visualizando o menu lateral, quando compara os grupos Cadastro e Lançamentos, então os itens não repetem apenas `Contas` e `Cartões`; eles aparecem como **Minhas Contas**, **Meus Cartões**, **Extrato de Contas** e **Fatura de Cartões**.
- Dado o usuário acessando um desses itens, quando a tela abre, então o título da página usa o mesmo nome desambiguado do menu.
- Dado um navegador com suporte a View Transitions API, quando o usuário alterna módulos pelo menu lateral, então a troca visual acontece com transição curta e sem bloquear os carregamentos da tela.
- Dado o dashboard carregado com dados do Cockpit para o mês atual, quando o usuário navega para Cockpit novamente sem alterar mês ou dados, então a UI reaproveita o snapshot em memória e não dispara nova busca completa dos endpoints pesados.
- Dado o usuário abrindo o Portfólio, quando a tela carrega, então a aba **Posição** renderiza primeiro; **Análise**, **Histórico** e rentabilidade detalhada são renderizados/carregados sob demanda no primeiro acesso.
- Dado o usuário alterando o agrupamento ou colapsando/expandindo grupos no Portfólio, quando a tela já tem dados carregados, então apenas a lista de posições é renderizada novamente.
- Dado a interface carregando scripts de terceiros não essenciais, quando o HTML é parseado, então esses scripts não bloqueiam a inicialização do app (`async`/`defer` quando aplicável).
- Dado uma área estrutural de layout como o dashboard principal, quando o menu lateral alterna estado, então a UI não anima propriedades caras como `grid-template-columns`.
- Dado uma função de renderização frequente, quando executada, então não deve emitir logs de debug no console em operação normal.
- Dado o usuário autenticado, quando alterna o modo privacidade, então `privacy-utils.js` aplica `data-privacy` no documento sem alterar endpoints, banco ou regras financeiras.
- Dado um navegador sem suporte à API ou com redução de movimento ativa, quando o usuário alterna módulos, então a navegação continua funcionando de forma instantânea.
- Dado o menu lateral, quando o usuário clica no rótulo de um grupo, então os itens do grupo colapsam/expandem com indicador de seta e `aria-expanded` coerente.
- Dado um grupo colapsado, quando a página recarrega, então o estado colapsado persiste como preferência local.
- Dado um grupo colapsado contendo a view ativa, quando outra view do mesmo grupo é acionada, então o grupo abre automaticamente antes da navegação.
- Dado o menu lateral com a sidebar inteira no modo ícones, quando um grupo está colapsado individualmente, então todos os itens permanecem acessíveis como ícones.
- Dado o menu lateral, então o item **Cockpit** aparece como primeiro nível, sem o grupo **Visão geral**.
- Dado o código do frontend versionado, quando a suíte automatizada é executada, então todos os imports locais de `app.js` resolvem e todos os módulos em `web/modules/` estão inventariados nesta spec.
- Dado um usuário alternando Situação, Consultor, Tendências e Saúde, quando o navegador suporta View Transitions e não há preferência de redução de movimento, então o painel ativo troca com transição curta; nos demais navegadores, a troca permanece instantânea e funcional.
- Dado uma atualização de mês em andamento no Cockpit, quando as APIs ainda não responderam, então `#cockpitView` expõe `aria-busy="true"`, preserva o painel atual com atenuação discreta e remove o estado ocupado ao concluir ou falhar a requisição mais recente.
- Dado foco em uma subtab do Cockpit, quando o usuário pressiona seta esquerda/direita ou Home/End, então foco, `aria-selected`, `tabIndex` e painel visível são atualizados de forma coerente.
- Dado foco em qualquer conjunto analítico de abas do Cockpit, Portfólio, Relatórios, Consultor ou Preferências, quando o usuário navega por teclado, então todos seguem o mesmo comportamento roving e respeitam redução de movimento.
- Dado uma consulta assíncrona de Tags, Tendências, Saúde Financeira ou Portfólio, quando uma seleção posterior torna a resposta anterior obsoleta, então o resultado antigo não substitui a visão atual e o estado `aria-busy` termina de forma coerente.
- Dado o Cockpit na aba Situação, quando existem alertas de versão, limites ou vencimentos, então eles aparecem antes dos KPIs; quando não existem, o contêiner de alertas não ocupa espaço.
- Dado Planejamento, Dívidas ou os gráficos executivos, quando o usuário recolhe ou expande uma seção, então o estado persiste localmente após recarregar a página e o conteúdo financeiro não é recalculado por essa preferência visual.
- Dado o usuário rolando o Cockpit, quando o título e os controles alcançam o topo, então permanecem visíveis; em viewport de até 860px o offset é reduzido para preservar área útil.
- Dado conteúdo passando sob o cabeçalho sticky do Cockpit, quando o usuário continua a rolagem, então nenhuma linha, card ou texto fica visível através do cabeçalho ou da barra de abas.
- Dado um formulário com ações primária, secundária e destrutiva, quando exibido em desktop ou mobile, então a ação primária aparece primeiro, a secundária mantém peso neutro e a destrutiva fica separada das demais sem mudar sua semântica.
- Dado um campo obrigatório ou com restrição inválida, quando o usuário tenta enviar o formulário, então o primeiro erro recebe foco e uma mensagem contextual acessível aparece junto ao campo; ao corrigi-lo, o erro desaparece sem apagar os outros valores.
- Dado um formulário em envio, quando a operação assíncrona ainda não terminou, então um segundo envio fica bloqueado, `aria-busy` permanece verdadeiro e, ao final, os controles recuperam o mesmo estado anterior ao envio.
- Dado qualquer módulo autenticado, quando o usuário rola a página, então o cabeçalho do módulo permanece visível, opaco e sem misturar o conteúdo rolado; barras sticky internas não ficam sob ele.
- Dado uma listagem com busca ou filtros, quando exibida em desktop ou mobile, então seus controles usam o mesmo contêiner visual e se reorganizam sem overflow indevido.
- Dado uma tabela maior que a largura disponível, quando exibida em viewport estreito, então o contêiner oferece rolagem horizontal, mantém a coluna legível e o cabeçalho visível durante a rolagem vertical da tabela.
- Dado o usuário no Portfólio ou em Preferências, quando rola um painel longo, então as abas permanecem visíveis abaixo do cabeçalho global com fundo opaco e navegação por teclado preservada.
- Dado um formulário lateral ou uma barra interna sticky, quando alcança o topo durante a rolagem, então para abaixo do cabeçalho global e não fica encoberto por ele.
- Dado o usuário autenticado, quando aciona **Buscar em todo o app** ou pressiona `/` fora de um campo editável, então abre um diálogo acessível com módulos e dados locais já carregados.
- Dado um termo correspondente a conta, cartão, lançamento, ativo, categoria ou módulo, quando seleciona o resultado, então navega à view adequada e prepara seu contexto sem transmitir o termo para fora do app.
- Dado o usuário alternando entre duas views, quando retorna à anterior na mesma sessão, então posição de rolagem, filtros, período e aba continuam no contexto deixado.
- Dado o usuário em Preferências, quando seleciona densidade **Compacta** ou **Confortável**, então a interface muda imediatamente e mantém a escolha após recarregar a página.
- Dado o modo compacto ativo, quando navega por cards, formulários, listas, tabelas e toolbars, então o conteúdo ocupa menos espaço sem cortar texto, valores, foco ou controles.
- Dado uma região assíncrona, quando carrega, falha ou não possui dados, então exibe o mesmo componente de estado com título, mensagem, ícone não dependente apenas de cor e atributos ARIA adequados ao tipo.
- Dado um estado vazio com próxima ação conhecida, quando exibido, então a mensagem orienta cadastro, seleção, mudança de filtro ou lançamento necessário em vez de apresentar somente “Nenhum dado”.
- Dado qualquer overlay aberto, quando o usuário usa Tab, Shift+Tab ou Escape, então o foco permanece no overlay, o fechamento ocorre de forma previsível e o foco retorna ao acionador.
- Dado uma operação concluída com sucesso, quando a resposta chega, então um toast discreto anuncia o resultado sem reservar espaço no formulário.
- Dado uma tabela de dados, quando o usuário aciona um cabeçalho, então as linhas são ordenadas e `aria-sort` reflete a direção; a primeira coluna permanece visível na rolagem horizontal.
- Dado filtros preenchidos, quando a listagem é exibida, então chips mostram os filtros ativos e permitem removê-los individualmente.
- Dado um formulário extenso, quando campos opcionais existem, então ficam em seção progressiva e um resumo dos valores preenchidos aparece antes de salvar.
- Dado um formulário novo ainda sem interação ou um campo condicional oculto/desabilitado, quando o resumo é calculado, então ele permanece vazio ou ignora esse campo, mesmo que o controle tenha valor padrão.
- Dado um lançamento simples à vista, quando o usuário preenche o formulário, então o resumo fica disponível recolhido; ao mudar a repetição para parcelada ou recorrente, ele se expande automaticamente.

## Fora de escopo

- Reescrever HTML/CSS.
- Criar build step.
- Alterar regras financeiras, endpoints ou banco.

## Changelog

- `4.22` — 2026-08-31 — Extração da apresentação de demonstrativo/evolução e coordenação pela fachada compatível de Relatórios.

- `4.21` — 2026-08-31 — Cálculos residuais do Portfólio movidos para Python; views recebem resultados, composição, metas e agregados. Prévias editáveis usam coordenador assíncrono e a participação por moeda do resumo do Cockpit vem do backend.

- `4.20` — 2026-08-31 — Documentada a coordenação de atualização após salvar lançamentos, separada de recargas auxiliares.
- `4.19` — 2026-08-31 — Fatias do Extrato ganham cache limitado e concorrência por chave; conciliação isolada atualiza a linha antes das recargas secundárias.

- `4.18` — 2026-08-31 — Concluída a decomposição de Lançamentos; a fachada preserva o contrato público e Cartões reutiliza a classificação assistida compartilhada.
- `4.17` — 2026-08-31 — Iniciada a decomposição de `transactions-view.js` em gráfico, classificação compartilhada, lista e formulários especializados, preservando a fachada pública atual.
- `4.16` — 2026-08-31 — Removidos coordenadas e geradores de path SVG sem consumidores do Extrato; teste impede reintrodução do legado após a migração para ApexCharts.
- `4.15` — 2026-08-31 — Iniciada remoção dos resíduos SVG sem consumidores em `transactions-view.js`, preservando o gráfico ApexCharts vigente.
- `4.14` — 2026-08-30 — Política `dirty + loadedAt + in-flight` concluída em Preferências, Histórico, Extrato e Simulações, com chave contextual, proteção contra corrida e reset de sessão.
- `4.13` — 2026-08-30 — Iniciada política compartilhada `dirty + loadedAt + in-flight` para carregamentos de views.
- `4.12` — 2026-08-30 — Adicionado `bank-logos.js` como catálogo compartilhado de logos de instituições financeiras, usado em Contas e Cartões.
- `4.11` — 2026-08-30 — Adicionado `virtual-list.js` para virtualização progressiva de listas extensas de Portfólio, Lançamentos e Relatórios.
- `4.10` — 2026-08-30 — Concluído o primeiro contrato `onEnter()`/`onLeave()` no Portfólio, acionado pelo composition root e coberto por testes de fronteira.
- `4.9` — 2026-08-30 — Iniciado ciclo de vida seletivo para liberar DOM e recursos gráficos de views pesadas sem descartar seu estado de dados.
- `4.8` — 2026-08-30 — Concluída a extração de estado e carregamentos coordenados, com contratos automatizados para preservar as fronteiras do composition root.
- `4.7` — 2026-08-30 — Iniciada extração de estado puro e carregadores coordenados, preservando `app.js` como composition root.
- `4.6` — 2026-08-30 — Vinculada à spec implementada [[../qualidade-codigo]], que formaliza a distinção entre raiz de composição e views coesas.
- `4.5` — 2026-08-30 — `portfolio-view.js` passa a coordenar módulos dedicados de gráfico, agrupamento e formulário; projeções de saldos/faturas deixam `app.js` e passam ao contrato Python `/api/balance-projection`.
- `4.4` — 2026-08-30 — Registrado `chart-adapter.js` como fronteira compartilhada entre as views e o ApexCharts 4.7.0 vendorizado.
- `4.3` — 2026-08-29 — Autocomplete de ativos compartilhado entre Portfólio e Lançamentos; modal de decisão passa a aceitar atualização derivada de campos durante a digitação.
- `4.2` — 2026-08-29 — Resumo pré-salvamento torna-se expansível, recolhido em lançamentos à vista e aberto automaticamente nos modos parcelado e recorrente.
- `4.1` — 2026-08-29 — Resumo pré-salvamento passa a iniciar vazio e ignorar controles condicionais ocultos ou desabilitados.
- `4.0` — 2026-08-29 — Consolidação final de overlays, toasts, cabeçalhos/atualização, tabelas/filtros, formulários progressivos e microcopy.
- `3.9` — 2026-08-29 — Estados loading/erro/vazio/info centralizados em componente acessível, com semântica, tom, ícone e orientação contextual consistentes.
- `3.8` — 2026-08-28 — Densidade configurável adicionada com modos Confortável/Compacto, persistência local e compactação segura das principais superfícies de dados.
- `3.7` — 2026-08-28 — Busca global local adicionada com atalho `/`, navegação contextual e preservação da posição de rolagem por módulo durante a sessão.
- `3.6` — 2026-08-28 — Abas de Portfólio e Preferências passam a permanecer sticky como no Cockpit; offsets de formulários e barras internas são alinhados ao cabeçalho global.
- `3.5` — 2026-08-28 — Cabeçalho sticky opaco promovido a padrão global; filtros e tabelas recebem toolbar, overflow, cabeçalho e estados de interação unificados.
- `3.4` — 2026-08-28 — Hierarquia de formulários padronizada com ação primária primeiro, destrutiva separada, validação contextual acessível e estado de envio que preserva os controles condicionais.
- `3.3` — 2026-08-28 — Superfícies sticky do Cockpit tornam-se opacas e contíguas, removendo translucidez/backdrop que misturava o conteúdo rolado com título e abas.
- `3.2` — 2026-08-28 — Cockpit ganha layout executivo: alertas prioritários antes dos KPIs compactos, título e controles sticky, núcleo de Saldos/Portfólio sempre visível e quatro seções secundárias recolhíveis com estado persistido em `localStorage`.
- `3.1` — 2026-08-28 — Fluidez generalizada: novo `tab-utils.js` padroniza transição e teclado em Cockpit, Portfólio, Relatórios, Consultor e Preferências; carregamentos de Portfólio, Tags, Tendências e Saúde passam a anunciar estado ocupado, com proteção adicional contra resposta obsoleta em Tags.
- `3.0` — 2026-08-28 — Primeira etapa de fluidez do Cockpit: transição progressiva entre subtabs, estado localizado `aria-busy` durante atualização mensal, preservação visual do painel existente, redução de movimento e navegação completa por teclado.
- `2.9` — 2026-08-28 — Inventário sincronizado com `instructions-content.js`, `instructions-view.js` e `simulations-view.js`; adicionados testes automatizados dos imports ES, do inventário documental e da ausência de artefatos de build.
- `2.8` — 2026-08-13 — Modo ícones da sidebar compactado para caber sem rolagem em telas comuns: botões com `min-height` 36px (antes 42px), gaps reduzidos de 8px para 4px e marca com menos respiro; **Sair** e todos os itens ficam visíveis sem rolar a página.
- `2.7` — 2026-08-13 — Navegação lateral com grupos colapsáveis: **Cadastro**, **Lançamentos**, **Gestão** e **Usuário** colapsam/expandem pelo rótulo (seta + `aria-expanded`), com preferência local persistida e abertura automática do grupo da view ativa; **Cockpit** passa a ser item de primeiro nível e o grupo **Visão geral** é removido.
- `2.6` — 2026-08-09 — Ajustes finais de performance frontend: widget externo BMC passa a carregar com `async/defer`, transição de `grid-template-columns` removida do dashboard e logs de debug removidos de renderizações frequentes.
- `2.5` — 2026-08-09 — Portfólio passa a renderizar abas sob demanda: Posição no carregamento inicial, Análise/Histórico no primeiro acesso e rentabilidade detalhada apenas ao abrir o drawer; agrupamento/colapso atualiza só a lista de posições.
- `2.4` — 2026-08-09 — Navegação para Cockpit passa a reaproveitar o snapshot em memória do mês já carregado, evitando a segunda busca pesada no load inicial e re-buscas completas ao clicar novamente no módulo.
- `2.3` — 2026-08-07 — Aba **Saúde Financeira** do Cockpit extraída para view dedicada `financial-health-view.js` (fábrica `registerFinancialHealthView`), desacoplando o estado de tela do `cockpit-view.js`.
- `2.2` — 2026-08-02 — Registrado `privacy-utils.js` como utilitário local para Modo Privacidade via `data-privacy`, sem backend ou build step.
- `2.1` — 2026-08-02 — Troca de módulos do dashboard passa a usar View Transitions API como melhoria progressiva, com fallback e respeito a redução de movimento.
- `2.0` — 2026-08-02 — Navegação lateral passa a documentar rótulos desambiguados para Cadastro e Lançamentos, com títulos de página alinhados.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados; referência cruzada com ADR.
- `1.1` — 2026-06-30 — Responsabilidade de busca/filtro da fatura registrada em `cards-view.js`; consolidações do Portfólio documentadas em `portfolio-view.js`.
- `1.2` — 2026-06-30 — Regra de tokenização de cores e gráficos registrada para preparação do modo escuro.
- `1.3` — 2026-06-30 — Infraestrutura local de tema registrada em `theme-utils.js`.
- `1.4` — 2026-06-30 — Regra de evolução do modo escuro por overrides centralizados de tokens registrada.
- `1.5` — 2026-07-01 — Controle claro/escuro em Preferências registrado em `user-admin-view.js`.
- `1.6` — 2026-07-01 — Critérios de aceite e cobertura de QA do tema claro/escuro registrados.
- `1.7` — 2026-07-09 — `operation-history-view.js` registrado como view funcional do Histórico de Operações.
- `1.8` — 2026-07-20 — `decision-modal.js` registrado como helper reutilizável para decisões e formulários curtos.
- `1.9` — 2026-07-24 — Tela estática Sobre documentada como view simples roteada por `app.js`.

## Relacionados

- [[adr/0002-modularizacao-frontend]]
- [[arquitetura]]
