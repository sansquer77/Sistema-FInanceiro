---
tipo: spec
area: importacao
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[contas-correntes]]"
  - "[[cartoes]]"
  - "[[categorias-tags-gestao]]"
  - "[[lancamentos]]"
  - "[[adr/0004-importador-xls-sem-dependencia]]"
  - "[[arquitetura]]"
tags: [spec, "area/importacao"]
aliases: ["Importação", "Importação Organizze"]
---

# Importação

> [!info] Status
> **implementado** · área: `importacao` · atualizado em 2026-06-29 · relacionados: [[contas-correntes]], [[cartoes]], [[categorias-tags-gestao]], [[adr/0004-importador-xls-sem-dependencia]]

## Problema

O usuário precisa importar movimentações de contas e cartões a partir de arquivos exportados do Organizze ou de planilhas modelo do próprio sistema, preservando categorias, subcategorias, tags e competência de fatura correta.

## Usuário

Usuário que está migrando dados de outro sistema ou que deseja lançar movimentações em massa via planilha.

## Jornada

1. O usuário acessa a área de Importação.
2. Escolhe o tipo: exportação do Organizze ou modelo do sistema.
3. Seleciona a conta ou cartão de destino.
4. Faz upload do arquivo (`.xls`, `.csv` ou `.xlsx`).
5. O sistema processa e exibe o resumo: total lido, total importado, total ignorado e motivos das linhas rejeitadas.

## Dados — Colunas reconhecidas

| Coluna | Regra |
|---|---|
| Data | ISO (`YYYY-MM-DD`), formato Organizze (`DD.MM.YYYY`) ou data serializada pelo Excel. |
| Descrição | Obrigatório. |
| Categoria | Obrigatório para receitas, despesas e investimentos. |
| Subcategoria | Opcional. |
| Valor | Formato brasileiro com vírgula (`66,02`) ou numérico do Excel. |
| Situação | Apenas linhas com `Pago` são importadas. |
| Tags | Opcional. Múltiplas tags separadas por separador suportado. |
| Informações adicionais | Opcional. |
| Tipo | Tipo do lançamento. |
| Conta destino | FK para transferências e câmbio. |
| Competência da fatura | `invoice_month` para importações de cartão. |

## Modelos do sistema

- `GET /api/import/template?target=account` — download do modelo de contas (`.xlsx` com abas de lançamentos, categorias/subcategorias, tags e contas).
- `GET /api/import/template?target=card` — download do modelo de cartões (`.xlsx` com abas de lançamentos, categorias/subcategorias e tags).

## Regras

- A importação de conta exige que o usuário escolha uma conta ativa de destino.
- A importação de cartão exige que o usuário escolha um cartão ativo de destino.
- Cada linha importada deve ter descrição, data válida e valor diferente de zero.
- Categoria é obrigatória para receitas, despesas e investimentos. Transferências e câmbio não exigem categoria.
- Linhas com situação diferente de `Pago` não afetam saldo e aparecem como ignoradas no resultado.
- Valores positivos entram como receita; negativos como despesa.
- Categorias, subcategorias e tags inexistentes são criadas automaticamente para o usuário autenticado. Ver [[categorias-tags-gestao]].
- Quando a coluna Tags trouxer mais de uma tag, todas devem ser vinculadas ao lançamento.
- Arquivos Excel podem trazer valores numéricos formatados visualmente; o parser usa o valor real da célula sem multiplicações indevidas.
- Importações de cartão preenchem `invoice_month` e consideram o mês da fatura para relatórios e limites. Ver [[cartoes]].
- A importação retorna resumo com total lido, total importado, total ignorado e motivos das primeiras linhas rejeitadas.
- O parser `.xls` é implementado sem dependência externa. Ver [[adr/0004-importador-xls-sem-dependencia]].

## Regras de segurança

- A rota de importação exige sessão autenticada.
- A conta ou cartão de destino precisa pertencer ao usuário autenticado e estar ativo.
- O upload aceita arquivos de até **5 MB**.
- A importação não aceita identificadores de outro usuário para contas, cartões, categorias ou tags.
- Dados textuais importados são normalizados antes de persistir.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/import/template?target=account` |
| `GET` | `/api/import/template?target=card` |
| `POST` | `/api/import/organizze-transactions` |
| `POST` | `/api/import/system-template` |

Tabelas: `transactions`, `credit_card_transactions`, `transaction_tags`, `credit_card_transaction_tags`, `categories`, `subcategories`, `tags`, `checking_accounts`, `credit_cards`.

## Critérios de aceite

- Dado um arquivo `.xls` exportado pelo Organizze, quando importado, é lido sem instalação manual de pacote externo.
- Dado um arquivo `.csv` ou `.xlsx` com colunas reconhecidas, quando importado, é aceito normalmente.
- Dado o final da importação de conta, quando consultado, os saldos refletem apenas as linhas importadas com situação `Pago`.
- Dado o final da importação de cartão, quando consultado, os lançamentos aparecem na fatura correta.
- Dado linhas rejeitadas, quando exibidas, mostram número da linha e motivo da rejeição.
- Dado a listagem de lançamentos importados, quando exibida, mostra categoria, subcategoria e tags quando existirem.

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[contas-correntes]]
- [[cartoes]]
- [[categorias-tags-gestao]]
- [[lancamentos]]
- [[adr/0004-importador-xls-sem-dependencia]]
- [[arquitetura]]
