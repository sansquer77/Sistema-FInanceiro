# Spec: Limites de Gastos

## Status

**Implementado**

## Problema

O usuário precisa estabelecer metas de gastos mensais por categoria e subcategoria e monitorar o andamento do consumo em relação a essas metas.

## Usuário

Qualquer usuário autenticado localmente que queira controlar seu orçamento de despesas.

## Jornada

1. O usuário seleciona a funcionalidade de Limites de Gastos.
2. Define o mês de competência (formato `AAAA-MM`), a categoria de despesa (e opcionalmente uma subcategoria específica) e o valor limite.
3. Acompanha o progresso do limite de gastos comparando a meta com o acumulado de transações reais correspondente àquele período e classificação.

## Regras

- Os limites aplicam-se apenas a categorias cujo `group_type` seja `expense` (despesa).
- Se uma subcategoria for selecionada, o limite é específico para ela. Caso contrário, aplica-se a toda a categoria.
- O consumo considera despesas em contas pelo mês da data do lançamento.
- O consumo considera despesas em cartões pela fatura aberta do mês (`invoice_month`), mesmo quando a data da compra pertence ao mês anterior.
- Pagamentos de fatura não removem o consumo do limite; o limite mede competência/gasto da fatura, não a quitação.
- É permitida apenas uma única meta por período (`AAAA-MM`), categoria e subcategoria (garantido por restrição UNIQUE no banco de dados).
- O limite deve ser um valor monetário positivo maior que zero.
- Quando algum limite do mês corrente é ultrapassado, o menu de Limites recebe alerta visual e o Cockpit exibe um farol com link direto para a função.

## API e Dados

- Rotas:
  - `GET /api/spending-limits` (opcionalmente filtrado por `month`)
  - `POST /api/spending-limits`
  - `PUT /api/spending-limits/{id}`
  - `DELETE /api/spending-limits/{id}`
- Tabelas: `spending_limits`, `categories`, `subcategories`.

## Criterios de Aceite

- O usuário consegue definir e salvar uma meta de despesa de R$ 500,00 para a categoria "Alimentação" no mês "2026-06".
- Ao tentar cadastrar uma meta duplicada para o mesmo mês/categoria, o sistema atualiza a meta existente ou retorna um erro de conflito.
- A exclusão de um limite de gastos não altera nenhuma transação financeira do usuário.
- Despesas de cartão na fatura aberta do mês impactam o limite da categoria/subcategoria correspondente.
