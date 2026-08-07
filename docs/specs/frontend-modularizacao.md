---
tipo: spec
area: frontend
status: implementado
versao: 2.3
atualizado: 2026-08-07
relacionados:
  - "[[adr/0002-modularizacao-frontend]]"
  - "[[arquitetura]]"
tags: [spec, "area/frontend"]
aliases: ["Modularização Frontend", "ES Modules"]
---

# Modularização do Frontend

> [!info] Status
> **implementado** · área: `frontend` · atualizado em 2026-08-02 · relacionados: [[adr/0002-modularizacao-frontend]], [[arquitetura]]

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
| `decision-modal.js` | Modal reutilizável para decisões, confirmações explícitas e pequenos formulários. |
| `theme-utils.js` | Preferência visual local e aplicação de tema no `documentElement`. |
| `privacy-utils.js` | Preferência visual local de privacidade, aplicação de `data-privacy` e marcação visual de valores monetários. |

## Views funcionais

| Arquivo | Responsabilidade |
|---|---|
| `auth-view.js` | Login, cadastro, logout e recuperação de senha. |
| `user-admin-view.js` | Preferência visual, troca de email/senha, config. SMTP, limpeza e exclusão. |
| `classifications-view.js` | Categorias, subcategorias e tags. |
| `limits-view.js` | Limites de gastos e índice de consumo. |
| `reports-view.js` | Filtros, abas, agrupamentos e tabelas. |
| `imports-view.js` | Upload, download de modelo e resultado da importação. |
| `cockpit-view.js` | Resumo, saldos, planejamento, dívidas, portfólio e alertas. |
| `financial-health-view.js` | Aba Saúde Financeira do Cockpit: score/gauge, pilares, Paz Financeira e recomendações. |
| `trends-view.js` | Aba Tendências do Cockpit: gráfico de evolução mensal, Budget x Realizado e achados. |
| `consultor-view.js` | Aba Consultor/Calendário do Cockpit: vencimentos, atrasos e plano próximo. |
| `accounts-view.js` | Contas: cadastro, edição, arquivamento e restauração. |
| `cards-view.js` | Cartões: cadastro, faturas, busca/filtro da fatura, pagamento e conciliação. |
| `portfolio-view.js` | Ativos: posições, consolidações com escala BRL, histórico, resgate e encerramento. |
| `transactions-view.js` | Lançamentos: formulário, recorrência, parcelas e câmbio. |
| `operation-history-view.js` | Histórico de Operações: filtros, busca, agrupamentos e paginação incremental. |

Views estáticas simples, como **Sobre**, podem permanecer declaradas no HTML e roteadas por `app.js` quando não possuem estado próprio, API ou lógica funcional dedicada.

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
- Cores de UI e gráficos devem vir de tokens CSS compartilhados; literais ficam restritos a marcas/logos externos.
- Tema visual é uma preferência local: `theme-utils.js` aplica `data-theme` no elemento raiz e persiste em `localStorage`.
- Modo privacidade é uma preferência local: `privacy-utils.js` aplica `data-privacy` no elemento raiz, persiste em `localStorage` e não altera dados, cálculos ou chamadas de API.
- O modo escuro deve ser evoluído por tokens em CSS, mantendo views sem ramificações por tema.
- `user-admin-view.js` apenas orquestra o controle de Preferências; persistência e aplicação do tema permanecem em `theme-utils.js`.
- Fluxos com decisão financeira, destrutiva ou de cascata devem usar `decision-modal.js`, evitando `window.confirm()` e `window.prompt()` para escolhas de domínio.
- A navegação lateral deve usar rótulos desambiguados quando dois módulos compartilham o mesmo substantivo de domínio: em **Cadastro**, usar **Minhas Contas** e **Meus Cartões**; em **Lançamentos**, usar **Extrato de Contas** e **Fatura de Cartões**.
- Os títulos de página controlados por `app.js` devem acompanhar os rótulos desambiguados da navegação para reforçar a intenção da tela ativa.
- A troca entre módulos do dashboard deve usar `document.startViewTransition()` quando disponível, como melhoria progressiva, preservando fallback instantâneo em navegadores sem suporte.
- A transição de visão deve respeitar `prefers-reduced-motion: reduce` e nunca aguardar chamadas de API, carregamentos remotos ou cálculos de tela para iniciar a navegação.

## API e dados

- Nenhum endpoint novo.
- Nenhuma tabela nova.
- `index.html` carrega `app.js` como `type="module"`.

## Critérios de aceite

- Dado o app carregado, quando o navegador busca `app.js`, todos os imports de `web/modules/` resolvem sem erro.
- Dado um fluxo existente (login, navegação, lançamentos, cartões, relatórios, portfólio), quando usado, as chamadas de API e formatações continuam iguais ao comportamento anterior.
- Dado um mantenedor buscando formatação monetária ou de datas, quando procura, encontra em `money-utils.js` e `date-utils.js`.
- Dado um mantenedor buscando qualquer área funcional, quando procura, encontra no arquivo de view correspondente.
- Dado o usuário autenticado, quando alterna `Claro` ou `Escuro` em Preferências, o `data-theme` do documento muda imediatamente e persiste após reload.
- Dado o tema claro ou escuro ativo, quando navega por Cockpit, Contas, Cartões, Lançamentos, Portfólio, Limites, Relatórios, Categorias, Importação e Preferências, os módulos abrem sem erro de console e mantêm contraste legível.
- Dado viewport mobile, quando abre Preferências, o controle de tema ocupa a largura disponível sem overflow horizontal.
- Dado uma decisão de edição/exclusão em cascata ou encerramento de posição, quando a interface solicita confirmação, os botões exibem ações explícitas e `Voltar` aborta a operação.
- Dado o grupo Usuário, quando o item Sobre é acionado, então `app.js` exibe uma view estática sem criar módulo ou endpoint desnecessário.
- Dado o usuário visualizando o menu lateral, quando compara os grupos Cadastro e Lançamentos, então os itens não repetem apenas `Contas` e `Cartões`; eles aparecem como **Minhas Contas**, **Meus Cartões**, **Extrato de Contas** e **Fatura de Cartões**.
- Dado o usuário acessando um desses itens, quando a tela abre, então o título da página usa o mesmo nome desambiguado do menu.
- Dado um navegador com suporte a View Transitions API, quando o usuário alterna módulos pelo menu lateral, então a troca visual acontece com transição curta e sem bloquear os carregamentos da tela.
- Dado o usuário autenticado, quando alterna o modo privacidade, então `privacy-utils.js` aplica `data-privacy` no documento sem alterar endpoints, banco ou regras financeiras.
- Dado um navegador sem suporte à API ou com redução de movimento ativa, quando o usuário alterna módulos, então a navegação continua funcionando de forma instantânea.

## Fora de escopo

- Reescrever HTML/CSS.
- Criar build step.
- Alterar regras financeiras, endpoints ou banco.

## Changelog

- `2.3` — 2026-08-07 — Aba **Saúde Financeira** do Cockpit extraída para view dedicada `financial-health-view.js` (fábrica `registerFinancialHealthView`), desacoplando o estado de tela do `cockpit-view.js`.
- `2.2` — 2026-08-02 — Registrado `privacy-utils.js` como utilitário local para Modo Privacidade via `data-privacy`, sem backend ou build step.
- `2.1` — 2026-08-02 — Troca de módulos do dashboard passa a usar View Transitions API como melhoria progressiva, com fallback e respeito a redução de movimento.
- `2.0` — 2026-08-02 — Navegação lateral passa a documentar rótulos desambiguados para Cadastro e Lançamentos, com títulos de página alinhados.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados; referência cruzada com ADR.
- `1.1` — 2026-06-30 — Responsabilidade de busca/filtro da fatura registrada em `cards-view.js`; consolidações do Portfólio documentadas em `portfolio-view.js`.
- `1.2` — 2026-06-30 — Regra de tokenização de cores e gráficos registrada para preparação do modo escuro.
- `1.3` — 2026-06-30 — Infraestrutura local de tema registrada em `theme-utils.js`.
- `1.4` — 2026-06-30 — Regra de evolução do modo escuro por overrides centralizados de tokens registrada.
- `1.5` — 2026-07-01 — Controle claro/escuro em Preferências registrado em `user-admin-view.js`.
- `1.6` — 2026-07-01 — Critérios de aceite e cobertura de QA do tema claro/escuro registrados.
- `1.7` — 2026-07-09 — `operation-history-view.js` registrado como view funcional do Histórico de Operações.
- `1.8` — 2026-07-20 — `decision-modal.js` registrado como helper reutilizável para decisões e formulários curtos.
- `1.9` — 2026-07-24 — Tela estática Sobre documentada como view simples roteada por `app.js`.

## Relacionados

- [[adr/0002-modularizacao-frontend]]
- [[arquitetura]]
