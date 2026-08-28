---
tipo: spec
area: relatorios
status: implementado
versao: 1.0
atualizado: 2026-08-26
relacionados:
  - "[[relatorios]]"
  - "[[arquitetura]]"
tags: [spec, "area/relatorios", "status/implementado"]
aliases: ["Bugfix: Agrupamento Subcategoria e Evolução"]
---

# Bugfix: Agrupamento incorreto no relatório de subcategorias e evolução de "Sem subcategoria"

> [!info] Status
> **implementado** · área: `relatorios` · atualizado em 2026-08-26 · relacionados: [[relatorios]], [[arquitetura]]

## Problema

Dois problemas relacionados no relatório de subcategorias (aba "Subcategorias" em Relatórios):

1. **Tabela**: A linha `Cuidados Pessoais / Sem subcategoria` exibia valor incorreto (R$ 9.044,00) para agosto/2026, agregando indevidamente lançamentos de outras subcategorias. O valor correto é R$ 490,00 (apenas o lançamento *Posto de Serviços* da fatura Porto, competência agosto/2026).

2. **Gráfico de evolução**: Ao clicar no botão de evolução temporal da linha `Categoria / Sem subcategoria`, o gráfico exibia o total de TODA a categoria (todas as subcategorias somadas) em vez de apenas os lançamentos sem subcategoria. Exemplo: para Cuidados Pessoais em agosto/2026, o gráfico mostrava ~R$ 3.621 (total da categoria) em vez de R$ 490 (apenas "Sem subcategoria").

Causa raiz: o frontend enviava `subcategory_id="None"` (string) para a API de evolução, mas o backend tratava valor não-numérico como "sem filtro", retornando o total da categoria inteira.

## Usuário

Usuário autenticado que acessa Relatórios → Subcategorias para analisar despesas por subcategoria no mês selecionado, e usa o botão de evolução temporal para ver a série histórica de uma subcategoria específica.

## Jornada

1. Usuário abre Relatórios.
2. Seleciona aba "Subcategorias".
3. Navega para agosto/2026.
4. Visualiza a linha `Cuidados Pessoais / Sem subcategoria` com valor correto (R$ 490,00).
5. Clica no botão de evolução temporal (ícone de gráfico) dessa linha.
6. O gráfico de evolução exibe a série histórica apenas dos lançamentos de Cuidados Pessoais **sem subcategoria**, não o total da categoria.

## Dados

- `state.cardTransactions`: array de transações de cartão carregado via `fetchAllListed("/api/credit-card-transactions")`.
- `state.transactions`: array de transações de conta carregado via `fetchAllListed("/api/transactions")`.
- `state.reportMonth`: mês selecionado no formato `AAAA-MM`.
- Cada transação possui `category_name`, `subcategory_name` (pode ser `null`), `invoice_month` (cartão) ou `date` (conta), `type` (`income`/`expense`/`investment`), `amount`.
- `subcategory_id`: inteiro para subcategoria específica, `null` para "Sem subcategoria".

## Regras

- Lançamentos de cartão entram nos relatórios pela competência da fatura (`invoice_month`), não pela data da compra.
- Lançamentos de conta entram pela data do lançamento (`date`).
- O relatório de subcategorias agrupa por `Categoria / Subcategoria`; lançamentos sem subcategoria aparecem como `Categoria / Sem subcategoria`.
- Apenas transações do mês selecionado (`state.reportMonth`) compõem o relatório.
- Pagamentos de fatura (lançamentos de conta com `is_credit_card_payment=true`) são excluídos das análises de despesa.
- **Evolução de "Sem subcategoria"**: a API `/api/reports/category-evolution` deve aceitar `subcategory_id=null` (ou `none`, `-1`) para filtrar apenas lançamentos com `subcategory_id IS NULL`.

## API e dados

- Correção no backend: `financeiro/categories.py` (`get_category_evolution`) e `app.py` (`handle_category_evolution`) para suportar filtro por `subcategory_id IS NULL`.
- Correção no frontend: `web/modules/reports-view.js` já envia `subcategoryId` como string "None" para linhas "Sem subcategoria"; backend agora reconhece esse valor.

## Critérios de aceite

- Dado o usuário visualizando o relatório de subcategorias para agosto/2026, quando a linha `Cuidados Pessoais / Sem subcategoria` é exibida, então o valor é R$ 490,00 (apenas o lançamento *Posto de Serviços* da fatura Porto, competência agosto/2026).
- Dado o usuário visualizando o relatório de subcategorias para agosto/2026, quando as demais linhas de Cuidados Pessoais são exibidas (ex.: `Cuidados Pessoais / Vestuário`, `Cuidados Pessoais / Academia...`), então cada linha mostra apenas os lançamentos da respectiva subcategoria no mês.
- Dado o usuário alternando o mês do relatório, quando o mês muda, então os totais de todas as linhas refletem exatamente a competência/mês selecionado.
- Dado um lançamento de cartão com `subcategory_name` preenchido e `invoice_month` = mês do relatório, quando o relatório é renderizado, então o lançamento aparece na linha da subcategoria correspondente, **não** em `Sem subcategoria`.
- Dado um lançamento de conta com `subcategory_name` preenchido e `date` no mês do relatório, quando o relatório é renderizado, então o lançamento aparece na linha da subcategoria correspondente.
- **Dado o usuário clicando no botão de evolução da linha `Categoria / Sem subcategoria`, quando o gráfico é exibido, então a série mostra apenas os lançamentos daquela categoria com `subcategory_id IS NULL` (não o total da categoria).**
- **Dado o usuário visualizando a evolução de `Cuidados Pessoais / Sem subcategoria` para agosto/2026, quando o gráfico é renderizado, então o valor do mês é R$ 490,00 (não R$ 3.621,18 que é o total da categoria).**

## Pendências

> [!question] Pendências
> - [ ] Confirmar se o bug ocorria também no relatório de categorias (aba "Categorias") ou apenas no de subcategorias.
> - [ ] Verificar se há outros usuários/meses afetados pelo mesmo padrão.
> - [ ] Reiniciar o servidor para que as alterações no backend (`app.py`, `financeiro/categories.py`) entrem em vigor.

## Fora de escopo

- Alterações no banco de dados.
- Mudanças no relatório de tags, demonstrativo mensal ou evolução de categoria (exceto o filtro por NULL subcategory).
- Correção de dados históricos (launchamentos já cadastrados).

## Plano de implementação

- [x] Passo 1 — Corrigir `groupReportItems` em `web/modules/reports-view.js` para garantir que string vazia/whitespace em `item.subcategory` seja tratada como "Sem subcategoria", não agregando lançamentos com subcategoria válida. Fecha: critérios 1, 2, 4, 5.
- [x] Passo 2 — Atualizar `handle_category_evolution` em `app.py` para reconhecer `subcategory_id=null|none|-1` como "filtrar por subcategory_id IS NULL". Fecha: critérios 6, 7.
- [x] Passo 3 — Atualizar `get_category_evolution` em `financeiro/categories.py` para aceitar `subcategory_id: int | str | None` e gerar SQL com `IS NULL` quando valor for `"null"`. Fecha: critérios 6, 7.
- [ ] Passo 4 — Reiniciar servidor para aplicar alterações no backend. Fecha: todos os critérios.
- [ ] Passo 5 — Testar manualmente no navegador: abrir Relatórios → Subcategorias → agosto/2026, confirmar valor da linha `Cuidados Pessoais / Sem subcategoria` = R$ 490,00, clicar em evolução e confirmar gráfico mostrando apenas R$ 490,00 para agosto/2026. Fecha: todos os critérios.

## Changelog

- `1.0` — 2026-08-26 — Corrigido agrupamento no relatório de subcategorias: a chave de agrupamento trata explicitamente string vazia/whitespace como "Sem subcategoria", garantindo que lançamentos com subcategoria válida não caiam no bucket "Sem subcategoria". Corrigido também a API de evolução de categoria para suportar `subcategory_id=null` (filtro por `subcategory_id IS NULL`), fazendo o gráfico de evolução de "Sem subcategoria" exibir apenas os lançamentos sem subcategoria, não o total da categoria.

## Relacionados

- [[relatorios]]
- [[arquitetura]]