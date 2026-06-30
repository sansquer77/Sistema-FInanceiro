---
tipo: spec
area: seguranca
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[seguranca-autenticacao]]"
  - "[[adr/0005-smtp-criptografado-local]]"
  - "[[arquitetura]]"
tags: [spec, "area/seguranca"]
aliases: ["Recuperação de Senha", "Reset de Senha"]
---

# Recuperação de Senha

> [!info] Status
> **implementado** · área: `seguranca` · atualizado em 2026-06-29 · relacionados: [[seguranca-autenticacao]], [[adr/0005-smtp-criptografado-local]]

## Problema

O usuário precisa redefinir a senha quando esquecer a credencial atual, usando código temporário enviado por e-mail SMTP configurado localmente — sem depender de serviço externo de envio.

## Usuário

Usuário local do Sistema Financeiro que protege dados financeiros sensíveis por senha.

## Jornada

1. Usuário configura o envio de e-mail em Preferências, escolhendo Gmail, Outlook/Microsoft ou configuração manual.
2. Para Gmail ou Outlook/Microsoft, informa apenas e-mail remetente e senha de app; servidor SMTP, porta e STARTTLS são preenchidos automaticamente.
3. Usuário clica em "Esqueci minha senha" na tela de login.
4. Informa o e-mail cadastrado.
5. O sistema gera um código temporário quando o e-mail existe.
6. O código é enviado ao e-mail cadastrado.
7. Usuário informa o código e a nova senha.
8. Sistema invalida o código, troca a senha e encerra sessões ativas.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `email` | texto | E-mail cadastrado do usuário. |
| `code` | hash | Código temporário; armazenado apenas como hash. |
| `nova_senha` | texto | Mínimo 8 caracteres. |
| `expires_at` | timestamp | Código expira em 15 minutos. |

## Regras

- A nova senha deve ter pelo menos 8 caracteres.
- O código expira em 15 minutos.
- Apenas o último código ativo de um usuário permanece válido.
- O código é marcado como usado após a troca da senha.
- Sessões existentes do usuário são encerradas após a redefinição. Ver [[seguranca-autenticacao]].
- A solicitação retorna resposta genérica mesmo quando o e-mail não existe (sem enumeração de usuários).
- Presets suportados: Gmail (`smtp.gmail.com:587`) e Outlook/Microsoft (`smtp.office365.com:587`), ambos com STARTTLS.
- Configuração manual permite servidor SMTP, porta e uso de STARTTLS.
- O pacote distribuível não inclui credenciais SMTP. Ver [[adr/0005-smtp-criptografado-local]].

## Regras de segurança

- O código não é salvo em texto puro — apenas hash.
- A confirmação de redefinição aceita apenas códigos não usados e não expirados.
- A configuração SMTP fica fora do código-fonte em `data/email_config.enc` (criptografada). Ver [[adr/0005-smtp-criptografado-local]].
- `data/email_config.enc` e `data/email_config.key` são arquivos locais de runtime, não versionados.

## API e dados

| Método | Rota |
|---|---|
| `POST` | `/api/password-reset/request` |
| `POST` | `/api/password-reset/confirm` |
| `GET` | `/api/email-config` |
| `POST` | `/api/email-config` |

Tabelas: `password_resets`, `sessions`.

## Critérios de aceite

- Dado a solicitação de código, quando o e-mail existe e SMTP está configurado, o usuário recebe o código por e-mail.
- Dado a solicitação de código, quando o e-mail não existe, a resposta é genérica sem revelar a informação.
- Dado a configuração via preset Gmail/Outlook, quando informado apenas e-mail e senha de app, o preset preenche os demais campos automaticamente.
- Dado um código válido informado, quando usado para redefinição, a nova senha passa a funcionar e a senha anterior deixa de funcionar.
- Dado um código expirado ou já usado, quando informado, a operação é bloqueada.
- Dado a redefinição bem-sucedida, quando executada, as sessões anteriores do usuário são encerradas.

## Fora de escopo

- Exposição do app publicamente.
- Envio de e-mail sem configuração SMTP prévia.

## Changelog

- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Relacionados

- [[seguranca-autenticacao]]
- [[adr/0005-smtp-criptografado-local]]
- [[arquitetura]]
