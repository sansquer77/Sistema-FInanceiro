---
tipo: spec
area: landing-page
status: implementado
versao: 1.8
atualizado: 2026-08-04
relacionados:
  - "[[sobre-app]]"
  - "[[../design/design-system|Design System]]"
  - "[[../adr/0007-landing-page-institucional-isolada|ADR-0007]]"
tags: [spec, "area/landing-page", "status/implementado"]
aliases: ["Landing Page do Produto", "Site Institucional de Apresentação"]
---

# Landing Page do Produto e Showcase Visual

> [!info] Status
> **implementado** · área: `landing-page` · atualizado em 2026-08-04 · relacionados: [[sobre-app]], [[../design/design-system|Design System]], [[../adr/0007-landing-page-institucional-isolada|ADR-0007]]

### Problema

Novos usuários, potenciais interessados ou pessoas navegando pelo repositório não possuem uma página institucional de apresentação do **Sistema Financeiro** que demonstre visualmente suas telas, funcionalidades principais, proposta de privacidade local e facilidades antes de baixar ou rodar a aplicação.

### Usuário

Visitante ou usuário interessado que busca entender a proposta de valor, visualizar telas reais da aplicação, verificar recursos de privacidade/saúde financeira e aprender como executar o aplicativo.

### Jornada

1. O visitante acessa a Landing Page online ou localmente a partir do repositório próprio `sistemafinanceiropage`.
2. Na seção principal (Hero), visualiza a proposta de valor do aplicativo acompanhada por um mockup em destaque do Cockpit financeiro.
3. Navega por uma seção visual em formato de **árvore do sistema**, inspirada no modelo “COMPUTE - The Platform to Build & Ship AI Agents” do v0.app, onde cada ramo representa uma capacidade central do app.
4. Navega pelas seções de destaques:
   - **Privacidade Local Primeiro**: com prévia visual do Modo Privacidade (Glass Blur).
   - **Uso em Família / Rede Local**: explicando que o app pode rodar em um computador da casa e ser acessado por dispositivos autorizados na mesma rede local.
   - **Saúde Financeira**: demonstrando o Gauge Chart de 0 a 1000 pts e os pilares expansíveis.
   - **Investimentos & Renda Fixa**: exibindo a gestão de ativos (Pré, Pós e Híbridos).
   - **Gestão de Contas, Cartões & Extratos**: apresentando controle de faturas e conciliação.
5. Em cada área visual, encontra exemplos baseados nas telas reais do aplicativo, sempre com dados fictícios e diferentes da base de homologação.
6. Na seção de downloads, o visitante encontra os pacotes oficiais gratuitos gerados por GitHub Releases a partir do repositório do app principal.
7. O visitante encontra um disclaimer claro de que o Sistema Financeiro é um projeto pessoal disponibilizado gratuitamente, sem suporte formal.
8. O visitante usa o e-mail apenas como canal para sugestões, dúvidas gerais ou relato de problemas, sem expectativa de SLA ou atendimento garantido.
9. O visitante encontra a licença Apache 2.0 e, se desejar, um link separado para contribuição voluntária.

### Dados

- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/cockpit-preview.png`: captura de tela demonstrativa do Cockpit financeiro.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/trends-preview.png`: captura de tela demonstrativa da aba Tendências do Cockpit.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/saude-financeira-preview.png`: captura de tela do painel de Saúde Financeira com o velocímetro de score.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/portfolio-preview.png`: captura de tela da visão de investimentos e renda fixa.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/privacy-mode-preview.png`: captura demonstrativa do efeito de mascaramento/desfoque do Modo Privacidade.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/cards-preview.png`: captura de tela da gestão de cartões e faturas.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/assets/demo-data/`: dados demonstrativos ou fixtures visuais usados para gerar capturas fictícias, sem relação com a base de homologação, caso esse diretório seja usado.

### Regras

- A Landing Page é um site/apresentação institucional isolado em repositório próprio (`/Users/sansquer/Documents/GitHub/sistemafinanceiropage`), inspirado em templates do **v0.app**, especialmente no modelo visual “COMPUTE - The Platform to Build & Ship AI Agents”.
- A Landing Page pode usar stack própria de site institucional, incluindo Next.js, React, Tailwind e dependências npm, desde que permaneça confinada ao repositório `sistemafinanceiropage` e seja tratada como projeto independente do app principal.
- As restrições de frontend sem build step de [[../adr/0002-modularizacao-frontend|ADR-0002]] continuam válidas para o app principal (`web/`, `app.py`, `financeiro/`) e não devem ser relaxadas por causa da landing page.
- O deploy recomendado da landing page é via Vercel apontando para o repositório `sistemafinanceiropage`.
- O código exportado do v0.app deve ser descompactado diretamente na raiz de `sistemafinanceiropage`, evitando criar um nível intermediário como `sistemafinanceiropage/compute-the-platform.../`.
- Ao descompactar o template em `sistemafinanceiropage`, os assets demonstrativos já gerados devem ser preservados ou copiados para `public/images/` conforme a estrutura final do projeto Next.
- A Landing Page deve ser totalmente responsiva, funcionando em dispositivos mobile, tablets e desktops.
- A página não exige autenticação nem conexão com o banco de dados do aplicativo.
- Todas as imagens demonstrativas em `sistemafinanceiropage/public/images/` devem utilizar dados fictícios, com nomes, valores, contas, cartões, investimentos, saldos, limites e e-mails diferentes dos dados reais e da base de homologação.
- A seção de árvore deve preservar a metáfora visual do template original, com uma imagem de árvore em destaque no lado direito em telas amplas, conectando crescimento financeiro, raízes e evolução dos módulos do app.
- A árvore visual pode ter animação discreta de entrada/flutuação para reforçar sensação premium, mas deve evitar movimento excessivo, não competir com o texto e respeitar `prefers-reduced-motion`.
- A copy pública da landing não deve mencionar internamente “homologação”, “massa fictícia”, “dados reais” ou termos semelhantes; essas garantias permanecem como regra de produção/documentação, não como texto de marketing.
- A landing deve conter seção profissional sobre uso em rede local para famílias, deixando claro que o app pode ser instalado em um computador central e acessado por dispositivos autorizados na mesma rede doméstica/confiável, sem prometer serviço em nuvem ou acesso remoto público.
- A árvore visual deve apresentar o app como um sistema integrado, com tronco central representando o **Sistema Financeiro** e ramos para Contas, Cartões, Cockpit, Saúde Financeira, Tendências, Portfólio, Relatórios, Simulação, Privacidade e Preferências.
- A seção de exemplos reais deve usar capturas ou mockups fiéis às páginas do app, mas sempre renderizados com massa de dados demonstrativa.
- As capturas fiéis devem ser geradas preferencialmente a partir de uma instância local isolada do app com `SISTEMA_FINANCEIRO_DATA_DIR` temporário e usuário demonstrativo, sem reutilizar `data/` de desenvolvimento ou homologação.
- A seção “Como começar” deve orientar o visitante por módulos em linguagem didática, explicando a lógica de uso do app sem substituir a documentação completa.
- A orientação de Portfólio deve deixar claro que o ativo representa a posição cadastrada, enquanto aportes e resgates posteriores são registrados pelos lançamentos da conta para preservar histórico, saldo e relatórios.
- A seção de downloads deve indicar que o app é gratuito e apontar para pacotes oficiais publicados em GitHub Releases do repositório do app principal.
- A seção de downloads deve buscar a release mais recente do repositório `sansquer77/Sistema-FInanceiro` em Server Component do Next.js com `fetch(..., { next: { revalidate: 3600 } })`, sem token, backend próprio ou chamada por visitante no client.
- A seção de downloads deve exibir “Versão mais recente: <tag>” e botões “Baixar para Windows”, “Baixar para macOS” e “Baixar para Linux”, mapeando assets da release por nome/plataforma.
- Cada botão de download deve exibir um símbolo visual do sistema operacional correspondente, preservando leitura profissional e acessibilidade textual.
- A seção de downloads não deve exibir link textual separado para notas da versão; a navegação principal deve permanecer concentrada nos botões de download por plataforma.
- A landing deve expor um endpoint público `/api/latest-version` que retorna a versão mais recente e os links de download/release em JSON, para que o app principal possa detectar atualizações sem fazer scraping de HTML.
- O endpoint `/api/latest-version` deve reutilizar a mesma função `getLatestRelease()` usada na seção de downloads, com cache server-side de 1 hora.
- A landing deve conter disclaimer informando que o Sistema Financeiro é um projeto pessoal open source disponibilizado gratuitamente, sem suporte formal, garantia de atendimento ou obrigação de manutenção.
- O contato por e-mail deve ser apresentado como canal para sugestões, dúvidas gerais ou relatos de problemas, não como suporte contratado.
- A landing deve informar a licença Apache License 2.0 na área de contato/download.
- A landing pode exibir link de contribuição voluntária em `https://buymeacoffee.com/sansquerh` com o texto “Me pague um café se gostou do app”, deixando claro que a contribuição é opcional e não condiciona o uso do app.
- As cores visuais da landing page devem seguir o guia de identidade do aplicativo (`--bg`, `--panel`, `--accent`, etc.) conforme definido no Design System.
- A landing page não deve expor prints, nomes, e-mails, saldos, ativos, contas ou cartões reais do desenvolvedor ou de qualquer base de homologação.
- O diretório legado `landing-page/` foi removido deste repositório do app principal; qualquer recriação desse diretório deve ser tratada como regressão, salvo pedido explícito de migração/consulta histórica.

### API e dados

- Nenhuma rota backend nova no aplicativo principal.
- Nenhuma alteração em esquemas do SQLite ou modelos do Python backend (`financeiro/`).
- A landing page expõe a rota serverless `GET /api/latest-version` no Next.js, retornando JSON com `version`, `download_url` e `release_url` da release mais recente do GitHub, com cache de 1 hora.
- O endpoint `/api/latest-version` reutiliza a lógica `getLatestRelease()` já existente em `app/page.tsx`.
- Conteúdo institucional armazenado no repositório `/Users/sansquer/Documents/GitHub/sistemafinanceiropage`, com dependências, scripts e configuração próprios quando a landing usar Next.js/React.
- A landing page não deve importar módulos de `web/`, `financeiro/` ou `app.py`; a comunicação com o app principal no MVP é apenas visual/institucional.
- O CTA de contato pode usar link `mailto:` com assunto pré-preenchido para sugestões ou relato de problemas, sem persistência local.

### Critérios de aceite

- Dado um visitante acessando a Landing Page, quando navega pela seção Hero, então encontra uma apresentação clara do produto com mockup responsivo do Cockpit.
- Dado um visitante visualizando a narrativa principal, quando chega na seção de árvore, então entende as áreas do sistema por ramos visuais conectados ao produto central.
- Dado a seção de árvore do sistema, quando ela é exibida em tela estreita, então os ramos se reorganizam em cartões/linha vertical sem perda de leitura ou rolagem horizontal.
- Dado a seção de árvore em telas amplas, quando ela é exibida, então a imagem fica alinhada visualmente ao bloco textual, com animação sutil e sem prejudicar leitura ou acessibilidade.
- Dado um visitante interessado na privacidade dos dados, quando navega até a seção de Privacidade, então visualiza uma demonstração interativa ou imagem explicativa do Modo Privacidade (Glass Blur).
- Dado um visitante interessado no uso familiar, quando navega até a seção de rede local, então entende que o app pode ser instalado em um computador da casa e acessado por dispositivos autorizados na mesma rede local confiável.
- Dado um visitante analisando os recursos de saúde financeira, quando chega na seção de Diagnóstico, então encontra a explicação da pontuação de 0 a 1000 e dos 5 pilares estratégicos.
- Dado um visitante analisando exemplos do app, quando visualiza capturas ou mockups, então todos os dados exibidos são fictícios e não correspondem à homologação.
- Dado um visitante lendo a seção “Como começar”, quando seleciona “Portfólio e ativos”, então entende a diferença entre cadastrar a posição do ativo e registrar aportes/resgates pelos lançamentos da conta.
- Dado um visitante interessado em baixar o app, quando chega à seção de downloads, então encontra links para os pacotes gratuitos oficiais publicados em GitHub Releases.
- Dado a API pública do GitHub disponível, quando a landing é renderizada, então a seção de downloads exibe a tag da release mais recente e os links dos assets Windows/macOS/Linux encontrados.
- Dado que o app principal consulta `/api/latest-version`, quando a landing responde, então retorna JSON com `version`, `download_url` e `release_url` da release mais recente.
- Dado que a API do GitHub está indisponível, quando o endpoint `/api/latest-version` é chamado, então retorna JSON com valores nulos/fallback sem expor stack trace ou erro interno.
- Dado a API pública do GitHub indisponível ou sem asset esperado, quando a landing é renderizada, então a seção de downloads continua acessível e aponta para a página geral de releases como fallback.
- Dado um visitante lendo a seção de contato, quando avalia o canal de e-mail, então entende que ele serve para sugestões e relatos, sem suporte formal ou SLA.
- Dado um visitante lendo a seção de contato, quando visualiza a contribuição voluntária, então entende que ela é opcional e não condiciona o uso gratuito do app.
- Dado um visitante acessando via smartphone ou dispositivo com tela reduzida, quando rola a página, então todo o layout se adapta de forma fluida sem rolagem horizontal indesejada.
- Dado o repositório `sistemafinanceiropage`, quando um desenvolvedor roda o build do projeto ou a Vercel publica esse repositório, então os recursos são carregados sem dependência da API backend em execução.
- Dado o app principal sendo distribuído para usuários finais, quando o pacote é gerado, então o repositório/projeto da landing page não é incluído no pacote.

### Pendências

- [x] Definir quais elementos visuais do template “COMPUTE - The Platform to Build & Ship AI Agents” serão adaptados, especialmente a árvore/narrativa modular.
- [x] Definir texto final, política gratuita sem suporte formal e canal de contato para sugestões.
- [x] Gerar e salvar as imagens de captura de tela em `sistemafinanceiropage/public/images/` utilizando massa fictícia independente da base de homologação.
- [x] Definir se a landing page será hospedada via Vercel/GitHub Pages ou servida opcionalmente no `app.py`: decisão atual é Vercel com repositório próprio `sistemafinanceiropage`, sem servir pelo `app.py`.

### Fora de escopo

- Integração com gateways de pagamento, validação automática de PIX, cadastro de usuários ou coleta de e-mails de marketing na landing page.
- Armazenar comprovantes, pedidos, dados pessoais ou qualquer informação de pagamento.
- Alteração do backend Python em `app.py` no primeiro MVP da landing page.
- Uso de dados reais ou capturas da base de homologação sem anonimização completa.
- Inclusão da landing page neste repositório principal ou nos pacotes instaláveis macOS/Windows/Linux do Sistema Financeiro.
- Uso da stack Next/React/Tailwind da landing como precedente para alterar a stack do app principal.

### Plano de implementação

- [x] Passo 1 — Definir a narrativa visual da árvore, copy principal e CTA de download/contato, sem alterar código do app principal. Fecha: critérios 1, 2 e 6.
- [x] Passo 2 — Criar o repositório `sistemafinanceiropage` com `public/images/` e capturas/mockups fictícios dos módulos. Fecha: critérios 4, 5 e 8.
- [x] Passo 3 — Descompactar/adaptar o projeto exportado do v0.app diretamente em `sistemafinanceiropage`, preservando os assets demonstrativos e configurando a Vercel para usar esse repositório. Fecha: critérios 1, 2, 3, 4, 6, 7, 9 e 10.
- [ ] Passo 4 — Validar acessibilidade, responsividade mobile, contraste visual e ausência de dados reais nas imagens. Fecha: critérios 3, 7, 8 e 9.
- [ ] Passo 5 — Criar endpoint `GET /api/latest-version` em `sistemafinanceiropage/app/api/latest-version/route.ts` reutilizando `getLatestRelease()` e com cache de 1 hora. Fecha: critérios 13 e 14.

### Changelog

- `1.8` — 2026-08-04 — Spec marcada como `implementado` na documentação do repositório principal; a landing page vive em `sistemafinanceiropage` e este repositório mantém apenas a especificação/decisão do produto.
- `1.7` — 2026-08-04 — Adicionado endpoint público `/api/latest-version` para que o app principal detecte novas versões sem scraping de HTML.
- `1.6` — 2026-08-04 — Incluída orientação didática da seção “Como começar”, com destaque para o fluxo correto de cadastro de ativos, aportes e resgates.
- `1.5` — 2026-08-04 — Removido o link textual separado “Ver notas da versão no GitHub” da seção de downloads, mantendo foco nos botões por plataforma.
- `1.4` — 2026-08-04 — Incluído Linux na seção de downloads e definidos símbolos visuais de sistema operacional nos botões Windows, macOS e Linux.
- `1.3` — 2026-08-04 — Definida a seção de downloads com busca server-side da última GitHub Release, cache de 1h e botões para Windows/macOS com fallback para a página de releases.
- `1.2` — 2026-08-04 — Incluída na landing a exibição da licença Apache 2.0 e link de contribuição voluntária “Me pague um café se gostou do app”, sem condicionar o uso gratuito.
- `1.1` — 2026-08-04 — Atualizada a proposta pública da landing para download gratuito via GitHub Releases, removendo PIX/cobrança e definindo contato como canal de sugestões sem suporte formal.
- `1.0` — 2026-08-03 — Registrado o comportamento visual da árvore com alinhamento ao texto, animação sutil e respeito a `prefers-reduced-motion`.
- `0.9` — 2026-08-03 — Incluída na landing a seção pública “Uso em família” para explicar o uso multiusuário em rede local confiável, mantendo tom profissional e sem prometer serviço em nuvem.
- `0.8` — 2026-08-03 — Registrado que a landing deve manter a árvore visual do template como metáfora de evolução financeira e remover do texto público menções internas a homologação/massa fictícia.
- `0.7` — 2026-08-03 — Registrado que o diretório legado `landing-page/` foi removido do repositório do app principal; o repositório `sistemafinanceiropage` permanece como fonte canônica da landing.
- `0.6` — 2026-08-03 — Alterada a decisão de projeto: a Landing Page passa a viver em repositório próprio (`/Users/sansquer/Documents/GitHub/sistemafinanceiropage`), mantendo este repositório apenas como fonte de documentação/decisão do produto.
- `0.5` — 2026-08-03 — Template exportado do v0.app adaptado para a apresentação do Sistema Financeiro, com copy institucional, árvore modular, screenshots em `landing-page/public/images/` e CTA manual por PIX/e-mail.
- `0.4` — 2026-08-02 — Definido que a landing page é subprojeto institucional independente, podendo usar Next.js/React/Tailwind dentro de `landing-page/`, com deploy Vercel e exclusão dos pacotes do app principal.
- `0.3` — 2026-08-02 — Registrado que os previews da landing devem ser screenshots reais do app em instância demo isolada, incluindo a aba Tendências, sempre com massa fictícia independente de desenvolvimento/homologação.
- `0.2` — 2026-08-02 — Incluída decisão de usar uma narrativa visual em árvore inspirada no template COMPUTE do v0.app, exemplos reais com dados fictícios e CTA manual por PIX para solicitação de cópia.
- `0.1` — 2026-08-02 — Spec inicial em rascunho para a criação da Landing Page do produto com showcase de telas e integração a modelos do v0.app.

### Relacionados

- [[sobre-app]]
- [[../design/design-system|Design System]]
- [[../adr/0007-landing-page-institucional-isolada|ADR-0007]]
