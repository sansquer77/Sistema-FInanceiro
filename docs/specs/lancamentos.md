---
tipo: spec
area: lancamentos
status: implementado
versao: 2.8
atualizado: 2026-08-02
relacionados:
  - "[[contas-correntes]]"
  - "[[categorias-tags-gestao]]"
  - "[[cartoes]]"
  - "[[investimentos-portfolio]]"
  - "[[arquitetura]]"
tags: [spec, "area/lancamentos"]
aliases: ["Lançamentos", "Transações"]
---

# Lançamentos

> [!info] Status
> **implementado** · área: `lancamentos` · atualizado em 2026-08-02 · relacionados: [[contas-correntes]], [[categorias-tags-gestao]], [[cartoes]], [[investimentos-portfolio]]

## Problema

O usuário precisa registrar movimentações financeiras manuais e manter os saldos das contas atualizados em tempo real.

## Usuário

Qualquer usuário autenticado localmente que registre receitas, despesas, transferências, câmbio ou aportes de investimento.

## Jornada

1. Usuário abre a área de Lançamentos.
2. Escolhe a conta no topo do formulário.
3. Escolhe o tipo conforme a natureza da conta: receita, despesa, investimento, transferência ou câmbio.
4. Informa valor, data, descrição e, quando aplicável, categoria, subcategoria e tags.
5. Para transferência ou câmbio, informa também a conta de destino.
6. Para lançamentos recorrentes ou parcelados, define a frequência ou a quantidade total de parcelas.
7. O sistema grava o lançamento e atualiza os saldos das contas afetadas.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `tipo` | enum | Obrigatório. `income`, `expense`, `investment`, `transfer`, `exchange`. |
| `valor` | inteiro (centavos) | Obrigatório. Deve ser maior que zero. |
| `data` | ISO `YYYY-MM-DD` | Obrigatório. |
| `descricao` | texto | Obrigatório. |
| `conta_id` | FK | Obrigatório. |
| `conta_destino_id` | FK | Obrigatório para transferência e câmbio. |
| `categoria_id` | FK | Obrigatório para receita, despesa e investimento. |
| `subcategoria_id` | FK | Opcional. |
| `tags` | lista de FK | Opcional. N:M via `transaction_tags`. |
| `observacoes` | texto | Opcional. |
| `recorrente` | booleano + frequência | Opcional. |
| `parcelas` | inteiro | Opcional. Gera série com índice `1/N`. |
| `reconciled_at` | timestamp | Opcional. Marcado na conciliação bancária. |

## Regras de negócio

- **Despesa**: reduz o saldo da conta de origem.
- **Receita**: aumenta o saldo da conta de origem.
- **Investimento**: reduz a liquidez da conta quando for aporte e pode criar/atualizar a posição no portfólio. Ver [[investimentos-portfolio]].
- **Transferência**: reduz saldo da origem, aumenta saldo do destino. Exige contas diferentes com a mesma moeda.
- **Câmbio**: movimentação entre contas de moedas diferentes; registra valor de origem, valor de destino e cotação ajustável.
- Valor deve ser maior que zero.
- Categoria é obrigatória para receitas, despesas e investimentos. Transferências e câmbio não exigem categoria.
- Em novos lançamentos, descrições com histórico exato e confiança suficiente podem preencher categoria e subcategoria sem sobrescrever escolhas manuais. Ver [[classificacao-assistida]].
- Subcategoria, tags e observações são opcionais.
- Contas do tipo `wallet` aceitam apenas receitas, despesas e transferências à vista — sem recorrência. Ver [[contas-correntes]].
- Ao selecionar uma conta de investimento, o tipo padrão sugerido é `investment`.
- Excluir um lançamento reverte o impacto no saldo.
- **Edição em cascata** (`apply_to_future`): ao editar um lançamento de uma série, o usuário pode aplicar as alterações ao lançamento atual ou a todos os futuros da série que ainda não foram conciliados (`reconciled_at IS NULL`).
- **Exclusão em cascata** (`scope=future`): remove recursivamente todos os lançamentos futuros não conciliados da mesma série, revertendo os respectivos impactos nos saldos.
- A escolha de edição/exclusão em cascata deve usar modal com ações explícitas, como `Apenas este lançamento`, `Este e os próximos`, `Excluir apenas este`, `Excluir este e os próximos` e `Voltar`.
- Lançamentos parcelados exibem índice e total (`1/36`, `2/36`...) sem reiniciar a contagem em edições pontuais.
- Em lançamentos parcelados, o valor informado é o total da compra/lançamento e deve ser dividido pela quantidade de parcelas. Ex.: R$ 500 em 5x gera 5 lançamentos de R$ 100.
- Em lançamentos recorrentes, cada ocorrência futura deve manter exatamente o valor informado. Ex.: R$ 500 recorrente por 5 ocorrências gera 5 lançamentos de R$ 500.
- Ao final de cada grupo diário na tela de Lançamentos, `Saldo previsto` considera todos os lançamentos até a data e `Saldo conciliado` considera somente lançamentos com `reconciled_at`, ambos partindo do saldo inicial da conta selecionada.
- Valores financeiros extensos no gráfico de histórico/projeção de saldos devem se adaptar ao espaço disponível reduzindo a tipografia, sem aumentar a área do gráfico nem truncar centavos.
- Indicadores compactos distinguem visualmente valores previstos e conciliados sem introduzir novas cores semânticas.
- Cada lançamento exibe estado textual `Conciliado` ou `Pendente`, além da ação por ícone.
- Busca e filtro de conciliação permanecem ativos ao alternar temporariamente de módulo ou editar um lançamento.
- A busca oferece ação explícita para limpar o texto e a lista informa contagens total, conciliada e pendente no contexto pesquisado.
- Após criação ou edição, o lançamento retornado pela API recebe destaque visual temporário quando estiver visível pelos filtros atuais.
- Valores financeiros usam algarismos tabulares, largura consistente e alinhamento à direita para facilitar comparação vertical.
- Valores de lançamentos usam o mesmo tamanho de fonte dos textos de saldo do grupo diário, preservando densidade visual.
- O gráfico de histórico/projeção de saldos em Lançamentos de Contas deve manter o mesmo layout do gráfico de faturas de cartão: mês no topo de cada cartão, valor na base e sem marcadores textuais de `Previsto` ou `Conciliado` dentro do gráfico.
- O seletor mensal de Lançamentos de Contas deve usar botões compactos por ícone para mês anterior, mês atual e próximo mês, preservando rótulos acessíveis.
- O rótulo do mês no seletor mensal deve usar o formato compacto `MM/AAAA`.
- Categoria e subcategoria são apresentadas como caminho único no formato `Categoria › Subcategoria`.
- Em telas estreitas, metadados secundários são ocultados, preservando descrição, valor, conta e estado de conciliação.
- Cabeçalhos de data permanecem visíveis durante a rolagem do respectivo grupo e permitem expandir ou recolher o dia.
- Ao abrir uma combinação de conta e mês pela primeira vez, dias com data igual ou posterior à data local atual iniciam expandidos e datas passadas iniciam recolhidas; a escolha do usuário é mantida enquanto a sessão estiver ativa.
- Campos do formulário de lançamento devem manter altura e alinhamento consistentes dentro da mesma linha, especialmente nos blocos condicionais de investimento/renda fixa; textos auxiliares devem aparecer como linhas de ajuda separadas para não desalinharem inputs e selects.
- Quando uma linha de formulário tiver apenas um campo visível, esse campo deve ocupar a largura completa da linha para evitar lacunas visuais.
- Orientações extensas de renda fixa no formulário de investimento devem ficar em helper contextual acionado por ícone discreto, não como texto sempre visível entre campos.
- O formulário de Lançamentos de Contas deve exibir ação `Cancelar` também durante novo cadastro, permitindo limpar a entrada atual e retornar ao estado inicial sem depender de salvar ou navegar.
- No formulário de investimento, subcategorias de Poupança devem ser exibidas no combo apenas como `Poupança`, mesmo que o nome técnico/histórico da subcategoria contenha observações antigas; o valor interno deve ser preservado para não alterar históricos.
- No formulário de investimento de Lançamentos de Contas, aportes de Renda Fixa ou Poupança devem exibir marcador compacto `Usar este aporte como reserva de emergência`, persistindo essa decisão na operação de investimento. A marcação não aparece nem é enviada para outros tipos de ativo.
- O formulário de investimento deve se adaptar ao ativo selecionado para reduzir dúvidas: quando o aporte for Poupança, campos de quantidade, preço unitário, renda fixa, CNPJ, corretagem, emolumentos, impostos e outros custos ficam ocultos/desabilitados, pois não são aplicáveis.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/transactions` |
| `POST` | `/api/transactions` |
| `PUT` | `/api/transactions/{id}` |
| `DELETE` | `/api/transactions/{id}` |
| `PUT` | `/api/transactions/{id}/reconciliation` |
| `GET` | `/api/exchange-rate` |
| `GET` | `/api/classification-suggestion` |

Tabelas: `transactions`, `transaction_tags`, `checking_accounts`, `categories`, `subcategories`, `tags`.

## Critérios de aceite

- Dado uma receita criada, quando listado, o saldo da conta aumenta pelo valor informado.
- Dado uma despesa criada, quando listada, o saldo da conta diminui pelo valor informado.
- Dado uma transferência criada, quando listada, origem e destino são atualizados corretamente.
- Dado um câmbio criado, quando listado, origem reduz pelo valor de origem e destino aumenta pelo valor de destino.
- Dado um lançamento excluído, quando consultado, o saldo volta ao estado anterior.
- Dado `scope=future` na exclusão, quando executado, as parcelas/recorrências futuras não conciliadas são removidas e os saldos revertidos.
- Dado `apply_to_future` na edição, quando executado, os dados e saldos das ocorrências futuras não conciliadas são atualizados.
- Dado um lançamento de série em edição ou exclusão, quando o modal aparece, `Voltar` cancela a ação sem alterar dados.
- Dado um lançamento listado, quando exibido, mostra conta, tipo, valor, data, categoria, subcategoria, tags e indicação de recorrente/parcelado.
- Dado um dia com lançamentos conciliados e não conciliados, quando o agrupamento diário é exibido, então mostra separadamente o saldo previsto com todos os lançamentos e o saldo conciliado somente com os conciliados.
- Dado um filtro ou busca ativo, quando o usuário alterna de módulo ou edita um lançamento, então o estado de filtragem é preservado.
- Dado uma busca preenchida, quando o usuário aciona limpar, então o texto e o resultado filtrado são restaurados.
- Dada a lista mensal, quando exibida, então informa quantidade total, conciliada e pendente no contexto da busca.
- Dado um lançamento criado ou atualizado visível pelos filtros, quando a lista é recarregada, então a linha recebe destaque temporário.
- Dada uma lista de lançamentos, quando os valores são exibidos, então usam algarismos tabulares, coluna com largura consistente e alinhamento à direita.
- Dado um lançamento categorizado, quando listado, então categoria e subcategoria aparecem como um único caminho separado por `›`.
- Dada uma tela com até `520px`, quando a lista é exibida, então preserva descrição, valor, conta e conciliação e reduz os demais metadados.
- Dado um mês com lançamentos em mais de um dia, quando a lista é aberta pela primeira vez, então os dias de hoje e futuros estão expandidos e os dias passados estão recolhidos.
- Dado um cabeçalho diário, quando acionado, então alterna o conteúdo do dia e informa o estado por `aria-expanded`.
- Dado um grupo diário longo, quando a página é rolada dentro dele, então o cabeçalho da data permanece brevemente visível.
- Dado o gráfico de histórico/projeção de saldos, quando exibido, então cada cartão mensal mostra o mês no topo e não exibe marcadores `Previsto` ou `Conciliado` dentro da área do gráfico.
- Dado o gráfico de histórico/projeção de saldos com valores extensos, quando exibido em qualquer tamanho de tela, então os valores cabem nos cartões mensais por ajuste responsivo de tipografia e de largura mínima dos cartões, mantendo o tamanho atual da área e sem truncar centavos.
- Dado o usuário visualizando o seletor mensal de Lançamentos de Contas, quando os botões de navegação aparecem, então usam ícones compactos com rótulo acessível em vez de palavras longas.
- Dado o usuário visualizando o seletor mensal de Lançamentos de Contas, quando o mês é exibido, então o rótulo usa o formato `MM/AAAA`.
- Dado o tipo Investimento selecionado no formulário de Lançamentos, quando campos condicionais de renda fixa são exibidos, então inputs e selects da mesma linha mantêm alturas e alinhamentos consistentes, com dicas exibidas sem deslocar campos vizinhos.
- Dado qualquer tipo de lançamento de conta, quando uma linha condicional exibe apenas um campo, então esse campo ocupa a linha inteira e o formulário não apresenta coluna vazia.
- Dado o tipo Investimento com categoria Renda Fixa selecionado, quando o usuário aciona o ícone de ajuda, então vê orientação contextual para pré-fixada, pós-fixada e híbrida sem alterar o alinhamento dos campos.
- Dado um novo lançamento de conta em preenchimento, quando o usuário aciona `Cancelar`, então o formulário é limpo e volta ao estado inicial sem criar lançamento.
- Dado o tipo Investimento com subcategoria de Poupança cadastrada com texto complementar antigo, quando o combo de subcategoria é exibido, então a opção aparece como `Poupança`, preservando o valor interno original.
- Dado um aporte de Renda Fixa ou Poupança criado em Lançamentos de Contas, quando o usuário marca `Usar este aporte como reserva de emergência` e salva, então a operação de investimento fica marcada como reserva e a opção volta preenchida ao editar o lançamento.
- Dado o tipo Investimento com subcategoria Poupança selecionada, quando o formulário é exibido, então apenas campos aplicáveis à Poupança permanecem visíveis, ocultando/desabilitando quantidade, preço unitário, renda fixa, CNPJ, corretagem, emolumentos, impostos e outros custos.

## Changelog

- `2.8` — 2026-08-02 — Gráfico de saldos em Lançamentos de Contas ganha ajustes responsivos para telas de 14 polegadas (e breakpoints intermediários), evitando quebra de linha em valores extensos sem truncar centavos.
- `2.7` — 2026-08-02 — Rótulo do seletor mensal passa a usar formato fixo `MM/AAAA`.
- `2.6` — 2026-08-02 — Seletor mensal de Lançamentos de Contas padronizado com botões compactos por ícone.
- `2.5` — 2026-07-29 — Formulário de investimento em Lançamentos de Contas passa a ocultar campos não aplicáveis a aportes de Poupança.
- `2.4` — 2026-07-29 — Aportes de Renda Fixa e Poupança em Lançamentos de Contas passam a expor marcador de reserva de emergência.
- `2.3` — 2026-07-29 — Formulário de Lançamentos passa a exibir `Cancelar` também em novo cadastro e simplifica a exibição de subcategorias de Poupança no combo.
- `2.2` — 2026-07-26 — Orientações extensas de renda fixa passam para helper contextual acionado por ícone no formulário de investimento.
- `2.1` — 2026-07-26 — Blocos condicionais de investimento/renda fixa no formulário passam a separar dicas de campos para preservar alinhamento e altura dos controles.
- `2.0` — 2026-07-24 — Gráfico de saldos passa a adaptar valores financeiros extensos ao espaço disponível sem ampliar a área visual.
- `1.9` — 2026-07-24 — Grupos diários passam a abrir inicialmente de hoje em diante, mantendo datas passadas recolhidas.
- `1.8` — 2026-07-24 — Gráfico de saldos em Lançamentos de Contas volta ao layout do gráfico de cartões, com mês no topo e sem marcadores de previsto/conciliado.
- `1.7` — 2026-07-24 — Rótulos de saldos diários removem redundância `no dia` e valores de lançamentos ganham fonte mais compacta.
- `1.6` — 2026-07-24 — Leitura financeira com colunas tabulares, metadados responsivos, caminho de categoria e grupos diários sticky/recolhíveis.
- `1.5` — 2026-07-24 — Melhorias de UX na leitura de previsto/conciliado, estado por lançamento, busca persistente, filtros, contagem contextual e destaque pós-gravação.
- `1.4` — 2026-07-24 — Agrupamento diário passa a exibir saldos previsto e conciliado separadamente.
- `1.3` — 2026-07-23 — Integrada a sugestão local de categoria e subcategoria por histórico exato.
- `1.2` — 2026-07-20 — Modal de decisão explícita documentado para edição e exclusão de séries.
- `1.1` — 2026-06-29 — Frontmatter, tabela de dados e critérios formalizados; wikilinks adicionados.
- `1.0` — versão original.

## Relacionados

- [[contas-correntes]]
- [[categorias-tags-gestao]]
- [[cartoes]]
- [[investimentos-portfolio]]
- [[arquitetura]]
