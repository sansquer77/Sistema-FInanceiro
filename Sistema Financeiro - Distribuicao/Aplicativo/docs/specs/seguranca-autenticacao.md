---
tipo: spec
area: seguranca
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[recuperacao-senha]]"
  - "[[adr/0005-smtp-criptografado-local]]"
  - "[[arquitetura]]"
tags: [spec, "area/seguranca"]
aliases: ["Segurança", "Autenticação"]
---

# Segurança de Autenticação

> [!info] Status
> **implementado** · área: `seguranca` · atualizado em 2026-06-29 · relacionados: [[recuperacao-senha]], [[arquitetura]]

## Problema

O app já usa senha com hash forte e sessão opaca, mas tentativas repetidas de login e recuperação de senha não tinham bloqueio persistente, deixando o fluxo exposto a brute-force online e abuso de e-mail de recuperação.

## Usuário

Usuários locais do Sistema Financeiro que protegem dados financeiros sensíveis por senha.

## Jornada

1. Usuário tenta autenticar com e-mail e senha.
2. O servidor valida a senha e registra falhas por e-mail e origem da conexão.
3. Após repetidas falhas, novas tentativas recebem bloqueio temporário.
4. Pedidos e confirmações de recuperação de senha também respeitam limite persistente.
5. Quando o app roda em HTTPS, o cookie de sessão recebe `Secure`.
6. Requisições mutáveis são aceitas apenas a partir dos hosts/origens locais esperados.

## Dados

| Campo | Tipo | Descrição |
|---|---|---|
| `auth_attempts.action` | enum | Tipo de tentativa: `login`, `password-reset-request`, `password-reset-confirm`. |
| `auth_attempts.identifier` | texto | Chave normalizada por e-mail/token/origem. |
| `auth_attempts.attempt_count` | inteiro | Quantidade de tentativas na janela. |
| `auth_attempts.locked_until` | timestamp | Fim do bloqueio temporário. |
| `auth_attempts.last_attempt_at` | timestamp | Última tentativa registrada. |

## Regras

- Login bloqueia temporariamente após **5 falhas**.
- Pedido de recuperação bloqueia temporariamente após **3 pedidos** na janela.
- Confirmação de token bloqueia temporariamente após **5 falhas**.
- Erros de login não revelam se o e-mail existe.
- Cookie de sessão usa `HttpOnly` e `SameSite=Lax`.
- Cookie de sessão usa `Secure` somente quando `APP_URL` estiver em HTTPS.
- Métodos mutáveis (`POST`, `PUT`, `DELETE`) validam `Host` e, quando enviado, `Origin`.
- Hosts locais permitidos: `sistema-financeiro.localhost` e `127.0.0.1` na porta configurada em `APP_PORT`.
- A origem definida em `APP_URL` também é aceita.
- Respostas JSON e arquivos estáticos enviam headers defensivos:
  - `Content-Security-Policy: frame-ancestors 'none'`
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: same-origin`
  - `Permissions-Policy` restritiva.

## API e dados

Nenhum endpoint novo. Tabela nova (idempotente): `auth_attempts`.

Rotas afetadas:

| Método | Rota |
|---|---|
| `POST` | `/api/login` |
| `POST` | `/api/password-reset/request` |
| `POST` | `/api/password-reset/confirm` |

## Critérios de aceite

- Dado 5 senhas erradas para um usuário existente, quando a próxima tentativa é feita, retorna `429 Too Many Requests`.
- Dado pedidos de recuperação excedendo o limite, quando o próximo pedido chega, retorna `429 Too Many Requests`.
- Dado `APP_URL` HTTP, quando o cookie é gerado, não contém `Secure`.
- Dado `APP_URL` HTTPS, quando o cookie é gerado, contém `Secure`.
- Dado um `Origin` desconhecido em requisição mutável, quando recebido, a API retorna `403 Forbidden`.
- Dado um `Host` fora da lista permitida em requisição mutável, quando recebido, a API retorna `403 Forbidden`.
- Dado qualquer resposta JSON ou arquivo estático, quando entregue, os headers defensivos estão presentes.
- Dado tentativas de alterar recursos de outro usuário, quando feitas, retornam `404`.

## Fora de escopo

- Exposição do app publicamente.
- Adição de JWE.
- Implementação de CSRF token.
- Expiração por inatividade ou rotação automática de sessão.

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[recuperacao-senha]]
- [[adr/0005-smtp-criptografado-local]]
- [[arquitetura]]
