# Supabase migrations

Este diretório contém migrations PostgreSQL para criar uma base Supabase compatível com o esquema atual do app local.

## Como aplicar

Com a CLI do Supabase configurada no projeto:

```bash
supabase db push
```

Ou execute o arquivo SQL diretamente no SQL Editor do Supabase:

```text
supabase/migrations/20260630000000_initial_schema.sql
```

## Observações

- A migration preserva o modelo atual de autenticação própria do aplicativo na tabela `public.users`; ela ainda não integra com `auth.users`.
- Valores monetários continuam em centavos e taxas/quantidades continuam em micros, como no SQLite.
- Datas de negócio foram convertidas para `date`; campos de auditoria e expiração foram convertidos para `timestamptz`. Campos opcionais que participam de chaves únicas com valor vazio foram mantidos como `text`.
- Campos JSON do app foram definidos como `jsonb` no PostgreSQL.
