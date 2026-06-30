---
tipo: adr
area: seguranca
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[specs/recuperacao-senha]]"
  - "[[specs/seguranca-autenticacao]]"
  - "[[arquitetura]]"
tags: [adr, seguranca]
aliases: ["ADR-0005", "SMTP criptografado local"]
---

# ADR-0005 — Configuração SMTP criptografada no ambiente local

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-06-29

## Contexto

A funcionalidade de recuperação de senha requer envio de e-mail via SMTP. As credenciais (senha de app do Gmail ou Outlook, por exemplo) não podem ser armazenadas em texto puro nem versionadas junto com o código-fonte.

## Decisão

- As credenciais SMTP são armazenadas **criptografadas** em `data/email_config.enc`.
- A chave de criptografia fica em `data/email_config.key` ou na variável de ambiente `SISTEMA_FINANCEIRO_CONFIG_KEY`.
- O módulo `financeiro/secure_config.py` encapsula toda a lógica de leitura e escrita criptografada.
- O pacote distribuível **nunca inclui** `data/email_config.enc`, `data/email_config.key` ou qualquer credencial SMTP.
- Cada instalação configura seu próprio remetente pela interface de Preferências.

## Consequências positivas

- Um atacante com acesso ao arquivo `.enc` não obtém as credenciais sem a chave.
- A senha de app não aparece em logs, variáveis de ambiente de processo ou no banco SQLite.
- O assistente de configuração (Gmail/Outlook) reduz a chance de configuração incorreta pelo usuário.

## Consequências negativas / trade-offs

- Se o usuário perder `data/email_config.key` e não tiver backup, precisará reconfigurar o e-mail.
- A recuperação de senha só funciona se o usuário tiver configurado o SMTP previamente — caso contrário, a feature simplesmente não está disponível (comportamento documentado).

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
