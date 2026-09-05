---
tipo: spec
area: seguranca
status: implementado
versao: 1.6
atualizado: 2026-09-01
relacionados:
  - "[[recuperacao-senha]]"
  - "[[adr/0005-smtp-criptografado-local]]"
  - "[[arquitetura]]"
tags: [spec, "area/seguranca"]
aliases: ["Segurança", "Autenticação"]
---

# Segurança de Autenticação

> [!info] Status
> **implementado** · área: `seguranca` · atualizado em 2026-09-01 · relacionados: [[recuperacao-senha]], [[arquitetura]]

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
6. Requisições mutáveis são aceitas apenas a partir dos hosts e origens locais esperados.
7. Ao trocar ou recuperar a senha, todas as sessões do usuário são revogadas e ele precisa entrar novamente.
8. A sessão expira definitivamente 30 dias após sua criação.
9. O cadastro público reserva uma tentativa persistente por origem antes do trabalho de criação do usuário.

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
- Cadastro público permite no máximo **5 tentativas por origem em 60 minutos**; tentativas inválidas também consomem o orçamento, e outra origem mantém seu próprio orçamento.
- Pedido de recuperação bloqueia temporariamente após **3 pedidos** na janela.
- Confirmação de token bloqueia temporariamente após **5 falhas**.
- Erros de login não revelam se o e-mail existe.
- Cookie de sessão usa `HttpOnly` e `SameSite=Lax`.
- Cookie de sessão usa `Secure` somente quando `APP_URL` estiver em HTTPS.
- O banco armazena somente o hash SHA-256 do token de sessão; o token original existe apenas no cookie.
- Métodos mutáveis (`POST`, `PUT`, `DELETE`) exigem e validam `Host` e `Origin`.
- Rotas `GET` de coleção e perfil são reconhecidas pelo caminho exato; sufixos ou colisões de prefixo não podem acionar outro handler da API.
- A troca e a recuperação de senha revogam todas as sessões do usuário.
- Sessões têm expiração absoluta de **30 dias**, sem renovação automática por atividade.
- HTTP continua permitido quando o servidor escuta apenas localmente.
- Exposição em LAN usando HTTP não bloqueia a inicialização, mas emite um alerta explícito no terminal.
- Hosts locais permitidos: `sistema-financeiro.localhost` e `127.0.0.1` na porta configurada em `APP_PORT`.
- A origem definida em `APP_URL` também é aceita.
- Hosts adicionais podem ser definidos em `APP_ALLOWED_HOSTS` como CSV; valores sem porta também aceitam `APP_PORT`.
- Origens adicionais podem ser definidas em `APP_ALLOWED_ORIGINS` como CSV; valores sem esquema assumem `http://` e valores sem porta assumem `APP_PORT`.
- Respostas JSON e arquivos estáticos enviam headers defensivos:
  - `Content-Security-Policy` restritivo, permitindo scripts e imagens apenas de origens controladas; exceção explícita para o widget voluntário de contribuição no `Buy Me a Coffee` (`https://cdnjs.buymeacoffee.com` e `https://cdn.buymeacoffee.com`).
  - `X-Content-Type-Options: nosniff`
  - `Referrer-Policy: same-origin`
  - `Permissions-Policy` restritiva.

## API e dados

Nenhum endpoint novo. A tabela `sessions` armazena `token_hash` em vez do token original; instalações existentes são migradas de forma idempotente.

Rotas afetadas:

| Método | Rota |
|---|---|
| `POST` | `/api/login` |
| `POST` | `/api/register` |
| `POST` | `/api/password-reset/request` |
| `POST` | `/api/password-reset/confirm` |

## Critérios de aceite

- Dado 5 senhas erradas para um usuário existente, quando a próxima tentativa é feita, retorna `429 Too Many Requests`.
- Dadas 5 tentativas de cadastro da mesma origem, válidas ou inválidas, quando uma nova tentativa é feita dentro da janela, retorna `429 Too Many Requests` antes de criar usuário.
- Dada uma origem diferente ainda dentro de seu orçamento, quando realiza um cadastro válido, o usuário é criado normalmente.
- Dado pedidos de recuperação excedendo o limite, quando o próximo pedido chega, retorna `429 Too Many Requests`.
- Dado `APP_URL` HTTP, quando o cookie é gerado, não contém `Secure`.
- Dado `APP_URL` HTTPS, quando o cookie é gerado, contém `Secure`.
- Dado um `Origin` desconhecido em requisição mutável, quando recebido, a API retorna `403 Forbidden`.
- Dada uma requisição mutável sem `Origin`, quando recebida, a API retorna `403 Forbidden`.
- Dado um `Host` fora da lista permitida em requisição mutável, quando recebido, a API retorna `403 Forbidden`.
- Dado um host/origem de LAN configurado por `APP_ALLOWED_HOSTS`/`APP_ALLOWED_ORIGINS`, quando uma mutação vem dessa origem, a validação aceita a requisição.
- Dado qualquer resposta JSON ou arquivo estático, quando entregue, os headers defensivos estão presentes.
- Dado tentativas de alterar recursos de outro usuário, quando feitas, retornam `404`.
- Dado um token de sessão emitido, quando o banco é consultado, somente seu hash está armazenado.
- Dada uma troca ou recuperação de senha, quando qualquer sessão anterior é reutilizada, ela não autentica.
- Dada uma sessão com mais de 30 dias, quando reutilizada, ela não autentica.
- Dado `APP_HOST` local com HTTP, quando o app inicia, ele funciona sem alerta de exposição em rede.
- Dado `APP_HOST` exposto à LAN e `APP_URL` HTTP, quando o app inicia, ele exibe alerta recomendando HTTPS.
- Dado um caminho `GET` que apenas começa como uma rota válida, quando ele não corresponde ao contrato completo, então o handler da rota válida não é executado.

## Fora de escopo

- Exposição do app publicamente.
- Adição de JWE.
- Implementação de CSRF token dedicado (a proteção adotada é validação obrigatória de origem).
- Expiração por inatividade ou rotação automática de sessão.

## Changelog

- `1.6` — 2026-09-01 — Cadastro público passa a reservar orçamento persistente por origem, limitando cinco tentativas em 60 minutos antes da criação do usuário; abusos inválidos também consomem a janela.
- `1.5` — 2026-08-30 — CSP ajustado para permitir o widget voluntário de contribuição do Buy Me a Coffee (`cdnjs.buymeacoffee.com` para scripts e `cdn.buymeacoffee.com` para imagens).
- `1.4` — 2026-08-28 — O despacho de rotas `GET` de perfil, contas, cartões e lançamentos passa a exigir caminho exato, impedindo colisões por prefixo; adicionada cobertura automatizada positiva e negativa.
- `1.3` — 2026-07-10 — Adicionada expiração absoluta de 30 dias e alerta não bloqueante para exposição em LAN sem HTTPS; HTTP local permanece permitido.
- `1.2` — 2026-07-10 — Tokens de sessão passam a ser armazenados com hash, `Origin` torna-se obrigatório em mutações e troca/recuperação de senha revoga todas as sessões.
- `1.1` — 2026-07-04 — Validação de Host/Origin atualizada para documentar listas CSV de LAN e normalização de porta/esquema.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[recuperacao-senha]]
- [[adr/0005-smtp-criptografado-local]]
- [[arquitetura]]
