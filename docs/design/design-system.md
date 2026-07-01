---
tipo: design
area: meta
status: implementado
versao: 1.2
atualizado: 2026-06-30
relacionados:
  - "[[arquitetura]]"
  - "[[specs/frontend-modularizacao]]"
tags: [design, meta]
aliases: ["Design System", "Tokens Visuais", "Precisão Institucional"]
---

# Design System — Precisão Institucional

> [!info] Status
> **implementado** · área: `meta` · atualizado em 2026-06-30 · relacionados: [[arquitetura]], [[specs/frontend-modularizacao]]

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

### Botões

| Variante | Fundo | Texto |
|---|---|---|
| Primário | `--primary` | `--on-primary` (`#ffffff`) |
| Secundário | transparente | `--on-surface` com borda `--outline` |

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

---

## Changelog

- `1.0` — 2026-06-29 — Consolidação do design original em tokens tabulados com frontmatter e wikilinks.
- `1.1` — 2026-06-30 — Regras de tokenização para preparação do modo escuro e paleta de gráficos documentadas.
- `1.2` — 2026-06-30 — Infraestrutura de aplicação de tema com `data-theme` e preferência local documentada.

## Relacionados

- [[arquitetura]]
- [[specs/frontend-modularizacao]]
