---
tipo: adr
area: arquitetura-v2
status: implementado
versao: 1.0
atualizado: 2026-08-30
relacionados:
  - "[[../specs/desconcentracao-arquitetura-v2]]"
  - "[[../arquitetura]]"
  - "[[0001-stack-local-sem-framework]]"
  - "[[0002-modularizacao-frontend]]"
tags: [adr, "area/arquitetura-v2", "status/implementado"]
aliases: ["ADR-0014 Fachadas finas e roteamento declarativo"]
---

# ADR-0014 — Fachadas finas e roteamento declarativo

> [!info] Status
> **implementado** · área: `arquitetura-v2` · atualizado em 2026-08-30 · relacionados: [[../specs/desconcentracao-arquitetura-v2]], [[../arquitetura]]

## Contexto

`portfolio.py`, `app.py` e `web/app.js` cresceram como pontos de concentração. Uma substituição integral aumentaria o risco de quebrar integrações internas, testes e bancos existentes justamente na fundação da v2.

## Decisão

Adotar extração incremental com fachadas compatíveis. `portfolio.py` conserva nomes públicos e orquestra módulos internos de posições, cálculos e cotações. A tabela de rotas fica em `http_routes.py`, sem framework web, enquanto `AppHandler` conserva transporte, autenticação, validação de origem e adaptação HTTP. Payloads de domínio saem de `app.py` para módulos de `financeiro/`.

## Consequências

- Consumidores atuais não precisam migrar em bloco.
- Fronteiras menores podem ganhar testes próprios e evoluir independentemente.
- Wrappers só são aceitos na fachada pública quando protegem compatibilidade; wrappers de view sem função contratual devem ser removidos progressivamente.
- Dependências circulares são evitadas mantendo os módulos internos independentes da fachada.

## Alternativas consideradas

- Reescrever o Portfólio de uma vez: rejeitada pelo risco de regressão.
- Introduzir framework/roteador externo: rejeitada por contrariar o ADR-0001.
- Mover apenas funções entre arquivos JS: rejeitada para regras financeiras, pois não corrige a fronteira de autoridade.

## Changelog

- `1.0` — 2026-08-30 — Decisão adotada para a desconcentração inicial da v2.

## Relacionados

- [[../specs/desconcentracao-arquitetura-v2]]
- [[../arquitetura]]
- [[0001-stack-local-sem-framework]]
- [[0002-modularizacao-frontend]]
