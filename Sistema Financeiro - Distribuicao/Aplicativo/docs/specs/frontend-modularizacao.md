---
tipo: spec
area: frontend
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[adr/0002-modularizacao-frontend]]"
  - "[[arquitetura]]"
tags: [spec, "area/frontend"]
aliases: ["Modularização Frontend", "ES Modules"]
---

# Modularização do Frontend

> [!info] Status
> **implementado** · área: `frontend` · atualizado em 2026-06-29 · relacionados: [[adr/0002-modularizacao-frontend]], [[arquitetura]]

## Problema

O arquivo `web/app.js` concentrava estado de tela, chamadas de API, formatadores, renderização, regras auxiliares e handlers de todos os módulos. Isso dificultava leitura, revisão e evolução sem risco de regressão.

## Usuário

Mantenedores e agentes de IA em IDEs que precisam evoluir a interface local com segurança, mantendo o app simples e sem etapa de build.

## Jornada

1. O mantenedor abre a pasta `web/`.
2. Encontra responsabilidades comuns em `web/modules/`.
3. Evolui uma área funcional sem precisar percorrer todo o `app.js`.
4. O navegador carrega a interface por ES Modules nativos.

## Módulos utilitários

| Arquivo | Responsabilidade |
|---|---|
| `api.js` | Chamadas HTTP JSON e upload. |
| `date-utils.js` | Datas locais, meses e exibição. |
| `money-utils.js` | Formatação e parsing numérico/monetário. |
| `dom-utils.js` | Helpers de formulário, mensagens e empty state. |
| `transaction-kind.js` | Predicados de tipo de lançamento. |
| `labels.js` | Labels de domínio usados pela interface. |
| `month-picker.js` | Popover reutilizável de seleção de mês. |

## Views funcionais

| Arquivo | Responsabilidade |
|---|---|
| `auth-view.js` | Login, cadastro, logout e recuperação de senha. |
| `user-admin-view.js` | Troca de email/senha, config. SMTP, limpeza e exclusão. |
| `classifications-view.js` | Categorias, subcategorias e tags. |
| `limits-view.js` | Limites de gastos e índice de consumo. |
| `reports-view.js` | Filtros, abas, agrupamentos e tabelas. |
| `imports-view.js` | Upload, download de modelo e resultado da importação. |
| `cockpit-view.js` | Resumo, saldos, planejamento, dívidas, portfólio e alertas. |
| `accounts-view.js` | Contas: cadastro, edição, arquivamento e restauração. |
| `cards-view.js` | Cartões: cadastro, faturas, pagamento e conciliação. |
| `portfolio-view.js` | Ativos: posições, histórico, resgate e encerramento. |
| `transactions-view.js` | Lançamentos: formulário, recorrência, parcelas e câmbio. |

## Contrato de fábrica para views

```js
export function createXxxView({ state, elements, services, formatters, actions }) {
  // state    → estado centralizado da tela
  // elements → referências DOM daquela área
  // services → api, upload e carregadores compartilhados
  // formatters → funções de data, dinheiro e labels
  // actions  → callbacks de navegação ou refresh global
}
```

## Regras

- Não alterar comportamento observável da interface.
- Não introduzir framework, bundler ou dependências de frontend.
- Módulos têm nomes em inglês e funções pequenas.
- Regras financeiras permanecem no domínio Python; o frontend apenas formata e orquestra.
- Novos módulos recebem dependências explicitamente via contrato de fábrica.

## API e dados

- Nenhum endpoint novo.
- Nenhuma tabela nova.
- `index.html` carrega `app.js` como `type="module"`.

## Critérios de aceite

- Dado o app carregado, quando o navegador busca `app.js`, todos os imports de `web/modules/` resolvem sem erro.
- Dado um fluxo existente (login, navegação, lançamentos, cartões, relatórios, portfólio), quando usado, as chamadas de API e formatações continuam iguais ao comportamento anterior.
- Dado um mantenedor buscando formatação monetária ou de datas, quando procura, encontra em `money-utils.js` e `date-utils.js`.
- Dado um mantenedor buscando qualquer área funcional, quando procura, encontra no arquivo de view correspondente.

## Fora de escopo

- Reescrever HTML/CSS.
- Criar build step.
- Alterar regras financeiras, endpoints ou banco.

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados; referência cruzada com ADR.

## Relacionados

- [[adr/0002-modularizacao-frontend]]
- [[arquitetura]]
