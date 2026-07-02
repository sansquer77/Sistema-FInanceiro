---
tipo: adr
area: meta
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[arquitetura]]"
  - "[[specs/frontend-modularizacao]]"
  - "[[adr/0001-stack-local-sem-framework]]"
tags: [adr, meta, frontend]
aliases: ["ADR-0002", "ES Modules nativos"]
---

# ADR-0002 — Modularização do frontend em ES Modules nativos

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-06-29

## Contexto

O arquivo `web/app.js` cresceu concentrando estado de tela, chamadas de API, formatadores, renderização, regras auxiliares e handlers de todos os módulos. Isso aumentou o risco de regressão a cada mudança e dificultou a leitura por mantenedores e agentes de IA.

## Decisão

Dividir o frontend em **ES Modules nativos** carregados pelo próprio navegador via `<script type="module">`, sem etapa de build, bundler ou transpiler.

A estrutura segue um contrato de fábrica:
```js
export function createXxxView({ state, elements, services, formatters, actions }) { … }
```

Responsabilidades separadas por tipo de módulo:
- **Utilitários** (`api`, `date-utils`, `money-utils`, `dom-utils`, `labels`, `month-picker`, `transaction-kind`): funções puras, sem estado.
- **Views** (`accounts-view`, `cards-view`, `transactions-view` etc.): estado local de tela, renderização e handlers de um único módulo funcional.
- **`app.js`**: orquestração geral, navegação e injeção de dependências.

## Consequências positivas

- Cada área funcional pode ser lida, modificada e testada isoladamente.
- Nenhum impacto de instalação: o navegador moderno já suporta ES Modules.
- Agentes de IA em IDEs conseguem localizar responsabilidades por arquivo sem percorrer um monolito.
- Sem risco de dependência circular quando o contrato de fábrica é respeitado.

## Consequências negativas / trade-offs

- Sem tree-shaking ou minificação: o volume de código transferido ao navegador é maior (aceitável para uso local).
- Debugging pode ser ligeiramente mais distribuído em múltiplos arquivos.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| React/Vue com bundler | Introduz build step, `node_modules` e complexidade de setup incompatíveis com a filosofia local-offline-first. |
| Concatenação manual de scripts | Não resolve o problema de responsabilidades misturadas; apenas fragmenta o arquivo. |
| Web Components nativos | Overhead de API mais verbosa para benefício equivalente. |

## Relacionados

- [[specs/frontend-modularizacao]]
- [[arquitetura]]
- [[adr/0001-stack-local-sem-framework]]
