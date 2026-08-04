---
tipo: spec
area: usuario
status: rascunho
versao: 0.2
atualizado: 2026-08-04
relacionados:
  - "[[sobre-app]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[investimentos-portfolio]]"
  - "[[score-saude-financeira]]"
tags: [spec, "area/usuario", "status/rascunho"]
aliases: ["Instruções do App", "Central de Ajuda Local"]
---

# Instruções do App

> [!info] Status
> **rascunho** · área: `usuario` · atualizado em 2026-08-04 · relacionados: [[sobre-app]], [[lancamentos]], [[cartoes]], [[investimentos-portfolio]], [[score-saude-financeira]]

### Problema

O Sistema Financeiro deixou de ser usado apenas como projeto pessoal e já atende um grupo maior de usuários. Com isso, fluxos mais ricos — como lançamentos, faturas, portfólio, renda fixa, conciliação e saúde financeira — podem gerar dúvidas operacionais recorrentes. O app precisa de uma área de instruções acessível dentro da própria interface, sem depender de explicações externas ou suporte individual.

### Usuário

Usuário final que usa o app no dia a dia, sozinho ou em ambiente familiar, e precisa entender rapidamente como executar tarefas comuns sem conhecer a documentação técnica do projeto.

Também atende usuários novos que acabaram de instalar o app e precisam de uma trilha inicial para configurar contas, cartões, categorias e primeiros lançamentos.

### Jornada

1. O usuário cria uma conta um email válido
2. O usuário acessa o menu lateral em **Usuário**.
3. O usuário abre o novo módulo **Instruções**.
4. O usuário visualiza uma página de ajuda prática, organizada por temas e módulos.
5. O usuário pesquisa ou seleciona um tópico, como “Como cadastrar CDB?”, “Como pagar fatura?” ou “O que é conciliado?”.
6. O usuário expande um card/accordion e lê passos curtos com exemplos.
7. O usuário volta ao módulo funcional correspondente com clareza sobre a ação esperada.

### Dados

- `id`: identificador estável do tópico de instrução.
- `grupo`: seção principal do conteúdo, como `primeiros-passos`, `lancamentos-contas`, `cartoes`, `portfolio`, `cockpit`, `privacidade-rede`.
- `titulo`: título curto exibido no card ou accordion.
- `resumo`: descrição breve do objetivo do tópico.
- `conteudo`: passos e explicações em linguagem simples.
- `termos_busca`: palavras-chave associadas ao tópico para busca local.
- `modulo_relacionado`: módulo do app ao qual a instrução se refere, quando aplicável.
- `rota_modulo`: identificador interno de navegação para o módulo relacionado, quando houver link “Ir para o módulo”.
- `topico_contextual`: identificador do tópico que pode ser aberto a partir de um botão contextual `?` em telas funcionais.

### Regras

- O módulo **Instruções** deve aparecer no menu lateral dentro do grupo **Usuário**, entre **Preferências** e **Sobre**, salvo ajuste posterior de UX.
- O módulo **Sobre** permanece institucional; o módulo **Instruções** deve ser operacional e didático.
- O conteúdo deve ser estático, versionado no frontend e disponível offline.
- O conteúdo deve usar linguagem clara, direta e orientada a tarefas, evitando termos técnicos quando não forem necessários.
- O conteúdo deve conter exemplos práticos, mas sem usar dados reais do desenvolvedor, homologação ou usuários.
- A página deve permitir busca textual local por título, resumo, conteúdo e termos de busca.
- A organização visual deve usar cards por tema e accordions para leitura progressiva.
- O módulo não deve depender de IA, API externa, servidor adicional ou conexão com internet.
- O módulo não deve alterar dados financeiros, criar lançamentos ou executar ações; ele apenas orienta o usuário.
- Quando houver botão ou link contextual para um módulo funcional, a navegação deve ser interna e não deve alterar filtros ou dados do módulo de destino.
- A primeira versão deve ter links internos “Ir para o módulo” nos tópicos que correspondem a módulos funcionais já implantados.
- Cada tela funcional deve poder exibir futuramente um botão contextual `?` pequeno e discreto ao lado do nome da tela, abrindo diretamente o tópico correspondente em **Instruções**.
- A primeira versão deve cobrir todos os módulos operacionais atualmente implantados: Cockpit, Minhas Contas, Meus Cartões, Extrato de Contas, Fatura de Cartões, Portfólio, Limites, Simulação, Relatórios, Categorias, Importação, Histórico, Preferências, Privacidade e Instruções.
- O módulo **Sobre** fica fora do conteúdo operacional, pois já é institucional e não exige instrução de uso.
- O tópico de **Preferências** deve explicar a configuração SMTP usada para recuperação de senha e a configuração opcional de IA usada no módulo de Tendências.
- O tópico de **Portfólio e ativos** deve explicar claramente a diferença entre cadastro da posição e movimentação financeira: o ativo descreve a posição, enquanto aportes e resgates posteriores devem ser registrados pelos lançamentos da conta.
- O tópico de **Portfólio e ativos** deve explicar também sobre a atualização manual dos valores e encerramento de posição (área histórico)
- O tópico de **Renda fixa** deve diferenciar pré-fixada, pós-fixada e híbrida em linguagem prática.
- O tópico de **Cartões** deve explicar diferença entre compra parcelada/recorrente, fatura, pagamento de fatura e antecipação de parcelas. Além disso, deixar claro que uma vez paga a fatura os dados não são alterados.
- O tópico de **Lançamentos de contas** deve explicar diferença entre saldo previsto e saldo conciliado, além de entre compra parcelada/recorrente.
- O módulo deve respeitar o design system existente e a identidade visual do app, sem criar nova linguagem visual.

### API e dados

- Nenhuma rota backend nova prevista no MVP.
- Nenhuma tabela SQLite nova prevista no MVP.
- Nenhuma alteração em `financeiro/` prevista no MVP.
- Conteúdo inicial pode ser definido em módulo JavaScript estático, por exemplo `web/modules/instructions-content.js`, ou estrutura equivalente alinhada ao padrão de modularização frontend.
- A view deve seguir o contrato de fábrica dos módulos em `web/modules/`, por exemplo `createInstructionsView({ state, elements, services, formatters, actions })`.
- `web/app.js` deve orquestrar a navegação para o novo módulo.

### Critérios de aceite

- Dado um usuário autenticado, quando abre o menu **Usuário**, então visualiza o item **Instruções** entre **Preferências** e **Sobre**.
- Dado um usuário autenticado, quando clica em **Instruções**, então a tela principal exibe a central de instruções sem alterar dados financeiros.
- Dado um usuário na tela de instruções, quando não digitou busca, então visualiza grupos de ajuda por tema.
- Dado um usuário na tela de instruções, quando digita um termo de busca existente, então a lista mostra apenas tópicos relacionados ao termo.
- Dado um usuário na tela de instruções, quando digita um termo de busca inexistente, então a página exibe estado vazio amigável.
- Dado um usuário lendo um grupo com muitos tópicos, quando abre um tópico, então apenas o conteúdo detalhado daquele tópico fica visível em formato expansível.
- Dado um usuário lendo o tópico de Portfólio e ativos, quando chega à explicação de aportes e resgates, então entende que movimentações posteriores devem ser feitas pelos lançamentos da conta.
- Dado um usuário lendo o tópico de Renda fixa, quando compara modalidades, então entende a diferença entre pré-fixada, pós-fixada e híbrida.
- Dado um usuário lendo o tópico de Cartões, quando compara fatura e pagamento de fatura, então entende que o pagamento da fatura não substitui o histórico detalhado das compras.
- Dado um usuário lendo o tópico de Lançamentos de contas, quando compara saldos diários, então entende a diferença entre previsto e conciliado.
- Dado um usuário em tela estreita, quando acessa Instruções, então a navegação por grupos, busca e tópicos permanece legível sem rolagem horizontal.
- Dado um usuário sem conexão com internet, quando acessa Instruções, então o conteúdo continua disponível.
- Dado um visitante sem sessão válida, quando tenta acessar diretamente o módulo Instruções pelo app, então o comportamento segue a proteção normal de autenticação do aplicativo.
- Dado um usuário lendo um tópico de módulo operacional, quando clica em “Ir para o módulo”, então o app navega internamente para o módulo relacionado sem executar alterações de dados.
- Dado um usuário em uma tela funcional com tópico de ajuda associado, quando clica no botão contextual `?` ao lado do nome da tela, então o app abre o tópico correspondente em **Instruções**.
- Dado um usuário lendo o tópico de Preferências, quando consulta SMTP e IA, então entende que SMTP apoia recuperação de senha e IA é opcional para Tendências.

### Pendências

> [!question] Pendências
> Toda pergunta em aberto, decisão não tomada ou premissa não validada entra aqui. Nenhum agente de IA deve implementar uma seção que dependa de um item desta lista sem confirmação humana antes. Remova o item somente quando a resposta já estiver refletida no restante da spec.

Nenhuma pendência conhecida.

### Fora de escopo

- Chatbot, assistente por IA ou geração dinâmica de ajuda.
- Tutorial interativo que executa ações no app.
- Vídeos, imagens externas ou documentação hospedada fora do app.
- Sistema de feedback, avaliação de artigos ou telemetria de leitura.
- Tradução multilíngue.
- Alterações em regras financeiras, cálculos, saldos, faturas ou portfólio.

### Plano de implementação

- [ ] Passo 1 — Refinar a lista final de tópicos, grupos, termos de busca e textos didáticos na própria spec. Fecha: critérios 3, 7, 8, 9, 10 e 16.
- [ ] Passo 2 — Criar o conteúdo estático versionado no frontend, sem dependência de backend ou internet. Fecha: critérios 11, 12 e 16.
- [ ] Passo 3 — Criar a view `Instruções` em `web/modules/` seguindo o contrato modular do frontend. Fecha: critérios 2, 3, 4, 5, 6 e 14.
- [ ] Passo 4 — Adicionar o item **Instruções** no menu **Usuário** e conectar a navegação em `web/app.js`. Fecha: critérios 1, 13 e 14.
- [ ] Passo 5 — Ajustar responsividade, estados vazios, acessibilidade básica, links internos, botões contextuais `?` e aderência ao design system. Fecha: critérios 5, 6, 11, 14 e 15.
- [ ] Passo 6 — Validar manualmente no app local/homologação os fluxos de menu, busca, accordion, sessão e responsividade. Fecha: todos os critérios.

### Changelog

- `0.2` — 2026-08-04 — Fechadas as pendências iniciais: primeira versão terá links internos “Ir para o módulo”, botões contextuais `?` nas telas funcionais e cobertura de todos os módulos operacionais, incluindo Preferências para SMTP e IA.
- `0.1` — 2026-08-04 — Spec inicial em rascunho para o módulo **Instruções** no menu Usuário, com central de ajuda local, busca, grupos por tema e destaque para fluxos de Portfólio, Renda Fixa, Cartões e Lançamentos.

### Relacionados

- [[sobre-app]]
- [[lancamentos]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[score-saude-financeira]]
