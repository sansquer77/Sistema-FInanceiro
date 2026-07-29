---
tipo: design
area: meta
status: implementado
versao: 2.0
atualizado: 2026-07-29
relacionados:
  - "[[arquitetura]]"
  - "[[specs/frontend-modularizacao]]"
tags: [design, meta]
aliases: ["Design System", "Tokens Visuais", "Precisão Institucional"]
---

# Design System — Precisão Institucional

> [!info] Status
> **implementado** · área: `meta` · atualizado em 2026-07-29 · relacionados: [[arquitetura]], [[specs/frontend-modularizacao]]

## Personalidade da marca

Autoritária, sistemática e altamente técnica. A interface deve evocar confiabilidade absoluta e clareza — estilo **Corporativo Moderno** com tendências **Minimalistas**. Prioriza densidade de dados e legibilidade em vez de elementos decorativos. Interesse visual gerado por alinhamento preciso e uso estratégico de cores categóricas.

---

## Tokens de cor

### Paleta principal

| Token | Valor | Uso |
|---|---|---|
| `--primary` | `#00328a` | Branding, ações primárias, estados ativos de navegação. |
| `--primary-container` | `#0047bb` | Botões primários em hover / foco. |
| `--on-primary` | `#ffffff` | Texto sobre fundo primário. |
| `--secondary` | `#a04100` | **Exclusivamente** para ícones e itens de interface. Nunca para valores numéricos. |
| `--secondary-container` | `#fe6b00` | Chips/badges de despesa ou passivo. |

### Superfícies

| Token | Valor | Uso |
|---|---|---|
| `--surface` | `#faf8ff` | Fundo geral da página. |
| `--surface-container-lowest` | `#ffffff` | Cartões e containers principais. |
| `--surface-container-low` | `#f2f3ff` | Fundo de seções secundárias. |
| `--surface-container` | `#eaedff` | Itens de lista em hover. |
| `--surface-container-high` | `#e2e7ff` | Bordas internas de tabelas. |
| `--surface-dim` | `#d2d9f4` | Fundos desabilitados / inativos. |

### Textos e bordas

| Token | Valor | Uso |
|---|---|---|
| `--on-surface` | `#131b2e` | Texto principal. |
| `--on-surface-variant` | `#434653` | Texto secundário e labels. |
| `--outline` | `#737685` | Bordas de campos de formulário. |
| `--outline-variant` | `#c3c6d6` | Divisores e bordas de baixo contraste. |

### Indicadores semânticos e numéricos

> [!warning] Regra crítica — aplicar sem exceção
> Estas cores têm semântica financeira estrita. Nunca as use para botões gerais ou ícones categóricos.

| Cor | Valor | Uso obrigatório |
|---|---|---|
| **Vermelho** | `#EF4444` | **Todos** os números negativos (saldos e lançamentos) e alertas críticos. |
| **Verde** | `#10B981` | **Somente** saldos positivos e indicadores de saúde financeira. |
| **Preto** | `#131b2e` | Números positivos em **itens de lançamento** (entradas). |

### Tokens semânticos para gráficos e estados

Para garantir contraste acessível (WCAG AA ≥ 4.5:1 para texto) em ambos os temas, os elementos coloridos que carregam significado financeiro devem preferir os tokens semânticos abaixo em vez de literais. Os valores de fallback refletem a intenção no tema claro; o tema escuro faz override quando necessário.

| Token | Fallback claro | Uso | Texto sobre o token |
|---|---|---|---|
| `--color-success` | `#10B981` | Indicadores saudáveis, barras de score "bom", saldos positivos em gráficos. | `--color-success-text` → `#ffffff` |
| `--color-success-text` | `#ffffff` | Texto/ícone sobre fundo de sucesso. | Override escuro quando o fallback não atinge contraste. |
| `--color-warning` | `#F59E0B` | Estados de atenção, badges de alerta moderado. | `--color-warning-text` → `#1f2937` |
| `--color-warning-text` | `#1f2937` | Texto/ícone sobre fundo de aviso. | Deve manter contraste ≥ 4.5:1 sobre `--color-warning`. |
| `--color-error` | `#EF4444` | Estados críticos, erros, saldos negativos em gráficos. | `--color-error-text` → `#ffffff` |
| `--color-error-text` | `#ffffff` | Texto/ícone sobre fundo de erro. | Override escuro quando o fallback não atinge contraste. |

Regras de aplicação:
- Use `var(--color-success)` no lugar de `#10B981` em novos componentes e no gráfico de pilares do Score de Saúde Financeira.
- Use `var(--color-error)` no lugar de `#EF4444` para estados críticos e saldos negativos.
- Use `var(--color-warning)` para estados de atenção, substituindo literais como `#F59E0B`.
- Sempre pare fundo semântico com seu respectivo `*-text` para garantir contraste.
- O tema escuro deve fazer override dos tokens acima (por exemplo, `--color-success: #34d399`) e, quando necessário, ajustar `--color-success-text` para `#101114` para manter contraste.

### Estado / Erro

| Token | Valor |
|---|---|
| `--error` | `#ba1a1a` |
| `--error-container` | `#ffdad6` |

### Preparação para tema escuro

- Cores de UI devem ser aplicadas por tokens CSS, nunca como literais espalhados em componentes.
- Gráficos e barras de distribuição devem consumir tokens de paleta (`--chart-*`) para permitir troca de tema sem alterar módulos funcionais.
- Logos e cores institucionais de bancos podem permanecer literais quando representam marca ou ativo visual externo.
- Novos componentes devem reutilizar tokens existentes antes de criar novos aliases.
- A primeira etapa de implantação de tema escuro deve preservar o modo claro sem mudança visual perceptível.
- O tema ativo é aplicado em `document.documentElement.dataset.theme` com valores `light` ou `dark`.
- A preferência visual é local ao navegador e persistida em `localStorage` pela chave `sistemaFinanceiro.theme`.
- O `index.html` deve aplicar o tema antes do carregamento do CSS para evitar flash visual.
- O tema escuro é implementado somente por overrides de tokens em `[data-theme="dark"]`; componentes não devem criar regras escuras próprias sem necessidade.
- Cores semânticas mantêm a intenção no escuro: negativos continuam em vermelho, positivos em verde e ações primárias usam o token de destaque com contraste adequado.
- A alternância entre `light` e `dark` fica no módulo Preferências, em um controle segmentado com estado ativo visível.

---

## Tipografia

Fonte única: **Inter**. Use figuras tabulares (`font-variant-numeric: tabular-nums`) em todos os valores financeiros para alinhamento vertical.

| Token | Tamanho | Peso | Altura de linha | Tracking | Uso |
|---|---|---|---|---|---|
| `display-lg` | 48px | 700 | 56px | -0.02em | Títulos de tela principais. |
| `headline-lg` | 32px | 600 | 40px | -0.01em | Cabeçalhos de seção. |
| `headline-lg-mobile` | 24px | 600 | 32px | — | Cabeçalhos em mobile. |
| `title-md` | 20px | 600 | 28px | — | Títulos de cards e painéis. |
| `body-md` | 16px | 400 | 24px | — | Corpo de texto principal. |
| `body-sm` | 14px | 400 | 20px | — | Texto auxiliar e descrições. |
| `label-md` | 12px | 600 | 16px | 0.05em | Cabeçalhos de colunas de tabela (MAIÚSCULAS). |
| `label-sm` | 11px | 500 | 14px | — | Labels de status e badges. |

---

## Espaçamento

Grade de linha de base: **4px** (todos os valores são múltiplos de 4px).

| Token | Valor | Uso típico |
|---|---|---|
| `--spacing-xs` | 4px | Gap mínimo entre elementos internos. |
| `--spacing-sm` | 8px | Padding interno de chips e badges. |
| `--spacing-md` | 16px | Padding de campos, botões e cards. |
| `--spacing-lg` | 24px | Gutter de grade; padding de seções. |
| `--spacing-xl` | 32px | Margem entre blocos maiores. |
| `--gutter` | 24px | Padding lateral da página. |

---

## Border radius

| Token | Valor | Uso |
|---|---|---|
| `--rounded-sm` | 0.25rem | Checkboxes, tags, badges e chips pequenos. |
| `--rounded` | 0.5rem | Botões, campos de input, cards — padrão. |
| `--rounded-md` | 0.75rem | Containers médios. |
| `--rounded-lg` | 1rem | Cards de dashboard, modais. |
| `--rounded-xl` | 1.5rem | Elementos de destaque. |
| `--rounded-full` | 9999px | Avatares, indicadores circulares. |

---

## Layout e grade

| Breakpoint | Grade | Margem |
|---|---|---|
| Desktop | 12 colunas, largura 100% (sem `max-width`) | 24px lateral |
| Tablet | 8 colunas | 24px lateral |
| Mobile | 4 colunas fluidas | 16px lateral |

---

## Elevação e sombras

- **Superfícies**: hierarquia por camada tonal (tokens `--surface-*`), não por sombra.
- **Bordas**: 1px sólida em `--outline-variant` para delimitar cards e tabelas.
- **Sombras**: apenas em elementos transitórios (dropdowns, modais, tooltips).
  - Sombra padrão: `0 4px 20px rgba(15, 23, 42, 0.08)`.

---

## Componentes

### Hierarquia de títulos

- O cabeçalho global identifica o módulo ativo, como `Portfólio`, `Limites` ou `Relatórios`.
- O primeiro painel não deve repetir o nome do módulo. Seu título deve descrever o conteúdo ou a ação, como `Resumo da carteira`, `Resumo mensal`, `Resumo do período` ou `Nova importação`.
- Títulos de painel usam linguagem curta, específica e orientada à tarefa.
- Esta regra se aplica também aos módulos agrupados no menu Gestão, evitando sequências visuais como `Portfólio` seguido imediatamente de `Portfólio`.

### Menu de navegação (Sidebar)

- **Gaps**: Grupos separados por `12px`. Itens do mesmo grupo separados por `4px` (`--spacing-xs`).
- **Botões (`.nav-button`)**: Altura mínima de `32px` para garantir densidade de dados sem comprometer a área de clique.
- **Hierarquia**: Títulos de grupos (ex: "Cadastro", "Gestão") devem ser concisos e agrupar itens logicamente.

### Botões

| Variante | Fundo | Texto |
|---|---|---|
| Primário | `--primary` | `--on-primary` (`#ffffff`) |
| Secundário | transparente | `--on-surface` com borda `--outline` |

### Modais de decisão

- Decisões financeiras, destrutivas ou de edição em cascata não devem usar `window.confirm()` ou `window.prompt()`.
- Use o helper reutilizável `decision-modal.js` para manter consistência visual, acessibilidade e textos acionáveis.
- Botões devem descrever a ação real, como `Apenas este lançamento`, `Este e os próximos`, `Excluir apenas este`, `Excluir este e os próximos` ou `Encerrar posição`.
- Evite escolhas ambíguas do tipo `OK`/`Cancelar` quando cada opção representa um comportamento de domínio.
- A ação de retorno deve ser nomeada como `Voltar` e deve abortar a operação sem efeitos colaterais.
- Formulários em modal devem agrupar os campos necessários em uma única etapa quando isso reduzir cliques, como no encerramento de posição do Portfólio.
- Opções que movimentam saldo financeiro adicional devem iniciar desmarcadas por padrão.

### Campos de input

- Borda padrão: 1px `--outline`.
- Foco: borda 2px `--primary`.
- Erro: borda `--error` com ícone auxiliar.

### Chips / Badges

| Variante | Cor | Uso |
|---|---|---|
| Neutro | `--surface-container` | Metadados gerais. |
| Laranja | `--secondary-container` | "Despesa", "Passivo", itens de interface. |
| Verde | `#10B981` | "Pago", "Ativo", status positivo. |
| Vermelho | `#EF4444` | "Em atraso", alerta crítico. |

### Cartões (cards)

- Fundo: `--surface-container-lowest` (`#ffffff`).
- Borda: 1px `--outline-variant`.
- Border radius: `--rounded-lg`.
- Cabeçalho separado por linha horizontal sutil (`--outline-variant`).

### Tabelas de dados

- Zebra striping: linha alternada com `--surface-container-low` em hover.
- Cabeçalhos de coluna: `label-md` em maiúsculas.
- **Colunas numéricas alinhadas à direita** com `font-variant-numeric: tabular-nums`.
- Notação de cores obrigatória:
  - Números negativos → vermelho `#EF4444`.
  - Saldos positivos → verde `#10B981`.
  - Lançamentos positivos (entradas) → preto `--on-surface`.

### Indicadores de status

- Ponto de 8px.
- Ativo / Operacional → verde `#10B981`.
- Inativo / Em atraso / Alerta → vermelho `#EF4444`.

### Formulários de lançamento

- Nas telas de Lançamentos de contas e Lançamentos de cartões, o formulário principal deve permanecer visível no desktop/tablet durante a rolagem da lista, usando comportamento sticky dentro da coluna esquerda.
- Quando o formulário for maior que a altura disponível, a rolagem deve acontecer dentro do próprio painel para manter cabeçalho e ações acessíveis sem ocultar a lista.
- Em mobile, o formulário volta ao fluxo normal da página para preservar área útil e evitar sobreposição com listas e controles.

---

## QA de tema

- Validar os temas `light` e `dark` navegando por Cockpit, Contas, Cartões, Lançamentos de contas, Lançamentos de cartões, Portfólio, Limites, Relatórios, Categorias, Importação e Preferências.
- Confirmar que o módulo ativo no menu mantém texto branco sobre fundo de destaque.
- Confirmar que painéis, tabelas, drawers, tooltips, campos e botões mantêm contraste legível nos dois temas.
- Confirmar que gráficos e barras usam `--chart-*` e permanecem visíveis em superfícies claras e escuras.
- Confirmar que o controle de Preferências alterna o tema sem recarregar a página e persiste após reload.
- Validar viewport mobile no módulo Preferências: controle de tema empilhado, sem overflow horizontal.

## Release e rollback

- O modo claro continua sendo o padrão quando não há preferência salva.
- A preferência fica apenas em `localStorage`; não há migração de banco, endpoint novo ou alteração de autenticação.
- Rollback visual simples: remover a chave `sistemaFinanceiro.theme` do `localStorage` ou selecionar `Claro` em Preferências.
- Rollback técnico: remover o bloco `[data-theme="dark"]`, o card de Preferências e o uso de `theme-utils.js`; o restante do app volta ao comportamento claro por tokens.

---

## Changelog

- `1.0` — 2026-06-29 — Consolidação do design original em tokens tabulados com frontmatter e wikilinks.
- `1.1` — 2026-06-30 — Regras de tokenização para preparação do modo escuro e paleta de gráficos documentadas.
- `1.2` — 2026-06-30 — Infraestrutura de aplicação de tema com `data-theme` e preferência local documentada.
- `1.3` — 2026-06-30 — Paleta de tokens do tema escuro documentada como override centralizado.
- `1.4` — 2026-07-01 — Controle de alternância claro/escuro em Preferências documentado.
- `1.5` — 2026-07-01 — Checklist de QA, release e rollback do tema documentados.
- `1.6` — 2026-07-08 — Hierarquia de títulos definida para impedir repetição entre o cabeçalho do módulo e o primeiro painel.
- `1.7` — 2026-07-09 — Diretrizes de espaçamento e compactação do menu de navegação documentadas.
- `1.8` — 2026-07-17 — Comportamento sticky dos formulários de lançamento em contas e cartões documentado.
- `2.0` — 2026-07-29 — Adicionados tokens semânticos acessíveis (`--color-success`, `--color-success-text`, `--color-warning`, `--color-warning-text`, `--color-error`, `--color-error-text`) com fallback e overrides de tema escuro para garantir contraste WCAG AA em gráficos e indicadores de status; regras de aplicação e pares texto/fundo documentados.
- `1.9` — 2026-07-20 — Padrão de modais de decisão definido para substituir prompts/confirms nativos em decisões financeiras e de cascata.

## Relacionados

- [[arquitetura]]
- [[specs/frontend-modularizacao]]
