---
tipo: spec
area: usuario
status: implementado
versao: 1.3
atualizado: 2026-07-27
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
> **implementado** · área: `usuario` · atualizado em 2026-07-27 · relacionados: [[frontend-modularizacao]], [[../arquitetura|Arquitetura]], [[../distribuição|Distribuicao]], [[../requisitos|Requisitos]]

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
- A tela deve ser somente leitura e não deve criar endpoints, tabelas, arquivos de dados ou chamadas externas.
- O conteúdo deve mencionar o objetivo principal: controle financeiro local, privado e simples.
- As funcionalidades devem cobrir contas, cartões, lançamentos, categorias/tags, limites, relatórios, cockpit, portfólio, importação, histórico e preferências/segurança.
- Os dados de desenvolvimento devem informar:
  - Desenvolvedor: Cristiano Gaspar.
  - Versão atual do sistema, a partir do endpoint de metadados do app.
  - Tecnologias utilizadas no app.
  - Contato: `cristiano_gaspar@outlook.com`.
- A versão de produto deve partir de `1.0.50` e evoluir preferencialmente em `1.0.n` para correções e ajustes incrementais; mudanças funcionais maiores podem justificar evolução `1.y`.
- A infraestrutura mínima deve distinguir uso local e uso em rede/LAN.
- O uso em rede deve ser descrito como adequado apenas para rede confiável; acesso remoto deve usar HTTPS/reverse-proxy.
- A tela deve respeitar o design system existente, sem introduzir nova identidade visual.
- O painel principal não deve repetir o rótulo **Sobre** acima de **Sistema Financeiro**, pois o módulo já informa esse contexto no cabeçalho da página.

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

## Fora de escopo

- Tela de changelog/versionamento automático.
- Captura automática de commit.
- Formulário de contato, envio de e-mail ou abertura de cliente externo.
- Diagnóstico automático da máquina ou da rede.

## Changelog

- `1.3` — 2026-07-27 — Versão do sistema centralizada em metadado do backend, exposta via endpoint e exibida na tela Sobre; versão inicial convencionada como `1.0.50`.
- `1.2` — 2026-07-27 — Tela Sobre passa a exibir a versão atual do sistema para identificação do app em execução.
- `1.1` — 2026-07-24 — Removida repetição do rótulo Sobre no painel principal.
- `1.0` — 2026-07-24 — Criada tela **Sobre** no menu Usuário com descrição, funcionalidades, desenvolvimento, tecnologias, contato e infraestrutura mínima.

## Relacionados

- [[frontend-modularizacao]]
- [[../arquitetura|Arquitetura]]
- [[../distribuição|Distribuicao]]
- [[../requisitos|Requisitos]]
