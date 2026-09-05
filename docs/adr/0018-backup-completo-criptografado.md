---
tipo: adr
area: seguranca
status: rascunho
versao: 0.1
atualizado: 2026-09-05
relacionados:
  - "[[../specs/backup-restauracao]]"
  - "[[0010-segredos-criptografados-sqlite]]"
  - "[[0003-sqlite-fonte-de-verdade]]"
  - "[[../distribuição]]"
tags: [adr, "area/seguranca", "status/rascunho"]
aliases: ["ADR-0018", "Backup completo criptografado"]
---

# ADR-0018 — Pacote completo de backup criptografado

> [!info] Status
> **rascunho** · área: `seguranca` · atualizado em 2026-09-05 · relacionados: [[../specs/backup-restauracao]], [[0010-segredos-criptografados-sqlite]]

## Contexto

O `finance.db` não é o único artefato necessário para recuperar uma instalação. O ambiente também possui configurações criptografadas e a chave mestra local. Uma cópia simples do arquivo SQLite pode ser inconsistente durante uma escrita, omitir o estado WAL ou restaurar um banco sem a capacidade de ler suas configurações protegidas.

O usuário solicitou um backup completo em pacote ZIP, salvo em diretório escolhido nas Preferências e executado de forma recorrente. O pacote pode circular em mídia removível, pasta compartilhada ou sincronização externa; portanto, seu conteúdo financeiro e suas chaves não podem ficar expostos.

## Decisão proposta

Adotar um pacote ZIP como container de transporte, mas proteger o conteúdo em um payload criptografado com autenticação forte. O ZIP não usará ZipCrypto nem dependerá da criptografia legada da biblioteca padrão. O payload protegido conterá:

- cópia online consistente de `finance.db`;
- configurações criptografadas necessárias;
- chave mestra local;
- manifesto com versão, schema, arquivos, tamanhos, hashes SHA-256 e resultado de integridade;
- instruções mínimas de restauração sem dados financeiros.

A senha será fornecida na configuração da aba Backup em Preferências. Para permitir execução automática, o usuário poderá optar por armazená-la criptografada em `secure_configs`, protegida pela chave mestra atual. A senha nunca será gravada em texto puro, logs, banco sem proteção ou no pacote fora do payload cifrado.

O algoritmo, KDF, parâmetros e dependência multiplataforma ainda precisam ser fechados antes da implementação. O formato deve usar criptografia autenticada, salt e nonce aleatórios por pacote, envelope versionado e rejeição de parâmetros que possam causar consumo arbitrário de CPU ou memória.

## Alternativas consideradas

| Alternativa | Avaliação |
|---|---|
| Copiar somente `finance.db` | Rejeitada: pode ser inconsistente em uso e não recupera configurações/chave. |
| Copiar `finance.db`, `-wal` e `-shm` manualmente | Rejeitada: acopla a implementação ao estado do journal e não produz restauração validada. |
| ZIP sem criptografia | Rejeitada: expõe dados financeiros e segredos locais. |
| ZipCrypto ou criptografia legada de `zipfile` | Rejeitada: proteção insuficiente para um backup completo. |
| Exigir senha a cada backup automático | Mantida como opção de segurança, mas inviabiliza a recorrência sem interação. |
| Guardar a senha em texto puro para automatizar | Rejeitada: viola o modelo de segredos criptografados do app. |
| Reutilizar diretamente o ADR-0011 da Consolidação Familiar | Rejeitada como decisão automática: o backup restaura um ambiente operacional inteiro, exige retenção e pode precisar de política de senha lembrada; os parâmetros só serão compartilhados após validação de compatibilidade. |

## Consequências

- O backup completo terá proteção adequada para dados financeiros e credenciais locais.
- A execução automática exige aceitar o risco controlado de guardar a senha sob a chave mestra.
- Perder a senha e a chave mestra pode tornar o pacote irrecuperável.
- A distribuição precisará incluir a dependência criptográfica aprovada em macOS, Windows e Linux.
- O formato precisará de versionamento e testes de round-trip entre plataformas.
- A restauração será mais lenta que uma cópia simples, mas poderá validar integridade antes de alterar o ambiente ativo.

## Gates para sair de rascunho

1. Algoritmo e parâmetros aprovados com benchmark nos runtimes distribuídos.
2. Pacote criado e restaurado em macOS, Windows e Linux.
3. Alteração de um byte, senha incorreta e manifesto incompatível rejeitados sem escrita ativa.
4. Senha lembrada armazenada apenas no mecanismo seguro existente.
5. Restauração seguida de `integrity_check` e leitura das configurações criptografadas.
6. Política de retenção validada sem remover o último backup válido.

## Changelog

- `0.1` — 2026-09-05 — Rascunho inicial da decisão de usar ZIP como container e payload criptografado autenticado para backup completo.

## Relacionados

- [[../specs/backup-restauracao]]
- [[0010-segredos-criptografados-sqlite]]
- [[0003-sqlite-fonte-de-verdade]]
- [[../distribuição]]
