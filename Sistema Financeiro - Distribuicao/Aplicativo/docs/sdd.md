# SDD: Spec Development Driven

SDD significa conduzir o desenvolvimento por especificacoes. Antes de alterar o app, descrevemos o comportamento esperado em linguagem clara e so entao implementamos.

## Fluxo

1. Criar ou atualizar uma especificacao em `docs/specs/`.
2. Validar jornada do usuario, dados e criterios de aceite.
3. Atualizar `docs/requisitos.md` se o escopo geral mudar.
4. Atualizar `docs/arquitetura.md` se houver novo fluxo, rota, tabela ou decisao tecnica.
5. Implementar a menor mudanca que cumpre a especificacao.
6. Verificar manualmente ou com testes.

## Modelo de especificacao

```markdown
# Nome da funcionalidade

## Problema

Qual dor ou necessidade esta mudanca resolve?

## Usuario

Quem usa e em qual contexto?

## Jornada

1. Passo inicial.
2. Acao principal.
3. Resultado esperado.

## Dados

- Campo: descricao, tipo e regra.

## Regras

- Regra de negocio verificavel.

## API e dados

- Endpoints, tabelas ou campos afetados.

## Criterios de aceite

- Dado um estado inicial, quando uma acao ocorre, entao o resultado deve ser observavel.

## Fora de escopo

O que nao sera feito nesta entrega.
```

## Criterios para uma boa spec

- Deve ser pequena o bastante para caber em uma entrega.
- Deve evitar detalhes de implementacao prematuros.
- Deve deixar claro o que e sucesso.
- Deve indicar impactos em dados, tela e API.
- Deve ser atualizada quando a implementacao real mudar o comportamento previsto.
