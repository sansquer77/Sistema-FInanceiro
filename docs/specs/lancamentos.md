---
tipo: spec
area: lancamentos
status: implementado
versao: 1.4
atualizado: 2026-07-24
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
> **implementado** · área: `lancamentos` · atualizado em 2026-07-24 · relacionados: [[contas-correntes]], [[categorias-tags-gestao]], [[cartoes]], [[investimentos-portfolio]]

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
- Ao final de cada grupo diário na tela de Lançamentos, `Saldo previsto no dia` considera todos os lançamentos até a data e `Saldo conciliado no dia` considera somente lançamentos com `reconciled_at`, ambos partindo do saldo inicial da conta selecionada.

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

## Changelog

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
