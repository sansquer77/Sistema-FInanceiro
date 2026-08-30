---
tipo: adr
area: frontend-v2
status: implementado
versao: 1.0
atualizado: 2026-08-30
relacionados:
  - "[[0002-modularizacao-frontend]]"
  - "[[0008-licenca-apache-2-0]]"
  - "[[../specs/frontend-fundacao-v2]]"
  - "[[../distribuição]]"
  - "[[../design/design-system]]"
tags: [adr, "area/frontend-v2", "status/implementado"]
aliases: ["Dependências do frontend v2", "ApexCharts, IMask e Command Palette"]
---

# ADR-0013 — Dependências e primitives do frontend v2

> [!info] Status
> **implementado** · área: `frontend-v2` · atualizado em 2026-08-30 · relacionados: [[0002-modularizacao-frontend]], [[0008-licenca-apache-2-0]], [[../specs/frontend-fundacao-v2]], [[../distribuição]], [[../design/design-system]]

## Contexto

A fundação da v2 pretende elevar a qualidade dos gráficos, padronizar a digitação de dinheiro e datas, oferecer uma Command Palette por `Cmd+K`/`Ctrl+K` e manter listas extensas responsivas por virtualização. O frontend atual usa HTML, CSS e ES Modules nativos, sem build step, funciona offline e é distribuído sob Apache-2.0.

As escolhas precisam respeitar essas restrições. ApexCharts oferece API para JavaScript sem framework, mas as versões atuais deixaram de usar licença MIT e adotaram condições relacionadas a receita e redistribuição. IMask é uma biblioteca vanilla sem dependências. O pacote `cmdk` é um componente React e requer React, JSX já compilado e dependências transitivas; sua adoção literal criaria uma exceção estrutural desproporcional para um único componente.

## Decisão

### ApexCharts

- Adotar **ApexCharts 4.7.0**, última linha validada nesta decisão sob licença MIT.
- O arquivo minificado e o texto da licença serão vendorizados no repositório e incluídos nos pacotes offline.
- O runtime nunca carregará ApexCharts por CDN.
- Atualização para a linha 5 ou posterior fica bloqueada até revisão explícita de licença e novo ADR.
- Somente recursos presentes na versão fixada e compatíveis com o design system podem ser utilizados.
- A integração ficará atrás de um adaptador local, evitando que views construam configurações divergentes ou dependam diretamente de detalhes da biblioteca.

### IMask

- Adotar **IMask** em versão exata fixada no momento da implementação, sob licença MIT validada e registrada no inventário de terceiros.
- O artefato browser será vendorizado localmente, sem CDN e sem instalar runtime Node no app.
- Um adaptador único será responsável por máscaras monetárias e de data, ciclo de vida e extração do valor não mascarado.
- Máscara é assistência de entrada, nunca regra de negócio: o backend continua validando valores e datas.

### Command Palette

- Incorporar o **contrato de experiência associado ao cmdk** — busca incremental, agrupamento, seleção por teclado, estado vazio e abertura por `Cmd+K`/`Ctrl+K` — mas **não incorporar o pacote React `cmdk`**.
- Implementar a palette como ES Module nativo, reutilizando diálogo, confinamento de foco, normalização de busca e navegação já existentes.
- O comando `/` permanece reservado à busca global atual; `Cmd+K`/`Ctrl+K` abre a nova palette.
- Adotar literalmente `cmdk` exigiria React e um bundle especial, contrariando [[0002-modularizacao-frontend]]; essa alternativa só pode ser reaberta por novo ADR que justifique a mudança de stack.

### Virtualização

- Implementar virtualização de listas longas internamente, sem dependência externa.
- Cada lista virtualizada deve calcular a janela visível a partir de `scrollTop`, altura da viewport, altura medida/estável da linha e overscan.
- O DOM conterá apenas a janela visível e linhas de segurança; espaçadores superior e inferior preservarão a altura e a posição aparente do conjunto completo.
- A virtualização pertence a um utilitário compartilhado e não pode alterar ordenação, filtros, paginação, seleção, foco ou semântica financeira.

## Empacotamento e cadeia de fornecimento

- Dependências browser ficam em `web/vendor/<biblioteca>/<versao>/` ou estrutura equivalente explícita.
- Cada dependência deve incluir versão, URL de origem, hash SHA-256 e licença no inventário de terceiros.
- A atualização de um artefato vendorizado exige revisão de licença, notas de versão e testes de regressão.
- O app não faz download dessas dependências em runtime e continua plenamente funcional offline.
- Código vendorizado não é editado manualmente; customizações ficam nos adaptadores locais.

## Consequências positivas

- Gráficos ganham interatividade e consistência sem framework ou build step.
- Máscaras deixam de ser implementadas repetidamente em formulários.
- A Command Palette melhora navegação por teclado sem introduzir React.
- Listas grandes reduzem custo de DOM e renderização.
- Versões, hashes e licenças ficam auditáveis nos pacotes.

## Consequências negativas e limites

- ApexCharts fica congelado em uma versão MIT anterior; correções posteriores exigem avaliação jurídica e técnica.
- Artefatos vendorizados aumentam o tamanho do pacote.
- A aplicação assume responsabilidade pelo ciclo de vida das instâncias de gráficos e máscaras.
- A palette nativa não reutiliza código do pacote `cmdk`; reutiliza apenas o padrão de interação.
- Virtualização com altura variável não faz parte do primeiro contrato e exigiria medição/cache mais complexos.

## Alternativas consideradas

| Alternativa | Decisão |
|---|---|
| ApexCharts atual via CDN | Rejeitada: quebra operação offline, reprodutibilidade e controle de licença. |
| ApexCharts atual vendorizado | Rejeitada nesta fundação: licença atual não é compatível de forma geral com a promessa Apache-2.0 e redistribuição irrestrita do app. |
| Manter todos os gráficos SVG próprios | Rejeitada como direção geral: perpetua implementações duplicadas e limita acessibilidade/interação; pode permanecer apenas onde o gráfico especializado não se adapte ao ApexCharts. |
| Instalar React e `cmdk` somente para a palette | Rejeitada: custo de runtime, build e manutenção desproporcional. |
| Biblioteca externa de virtualização | Rejeitada inicialmente: o contrato de linha fixa e janela visível é pequeno e pode ser implementado de forma nativa. |

## Changelog

- `1.0` — 2026-08-30 — Definidos ApexCharts 4.7.0 MIT e IMask vendorizados, Command Palette nativa com contrato cmdk e virtualização compartilhada sem dependência.

## Relacionados

- [[0002-modularizacao-frontend]]
- [[0008-licenca-apache-2-0]]
- [[../specs/frontend-fundacao-v2]]
- [[../distribuição]]
- [[../design/design-system]]
