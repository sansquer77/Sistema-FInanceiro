---
tipo: spec
area: arquitetura-v2
status: implementado
versao: 2.3
atualizado: 2026-08-31
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
> **implementado** · área: `arquitetura-v2` · atualizado em 2026-08-31 · relacionados: [[../arquitetura]], [[../adr/0014-desconcentracao-fachadas-e-roteamento]], [[investimentos-portfolio]], [[frontend-modularizacao]], [[../qualidade-codigo]]

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

- `financeiro/consultor_history.py` e `financeiro/consultor_provider.py` encapsulam histórico e transporte externo, com compatibilidade pela fachada `consultor.py`.
- `financeiro/consultor_context.py` reúne builders e compactação; a fachada coordena validação, seleção e enriquecimento por perfis.
- `financeiro/consultor_settings.py` concentra configurações e perfil criptografado; `financeiro/consultor_catalog.py` concentra catálogo, validações e prompts. `consultor_errors.py` compartilha a exceção pública sem ciclos de importação.

## Critérios de aceite

1. Dado qualquer endpoint existente, quando sua rota é resolvida, então o mesmo handler é executado.
2. Dada uma rota de mutação, quando a origem é inválida, então a validação ocorre antes do dispatch.
3. Dado um consumidor de `financeiro.portfolio`, quando importa a API pública atual, então o import continua válido.
4. Dadas posições do Portfólio, quando são agrupadas, então totais, moedas e percentuais permanecem equivalentes.
5. Dado ativo externo, quando precisa de símbolo ou cache, então a responsabilidade auxiliar pertence ao módulo de cotações.
6. Dado o Cockpit, quando agrega lançamentos, então o cálculo não reside no servidor HTTP.
7. Dado o frontend, quando inicializa as views, então `app.js` atua como composição e não recebe novas regras financeiras.

8. Dado um consumidor do Consultor, quando chama a fachada ou injeta/moca seu provedor, então mensagens, payloads, timeout e erros públicos permanecem compatíveis, sem dependência circular nem SQL no adaptador.

9. Dada uma análise do Consultor, quando o contexto é montado após a extração, então payloads, limites de compactação, perfis por usuário e reutilização das posições permanecem equivalentes, sem expor identificadores adicionais.

10. Dado um usuário do Consultor, quando altera configurações ou perfil, então consentimento, criptografia, expurgo de histórico e isolamento por usuário continuam iguais.
11. Dado um consumidor do catálogo, quando lista análises ou monta prompts, então IDs, ordem, períodos, textos e exceção pública permanecem compatíveis.
12. Dadas as mesmas entradas e cotações, quando a tela e os consumidores internos consultam posições, então usam a mesma leitura e montagem, preservando ordem, fontes, resgates, encerramentos e ajustes manuais.
13. Dada uma consulta do Portfólio, quando ocorrem cotações ou câmbio, então a conexão do snapshot local já está fechada; resgates e encerramentos mantêm a revalidação antes da escrita.
14. Dado o histórico da carteira, quando a tela é consultada, então nomes de conta, ordem dos históricos, isolamento por usuário e formato público permanecem iguais.

15. Dado um consumidor das cotações, quando transporte/cache são delegados, então timeout, cabeçalhos, exceção pública, TTL, force-refresh e fallback de cache vencido permanecem compatíveis, sem importação da fachada pelo módulo interno.
16. Dado cache persistente indisponível ou inválido, quando há consulta de cotação, então leitura/escrita falham de forma tolerada como antes e nenhuma conexão fica aberta durante a chamada HTTP.
17. Dado cache em memória ou cambial, quando expira ou atinge o limite, então expurgo, LRU, locks e objetos públicos de cache continuam equivalentes.

18. Dadas posições idênticas, quando valorizadas após a separação, então valores líquidos/brutos, impostos, aniversários e variação diária permanecem equivalentes.
19. Dadas posições já carregadas, quando a rentabilidade histórica é solicitada, então não há nova leitura da carteira; séries por moeda, baseline, limite de 12 meses e aproximações permanecem iguais.
20. Dadas consultas simultâneas, quando os motores internos calculam valores, então caches de fatores continuam locais à chamada e não há importação reversa da fachada nem substituição temporária de dependências globais.

## Fora de escopo

- Alterar contratos públicos, schema SQLite ou comportamento financeiro.
- Dividir todos os módulos candidatos na mesma entrega.

## Candidatos auditados para as próximas extrações

- `consultor.py`: extrações de histórico, provedor, contexto, configurações e catálogo concluídas. A fachada mantém composição, execução e pós-processamento; não há nova divisão prevista nesta etapa.
- `database.py`: separar conexão/manutenção, baseline do schema e catálogo de migrações.
- `imports.py`: separar parsers de formato, normalização e orquestração transacional.
- `transactions.py` e `credit_cards.py`: avaliar se partes internas do serviço de projeções devem ser aproximadas desses domínios sem duplicar cálculos.
- `web/app.js`: wrappers de views e o bloco legado de projeção financeira foram removidos; o arquivo permanece como composição do contrato backend.

## Plano de implementação

- [x] Passo 19 — Separar valorização por data e série histórica, com dependências explícitas e fachada compatível. Fecha: critérios 18–20.
- [x] Passo 20 — Verificar contratos, fatores compartilhados, impostos, aniversários e fronteiras transacionais com testes isolados e suíte completa. Fecha: critérios 18–20. Suíte completa: 453 testes aprovados, incluindo cinco novos contratos de fronteira.

- [x] Passo 17 — Mover transporte HTTP e estado/políticas dos caches para `portfolio_quotes.py`, mantendo wrappers públicos e dependências explícitas. Fecha: critérios 15–17.
- [x] Passo 18 — Testar cache quente/frio/vencido, refresh, falhas de persistência/transporte e fronteiras de escrita; executar suíte completa. Fecha: critérios 13, 15–17. Suíte de 446 testes aprovada; após adicionar dois casos complementares, os 10 testes isolados de cache/transporte também passaram.
- [x] Passo 15 — Unificar consultas de entradas em `portfolio_positions.py` e montagem na fachada, sem duplicar a preparação. Fecha: critérios 12 e 13.
- [x] Passo 16 — Testar equivalência pública/interna, histórico, isolamento e fronteira transacional; executar suíte completa. Fecha: critérios 12–14.
- [x] Passo 12 — extrair configurações, consentimento e perfil criptografado para `consultor_settings.py`; preservar expurgo e isolamento por usuário.
- [x] Passo 13 — extrair catálogo, perfis educacionais, validação de seleção e prompts para `consultor_catalog.py`; compartilhar `ConsultorError` por módulo mínimo de erros, sem importar a fachada.
- [x] Passo 14 — manter reexports públicos, verificar contratos e executar a suíte completa. Fecha: critérios 10 e 11.

- [x] Passo 10 — extrair builders e compactação para `consultor_context.py`; manter validação, seleção e perfis na fachada, sem dependência circular.
- [x] Passo 11 — verificar payloads, minimização, reutilização de posições e imports compatíveis com testes isolados e suíte completa.

- [x] Passo 8 — extrair mensagens, payloads e transporte para `consultor_provider.py`, sem importar a fachada e preservando erros, injeção e mocks públicos.
- [x] Passo 9 — validar contratos dos provedores, falhas, fachada e suíte completa sem chamadas externas reais.

- [x] Passo 6 — extrair persistência do histórico, quota diária e cooldown para `consultor_history.py`, preservando imports públicos e exceções de `consultor.py`.
- [x] Passo 7 — adicionar contratos contra regressão e executar testes do Consultor e suíte completa.

- [x] Passo 1 — extrair tabela e resolução de rotas. Fecha: critérios 1 e 2.
- [x] Passo 2 — extrair agregação do Cockpit de `app.py`. Fecha: critério 6.
- [x] Passo 3 — criar fronteiras internas do Portfólio preservando fachada. Fecha: critérios 3 a 5.
- [x] Passo 4 — retirar projeções financeiras de `app.js` e modularizar internamente `portfolio-view.js`. Fecha: critério 7.
- [x] Passo 5 — executar testes de contratos, domínio e suíte completa. Fecha: critérios 1 a 7.

## Changelog

- `2.3` — 2026-08-31 — Separadas valorização por data (`portfolio_valuation.py`) e rentabilidade histórica (`portfolio_returns.py`), preservando regras, contratos e caches locais; testes de fronteira adicionados. Aplicação de cotações de mercado/fundos continua na fachada.

- `2.2` — 2026-08-31 — Transferidos transporte HTTP/JSON, caches de cotação/câmbio, persistência, locks, TTL, expurgo/LRU e fallback para `portfolio_quotes.py`. Fachada compatível e dependências injetadas sem ciclo. Testes de domínio, transporte/cache e fronteira transacional aprovados; sem incremento de produto. Retry SSL legado preservado e sinalizado no ADR-0014 para revisão própria.
- `2.1` — 2026-08-31 — Unificadas leitura e montagem das posições: tela e consumidores internos compartilham entradas, descontos de resgates, exclusão de encerrados, cotações e overrides do snapshot. Históricos preservados; testes de equivalência, imutabilidade, isolamento e fronteira transacional.
- `2.0` — 2026-08-31 — Extrações concluídas e documentação sincronizada: catálogo e prompts idênticos ao snapshot anterior, configurações e exceção pública preservadas; 419 testes aprovados. Fachada reduzida de 967 para 398 linhas, sem incremento da versão do produto.

- `1.9` — 2026-08-31 — Iniciada extração de configurações e catálogo, mantendo prompts, consentimento, criptografia e exceção pública.

- `1.8` — 2026-08-31 — Extração concluída: fachada com 967 linhas, contexto com 458; 412 testes aprovados na suíte completa, incluindo contratos de compactação, reexports e reutilização de posições. Sem alteração de versão do produto.

- `1.7` — 2026-08-31 — Planejada a extração dos contextos, preservando os contratos e a montagem central dos perfis na fachada.

- `1.6` — 2026-08-31 — Adaptador de provedores concluído com dependências tardias e tradução de erros na fachada; 75 testes focados e 406 testes da suíte completa aprovados, sem chamadas reais ao provedor nesta validação.

- `1.5` — 2026-08-31 — Iniciada extração do adaptador de provedores do Consultor, preservando mensagens, autenticação, timeout e compatibilidade.

- `1.4` — 2026-08-31 — Extração de `consultor_history.py` concluída e protegida por wrappers compatíveis, testes do Consultor e gate de qualidade.
- `1.3` — 2026-08-31 — Iniciada a desconcentração do Consultor pela extração isolada de histórico, quota e cooldown, mantendo `consultor.py` como fachada pública.
- `1.2` — 2026-08-30 — Vinculada à spec implementada [[../qualidade-codigo]], que formaliza as fronteiras preservadas por esta desconcentração.
- `1.1` — 2026-08-30 — Projeções de saldo/fatura movidas ao núcleo e Portfólio frontend dividido em gráfico, agrupamento, formulário e coordenador.
- `1.0` — 2026-08-30 — Refatoração arquitetural inicial da fundação v2 implementada e verificada.

## Relacionados

- [[../arquitetura]]
- [[../adr/0014-desconcentracao-fachadas-e-roteamento]]
- [[investimentos-portfolio]]
- [[frontend-modularizacao]]
