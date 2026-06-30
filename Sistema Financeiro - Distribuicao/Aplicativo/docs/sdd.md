---
tipo: metodologia
area: meta
status: implementado
versao: 2.0
atualizado: 2026-06-29
relacionados:
  - "[[templates/spec-template|Template de spec]]"
  - "[[arquitetura]]"
  - "[[requisitos]]"
  - "[[glossario]]"
tags: [metodologia, meta]
aliases: ["SDD", "Spec Driven Development"]
---

# SDD: Spec Driven Development

> [!info] Status
> **implementado** · área: `meta` · atualizado em 2026-06-29 · relacionados: [[templates/spec-template|Template de spec]], [[arquitetura]], [[requisitos]]

SDD significa conduzir o desenvolvimento por especificações. Antes de alterar o app, descrevemos o comportamento esperado em linguagem clara e só então implementamos. Esta documentação é o principal insumo para agentes de IA em IDEs e para qualquer mantenedor humano — por isso precisa ser precisa, navegável e sempre atualizada.

Este vault foi organizado para ser aberto diretamente no **Obsidian** (cada `[[link-entre-colchetes]]` é um link clicável entre notas) e, ao mesmo tempo, continuar legível como markdown puro por IDEs, GitHub e agentes de IA.

## Estrutura do vault

```text
docs/
  README.md                 Ponto de entrada (Map of Content)
  sdd.md                    Este documento (metodologia)
  requisitos.md             Escopo funcional consolidado
  arquitetura.md            Camadas, rotas, tabelas e fluxos
  visao-produto.md          Direção de produto e módulos
  roadmap.md                Sequência de evolução
  glossario.md              Vocabulário de domínio com links
  templates/
    spec-template.md        Modelo obrigatório para novas specs
  specs/                     Uma spec por módulo funcional
  adr/                       Decisões técnicas/arquiteturais (Architecture Decision Records)
  design/
    design-system.md        Tokens visuais e regras de UI
```

## Frontmatter padrão

Toda nota deste vault carrega um frontmatter YAML com as mesmas chaves, para permitir navegação, busca e (se desejado) consultas via plugins do Obsidian:

| Campo | Valores | Uso |
|---|---|---|
| `tipo` | `spec`, `adr`, `design`, `metodologia`, `produto`, `arquitetura`, `roadmap`, `glossario`, `template` | Classifica a nota. |
| `area` | slug curto, ex.: `cartoes`, `investimentos`, `meta` | Agrupa notas do mesmo domínio. |
| `status` | `rascunho`, `em-implementacao`, `implementado`, `em-revisao`, `depreciado` | Estado real da funcionalidade. |
| `versao` | número semântico simples (`1.0`, `1.1`) | Incrementado a cada mudança relevante de comportamento. |
| `atualizado` | `AAAA-MM-DD` | Data da última revisão de conteúdo. |
| `relacionados` | lista de wikilinks | Alimenta a navegação cruzada e os backlinks do Obsidian. |
| `tags` | lista, incluindo sempre `tipo` e `area/<slug>` | Permite filtrar pelo painel de tags do Obsidian. |
| `aliases` | *(opcional)* nome legível para o link curto | Permite digitar `[[Cartões de Crédito]]` em vez do nome do arquivo. |

Cada spec também exibe um callout `> [!info] Status` logo abaixo do título, repetindo o essencial do frontmatter para quem está lendo o arquivo fora do Obsidian (IDE, GitHub, terminal de um agente de IA).

## Fluxo

1. Criar ou atualizar uma especificação em `specs/` usando [[templates/spec-template|o template]].
2. Validar jornada do usuário, dados, regras e critérios de aceite.
3. Atualizar [[requisitos]] se o escopo geral mudar.
4. Atualizar [[arquitetura]] se houver novo fluxo, rota, tabela ou decisão técnica relevante.
5. Se a mudança envolver uma decisão técnica não trivial (escolha de biblioteca, padrão de dados, trade-off de performance/segurança), registrar um ADR em `adr/`.
6. Implementar a menor mudança que cumpre a especificação.
7. Verificar manualmente ou com testes.
8. Atualizar o `status`, a `versao`, o `atualizado` e o `Changelog` da spec afetada.

## Ciclo de vida de uma spec (`status`)

```text
rascunho ──▶ em-implementacao ──▶ implementado ──▶ em-revisao ──▶ implementado
                                        │
                                        └──▶ depreciado
```

- **rascunho**: problema e jornada descritos, ainda sem compromisso de implementação.
- **em-implementacao**: implementação em andamento; comportamento pode não bater 100% com a spec ainda.
- **implementado**: comportamento descrito reflete o app em produção local.
- **em-revisao**: comportamento mudou ou está sendo questionado; a spec precisa ser revalidada.
- **depreciado**: funcionalidade removida ou substituída; a nota é mantida por histórico, sem implementação ativa.

## Especificações (`spec`) vs. decisões técnicas (`adr`) vs. design (`design`)

- **`specs/`** descreve **comportamento observável pelo usuário**: jornada, dados, regras de negócio, API e critérios de aceite. Não deve depender de detalhes de implementação internos.
- **`adr/`** registra **por que** uma decisão técnica foi tomada (ex.: não usar framework web, modularizar o frontend em ES Modules) e quais alternativas foram descartadas. Specs podem linkar um ADR para justificar uma restrição técnica.
- **`design/`** guarda os tokens visuais (cores, tipografia, espaçamento, formas) que toda a interface deve respeitar — é referência de UI, não de regra de negócio.

## Critérios para uma boa spec

- Deve ser pequena o bastante para caber em uma entrega.
- Deve evitar detalhes de implementação prematuros (isso é papel do código e, quando necessário, de um ADR).
- Deve deixar claro o que é sucesso (critérios de aceite verificáveis, no formato *dado/quando/então*).
- Deve indicar impactos em dados, tela e API.
- Deve linkar as specs relacionadas (`relacionados` no frontmatter + seção final) para manter o grafo de dependências do domínio navegável no Obsidian.
- Deve ser atualizada — `status`, `versao`, `atualizado` e `Changelog` — quando a implementação real mudar o comportamento previsto.

## Changelog

- `2.0` — 2026-06-29 — Reestruturação completa do vault: frontmatter padronizado, status por spec, ADRs separados de specs, glossário e template formal adicionados.
- `1.0` — versão original do fluxo SDD, sem metadados estruturados.

## Relacionados

- [[templates/spec-template|Template de spec]]
- [[arquitetura]]
- [[requisitos]]
- [[glossario]]
