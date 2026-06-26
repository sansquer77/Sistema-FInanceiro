# Gestao de Categorias e Tags

## Objetivo

Permitir que o usuario mantenha a taxonomia usada nos lancamentos financeiros.

## Estado

Implementado para categorias, subcategorias e tags.

## Regras funcionais

- Toda transacao deve ter exatamente uma categoria.
- Toda transacao pode ter uma subcategoria opcional.
- Toda transacao deve ter uma ou mais tags.
- Categorias, subcategorias e tags pertencem ao usuario autenticado.
- O usuario pode listar, criar, renomear e excluir itens nao utilizados.
- Categorias, subcategorias e tags usadas em lancamentos nao podem ser excluidas.
- Importacoes do Organizze podem criar automaticamente categorias, subcategorias e tags inexistentes.
- Tags informadas em uma mesma celula devem ser separadas quando houver separadores suportados.

## Modelo de dados

- `categories`: cadastro de categorias por usuario.
- `subcategories`: subcategorias vinculadas a uma categoria do mesmo usuario.
- `tags`: cadastro de tags por usuario.
- `transactions.category_id`: categoria unica do lancamento.
- `transactions.subcategory_id`: subcategoria opcional.
- `transaction_tags`: vinculo muitos-para-muitos entre lancamentos e tags.

## API

- `GET /api/categories`
- `POST /api/categories`
- `PUT /api/categories/{id}`
- `DELETE /api/categories/{id}`
- `POST /api/subcategories`
- `PUT /api/subcategories/{id}`
- `DELETE /api/subcategories/{id}`
- `GET /api/tags`
- `POST /api/tags`
- `PUT /api/tags/{id}`
- `DELETE /api/tags/{id}`

## Criterios de aceite

- O modulo exibe categorias e tags com contagem de lancamentos em uso.
- Renomear uma categoria, subcategoria ou tag reflete nos lancamentos relacionados.
- Excluir item em uso e bloqueado com mensagem clara.
- Um lancamento manual aceita varias tags separadas por virgula.
- Um lancamento importado persiste todas as tags reconhecidas.
