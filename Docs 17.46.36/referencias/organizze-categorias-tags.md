# Referência: Categorias e Tags

Análise feita em 13/06/2026 com conta de teste autorizada.

## Papel dos módulos

Categorias criam a estrutura principal de classificação financeira. Tags adicionam marcações livres e transversais que podem atravessar categorias, contas e cartões.

## Categorias

### Estrutura observada

- Página dedicada em configurações.
- Alternância entre categoria de despesa e categoria de receita.
- Abas/listas para despesas e receitas.
- Categorias principais.
- Subcategorias dentro de categorias.
- Ação para arquivar categoria.
- Ação para adicionar subcategoria.
- Área de categorias arquivadas.

### Entidade sugerida

- `id`
- `user_id`
- `name`
- `kind`: `expense` ou `income`
- `parent_id`
- `archived_at`
- `created_at`
- `updated_at`

### Regras

- Categoria pode ter subcategorias.
- Subcategoria pertence a uma categoria principal do mesmo tipo.
- Categoria usada em lançamentos não deve ser excluída fisicamente.
- Arquivar categoria remove das seleções padrão, mas preserva histórico.
- Relatórios devem agrupar por categoria principal e permitir detalhar subcategorias.

## Tags

### Estrutura observada

- Página dedicada em configurações.
- Lista simples de tags.
- Ações de editar e excluir.
- Tags são independentes de tipo de lançamento.

### Entidade sugerida

- `id`
- `user_id`
- `name`
- `color`
- `created_at`
- `updated_at`

### Associação com lançamentos

Tabela sugerida:

- `transaction_id`
- `tag_id`

### Regras

- Uma transação pode ter várias tags.
- Uma tag pode ser usada em várias transações.
- Excluir tag remove a associação futura, mas precisa preservar ou tratar histórico conforme decisão de produto.
- Tags devem estar disponíveis nos filtros de lançamentos e relatórios.

## Diferença entre categoria e tag

- Categoria responde "que tipo de gasto ou receita é este?".
- Tag responde "a que contexto, projeto, pessoa, ativo ou evento isto pertence?".

## Critérios de aceite futuros

- O usuário cria categoria de despesa e categoria de receita.
- O usuário cria subcategoria dentro de categoria principal.
- O usuário arquiva categoria sem apagar lançamentos históricos.
- O usuário cria tags livres.
- O usuário filtra lançamentos e relatórios por tag.
