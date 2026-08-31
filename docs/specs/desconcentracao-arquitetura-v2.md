---
tipo: spec
area: arquitetura-v2
status: implementado
versao: 1.2
atualizado: 2026-08-30
relacionados:
  - "[[../arquitetura]]"
  - "[[../adr/0014-desconcentracao-fachadas-e-roteamento]]"
  - "[[investimentos-portfolio]]"
  - "[[frontend-modularizacao]]"
  - "[[../qualidade-codigo]]"
tags: [spec, "area/arquitetura-v2", "status/implementado"]
aliases: ["Desconcentração arquitetural da v2"]
---

# Desconcentração arquitetural da v2

> [!info] Status
> **implementado** · área: `arquitetura-v2` · atualizado em 2026-08-30 · relacionados: [[../arquitetura]], [[../adr/0014-desconcentracao-fachadas-e-roteamento]], [[investimentos-portfolio]], [[frontend-modularizacao]], [[../qualidade-codigo]]

## Problema

O crescimento do produto concentrou roteamento, integrações, cálculos e persistência em poucos arquivos. Isso aumenta o risco de regressão e dificulta evoluir Portfólio, Open Finance e o futuro módulo familiar de forma independente.

## Usuário

Usuários da v2 que precisam manter os fluxos e dados atuais estáveis enquanto a base técnica ganha fronteiras menores e testáveis.

## Jornada

1. O usuário abre e utiliza os fluxos atuais sem mudança de contrato.
2. O servidor resolve a rota fora do `AppHandler` e entrega o processamento ao handler existente.
3. O Portfólio coordena posições, cotações e cálculos por módulos internos especializados.

## Dados

- Nenhuma tabela ou coluna nova.
- Valores monetários continuam em centavos inteiros no núcleo e datas em ISO.

## Regras

- `financeiro/portfolio.py` permanece a fachada pública compatível do Portfólio.
- Persistência/posições, cálculos e integrações de cotação possuem módulos internos próprios.
- `app.py` mantém transporte HTTP e delega resolução de rotas e payloads de domínio.
- `web/app.js` mantém bootstrap, estado e injeção; não deve receber novas regras financeiras.
- Refatorações preservam rotas, formatos de resposta e pontos públicos usados por outros módulos.
- As fronteiras e sinais de alerta desta refatoração seguem [[../qualidade-codigo]].

## API e dados

- Rotas existentes preservadas e novo endpoint de leitura `GET /api/balance-projection` para retirar projeções financeiras do frontend.
- Novos módulos: `financeiro/http_routes.py`, `financeiro/cockpit.py`, `financeiro/portfolio_positions.py`, `financeiro/portfolio_quotes.py` e `financeiro/portfolio_calculations.py`.

## Critérios de aceite

1. Dado qualquer endpoint existente, quando sua rota é resolvida, então o mesmo handler é executado.
2. Dada uma rota de mutação, quando a origem é inválida, então a validação ocorre antes do dispatch.
3. Dado um consumidor de `financeiro.portfolio`, quando importa a API pública atual, então o import continua válido.
4. Dadas posições do Portfólio, quando são agrupadas, então totais, moedas e percentuais permanecem equivalentes.
5. Dado ativo externo, quando precisa de símbolo ou cache, então a responsabilidade auxiliar pertence ao módulo de cotações.
6. Dado o Cockpit, quando agrega lançamentos, então o cálculo não reside no servidor HTTP.
7. Dado o frontend, quando inicializa as views, então `app.js` atua como composição e não recebe novas regras financeiras.

## Fora de escopo

- Alterar contratos públicos, schema SQLite ou comportamento financeiro.
- Dividir todos os módulos candidatos na mesma entrega.

## Candidatos auditados para as próximas extrações

- `consultor.py`: separar montagem de contexto, execução do provedor e persistência do histórico.
- `database.py`: separar conexão/manutenção, baseline do schema e catálogo de migrações.
- `imports.py`: separar parsers de formato, normalização e orquestração transacional.
- `transactions.py` e `credit_cards.py`: avaliar se partes internas do serviço de projeções devem ser aproximadas desses domínios sem duplicar cálculos.
- `web/app.js`: wrappers de views e o bloco legado de projeção financeira foram removidos; o arquivo permanece como composição do contrato backend.

## Plano de implementação

- [x] Passo 1 — extrair tabela e resolução de rotas. Fecha: critérios 1 e 2.
- [x] Passo 2 — extrair agregação do Cockpit de `app.py`. Fecha: critério 6.
- [x] Passo 3 — criar fronteiras internas do Portfólio preservando fachada. Fecha: critérios 3 a 5.
- [x] Passo 4 — retirar projeções financeiras de `app.js` e modularizar internamente `portfolio-view.js`. Fecha: critério 7.
- [x] Passo 5 — executar testes de contratos, domínio e suíte completa. Fecha: critérios 1 a 7.

## Changelog

- `1.2` — 2026-08-30 — Vinculada à spec implementada [[../qualidade-codigo]], que formaliza as fronteiras preservadas por esta desconcentração.
- `1.1` — 2026-08-30 — Projeções de saldo/fatura movidas ao núcleo e Portfólio frontend dividido em gráfico, agrupamento, formulário e coordenador.
- `1.0` — 2026-08-30 — Refatoração arquitetural inicial da fundação v2 implementada e verificada.

## Relacionados

- [[../arquitetura]]
- [[../adr/0014-desconcentracao-fachadas-e-roteamento]]
- [[investimentos-portfolio]]
- [[frontend-modularizacao]]
