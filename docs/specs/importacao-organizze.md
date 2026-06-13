# Importacao Organizze

## Objetivo

Permitir importar movimentacoes exportadas pelo Organizze em `.xls` ou `.csv`.

## Estado

Implementado.

## Colunas reconhecidas

- Data
- Descricao
- Categoria
- Subcategoria
- Valor
- Situacao
- Tags
- Informacoes adicionais

## Regras funcionais

- A importacao exige que o usuario escolha uma conta ativa de destino.
- Cada linha importada deve ter descricao, categoria, ao menos uma tag, data valida e valor diferente de zero.
- Linhas sem categoria ou sem tag nao devem ser importadas.
- Linhas com situacao diferente de `Pago` nao devem afetar saldo e devem aparecer como ignoradas no resultado.
- Valores positivos entram como receita.
- Valores negativos entram como despesa.
- Categorias, subcategorias e tags inexistentes sao criadas automaticamente para o usuario autenticado.
- Quando a coluna Tags trouxer mais de uma tag, todas devem ser vinculadas ao lancamento.
- A importacao retorna resumo com total lido, total importado, total ignorado e motivos das primeiras linhas rejeitadas.

## Regras de seguranca

- A rota de importacao exige sessao autenticada.
- A conta de destino precisa pertencer ao usuario autenticado e estar ativa.
- O upload aceita arquivos de ate 5 MB.
- A importacao nao aceita identificadores de outro usuario para contas, categorias ou tags.
- Dados textuais importados devem ser normalizados antes de persistir.

## API e dados

- `POST /api/import/organizze-transactions`
- Tabelas: `transactions`, `transaction_tags`, `categories`, `subcategories`, `tags`, `checking_accounts`.

## Criterios de aceite

- Um arquivo `.xls` exportado pelo Organizze e lido sem instalacao manual de pacote externo.
- Um arquivo `.csv` com colunas reconhecidas tambem e aceito.
- Ao final da importacao, os saldos da conta escolhida refletem apenas as linhas importadas.
- Linhas rejeitadas sao exibidas para o usuario com numero da linha e motivo.
- A listagem de lancamentos exibe categoria, subcategoria e tags quando existirem.
