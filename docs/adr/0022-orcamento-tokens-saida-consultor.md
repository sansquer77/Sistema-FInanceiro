---
tipo: adr
area: consultor
status: em-implementacao
versao: 0.1
atualizado: 2026-11-01
relacionados:
  - "[[../specs/consultor]]"
  - "[[../arquitetura]]"
  - "[[0021-janela-contexto-local-consultor]]"
tags: [adr, "area/consultor", "status/em-implementacao"]
---

# ADR-0022 — Orçamento de tokens de saída do Consultor remoto

> [!info] Status
> **em-implementacao** · área: `consultor` · atualizado em 2026-11-01 · relacionados: [[../specs/consultor]], [[../arquitetura]], [[0021-janela-contexto-local-consultor]]

## Contexto

Análises remotas do Consultor passavam a usar `max_tokens = min(configurado nas Preferências, 900)`, com 1500 apenas para o card Análise da Carteira. Em modelos Gemini recentes, o raciocínio interno (`thoughtsTokenCount`) é descontado do mesmo `maxOutputTokens`. Medições reais na homologação com `gemini-3.6-flash` mostraram 470 tokens de raciocínio para 160 tokens de texto; com o limite de 700 salvo nas Preferências, restavam cerca de 230 tokens para o texto, e a resposta era truncada no meio das seções obrigatórias, bloqueando a entrega pelo pós-processamento que exige todas as seções.

Os limites de raciocínio do provedor não resolveram: `thinkingLevel: minimal` é rejeitado pelo modelo (400), `thinkingLevel: low` ainda gastou 434 tokens e elevou a latência para 65s, e `thinkingBudget: 0` não pôde ser validado (429 de cota na chave de homologação). O formato da requisição (URL, cabeçalho de chave, corpo) foi verificado e está correto.

## Decisão

- Análises **remotas** usam orçamento de saída com piso de 2500 e teto de 4000 tokens: `max(normalize(configurado), 2500)`, limitado a 4000.
- A **análise local** (WebLLM) mantém 900 tokens, porque a janela de 4096 tokens é compartilhada entre entrada, raciocínio e saída e um limite maior reduziria o espaço do prompt.
- Não enviar `thinkingConfig` nas chamadas remotas: os níveis testados não reduzem o raciocínio de forma confiável e adicionam risco de erro de contrato por modelo.
- Manter as repetições em erros transitórios (ADR-0021) e recomendar timeout de 60s nas Preferências, já que respostas maiores levam mais tempo.
- O custo por análise remota aumenta proporcionalmente ao teto apenas quando o modelo realmente gera os tokens; respostas curtas continuam consumindo o mesmo.

## Consequências

- As seções obrigatórias passam a caber mesmo quando o modelo gasta ~500 tokens de raciocínio, eliminando o truncamento que aparecia como "Consultor indisponível".
- O piso ignora uma configuração menor das Preferências para análises remotas; quem quiser respostas mais curtas deve reduzir o escopo do card, não o limite de tokens.
- Chaves com cota apertada podem falhar por 429 no provedor; o fluxo de indisponibilidade continua valendo e a mensagem permanece amigável.
- O teto de 4000 é uma proteção de custo e latência, não uma garantia de qualidade: respostas que ainda excedam esse orçamento continuam sendo bloqueadas pelo pós-processamento.

## Alternativas consideradas

- **Desativar o raciocínio com `thinkingBudget: 0`.** Não validado: a chave de homologação respondeu 429 de cota; além disso, o suporte varia por modelo e provedor.
- **Usar `thinkingLevel: minimal` ou `low`.** `minimal` é rejeitado pelo modelo e `low` manteve ~434 tokens de raciocínio com 65s de latência.
- **Manter 900 e encurtar o prompt de cada card.** Reduz o conteúdo da análise, mas não resolve a proporção entre raciocínio e texto quando o modelo decide pensar mais.
- **Enviar a análise em duas chamadas (rascunho e continuação).** Duplicaria custo e latência para o mesmo resultado.

## Relacionados

- [[../specs/consultor]] — critérios 79 e 80, passos 40 e 41.
- [[../arquitetura]] — v4.57.
- [[0021-janela-contexto-local-consultor]] — janela local e repetição de erros transitórios.
