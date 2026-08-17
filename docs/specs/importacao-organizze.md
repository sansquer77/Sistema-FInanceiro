---
tipo: spec
area: importacao
status: implementado
versao: 1.2
atualizado: 2026-08-17
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
> **implementado** · área: `importacao` · atualizado em 2026-08-17 · relacionados: [[contas-correntes]], [[cartoes]], [[categorias-tags-gestao]], [[adr/0004-importador-xls-sem-dependencia]]

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
| Data | ISO (`YYYY-MM-DD`), `DD.MM.YYYY`, `DD/MM/YYYY`, `DD-MM-YYYY` ou data serializada pelo Excel. Data inválida rejeita a linha com motivo `Data invalida.` |
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
| Repetição | Modelo próprio: `avulso` (padrão), `parcelado` ou `recorrente`. Aceita também `single`, `installment` e `recurring`. |
| Parcelas | Modelo próprio: quantidade de parcelas (2 a 120), obrigatória quando Repetição é `parcelado`. |
| Recorrência | Modelo próprio: frequência (`semanal`, `mensal`, `trimestral`, `semestral` ou `anual`), obrigatória quando Repetição é `recorrente`. |
| Média | Modelo próprio: `sim`/`não` para recorrentes usarem o valor médio do histórico (só se aplica a `recorrente`). |

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
- No modelo próprio, uma linha com Repetição `parcelado` gera uma série de N lançamentos parcelados; uma linha `recorrente` gera uma série recorrente (até 120 ocorrências) e pode usar a Média do histórico. Transferências e câmbio são sempre avulsos, mesmo se a linha trouxer Repetição.
- Modelos gerados antes da coluna Repetição (sem `repeticao`, `parcelas`, `recorrencia` e `media`) continuam importando normalmente: as linhas entram como avulsas.
- A importação retorna resumo com total lido, total importado, total ignorado e motivos das primeiras linhas rejeitadas.
- Importações em lote devem processar a leitura/parsing fora da conexão SQLite e persistir cada linha em uma transação curta, preservando sucesso parcial sem segurar lock durante todo o arquivo.
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
- Dado uma linha com data `02.05.2026` (DD.MM.YYYY) no modelo próprio, quando importada, é aceita normalmente.
- Dado uma linha com data inválida, quando importada, é rejeitada com motivo `Data invalida.` sem afetar as demais linhas.
- Dado uma linha parcelada com `parcelas` = 3, quando importada, gera 3 lançamentos da mesma série.
- Dado uma linha recorrente com Média `sim`, quando importada, a série usa o valor médio do histórico.
- Dado um modelo antigo sem as colunas de repetição, quando importado, continua funcionando (linhas avulsas).

## Changelog

- `1.2` — 2026-08-17 — Modelo próprio ganha colunas de repetição (`repeticao`, `parcelas`, `recorrencia`, `media`); datas aceitas ampliadas (`DD/MM/YYYY`, `DD-MM-YYYY`) e data inválida rejeita a linha com motivo explícito.
- `1.1` — 2026-07-03 — Regra de importação em lote atualizada para transações curtas por linha.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[contas-correntes]]
- [[cartoes]]
- [[categorias-tags-gestao]]
- [[lancamentos]]
- [[adr/0004-importador-xls-sem-dependencia]]
- [[arquitetura]]
