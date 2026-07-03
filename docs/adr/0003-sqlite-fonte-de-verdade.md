---
tipo: adr
area: meta
status: implementado
versao: 1.1
atualizado: 2026-07-03
relacionados:
  - "[[arquitetura]]"
  - "[[adr/0001-stack-local-sem-framework]]"
tags: [adr, meta]
aliases: ["ADR-0003", "SQLite local"]
---

# ADR-0003 — SQLite como fonte de verdade local

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-07-03

## Contexto

O app precisa de persistência confiável, funcionar sem internet, ser fácil de distribuir e não exigir instalação de servidor de banco de dados.

## Decisão

Usar **SQLite** como única fonte de verdade, armazenado em `data/finance.db` e criado automaticamente na inicialização via migrações idempotentes em `financeiro/database.py`.

Valores monetários são persistidos em **centavos** (inteiro) para evitar erros de ponto flutuante.

Para tolerar uso familiar leve com poucos usuários acessando o mesmo servidor local, as conexões usam WAL e `busy_timeout`. Escritas críticas devem ser curtas, serializadas quando dependem de leitura prévia, e evitar chamadas externas enquanto a conexão estiver aberta.

## Consequências positivas

- Zero configuração: o banco é um arquivo local, sem processo separado.
- Distribuível: o arquivo `.db` pode ser copiado como backup.
- Migrações idempotentes preservam bancos existentes ao atualizar o app.
- Compatível com Python via `sqlite3` da biblioteca padrão — sem ORM externo.
- WAL permite leituras concorrentes durante escritas curtas e melhora a ergonomia para uso doméstico compartilhado.

## Consequências negativas / trade-offs

- Concorrência de escrita limitada; mitigada por transações curtas, espera por locks e atualizações atômicas de saldo, mas ainda não equivale a um banco cliente-servidor.
- Sem suporte nativo a tipos monetários com precisão arbitrária — resolvido pelo padrão de centavos.
- Consultas complexas (ex.: portfólio consolidado) requerem SQL manual mais verboso.

## Changelog

- `1.1` — 2026-07-03 — Decisão complementada com WAL, `busy_timeout` e disciplina de transações curtas para uso familiar leve.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| PostgreSQL | Requer servidor separado; incompatível com filosofia local-offline-first. |
| JSON em arquivo | Sem índices, sem transações atômicas, sem integridade referencial. |
| DuckDB | Mais adequado a análises OLAP; maturidade menor para OLTP local na época da decisão. |

## Relacionados

- [[arquitetura]]
- [[adr/0001-stack-local-sem-framework]]
