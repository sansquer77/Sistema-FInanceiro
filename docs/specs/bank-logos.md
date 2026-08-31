---
tipo: spec
area: frontend
status: implementado
versao: 1.2
atualizado: 2026-08-30
relacionados:
  - "[[frontend-modularizacao]]"
  - "[[contas-correntes]]"
  - "[[cartoes]]"
tags: [spec, "area/frontend", "status/implementado"]
aliases: ["Logos de Bancos e Bandeiras", "Bank Logos"]
---

# Logos de Bancos e Bandeiras

> [!info] Status
> **implementado** · área: `frontend` · atualizado em 2026-08-30 · relacionados: [[frontend-modularizacao]], [[contas-correntes]], [[cartoes]]

## Problema

A lista de contas e cartões usa logos de instituições financeiras e bandeiras espalhados em código e com nomes de arquivo irregulares. Isso dificulta manutenção, repetição de regras de correspondência e reuso visual entre contas e cartões.

## Usuário

Qualquer usuário autenticado que visualize contas correntes ou cartões de crédito e reconheça a instituição financeira e a bandeira pelo logotipo.

## Jornada

1. O usuário cadastra uma conta ou cartão informando o nome do banco/emissor e, no cartão, a bandeira.
2. Ao abrir a listagem, o sistema exibe o logo correspondente quando disponível.
3. Nos cartões, o logo da bandeira é exibido junto ao logo do emissor.
4. Se o logo não estiver disponível ou a imagem falhar, um fallback visual padronizado aparece.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `bank_name` / `issuer` | texto | Nome informado pelo usuário; usado para resolver o logo do banco/emissor. |
| `network` | texto | Bandeira do cartão; usado para resolver o logo da bandeira. |
| `account_type` | enum | Quando `wallet`, exibe ícone de carteira em vez de logo de banco. |
| asset de logo | arquivo | Nome em ASCII minúsculo, ex.: `banco-do-brasil.svg`, `itau.png`, `mercado-pago.svg`, `visa.svg`. |

## Regras

- Os arquivos de logo devem usar nomes em ASCII minúsculos, com hífen como separador.
- O catálogo de logos vive em um módulo compartilhado (`web/modules/bank-logos.js`).
- A normalização do nome informada remove acentos, caixa alta e termos genéricos como "Banco", "Bank" e "S.A.".
- Cada entrada do catálogo mantém aliases explícitos (ex.: `["bb", "banco do brasil"]`).
- O mesmo resolvedor de bancos é usado em contas correntes (`accounts-view.js`) e cartões (`cards-view.js`).
- O resolvedor de bandeiras é usado em cartões (`cards-view.js`).
- Se a imagem do logo falhar ao carregar, o componente exibe fallback visual genérico de banco.
- Contas do tipo `wallet` sempre exibem ícone de carteira, independentemente do nome preenchido.
- Bandeiras sem asset correspondente exibem fallback visual de bandeira (círculo com a inicial ou ícone genérico).

## API e dados

- Nenhuma rota ou tabela nova.
- Assets de bancos em `web/assets/banks/`.
- Assets de bandeiras em `web/assets/bandeiras/`.
- Módulo compartilhado em `web/modules/bank-logos.js`.

## Critérios de aceite

- Dado uma conta com banco "Itaú", quando listada, então exibe o logo correspondente ao Itaú.
- Dado um cartão com emissor "Nubank", quando listado, então exibe o logo correspondente ao Nubank.
- Dado um cartão com bandeira "Visa", quando listado, então exibe o logo da bandeira Visa junto ao logo do emissor.
- Dado uma conta com banco "Banco do Brasil S.A.", quando listada, então a normalização resolve para o logo do Banco do Brasil.
- Dado um arquivo de logo renomeado para nome ASCII minúsculo, quando o resolvedor busca, então encontra o asset correto.
- Dado uma imagem de logo indisponível, quando o elemento `<img>` dispara erro, então exibe fallback visual genérico.
- Dado uma conta do tipo `wallet`, quando listada, então exibe ícone de carteira em vez de logo de banco.
- Dado um cartão com bandeira ausente ou não catalogada, quando listado, então exibe fallback visual de bandeira sem quebrar o layout.

## Pendências

Nenhuma pendência conhecida.

## Changelog

- `1.2` — 2026-08-30 — Adicionados novos logos de bancos: Binance, Foxbit, PayPal e Porto Bank.
- `1.1` — 2026-08-30 — Adicionado catálogo de bandeiras em `web/assets/bandeiras` e exibição do logo da bandeira nos cartões de crédito.
- `1.0` — 2026-08-30 — Implementado catálogo compartilhado em `web/modules/bank-logos.js`, padronização de nomes de assets em `web/assets/banks` e aplicação em Contas e Cartões com fallback visual.
- `0.1` — 2026-08-30 — Criação da spec com catálogo compartilhado, normalização de nomes e fallback visual.

## Relacionados

- [[frontend-modularizacao]]
- [[contas-correntes]]
- [[cartoes]]
