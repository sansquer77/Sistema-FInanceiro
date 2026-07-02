---
tipo: spec
area: limites
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[categorias-tags-gestao]]"
  - "[[cartoes]]"
  - "[[relatorios]]"
  - "[[arquitetura]]"
tags: [spec, "area/limites"]
aliases: ["Limites de Gastos", "Budgets", "Metas"]
---

# Limites de Gastos

> [!info] Status
> **implementado** · área: `limites` · atualizado em 2026-06-29 · relacionados: [[categorias-tags-gestao]], [[cartoes]], [[relatorios]]

## Problema

O usuário precisa estabelecer metas de gastos mensais por categoria e subcategoria e monitorar o andamento do consumo em relação a essas metas.

## Usuário

Qualquer usuário autenticado localmente que queira controlar seu orçamento de despesas.

## Jornada

1. O usuário seleciona a funcionalidade de Limites de Gastos.
2. Define o mês de competência (`AAAA-MM`), a categoria de despesa (e opcionalmente uma subcategoria específica) e o valor limite.
3. Acompanha o progresso comparando a meta com o acumulado de transações reais do período.
4. Quando algum limite do mês corrente é ultrapassado, o menu de Limites exibe alerta visual e o Cockpit exibe um farol com link direto para a função.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Obrigatório. Mês de competência. |
| `categoria_id` | FK | Obrigatório. Deve ter `group_type = expense`. |
| `subcategoria_id` | FK | Opcional. Se informado, limite é específico para ela. |
| `valor` | inteiro (centavos) | Obrigatório. Deve ser maior que zero. |

## Regras

- Os limites aplicam-se apenas a categorias cujo `group_type` seja `expense` (despesa).
- Se uma subcategoria for selecionada, o limite é específico para ela; caso contrário, aplica-se a toda a categoria.
- O consumo considera despesas em contas pelo mês da data do lançamento.
- O consumo considera despesas em cartões pela fatura aberta do mês (`invoice_month`), mesmo quando a data da compra pertence ao mês anterior. Ver [[cartoes]].
- Pagamentos de fatura não removem o consumo do limite — o limite mede competência/gasto da fatura, não a quitação.
- É permitida apenas uma única meta por período (`AAAA-MM`), categoria e subcategoria (restrição UNIQUE no banco).
- O limite deve ser um valor monetário positivo maior que zero.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/spending-limits` |
| `GET` | `/api/spending-limits?month=AAAA-MM` |
| `POST` | `/api/spending-limits` |
| `PUT` | `/api/spending-limits/{id}` |
| `DELETE` | `/api/spending-limits/{id}` |

Tabelas: `spending_limits`, `categories`, `subcategories`.

## Critérios de aceite

- Dado a criação de uma meta de R$ 500,00 para "Alimentação" em "2026-06", quando consultada, ela aparece com o consumo atualizado.
- Dado uma tentativa de cadastrar meta duplicada para o mesmo mês/categoria, quando executada, o sistema atualiza a meta existente ou retorna erro de conflito.
- Dado a exclusão de um limite, quando executada, nenhuma transação financeira é afetada.
- Dado despesas de cartão na fatura aberta do mês, quando computadas, impactam o limite da categoria/subcategoria correspondente.
- Dado um limite ultrapassado no mês corrente, quando exibido, o menu de Limites e o Cockpit exibem alertas visuais.

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[categorias-tags-gestao]]
- [[cartoes]]
- [[relatorios]]
- [[arquitetura]]
