---
tipo: template
area: meta
status: implementado
versao: 1.3
atualizado: 2026-07-24
relacionados:
  - "[[sdd]]"
  - "[[glossario]]"
tags: [template, meta]
---

# Template de Spec

> [!info] Como usar
> Duplique este arquivo para criar qualquer novo documento do vault. Para specs, salve dentro de `specs/` com o nome `area-da-funcionalidade.md` e preencha todas as seções obrigatórias. Para outros tipos (`adr`, `design`, `produto`, `arquitetura`, `roadmap`, `glossario`, `metodologia`), adapte o frontmatter, o título e as seções mantendo status, changelog e relacionados. Veja o processo completo em [[sdd]].

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

> Um critério por regra — nunca componha duas condições numa frase só (se a frase tem "e", provavelmente são dois critérios). Cada critério deve ser verificável: por teste automatizado sempre que possível, ou por um passo manual explícito quando não for (ex.: aparência visual). Cubra pelo menos um caso de sucesso, um caso de borda e, se a funcionalidade tiver alguma restrição de acesso, um caso de permissão/segurança.

- Dado [estado inicial], quando [ação do usuário ou evento do sistema], então [resultado único e observável].
- Dado [estado inicial alternativo ou de borda], quando [mesma ação ou variação dela], então [resultado diferente ou erro esperado].
- Dado [pré-condição de permissão/segurança, se houver], quando [ação], então [comportamento de proteção esperado].

### Pendências *(obrigatória enquanto `status` for `rascunho` ou `em-implementacao`)*

> [!question] Pendências
> Toda pergunta em aberto, decisão não tomada ou premissa não validada entra aqui. Nenhum agente de IA deve implementar uma seção que dependa de um item desta lista sem confirmação humana antes. Remova o item somente quando a resposta já estiver refletida no restante da spec. Se não houver pendências, escreva "Nenhuma pendência conhecida."

- [ ] Pergunta ou decisão em aberto.

### Fora de escopo *(opcional)*

O que conscientemente não será feito nesta entrega.

### Plano de implementação *(obrigatória quando a spec tiver mais de 6 critérios de aceite ou tocar mais de um módulo de `financeiro/`)*

> Decomponha a entrega em passos atômicos e sequenciáveis. Cada passo referencia o(s) critério(s) de aceite que fecha, para um agente de IA (ou humano) saber quando pode marcar o passo como concluído e para a revisão poder checar cobertura: todo critério de aceite deve aparecer em pelo menos um passo. Não é um cronograma — é a ordem de implementação segura (ex.: schema antes de rota, rota antes de UI).

- [ ] Passo 1 — o que muda e onde (`arquivo`/`módulo`). Fecha: critério(s) N.
- [ ] Passo 2 — o que muda e onde (`arquivo`/`módulo`). Fecha: critério(s) N.
- [ ] Passo N — testes automatizados cobrindo os critérios acima.

Para specs pequenas (até 6 critérios, um único módulo), omita esta seção — o passo 6 do fluxo ("implementar a menor mudança que cumpre a especificação") é suficiente sem decomposição formal.

### Changelog

- `{{versao}}` — {{data}} — descrição da mudança.

### Relacionados

- [[outra-spec]]

## Changelog do template

- `1.3` — 2026-07-24 — Adicionada seção opcional "Plano de implementação" (obrigatória para specs com mais de 6 critérios de aceite ou que tocam mais de um módulo de `financeiro/`), decompondo a entrega em passos atômicos rastreáveis até os critérios de aceite que cada um fecha.
- `1.2` — 2026-07-24 — "Critérios de aceite" passa a exigir múltiplos critérios atômicos (sucesso, borda e permissão/segurança quando aplicável) em vez de um exemplo único; adicionada seção obrigatória "Pendências" (rascunho/em-implementacao) que bloqueia implementação de itens não confirmados por um agente de IA.
- `1.1` — 2026-07-04 — Uso ampliado: o template passa a ser a base de qualquer novo documento do vault, não apenas specs.
- `1.0` — 2026-06-29 — Template inicial para specs.
