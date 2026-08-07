---
tipo: spec
area: cartoes
status: implementado
versao: 2.6
atualizado: 2026-08-07
relacionados:
  - "[[contas-correntes]]"
  - "[[lancamentos]]"
  - "[[limites-gastos]]"
  - "[[relatorios]]"
  - "[[importacao-organizze]]"
  - "[[arquitetura]]"
tags: [spec, "area/cartoes"]
aliases: ["Cartões de Crédito", "Faturas"]
---

# Cartões de Crédito

> [!info] Status
> **implementado** · área: `cartoes` · atualizado em 2026-08-07 · relacionados: [[contas-correntes]], [[lancamentos]], [[limites-gastos]], [[relatorios]]

## Problema

O usuário precisa controlar gastos de cartão, limites, faturas e vencimentos sem misturar compras de cartão com o saldo imediato de sua conta-corrente.

## Usuário

Qualquer usuário autenticado localmente que utilize cartões de crédito para despesas pessoais.

## Jornada

1. O usuário cria um cartão manual com limite, dia de fechamento, dia de vencimento, emissor, bandeira, moeda e conta preferencial de pagamento.
2. Registra despesas e receitas no cartão, associadas a uma fatura mensal (`AAAA-MM`).
3. Acompanha a fatura em aberto com lançamentos e saldo consolidado.
4. Realiza a conciliação (`reconciled_at`) de transações contra a fatura oficial.
5. Filtra a lista da fatura por todos, não conciliados ou conciliados, e busca lançamentos por texto.
6. Move lançamentos entre faturas anterior/próxima quando necessário.
7. Paga a fatura escolhendo uma conta-corrente de mesma moeda; o sistema gera automaticamente uma despesa na conta de pagamento.

## Dados

**Cartão:**

| Campo | Tipo | Regra |
|---|---|---|
| `nome` | texto | Obrigatório. |
| `limite` | inteiro (centavos) | Obrigatório. |
| `dia_fechamento` | inteiro (1-31) | Obrigatório. |
| `dia_vencimento` | inteiro (1-31) | Obrigatório. |
| `emissor` | texto | Opcional. |
| `bandeira` | texto | Opcional. |
| `moeda` | enum | Obrigatório. `BRL`, `USD`, `EUR` ou `GBP`. |
| `conta_preferencial_id` | FK | Opcional. Deve ter a mesma moeda do cartão. |

**Lançamento de cartão:**

| Campo | Tipo | Regra |
|---|---|---|
| `invoice_month` | `AAAA-MM` | Obrigatório. Calculado pela data e dia de fechamento. |
| `valor` | inteiro (centavos) | Obrigatório. |
| `data` | ISO `YYYY-MM-DD` | Obrigatório. |
| `descricao` | texto | Obrigatório. |
| `categoria_id` | FK | Obrigatório para despesas e receitas. |
| `subcategoria_id` | FK | Opcional. |
| `tags` | lista de FK | Opcional. N:M via `credit_card_transaction_tags`. |
| `parcelas` | inteiro | Opcional. Exibe `1/12`, `2/12` etc. |
| `use_average` | booleano | Opcional. Apenas para recorrentes. Persiste em todas as ocorrências da série. |
| `reconciled_at` | timestamp | Opcional. Marcado na conciliação. |

## Regras

- Gasto em cartão pertence obrigatoriamente a uma fatura mensal (`AAAA-MM`).
- A fatura é calculada pela data do lançamento e pelo dia de fechamento do cartão. Compras após o fechamento entram na fatura posterior.
- Quando a fatura calculada pela data já estiver paga/fechada, o lançamento deve ser registrado automaticamente na próxima fatura aberta.
- Não é permitido adicionar ou editar lançamentos diretamente em faturas já pagas (fechadas); nesses casos o sistema deve avançar a competência para a próxima fatura aberta quando a operação vier de um lançamento por data.
- É possível mover uma transação para a fatura anterior ou posterior desde que a fatura de destino não esteja paga.
- O sistema não deve perder silenciosamente lançamentos de cartão quando a competência original estiver fechada.
- Moedas do cartão e da conta de pagamento da fatura devem ser idênticas.
- A conta preferencial de pagamento, quando informada, deve ter a mesma moeda do cartão.
- Lançamentos em cartão de moeda estrangeira persistem valor normalizado em BRL pela cotação informada manualmente; quando ela não for informada, o sistema consulta a última PTAX de venda disponível até a data do lançamento.
- Lançamentos de cartão podem ser únicos, parcelados ou recorrentes.
- Em lançamentos recorrentes de cartão, cada ocorrência futura deve manter exatamente o valor informado, a menos que o usuário ative a opção de calcular valores futuros pela média dos últimos 12 lançamentos com a mesma descrição normalizada, mesmo tipo e mesma categoria/subcategoria.
- Quando a opção de média estiver ativa em um lançamento recorrente de cartão, o valor de cada ocorrência futura usa a média aritmética inteira (em centavos) dos valores dos últimos 12 lançamentos do usuário com a mesma descrição normalizada, mesmo tipo e mesma categoria/subcategoria; se houver menos de 12, usa todos os disponíveis; se não houver histórico, mantém o valor informado no formulário.
- Lançamentos recorrentes de cartão não exibem o campo de quantidade de ocorrências no formulário; o sistema grava a série com 120 ocorrências automaticamente para manter compatibilidade com lançamentos antigos que usam o campo.
- A marcação de média (`use_average`) em lançamentos recorrentes de cartão é persistida em todas as ocorrências geradas da série.
- Ao editar uma ocorrência de uma série recorrente de cartão com `use_average` ativo, o sistema não exibe o modal de escopo; a alteração é aplicada automaticamente a todas as ocorrências futuras não conciliadas e seus valores são recalculados pela média dos últimos 12 lançamentos com a mesma descrição normalizada, mesmo tipo e mesma categoria/subcategoria.
- Se `use_average` não estiver ativo, o comportamento atual de edição/exclusão em cascata se mantém.
- O formulário manual de lançamento no cartão deve oferecer o campo `Tag`, com as mesmas sugestões de tags usadas em lançamentos de contas e suporte a múltiplas tags separadas por vírgula.
- Em novos lançamentos, descrições com histórico exato e confiança suficiente podem preencher categoria e subcategoria sem sobrescrever escolhas manuais. Ver [[classificacao-assistida]].
- Em lançamentos parcelados de cartão, o valor informado é o total da compra e deve ser dividido pela quantidade de parcelas. Ex.: R$ 500 em 5x gera 5 lançamentos/faturas de R$ 100.
- Em lançamentos recorrentes de cartão, cada ocorrência deve manter exatamente o valor informado. Ex.: R$ 500 recorrente por 5 ocorrências gera 5 lançamentos de R$ 500.
- A fatura exibe total atual, total conciliado e contador de lançamentos não conciliados.
- A lista de lançamentos da fatura permite busca por descrição, categoria, subcategoria, tag, observação, data, tipo ou valor.
- O filtro de conciliação da fatura alterna entre todos, não conciliados e conciliados sem alterar os totais da fatura.
- Cartões arquivados não podem receber novos lançamentos, mas podem ser restaurados.
- Lançamentos de cartão entram em relatórios e limites pela competência da fatura (`invoice_month`), não pela data da compra. Ver [[relatorios]], [[limites-gastos]].
- Faturas não pagas com lançamentos conciliados devem entrar como abatimento no saldo previsto da conta preferencial de pagamento, no mês de vencimento da fatura.
- Faturas já pagas não devem ser abatidas novamente no saldo previsto da conta preferencial.
- O lançamento de conta gerado pelo pagamento da fatura deve reduzir o saldo da conta de pagamento, mas deve ser identificado como pagamento de fatura para não entrar em análises de despesa e evitar duplicidade com os lançamentos detalhados do cartão.
- Valores de lançamentos de cartão usam o mesmo tamanho de fonte compacto dos lançamentos de conta para melhorar a densidade de leitura.
- Valores financeiros extensos no gráfico de faturas devem se adaptar ao espaço disponível reduzindo a tipografia, sem aumentar a área do gráfico nem truncar centavos.
- O seletor mensal da fatura deve usar botões compactos por ícone para mês anterior, mês atual e próximo mês, preservando rótulos acessíveis.
- O rótulo do mês no seletor mensal da fatura deve usar o formato compacto `MM/AAAA`.
- Campos do formulário de lançamento no cartão devem manter altura e alinhamento consistentes dentro da mesma linha; linhas com apenas um campo visível devem ocupar a largura completa para evitar lacunas visuais.
- O formulário de Lançamentos de Cartões deve exibir ação `Cancelar` também durante novo cadastro, em variante discreta, permitindo limpar a entrada atual e retornar ao estado inicial sem depender de salvar ou navegar.
- As listagens completas de lançamentos e pagamentos de cartão (`GET /api/credit-card-transactions` e `GET /api/credit-card-payments`) são paginadas por `limit` (padrão 2000, máximo 5000) e `offset`, respondendo `has_more`; o frontend percorre as páginas até receber uma página menor que `limit`.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/credit-cards` |
| `GET` | `/api/credit-cards?status=archived` |
| `POST` | `/api/credit-cards` |
| `PUT` | `/api/credit-cards/{id}` |
| `DELETE` | `/api/credit-cards/{id}` |
| `POST` | `/api/credit-cards/{id}/restore` |
| `GET` | `/api/credit-card-invoice` |
| `GET` | `/api/credit-card-transactions` |
| `POST` | `/api/credit-card-transactions` |
| `PUT` | `/api/credit-card-transactions/{id}` |
| `DELETE` | `/api/credit-card-transactions/{id}` |
| `PUT` | `/api/credit-card-transactions/{id}/invoice` |
| `PUT` | `/api/credit-card-transactions/{id}/reconciliation` |
| `GET` | `/api/credit-card-payments` |
| `GET` | `/api/classification-suggestion` |
| `POST` | `/api/credit-card-invoice/pay` |

Tabelas: `credit_cards`, `credit_card_transactions`, `credit_card_payments`, `credit_card_transaction_tags`.

## Plano de implementação

- [x] Manter o pagamento da fatura criando lançamento de conta para efeito de saldo.
- [x] Expor nos lançamentos de conta um indicador derivado do vínculo com `credit_card_payments`.
- [x] Usar esse indicador para excluir o pagamento agregado das visões analíticas sem apagar o histórico operacional do pagamento.
- [x] Validar que a fatura continua paga e o saldo da conta continua abatido.

## Critérios de aceite

- Dado um cartão cadastrado, quando uma despesa é registrada, ela aparece na fatura correta calculada pelo dia de fechamento.
- Dado uma compra com data antes do fechamento de uma fatura já paga, quando registrada, então ela aparece na próxima fatura aberta.
- Dado uma fatura em aberto, quando consultada, o total soma seus lançamentos.
- Dado uma fatura paga, quando o usuário registra um lançamento cuja data cairia nela, então o sistema preserva o lançamento e ajusta a competência para a próxima fatura aberta.
- Dado um lançamento conciliado, quando exibido, o status de verificado persiste.
- Dado uma fatura com lançamentos, quando o usuário busca por texto, a lista exibe apenas os lançamentos correspondentes sem alterar o total da fatura.
- Dado uma fatura com lançamentos conciliados e não conciliados, quando o usuário troca o filtro de conciliação, a lista exibe apenas o status escolhido.
- Dado um lançamento de cartão criado ou editado com tags, quando a fatura é exibida, então as tags aparecem no lançamento e podem ser usadas na busca.
- Dado o pagamento de uma fatura, quando executado, o saldo da conta escolhida é reduzido pelo valor da fatura e a fatura é marcada como paga.
- Dado o pagamento de uma fatura, quando Cockpit, relatórios ou limites de gastos somam despesas analíticas, então o pagamento agregado da fatura é ignorado e os lançamentos detalhados do cartão permanecem considerados.
- Dado lançamentos recorrentes de cartão, quando listados no Cockpit, aparecem pela competência da fatura.
- Dado uma fatura conciliada e não paga com conta preferencial configurada, quando a conta exibe saldo previsto, então a fatura é considerada pelo vencimento sem duplicar faturas já pagas.
- Dado o gráfico de faturas com valores extensos, quando exibido em telas de 14 polegadas ou menores, então os valores cabem nos cartões mensais por ajuste responsivo de tipografia e de largura mínima dos cartões, mantendo o tamanho atual da área e sem truncar centavos.
- Dado o usuário visualizando o seletor mensal da fatura, quando os botões de navegação aparecem, então usam ícones compactos com rótulo acessível em vez de palavras longas.
- Dado o usuário visualizando o seletor mensal da fatura, quando o mês é exibido, então o rótulo usa o formato `MM/AAAA`.
- Dado qualquer tipo de lançamento no cartão, quando campos condicionais de parcela ou recorrência são exibidos ou ocultados, então os campos visíveis mantêm altura/alinhamento consistentes e linhas unitárias ocupam a largura completa.
- Dado um novo lançamento de cartão em preenchimento, quando o usuário aciona `Cancelar`, então o formulário é limpo e volta ao estado inicial sem criar lançamento.
- Dado um lançamento recorrente de cartão sem histórico de mesma descrição, categoria e subcategoria, quando a opção de média estiver ativada, então todas as ocorrências futuras mantêm o valor informado no formulário.
- Dado um histórico de 3 lançamentos de cartão com a mesma descrição, categoria e subcategoria e valores R$ 100, R$ 200 e R$ 300, quando um lançamento recorrente mensal ativa a opção de média, então cada uma das 120 ocorrências futuras usa o valor de R$ 200.
- Dado um lançamento recorrente de cartão sendo criado, quando o usuário seleciona o tipo "Recorrente", então o campo de quantidade de ocorrências permanece oculto e a série é gravada com 120 ocorrências.
- Dado um lançamento recorrente de cartão existente sendo editado, quando o formulário é aberto, então o campo de quantidade de ocorrências continua oculto e a frequência permanece desabilitada.
- Dado um lançamento recorrente de cartão criado com a opção `use_average`, quando as ocorrências são geradas, então todas persistem `use_average` ativo.
- Dado uma série recorrente de cartão com `use_average` ativo, quando o usuário edita qualquer ocorrência, então o sistema não exibe o modal de escopo e aplica automaticamente a alteração a todas as ocorrências futuras não conciliadas, recalculando seus valores pela média.
- Dado uma série recorrente de cartão sem `use_average`, quando o usuário edita uma ocorrência, então o sistema mantém o comportamento atual de perguntar se deseja alterar apenas o lançamento atual ou também os futuros.
- Dado `GET /api/credit-card-transactions` com `limit` e `offset` válidos, quando consultado, então retorna no máximo `limit` lançamentos da página solicitada com `has_more` adequado.
- Dado `GET /api/credit-card-payments` com `limit` e `offset` válidos, quando consultado, então retorna no máximo `limit` pagamentos da página solicitada com `has_more` adequado.

## Changelog

- `2.6` — 2026-08-07 — Listagens completas de cartão paginadas: `GET /api/credit-card-transactions` e `GET /api/credit-card-payments` aceitam `limit`/`offset` (padrão 2000, máximo 5000) e respondem `has_more`; o frontend itera as páginas automaticamente.

- `2.5` — 2026-08-06 — Lançamentos recorrentes de cartão com `use_average` persistem a marcação em todas as ocorrências e, ao editar qualquer ocorrência dessa série, recalculam automaticamente os valores futuros pela média sem exibir modal de escopo.
- `2.4` — 2026-08-06 — Lançamentos recorrentes de cartão permitem calcular valores futuros pela média dos últimos 12 lançamentos com mesma descrição e passam a usar 120 ocorrências automaticamente, sem exibir o campo de quantidade.
- `2.3` — 2026-08-02 — Lançamentos de cartão em moeda estrangeira passam a gravar valor normalizado em BRL por cotação manual ou pela última PTAX de venda disponível.
- `2.2` — 2026-08-02 — Gráfico de faturas e resumo de fatura ganham ajustes responsivos para telas de 14 polegadas (e breakpoints intermediários), evitando quebra de linha em valores extensos e melhorando a densidade dos cartões de resumo.
- `2.1` — 2026-08-02 — Rótulo do seletor mensal da fatura passa a usar formato fixo `MM/AAAA`.
- `2.0` — 2026-08-02 — Seletor mensal de Faturas/Lançamentos de Cartões padronizado com botões compactos por ícone.
- `1.9` — 2026-07-29 — Formulário de Lançamentos de Cartões passa a exibir `Cancelar` também em novo cadastro, em variante discreta.
- `1.8` — 2026-07-26 — Formulário de lançamentos no cartão passa a seguir alinhamento consistente em linhas pareadas e linhas unitárias.
- `1.7` — 2026-07-24 — Pagamento de fatura passa a ser identificado para reduzir saldo sem duplicar despesas analíticas.
- `1.6` — 2026-07-24 — Gráfico de faturas passa a adaptar valores financeiros extensos ao espaço disponível sem ampliar a área visual.
- `1.5` — 2026-07-24 — Valores de lançamentos de cartão padronizados com a fonte compacta dos lançamentos de conta.
- `1.4` — 2026-07-23 — Integrada a sugestão local de categoria e subcategoria por histórico exato.
- `1.3` — 2026-07-17 — Lançamentos com competência calculada em fatura paga passam automaticamente para a próxima fatura aberta.
- `1.2` — 2026-07-05 — Faturas conciliadas e não pagas passam a impactar o saldo previsto da conta preferencial no mês de vencimento.
- `1.1` — 2026-06-30 — Busca textual e filtro de conciliação na lista da fatura.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[contas-correntes]]
- [[lancamentos]]
- [[limites-gastos]]
- [[relatorios]]
- [[importacao-organizze]]
- [[arquitetura]]
