---
tipo: adr
area: seguranca
status: implementado
versao: 1.1
atualizado: 2026-07-05
relacionados:
  - "[[specs/recuperacao-senha]]"
  - "[[specs/seguranca-autenticacao]]"
  - "[[arquitetura]]"
tags: [adr, seguranca]
aliases: ["ADR-0005", "SMTP criptografado local"]
---

# ADR-0005 — Configuração SMTP criptografada no ambiente local

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-07-05

## Contexto

A funcionalidade de recuperação de senha requer envio de e-mail via SMTP. As credenciais (senha de app do Gmail ou Outlook, por exemplo) não podem ser armazenadas em texto puro nem versionadas junto com o código-fonte.

## Decisão

- As credenciais SMTP são armazenadas **criptografadas por usuário** em `data/email_config_user_{id}.enc`.
- A chave de criptografia fica em `data/email_config.key` ou na variável de ambiente `SISTEMA_FINANCEIRO_CONFIG_KEY`.
- O módulo `financeiro/secure_config.py` encapsula toda a lógica de leitura e escrita criptografada.
- O pacote distribuível **nunca inclui** `data/email_config_user_{id}.enc`, `data/email_config.key` ou qualquer credencial SMTP.
- Cada usuário configura seu próprio remetente pela interface de Preferências.

## Consequências positivas

- Um atacante com acesso ao arquivo `.enc` não obtém as credenciais sem a chave.
- A senha de app não aparece em logs, variáveis de ambiente de processo ou no banco SQLite.
- O assistente de configuração (Gmail/Outlook) reduz a chance de configuração incorreta pelo usuário.
- Usuários autenticados não veem nem sobrescrevem a configuração SMTP de outros usuários.

## Consequências negativas / trade-offs

- Se o usuário perder `data/email_config.key` e não tiver backup, precisará reconfigurar o e-mail.
- A recuperação de senha só funciona se o usuário tiver configurado o SMTP previamente — caso contrário, a feature simplesmente não está disponível (comportamento documentado).

## Changelog

- `1.1` — 2026-07-05 — Configuração SMTP deixou de ser global e passou a ser criptografada por usuário.
- `1.0` — 2026-06-29 — Decisão inicial de armazenar SMTP criptografado localmente.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| Credenciais em texto puro no banco SQLite | Banco pode ser copiado/versionado inadvertidamente, expondo credenciais. |
| Variável de ambiente com a senha | Exige configuração de shell; não amigável para usuário não técnico. |
| Serviço de e-mail externo (SendGrid, etc.) | Dependência externa obrigatória; viola o princípio offline-first para operação básica. |

## Relacionados

- [[specs/recuperacao-senha]]
- [[specs/seguranca-autenticacao]]
- [[arquitetura]]
