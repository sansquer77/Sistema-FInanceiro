---
tipo: produto
area: meta
status: implementado
versao: 2.0
atualizado: 2026-06-29
tags: [meta, moc]
aliases: ["Home", "Índice", "Map of Content"]
---

# Sistema Financeiro — Documentação

> [!info] Como usar este vault
> Abra esta pasta no **Obsidian** para navegação por wikilinks, grafo de dependências e painel de tags. Funciona igualmente como markdown puro em qualquer IDE ou agente de IA. O processo de desenvolvimento está em [[sdd]].

Este é o **Map of Content (MoC)** do vault. Cada link leva ao documento canônico da área. Antes de alterar qualquer parte do app, localize a spec correspondente aqui e siga o fluxo descrito em [[sdd]].

---

## Documentos estruturais

| Documento | Descrição |
|---|---|
| [[sdd]] | Metodologia SDD: como criar e manter specs, ciclo de vida, convenções do vault. |
| [[requisitos]] | Escopo funcional completo, regras de negócio e requisitos não funcionais. |
| [[arquitetura]] | Camadas, rotas da API, tabelas, módulos Python e fluxos principais. |
| [[visao-produto]] | Direção de produto, princípios de experiência e estado atual dos módulos. |
| [[roadmap]] | Sequência de evolução, status por módulo e próximas prioridades. |
| [[glossario]] | Vocabulário de domínio com links para as specs onde cada conceito é definido. |
| [[templates/spec-template]] | Template obrigatório para criar novas specs. |

---

## Specs por módulo

| Spec | Status | Área |
|---|---|---|
| [[specs/contas-correntes]] | ✅ implementado | Contas |
| [[specs/lancamentos]] | ✅ implementado | Lançamentos |
| [[specs/categorias-tags-gestao]] | ✅ implementado | Classificação |
| [[specs/cartoes]] | ✅ implementado | Cartões |
| [[specs/limites-gastos]] | ✅ implementado | Limites |
| [[specs/investimentos-portfolio]] | ✅ implementado | Investimentos |
| [[specs/relatorios]] | ✅ implementado | Relatórios |
| [[specs/importacao-organizze]] | ✅ implementado | Importação |
| [[specs/recuperacao-senha]] | ✅ implementado | Segurança |
| [[specs/seguranca-autenticacao]] | ✅ implementado | Segurança |
| [[specs/frontend-modularizacao]] | ✅ implementado | Frontend |

---

## ADRs — Decisões técnicas

| ADR | Decisão |
|---|---|
| [[adr/0001-stack-local-sem-framework]] | Servidor HTTP puro em Python, sem framework web. |
| [[adr/0002-modularizacao-frontend]] | ES Modules nativos sem build step. |
| [[adr/0003-sqlite-fonte-de-verdade]] | SQLite local como única fonte de verdade. |
| [[adr/0004-importador-xls-sem-dependencia]] | Parser `.xls` implementado sem biblioteca externa. |
| [[adr/0005-smtp-criptografado-local]] | Configuração SMTP criptografada em arquivo local. |

---

## Design

| Documento | Descrição |
|---|---|
| [[design/design-system]] | Tokens visuais, paleta, tipografia, espaçamento, bordas e componentes. |

---

## Regra prática para qualquer mudança

```
1. Localize ou crie a spec em specs/  →  [[sdd]]
2. Atualize requisitos se o escopo geral mudar  →  [[requisitos]]
3. Atualize arquitetura se houver nova rota, tabela ou fluxo  →  [[arquitetura]]
4. Se houver decisão técnica não trivial, registre um ADR em adr/
5. Implemente a menor mudança que cumpre a spec
6. Atualize status, versao, atualizado e Changelog da spec
```

---

## Stack

| Camada | Tecnologia |
|---|---|
| Servidor | Python 3 (biblioteca padrão, sem framework) |
| Banco | SQLite em `data/finance.db` |
| Frontend | HTML + CSS + JavaScript (ES Modules nativos, sem build) |
| macOS | App local offline-first |

## Changelog

- `2.0` — 2026-06-29 — Reestruturação completa do vault: frontmatter padronizado em todas as notas, glossário, ADRs, design system, template de spec, MoC como ponto de entrada único, wikilinks cruzados entre todos os documentos.
- `1.0` — versão original com documentos soltos sem estrutura de navegação.
