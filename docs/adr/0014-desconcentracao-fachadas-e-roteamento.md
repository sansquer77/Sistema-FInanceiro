---
tipo: adr
area: arquitetura-v2
status: implementado
versao: 1.3
atualizado: 2026-08-31
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
> **implementado** · área: `arquitetura-v2` · atualizado em 2026-08-31 · relacionados: [[../specs/desconcentracao-arquitetura-v2]], [[../arquitetura]]

## Contexto

`portfolio.py`, `app.py` e `web/app.js` cresceram como pontos de concentração. Uma substituição integral aumentaria o risco de quebrar integrações internas, testes e bancos existentes justamente na fundação da v2.

## Decisão

Adotar extração incremental com fachadas compatíveis. `portfolio.py` conserva nomes públicos e orquestra módulos internos de posições, cálculos e cotações. A tabela de rotas fica em `http_routes.py`, sem framework web, enquanto `AppHandler` conserva transporte, autenticação, validação de origem e adaptação HTTP. Payloads de domínio saem de `app.py` para módulos de `financeiro/`.

### Confirmação de resgates e encerramentos sem rede

As entradas locais são lidas em uma transação curta de leitura, encerrada antes de obter cotações. Depois, `BEGIN IMMEDIATE` protege a releitura das mesmas entradas e a gravação. Se as entradas não mudaram, reutilizam-se as posições preparadas; se mudaram, a operação retorna HTTP 409 e pede nova tentativa, sem efeitos financeiros. A comparação inclui operações elegíveis, posições iniciais, resgates, encerramentos, ajustes manuais e dados relevantes das contas, limitada ao usuário. Cotações/cache não participam da comparação: os valores são os obtidos no preparo.

Aquecer cache e recomputar dentro da escrita foi descartado: expiração, falha ou remoção de cache ainda poderiam disparar rede. A comparação otimista evita essa dependência sem criar versões de linha ou migrações; o trade-off é uma leitura local adicional e a possibilidade de rejeitar a operação quando outra posição da mesma carteira muda. Não há repetição automática de mutações.

## Consequências

### Transporte/cache do Portfólio

`portfolio_quotes.QuoteCache` possui os caches e locks, consulta/grava o cache SQLite e coordena TTL, expurgo, LRU, refresh e fallback vencido. A fachada injeta conexão, relógio, leitor HTTP e classe de erro, mantendo wrappers públicos e aliases dos mesmos objetos de cache. O transporte HTTP/JSON também reside no módulo interno; não há importação reversa de `portfolio.py` nem troca temporária de globais para encaminhar dependências. Assim testes e consumidores existentes podem continuar substituindo `portfolio.read_json_url`, `portfolio.urlopen` e `portfolio.get_connection`.

Alternativa descartada: mover funções com importação da fachada dentro do módulo interno, pois manteria acoplamento circular. O custo aceito é manter wrappers de compatibilidade explícitos. Normalização dos provedores e cálculos de valorização não fazem parte desta etapa. Políticas existentes foram preservadas, inclusive o retry legado sem verificação de certificado para erro SSL específico; esse comportamento precisa de revisão de segurança separada e não é uma garantia de transporte seguro.

### Atualização após salvar lançamentos e custo da projeção

A resposta confirmada do servidor atualiza a ocorrência antes das recargas. A fatia conta/mês tem prioridade e confirma os efeitos de séries e exclusões; contas e histórico global são atualizados depois, sem bloquear o formulário. Essas respostas auxiliares só são aplicadas se revisão e sessão continuam atuais. O Cockpit é invalidado para a próxima entrada. Saldos ficam indisponíveis enquanto a projeção é revalidada, em vez de mostrar valores antigos ou calcular deltas no navegador. Falha após gravação é comunicada como falha de atualização, não de salvamento.

O backend ordena os movimentos e acumula lotes por data, em centavos. Faturas conciliadas não pagas são agregadas uma vez e entram na reserva por vencimento, preservando o tratamento existente de pagamentos. Evita-se custo proporcional a datas × histórico sem criar cache financeiro persistente. O trade-off é manter acumuladores temporários durante a requisição. Recalcular tudo por data foi descartado pelo custo; cálculos otimistas no frontend foram descartados pela duplicação de regras financeiras. Testes comparam todas as datas contra as funções de referência.

- Consumidores atuais não precisam migrar em bloco.
- Fronteiras menores podem ganhar testes próprios e evoluir independentemente.
- Wrappers só são aceitos na fachada pública quando protegem compatibilidade; wrappers de view sem função contratual devem ser removidos progressivamente.
- Dependências circulares são evitadas mantendo os módulos internos independentes da fachada.

## Alternativas consideradas

- Reescrever o Portfólio de uma vez: rejeitada pelo risco de regressão.
- Introduzir framework/roteador externo: rejeitada por contrariar o ADR-0001.
- Mover apenas funções entre arquivos JS: rejeitada para regras financeiras, pois não corrige a fronteira de autoridade.

## Changelog

- `1.3` — 2026-08-31 — Transporte/cache efetivos no módulo interno, com dependências injetadas e fachada compatível; política TLS legada identificada para revisão separada.
- `1.2` — 2026-08-31 — Atualização confirmada de lançamentos desacoplada de dados auxiliares e projeção incremental por data.
- `1.1` — 2026-08-31 — Decisão de confirmação otimista sem rede para resgate/encerramento, com conflito seguro em vez de recomposição sob bloqueio.

- `1.0` — 2026-08-30 — Decisão adotada para a desconcentração inicial da v2.

## Relacionados

- [[../specs/desconcentracao-arquitetura-v2]]
- [[../arquitetura]]
- [[0001-stack-local-sem-framework]]
- [[0002-modularizacao-frontend]]
