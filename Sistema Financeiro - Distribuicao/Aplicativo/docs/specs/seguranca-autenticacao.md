# Segurança de autenticação

## Problema

O app ja usa senha com hash forte e sessao opaca, mas tentativas repetidas de login e recuperacao de senha nao tinham bloqueio persistente. Isso deixava o fluxo mais exposto a brute-force online e abuso de email de recuperacao.

## Usuario

Usuarios locais do Sistema Financeiro que protegem dados financeiros sensiveis por senha.

## Jornada

1. Um usuario tenta autenticar com email e senha.
2. O servidor valida a senha e registra falhas por email e origem da conexao.
3. Apos repetidas falhas, novas tentativas recebem bloqueio temporario.
4. Pedidos e confirmacoes de recuperacao de senha tambem respeitam limite persistente.
5. Quando o app roda em HTTPS, o cookie de sessao recebe `Secure`.
6. Requisicoes mutaveis sao aceitas apenas a partir dos hosts/origens locais esperados.

## Dados

- `auth_attempts.action`: tipo de tentativa (`login`, `password-reset-request`, `password-reset-confirm`).
- `auth_attempts.identifier`: chave normalizada por email/token/origem.
- `auth_attempts.attempt_count`: quantidade de tentativas na janela.
- `auth_attempts.locked_until`: fim do bloqueio temporario.
- `auth_attempts.last_attempt_at`: ultima tentativa registrada.

## Regras

- Login bloqueia temporariamente apos 5 falhas.
- Pedido de recuperacao bloqueia temporariamente apos 3 pedidos na janela.
- Confirmacao de token bloqueia temporariamente apos 5 falhas.
- Erros de login continuam sem revelar se o email existe.
- Cookie de sessao usa `HttpOnly` e `SameSite=Lax`.
- Cookie de sessao usa `Secure` somente quando `APP_URL`/URL publica estiver em HTTPS, para nao quebrar o app local em HTTP.
- JWE nao sera adotado nesta entrega porque a sessao ja e opaca e validada no servidor.
- Metodos mutaveis (`POST`, `PUT`, `DELETE`) validam `Host` e, quando enviado, `Origin`.
- Hosts locais permitidos: `sistema-financeiro.localhost` e `127.0.0.1` na porta configurada em `APP_PORT`.
- A origem definida em `APP_URL` tambem e aceita para permitir execucoes locais customizadas.
- Respostas JSON e arquivos estaticos enviam headers defensivos: CSP com `frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin` e `Permissions-Policy` restritiva.

## API e dados

- Nenhum endpoint novo.
- Nova tabela idempotente: `auth_attempts`.
- Rotas afetadas:
  - `POST /api/login`
  - `POST /api/password-reset/request`
  - `POST /api/password-reset/confirm`

## Criterios de aceite

- Dado um usuario existente, quando 5 senhas erradas sao enviadas, entao a proxima tentativa retorna `429 Too Many Requests`.
- Dado um email valido em formato, quando pedidos de recuperacao excedem o limite, entao a proxima tentativa retorna `429 Too Many Requests`.
- Dado `APP_URL` HTTP, o cookie nao contem `Secure`.
- Dado `APP_URL` HTTPS, o cookie contem `Secure`.
- Dado um `Origin` desconhecido em requisicao mutavel, a API retorna `403 Forbidden`.
- Dado um `Host` fora da lista permitida em requisicao mutavel, a API retorna `403 Forbidden`.
- Dado uma resposta JSON ou arquivo estatico, os headers defensivos sao enviados.
- Tentativas de alterar recursos de outro usuario continuam retornando `404` nos dominios cobertos por teste.

## Fora de escopo

- Expor o app publicamente.
- Adicionar JWE.
- Implementar CSRF token.
- Implementar expiracao por inatividade ou rotacao automatica de sessao.
