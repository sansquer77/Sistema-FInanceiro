---
tipo: adr
area: licenciamento
status: implementado
versao: 1.0
atualizado: 2026-08-04
relacionados:
  - "[[../requisitos]]"
  - "[[../distribuição]]"
  - "[[../specs/landing-page]]"
tags: [adr, "area/licenciamento", "status/implementado"]
aliases: ["ADR-0008", "Licença Apache 2.0", "Licenciamento Open Source"]
---

# ADR-0008 — Licenciamento open source sob Apache License 2.0

> [!info] Status
> **implementado** · tipo: `adr` · atualizado em 2026-08-04 · relacionados: [[../requisitos]], [[../distribuição]], [[../specs/landing-page]]

## Contexto

O Sistema Financeiro deixa de ser tratado como um produto distribuído mediante cobrança manual e passa a ser disponibilizado gratuitamente como projeto pessoal aberto.

A distribuição pública do app, incluindo código-fonte e pacotes gerados por automação, exige uma licença clara para que usuários e eventuais contribuidores saibam quais usos são permitidos.

Sem um arquivo de licença e uma decisão documentada, o repositório permanece sob direitos autorais padrão, o que gera ambiguidade sobre uso, cópia, modificação, redistribuição e contribuição.

## Decisão

Adotar a **Apache License 2.0** como licença open source oficial do repositório do app principal.

A licença deve ser representada por um arquivo `LICENSE` na raiz do repositório, usando o texto padrão da Apache License 2.0.

O README público do repositório deve informar a licença de forma direta, preferencialmente com referência SPDX `Apache-2.0`.

A Landing Page institucional deve comunicar que o Sistema Financeiro é um projeto pessoal disponibilizado gratuitamente, sem suporte formal ou garantia de atendimento, e que o e-mail de contato é destinado a sugestões, dúvidas gerais ou relatos de problemas.

O licenciamento não altera a responsabilidade do usuário por instalação, configuração, backup, segurança do ambiente local, exposição em rede e validação das informações financeiras registradas no app.

## Consequências positivas

- Permite uso, cópia, modificação, distribuição e uso comercial sob termos conhecidos e amplamente aceitos.
- Mantém atribuição/autoria e aviso de copyright.
- Inclui concessão explícita de patente, tornando a licença mais robusta que alternativas permissivas mais simples.
- Facilita contribuições externas e consumo por ferramentas do GitHub, que detectam licenças padrão.
- Alinha o modelo público da Landing Page com downloads abertos por GitHub Releases.

## Consequências negativas / trade-offs

- Terceiros podem redistribuir ou criar versões derivadas, inclusive com uso comercial, desde que respeitem os termos da licença.
- A licença não obriga forks ou derivados distribuídos a manterem o código aberto.
- A abertura do código exige cuidado adicional para garantir que nenhum dado runtime, credencial, chave local, banco SQLite, arquivo `.enc` ou informação pessoal seja versionado.
- A Landing Page e os pacotes públicos devem evitar linguagem de suporte pago, garantia de funcionamento ou compromisso de atendimento.

## Alternativas descartadas

| Alternativa | Motivo da rejeição |
|---|---|
| MIT | Simples e permissiva, mas sem cláusula explícita de patente. |
| BSD-3-Clause | Permissiva e madura, mas menos completa que Apache 2.0 para o objetivo atual. |
| GPLv3 | Copyleft forte poderia reduzir adoção e reuso por exigir que derivados distribuídos permaneçam sob termos compatíveis. |
| AGPLv3 | Forte demais para a proposta, especialmente por impor obrigações adicionais em uso via rede. |
| Manter sem licença | Gera ambiguidade jurídica e impede uso open source claro por terceiros. |

## Critérios de aceite

- Dado o repositório público do app, quando um visitante acessa a raiz do projeto, então encontra um arquivo `LICENSE` com a Apache License 2.0.
- Dado o README público do app, quando um visitante procura a seção de licença, então encontra a indicação `Apache-2.0`.
- Dado a Landing Page pública, quando um visitante lê a seção de download/contato, então entende que o app é disponibilizado gratuitamente como projeto pessoal, sem suporte formal.
- Dado um pacote público gerado por GitHub Releases, quando o usuário consulta a release, então a versão do pacote fica associada ao código-fonte licenciado.

## Fora de escopo

- Prestação de suporte, SLA, consultoria, garantia de correção ou obrigação de atendimento.
- Criação de modelo comercial, cobrança por download ou validação de pagamento.
- Revisão jurídica formal por advogado.
- Licenciamento de dados pessoais, bancos SQLite de usuários, credenciais ou arquivos runtime locais.

## Changelog

- `1.0` — 2026-08-04 — Decisão inicial de licenciar o app principal sob Apache License 2.0 e comunicar distribuição gratuita sem suporte formal.

## Relacionados

- [[../requisitos]]
- [[../distribuição]]
- [[../specs/landing-page]]
