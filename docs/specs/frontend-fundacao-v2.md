---
tipo: spec
area: frontend-v2
status: em-implementacao
versao: 0.9
atualizado: 2026-08-31
relacionados:
  - "[[frontend-modularizacao]]"
  - "[[../adr/0002-modularizacao-frontend]]"
  - "[[../adr/0013-dependencias-frontend-v2]]"
  - "[[../design/design-system]]"
  - "[[relatorios]]"
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[investimentos-portfolio]]"
  - "[[efeito-borboleta]]"
tags: [spec, "area/frontend-v2", "status/em-implementacao"]
aliases: ["Fundação visual da v2", "Gráficos, máscaras, Command Palette e virtualização"]
---

# Fundação do frontend v2

> [!info] Status
> **em-implementacao** · área: `frontend-v2` · atualizado em 2026-08-31 · relacionados: [[frontend-modularizacao]], [[../adr/0013-dependencias-frontend-v2]], [[../design/design-system]], [[relatorios]], [[lancamentos]], [[cartoes]], [[investimentos-portfolio]], [[efeito-borboleta]]

## Problema

Os gráficos atuais foram construídos em diferentes módulos com SVG/HTML próprios, campos monetários e datas não compartilham uma experiência única de digitação, a busca global não atua como lançador de ações e listas extensas podem manter linhas demais no DOM. A v2 precisa de primitives compartilhadas que elevem consistência, acessibilidade e desempenho sem mover regras financeiras para o frontend nem criar build step.

## Usuário

Usuário que acompanha muitos lançamentos, faturas, operações ou posições e precisa interpretar gráficos, preencher formulários e navegar rapidamente pelo app usando mouse ou teclado.

## Jornada

### Gráficos

1. O usuário abre Cockpit, Lançamentos, Cartões, Relatórios, Portfólio, Saúde Financeira ou Efeito Borboleta.
2. O módulo fornece ao adaptador compartilhado somente séries e metadados já calculados pelo backend ou pelo contrato de apresentação existente.
3. O gráfico usa tokens do tema, tooltip monetário, legenda, foco e redimensionamento consistentes.
4. Ao trocar tema, período, filtro ou dados, a instância é atualizada ou destruída sem deixar SVG, listeners ou observadores órfãos.

### Máscaras

1. Ao focar valor monetário, o usuário digita na convenção local e vê separadores coerentes com a moeda do campo.
2. Ao focar uma data textual prevista pela tela, recebe assistência de formato e limites de calendário.
3. O formulário entrega aos parsers atuais o valor não mascarado/canônico; o backend continua como autoridade de validação.

### Command Palette

1. O usuário pressiona `Cmd+K` no macOS ou `Ctrl+K` nas demais plataformas.
2. Uma palette modal apresenta comandos agrupados e pesquisa incremental normalizada.
3. Setas mudam a opção ativa, Enter executa, Escape fecha e o foco retorna ao elemento anterior.
4. Comandos navegam para módulos, iniciam ações seguras ou focam buscas; ações destrutivas nunca são executadas sem a confirmação de domínio existente.

### Lista virtualizada

1. O usuário abre uma coleção acima do limiar configurado.
2. A lista preserva a altura total aparente, mas renderiza apenas itens visíveis e uma margem de overscan.
3. Durante a rolagem, a janela é recalculada e os espaçadores mantêm a posição do scrollbar.
4. Busca, filtros, ordenação, destaque e navegação para um item continuam usando os índices do conjunto filtrado completo.

## Dados e contratos de apresentação

### Adaptador de gráficos

- `chart_id`: identificador estável da instância.
- `type`: tipo aprovado (`line`, `area`, `bar`, `donut` ou `radialBar` quando compatível com a versão fixada).
- `series`: valores numéricos já calculados; dinheiro mantém a unidade definida pelo payload e nunca é recalculado pela biblioteca.
- `categories`/`x`: categorias ou datas do eixo.
- `currency`: moeda usada apenas para formatação.
- `semantic_role`: receita, despesa, saldo, benchmark, simulado ou neutro; resolve cores por tokens.
- `empty_message`: estado vazio fora do canvas/SVG do gráfico.

### Máscaras

- `data-mask="money"`: campo monetário associado à moeda efetiva do formulário.
- `data-mask="date"`: campo textual de data quando o input nativo não for adequado ao fluxo.
- `rawValue`: valor sem decoração, convertido pelos parsers compartilhados existentes.
- A máscara não altera centavos persistidos, taxa de câmbio, sinal ou timezone.

### Comandos

- `id`: identificador estável.
- `label`: texto visível.
- `keywords`: termos locais de busca.
- `group`: Navegação, Lançamentos, Gestão ou Usuário.
- `enabled(context)`: disponibilidade pelo estado atual.
- `run(context)`: ação que reutiliza callbacks existentes.

### Virtualização de altura fixa

- `totalCount`: quantidade do conjunto já filtrado/ordenado.
- `rowHeight`: altura estável por modo de densidade.
- `viewportHeight`: altura visível do contêiner.
- `scrollTop`: deslocamento vertical atual.
- `overscan`: linhas adicionais antes e depois da janela, com padrão inicial de 5.
- `startIndex = max(0, floor(scrollTop / rowHeight) - overscan)`.
- `visibleCount = ceil(viewportHeight / rowHeight) + 2 * overscan`.
- `endIndex = min(totalCount, startIndex + visibleCount)`.
- `paddingTop = startIndex * rowHeight`.
- `paddingBottom = max(0, (totalCount - endIndex) * rowHeight)`.

## Regras

### Dependências e offline

- ApexCharts 4.7.0 e IMask devem ser arquivos locais, fixados e acompanhados de licença/hash; nenhuma CDN participa do runtime.
- Views não acessam diretamente globais das bibliotecas; usam `chart-adapter.js` e `input-mask.js` ou nomes equivalentes.
- O pacote React `cmdk` não integra o runtime; a palette nativa segue o contrato definido no [[../adr/0013-dependencias-frontend-v2]].
- A falha ao carregar uma melhoria visual não pode impedir login, lançamentos ou acesso aos dados; gráficos exibem estado de erro e máscaras degradam para os inputs/parsers atuais.

### Gráficos

- Migrar progressivamente os gráficos existentes, um fluxo por vez, preservando o payload e o significado financeiro.
- Cores vêm do design system; receita, despesa, saldo negativo, benchmark e simulação não podem trocar de semântica entre telas.
- Tooltip e labels usam formatadores compartilhados, nunca divisão implícita de centavos.
- Todo gráfico oferece alternativa textual ou tabular equivalente aos valores essenciais.
- Animações de gráficos ficam desativadas em todos os temas e navegadores, inclusive transições iniciais, graduais e de atualização; views não podem reativá-las. Tooltips, filtros, séries e demais interações permanecem disponíveis conforme cada tela. Resize não recria instâncias em loop.
- Instâncias são destruídas ao substituir contêiner ou desmontar view.
- O adaptador mantém um único observador de remoções e mudanças do atributo `hidden`. Gráficos em contêineres desconectados são descartados; gráficos dentro de telas, abas ou drawers ocultos são destruídos, preservando somente sua última configuração de apresentação para recriação ao retornar, sem novas consultas. Atualizações recebidas enquanto ocultos substituem essa configuração sem criar instâncias. Logout descarta também as configurações preservadas.
- Impressão/exportação mantém os demonstrativos atuais; não depende de recurso premium do ApexCharts.

### Máscaras

- Máscara auxilia digitação, mas campos continuam submetendo contrato compatível com os parsers existentes.
- Colagem, seleção, edição no meio do valor, valores negativos permitidos e casas decimais da moeda precisam ser testados.
- Datas impossíveis não se tornam válidas apenas por estarem completas visualmente.
- Inputs nativos `type="date"` permanecem quando oferecem melhor acessibilidade e compatibilidade; IMask não os substitui indiscriminadamente.
- Toda instância de máscara é destruída antes de reinicializar o formulário ou remover o campo.

### Command Palette

- `Cmd+K`/`Ctrl+K` não dispara quando o navegador ou sistema reservar a combinação de forma irremovível; o botão visível no cabeçalho permanece alternativa.
- A palette usa `role="dialog"`, nome acessível, foco confinado, `aria-activedescendant` ou padrão equivalente e anúncio do número de resultados.
- Comandos não duplicam regras de autorização ou domínio; delegam às ações existentes.
- A palette não pesquisa descrições financeiras além dos dados já carregados e nunca envia consulta externa.
- Comandos destrutivos abrem o modal de confirmação correspondente; não executam exclusão diretamente por Enter.
- `/` continua abrindo a busca global; a coexistência dos atalhos deve ser documentada na Central de Ajuda.

### Virtualização

- Aplicar inicialmente a lançamentos de conta, rankings de Relatórios e posições do Portfólio quando a coleção filtrada exceder 200 itens. Fatura de cartão e Histórico de Operações permanecem como próxima etapa, pois usam estruturas próprias que exigem preservação adicional de semântica.
- Listas abaixo do limiar permanecem no render simples para reduzir complexidade.
- A primeira versão exige altura fixa por modo Confortável/Compacto; conteúdo variável deve ser truncado/limitado conforme o design existente ou ficar fora da virtualização.
- O cálculo de scroll é agendado no máximo uma vez por frame com `requestAnimationFrame`.
- O item focado ou destacado por navegação programática deve ser trazido à janela antes de receber foco.
- O índice usado por ações pertence ao conjunto filtrado completo, não ao fragmento atualmente renderizado.
- Mudança de filtro, ordenação, densidade ou tamanho do contêiner recalcula métricas sem salto indevido.
- Acessibilidade deve informar tamanho/posição da coleção quando a semântica de tabela/lista exigir (`aria-rowcount`, `aria-rowindex` ou equivalente).

## API e dados

- Nenhuma rota ou tabela nova.
- Regras financeiras e agregações permanecem no backend.
- Novos módulos previstos: adaptador de gráficos, adaptador de máscaras, Command Palette e virtualizador de lista.
- Novos assets previstos: ApexCharts 4.7.0, IMask fixado, licenças e inventário de terceiros.

## Critérios de aceite

1. Dado o app instalado sem internet, quando qualquer tela com gráfico abre, então o gráfico carrega somente assets locais.
2. Dado tema claro ou escuro, quando um gráfico renderiza, então cores, texto, grid e tooltip permanecem legíveis e semanticamente coerentes.
3. Dado usuário com redução de movimento ativa, quando séries mudam, então o gráfico atualiza sem animação não essencial.
4. Dado gráfico indisponível ou sem dados, quando a tela abre, então apresenta estado acessível e os dados essenciais continuam disponíveis em texto ou tabela.
5. Dado campo monetário, quando o usuário digita ou cola um valor válido, então vê máscara local e o formulário preserva o valor numérico esperado pelos parsers atuais.
6. Dado campo de data mascarado, quando o usuário informa data impossível, então o formulário não a aceita como válida.
7. Dado macOS, quando o usuário pressiona `Cmd+K`, então a Command Palette abre e posiciona foco na busca.
8. Dado Windows/Linux, quando o usuário pressiona `Ctrl+K`, então a mesma palette abre.
9. Dado palette aberta, quando o usuário usa setas, Enter e Escape, então seleção, execução, fechamento e restauração de foco funcionam sem mouse.
10. Dado comando destrutivo, quando executado pela palette, então abre confirmação e não altera dados diretamente.
11. Dado palette aberta, quando o usuário pesquisa, então somente comandos/dados locais permitidos são filtrados e nada é enviado à rede.
12. Dado coleção com até 200 itens, quando exibida, então usa renderização simples.
13. Dado coleção acima de 200 itens, quando exibida, então o DOM contém somente a janela visível mais overscan.
14. Dado lista virtualizada, quando o usuário rola, então scrollbar, posição visual e ordem permanecem coerentes com o conjunto completo.
15. Dado filtro ou ordenação alterado, quando a lista virtualizada recalcula, então ações e destaques apontam para o item correto do conjunto filtrado.
16. Dado mudança entre densidade Confortável e Compacto, quando a lista está virtualizada, então altura e janela são recalculadas sem sobreposição de linhas.
17. Dado atualização ou desmontagem repetida de gráfico/máscara/lista, quando inspecionada, então não acumula instâncias, listeners ou observadores órfãos.
18. Dado pacote distribuível, quando inspecionado, então contém versões, hashes e licenças das dependências vendorizadas e não contém `node_modules`.
19. Dado drawer de rentabilidade do Portfólio, quando aberto, então pertence ao nível global de overlays e permanece acima dos cabeçalhos sticky.
20. Dado duas categorias de relatório abertas em sequência, quando as respostas chegam fora de ordem, então somente a categoria mais recente atualiza o gráfico.
21. Dado histórico de conta ou cartão, quando o gráfico Apex renderiza, então permanece contido na área de 92 px reservada ao plot.
22. Dado histórico mensal de conta ou cartão, quando o gráfico renderiza, então cada marcador fica horizontalmente centralizado com o card do mês correspondente.
23. Dado histórico mensal de conta ou cartão, quando o usuário aponta um marcador, então nenhum tooltip redundante é exibido, pois o card mensal correspondente já apresenta o valor e seu contexto.
24. Dado um gráfico ApexCharts cujo elemento é removido ou substituído no DOM, quando o ciclo de mutações termina, então sua instância é destruída e deixa de reter listeners, observadores ou estruturas internas da biblioteca.
25. Dado qualquer gráfico, quando renderizado mesmo com animações solicitadas pela view, então o adaptador desativa animações iniciais, graduais e dinâmicas sem modificar séries, formatadores ou a configuração de tooltip.

26. Dado um gráfico em tela, aba ou drawer oculto por `hidden`, quando a visibilidade muda, então sua instância é destruída e só é recriada ao reaparecer, com os últimos dados disponíveis e sem consulta adicional.
27. Dado um gráfico suspenso, quando seu contêiner é removido ou a sessão termina, então sua configuração é descartada e não reaparece na próxima sessão.

## Pendências

> [!question] Pendências
> Nenhuma pendência funcional conhecida. A versão exata do IMask será fixada na implementação após validação de compatibilidade nos navegadores mínimos dos pacotes.

## Fora de escopo

- Introduzir React, Vue, bundler, transpiler ou build step no frontend.
- Usar recursos premium/licenciados das versões atuais do ApexCharts.
- Virtualização de linhas com altura arbitrária na primeira entrega.
- Mover cálculos de saldo, fatura, score, rentabilidade ou simulação para JavaScript.
- Substituir tabelas necessárias para impressão por gráficos sem alternativa textual.

## Plano de implementação

- [x] Suspender gráficos sob ancestrais `hidden`, restaurar configurações recentes e limpar na sessão; testar ciclos, respostas tardias e descarte. Fecha: critérios 17, 24, 26 e 27 no adaptador, com instâncias simuladas. Memória real no Safari continua sujeita à validação manual.
- [x] Desativar animações no adaptador compartilhado e testar precedência, preservação das interações e descarte em ciclos repetidos. Fecha: critérios 3 e 25; regressão do adaptador para 17 e 24. Teste usa instâncias simuladas, não mede memória real. A estabilização de memória no Safari exige validação manual.
- [x] Passo 1 — adicionar inventário/licenças e assets vendorizados, com testes de ausência de CDN e `node_modules`. Fecha: critérios 1 e 18.
- [x] Passo 2 — criar adaptador ApexCharts com tokens, formatadores, lifecycle, fallback e acessibilidade; migrar um gráfico piloto. Fecha: critérios 1 a 4 e 17.
- [x] Passo 3 — migrar progressivamente gráficos de Lançamentos, Cartões, Cockpit/Relatórios, Portfólio e Efeito Borboleta, com testes de equivalência por fluxo. Fecha: critérios 2 a 4.
- [ ] Passo 4 — criar adaptador IMask e aplicar por tipo de campo, preservando parsers e validação backend. Fecha: critérios 5, 6 e 17.
- [ ] Passo 5 — implementar Command Palette nativa e integrar comandos existentes/ajuda. Fecha: critérios 7 a 11 e 17.
- [x] Passo 6 — implementar virtualizador compartilhado e integrar Lançamentos, rankings de Relatórios e posições do Portfólio. Fecha: critérios 12 a 17 parcialmente.
- [ ] Passo 6b — integrar Faturas e Histórico de Operações sem perder semântica de tabela, ações e foco. Fecha: critérios 12 a 17 restantes.
- [ ] Passo 7 — validar visualmente temas, densidades, teclado, leitores de tela, impressão e pacotes offline nas plataformas suportadas. Fecha: critérios 1 a 18.

## Changelog

- `0.9` — 2026-08-31 — Implementada suspensão de gráficos de módulos, abas e drawers sob `hidden`, com retomada local e limpeza na troca de sessão. Testes de ciclos repetidos, configuração mais recente e falha tardia aprovados; memória real no Safari não medida.
- `0.8` — 2026-08-31 — Desativadas animações globais, graduais e dinâmicas, com precedência sobre opções das views. Testadas configuração, preservação de interações e limpeza em ciclos com instâncias simuladas. Mitigação não garante ausência de recarregamentos nem elimina gráficos retidos em telas apenas ocultas.
- `0.7` — 2026-08-30 — Primeiro virtualizador compartilhado integrado a Lançamentos, rankings de Relatórios e posições do Portfólio; Faturas e Histórico de Operações ficam explicitamente na etapa seguinte.
- `0.6` — 2026-08-30 — Corrigido o ciclo de vida do ApexCharts com descarte automático de instâncias ligadas a elementos removidos do DOM, evitando crescimento contínuo de memória no Safari.
- `0.5` — 2026-08-30 — Removidos os tooltips redundantes dos históricos mensais de contas e cartões; os valores permanecem disponíveis nos cards correspondentes.
- `0.4` — 2026-08-30 — Alinhados os marcadores aos centros dos cards mensais e adotado tooltip compacto, sem cabeçalho e centralizado no plot dos históricos de contas e cartões.
- `0.3` — 2026-08-30 — Corrigidos o empilhamento global do drawer de rentabilidade, a corrida entre categorias em Relatórios e os limites dos gráficos de históricos de contas/cartões.
- `0.2` — 2026-08-30 — ApexCharts 4.7.0 vendorizado e gráficos existentes migrados para o adaptador compartilhado, preservando séries e tipos de visualização.
- `0.1` — 2026-08-30 — Especificada a fundação do frontend v2 com ApexCharts vendorizado, IMask, Command Palette nativa no padrão cmdk e virtualização de listas longas por janela visível.

## Relacionados

- [[frontend-modularizacao]]
- [[../adr/0002-modularizacao-frontend]]
- [[../adr/0013-dependencias-frontend-v2]]
- [[../design/design-system]]
- [[relatorios]]
- [[lancamentos]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[efeito-borboleta]]
