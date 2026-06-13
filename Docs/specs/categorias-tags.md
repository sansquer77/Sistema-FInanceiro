# Spec: Categorias e Tags

## Problema

O usuário precisa classificar lançamentos para filtrar, agrupar e gerar relatórios úteis.

## Jornada

1. O usuário cria categorias de despesa e receita.
2. Cria subcategorias quando precisa de detalhe.
3. Cria tags livres para contextos transversais.
4. Usa categorias e tags em lançamentos.
5. Filtra relatórios por essas dimensões.

## Regras

- Categoria tem tipo: despesa ou receita.
- Subcategoria herda o tipo da categoria principal.
- Categoria usada em lançamento não deve ser apagada fisicamente.
- Tags podem ser associadas a vários lançamentos.
- Lançamentos podem ter várias tags.

## Critérios de aceite

- O usuário cria, edita e arquiva categorias.
- O usuário cria subcategoria dentro de uma categoria.
- O usuário cria, edita e exclui tags.
- Relatórios conseguem agrupar por categoria e por tag.
