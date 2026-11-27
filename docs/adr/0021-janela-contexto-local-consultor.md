---
tipo: adr
area: ia-local
status: em-implementacao
versao: 0.6
atualizado: 2026-11-26
relacionados:
  - "[[0019-inferencia-local-webllm]]"
  - "[[../specs/consultor]]"
  - "[[../arquitetura]]"
tags: [adr, "area/ia-local", "status/em-implementacao"]
aliases: ["ADR-0021", "Janela de contexto do modelo local"]
---

# ADR-0021 — Janela de contexto e orçamento de tokens da inferência local

> [!info] Status
> **em-implementacao** · área: `ia-local` · atualizado em 2026-11-26 · relacionados: [[0019-inferencia-local-webllm]], [[../specs/consultor]], [[../arquitetura]]

## Contexto

O modelo local `Qwen2.5-3B-Instruct-q4f16_1-MLC` usa, por padrão no WebLLM, uma janela de contexto de 4096 tokens. O card **Melhor Destino para Investimentos a Vencer** enviava uma linha do tempo de lançamentos futuros sem limite, e com dados reais o prompt chegou a cerca de 30 mil caracteres (estimativa de mais de 8 mil tokens). A inferência falhava antes de gerar qualquer resposta, e o fallback remoto também falhava no mesmo cenário.

Duas causas precisam ser tratadas: a janela configurada pelo cliente e o tamanho do payload que o backend monta.

## Decisão

1. **Solicitar janela de 4096 tokens** ao criar o engine WebLLM (`chatOpts.context_window_size`), nos modos Worker e página, mantendo o mesmo modelo e o mesmo cache de pesos. Em uso real, 8192 tokens causou perda do dispositivo GPU por falta de memória.
2. **Limitar o payload no backend** do card de vencimentos: 4 datas por moeda na linha do tempo, até 3 meses por moeda, 5 faturas abertas, sem valores zerados nos eventos, com contagem de itens omitidos e saldo projetado ao fim do horizonte preservados. Medido com dados reais de homologação, o payload caiu de cerca de 25 mil para 7.933 caracteres.
3. O orçamento de tokens da inferência local passa a ser: prompt do sistema + payload + 900 tokens de resposta, dentro da janela de 4096. O servidor usa o limite operacional de 11.000 caracteres para decidir quando desviar para a IA remota; a contagem em caracteres é uma estimativa conservadora e não substitui a medição com o tokenizador do Qwen.

4. O payload compacto do card é o contrato único para inferência local e remota. O backend calcula os valores completos antes da compactação; o modelo recebe vencimentos agrupados por data, moeda, tipo e comprometimento, além de uma única linha do tempo financeira por moeda. As representações internas em centavos e estruturas repetidas de projeção não são necessárias para a decisão do modelo.
5. O mesmo contrato compacto também vale para **Análise da Carteira**: depois dos cálculos financeiros, o backend envia agregados por classe, moeda e mercado, limita cada lista e acrescenta um grupo com o total dos itens omitidos. Valores exibíveis, metas, compromissos, score e fontes de cotação são preservados; centavos, floats, posições individuais e identificadores não são repetidos no payload.
6. Os prompts usam um bloco comum curto, sem repetir guardrails equivalentes, e o card **Evolução do Score no Tempo** envia a definição dos pilares uma única vez; cada mês carrega apenas seus valores e estado. A mesma mensagem compacta é usada na preparação local e na chamada remota.

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

- `0.6` — 2026-11-26 — Otimiza o prompt comum dos cards e compacta a série de pilares da Evolução do Score, mantendo a janela de 12 meses abaixo do limite operacional local.
- `0.5` — 2026-11-26 — Estende o contrato compacto à Análise da Carteira, agregando classes, moedas e mercados, preservando totais omitidos e alinhando a decisão à janela real de 4096 tokens.
- `0.4` — 2026-11-26 — Torna o payload compacto do card de vencimentos único para IA local e remota; agrupa vencimentos equivalentes e elimina a repetição entre projeção mensal, eventos e lista de faturas depois dos cálculos do backend.
- `0.3` — 2026-11-01 — Prompts locais acima de 11.000 caracteres (estimativa conservadora de ~3 caracteres por token para a entrada de 4096 − 900 tokens) não são tentados localmente quando a IA remota está permitida. O limite é uma estimativa e deve ser recalibrado se o tokenizador do Qwen for medido. Erros transitórios da IA remota são repetidos em até 3 tentativas.
- `0.2` — 2026-11-01 — **Revisão da decisão 1.** Em uso real no navegador, a geração com janela de 8192 tokens terminou em perda do dispositivo GPU ("Device was lost ... insufficient memory"). A janela volta ao padrão do modelo (4096). O limite de payload (decisão 2) permanece. A falha de memória passa a ser tratada como falha local: quando a IA remota está configurada e permitida pela política, o Consultor usa a remota; em `somente_local` não há chamada remota. A estimativa de tokens continua sem validação com o tokenizador do Qwen e pode exigir mais redução de payload se o prompt ultrapassar a janela.
- `0.1` — 2026-10-31 — Decisão inicial de janela de 8192 tokens com limite de payload no card de vencimentos.
