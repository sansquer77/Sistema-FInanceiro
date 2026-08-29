---
tipo: design
area: meta
status: implementado
versao: 3.9
atualizado: 2026-08-29
relacionados:
  - "[[arquitetura]]"
  - "[[specs/frontend-modularizacao]]"
tags: [design, meta]
aliases: ["Design System", "Tokens Visuais", "Precisão Institucional"]
---

# Design System — Precisão Institucional

> [!info] Status
> **implementado** · área: `meta` · atualizado em 2026-08-29 · relacionados: [[arquitetura]], [[specs/frontend-modularizacao]]

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
| `--surface` | `#ffffff` | Fundo geral da página (branco no tema claro; `#101114` no escuro). |
| `--surface-container-lowest` | `#ffffff` | Cartões e containers principais. |
| `--surface-container-low` | `#f2f3ff` | Fundo de seções secundárias. |
| `--surface-container` | `#eaedff` | Itens de lista em hover. |
| `--surface-container-high` | `#e2e7ff` | Bordas internas de tabelas. |
| `--surface-dim` | `#d2d9f4` | Fundos desabilitados / inativos. |

> [!note] Fundo da página
> No tema claro o fundo da tela é **branco** (`#ffffff`), no escuro é o tom base sólido (`#101114`). A separação entre as seções do layout é feita pelos **cards** (fundo de card + borda `1px` em `--outline-variant`), nunca por tonalidades diferentes no fundo da página. Evite reintroduzir fundos coloridos na página (ex.: lilás) para hierarquizar seções: a hierarquia deve vir dos cards, do espaçamento e do agrupamento.

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
- Linhas de referência neutras em gráficos (ex.: média) usam o token `--chart-average-line` (cinza `#9aa3b8` no claro, branco `#ffffff` no escuro) e nunca `--secondary`/`--secondary-container`.
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

- **Superfícies**: separação de seções por cards com borda (`1px` em `--outline-variant`) sobre fundo neutro da página (branco no claro, escuro sólido no escuro), não por sombras nem por fundos coloridos.
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
- Itens de menu não devem repetir o mesmo rótulo em grupos diferentes quando a intenção for distinta; prefira nomes orientados à tarefa, como **Minhas Contas**, **Meus Cartões**, **Extrato de Contas** e **Fatura de Cartões**.
- O título exibido no cabeçalho da página deve reforçar o mesmo significado do item acionado no menu, evitando que a navegação volte a depender apenas do grupo pai para desambiguação.

### Botões

| Variante | Fundo | Texto |
|---|---|---|
| Primário | `--primary` | `--on-primary` (`#ffffff`) |
| Secundário | transparente | `--on-surface` com borda `--outline` |

### Ações e validação em formulários

- O rodapé usa `.form-actions`: ação primária primeiro, ações secundárias em seguida e ação destrutiva isolada no extremo oposto.
- Em telas estreitas, as ações ocupam a largura disponível; a destrutiva recebe separação vertical, preservando a ordem de leitura.
- A ação primária descreve o resultado (`Salvar conta`, `Importar lançamentos`), evitando rótulos vagos como `OK`.
- Durante o envio, o formulário usa `aria-busy="true"`, desabilita temporariamente seus controles e mostra `Aguarde...` no submit sem perder estados condicionais anteriores.
- Erros de restrição HTML aparecem imediatamente abaixo do campo, usam o token de erro e são vinculados por `aria-describedby`; corrigir o valor remove o erro sem reiniciar o formulário.

### Cabeçalho global, filtros e tabelas

- O `.topbar` é sticky em todos os módulos autenticados, usa fundo sólido `--bg`, linha inferior e `isolation: isolate`; conteúdo nunca aparece por transparência atrás dele.
- Toolbars de busca e filtro usam `.filter-toolbar`, com fundo de superfície baixa, borda `--outline-variant`, raio padrão e espaçamento de 8–12px.
- Filtros empilham em uma coluna abaixo de 860px; controles segmentados dividem a largura disponível quando isso melhora a leitura.
- Tabelas ficam em um wrapper com `overflow: auto`, borda e fundo de painel. Não reduza artificialmente colunas monetárias para caber no mobile: preserve `min-width` e permita rolagem horizontal.
- Cabeçalhos de coluna permanecem sticky dentro do wrapper, usam fundo opaco, caixa alta e contraste secundário. Linhas recebem hover discreto sem alterar cores financeiras.
- Valores monetários e numéricos ficam alinhados à direita e usam figuras tabulares; a primeira coluna textual permanece alinhada à esquerda.
- Abas principais que trocam painéis longos — Cockpit, Portfólio e Preferências — permanecem sticky logo abaixo do `.topbar`, com superfície opaca, borda e continuidade visual.
- Elementos sticky internos usam o offset estrutural do cabeçalho (`74px`, acrescido do respiro necessário), nunca `top: 0` quando disputam a mesma coluna de conteúdo.

### Busca global e preservação de contexto

- O cabeçalho oferece um acionador compacto de busca global; em desktop exibe rótulo e atalho `/`, e em telas menores reduz-se ao atalho sem competir com o título.
- A busca abre em `<dialog>` nativo, com campo rotulado, resultados navegáveis por teclado e indicação do tipo de resultado.
- O resultado sempre informa título, contexto secundário e domínio (`Módulo`, `Conta`, `Cartão`, `Lançamento`, `Fatura`, `Portfólio` ou `Classificação`).
- A busca é local aos dados já carregados e não promete cobertura de períodos ainda não consultados.
- Trocas de módulo preservam filtros, abas, períodos e posição de rolagem durante a sessão; uma busca contextual pode preparar o período e a entidade do resultado selecionado.

### Densidade configurável

- **Confortável** é o padrão e mantém os espaçamentos-base do design system.
- **Compacto** usa `data-density="compact"` e reduz apenas espaçamentos, paddings, gaps e altura de linhas; não reduz a fonte-base nem altera cores semânticas.
- Controles compactos mantêm altura mínima de 34px, foco visível e espaço suficiente para toque deliberado.
- A preferência é local ao navegador (`sistemaFinanceiro.density`) e deve ser aplicada antes do CSS para evitar salto de layout.
- A compactação prioriza painéis, grids, formulários, listas, toolbars e tabelas; modais destrutivos e mensagens de erro preservam o respiro necessário.

### Estados loading, erro, vazio e informação

- Todo estado localizado usa `.ui-state` com ícone, título curto e mensagem; `.empty-state` permanece como alias compatível durante a migração.
- `loading`: indicador animado, título **Carregando**, `role="status"`, `aria-live="polite"` e `aria-busy="true"`.
- `error`: ícone de alerta, título **Não foi possível concluir**, `role="alert"` e borda/texto de erro; nunca depender apenas do vermelho.
- `empty`: ícone neutro, título **Nada por aqui ainda** e orientação sobre cadastrar, selecionar ou ajustar filtros quando aplicável.
- `info`: ícone informativo e mensagem neutra para indisponibilidade contextual que não representa falha.
- Estados não deslocam controles globais, preservam o tamanho da região quando `compact` e respeitam `prefers-reduced-motion` no indicador de carregamento.

### Overlays, feedback e superfícies operacionais

- Modais, dialogs e drawers compartilham `aria-modal`, foco confinado, Escape, restauração de foco, cabeçalho e botão de fechar.
- Sucesso usa toast temporário no canto inferior; erro continua inline e persistente.
- Cabeçalhos de cards agrupam ações e exibem última atualização em texto auxiliar quando houver recarga explícita.
- Tabelas ordenáveis exibem indicador no cabeçalho, primeira coluna sticky e contagem; filtros ativos usam chips removíveis.
- Formulários extensos recolhem detalhes opcionais e mostram resumo não financeiro dos campos preenchidos antes do submit.

### Abas (tabs)

Padrão único em toda a aplicação, conforme o modelo usado no menu **Preferências**:

- **Estrutura**: contêiner `flex` com `gap: 8px` e `flex-wrap: wrap` — sem trilho/painel de fundo, sem bordas agrupadas nem contêiner escuro.
- **Botão (`tab`)**: pílula — `border-radius: 999px`, borda `1px solid --outline`, fundo do card (`--surface-container-lowest`), texto `--on-surface-variant`, padding `6px 14px`/`8px 16px`.
- **Hover**: texto `--on-surface` e borda `--outline-strong`.
- **Ativo**: fundo `--accent-container`, borda `--accent`, texto `--on-surface` com `font-weight: 600`. Nunca usar `box-shadow` para marcar o estado ativo.
- **Acessibilidade**: `role="tablist"` no contêiner, `role="tab"` + `aria-selected` nos botões e `aria-controls` apontando ao painel; painel com `role="tabpanel"`.
- O mesmo padrão vale para o seletor de Acesso (login), as abas do Cockpit, as abas de Relatórios e quaisquer novas abas do produto.

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
- Textos explicativos longos em formulários densos devem ficar sob demanda em helper discreto (`?`, popover ou disclosure equivalente), preservando o alinhamento dos campos.
- Quando um campo muda de significado conforme uma escolha anterior, prefira microcopy dinâmica no rótulo e placeholder em vez de parágrafos permanentes.
- Opções curtas e mutuamente exclusivas, como modalidades de Renda Fixa, podem usar segmented control/radio chips para reduzir cliques e manter todas as alternativas visíveis.
- Atalhos de preenchimento devem ser chips compactos, neutros e opcionais; eles aceleram o input sem substituir campos explícitos.
- Previews de configuração devem ser badges discretos e textuais, usados para confirmar entendimento do usuário sem introduzir nova regra financeira.

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
- Colunas de valor, percentual e estado devem ter largura previsível; a coluna descritiva/categoria ocupa o espaço flexível principal.
- Estados textuais em tabelas densas devem manter alinhamento consistente entre linhas, sem molduras, fundos, bordas ou chips quando a própria cor/texto já comunicar o estado.
- Evite classes semânticas genéricas em linhas ou containers (`danger`, `warning`, `success`) quando puderem colidir com estilos globais; prefira classes escopadas ao componente ou estados neutros como `over`, `attention`, `on-track`.
- Notação de cores obrigatória:
  - Números negativos → vermelho `#EF4444`.
  - Saldos positivos → verde `#10B981`.
  - Lançamentos positivos (entradas) → preto `--on-surface`.

### Abas e painéis analíticos

- Abas do Cockpit devem seguir a ordem de leitura: **Situação**, **Tendências** e **Saúde Financeira**.
- Painéis analíticos com tabelas e cards de leitura, como Tendências, devem priorizar fluxo vertical em largura total antes de dividir conteúdo em colunas, especialmente em telas intermediárias como MacBook Air.
- A densidade visual deve ser obtida por alinhamento, largura previsível e tipografia tabular, não por redução extrema de legibilidade.

### Movimento e transições

- Transições entre módulos do dashboard devem ser curtas, discretas e funcionais, suavizando a troca de contexto sem competir com os dados financeiros.
- Use View Transitions API como melhoria progressiva para navegação entre módulos, preservando fallback instantâneo quando indisponível.
- Respeite `prefers-reduced-motion: reduce`: nesse caso, a navegação não deve aplicar animação.
- A duração recomendada para transições globais de visão é de aproximadamente `160ms`, com easing suave (`ease-out`), evitando efeitos decorativos longos.
- Trocas entre subtabs de um mesmo módulo podem usar a mesma duração de aproximadamente `160ms`, combinando apenas opacidade e pequeno deslocamento vertical; estados de atualização preservam o conteúdo anterior com atenuação discreta e `aria-busy`, sem bloquear a navegação.
- Todos os conjuntos de abas funcionais devem adotar foco roving: somente a aba ativa participa da ordem Tab; setas movem entre vizinhas, Home/End alcançam extremos e a seleção acompanha o foco.
- Regiões que aguardam dados devem usar `aria-busy` e atenuação moderada apenas no conteúdo afetado, mantendo navegação, cabeçalhos e controles disponíveis.
- No Cockpit, a hierarquia executiva posiciona alertas antes dos KPIs, mantém Saldos/Portfólio expandidos e usa `details/summary` para conteúdo secundário; título e controles sticky devem usar superfícies/tokens existentes, sem sombra ou cor decorativa nova.
- Cabeçalhos sticky que cobrem dados financeiros devem usar superfície opaca (`--bg` ou `--panel`), nunca `--panel-translucent` ou desfoque; blocos sticky empilhados devem ser visualmente contíguos para impedir vazamento do conteúdo rolado pelos intervalos.

### Diagnóstico visual e disclosure progressivo

- Indicadores executivos de diagnóstico, como o Score de Saúde Financeira, podem usar visualização tipo gauge/velocímetro quando a leitura instantânea for mais importante que a explicação textual completa.
- Gauges devem preservar escala textual explícita, valor central em algarismos tabulares e legenda das faixas, sem depender exclusivamente de cor.
- Cards de diagnóstico com explicações longas devem preferir disclosure progressivo (`details/summary` ou equivalente acessível): fechado para síntese, aberto para métricas e orientação.
- Zonas de saúde financeira usam quatro cores semânticas: vermelho para crítico, laranja para atenção/vulnerável, amarelo para moderado/em construção e verde para excelente/sólido. Essas cores são restritas a diagnóstico/estado, não a botões genéricos.

### Indicadores de status

- Ponto de 8px.
- Ativo / Operacional → verde `#10B981`.
- Inativo / Em atraso / Alerta → vermelho `#EF4444`.

### Modo Privacidade

- O botão global de privacidade deve ficar no cabeçalho superior como ação circular discreta, com estado e rótulo acessível.
- Valores monetários mascaráveis usam `.money-value` ou `.privacy-mask`.
- Em `:root[data-privacy="true"]`, valores monetários usam máscara textual leve (`color: transparent` + `text-shadow`), transição curta e `user-select: none`.
- No hover/foco do valor individual, a cor volta a `inherit` e a sombra é removida para permitir consulta rápida sem desligar o modo global.
- A máscara não deve alterar largura, alinhamento ou densidade dos cards/tabelas; a estrutura visual deve permanecer estável.

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

- `3.9` — 2026-08-29 — Contratos unificados para overlays, toast, cabeçalhos/atualização, tabelas/filtros e formulários progressivos.
- `3.8` — 2026-08-29 — Estados loading/erro/vazio/info padronizados com estrutura, semântica ARIA, tons e orientação contextual compartilhados.
- `3.7` — 2026-08-28 — Densidade configurável documentada com modos Confortável/Compacto, persistência local e limites mínimos de legibilidade/interação.
- `3.6` — 2026-08-28 — Busca global e preservação de contexto definidas com diálogo nativo, atalho `/`, resultados tipados e restauração de rolagem por módulo.
- `3.5` — 2026-08-28 — Abas de Portfólio e Preferências tornam-se sticky; offsets dos elementos sticky internos passam a respeitar o cabeçalho global.
- `3.4` — 2026-08-28 — Cabeçalho sticky vira padrão global; adicionados contratos unificados para toolbars de filtro e tabelas responsivas com cabeçalho sticky.
- `3.3` — 2026-08-28 — Definida hierarquia de ações e formulários: primária primeiro, destrutiva separada, feedback inválido contextual e envio ocupado sem perda de estado.
- `3.2` — 2026-08-28 — Cabeçalhos sticky sobre dados passam a exigir fundo opaco e continuidade visual; corrigida a mistura do conteúdo rolado sob título/abas do Cockpit.
- `3.1` — 2026-08-28 — Layout executivo do Cockpit padronizado com alertas prioritários, KPIs compactos, cabeçalhos sticky e disclosure progressivo persistente para seções secundárias.
- `3.0` — 2026-08-28 — Padrão de fluidez ampliado a todos os conjuntos de abas analíticas, com foco roving acessível e estados ocupados localizados que preservam controles e contexto.
- `2.9` — 2026-08-28 — Movimento interno do Cockpit padronizado: subtabs com transição curta de opacidade/deslocamento, atualização localizada com conteúdo preservado e respeito obrigatório à redução de movimento.
- `2.8` — 2026-08-09 — Modo Privacidade passa a usar máscara textual leve no lugar de `filter: blur()` em massa, mantendo revelação em hover/foco e preservando alinhamento.
- `2.7` — 2026-08-08 — Fundo da página torna-se branco no tema claro (e escuro sólido no escuro) com separação de seções pelos cards (borda 1px); padronizado o componente de **Abas** como pílulas com borda `--outline`, ativo em `--accent-container` + `--accent` (modelo do menu Preferências), sem trilho nem sombras no estado ativo.
- `2.6` — 2026-08-02 — Documentado padrão do Modo Privacidade com botão global, valores `.money-value`/`.privacy-mask`, Glass Blur e revelação em hover/foco.
- `2.5` — 2026-08-02 — Documentado padrão de redução de ruído visual em formulários densos com helper sob demanda, microcopy dinâmica, segmented controls, presets e previews compactos.
- `2.4` — 2026-08-02 — Documentado padrão premium para diagnóstico visual com gauge, zonas semânticas e cards expansíveis acessíveis.
- `2.3` — 2026-08-02 — Documentado padrão de movimento para transições de visão com View Transitions API, fallback e respeito a redução de movimento.
- `2.2` — 2026-08-02 — Documentada regra de desambiguação dos nomes do menu lateral e alinhamento entre item de navegação e título da página.
- `2.1` — 2026-08-02 — Documentadas regras para tabelas densas, estados textuais sem moldura, distribuição de colunas e ordem das abas analíticas do Cockpit.
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
