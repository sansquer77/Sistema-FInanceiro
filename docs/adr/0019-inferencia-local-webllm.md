---
tipo: adr
area: ia-local
status: em-implementacao
versao: 0.9
atualizado: 2026-11-18
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
> **em-implementacao** · área: `ia-local` · atualizado em 2026-11-18 · relacionados: [[0002-modularizacao-frontend]], [[0006-classificacao-assistida-local]], [[0010-segredos-criptografados-sqlite]], [[../specs/consultor]], [[../specs/tendencias-saude-financeira]], [[../distribuição]]

## Contexto

O Consultor e Tendências precisam de sínteses de IA com o mesmo requisito de privacidade e disponibilidade. Duplicar a seleção de IA local, remota e resumo determinístico em cada módulo faria consentimento, fallback e experiência divergirem. A aplicação é offline-first, já preserva o backend Python como fronteira das regras financeiras e não possui build step no frontend.

## Decisão

Adotar WebLLM como opção de inferência local no navegador, com `Qwen2.5-1.5B-Instruct-q4f16_1-MLC` como modelo padrão. Uma política central `ai_execution_settings` define `local_primeiro` e o `local_model_id` por usuário, e é consumida por todos os recursos: local → remota consentida → determinística. A IA remota continua disponível como fallback somente quando já configurada e autorizada pelo usuário.

Se a geração perder o dispositivo GPU por memória insuficiente, o cliente descarrega o engine e tenta temporariamente `gemma3-1b-it-q4f16_1-MLC`, sem regravar a preferência do usuário. A troca temporária é informada na interface; o usuário continua podendo escolher outro modelo nas Preferências.

Quando o WebLLM executado em Worker serializar a falha como texto após a perda do dispositivo, o cliente também trata esse retorno como falha recuperável: descarrega o engine, tenta o Gemma 3 1B e cria essa segunda tentativa diretamente na página, preservando a preferência persistida.

As Preferências exibem um catálogo fechado de modelos WebLLM já presentes no runtime vendorizado, com estimativa de memória e indicação de uso. A troca de seleção não apaga o cache anterior; cada modelo é identificado separadamente pelo cache privado do navegador. O botão de atualização permite remover e reconstruir o cache do modelo selecionado quando houver falha ou atualização dos pesos.

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

- `0.9` — 2026-11-18 — Documenta o retry do modelo local ultraleve no contexto principal quando o Worker Safari devolve a perda da GPU como `string_error`.
- `0.8` — 2026-11-18 — Registra a necessidade de invalidar o cache dos módulos cliente e worker quando o fallback local é alterado, evitando que navegadores executem o cliente WebLLM anterior.
- `0.7` — 2026-11-18 — Adiciona fallback local temporário para o Gemma 3 1B quando o modelo selecionado perde o dispositivo GPU por memória insuficiente durante a geração.
- `0.6` — 2026-11-18 — Substitui o modelo padrão pelo Qwen 2.5 1.5B, adiciona catálogo fechado selecionável por usuário, cache separado por modelo e atualização forçada do cache selecionado.
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
