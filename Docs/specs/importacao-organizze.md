# Modulo de Importacao Organizze

## Objetivo

Permitir importar movimentacoes exportadas pelo Organizze no modelo `.xls` com as colunas:

- Data
- Descricao
- Categoria
- Valor
- Situacao
- Tags
- Informacoes adicionais

## Regras Funcionais

- A importacao exige que o usuario escolha uma conta ativa de destino.
- Cada linha importada deve ter descricao, categoria, tag, data valida e valor diferente de zero.
- Linhas sem categoria ou sem tag nao devem ser importadas.
- Linhas com situacao diferente de `Pago` nao devem afetar saldo e devem aparecer como ignoradas no resultado.
- Valores positivos entram como receita.
- Valores negativos entram como despesa.
- Categorias e tags inexistentes sao criadas automaticamente para o usuario autenticado.
- A importacao deve retornar resumo com total lido, total importado, total ignorado e motivos das primeiras linhas rejeitadas.

## Regras de Seguranca

- A rota de importacao exige sessao autenticada.
- A conta de destino precisa pertencer ao usuario autenticado e estar ativa.
- O upload aceita arquivos de ate 5 MB.
- A importacao nao aceita identificadores de outro usuario para contas, categorias ou tags.
- Dados textuais importados devem ser normalizados antes de persistir.

## Mapeamento de Dados

| Organizze | Sistema Financeiro |
| --- | --- |
| Data | `transactions.date` |
| Descricao | `transactions.description` |
| Categoria | `categories.name` e `transactions.category_id` |
| Valor positivo | `transactions.type = income` |
| Valor negativo | `transactions.type = expense` |
| Tags | `tags.name` e `transactions.tag_id` |
| Informacoes adicionais | `transactions.notes` |

## Criterios de Aceite

- Um arquivo `.xls` exportado pelo Organizze deve ser lido sem depender de instalacao manual de pacote externo.
- Ao final da importacao, os saldos da conta escolhida devem refletir apenas as linhas importadas.
- Linhas rejeitadas devem ser exibidas para o usuario com numero da linha e motivo.
- A listagem de lancamentos deve exibir categoria e tag quando existirem.
