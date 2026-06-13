# Gestao de Categorias e Tags

## Objetivo

Permitir que o usuario mantenha a taxonomia usada nos lancamentos financeiros.

## Regras Funcionais

- Toda transacao deve ter exatamente uma categoria.
- Toda transacao deve ter uma ou mais tags.
- Categorias e tags pertencem ao usuario autenticado.
- O usuario pode listar, criar e renomear categorias e tags.
- O usuario pode excluir categorias e tags apenas quando nao houver lancamentos vinculados.
- Importacoes do Organizze podem criar automaticamente categorias e tags inexistentes.
- Tags importadas em uma mesma celula devem ser tratadas como multiplas quando houver separadores suportados.

## Modelo de Dados

- `categories`: cadastro de categorias por usuario.
- `tags`: cadastro de tags por usuario.
- `transactions.category_id`: categoria unica do lancamento.
- `transaction_tags`: vinculo muitos-para-muitos entre lancamentos e tags.

## Criterios de Aceite

- O modulo deve exibir categorias e tags com contagem de lancamentos em uso.
- Renomear uma categoria ou tag deve refletir nos lancamentos relacionados.
- Excluir item em uso deve ser bloqueado com mensagem clara.
- Um lancamento manual deve aceitar varias tags separadas por virgula.
- Um lancamento importado deve persistir todas as tags reconhecidas.
