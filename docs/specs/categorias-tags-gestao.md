---
tipo: spec
area: classificacao
status: implementado
versao: 1.2
atualizado: 2026-09-04
relacionados:
  - "[[lancamentos]]"
  - "[[importacao-dados]]"
  - "[[relatorios]]"
  - "[[limites-gastos]]"
  - "[[arquitetura]]"
tags: [spec, "area/classificacao"]
aliases: ["Categorias e Tags", "Classificações"]
---

# Categorias e Tags

> [!info] Status
> **implementado** · área: `classificacao` · atualizado em 2026-09-04 · relacionados: [[lancamentos]], [[importacao-dados]], [[relatorios]], [[limites-gastos]]

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
- Importações podem criar automaticamente categorias, subcategorias e tags inexistentes para o usuário autenticado. Ver [[importacao-dados]].
- Tags informadas em uma mesma célula devem ser separadas quando houver separadores suportados (vírgula, ponto-e-vírgula).
- Categorias e subcategorias podem alimentar a evolução temporal dos relatórios por meio de séries mensais. Ver [[relatorios]].
- A busca de Categorias e de Tags é local aos dados já carregados, ignora acentos e não dispara nova consulta ao backend.
- A busca de Categorias considera tanto o nome da categoria quanto o de suas subcategorias; quando uma subcategoria corresponde, seu grupo é aberto para revelar o resultado.
- Subcategorias permanecem recolhidas por categoria até abertura explícita, preservada enquanto a tela estiver montada.
- Renomear e excluir são ações secundárias agrupadas em um menu contextual acessível por item, sem alterar as proteções de domínio existentes.

## API e dados

| Método | Rota |
|---|---|
| `GET/POST` | `/api/categories` |
| `PUT/DELETE` | `/api/categories/{id}` |
| `POST` | `/api/subcategories` |
| `PUT/DELETE` | `/api/subcategories/{id}` |
| `GET/POST` | `/api/tags` |
| `PUT/DELETE` | `/api/tags/{id}` |
| `GET` | `/api/reports/category-evolution?category_id={id}&subcategory_id={id}&period={periodo}` |

Tabelas: `categories`, `subcategories`, `tags`, `transaction_tags`, `credit_card_transaction_tags`.

## Critérios de aceite

- Dado a listagem de categorias, quando exibida, mostra cada categoria com a contagem de lançamentos em uso.
- Dado uma categoria renomeada, quando listada, o novo nome reflete em todos os lançamentos relacionados.
- Dado uma tentativa de excluir item em uso, quando executada, a operação é bloqueada com mensagem clara.
- Dado um lançamento manual, quando criado com múltiplas tags separadas por vírgula, todas as tags são vinculadas.
- Dado um lançamento importado, quando processado, todas as tags reconhecidas são persistidas.
- Dado um termo com ou sem acentos, quando digitado na busca de Categorias ou Tags, então somente itens carregados cujo nome corresponda permanecem visíveis, sem requisição adicional.
- Dado um termo que corresponda apenas a uma subcategoria, quando o filtro é aplicado, então a categoria pai permanece visível e a lista correspondente é aberta.
- Dado uma categoria com subcategorias sem filtro ativo, quando a lista é apresentada, então suas subcategorias começam recolhidas e podem ser abertas por teclado ou ponteiro.
- Dado uma categoria, subcategoria ou tag, quando o usuário abre Mais ações, então Renomear e Excluir ficam disponíveis com nomes acessíveis e mantêm o comportamento atual.
- Dado uma busca sem correspondência, quando a lista é atualizada, então um estado vazio informa que nenhum resultado foi encontrado sem confundir com ausência de cadastros.

## Plano de implementação

- [x] Adicionar buscas locais independentes e contadores acessíveis no HTML da tela. Fecha: critérios 6 e 10.
- [x] Implementar filtro puro normalizado, incluindo correspondência de subcategorias. Fecha: critérios 6 e 7.
- [x] Tornar subcategorias recolhíveis e preservar expansão durante a sessão da view. Fecha: critérios 7 e 8.
- [x] Compactar ações secundárias em menu contextual nativo. Fecha: critério 9.
- [x] Cobrir contratos de filtro, ausência de rede e estrutura acessível com testes automatizados. Fecha: critérios 6 a 10.

## Changelog

- `1.2` — 2026-09-04 — Categorias e Tags ganham busca local normalizada, subcategorias recolhíveis e menus contextuais de ações para reduzir carga visual em listas extensas.
- `1.1` — 2026-06-30 — Relação com evolução temporal de categorias/subcategorias documentada.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[lancamentos]]
- [[importacao-dados]]
- [[relatorios]]
- [[limites-gastos]]
- [[arquitetura]]
