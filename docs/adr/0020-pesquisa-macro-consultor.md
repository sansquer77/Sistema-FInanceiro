---
tipo: adr
area: consultor
status: em-implementacao
versao: 0.1
atualizado: 2026-10-11
relacionados:
  - "[[../specs/consultor]]"
  - "[[../arquitetura]]"
  - "[[0015-ssrf-ai-endpoints]]"
  - "[[0019-inferencia-local-webllm]]"
tags: [adr, "area/consultor", "status/em-implementacao"]
---

# ADR-0020 — Pesquisa macroeconômica sem dados do usuário

> [!info] Status
> **em-implementacao** · área: `consultor` · atualizado em 2026-10-11 · relacionados: [[../specs/consultor]], [[../arquitetura]], [[0015-ssrf-ai-endpoints]], [[0019-inferencia-local-webllm]]

## Contexto

O card **Análise da Carteira** precisa de informações macroeconômicas atuais, enquanto o resultado da pesquisa pode ser útil tanto à inferência WebLLM local quanto à IA remota. A consulta inicial deve permanecer separada do contexto financeiro: carteira, perfil e quaisquer dados do usuário não podem chegar ao provedor durante a pesquisa.

## Decisão

- Restringir a pesquisa ao card `analise_carteira` e a um tópico macroeconômico fixo sobre mercado de ações, sem contexto do usuário.
- Usar busca web nativa apenas nas APIs oficiais de provedores que tenham adaptador explícito. Não presumir que endpoints customizados, locais ou compatíveis com chat completions implementem pesquisa web.
- Executar a pesquisa somente quando a política central atual permitir o estágio remoto. Assim, `somente_local` não causa tráfego remoto nem mesmo para esse enriquecimento.
- Limitar tokens, buscas, fontes, tamanho do resultado e timeout; tratar texto pesquisado como conteúdo externo não confiável, nunca como instrução.
- Passar resumo, data e fontes junto ao contexto da carteira somente no segundo passo, à inferência selecionada pela política central.
- Falha, ausência de fontes ou provedor incompatível não bloqueiam a análise; não inventar pesquisa nem fontes.
- Não armazenar o payload intermediário da pesquisa ou enviar contexto financeiro durante esse passo.

## Consequências

- A pesquisa pode aprimorar tanto a inferência local quanto a remota sem revelar a carteira ao provedor de pesquisa.
- O benefício varia por provedor, modelo, disponibilidade da busca e consentimento/política central; configurações locais e customizadas sem adaptação explícita seguem sem enriquecimento.
- O adaptador deve preservar fontes citáveis e as barreiras anti-SSRF existentes.

## Alternativas consideradas

- Consultar a IA remota com o prompt da carteira diretamente: rejeitada porque encaminha os dados do usuário junto com a pesquisa.
- Usar busca genérica em qualquer endpoint OpenAI-compatible/custom: rejeitada porque o endpoint pode não suportar busca e não possui contrato confiável de citações.
- Impedir a análise se não houver pesquisa: rejeitada para preservar a disponibilidade da análise financeira.

## Changelog

- `0.1` — 2026-10-11 — Decisão inicial sobre busca macroeconômica prévia isolada dos dados do usuário.

## Relacionados

- [[../specs/consultor]]
- [[../arquitetura]]
- [[0015-ssrf-ai-endpoints]]
- [[0019-inferencia-local-webllm]]
