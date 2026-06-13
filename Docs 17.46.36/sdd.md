# SDD: Spec Development Driven

SDD significa conduzir o desenvolvimento por especificações. Antes de alterar o app, escrevemos o comportamento esperado em linguagem clara e só então implementamos.

## Fluxo

1. Criar ou atualizar uma especificação em `Docs/specs/`.
2. Validar a jornada do usuário e os critérios de aceite.
3. Implementar a menor mudança que cumpre a especificação.
4. Verificar manualmente ou com testes.
5. Registrar decisões novas na documentação quando afetarem arquitetura ou produto.

## Modelo de especificação

```markdown
# Nome da funcionalidade

## Problema

Qual dor ou necessidade esta mudança resolve?

## Usuário

Quem usa e em qual contexto?

## Jornada

1. Passo inicial.
2. Ação principal.
3. Resultado esperado.

## Dados

- Campo: descrição, tipo e regra.

## Regras

- Regra de negócio verificável.

## Critérios de aceite

- Dado um estado inicial, quando uma ação ocorre, então o resultado deve ser observável.

## Fora de escopo

O que não será feito nesta entrega.
```

## Critérios para uma boa spec

- Deve ser pequena o bastante para caber em uma entrega.
- Deve evitar detalhes de implementação prematuros.
- Deve deixar claro o que é sucesso.
- Deve indicar impactos em dados, tela e API.

## Pasta de specs

Use `Docs/specs/` para funcionalidades específicas. Exemplos:

- `contas-correntes.md`
- `cartoes.md`
- `movimentacoes.md`
- `investimentos.md`
