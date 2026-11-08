---
tipo: adr
area: ia-local
status: em-implementacao
versao: 0.3
atualizado: 2026-11-01
relacionados:
  - "[[0019-inferencia-local-webllm]]"
  - "[[../specs/consultor]]"
  - "[[../arquitetura]]"
tags: [adr, "area/ia-local", "status/em-implementacao"]
aliases: ["ADR-0021", "Janela de contexto do modelo local"]
---

# ADR-0021 — Janela de contexto e orçamento de tokens da inferência local

> [!info] Status
> **em-implementacao** · área: `ia-local` · atualizado em 2026-10-31 · relacionados: [[0019-inferencia-local-webllm]], [[../specs/consultor]], [[../arquitetura]]

## Contexto

O modelo local `Qwen2.5-3B-Instruct-q4f16_1-MLC` usa, por padrão no WebLLM, uma janela de contexto de 4096 tokens. O card **Melhor Destino para Investimentos a Vencer** enviava uma linha do tempo de lançamentos futuros sem limite, e com dados reais o prompt chegou a cerca de 30 mil caracteres (estimativa de mais de 8 mil tokens). A inferência falhava antes de gerar qualquer resposta, e o fallback remoto também falhava no mesmo cenário.

Duas causas precisam ser tratadas: a janela configurada pelo cliente e o tamanho do payload que o backend monta.

## Decisão

1. **Solicitar janela de 8192 tokens** ao criar o engine WebLLM (`chatOpts.context_window_size`), nos modos Worker e página, mantendo o mesmo modelo e o mesmo cache de pesos. O custo de memória é o cache de chave/valor, de cerca de 36 KB por token para este modelo, ou cerca de 300 MB na janela cheia.
2. **Limitar o payload no backend** do card de vencimentos: 4 datas por moeda na linha do tempo, até 3 meses por moeda, 5 faturas abertas, sem valores zerados nos eventos, com contagem de itens omitidos e saldo projetado ao fim do horizonte preservados. Medido com dados reais de homologação, o payload caiu de cerca de 25 mil para 7.933 caracteres.
3. O orçamento de tokens da inferência local passa a ser: prompt do sistema + payload + 900 tokens de resposta, dentro de 8192. Pela contagem de caracteres (5.218 do sistema e 7.933 do payload), a estimativa é de cerca de 4 mil tokens no pior caso medido, mas essa contagem ainda não foi validada com o tokenizador do Qwen.

## Consequências

- A falha por janela excedida deixa de ocorrer no cenário atual e tem margem para crescimento moderado dos dados.
- O limite do payload é a proteção principal: a janela maior sozinha só adia o problema e aumenta o uso de memória em navegadores com pouca GPU.
- Equipamentos sem memória para 8192 podem falhar ao carregar o engine; a mensagem de erro de inicialização existente continua aplicável. Se isso ocorrer em escala, a janela pode voltar a 4096, pois o limite do payload continua válido.
- Itens omitidos da linha do tempo não aparecem no texto da análise; o card informa a contagem para que a IA não trate a lista como completa.
- Não há mudança de modelo, de política de consentimento nem de fallback.

## Alternativas consideradas

- **Só aumentar a janela:** descartada como solução única, porque o payload continuaria sem limite e o custo de memória cresceria com os dados do usuário.
- **Só limitar o payload:** descartada como solução única por não dar margem para as instruções do sistema e para a resposta de 900 tokens quando o card tiver muitos itens reais; mantida como proteção principal.
- **Trocar para um modelo com janela maior:** descartada nesta etapa, porque exige novo download de pesos, nova validação de qualidade em português e nova decisão de licença.
- **Resumir os dados no navegador:** descartada, porque o AGENTS.md proíbe regra financeira em JavaScript; o corte fica no backend.

## Histórico

- `0.3` — 2026-11-01 — Prompts locais acima de 11.000 caracteres (estimativa conservadora de ~3 caracteres por token para a entrada de 4096 − 900 tokens) não são tentados localmente quando a IA remota está permitida. O limite é uma estimativa e deve ser recalibrado se o tokenizador do Qwen for medido. Erros transitórios da IA remota são repetidos em até 3 tentativas.
- `0.2` — 2026-11-01 — **Revisão da decisão 1.** Em uso real no navegador, a geração com janela de 8192 tokens terminou em perda do dispositivo GPU ("Device was lost ... insufficient memory"). A janela volta ao padrão do modelo (4096). O limite de payload (decisão 2) permanece. A falha de memória passa a ser tratada como falha local: quando a IA remota está configurada e permitida pela política, o Consultor usa a remota; em `somente_local` não há chamada remota. A estimativa de tokens continua sem validação com o tokenizador do Qwen e pode exigir mais redução de payload se o prompt ultrapassar a janela.
- `0.1` — 2026-10-31 — Decisão inicial de janela de 8192 tokens com limite de payload no card de vencimentos.
