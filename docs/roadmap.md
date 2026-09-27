---
tipo: roadmap
area: meta
status: implementado
versao: 1.27
atualizado: 2026-09-25
relacionados:
  - "[[visao-produto]]"
  - "[[requisitos]]"
  - "[[arquitetura]]"
tags: [roadmap, meta]
aliases: ["Roadmap", "Replicação Local"]
---

# Roadmap

> [!info] Status
> **implementado** (módulos 1–12 e 16–19 concluídos; módulos 13–15 descartados) · área: `meta` · atualizado em 2026-09-25

Este documento organiza a evolução do Sistema Financeiro e serve de histórico de decisões de sequenciamento. Módulos planejados que ainda não iniciaram ficam com status `planejado`.

## Premissas

- O app local deve funcionar sem internet para operações financeiras básicas.
- A fonte de verdade é o SQLite local. Ver [[adr/0003-sqlite-fonte-de-verdade]].
- Cada módulo ou documento novo precisa nascer a partir de [[templates/spec-template|`docs/templates/spec-template.md`]] antes da implementação. Ver [[sdd]].
- Dados monetários são armazenados em centavos.
- Registros removidos pelo usuário devem ser arquivados sempre que houver valor histórico.
- A interface deve separar cadastros, lançamentos, relatórios e visão geral.

---

## Módulos e status

| # | Módulo | Status | Spec |
|---|---|---|---|
| 1 | Contas manuais, arquivamento e saldo por moeda. Naturezas: liquidez, carteira, investimentos. | ✅ Implementado | [[contas-correntes]] |
| 2 | Categorias e tags: taxonomia financeira e classificação transversal (múltiplas tags). | ✅ Implementado | [[categorias-tags-gestao]] |
| 3 | Lançamentos: despesas, receitas, transferências, recorrência, parcelamento e conciliação bancária. | ✅ Implementado | [[lancamentos]] |
| 4 | Cartões de crédito: cartões manuais, limite, fechamento, vencimento, conta preferencial de pagamento, recorrência/parcelamento, conciliação, movimentação entre faturas, pagamento e faturas mensais. | ✅ Implementado | [[cartoes]] |
| 5 | Limites de gastos: metas por categoria e subcategoria mensais. | ✅ Implementado | [[limites-gastos]] |
| 6 | Investimentos e Portfólio: consolidação de ativos, cotações integradas de mercado, indexadores de renda fixa (SGS/BCB), poupança, previdência privada, resgate, encerramento e ajuste manual de valor. | ✅ Implementado | [[investimentos-portfolio]] |
| 7 | Relatórios avançados e Cockpit integrando contas, cartões, limites, dívidas e portfólio. | ✅ Implementado | [[relatorios]] |
| 8 | Segurança: bloqueio de tentativas, cookie seguro, headers defensivos, validação de origem. | ✅ Implementado | [[seguranca-autenticacao]] |
| 9 | Recuperação de senha com configuração SMTP local criptografada e assistente para Gmail/Outlook. | ✅ Implementado | [[recuperacao-senha]] |
| 10 | Importação de arquivos externos legados e planilhas modelo do sistema (`.xlsx`). | ✅ Implementado | [[importacao-dados]] |
| 11 | Modularização do frontend em ES Modules nativos sem build step. | ✅ Implementado | [[adr/0002-modularizacao-frontend]] |
| 12 | Distribuição desktop macOS/Windows, instaladores, zips limpos e launchers local/LAN. | ✅ Implementado | [[distribuição]] |
| 13 | Conciliação automática de arquivos OFX bancários. | ❌ Descartado — OFX parece padrão, mas na prática bancos exportam com diferenças de encoding, campos ausentes, datas estranhas, sinal de valor inconsistente e descrições muito sujas. | — |
| 14 | Exportação direta de dados em outros formatos. | ❌ Descartado — arquivo SQLite já é acessível por leitor genérico ou agente de IA, sem justificar dependência nova | [[exportacao-dados]] |
| 15 | Imposto de Renda (IR): apuração mensal de DARF por classe de ativo do Portfólio e relatório anual de apoio à declaração IRPF. | ❌ Descartado — custo de manutenção das regras fiscais não compensa para uso familiar | [[imposto-renda]] |
| 16 | Score de Saúde Financeira: indicador síntese (0 a 1000) e diagnóstico de 5 pilares de estabilidade financeira. | ✅ Implementado | [[specs/score-saude-financeira]] |
| 17 | Fundação do frontend v2: ApexCharts vendorizado, IMask, Command Palette nativa e virtualização de listas extensas. | ✅ Implementado | [[specs/frontend-fundacao-v2]] |
| 18 | Objetivos financeiros e fundos de provisão com Reserva de Emergência, exclusividade de recursos e projeções comparativas. | ✅ Implementado | [[specs/objetivos-financeiros]] |
| 19 | Empréstimos e quitação: contratos e pagamentos vinculados; estudos Price/SAC em todas as moedas; evolução atual para TR, IPCA e poupança indexados. | 🚧 Em implementação | [[specs/emprestimos-quitacao]] |
| 20 | Crédito Rotativo: cheque especial e rotativo de cartão com juros compostos sobre saldo aberto, pagamento parcial integrado, prioridade nas estratégias e quitação/troca para Price. | 🚧 Em implantação — monitoramento, integração unidirecional, estratégias, estudo individual e rascunho Price após troca implementados; validação completa pendente | [[specs/emprestimos-quitacao#Proposta de desenho — Crédito Rotativo]] |

---

## Sequência de evolução concluída

1. ✅ Consolidar filtros, busca e edição de lançamentos.
2. ✅ Implementar cartões de crédito e faturas.
3. ✅ Implementar limites de gastos (budgets).
4. ✅ Implementar portfólio de investimentos e precificação automática.
5. ✅ Implementar conciliação e recorrência.
6. ✅ Implementar relatórios sintéticos/analíticos interativos no frontend web.
7. ✅ Modularizar o frontend em ES Modules nativos.
8. ✅ Enrijecer autenticação (bloqueio de tentativas, headers defensivos).
9. ✅ Organizar distribuição desktop por plataforma, com modo local padrão e modo rede/LAN explícito.

## Próximas prioridades sugeridas

Nenhuma prioridade adicional foi confirmada. Defina a próxima iniciativa na próxima revisão de produto.

Antes de iniciar qualquer item acima, criar spec em `specs/` seguindo [[sdd]] e atualizar esta tabela.

---

## Modelo de dados conceitual

```text
users
sessions
password_resets
auth_attempts
checking_accounts
categories
subcategories
tags
transactions
transaction_tags
credit_cards
credit_card_transactions
credit_card_payments
credit_card_transaction_tags
spending_limits
investment_opening_positions
investment_operations
investment_redemptions
investment_closed_positions
investment_value_overrides
quote_cache
```

Ver mapeamento completo de tabelas em [[arquitetura]].

---

## Critério de fidelidade

A implementação local não copia a interface de nenhum produto externo. Reproduz capacidades:

- Cadastrar estruturas financeiras.
- Registrar e consultar movimentações.
- Classificar por categoria, subcategoria e tags.
- Acompanhar saldo realizado.
- Acompanhar faturas e limites de cartão.
- Acompanhar portfólio de investimentos de renda variável, renda fixa e criptoativos com valorização real.
- Acompanhar poupança, previdência privada e ativos multimoeda na moeda da carteira.
- Acompanhar limites de gastos.
- Gerar relatórios por período, categoria, subcategoria, conta, tag e fluxo diário.
- Usar Cockpit para visualizar saldos, planejamento recorrente, dívidas, maiores receitas/despesas e portfólio por tipo.
- Distribuir o app por pacotes macOS e Windows sem banco, logs, chaves, credenciais SMTP, testes ou docs técnicas; cada instalação configura sua própria recuperação por e-mail.
- Oferecer launchers de rede local apenas para redes confiáveis, mantendo reverse-proxy HTTPS como caminho para acesso remoto.

## Changelog

- `1.27` — 2026-09-25 — Adiciona atalho editável para iniciar cadastro Price após troca do rotativo; validação completa da V1 ainda pendente.
- `1.26` — 2026-09-25 — Registra conclusão da etapa de estudo individual no Efeito Borboleta; validação completa da V1 ainda pendente.
- `1.25` — 2026-09-25 — Estudo individual de rotativo implementado no Efeito Borboleta; validação completa da V1 ainda pendente.
- `1.24` — 2026-09-25 — Inicia implementação do Crédito Rotativo; monitoramento, integração unidirecional e prioridade estratégica avançam, enquanto o estudo individual segue pendente.
- `1.23` — 2026-09-25 — Crédito Rotativo pronto para implantação após fechar critérios, plano e regra de mão única sem geração de lançamentos.
- `1.22` — 2026-09-25 — Fecha convenções de taxa e calendário do Crédito Rotativo; detalhamento de critérios, plano e experiência permanece pendente.
- `1.21` — 2026-09-25 — Define prioridade rotativa em avalanche/bola de neve e fluxo de quitação definitiva ou troca com alerta para contrato Price.
- `1.20` — 2026-09-25 — Confirma residual da fatura parcial como saldo inicial do card rotativo, com alerta para complementar dados contratuais.
- `1.19` — 2026-09-25 — Iniciado o desenho do Crédito Rotativo em Empréstimos, com acompanhamento de saldo, juros compostos, pagamentos e conversão para Price.
- `1.18` — 2026-09-25 — Indexação de contratos entra em implementação; Crédito Rotativo é separado como próxima evolução do módulo.
- `1.17` — 2026-09-25 — Empréstimos passa a aceitar SAC prefixado além de Price, incluindo explicações e cálculos determinísticos.
- `1.16` — 2026-09-25 — Ajusta a apresentação da V1.1 para sinalizar quando os campos de estimativa não chegam do backend.
- `1.15` — 2026-09-25 — V1.1 de Empréstimos apresenta no card compromisso nominal, principal estimado e custo financeiro futuro Price.
- `1.14` — 2026-09-25 — Melhorias dos cards do Consultor concluídas; próxima prioridade fica para decisão em revisão de produto.
- `1.13` — 2026-09-25 — Efeito Borboleta concluído após validação Safari; próxima prioridade sugerida: enriquecer análises do Consultor com metas e obrigações financeiras.
- `1.12` — 2026-09-25 — Módulo 19 Empréstimos e quitação aprovado como implementado; próxima prioridade corrigida para a validação visual ainda pendente do Efeito Borboleta.
- `1.11` — 2026-09-24 — Reorganiza Empréstimos: cadastro/acompanhamento no módulo próprio e estudos na aba de Empréstimos do Efeito Borboleta.
- `1.10` — 2026-09-24 — Inicia o módulo 19 Empréstimos e quitação após fechamento das decisões da V1.

- `1.9` — 2026-09-23 — Adicionado e implementado o módulo 18, Objetivos Financeiros e Fundos de Provisão, sobre a fundação gráfica da V2; módulo 17 sincronizado como implementado.
- `1.8` — 2026-08-30 — Adicionado módulo 17, Fundação do frontend v2, em estado planejado; módulo 16 sincronizado como implementado.
- `1.7` — 2026-07-27 — Adicionado módulo 16 (Score de Saúde Financeira) em status "Em implementação", com spec [[specs/score-saude-financeira]].
- `1.6` — 2026-07-27 — Módulo 13 (Importação OFX) marcado como descartado antes da criação da spec: o arquivo OFX traz mais complexidade e riscos — um match errado é pior do que não conciliar, porque dá uma falsa sensação de precisão — do que ganhos. Sem spec criada.
- `1.5` — 2026-07-27 — Módulo 14 (Exportação de dados) marcado como descartado desde a criação da spec: o arquivo SQLite já é acessível por leitor genérico ou agente de IA, sem justificar dependência nova (`xlsxwriter`); removido das próximas prioridades sugeridas. Spec [[exportacao-dados]] mantida como registro do design cogitado.
- `1.4` — 2026-07-27 — Módulo 15 (Imposto de Renda) marcado como descartado: complexidade de manter regras fiscais atualizadas não compensa o ganho para um sistema de uso familiar; spec [[imposto-renda]] mantida como registro histórico.
- `1.3` — 2026-07-27 — Adicionado módulo 15 (Imposto de Renda) em status "Em especificação", com spec [[imposto-renda]].
- `1.2` — 2026-07-04 — Roadmap inclui distribuição desktop macOS/Windows e regra de criação de documentos a partir do template.
- `1.1` — 2026-06-29 — Consolidação de `replicacao-local.md` neste arquivo; adição de frontmatter, status por módulo e próximas prioridades.
- `1.0` — versão original.

## Relacionados

- [[visao-produto]]
- [[requisitos]]
- [[arquitetura]]
- [[sdd]]
