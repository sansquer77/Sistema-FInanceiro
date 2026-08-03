---
tipo: spec
area: landing-page
status: em-implementacao
versao: 0.7
atualizado: 2026-08-03
relacionados:
  - "[[sobre-app]]"
  - "[[../design/design-system|Design System]]"
  - "[[../adr/0007-landing-page-institucional-isolada|ADR-0007]]"
tags: [spec, "area/landing-page", "status/em-implementacao"]
aliases: ["Landing Page do Produto", "Site Institucional de Apresentação"]
---

# Landing Page do Produto e Showcase Visual

> [!info] Status
> **em-implementacao** · área: `landing-page` · atualizado em 2026-08-03 · relacionados: [[sobre-app]], [[../design/design-system|Design System]], [[../adr/0007-landing-page-institucional-isolada|ADR-0007]]

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
   - **Saúde Financeira**: demonstrando o Gauge Chart de 0 a 1000 pts e os pilares expansíveis.
   - **Investimentos & Renda Fixa**: exibindo a gestão de ativos (Pré, Pós e Híbridos).
   - **Gestão de Contas, Cartões & Extratos**: apresentando controle de faturas e conciliação.
5. Em cada área visual, encontra exemplos baseados nas telas reais do aplicativo, sempre com dados fictícios e diferentes da base de homologação.
6. Na seção de aquisição (Call to Action - CTA), o visitante visualiza o QR Code PIX, instruções de pagamento e uma forma simples de solicitar uma cópia após o pagamento.
7. O visitante usa o contato informado para enviar comprovante ou solicitar a cópia, sem que a landing page precise validar pagamento automaticamente no MVP.

### Dados

- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/cockpit-preview.png`: captura de tela demonstrativa do Cockpit financeiro.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/trends-preview.png`: captura de tela demonstrativa da aba Tendências do Cockpit.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/saude-financeira-preview.png`: captura de tela do painel de Saúde Financeira com o velocímetro de score.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/portfolio-preview.png`: captura de tela da visão de investimentos e renda fixa.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/privacy-mode-preview.png`: captura demonstrativa do efeito de mascaramento/desfoque do Modo Privacidade.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/cards-preview.png`: captura de tela da gestão de cartões e faturas.
- `/Users/sansquer/Documents/GitHub/sistemafinanceiropage/public/images/pix-qrcode.jpg`: QR Code PIX informado pelo mantenedor para pagamento.
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
- A árvore visual deve apresentar o app como um sistema integrado, com tronco central representando o **Sistema Financeiro** e ramos para Contas, Cartões, Cockpit, Saúde Financeira, Tendências, Portfólio, Relatórios, Simulação, Privacidade e Preferências.
- A seção de exemplos reais deve usar capturas ou mockups fiéis às páginas do app, mas sempre renderizados com massa de dados demonstrativa.
- As capturas fiéis devem ser geradas preferencialmente a partir de uma instância local isolada do app com `SISTEMA_FINANCEIRO_DATA_DIR` temporário e usuário demonstrativo, sem reutilizar `data/` de desenvolvimento ou homologação.
- A seção de aquisição deve conter QR Code PIX fornecido manualmente pelo mantenedor, valor/instruções quando aplicável e texto claro de que a liberação/cópia é tratada manualmente após confirmação do pagamento.
- A solicitação de cópia após PIX deve usar um canal simples e externo ao app no MVP, como `mailto:` para o e-mail de contato, evitando cadastro, checkout, backend de pedidos ou armazenamento de comprovantes.
- As cores visuais da landing page devem seguir o guia de identidade do aplicativo (`--bg`, `--panel`, `--accent`, etc.) conforme definido no Design System.
- A landing page não deve expor prints, nomes, e-mails, saldos, ativos, contas ou cartões reais do desenvolvedor ou de qualquer base de homologação.
- O diretório legado `landing-page/` foi removido deste repositório do app principal; qualquer recriação desse diretório deve ser tratada como regressão, salvo pedido explícito de migração/consulta histórica.

### API e dados

- Nenhuma rota backend nova no aplicativo principal.
- Nenhuma alteração em esquemas do SQLite ou modelos do Python backend (`financeiro/`).
- Conteúdo institucional armazenado no repositório `/Users/sansquer/Documents/GitHub/sistemafinanceiropage`, com dependências, scripts e configuração próprios quando a landing usar Next.js/React.
- A landing page não deve importar módulos de `web/`, `financeiro/` ou `app.py`; a comunicação com o app principal no MVP é apenas visual/institucional.
- O CTA de solicitação de cópia pode usar link `mailto:` com assunto pré-preenchido e instruções para anexar comprovante PIX, sem persistência local.

### Critérios de aceite

- Dado um visitante acessando a Landing Page, quando navega pela seção Hero, então encontra uma apresentação clara do produto com mockup responsivo do Cockpit.
- Dado um visitante visualizando a narrativa principal, quando chega na seção de árvore, então entende as áreas do sistema por ramos visuais conectados ao produto central.
- Dado a seção de árvore do sistema, quando ela é exibida em tela estreita, então os ramos se reorganizam em cartões/linha vertical sem perda de leitura ou rolagem horizontal.
- Dado um visitante interessado na privacidade dos dados, quando navega até a seção de Privacidade, então visualiza uma demonstração interativa ou imagem explicativa do Modo Privacidade (Glass Blur).
- Dado um visitante analisando os recursos de saúde financeira, quando chega na seção de Diagnóstico, então encontra a explicação da pontuação de 0 a 1000 e dos 5 pilares estratégicos.
- Dado um visitante analisando exemplos do app, quando visualiza capturas ou mockups, então todos os dados exibidos são fictícios e não correspondem à homologação.
- Dado um visitante interessado em obter uma cópia, quando chega ao CTA final, então visualiza o QR Code PIX, instruções de pagamento e link de contato para solicitar a cópia após o pagamento.
- Dado um visitante acessando via smartphone ou dispositivo com tela reduzida, quando rola a página, então todo o layout se adapta de forma fluida sem rolagem horizontal indesejada.
- Dado o repositório `sistemafinanceiropage`, quando um desenvolvedor roda o build do projeto ou a Vercel publica esse repositório, então os recursos são carregados sem dependência da API backend em execução.
- Dado o app principal sendo distribuído para usuários finais, quando o pacote é gerado, então o repositório/projeto da landing page não é incluído no pacote.

### Pendências

- [x] Definir quais elementos visuais do template “COMPUTE - The Platform to Build & Ship AI Agents” serão adaptados, especialmente a árvore/narrativa modular.
- [x] Definir texto final, valor, chave/QR Code PIX e canal de contato para solicitação de cópia.
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

- [x] Passo 1 — Definir a narrativa visual da árvore, copy principal e CTA PIX/manual, sem alterar código do app principal. Fecha: critérios 1, 2 e 6.
- [x] Passo 2 — Criar o repositório `sistemafinanceiropage` com `public/images/`, QR Code PIX e capturas/mockups fictícios dos módulos. Fecha: critérios 4, 5 e 8.
- [x] Passo 3 — Descompactar/adaptar o projeto exportado do v0.app diretamente em `sistemafinanceiropage`, preservando os assets demonstrativos e configurando a Vercel para usar esse repositório. Fecha: critérios 1, 2, 3, 4, 6, 7, 9 e 10.
- [ ] Passo 4 — Validar acessibilidade, responsividade mobile, contraste visual e ausência de dados reais nas imagens. Fecha: critérios 3, 7, 8 e 9.

### Changelog

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
