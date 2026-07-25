---
tipo: metodologia
area: meta
status: implementado
versao: 2.6
atualizado: 2026-07-24
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
> **implementado** · área: `meta` · atualizado em 2026-07-24 · relacionados: [[templates/spec-template|Template de spec]], [[arquitetura]], [[requisitos]]

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
    spec-template.md        Modelo obrigatório para novos documentos
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

<!-- sync:fluxo-8-passos — espelhado (resumido) em AGENTS.md, seção "1. Fluxo obrigatório para qualquer mudança" -->
1. Criar ou atualizar uma especificação em `specs/` usando [[templates/spec-template|o template]].
2. Validar jornada do usuário, dados, regras e critérios de aceite.
3. Atualizar [[requisitos]] se o escopo geral mudar.
4. Atualizar [[arquitetura]] se houver novo fluxo, rota, tabela ou decisão técnica relevante.
5. Se a mudança envolver uma decisão técnica não trivial (escolha de biblioteca, padrão de dados, trade-off de performance/segurança), registrar um ADR em `adr/`.
6. Implementar a menor mudança que cumpre a especificação, citando a spec nas regras de negócio não triviais (ver [[#Rastreabilidade: código ↔ spec]]).
7. Verificar: todo critério de aceite automatizável deve ter um teste correspondente; critérios que só podem ser verificados manualmente (ex.: aparência visual) devem ser sinalizados como tal na própria spec.
8. Atualizar o `status`, a `versao`, o `atualizado` e o `Changelog` da spec afetada.
<!-- /sync:fluxo-8-passos -->

## Modelo de maturidade: spec-anchored

<!-- sync:modelo-spec-anchored — espelhado (resumido) em AGENTS.md, parágrafo logo após o fluxo -->
Este projeto é **spec-anchored**, não *spec-as-source*: a spec ancora a intenção, o contrato observável e os critérios de aceite de uma funcionalidade, mas **o código e os testes são a fonte de verdade executável**. Nenhuma spec é gerada nem executada automaticamente a partir do código, nem o inverso — a ligação entre os dois é sempre mediada por revisão humana ou de agente.

Na prática, isso significa:

- Se o comportamento real do app divergir da spec, a causa é investigada antes de presumir qual dos dois está errado — a spec não é automaticamente tratada como correta só por existir.
- Uma vez confirmado qual é o comportamento correto, a spec é atualizada (passo 8 acima) para voltar a refletir a realidade; ela nunca deve ficar "quase certa" por muito tempo.
- Um agente de IA não deve usar uma spec desatualizada como justificativa para reintroduzir um comportamento antigo, nem presumir que uma divergência é sempre um bug no código — o comportamento em produção local, coberto por teste, tem precedência sobre uma spec ainda não revalidada.
<!-- /sync:modelo-spec-anchored -->

## Rastreabilidade: código ↔ spec

<!-- sync:rastreabilidade-codigo-spec — espelhado (resumido) em AGENTS.md, seção "Rastreabilidade: código ↔ spec" -->
`arquitetura.md` mapeia módulo → spec, mas esse mapeamento é grosso demais para achar *qual regra específica* motivou um trecho de código. Para regra de negócio **não óbvia** — qualquer cálculo, validação ou efeito colateral que não seria previsível só lendo o nome da função — o código cita a spec de origem em comentário, logo acima do trecho relevante:

```python
# spec: investimentos-portfolio v1.3 — critério 4
# (venda parcial não pode deixar quantidade residual negativa)
if quantidade_venda > posicao.quantidade:
    raise ValueError("quantidade insuficiente")
```

```javascript
// spec: cartoes v2.0 — critério 7
// (estorno de parcela futura não conciliada reverte o saldo da fatura aberta)
```

Formato: `spec: <area>/<slug-do-arquivo em specs/> vX.Y — critério N` (o número do critério é a posição dele na lista de "Critérios de aceite" da spec). Regras óbvias — um `if` simples de validação de campo obrigatório, por exemplo — não precisam da citação; o objetivo é ancorar as decisões que um agente de IA (ou um humano seis meses depois) não deduziria só olhando o código.

O `vX.Y` da citação é um ponteiro, não uma trava: quando uma spec ganha `versao` nova, quem faz o PR busca por `spec: <area>/<slug>` no código e atualiza o número nos comentários que a citam. Na maioria dos casos o `critério N` continua válido — critérios novos costumam ser anexados ao final da lista, não inseridos no meio — mas o número de versão referenciado, se deixado desatualizado, é um sinal falso de que a citação foi revisada quando não foi.

Isso não substitui a spec nem o ADR — é uma migalha de pão na direção contrária, para quem está no código e precisa achar rápido o "porquê" documentado.
<!-- /sync:rastreabilidade-codigo-spec -->

## Regra obrigatória para novos arquivos

- Todo novo arquivo de documentação criado neste vault deve começar como duplicata de [[templates/spec-template|`docs/templates/spec-template.md`]].
- Para specs em `docs/specs/`, o template deve ser preenchido sem remover seções obrigatórias antes da implementação.
- Para documentos que não sejam specs (`adr/`, `design/`, `roadmap`, `arquitetura`, `produto`, `glossario` ou `metodologia`), use o template como base estrutural e adapte `tipo`, `area`, título e seções, preservando frontmatter, callout de status, `Changelog` e `Relacionados`.
- Nenhum arquivo novo deve começar como markdown livre.

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

<!-- sync:spec-vs-adr-vs-design — espelhado em AGENTS.md, seção "O que é spec vs. ADR vs. design" -->
- **`specs/`** descreve **comportamento observável pelo usuário**: jornada, dados, regras de negócio, API e critérios de aceite. Não deve depender de detalhes de implementação internos.
- **`adr/`** registra **por que** uma decisão técnica foi tomada (ex.: não usar framework web, modularizar o frontend em ES Modules) e quais alternativas foram descartadas. Specs podem linkar um ADR para justificar uma restrição técnica.
- **`design/`** guarda os tokens visuais (cores, tipografia, espaçamento, formas) que toda a interface deve respeitar — é referência de UI, não de regra de negócio.
<!-- /sync:spec-vs-adr-vs-design -->

## Critérios para uma boa spec

- Deve ser pequena o bastante para caber em uma entrega.
- Deve evitar detalhes de implementação prematuros (isso é papel do código e, quando necessário, de um ADR).
- Deve deixar claro o que é sucesso (critérios de aceite verificáveis, no formato *dado/quando/então*).
- Deve indicar impactos em dados, tela e API.
- Deve linkar as specs relacionadas (`relacionados` no frontmatter + seção final) para manter o grafo de dependências do domínio navegável no Obsidian.
- Deve ser atualizada — `status`, `versao`, `atualizado` e `Changelog` — quando a implementação real mudar o comportamento previsto.

## Changelog

- `2.6` — 2026-07-24 — Adicionados marcadores `<!-- sync:NOME -->` ao redor dos quatro blocos duplicados com AGENTS.md (fluxo de 8 passos, modelo spec-anchored, spec-vs-adr-vs-design, rastreabilidade código↔spec), para tornar o par grep-ável e reduzir risco de drift entre os dois arquivos.
- `2.5` — 2026-07-24 — "Rastreabilidade: código ↔ spec" ganhou regra explícita: quando a spec citada muda de `versao`, o `vX.Y` do comentário no código deve ser atualizado no mesmo PR (checklist do AGENTS.md espelha essa regra).
- `2.4` — 2026-07-24 — Adicionada a seção "Rastreabilidade: código ↔ spec", com convenção de comentário (`spec: area/slug vX.Y — critério N`) para regras de negócio não óbvias; passo 6 do fluxo passa a referenciá-la.
- `2.3` — 2026-07-24 — Adicionado o modelo de maturidade "spec-anchored" (código e testes como fonte de verdade executável; spec ancora intenção e critérios de aceite). Passo de verificação do fluxo detalhado para exigir teste correspondente a cada critério de aceite automatizável.
- `2.2` — 2026-07-04 — Regra de novos arquivos ampliada: qualquer novo documento do vault deve começar a partir de `docs/templates/spec-template.md`, adaptando o tipo quando não for spec.
- `2.1` — 2026-06-30 — Regra explícita adicionada: toda nova spec deve nascer de `docs/templates/spec-template.md`; documentos não-spec novos devem manter o frontmatter padrão e linkar a spec correspondente.
- `2.0` — 2026-06-29 — Reestruturação completa do vault: frontmatter padronizado, status por spec, ADRs separados de specs, glossário e template formal adicionados.
- `1.0` — versão original do fluxo SDD, sem metadados estruturados.

## Relacionados

- [[templates/spec-template|Template de spec]]
- [[arquitetura]]
- [[requisitos]]
- [[glossario]]
