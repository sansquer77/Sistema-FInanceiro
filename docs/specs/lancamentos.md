---
tipo: spec
area: lancamentos
status: implementado
versao: 3.32
atualizado: 2026-08-31
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
> **implementado** · área: `lancamentos` · atualizado em 2026-08-31 · relacionados: [[contas-correntes]], [[categorias-tags-gestao]], [[cartoes]], [[investimentos-portfolio]]

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
| `use_average` | booleano | Opcional. Apenas para recorrentes. Persiste em todas as ocorrências da série; na edição de um recorrente, o checkbox fica habilitado e o estado salvo propaga para as ocorrências futuras não conciliadas. |
| `reconciled_at` | timestamp | Opcional. Marcado na conciliação bancária. |

## Regras de negócio

- **Despesa**: reduz o saldo da conta de origem.
- **Receita**: aumenta o saldo da conta de origem.
- **Investimento**: reduz a liquidez da conta quando for aporte e pode criar/atualizar a posição no portfólio. Ver [[investimentos-portfolio]].
- **Transferência**: reduz saldo da origem, aumenta saldo do destino. Exige contas diferentes com a mesma moeda.
- **Câmbio**: movimentação entre contas de moedas diferentes; registra valor de origem, valor de destino e cotação ajustável.
- A prévia cambial entre duas contas é calculada no backend com precisão decimal; a interface apenas apresenta a cotação e o valor de destino devolvidos pela API.
- Lançamentos em conta de moeda estrangeira normalizam o valor em BRL pela cotação informada manualmente; quando ela não for informada, o sistema consulta a última PTAX de venda disponível até a data do lançamento. Se a PTAX estiver indisponível, o usuário deve informar a cotação manualmente.
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
- A marcação de média (`use_average`) em lançamentos recorrentes é persistida em todas as ocorrências geradas da série.
- Ao editar uma ocorrência de uma série recorrente, o checkbox de cálculo pela média permanece habilitado e reflete a marcação da ocorrência; o usuário pode ativar ou desativar a flag no próprio formulário de edição.
- Se a flag de média for **alterada** ao salvar a edição de uma série recorrente — ativada agora (série sem a marcação) ou desmarcada (série que a tinha ativa) —, o sistema não exibe o modal de escopo e aplica a alteração automaticamente a todas as ocorrências futuras não conciliadas: ao ativar, a marcação é persistida nelas e seus valores são recalculados pela média dos últimos 12 lançamentos com a mesma descrição normalizada, mesmo tipo e mesma categoria/subcategoria; ao desmarcar, a marcação é removida e os valores mantêm o informado no formulário, sem recálculo.
- Se a flag de média **não for alterada** na edição (permanecendo ativa ou inativa), o sistema mantém o modal de escopo (`Apenas este lançamento` / `Este e os próximos`); escolhendo os próximos em série com a flag ativa, os valores futuros são recalculados pela média; escolhendo apenas este, somente a ocorrência atual muda.
- Em uma série com média ativa e flag inalterada, o modal deve esclarecer que **Apenas este lançamento** não recalcula os próximos e **Este e os próximos** os recalcula pela média.
- Se `use_average` não estiver ativo e a série nunca tiver tido a flag ativa, o comportamento atual de edição/exclusão em cascata se mantém.
- Lançamentos parcelados exibem índice e total (`1/36`, `2/36`...) sem reiniciar a contagem em edições pontuais.
- A tela de Lançamentos organiza o formulário em uma composição compacta, mantendo todos os campos relevantes visíveis na edição, sem blocos contextuais escurecidos (inclusive nos campos de renda fixa).
- A modalidade de renda fixa (Pós-fixada, Pré-fixada, Híbrida) é escolhida em combo na linha do Indexador, com o botão de ajuda (?) alinhado inline ao rótulo Modalidade.
- O formulário de renda fixa não exibe os atalhos de presets (100% do CDI, 120% do CDI, IPCA + 6,5%) — a modalidade, o indexador e a taxa são preenchidos diretamente; marcadores tipo checkbox (média histórica e reserva de emergência) aparecem como checkbox simples, sem moldura tipo pill.
- O campo Valor fica logo abaixo da Descrição e acima de Categoria/Subcategoria, mantendo posição estável no formulário independentemente do tipo de lançamento; em investimento, o campo **Valor investido** ocupa exatamente a mesma posição (o campo Valor fica oculto), de forma que o valor aparece na mesma altura em todos os tipos de lançamento.
- Câmbio, transferência e o agrupamento geral de investimento não usam bloco contextual: os campos aparecem como linhas diretas, como as demais linhas simples do formulário.
- Linhas simples do formulário (Valor, Repetição, Recorrência e Média) dispensam o bloco contextual escurecido e o título em caixa alta, aparecendo como linhas de campo diretas para aumentar a densidade e reduzir repetição de rótulos — os blocos ficam reservados a grupos com múltiplos campos.
- O formulário de lançamento fica mais largo que o padrão (até 460px) e equilibra os espaços laterais: o mesmo espaço à esquerda entre o formulário e o menu e à direita entre o formulário e o extrato, sem encostar no menu.
- O painel de extrato prioriza leitura rápida: gráfico de saldos e cards de saldo previsto/conciliado compactos no topo, filtros e busca em bloco próprio e lista agrupada por dia com cabeçalhos discretos, contadores e linhas densas.
- Em lançamentos parcelados, o valor informado é o total da compra/lançamento e deve ser dividido pela quantidade total de parcelas. Ex.: R$ 500 em 5x gera 5 lançamentos de R$ 100.
- Em lançamentos recorrentes, cada ocorrência futura deve manter exatamente o valor informado, a menos que o usuário ative a opção de calcular valores futuros pela média dos últimos 12 lançamentos com a mesma descrição normalizada, mesmo tipo e mesma categoria/subcategoria.
- Um lançamento avulso existente pode ser editado para se tornar parcelado ou recorrente; nesse caso, a ocorrência atual vira a primeira parcela/ocorrência, as próximas são criadas a partir dela e todas recebem o mesmo `series_id`.
- Quando a opção de média estiver ativa em um lançamento recorrente, o valor de cada ocorrência futura usa a média aritmética inteira (em centavos) dos valores dos últimos 12 lançamentos do usuário com a mesma descrição normalizada, mesmo tipo e mesma categoria/subcategoria; se houver menos de 12, usa todos os disponíveis; se não houver histórico, mantém o valor informado no formulário.
- Lançamentos recorrentes não exibem o campo de quantidade de ocorrências no formulário; o sistema grava a série com 120 ocorrências automaticamente para manter compatibilidade com lançamentos antigos que usam o campo.
- Ao final de cada grupo diário na tela de Lançamentos, `Saldo previsto` considera todos os lançamentos até a data e `Saldo conciliado` considera somente lançamentos com `reconciled_at`, ambos partindo do saldo inicial da conta selecionada.
- Valores financeiros extensos no gráfico de histórico/projeção de saldos devem se adaptar ao espaço disponível reduzindo a tipografia, sem aumentar a área do gráfico nem truncar centavos.
- Indicadores compactos distinguem visualmente valores previstos e conciliados sem introduzir novas cores semânticas.
- Cada lançamento exibe estado textual `Conciliado` ou `Pendente`, além da ação por ícone.
- Busca e filtro de conciliação permanecem ativos ao alternar temporariamente de módulo ou editar um lançamento.
- A busca oferece ação explícita para limpar o texto e a lista informa contagens total, conciliada e pendente no contexto pesquisado.
- Após criação ou edição, o lançamento retornado pela API recebe destaque visual temporário quando estiver visível pelos filtros atuais.
- Valores financeiros usam algarismos tabulares, largura consistente e alinhamento à direita para facilitar comparação vertical.
- Valores de lançamentos usam o mesmo tamanho de fonte dos textos de saldo do grupo diário, preservando densidade visual.
- O gráfico de histórico/projeção de saldos em Lançamentos de Contas deve manter a mesma linguagem visual do gráfico de evolução de faturas: cards mensais compactos acima da curva, mês atual destacado, meses futuros atenuados e linha futura pontilhada, preservando cores semânticas para saldos positivos e negativos.
- O seletor mensal de Lançamentos de Contas deve usar botões compactos por ícone para mês anterior, mês atual e próximo mês, preservando rótulos acessíveis.
- O rótulo do mês no seletor mensal deve usar o formato compacto `MM/AAAA`.
- Categoria e subcategoria são apresentadas como caminho único no formato `Categoria › Subcategoria`.
- Em telas estreitas, metadados secundários são ocultados, preservando descrição, valor, conta e estado de conciliação.
- Cabeçalhos de data permanecem visíveis durante a rolagem do respectivo grupo e permitem expandir ou recolher o dia.
- Ao abrir uma combinação de conta e mês pela primeira vez, dias com data igual ou posterior à data local atual iniciam expandidos e datas passadas iniciam recolhidas; a escolha do usuário é mantida enquanto a sessão estiver ativa.
- Campos do formulário de lançamento devem manter altura e alinhamento consistentes dentro da mesma linha, especialmente nos blocos condicionais de investimento/renda fixa; textos auxiliares devem aparecer como linhas de ajuda separadas para não desalinharem inputs e selects.
- Quando uma linha de formulário tiver apenas um campo visível, esse campo deve ocupar a largura completa da linha para evitar lacunas visuais.
- Orientações extensas de renda fixa no formulário de investimento devem ficar em helper contextual acionado por ícone discreto, não como texto sempre visível entre campos.
- No formulário de investimento em Renda Fixa, a modalidade deve ser escolhida por controle compacto de opção única, com o `select` nativo preservado apenas como valor de formulário quando necessário.
- O campo de taxa de Renda Fixa deve ajustar rótulo e placeholder conforme a modalidade: `Taxa Anual (% a.a.)` para pré-fixada, `Percentual do Indexador (%)` para pós-fixada e `Taxa Adicional Anual (% a.a.)` para híbrida.
- O formulário de Renda Fixa pode oferecer atalhos discretos para padrões comuns, como `100% do CDI`, `120% do CDI` e `IPCA + 6,5%`, preenchendo modalidade, indexador e taxa sem alterar regras de cálculo.
- O formulário de Renda Fixa deve exibir uma confirmação compacta em tempo real do título configurado, reduzindo a necessidade de texto explicativo permanente.
- O formulário de Lançamentos de Contas deve exibir ação `Cancelar` também durante novo cadastro, permitindo limpar a entrada atual e retornar ao estado inicial sem depender de salvar ou navegar.
- No formulário de investimento, subcategorias de Poupança devem ser exibidas no combo apenas como `Poupança`, mesmo que o nome técnico/histórico da subcategoria contenha observações antigas; o valor interno deve ser preservado para não alterar históricos.
- No formulário de investimento de Lançamentos de Contas, aportes de Renda Fixa ou Poupança devem exibir marcador compacto `Usar este aporte como reserva de emergência`, persistindo essa decisão na operação de investimento. A marcação não aparece nem é enviada para outros tipos de ativo.
- O formulário de investimento deve se adaptar ao ativo selecionado para reduzir dúvidas: quando o aporte for Poupança, campos de quantidade, preço unitário, renda fixa, CNPJ, corretagem, emolumentos, impostos e outros custos ficam ocultos/desabilitados, pois não são aplicáveis.
- No formulário de investimento em **Fundos de Investimentos** ou **Previdência Privada**, o usuário pode informar CNPJ opcionalmente e buscar a cota pela **Mais Retorno**; a busca preenche **Preço unitário** como assistência editável e não salva dados automaticamente.
- A listagem completa de lançamentos (`GET /api/transactions`) é paginada por `limit` (padrão 2000, máximo 5000) e `offset`, respondendo `has_more`; o frontend percorre as páginas até receber uma página menor que `limit`.
- Com `month` e `account_id` juntos, a listagem retorna todo o histórico da conta até o fim do mês informado (sem limite inferior de data) — o extrato usa essa fatia para calcular saldos previsto/conciliado a partir do saldo inicial da conta; o intervalo estrito do mês (`>= primeira data do mês`) aplica-se apenas à listagem sem conta.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/transactions` |
| `POST` | `/api/transactions` |
| `PUT` | `/api/transactions/{id}` |
| `DELETE` | `/api/transactions/{id}` |
| `PUT` | `/api/transactions/{id}/reconciliation` |
| `GET` | `/api/exchange-rate` (aceita origem, destino, data, valor e cotação manual opcional para prévia) |
| `GET` | `/api/classification-suggestion` |
| `GET` | `/api/portfolio/fund-quote?cnpj={cnpj}` |

Tabelas: `transactions`, `transaction_tags`, `checking_accounts`, `categories`, `subcategories`, `tags`.

## Critérios de aceite

- Dado uma receita criada, quando listado, o saldo da conta aumenta pelo valor informado.
- Dado uma despesa criada, quando listada, o saldo da conta diminui pelo valor informado.
- Dado uma transferência criada, quando listada, origem e destino são atualizados corretamente.
- Dado um câmbio criado, quando listado, origem reduz pelo valor de origem e destino aumenta pelo valor de destino.
- Dado um lançamento em moeda estrangeira sem cotação manual, quando criado ou importado, então o valor em BRL usa a última PTAX de venda disponível até a data do lançamento.
- Dado um lançamento em conta de moeda estrangeira, quando o formulário é aberto, então a cotação é pré-preenchida com a última PTAX disponível até a data; se a PTAX estiver indisponível, um campo de cotação manual visível aparece com a moeda da conta e nenhum valor falso (ex.: 1,0) é enviado.
- Dado um lançamento em moeda estrangeira sendo editado, quando a data ou a conta mudam, então a cotação armazenada é preservada e não é sobrescrita automaticamente pela PTAX.
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
- Dado o gráfico de histórico/projeção de saldos em Lançamentos de Contas, quando há meses passados, atual e futuros, então ele usa o mesmo padrão visual do gráfico de faturas com cards mensais compactos, curva SVG suave e projeção futura atenuada/pontilhada.
- Dado o gráfico de histórico/projeção de saldos com valores extensos, quando exibido em qualquer tamanho de tela, então os valores cabem nos cartões mensais por ajuste responsivo de tipografia e de largura mínima dos cartões, mantendo o tamanho atual da área e sem truncar centavos.
- Dado o usuário visualizando o seletor mensal de Lançamentos de Contas, quando os botões de navegação aparecem, então usam ícones compactos com rótulo acessível em vez de palavras longas.
- Dado o usuário visualizando o seletor mensal de Lançamentos de Contas, quando o mês é exibido, então o rótulo usa o formato `MM/AAAA`.
- Dado um lançamento de investimento classificado como **Fundos de Investimentos** ou **Previdência Privada** com CNPJ preenchido e Mais Retorno configurada, quando o usuário aciona `Buscar cota`, então o sistema preenche **Preço unitário** com a última cota disponível e mantém o campo editável.
- Dado o tipo Investimento selecionado no formulário de Lançamentos, quando campos condicionais de renda fixa são exibidos, então inputs e selects da mesma linha mantêm alturas e alinhamentos consistentes, com dicas exibidas sem deslocar campos vizinhos.
- Dado qualquer tipo de lançamento de conta, quando uma linha condicional exibe apenas um campo, então esse campo ocupa a linha inteira e o formulário não apresenta coluna vazia.
- Dado o tipo Investimento com categoria Renda Fixa selecionado, quando o usuário aciona o ícone de ajuda, então vê orientação contextual para pré-fixada, pós-fixada e híbrida sem alterar o alinhamento dos campos.
- Dado o tipo Investimento com categoria Renda Fixa selecionado, quando o usuário escolhe a modalidade por chips, então o valor do formulário é atualizado como se o `select` nativo tivesse sido alterado.
- Dado o tipo Investimento com categoria Renda Fixa selecionado, quando o usuário alterna modalidade, então o campo de taxa muda rótulo e placeholder para a unidade correta.
- Dado o tipo Investimento com categoria Renda Fixa selecionado, quando o usuário aciona um atalho comum, então modalidade, indexador e taxa são preenchidos e o resumo do título é atualizado.
- Dado o tipo Investimento com categoria Renda Fixa selecionado, quando modalidade, indexador ou taxa mudam, então a confirmação compacta reflete a configuração atual sem ocupar espaço de ajuda permanente.
- Dado um novo lançamento de conta em preenchimento, quando o usuário aciona `Cancelar`, então o formulário é limpo e volta ao estado inicial sem criar lançamento.
- Dado o tipo Investimento com subcategoria de Poupança cadastrada com texto complementar antigo, quando o combo de subcategoria é exibido, então a opção aparece como `Poupança`, preservando o valor interno original.
- Dado um aporte de Renda Fixa ou Poupança criado em Lançamentos de Contas, quando o usuário marca `Usar este aporte como reserva de emergência` e salva, então a operação de investimento fica marcada como reserva e a opção volta preenchida ao editar o lançamento.
- Dado o tipo Investimento com subcategoria Poupança selecionada, quando o formulário é exibido, então apenas campos aplicáveis à Poupança permanecem visíveis, ocultando/desabilitando quantidade, preço unitário, renda fixa, CNPJ, corretagem, emolumentos, impostos e outros custos.
- Dado um lançamento recorrente sem histórico de mesma descrição, categoria e subcategoria, quando a opção de média estiver ativada, então todas as ocorrências futuras mantêm o valor informado no formulário.
- Dado um histórico de 3 lançamentos com a mesma descrição, categoria e subcategoria e valores R$ 100, R$ 200 e R$ 300, quando um lançamento recorrente mensal ativa a opção de média, então cada uma das 120 ocorrências futuras usa o valor de R$ 200.
- Dado um lançamento recorrente sendo criado, quando o usuário seleciona o tipo "Recorrente", então o campo de quantidade de ocorrências permanece oculto e a série é gravada com 120 ocorrências.
- Dado um lançamento recorrente existente sendo editado, quando o formulário é aberto, então o campo de quantidade de ocorrências continua oculto e a frequência permanece desabilitada.
- Dado um lançamento recorrente criado com a opção `use_average`, quando as ocorrências são geradas, então todas persistem `use_average` ativo.
- Dado uma série recorrente com `use_average` ativo, quando o usuário edita uma ocorrência sem alterar a flag de média, então o sistema exibe o modal de escopo perguntando se a alteração vale apenas para o lançamento atual ou também para os futuros e explicando que **Apenas este lançamento** altera somente a ocorrência atual sem recalcular os próximos, enquanto **Este e os próximos** recalcula os futuros pela média.
- Dado uma série recorrente sem `use_average`, quando o usuário edita uma ocorrência, então o sistema mantém o comportamento atual de perguntar se deseja alterar apenas o lançamento atual ou também os futuros.
- Dado `GET /api/transactions` com `limit` e `offset` válidos, quando os filtros de mês/conta também estão presentes, então retorna no máximo `limit` lançamentos da página solicitada com `has_more` indicando se há páginas seguintes.
- Dado `GET /api/transactions` com `limit` acima de 5000, quando processado, então o servidor reduz o limite para 5000 sem erro.
- Dado um lançamento avulso existente, quando o usuário edita a repetição para parcelado ou recorrente, então o sistema preserva o lançamento atual como primeira ocorrência, cria as próximas ocorrências futuras e passa a listar todas com o mesmo identificador de série.
- Dado o usuário preenchendo ou editando um lançamento, quando o tipo ou categoria exige campos específicos, então os campos aparecem em blocos contextuais claramente rotulados e os campos não aplicáveis permanecem ocultos/desabilitados sem deixar espaços vazios no formulário.
- Dado o usuário visualizando Lançamentos, quando o painel superior é exibido, então o gráfico e os saldos previsto/conciliado usam apresentação compacta para deixar mais área útil para a lista.
- Dado uma lista mensal com filtros, quando exibida, então busca, filtro de conciliação e contador ficam destacados antes dos grupos diários.
- Dado uma lista agrupada por dia, quando exibida, então os cabeçalhos diários, contadores, linhas e subtotais usam hierarquia visual compacta e preservam ações, metadados e valores sem ocultar informações importantes.
- Dado um lançamento recorrente existente sendo editado, quando o formulário é aberto, então o checkbox de cálculo pela média permanece habilitado e reflete a marcação da ocorrência.
- Dado um lançamento recorrente existente sem `use_average` sendo editado, quando o usuário marca a opção de média e salva, então o sistema não exibe o modal de escopo, aplica a alteração a todas as ocorrências futuras não conciliadas, persiste a marcação nelas e recalcula seus valores pela média dos últimos 12 lançamentos com a mesma descrição, tipo e categoria/subcategoria.
- Dado uma série recorrente com `use_average` ativo sendo editada, quando o usuário desmarca a opção de média e salva, então o sistema não exibe o modal de escopo, remove a marcação das ocorrências futuras não conciliadas e mantém nelas o valor informado no formulário, sem recálculo pela média.
- Dado uma série recorrente com `use_average` ativo, quando o usuário edita uma ocorrência sem alterar a flag de média e escolhe `Apenas este lançamento`, então somente a ocorrência atual é alterada e as ocorrências futuras permanecem intactas.
- Dado uma série recorrente com `use_average` ativo, quando o usuário edita uma ocorrência sem alterar a flag de média e escolhe `Este e os próximos`, então a alteração é aplicada às ocorrências futuras não conciliadas e seus valores são recalculados pela média.
- Dado uma série recorrente sendo editada com a flag de média alterada (marcada ou desmarcada), quando o usuário salva, então o sistema não exibe o modal de escopo e aplica a alteração automaticamente às ocorrências futuras não conciliadas — ao marcar, persiste a marcação e recalcula pela média; ao desmarcar, mantém o valor informado sem recálculo e remove a marcação.

- Dada uma conciliação confirmada, quando a resposta chega, então status, contadores e filtro são atualizados sem sair da tela.
- Dada uma carga anterior em andamento, quando há mutação ou troca de conta, então a resposta anterior não substitui dados atuais nem bloqueia a nova seleção.
- Dada uma conta recentemente visitada, quando selecionada novamente sem mutações, então a fatia é restaurada do cache limitado; logout e mutações invalidam o reaproveitamento.
- Dada falha de gravação ou carregamento, quando ocorre, então há mensagem amigável e nenhum sucesso ou saldo é inventado.
- Dada uma edição confirmada, quando a resposta de gravação chega, então o valor devolvido aparece na lista antes de concluir as recargas.
- Dada uma gravação confirmada, quando uma recarga posterior falha, então a mensagem informa que a operação foi salva e a atualização falhou.
- Dada uma edição/exclusão de série, quando a fatia é revalidada, então a lista apresenta as ocorrências devolvidas pelo backend sem depender da recarga global.
- Dada uma recarga auxiliar em andamento, quando há nova mutação ou troca de sessão, então sua resposta antiga não substitui os dados atuais.
- Dado o mesmo histórico financeiro, quando a projeção otimizada é calculada, então todos os saldos e indicadores de reserva correspondem ao cálculo de referência, inclusive em transferências e faturas pagas.
- Dado um mês recente em cache, quando o usuário retorna a ele, então o app reaproveita a fatia válida; uma resposta de outro mês não substitui o selecionado.

## Plano de implementação desta correção

- [x] Exibir a ocorrência confirmada após salvar, sem aguardar recargas globais; distinguir falha de gravação de falha de atualização após sucesso.
- [x] Revalidar a fatia para refletir séries/exclusões e atualizar dados auxiliares sem bloquear o formulário, descartando respostas obsoletas.
- [x] Reduzir percursos repetidos na projeção de saldos e faturas; testar equivalência com os cálculos anteriores e custo por volume.
- [x] Implementar os comportamentos descritos sem alterar regras financeiras.
- [x] Testar sucesso, falha, concorrência e contratos de apresentação aplicáveis.

## Changelog

- `3.32` — 2026-08-31 — Complemento implementado: edição com resposta imediata, atualização auxiliar desacoplada e projeções sem releitura integral a cada data. Testes automatizados de apresentação, concorrência e equivalência financeira; percepção de fluidez no Safari ainda requer validação no ambiente do usuário.
- `3.31` — 2026-08-31 — Correções concluídas: conciliação aplica resposta confirmada sem recarga global, troca de conta independente por chave e cache limitado. Projeção filtra dados da conta no backend. Validados por testes de concorrência, apresentação e projeção.

- `3.30` — 2026-08-31 — Especificadas correções de resposta visual, carregamento e escopo do apoio, conforme regras acima.

- `3.29` — 2026-08-31 — Prévia cambial concluída no backend com precisão decimal e cobertura para cotação cruzada e manual; o frontend apenas apresenta o resultado.
- `3.28` — 2026-08-31 — Iniciada a transferência da prévia cambial residual do formulário para o backend, mantendo cotação e valor de destino editáveis.
- `3.27` — 2026-08-30 — Fatia do Extrato e projeção passam a compartilhar cache por conta+mês, requisição em andamento e invalidação após mutações.
- `3.26` — 2026-08-30 — Iniciado reaproveitamento da fatia mensal por conta enquanto fresca, com invalidação após mutações.
- `3.25` — 2026-08-29 — Campo de ativo em lançamentos de investimento sugere posições já cadastradas, preenche o nome ao selecionar e preserva a criação livre de novos códigos.
- `3.24` — 2026-08-20 — Modal de escopo em série recorrente com média ativa passa a explicar que a escolha **Apenas este lançamento** não recalcula os próximos, enquanto **Este e os próximos** os recalcula pela média; sem mudança na regra de cálculo ou no escopo aplicado.
- `3.23` — 2026-08-17 — Modal de escopo restaurado em edições de séries recorrentes: o sistema pula o modal **somente** quando a flag de média é alterada na edição (marcada em série sem a marcação ou desmarcada em série que a tinha); com a flag inalterada — ativa ou inativa — o modal `Apenas este lançamento` / `Este e os próximos` volta a aparecer; escolhendo os próximos em série com a flag ativa, os valores futuros continuam recalculados pela média; escolhendo apenas este, a cascata não ocorre.
- `3.22` — 2026-08-17 — Edição de lançamento recorrente passa a permitir ativar/desativar a flag de cálculo pela média: o checkbox fica habilitado no formulário de edição; ao salvar com a flag ativa (já ativa ou ativada agora), a edição aplica-se em cascata às ocorrências futuras não conciliadas sem modal, persistindo a marcação e recalculando valores pela média; ao desmarcar em série que tinha a flag ativa, a cascata segue sem recálculo e a marcação é removida no escopo; séries nunca marcadas mantêm o modal de escopo.
- `3.21` — 2026-08-11 — Formulário de Lançamentos em conta estrangeira pré-preenche a cotação com a última PTAX até a data (antes enviava silenciosamente `1,0`, gravando `amount_brl` sem conversão — ex.: despesas de imposto em USD entravam no Cockpit como R$ 1:1); se a PTAX estiver indisponível, campo de cotação manual visível é exibido; na edição a cotação armazenada é preservada.
- `3.20` — 2026-08-11 — Escala vertical do gráfico de histórico/projeção de saldos corrigida: a curva usava só a faixa central (24–48 de 100), achatezendo variações grandes; agora ocupa quase toda a altura do plot (10–88), sem aumentar a área do gráfico.
- `3.19` — 2026-08-11 — Helper (?) de modalidade da renda fixa alinhado inline ao rótulo (`field-label-title`), corrigindo a quebra de layout no formulário de Lançamentos (mesma correção aplicada no Portfólio).
- `3.18` — 2026-08-11 — Modalidade de renda fixa (Pós/Pré/Híbrida) volta a ser combo ao lado do Indexador, com o helper (?) junto ao rótulo; removidos os controles segmentados e o CSS de presets/chips (sem usos restantes).
- `3.17` — 2026-08-11 — Checkboxes de média histórica sem moldura pill (checkbox simples), seguindo o marcador de reserva de emergência; o layout pill de checkboxes é descontinuado no app (CSS removido).
- `3.16` — 2026-08-11 — Renda fixa sem presets (100% do CDI, 120% do CDI, IPCA + 6,5%); opção selecionada da modalidade Pós/Pré/Híbrida destacada em cor de accent; marcador de reserva de emergência sem moldura (checkbox simples).
- `3.15` — 2026-08-11 — Renda fixa sem bloco escurecido; a escolha de modalidade (Pós/Pré/Híbrida) passa a uma lista segmentada centralizada em linha própria, sempre visível; removida a frase "Atalhos comuns:" sobre os presets (que ficam centralizados).
- `3.14` — 2026-08-11 — Bloco escurecido também removido dos campos de **Fundo ou previdência** (CNPJ e Cota) no lançamento de Investimento; o único bloco restante é o de Renda fixa.
- `3.13` — 2026-08-11 — **Valor investido** passa a ocupar a mesma posição do campo Valor (logo abaixo da Descrição) quando o tipo é Investimento, mantendo o valor na mesma altura em todos os tipos de lançamento.
- `3.12` — 2026-08-11 — Formulário de Lançamentos: Valor movido para logo abaixo da Descrição (posição estável em todos os tipos de lançamento); blocos escurecidos removidos também de Câmbio, Transferência e do agrupamento geral de Investimento — permanecem apenas nos grupos complexos (Fundos/previdência e Renda fixa).
- `3.11` — 2026-08-11 — Formulário de Lançamentos mais largo (até 460px) e espaçamento lateral equilibrado: 16px entre menu e formulário, iguais aos 16px entre formulário e extrato.
- `3.10` — 2026-08-11 — Formulário de Lançamentos mais denso: linhas simples (Valor, Repetição, Recorrência e Média) deixam de usar o bloco contextual escurecido com título em caixa alta, ficando diretas no fluxo do formulário; blocos permanecem apenas para grupos de múltiplos campos.
- `3.9` — 2026-08-11 — Tela de Lançamentos ganha refinamento de layout: formulário mais compacto, blocos condicionais por tipo/categoria, filtros em destaque, cards de saldo menores e grupos diários mais limpos.
- `3.8` — 2026-08-11 — Gráfico de histórico/projeção de saldos em Lançamentos passa a usar a mesma linguagem visual refinada do gráfico de faturas, com cards compactos e curva SVG nativa.
- `3.7` — 2026-08-11 — Edição de lançamento avulso passa a permitir alterar a repetição para parcelado ou recorrente, criando as ocorrências futuras a partir da ocorrência atual.
- `3.6` — 2026-08-10 — Campo CNPJ e busca assistida de cota pela Mais Retorno passam a aparecer também para lançamentos de Previdência Privada, mantendo CNPJ opcional.
- `3.5` — 2026-08-10 — Formulário de investimento em Fundos passa a oferecer busca assistida de cota pela Mais Retorno a partir do CNPJ, preenchendo **Preço unitário** como sugestão editável.
- `3.4` — 2026-08-07 — Corrigida uma regressão da v3.3: a fatia de `GET /api/transactions` com **mês + conta** voltou a retornar todo o histórico da conta até o fim do mês (`date <= fim do mês`, sem limite inferior), pois o extrato calcula saldos acumulados partindo do saldo inicial da conta somado aos lançamentos até a data (ver `getBalanceUntil` no frontend). O intervalo estrito do mês aplica-se apenas à listagem sem conta. Teste de regressão adicionado.
- `3.3` — 2026-08-07 — Listagens completas paginadas: `GET /api/transactions` aceita `limit`/`offset` (padrão 2000, máximo 5000) e responde `has_more`; o frontend itera as páginas automaticamente.

- `3.2` — 2026-08-06 — Lançamentos recorrentes com `use_average` persistem a marcação em todas as ocorrências e, ao editar qualquer ocorrência dessa série, recalculam automaticamente os valores futuros pela média sem exibir modal de escopo.
- `3.1` — 2026-08-06 — Lançamentos recorrentes permitem calcular valores futuros pela média dos últimos 12 lançamentos com mesma descrição e passam a usar 120 ocorrências automaticamente, sem exibir o campo de quantidade.
- `3.0` — 2026-08-02 — Formulário de Renda Fixa em Lançamentos reduz ruído visual com modalidade em chips, microcopy dinâmica, atalhos e preview compacto.
- `2.9` — 2026-08-02 — Lançamentos em moeda estrangeira sem cotação manual passam a consultar a última PTAX de venda disponível até a data do lançamento para normalizar valores em BRL.
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
