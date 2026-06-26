# Importacao

## Objetivo

Permitir importar movimentacoes de contas e cartoes a partir dos modelos do sistema ou de arquivos exportados do Organizze, preservando categorias, subcategorias, tags e competencia correta.

## Estado

Implementado.

## Modelos do sistema

- O sistema deve oferecer download de modelo em `.xlsx`.
- O modelo de contas deve ter uma aba de lancamentos e abas auxiliares para categorias/subcategorias, tags e contas.
- O modelo de cartoes deve ter uma aba de lancamentos e abas auxiliares para categorias/subcategorias e tags.
- A importacao e feita para uma conta ou cartao escolhido pelo usuario antes do upload.
- A aba de contas serve para relacionar campos como `conta_destino_id` em transferencias e cambio.

## Colunas reconhecidas

- Data
- Descricao
- Categoria
- Subcategoria
- Valor
- Situacao
- Tags
- Informacoes adicionais
- Tipo
- Conta destino
- Competencia da fatura

## Regras funcionais

- A importacao de conta exige que o usuario escolha uma conta ativa de destino.
- A importacao de cartao exige que o usuario escolha um cartao ativo de destino.
- Cada linha importada deve ter descricao, data valida e valor diferente de zero.
- Categoria e obrigatoria para receitas, despesas e investimentos.
- Transferencias e cambio nao exigem categoria nem subcategoria.
- Tags sao opcionais.
- Linhas sem categoria so devem ser rejeitadas quando o tipo exigir categoria.
- Linhas com situacao diferente de `Pago` nao devem afetar saldo e devem aparecer como ignoradas no resultado.
- Valores positivos entram como receita.
- Valores negativos entram como despesa.
- Categorias, subcategorias e tags inexistentes sao criadas automaticamente para o usuario autenticado.
- Quando a coluna Tags trouxer mais de uma tag, todas devem ser vinculadas ao lancamento.
- Tags inexistentes devem ser criadas; tags existentes devem ser reaproveitadas.
- A correlacao entre categoria, subcategoria e tag deve priorizar o objetivo/natureza do lancamento, nao apenas igualdade textual.
- Datas devem aceitar ISO (`YYYY-MM-DD`), formato Organizze (`DD.MM.YYYY`) e datas serializadas pelo Excel.
- Valores devem aceitar formato brasileiro com virgula decimal (`66,02`) e valores numericos do Excel.
- Arquivos Excel podem trazer valores numéricos formatados visualmente; o parser deve usar o valor real da celula sem multiplicacoes indevidas.
- Importacoes de cartao devem preencher a competencia da fatura (`invoice_month`) e considerar o mes da fatura para relatorios e limites.
- A importacao retorna resumo com total lido, total importado, total ignorado e motivos das primeiras linhas rejeitadas.

## Regras de seguranca

- A rota de importacao exige sessao autenticada.
- A conta ou cartao de destino precisa pertencer ao usuario autenticado e estar ativo.
- O upload aceita arquivos de ate 5 MB.
- A importacao nao aceita identificadores de outro usuario para contas, cartoes, categorias ou tags.
- Dados textuais importados devem ser normalizados antes de persistir.

## API e dados

- `GET /api/import/template?target=account`
- `GET /api/import/template?target=card`
- `POST /api/import/organizze-transactions`
- `POST /api/import/system-template`
- Tabelas: `transactions`, `credit_card_transactions`, `transaction_tags`, `credit_card_transaction_tags`, `categories`, `subcategories`, `tags`, `checking_accounts`, `credit_cards`.

## Criterios de aceite

- Um arquivo `.xls` exportado pelo Organizze e lido sem instalacao manual de pacote externo.
- Um arquivo `.csv` ou `.xlsx` com colunas reconhecidas tambem e aceito.
- Ao final da importacao, os saldos da conta escolhida refletem apenas as linhas importadas.
- Ao final da importacao de cartao, os lancamentos aparecem na fatura correta.
- Linhas rejeitadas sao exibidas para o usuario com numero da linha e motivo.
- A listagem de lancamentos exibe categoria, subcategoria e tags quando existirem.
