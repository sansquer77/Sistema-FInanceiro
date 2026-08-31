---
tipo: arquitetura
area: meta
status: implementado
versao: 1.12
atualizado: 2026-08-31
relacionados:
  - "[[arquitetura]]"
  - "[[sdd]]"
  - "[[adr/0001-stack-local-sem-framework]]"
  - "[[adr/0002-modularizacao-frontend]]"
  - "[[adr/0003-sqlite-fonte-de-verdade]]"
tags: [arquitetura, meta, "status/implementado"]
aliases: ["Qualidade de Código", "Padrões de Qualidade", "Convenções de Código", "Limites de Módulo"]
---

# Qualidade de Código

> [!info] Status
> **implementado** · área: `meta` · versão: `1.10` · atualizado em 2026-08-31 · relacionados: [[arquitetura]], [[sdd]], [[adr/0001-stack-local-sem-framework]], [[adr/0002-modularizacao-frontend]], [[adr/0003-sqlite-fonte-de-verdade]]

## Objetivo

Registrar, como regras verificáveis, os padrões de organização de código que já foram decididos (nas ADRs) ou observados na prática durante as limpezas de [[arquitetura]] — para que a divisão de responsabilidades entre `web/`, `app.py` e `financeiro/` não regrida com o tempo. Este documento não introduz uma decisão nova: ele formaliza o que motivou a divisão de `portfolio.py`, `portfolio-view.js` e a extração de roteamento/lógica residual de `app.py`/`app.js`, para que mudanças futuras tenham critérios explícitos em vez de reconstruir o raciocínio lendo o histórico de commits.

## Escopo

Cobre a organização interna de código em três camadas, conforme [[arquitetura]]:

- Backend de domínio (`financeiro/`)
- Servidor HTTP (`app.py`)
- Interface web (`web/`, `web/modules/`)

Não cobre estilo de formatação (indentação, aspas, ordenação de imports) nem convenções de nomenclatura — isso fica para uma futura configuração de linter, se adotada. O foco aqui é fronteira de responsabilidade e tamanho como sinal de alerta.

## Regras por camada

### `financeiro/`

- Todo cálculo financeiro (rentabilidade, conversão de câmbio, agregação de transações, taxa de poupança, ranking de categorias, o que for) vive aqui — nunca em `app.py` nem em `web/*.js`. Se um handler ou uma view precisa "só somar uns valores", isso ainda é regra de negócio e pertence a um módulo de `financeiro/`.
- Cada módulo de domínio (`portfolio.py`, `transactions.py`, `financial_health.py`, etc.) pode combinar regra de negócio, cálculo e acesso a dados do próprio domínio — essa combinação é intencional (ver [[adr/0003-sqlite-fonte-de-verdade]]) e não deve ser desfeita criando uma camada de persistência horizontal separada só por separar.
- Quando um módulo de domínio mistura sub-responsabilidades claramente distintas (ex.: integração HTTP externa + cache, cálculo, e CRUD/SQL de posições), ele deve ser dividido por sub-responsabilidade dentro do mesmo domínio (ex.: `portfolio_quotes.py`, `portfolio_calculations.py`, `portfolio_positions.py`), não por tipo técnico genérico.
- Dinheiro é representado e manipulado em centavos (inteiros) dentro de `financeiro/`; conversão para valor decimal é responsabilidade de borda (resposta da API), não do meio do cálculo.

### `app.py`

- Todo `handle_*` é um adaptador fino: parse da requisição → chamada a uma função de `financeiro/` → formatação da resposta. Nenhuma lógica de negócio (cálculo, agregação, regra condicional sobre dado financeiro) deve viver dentro de um `handle_*` nem em função de nível de módulo em `app.py`.
- O roteamento (`do_GET`/`do_POST`/etc.) usa uma tabela declarativa (mapeamento caminho → handler), não uma cadeia longa de `if`/`elif`. A tabela pode viver no próprio `app.py` — não é necessário nenhum framework ou sistema de decorators para isso (ver [[adr/0001-stack-local-sem-framework]]).
- Helpers de infraestrutura HTTP (autenticação de sessão, validação de origem, serialização JSON, tratamento de erro) podem continuar em `app.py`; helpers que calculam ou agregam dado financeiro, não — esses migram para `financeiro/`.

### `web/` e `web/modules/`

- Cada módulo de view (`register*View`) tem uma responsabilidade coesa. Quando uma view cresce a ponto de misturar formulário/edição, renderização, cálculo de gráfico (ex.: suavização de curva SVG) e agregação/agrupamento de dados para exibição, ela deve ser dividida em módulos menores por essas sub-responsabilidades, seguindo o mesmo padrão já usado para os utilitários extraídos (`api.js`, `date-utils.js`, `money-utils.js`, etc. — ver [[adr/0002-modularizacao-frontend]]).
- `app.js` é a raiz de composição da SPA (`boot`, carregamento de estado, wiring dos módulos de view) — seu tamanho vem de largura (orquestrar muitos domínios), não de mistura de responsabilidades, e por isso não segue o mesmo critério de divisão que uma view individual. Ainda assim, nenhum cálculo financeiro (mesmo que pareça "só uma projeção local") deve ficar em `app.js`: se o dado já existe no backend, ele deve vir pronto da API; se não existe, o cálculo migra para `financeiro/` e passa a ser exposto por um endpoint.

## Sinais de alerta (heurística de tamanho)

Tamanho de arquivo não é uma regra rígida — é um sinal para revisar se há mistura de responsabilidades. Como referência do que já foi observado neste projeto:

- Módulo de domínio em `financeiro/` ou módulo de view em `web/modules/` acima de **~1.200 linhas**: revisar se há mais de uma sub-responsabilidade misturada antes de simplesmente aceitar o crescimento. (`cards-view.js`, com 1.209 linhas, é hoje o maior módulo de view "saudável" — usado aqui como referência, não como teto absoluto.)
- Qualquer função ou bloco de nível de módulo em `app.py` ou `app.js` que faça conta sobre valor monetário (soma, proporção, `Math.*`, `reduce` sobre `amount`/`valor`/`cents`) é um sinal de lógica de domínio fora de lugar, independentemente do tamanho do arquivo.
- Uma classe `AppHandler` (ou equivalente) crescendo por adição de novos `handle_*` é esperado; crescendo por adição de lógica dentro de um `handle_*` existente não é.

## Processo

- Ao abrir uma spec ou PR que toque um dos três diretórios do escopo, checar as regras acima antes de considerar a mudança pronta — não é necessário um documento à parte por PR, só a revisão consciente contra esta lista.
- Divergência entre este documento e o código real é tratada como o modelo *spec-anchored* de [[sdd]]: investiga-se a causa antes de presumir qual dos dois está errado, e o lado desatualizado é corrigido.

### Ativação dos limites e da validação automatizada

Os limites numéricos da seção "Sinais de alerta" são verificados pelo teste `tests/test_code_quality.py`. O teste permite explicitamente os módulos grandes já revisados e falha quando surge um novo módulo acima do limite ou quando um módulo revisado cresce além do tamanho registrado. As extrações necessárias estão documentadas em [[specs/desconcentracao-arquitetura-v2]] e [[specs/frontend-modularizacao]].

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida. As regras desta nota refletem o estado atual do código e devem ser reavaliadas quando novas extrações ou módulos forem implementados.

## Fora de escopo

- Estilo de formatação e lint de sintaxe (aspas, indentação, ordenação de imports).
- Convenções de nomenclatura de variáveis e funções.
- Cobertura de teste em si (tratada por [[sdd]], seção "Fluxo", passo 7).

## Changelog

- `1.12` — 2026-08-31 — Fachada do Consultor reduzida a 398 linhas após extração de configurações (275) e catálogo (336); gate impede SQL na fachada e dependência de persistência/transporte no catálogo.

- `1.11` — 2026-08-31 — `consultor.py` reduzido a 967 linhas após extração de contextos (458 linhas), removido da lista de módulos superdimensionados; gate protege a fronteira do novo módulo.

- `1.10` — 2026-08-31 — Linha-base de `consultor.py` reduzida para 1.387 linhas após extração do provedor; contrato impede retorno do transporte à fachada e dependência circular.

- `1.9` — 2026-08-31 — Linha-base revisada de `consultor.py` reduzida de 1.511 para 1.454 linhas após extração de histórico, quota e cooldown.
- `1.8` — 2026-08-31 — `transactions-view.js` reduzido abaixo do limiar de módulos superdimensionados por extrações de gráfico, lista, formulário e classificação compartilhada.
- `1.7` — 2026-08-31 — Reduzida a linha-base revisada de `transactions-view.js` para 1.528 linhas após remoção de resíduos SVG comprovadamente mortos.
- `1.6` — 2026-08-31 — Sincronizados frontmatter e callout de status; arquitetura passa a reconhecer explicitamente o gate automatizado já aplicado por `tests/test_code_quality.py`.
- `1.5` — 2026-08-30 — Atualizada referência de tamanho de `cards-view.js` para 1.209 linhas após adição do badge de bandeira; módulo mantido no conjunto revisado do teste de qualidade.
- `1.4` — 2026-08-30 — Atualizada referência de tamanho de `cards-view.js` para 1.205 linhas após adição do badge de logo compartilhado; módulo registrado no conjunto revisado do teste de qualidade.
- `1.3` — 2026-08-30 — Criado `tests/test_code_quality.py` para verificar fronteiras das raízes, detectar cálculo financeiro residual e controlar crescimento de módulos acima do limite revisado.
- `1.2` — 2026-08-30 — Spec incorporada ao vault e promovida para `implementado`, com pendências encerradas e referências às extrações arquiteturais concluídas.
- `1.1` — 2026-08-30 — Adicionada a seção de ativação dos limites numéricos e da validação automatizada após as limpezas arquiteturais.
- `1.0` — 2026-08-30 — Documento criado para formalizar as fronteiras de responsabilidade e os sinais de alerta de tamanho dos módulos.

## Relacionados

- [[arquitetura]]
- [[sdd]]
- [[adr/0001-stack-local-sem-framework]]
- [[adr/0002-modularizacao-frontend]]
- [[adr/0003-sqlite-fonte-de-verdade]]
- [[specs/desconcentracao-arquitetura-v2]]
- [[specs/frontend-modularizacao]]
