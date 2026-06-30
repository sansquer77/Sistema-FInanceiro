---
tipo: spec
area: classificacao
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[lancamentos]]"
  - "[[importacao-organizze]]"
  - "[[relatorios]]"
  - "[[limites-gastos]]"
  - "[[arquitetura]]"
tags: [spec, "area/classificacao"]
aliases: ["Categorias e Tags", "Classificações"]
---

# Categorias e Tags

> [!info] Status
> **implementado** · área: `classificacao` · atualizado em 2026-06-29 · relacionados: [[lancamentos]], [[importacao-organizze]], [[relatorios]], [[limites-gastos]]

## Problema

O usuário precisa manter a taxonomia usada nos lançamentos financeiros — categorias, subcategorias e tags — e ser protegido de exclusões acidentais que quebrariam a classificação de lançamentos existentes.

## Usuário

Qualquer usuário autenticado localmente que classifique seus lançamentos por natureza e marcadores personalizados.

## Jornada

1. Usuário acessa a área de Classificações.
2. Lista categorias (com contagem de lançamentos em uso) e cria, renomeia ou exclui as que não estão em uso.
3. Associa subcategorias a categorias existentes.
4. Gerencia tags de forma independente das categorias.
5. Ao criar um lançamento, seleciona categoria, subcategoria opcional e uma ou mais tags.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `categoria.nome` | texto | Obrigatório, único por usuário. |
| `categoria.group_type` | enum | `income`, `expense` ou `investment`. |
| `subcategoria.nome` | texto | Obrigatório. |
| `subcategoria.categoria_id` | FK | Obrigatório. Deve pertencer ao mesmo usuário. |
| `tag.nome` | texto | Obrigatório, único por usuário. |

## Regras

- Toda transação deve ter exatamente uma categoria.
- Toda transação pode ter uma subcategoria opcional.
- Toda transação pode ter uma ou mais tags (N:M via `transaction_tags` / `credit_card_transaction_tags`).
- Categorias, subcategorias e tags pertencem ao usuário autenticado.
- O usuário pode listar, criar, renomear e excluir itens **não utilizados**.
- Categorias, subcategorias e tags **em uso** em lançamentos não podem ser excluídas.
- Importações podem criar automaticamente categorias, subcategorias e tags inexistentes para o usuário autenticado. Ver [[importacao-organizze]].
- Tags informadas em uma mesma célula devem ser separadas quando houver separadores suportados (vírgula, ponto-e-vírgula).

## API e dados

| Método | Rota |
|---|---|
| `GET/POST` | `/api/categories` |
| `PUT/DELETE` | `/api/categories/{id}` |
| `POST` | `/api/subcategories` |
| `PUT/DELETE` | `/api/subcategories/{id}` |
| `GET/POST` | `/api/tags` |
| `PUT/DELETE` | `/api/tags/{id}` |

Tabelas: `categories`, `subcategories`, `tags`, `transaction_tags`, `credit_card_transaction_tags`.

## Critérios de aceite

- Dado a listagem de categorias, quando exibida, mostra cada categoria com a contagem de lançamentos em uso.
- Dado uma categoria renomeada, quando listada, o novo nome reflete em todos os lançamentos relacionados.
- Dado uma tentativa de excluir item em uso, quando executada, a operação é bloqueada com mensagem clara.
- Dado um lançamento manual, quando criado com múltiplas tags separadas por vírgula, todas as tags são vinculadas.
- Dado um lançamento importado, quando processado, todas as tags reconhecidas são persistidas.

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[lancamentos]]
- [[importacao-organizze]]
- [[relatorios]]
- [[limites-gastos]]
- [[arquitetura]]
