---
tipo: adr
area: investimentos
status: implementado
versao: 1.1
atualizado: 2026-09-04
relacionados:
  - "[[../specs/rentabilidade-portfolio]]"
  - "[[../specs/investimentos-portfolio]]"
  - "[[0003-sqlite-fonte-de-verdade]]"
tags: [adr, "area/investimentos", "status/implementado"]
aliases: ["ADR-0017", "Snapshots de rentabilidade"]
---

# ADR-0017 — Snapshots mensais para rentabilidade do Portfólio

> [!info] Status
> **implementado** · área: `investimentos` · atualizado em 2026-09-04 · relacionados: [[../specs/rentabilidade-portfolio]], [[../specs/investimentos-portfolio]]

## Contexto

A série atual compara valores mensais agregados, mas não possui histórico persistido por ativo. Para renda variável, ETFs e cripto, o valor atual pode ser reutilizado como aproximação de meses anteriores, produzindo variações que não representam fielmente a evolução do patrimônio.

## Decisão

Persistir snapshots mensais por ativo e competência, mantendo a API e o flyover agregados por moeda. Cada snapshot deverá registrar, no mínimo:

- usuário, posição, competência e data de referência;
- quantidade, preço usado, valor de mercado e custo acumulado;
- aportes, resgates e proventos líquidos da competência;
- moeda, fonte da cotação e nível de confirmação;
- indicação explícita de `observado` ou `aproximado`.

O cálculo interno poderá usar cada ativo para determinar a contribuição, mas a resposta pública continuará contendo somente BRL, USD, CDI e IPCA. Nenhuma lista de ativos será adicionada ao flyover.

Snapshots ausentes não serão inventados: o período continuará disponível, marcado como aproximado. A captura será idempotente e não fará chamadas externas enquanto uma transação SQLite estiver aberta.

A captura ocorre sob demanda ao abrir a rentabilidade. Durante a competência, a mesma chave é atualizada e preserva a observação mais recente disponível; ao mudar o mês, a última captura anterior permanece imutável. Se o aplicativo não tiver sido usado durante uma competência, ela continua aproximada.

## Plano de implantação

1. Criar a tabela e a migração idempotente.
2. Implementar repositório de leitura/escrita e política de competência.
3. Integrar a valorização por data e as fontes de cotação já verificadas.
4. Ajustar `portfolio_returns.py` para priorizar snapshots e agregar por moeda.
5. Expor cobertura e aproximação no contrato sem aumentar o payload com ativos.
6. Atualizar o flyover e a nota explicativa.
7. Cobrir aportes, resgates, proventos, moedas, meses futuros, falhas de fonte e reprocessamento idempotente.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Consultar histórico externo a cada abertura | Rejeitada: dependência de rede, limites de uso e resultados instáveis. |
| Mostrar contribuição dos 89 ativos no flyover | Rejeitada: excesso de informação e impacto visual. |
| Recalcular o passado usando somente o valor atual | Mantida apenas como fallback explicitamente aproximado. |
| Persistir somente totais por moeda | Rejeitada: não permite auditar a origem da variação por ativo. |

## Consequências

- A qualidade da rentabilidade melhora progressivamente a cada competência capturada.
- O histórico anterior à implantação pode continuar aproximado.
- O banco cresce proporcionalmente a posições × competências, exigindo índices e política de retenção definida na implementação.
- A funcionalidade é compatível com o contrato visual atual e não exige nova dependência externa.

## Changelog

- `1.1` — 2026-09-04 — Captura antecipada ao cálculo e uso explícito dos fluxos do snapshot eliminam o primeiro resultado aproximado e preparam aportes, resgates e proventos.
- `1.0` — 2026-09-04 — Implementação concluída com captura sob demanda, persistência idempotente, cobertura explícita e flyover agregado por moeda.
- `0.1` — 2026-09-04 — Decisão inicial para snapshots mensais por ativo com apresentação agregada por moeda.

## Relacionados

- [[../specs/rentabilidade-portfolio]]
- [[../specs/investimentos-portfolio]]
- [[0003-sqlite-fonte-de-verdade]]
