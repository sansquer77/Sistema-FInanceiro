---
name: Precisão Institucional
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#434653'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#737685'
  outline-variant: '#c3c6d6'
  surface-tint: '#2156ca'
  primary: '#00328a'
  on-primary: '#ffffff'
  primary-container: '#0047bb'
  on-primary-container: '#afc1ff'
  inverse-primary: '#b3c5ff'
  secondary: '#a04100'
  on-secondary: '#ffffff'
  secondary-container: '#fe6b00'
  on-secondary-container: '#572000'
  tertiary: '#2b3b50'
  on-tertiary: '#ffffff'
  tertiary-container: '#425268'
  on-tertiary-container: '#b4c5df'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dbe1ff'
  primary-fixed-dim: '#b3c5ff'
  on-primary-fixed: '#00174a'
  on-primary-fixed-variant: '#003ea6'
  secondary-fixed: '#ffdbcc'
  secondary-fixed-dim: '#ffb693'
  on-secondary-fixed: '#351000'
  on-secondary-fixed-variant: '#7a3000'
  tertiary-fixed: '#d3e4fe'
  tertiary-fixed-dim: '#b7c8e1'
  on-tertiary-fixed: '#0b1c30'
  on-tertiary-fixed-variant: '#38485d'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  title-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-sm:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 14px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-max: 1280px
  gutter: 24px
---

## Marca e Estilo

A personalidade da marca é autoritária, sistemática e altamente técnica, projetada para finanças institucionais e gestão profissional de ativos. A interface do usuário (UI) deve evocar uma sensação de confiabilidade absoluta e clareza.

O estilo de design segue uma abordagem **Corporativa Moderna** com tendências **Minimalistas**. Prioriza a densidade de dados e a legibilidade em vez de elementos decorativos. Ao utilizar tipografia de alto contraste e uma grade (grid) estruturada, a interface permanece funcional e com aspecto premium. O interesse visual é gerado por meio do alinhamento preciso e do uso estratégico de cores categóricas em vez de elementos ilustrativos.

## Cores

A paleta é estritamente categorizada para evitar sobrecarga cognitiva em ambientes com grande volume de dados:

* **Primária (Azul Institucional):** Usada para todo o branding principal, ações primárias e estados ativos de navegação. Sinaliza estabilidade e intenção profissional.
* **Secundária (Laranja Vibrante):** Reservada **exclusivamente** para ícones e itens de interface. *Não* deve ser utilizada para valores numéricos de transações ou saldos.
* **Neutra:** Um tom de ardósia profundo usado para o texto principal e bordas estruturais para manter um ambiente sóbrio e de alto contraste.
* **Indicadores Semânticos e Numéricos:** * **Vermelho Puro (#EF4444):** Obrigatório para **todos os números negativos** em qualquer caso (tanto em saldos quanto em itens de lançamento/transações), além de alertas críticos do sistema.
    * **Verde Puro (#10B981):** Estritamente reservado para os números de **saldos positivos** e indicadores de status financeiro saudáveis.
    * **Preto:** Obrigatório para a exibição de números em **itens de lançamento positivos** (transações de entrada).
    * *Nota:* Não use as cores de status (Verde ou Vermelho) para botões gerais da interface do usuário ou ícones categóricos.

## Tipografia

Este sistema de design utiliza a fonte **Inter** em todos os níveis para aproveitar suas características neutras, sistemáticas e altamente legíveis.

* **Dados Numéricos:** Use figuras tabulares (`tnum`) para todos os valores financeiros para garantir o alinhamento vertical em listas e tabelas. Aplique rigorosamente a notação de cores (Vermelho para todos os negativos, Verde para saldos positivos, Preto para lançamentos positivos).
* **Hierarquia:** Use `label-md` em letras maiúsculas para cabeçalhos de seção e títulos de colunas de tabelas para fornecer uma base estrutural clara.
* **Peso:** Reserve os pesos em negrito (bold) para cabeçalhos principais e totais financeiros críticos. Pesos regulares são preferíveis para todo o texto instrucional para manter uma estética limpa e arejada.

## Layout e Espaçamento

O sistema emprega uma filosofia de **Grade Fixa** para desktop para manter o controle da densidade de dados, fazendo a transição para um modelo fluido em dispositivos móveis.

* **Desktop:** Grade de 12 colunas com largura máxima de 1280px, calhas (gutters) de 24px e margens laterais de 32px.
* **Tablet:** Grade de 8 colunas com margens laterais de 24px.
* **Mobile:** Grade fluida de 4 colunas com margens laterais de 16px.

Uma grade de linha de base estrita de 4px governa todo o ritmo vertical. Os componentes devem utilizar o preenchimento (padding) `md` (16px) ou `lg` (24px) para garantir que até mesmo as visualizações ricas em dados permaneçam fáceis de escanear e confortáveis.

## Elevação e Profundidade

A hierarquia visual é estabelecida principalmente por meio de **Camadas Tonais** e **Contornos de Baixo Contraste**.

* **Níveis de Superfície:** O fundo usa um tom de branco quebrado ou um cinza muito claro. Os cartões e os contêineres principais usam uma superfície branca pura.
* **Bordas:** Use bordas sólidas de 1px em um tom neutro suave para definir limites em vez de sombras pesadas.
* **Sombras:** Aplique sombras apenas em elementos transitórios, como menus suspensos (dropdowns), modais ou dicas de ferramentas (tooltips). Use uma única sombra "Ambiente" altamente difusa: `0 4px 20px rgba(15, 23, 42, 0.08)`.
* **Hierarquia de Profundidade:** Botões de ação flutuantes e modais ficam na elevação mais alta, enquanto as tabelas de dados e feeds estão fixados à superfície da página.

## Formas

A linguagem das formas é estruturada e profissional. Um raio de canto **Arredondado** padrão (0.5rem) é aplicado a todos os componentes principais da interface do usuário, como botões, campos de entrada e cartões.

* **Componentes Pequenos:** Use `rounded-sm` (0.25rem) para caixas de seleção, tags e selos.
* **Contêineres:** Cartões de dashboard grandes ou sobreposições de modais usam `rounded-lg` (1rem) para criar uma suavização sutil na estética institucional.
* **Estados Interativos:** Mantenha os mesmos raios de canto em todos os estados (hover, ativo, desativado) para garantir a estabilidade da interface.

## Componentes

* **Botões:** Os botões primários usam o fundo Azul Institucional com texto branco. Os botões secundários usam um contorno neutro.
* **Campos de Entrada:** Use bordas neutras de 1px que engrossam para 2px de Azul Primário no estado de foco (focus). Os estados de erro para validação usam o Vermelho Semântico para a borda e um pequeno ícone auxiliar.
* **Chips/Badges (Etiquetas/Selos):**
    * *Neutros:* Para metadados gerais.
    * *Laranja:* Apenas para componentes da interface, botões ou ícones categorizados como "Despesa" ou "Passivo".
    * *Verde (Status):* Especificamente para "Pago", "Ativo" ou status de lucro.
* **Cartões:** Fundo branco, borda neutra de 1px e cantos `rounded-lg`. Os cabeçalhos dentro dos cartões devem ser separados por uma linha horizontal sutil.
* **Tabelas de Dados:** Use listras alternadas (zebra-striping) ao passar o mouse (hover). Os cabeçalhos das colunas usam a tipografia `label-md`. Alinhe à direita todas as colunas numéricas e de moeda para garantir o alinhamento decimal, respeitando a notação de cores rigorosa (Vermelho para negativos, Verde para saldos positivos, Preto para lançamentos positivos).
* **Indicadores de Status:** Pequenos pontos de 8px. Use Vermelho Semântico para "Sistema Fora do Ar" ou "Em Atraso" e Verde Semântico para "Sistema Operacional".