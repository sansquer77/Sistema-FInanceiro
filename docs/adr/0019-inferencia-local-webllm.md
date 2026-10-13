---
tipo: adr
area: ia-local
status: em-implementacao
versao: 0.5
atualizado: 2026-10-10
relacionados:
  - "[[0002-modularizacao-frontend]]"
  - "[[0006-classificacao-assistida-local]]"
  - "[[0010-segredos-criptografados-sqlite]]"
  - "[[../specs/consultor]]"
  - "[[../distribuição]]"
tags: [adr, "area/ia-local", "status/em-implementacao"]
aliases: ["ADR-0019", "Inferência local WebLLM"]
---

# ADR-0019 — Inferência local compartilhada com WebLLM

> [!info] Status
> **em-implementacao** · área: `ia-local` · atualizado em 2026-10-10 · relacionados: [[0002-modularizacao-frontend]], [[0006-classificacao-assistida-local]], [[0010-segredos-criptografados-sqlite]], [[../specs/consultor]], [[../specs/tendencias-saude-financeira]], [[../distribuição]]

## Contexto

O Consultor e Tendências precisam de sínteses de IA com o mesmo requisito de privacidade e disponibilidade. Duplicar a seleção de IA local, remota e resumo determinístico em cada módulo faria consentimento, fallback e experiência divergirem. A aplicação é offline-first, já preserva o backend Python como fronteira das regras financeiras e não possui build step no frontend.

## Decisão

Adotar WebLLM como opção de inferência local no navegador, com `Qwen2.5-3B-Instruct-q4f16_1-MLC` como modelo inicial. Uma política central `ai_execution_settings` define `local_primeiro` por padrão e é consumida por todos os recursos: local → remota consentida → determinística. A IA remota continua disponível como fallback somente quando já configurada e autorizada pelo usuário.

O runtime JavaScript e seu worker serão vendorizados com versão, hash e licença auditáveis. A CSP libera somente `wasm-unsafe-eval` para a compilação do runtime WebAssembly, sem liberar `unsafe-eval` para JavaScript. Os pesos do modelo não entram no instalador principal: serão baixados no primeiro uso a partir de origem fixada e mantidos no cache privado do navegador. Um pacote offline opcional poderá ser avaliado separadamente.

As Preferências oferecem controle explícito para baixar, verificar e remover o modelo. Esse cache pertence ao perfil e à origem do navegador, portanto não fica na pasta do aplicativo e não pode ser compartilhado por um servidor entre usuários ou máquinas. Instalações via servidor exigem download uma vez por perfil cliente compatível.

O backend continua montando o contexto minimizado, validando propriedade, aplicando quota/cooldown e pós-processando a saída. A inferência local recebe o prompt fechado e o contexto do card por uma rota autenticada; a resposta volta ao backend para a validação e persistência usuais. Nenhuma chave de provedor é exposta ao navegador.

## Consequências

- Usuários compatíveis usam Consultor e Tendências sem conta nem API key e sem enviar o contexto para um provedor externo.
- Consentimento e ordem de execução têm uma única origem; um recurso não pode usar IA remota se a política central não o permitir.
- O primeiro uso requer download e WebGPU; a interface deve indicar progresso, capacidade e erros recuperáveis.
- O modelo ocupa espaço no cache do navegador e pode ser removido por políticas do próprio navegador.
- A dependência adiciona worker, política de Content Security Policy e cabeçalhos de isolamento; todos precisam ser compatíveis com a distribuição local e LAN.
- A qualidade local é inferior à de alguns provedores remotos. A escolha explícita de prioridade permite equilibrar privacidade, velocidade e qualidade.

## Alternativas consideradas

| Alternativa | Decisão |
|---|---|
| Manter somente IA remota | Rejeitada: mantém custo, conta e envio de dados como requisito. |
| Embutir pesos do modelo no instalador principal | Adiada: torna cada instalador e atualização substancialmente maior. |
| Executar modelo local no backend Python | Rejeitada: introduziria runtime/modelos nativos e requisitos de distribuição incompatíveis com a arquitetura atual. |
| Mover contexto financeiro e regras ao JavaScript | Rejeitada: viola a fronteira do núcleo Python e aumenta o risco de inconsistência. |

## Changelog

- `0.5` — 2026-10-10 — Registra a exceção CSP mínima `wasm-unsafe-eval`, necessária para o runtime WebAssembly local do WebLLM e distinta de `unsafe-eval` JavaScript.
- `0.4` — 2026-10-10 — Adiciona controles explícitos do cache privado do navegador; confirma que pesos não pertencem ao diretório da aplicação nem ao host do servidor.
- `0.3` — 2026-10-10 — Escopo ampliado para política central compartilhada por Consultor e Tendências, com fallback determinístico e consentimento remoto único.
- `0.2` — 2026-10-10 — Runtime WebLLM 0.2.85 vendorizado em `web/vendor/webllm/0.2.85/`, com licença Apache-2.0 e SHA-256 registrado; worker passa a importar somente o artefato local.
- `0.1` — 2026-10-10 — Decisão inicial de adotar WebLLM local-first no Consultor, com Qwen 2.5 3B, download no primeiro uso e fallback remoto consentido.

## Relacionados

- [[0002-modularizacao-frontend]]
- [[0006-classificacao-assistida-local]]
- [[0010-segredos-criptografados-sqlite]]
- [[../specs/consultor]]
- [[../distribuição]]
