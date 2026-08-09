---
tipo: adr
area: seguranca
status: implementado
versao: 1.0
atualizado: 2026-08-09
relacionados:
  - "[[../specs/preferencias-abas]]"
  - "[[../arquitetura]]"
  - "[[0005-smtp-criptografado-local]]"
  - "[[0003-sqlite-fonte-de-verdade]]"
tags: [adr, "area/seguranca", "status/implementado"]
aliases: ["ADR-0010", "Segredos criptografados no SQLite"]
---

# ADR-0010 — Segredos criptografados no SQLite com chave fora de data

> [!info] Status
> **implementado** · área: `seguranca` · atualizado em 2026-08-09 · relacionados: [[../specs/preferencias-abas]], [[../arquitetura]], [[0005-smtp-criptografado-local]]

## Problema

SMTP, IA e integrações opcionais acumulavam arquivos `.enc` por usuário dentro de `data/`. Embora os segredos já estivessem criptografados, o diretório `data/` também contém banco, logs e demais artefatos de runtime; manter a chave mestra no mesmo diretório tornava backup, suporte e atualização mais propensos a copiar material sensível junto com dados operacionais.

## Decisão

Persistir segredos de usuário como envelopes criptografados em `secure_configs.payload_enc` no SQLite, mantendo os campos não secretos em suas tabelas próprias. A chave mestra padrão deixa `data/email_config.key` e passa a ser criada em `secure/config.key`, um diretório irmão de `data/`.

Instalações existentes continuam compatíveis:

- se `data/email_config.key` existir e `secure/config.key` ainda não existir, o app copia a chave para o novo caminho no primeiro uso;
- se arquivos `data/email_config_user_{id}.enc`, `data/ai_config_user_{id}.enc` ou `data/mais_retorno_config_user_{id}.enc` existirem, o app copia o envelope criptografado para `secure_configs` na primeira leitura;
- os arquivos legados não são apagados automaticamente durante a migração, reduzindo risco para usuários em atualização.

Servidores ou instalações administradas podem definir `SISTEMA_FINANCEIRO_CONFIG_KEY_PATH` para outro caminho persistente, ou `SISTEMA_FINANCEIRO_CONFIG_KEY` quando a chave vier de variável de ambiente.

## Alternativas Consideradas

- **Keychain macOS / Credential Manager Windows / Secret Service Linux**: melhor isolamento por sistema operacional, mas adicionaria diferença operacional por plataforma e não ajuda diretamente no modo servidor acessado por rede.
- **Manter tudo em arquivos `.enc` no `data/`**: simples, mas pior para atualização e suporte, pois espalha segredos em arquivos de runtime.
- **Guardar segredos em texto puro no banco**: rejeitado; contraria as regras de segurança do projeto.

## Consequências

- O backup do SQLite passa a conter envelopes criptografados, mas não a chave mestra.
- O pacote de atualização deve preservar `data/` e `secure/`, sem embutir esses diretórios em zips de distribuição.
- A migração é transparente para os usuários atuais e não exige recadastro de API keys ou senha SMTP.

## Changelog

- `1.0` — 2026-08-09 — Decisão inicial: segredos em `secure_configs`, chave padrão em `secure/config.key`, compatibilidade com arquivos `.enc` legados.

## Relacionados

- [[../specs/preferencias-abas]]
- [[../arquitetura]]
- [[0005-smtp-criptografado-local]]
- [[0003-sqlite-fonte-de-verdade]]
