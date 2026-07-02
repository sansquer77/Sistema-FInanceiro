---
tipo: template
area: meta
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[sdd]]"
  - "[[glossario]]"
tags: [template, meta]
---

# Template de Spec

> [!info] Como usar
> Duplique este arquivo dentro de `specs/` com o nome `area-da-funcionalidade.md`, preencha o frontmatter e todas as seções. Apague apenas seções marcadas como opcionais quando não houver conteúdo. Veja o processo completo em [[sdd]].

## Frontmatter obrigatório

```yaml
---
tipo: spec                 # spec | adr | design | metodologia | produto | arquitetura | roadmap | glossario | template
area: slug-da-area          # ex.: cartoes, lancamentos, investimentos
status: rascunho            # rascunho | em-implementacao | implementado | em-revisao | depreciado
versao: 0.1
atualizado: AAAA-MM-DD
relacionados:
  - "[[outra-spec]]"
tags: [spec, "area/slug-da-area", "status/rascunho"]
aliases: ["Nome bonito da spec"]
---
```

## [Nome da funcionalidade]

> [!info] Status
> **{{status}}** · área: `{{area}}` · atualizado em {{data}} · relacionados: {{links}}

### Problema

Qual dor ou necessidade esta spec resolve? Escreva do ponto de vista do usuário, não da implementação.

### Usuário

Quem usa esta funcionalidade e em qual contexto? Uma ou duas frases bastam.

### Jornada

1. Passo inicial.
2. Ação principal.
3. Resultado esperado observável pelo usuário.

### Dados

- `campo`: descrição, tipo e regra de obrigatoriedade.

### Regras

- Regra de negócio verificável (uma frase, uma regra).

### API e dados

- Rotas afetadas ou criadas (`MÉTODO /api/caminho`).
- Tabelas afetadas ou criadas.

### Critérios de aceite

- Dado um estado inicial, quando uma ação ocorre, então o resultado deve ser observável.

### Fora de escopo *(opcional)*

O que conscientemente não será feito nesta entrega.

### Changelog

- `{{versao}}` — {{data}} — descrição da mudança.

### Relacionados

- [[outra-spec]]
