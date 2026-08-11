---
tipo: spec
area: usuario
status: implementado
versao: 1.8
atualizado: 2026-08-10
relacionados:
  - "[[frontend-modularizacao]]"
  - "[[../arquitetura|Arquitetura]]"
  - "[[../distribuição|Distribuicao]]"
  - "[[../requisitos|Requisitos]]"
tags: [spec, "area/usuario"]
aliases: ["Sobre o App", "Sobre"]
---

# Sobre o App

> [!info] Status
> **implementado** · área: `usuario` · atualizado em 2026-07-31 · relacionados: [[frontend-modularizacao]], [[../arquitetura|Arquitetura]], [[../distribuição|Distribuicao]], [[../requisitos|Requisitos]]

## Problema

O usuário precisa encontrar, dentro do próprio app, uma explicação curta sobre o objetivo do Sistema Financeiro, suas funcionalidades principais, dados de desenvolvimento, contato de suporte e condições mínimas de uso local ou em rede.

## Usuário

Usuários finais e mantenedores que usam o Sistema Financeiro localmente, instalam o pacote em outra máquina ou precisam orientar outra pessoa sobre o app.

## Jornada

1. Usuário autenticado abre o grupo **Usuário** no menu lateral.
2. Acessa o item **Sobre**.
3. Visualiza uma tela informativa com descrição do app, funcionalidades, dados de desenvolvimento e infraestrutura mínima.
4. Usa o contato informado para dúvidas, sugestões ou bugs.

## Dados

- `descricao`: texto estático e sucinto sobre o objetivo do app, sem repetir o título do módulo.
- `funcionalidades`: lista estática de capacidades principais.
- `desenvolvedor`: nome do responsável pelo desenvolvimento.
- `versao_atual`: versão atual do sistema exibida para identificação do que está rodando, lida dos metadados centralizados do app.
- `tecnologias`: lista estática de tecnologias usadas.
- `contato`: e-mail para dúvidas, sugestões e bugs.
- `infraestrutura_minima`: requisitos mínimos para uso local e em rede.

## Regras

- A tela **Sobre** deve ficar no grupo **Usuário** do menu lateral.
- A tela deve ser somente leitura e não deve criar tabelas, arquivos de dados ou chamadas externas.
- O conteúdo deve mencionar o objetivo principal: controle financeiro local, privado e simples.
- As funcionalidades devem cobrir contas, cartões, lançamentos, categorias/tags, limites, relatórios, cockpit, planejamento, saúde financeira, portfólio (renda fixa, ações, fundos, cripto, poupança e previdência), importação, histórico/auditoria, instruções e preferências/segurança.
- Os dados de desenvolvimento devem informar:
  - Desenvolvedor: Sansquer.
  - Versão atual do sistema, a partir do endpoint de metadados do app.
  - Tecnologias utilizadas no app.
  - Contato: `darksansquer@gmail.com`.
- A versão de produto deve partir de `1.0.50`, ficar centralizada em `financeiro/app_metadata.py`, ser exposta por `/api/app-info` e seguir versionamento semântico:
  - `PATCH` (`3.0.5` → `3.0.6`): correção compatível, segurança, desempenho ou ajuste operacional sem nova capacidade relevante para o usuário.
  - `MINOR` (`3.0.5` → `3.1.0`): nova funcionalidade ou capacidade relevante, compatível com os fluxos e dados existentes.
  - `MAJOR` (`3.0.5` → `4.0.0`): mudança incompatível em fluxo, regra, dados, configuração ou operação que exija migração/ação dos usuários ou operadores.
  - Mudanças somente em documentação, testes, comentários ou refatorações sem efeito observável não incrementam a versão do produto.
- Agentes e mantenedores devem sugerir explicitamente o incremento recomendado (`PATCH`, `MINOR`, `MAJOR` ou nenhum incremento) ao concluir mudanças, sem atualizar a constante automaticamente salvo pedido explícito ou spec aplicável.
- A infraestrutura mínima deve distinguir uso local e uso em rede/LAN.
- O uso em rede deve ser descrito como adequado apenas para rede confiável; acesso remoto deve usar HTTPS/reverse-proxy.
- A tela deve respeitar o design system existente, sem introduzir nova identidade visual.
- O painel principal não deve repetir o rótulo **Sobre** acima de **Sistema Financeiro**, pois o módulo já informa esse contexto no cabeçalho da página.
- O texto descritivo do painel principal deve aproveitar a largura disponível do card antes de quebrar linha, evitando sensação de coluna estreita em telas largas.
- A seção **Contato** pode exibir o widget opcional do **Buy Me a Coffee** ao lado do e-mail. O widget carrega recurso externo da CDN quando há conexão; sem internet ou com bloqueio de terceiros, ele simplesmente não renderiza e o restante da tela permanece íntegro (conteúdo local).
- O texto de **Tecnologias** deve refletir a stack vigente: Python 3 + servidor HTTP da biblioteca padrão, SQLite, HTML/CSS/JS com ES Modules sem build step, PyInstaller, criptografia local de segredos, SMTP local, fontes de cotações (Yahoo Finance, CoinGecko, Banco Central SGS, Mais Retorno) e IA externa opcional.

## API e dados

- `GET /api/app-info`: retorna metadados públicos do app, incluindo `name` e `version`.
- Nenhuma tabela nova.
- Nenhum dado persistido.

## Critérios de aceite

- Dado um usuário autenticado, quando abre o menu **Usuário**, então vê o item **Sobre**.
- Dado o item **Sobre**, quando acionado, então a tela exibe título e conteúdo informativo sem formulário mutável.
- Dada a tela **Sobre**, quando lida, então contém descrição sucinta, funcionalidades principais, versão atual, dados de desenvolvimento, tecnologias, contato e infraestrutura mínima.
- Dado o app em viewport estreita, quando a tela **Sobre** é aberta, então o conteúdo permanece legível e sem overflow horizontal.
- Dado o app em tema claro ou escuro, quando a tela **Sobre** é aberta, então usa os tokens visuais existentes e mantém contraste legível.
- Dada uma viewport larga, quando a tela **Sobre** é aberta, então a descrição do app no painel principal ocupa a largura disponível do card sem quebra prematura.

## Fora de escopo

- Tela de changelog/versionamento automático.
- Captura automática de commit.
- Formulário de contato, envio de e-mail ou abertura de cliente externo.
- Diagnóstico automático da máquina ou da rede.

## Changelog

- `1.8` — 2026-08-10 — Dados de desenvolvimento atualizados na tela Sobre: desenvolvedor passa a ser **Sansquer** e contato `darksansquer@gmail.com`.
- `1.7` — 2026-08-08 — Tela Sobre atualizada: novo texto de funcionalidades e tecnologias refletindo a stack vigente e widget opcional Buy Me a Coffee ao lado do contato (recurso externo, não bloqueia sem internet).
- `1.6` — 2026-07-31 — Versão atual do app elevada para `1.0.52` após ajustes compatíveis de UX no Cockpit.
- `1.5` — 2026-07-31 — Política de versionamento do produto formalizada com critérios para PATCH, MINOR, MAJOR e casos sem incremento de versão.
- `1.4` — 2026-07-27 — Ajustado layout do texto descritivo no painel principal para usar melhor a largura disponível; versão do app elevada para `1.0.51`.
- `1.3` — 2026-07-27 — Versão do sistema centralizada em metadado do backend, exposta via endpoint e exibida na tela Sobre; versão inicial convencionada como `1.0.50`.
- `1.2` — 2026-07-27 — Tela Sobre passa a exibir a versão atual do sistema para identificação do app em execução.
- `1.1` — 2026-07-24 — Removida repetição do rótulo Sobre no painel principal.
- `1.0` — 2026-07-24 — Criada tela **Sobre** no menu Usuário com descrição, funcionalidades, desenvolvimento, tecnologias, contato e infraestrutura mínima.

## Relacionados

- [[frontend-modularizacao]]
- [[../arquitetura|Arquitetura]]
- [[../distribuição|Distribuicao]]
- [[../requisitos|Requisitos]]
