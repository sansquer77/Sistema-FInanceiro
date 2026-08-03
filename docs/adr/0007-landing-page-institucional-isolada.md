---
tipo: adr
area: landing-page
status: implementado
versao: 1.0
atualizado: 2026-08-02
relacionados:
  - "[[../specs/landing-page]]"
  - "[[0002-modularizacao-frontend]]"
  - "[[../distribuição]]"
tags: [adr, "area/landing-page", "status/implementado"]
aliases: ["ADR-0007", "Landing Page institucional isolada"]
---

# ADR-0007 — Landing Page institucional como subprojeto isolado

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-08-02 · relacionados: [[../specs/landing-page]], [[0002-modularizacao-frontend]], [[../distribuição]]

## Contexto

O Sistema Financeiro possui um app principal local/offline-first, com backend Python sem framework e frontend em HTML/CSS/JavaScript com ES Modules nativos, conforme [[0001-stack-local-sem-framework]] e [[0002-modularizacao-frontend]].

A Landing Page institucional tem outro objetivo: apresentar o produto publicamente, usando inspiração e código exportado do v0.app, com deploy pela Vercel apontando para o diretório `landing-page/`.

Essa página não é parte do runtime local do app, não acessa SQLite, `data/`, sessões, API local ou homologação, e não deve entrar nos pacotes instaláveis.

## Decisão

Tratar `landing-page/` como um subprojeto institucional independente dentro do mesmo repositório.

Esse subprojeto pode usar stack própria de landing page, incluindo Next.js, React, Tailwind, dependências npm e configuração de build/deploy própria para Vercel.

As restrições de [[0002-modularizacao-frontend]] continuam válidas para o app principal (`web/`, `app.py`, `financeiro/`) e não são relaxadas por esta decisão.

O deploy recomendado da Landing Page é configurar a Vercel com **Root Directory** apontando para `landing-page/`.

O código exportado do v0.app deve ser descompactado diretamente dentro de `landing-page/`, evitando um nível intermediário como `landing-page/compute-the-platform.../`. Assets demonstrativos gerados pelo app devem ser preservados e movidos/copidos para a estrutura esperada pelo subprojeto, como `landing-page/public/`, quando necessário.

## Consequências positivas

- Preserva a fidelidade visual do template exportado pelo v0.app.
- Evita reimplementar animações, componentes e layout complexo em HTML estático manual.
- Permite deploy direto na Vercel sem afetar a instalação local do Sistema Financeiro.
- Mantém separação clara entre marketing/institucional e runtime financeiro local.
- Não introduz Node.js, build step ou dependências frontend no app principal.

## Consequências negativas / trade-offs

- O repositório passa a ter dois projetos frontend com stacks diferentes.
- Agentes e mantenedores precisam respeitar a fronteira de diretórios para não levar dependências da landing para o app principal.
- `landing-page/` precisará de regras próprias de build, lint e deploy.
- A distribuição do app precisa continuar excluindo explicitamente `landing-page/`.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| Recriar a landing em HTML/CSS/JS estático | Reduz dependências, mas perde fidelidade com o template baixado e aumenta esforço manual de animações/layout. |
| Incorporar a landing ao `app.py` | Mistura institucional público com app local autenticado e criaria acoplamento desnecessário. |
| Migrar o app principal para Next/React | Contraria [[0002-modularizacao-frontend]] e adiciona complexidade incompatível com o runtime local/offline-first. |
| Manter a landing em repositório separado | Isola melhor, mas dificulta reaproveitar screenshots, documentação e versionamento conjunto neste momento. |

## Relacionados

- [[../specs/landing-page]]
- [[0002-modularizacao-frontend]]
- [[../distribuição]]
