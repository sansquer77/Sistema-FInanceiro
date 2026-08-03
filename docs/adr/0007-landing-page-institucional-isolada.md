---
tipo: adr
area: landing-page
status: implementado
versao: 1.2
atualizado: 2026-08-03
relacionados:
  - "[[../specs/landing-page]]"
  - "[[0002-modularizacao-frontend]]"
  - "[[../distribuição]]"
tags: [adr, "area/landing-page", "status/implementado"]
aliases: ["ADR-0007", "Landing Page institucional em repositório separado"]
---

# ADR-0007 — Landing Page institucional em repositório separado

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-08-03 · relacionados: [[../specs/landing-page]], [[0002-modularizacao-frontend]], [[../distribuição]]

## Contexto

O Sistema Financeiro possui um app principal local/offline-first, com backend Python sem framework e frontend em HTML/CSS/JavaScript com ES Modules nativos, conforme [[0001-stack-local-sem-framework]] e [[0002-modularizacao-frontend]].

A Landing Page institucional tem outro objetivo: apresentar o produto publicamente, usando inspiração e código exportado do v0.app, com deploy pela Vercel.

Essa página não é parte do runtime local do app, não acessa SQLite, `data/`, sessões, API local ou homologação, e não deve entrar nos pacotes instaláveis.

Em 2026-08-03, a decisão evoluiu: em vez de manter a landing como subprojeto dentro deste repositório, ela passa a ter um repositório próprio no GitHub, com cópia local em `/Users/sansquer/Documents/GitHub/sistemafinanceiropage`.

## Decisão

Tratar `/Users/sansquer/Documents/GitHub/sistemafinanceiropage` como o repositório canônico da Landing Page institucional.

Esse projeto separado pode usar stack própria de landing page, incluindo Next.js, React, Tailwind, dependências npm e configuração de build/deploy própria para Vercel.

As restrições de [[0002-modularizacao-frontend]] continuam válidas para o app principal (`web/`, `app.py`, `financeiro/`) e não são relaxadas por esta decisão.

O deploy recomendado da Landing Page é configurar a Vercel diretamente para o repositório `sistemafinanceiropage`.

O código exportado do v0.app deve ser descompactado diretamente na raiz do repositório `sistemafinanceiropage`, evitando um nível intermediário como `sistemafinanceiropage/compute-the-platform.../`. Assets demonstrativos gerados pelo app devem ser preservados e movidos/copiados para a estrutura esperada pelo projeto Next, como `public/images/`, quando necessário.

Este repositório do Sistema Financeiro mantém apenas a documentação de produto/decisão sobre a landing. Alterações de código, imagens e configuração da página institucional devem ser feitas no repositório separado.

O diretório legado `landing-page/` foi removido deste repositório do app principal em 2026-08-03 para reduzir risco de manutenção no local errado. Sua recriação deve ser evitada, salvo pedido explícito de migração ou consulta histórica.

## Consequências positivas

- Preserva a fidelidade visual do template exportado pelo v0.app.
- Evita reimplementar animações, componentes e layout complexo em HTML estático manual.
- Permite deploy direto na Vercel sem afetar a instalação local do Sistema Financeiro.
- Mantém separação clara entre marketing/institucional e runtime financeiro local.
- Não introduz Node.js, build step ou dependências frontend no app principal.
- Evita que dependências, lockfiles e assets da landing poluam o histórico e a distribuição do app principal.

## Consequências negativas / trade-offs

- O produto passa a ter dois repositórios que precisam ser coordenados em mudanças de mensagem, screenshots e documentação.
- Screenshots e assets gerados a partir do app precisam ser copiados intencionalmente para o repositório da landing.
- Agentes e mantenedores precisam lembrar que o código executável da landing não vive mais neste repositório.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| Recriar a landing em HTML/CSS/JS estático | Reduz dependências, mas perde fidelidade com o template baixado e aumenta esforço manual de animações/layout. |
| Incorporar a landing ao `app.py` | Mistura institucional público com app local autenticado e criaria acoplamento desnecessário. |
| Migrar o app principal para Next/React | Contraria [[0002-modularizacao-frontend]] e adiciona complexidade incompatível com o runtime local/offline-first. |
| Manter a landing como subprojeto no repositório do app | Foi a primeira decisão, mas criaria ruído de dependências e artefatos de marketing dentro do repositório do runtime financeiro. |

## Relacionados

- [[../specs/landing-page]]
- [[0002-modularizacao-frontend]]
- [[../distribuição]]
