---
tipo: spec
area: landing-page
status: rascunho
versao: 0.1
atualizado: 2026-08-02
relacionados:
  - "[[sobre-app]]"
  - "[[../design/design-system|Design System]]"
tags: [spec, "area/landing-page", "status/rascunho"]
aliases: ["Landing Page do Produto", "Site Institucional de Apresentação"]
---

# Landing Page do Produto e Showcase Visual

> [!info] Status
> **rascunho** · área: `landing-page` · atualizado em 2026-08-02 · relacionados: [[sobre-app]], [[../design/design-system|Design System]]

### Problema

Novos usuários, potenciais interessados ou pessoas navegando pelo repositório não possuem uma página institucional de apresentação do **Sistema Financeiro** que demonstre visualmente suas telas, funcionalidades principais, proposta de privacidade local e facilidades antes de baixar ou rodar a aplicação.

### Usuário

Visitante ou usuário interessado que busca entender a proposta de valor, visualizar telas reais da aplicação, verificar recursos de privacidade/saúde financeira e aprender como executar o aplicativo.

### Jornada

1. O visitante acessa a Landing Page (seja online via hospedagem estática ou localmente na pasta `landing-page/`).
2. Na seção principal (Hero), visualiza a proposta de valor do aplicativo acompanhada por um mockup em destaque do Cockpit financeiro.
3. Navega pelas seções de destaques:
   - **Privacidade Local Primeiro**: com prévia visual do Modo Privacidade (Glass Blur).
   - **Saúde Financeira**: demonstrando o Gauge Chart de 0 a 1000 pts e os pilares expansíveis.
   - **Investimentos & Renda Fixa**: exibindo a gestão de ativos (Pré, Pós e Híbridos).
   - **Gestão de Contas, Cartões & Extratos**: apresentando controle de faturas e conciliação.
4. Na seção de captura/download (Call to Action - CTA), o visitante encontra links diretos para a documentação de uso ou comandos de execução local.

### Dados

- `landing-page/assets/cockpit-preview.png`: captura de tela demonstrativa do Cockpit financeiro.
- `landing-page/assets/saude-financeira-preview.png`: captura de tela do painel de Saúde Financeira com o velocímetro de score.
- `landing-page/assets/portfolio-preview.png`: captura de tela da visão de investimentos e renda fixa.
- `landing-page/assets/privacy-mode-preview.png`: captura demonstrativa do efeito de mascaramento/desfoque do Modo Privacidade.
- `landing-page/assets/cards-preview.png`: captura de tela da gestão de cartões e faturas.

### Regras

- A Landing Page é um site/apresentação institucional isolado no diretório `landing-page/`, utilizando componentes compatíveis com os templates do **v0.app** (React / Next.js / Tailwind / HTML5 estático).
- A Landing Page deve ser totalmente responsiva, funcionando em dispositivos mobile, tablets e desktops.
- A página não exige autenticação nem conexão com o banco de dados do aplicativo.
- Todas as imagens demonstrativas em `landing-page/assets/` devem utilizar dados fictícios / simulação de homologação para garantir total sigilo dos dados do usuário desenvolvedor.
- As cores visuais da landing page devem seguir o guia de identidade do aplicativo (`--bg`, `--panel`, `--accent`, etc.) conforme definido no Design System.

### API e dados

- Nenhuma rota backend nova no aplicativo principal.
- Nenhuma alteração em esquemas do SQLite ou modelos do Python backend (`financeiro/`).
- Conteúdo 100% estático armazenado em `landing-page/`.

### Critérios de aceite

- Dado um visitante acessando a Landing Page, quando navega pela seção Hero, então encontra uma apresentação clara do produto com mockup responsivo do Cockpit.
- Dado um visitante interessado na privacidade dos dados, quando navega até a seção de Privacidade, então visualiza uma demonstração interativa ou imagem explicativa do Modo Privacidade (Glass Blur).
- Dado um visitante analisando os recursos de saúde financeira, quando chega na seção de Diagnóstico, então encontra a explicação da pontuação de 0 a 1000 e dos 5 pilares estratégicos.
- Dado um visitante acessando via smartphone ou dispositivo com tela reduzida, quando rola a página, então todo o layout se adapta de forma fluida sem rolagem horizontal indesejada.
- Dado a pasta `landing-page/`, quando um desenvolvedor clica nos arquivos estáticos ou roda o build, então os recursos são carregados sem dependência da API backend em execução.

### Pendências

- [ ] Definir a lista final de componentes a serem exportados do v0.app (`https://v0.app/templates/landing-pages`).
- [ ] Gerar e salvar as imagens de captura de tela em `landing-page/assets/` utilizando a base de dados de homologação.
- [ ] Definir se a landing page será hospedada via Vercel/GitHub Pages ou servida opcionalmente no `app.py`.

### Fora de escopo

- Integração com gateways de pagamento, cadastro de usuários ou coleta de e-mails de marketing na landing page.
- Alteração do backend Python em `app.py` no primeiro MVP da landing page.

### Plano de implementação

- [ ] Passo 1 — Criar o diretório `landing-page/` e a pasta `landing-page/assets/` com as capturas de tela fictícias dos módulos. Fecha: critérios 1 e 5.
- [ ] Passo 2 — Exportar/adaptar a estrutura de componentes gerados no v0.app para a pasta `landing-page/`. Fecha: critérios 1, 2, 3 e 4.
- [ ] Passo 3 — Validar a acessibilidade, responsividade mobile e contraste visual da landing page. Fecha: critérios 4 e 5.

### Changelog

- `0.1` — 2026-08-02 — Spec inicial em rascunho para a criação da Landing Page do produto com showcase de telas e integração a modelos do v0.app.

### Relacionados

- [[sobre-app]]
- [[../design/design-system|Design System]]
