---
tipo: produto
area: meta
status: implementado
versao: 2.5
atualizado: 2026-07-23
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
| [[distribuição]] | Regras de geração, limpeza, instalação e validação dos pacotes macOS e Windows. |
| [[templates/spec-template]] | Template obrigatório para criar novos documentos. |

---

## Specs por módulo

| Spec | Status | Área |
|---|---|---|
| [[specs/contas-correntes]] | ✅ implementado | Contas |
| [[specs/lancamentos]] | ✅ implementado | Lançamentos |
| [[specs/categorias-tags-gestao]] | ✅ implementado | Classificação |
| [[specs/cartoes]] | ✅ implementado | Cartões |
| [[specs/limites-gastos]] | ✅ implementado | Limites |
| [[specs/classificacao-assistida]] | ✅ implementado | Classificação |
| [[specs/investimentos-portfolio]] | ✅ implementado | Investimentos |
| [[specs/relatorios]] | ✅ implementado | Relatórios |
| [[specs/importacao-organizze]] | ✅ implementado | Importação |
| [[specs/recuperacao-senha]] | ✅ implementado | Segurança |
| [[specs/seguranca-autenticacao]] | ✅ implementado | Segurança |
| [[specs/frontend-modularizacao]] | ✅ implementado | Frontend |
| [[distribuição]] | ✅ implementado | Distribuição |

---

## ADRs — Decisões técnicas

| ADR | Decisão |
|---|---|
| [[adr/0001-stack-local-sem-framework]] | Servidor HTTP puro em Python, sem framework web. |
| [[adr/0002-modularizacao-frontend]] | ES Modules nativos sem build step. |
| [[adr/0003-sqlite-fonte-de-verdade]] | SQLite local como única fonte de verdade. |
| [[adr/0004-importador-xls-sem-dependencia]] | Parser `.xls` implementado sem biblioteca externa. |
| [[adr/0005-smtp-criptografado-local]] | Configuração SMTP criptografada em arquivo local. |
| [[adr/0006-classificacao-assistida-local]] | Proposta de classificação assistida por hábitos locais, com IA externa apenas como fallback opcional. |

---

## Design

| Documento | Descrição |
|---|---|
| [[design/design-system]] | Tokens visuais, paleta, tipografia, espaçamento, bordas e componentes. |

---

## Regra prática para qualquer mudança

```
1. Localize ou crie a spec/documento usando [[templates/spec-template]]
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
| Distribuição | Pacotes macOS e Windows offline-first, com modo local padrão e modo LAN explícito |

## Changelog

- `2.5` — 2026-07-23 — MVP de classificação assistida concluído e documentação marcada como implementada.
- `2.4` — 2026-07-23 — MVP de classificação assistida aprovado e movido para implementação; ADR-0006 adotado.
- `2.3` — 2026-07-23 — Incluídos a spec e o ADR em rascunho para classificação assistida por hábitos locais.
- `2.2` — 2026-07-04 — Índice inclui a spec de distribuição, stack reflete macOS/Windows e reforça que novos documentos também partem do template de spec.
- `2.1` — 2026-06-30 — Regra prática ajustada para explicitar que novas specs devem usar `docs/templates/spec-template.md` como base.
- `2.0` — 2026-06-29 — Reestruturação completa do vault: frontmatter padronizado em todas as notas, glossário, ADRs, design system, template de spec, MoC como ponto de entrada único, wikilinks cruzados entre todos os documentos.
- `1.0` — versão original com documentos soltos sem estrutura de navegação.
