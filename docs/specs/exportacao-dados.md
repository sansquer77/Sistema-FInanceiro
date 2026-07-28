---
tipo: spec
area: exportacao-dados
status: depreciado
versao: 0.1
atualizado: 2026-07-27
relacionados:
  - "[[lancamentos]]"
  - "[[cartoes]]"
  - "[[relatorios]]"
  - "[[arquitetura]]"
tags: [spec, "area/exportacao-dados", "status/depreciado"]
aliases: ["Exportação de Dados", "Exportação Excel", "Exportação XLSX"]
---

# Exportação Direta de Dados em Outros Formatos

> [!info] Status
> **depreciado** · área: `exportacao-dados` · atualizado em 2026-07-27 (v0.1) · relacionados: [[lancamentos]], [[cartoes]], [[relatorios]]

> [!warning] Decisão de não implementar
> O Sistema Financeiro já guarda tudo em um único arquivo SQLite local (`data/finance.db`, ver ADR-0003). Esse formato já é diretamente legível por um leitor SQLite básico (DB Browser for SQLite, `sqlite3` via terminal, etc.) ou por um agente de IA a quem o arquivo seja enviado — ambos conseguem gerar a mesma planilha de análise sem que o app precise embutir lógica de exportação. Implementar isso dentro do app exigiria adicionar `xlsxwriter` como dependência externa — a primeira do tipo para geração de relatório neste projeto (que hoje evita dependências externas por princípio: ADR-0001, ADR-0002, ADR-0004) — o que só se justificaria com um ADR próprio comparando essa opção com o custo de simplesmente reaproveitar o arquivo SQLite existente. O ganho não foi considerado proporcional ao custo de manutenção da dependência e da lógica de exportação para um sistema de uso familiar. Módulo descartado antes de qualquer implementação; este documento registra o design que foi cogitado, caso seja revisitado.

## Problema

O usuário às vezes precisa levar seus lançamentos de contas e cartões para fora do app — para backup, auditoria ou análise em ferramentas externas (Excel, Google Sheets, tabela dinâmica) — sem depender de acesso direto e manual ao arquivo SQLite.

## Usuário

Qualquer usuário autenticado localmente que queira uma cópia organizada dos próprios lançamentos fora do app.

## Alternativa adotada em vez desta spec

Em vez de um exportador embutido, a orientação é usar o próprio arquivo `data/finance.db`:
- Abrir com um leitor SQLite (ex.: DB Browser for SQLite) para consulta e exportação ad hoc em CSV/Excel.
- Enviar o arquivo (ou uma cópia, se o usuário preferir não expor dados de outros usuários — ver [[seguranca-autenticacao]]) para um agente de IA capaz de ler SQLite e gerar a planilha sob demanda, com a estrutura que o usuário quiser a cada vez, sem exigir uma tela fixa no app.

## Design cogitado (não implementado)

### Jornada proposta

1. O usuário abriria **Usuário/Preferências → Exportação de dados**, um novo item ao lado de Perfil, Segurança, E-mail e Sobre.
2. Escolheria o escopo: todos os lançamentos ou um período específico (De/Até).
3. Escolheria a origem: contas (todas ou uma específica) e/ou cartões de crédito (todos ou um específico).
4. Escolheria o conteúdo: lançamentos de contas, lançamentos de cartões, pagamentos de fatura, tags, dados de conciliação.
5. Geraria um `.xlsx` para download com abas separadas por tipo de dado.

### Layout de tela proposto

```text
Usuário
├─ Perfil
├─ Segurança
├─ E-mail
├─ Exportação de dados
└─ Sobre

Exportação de dados
Gere uma planilha Excel com seus lançamentos para backup, auditoria ou análise externa.

[ Escopo ]
( ) Todos os lançamentos
( ) Período específico
    De: [__/__/____]   Até: [__/__/____]

[ Origem ]
[x] Contas
    Conta: [Todas as contas ▼]
[x] Cartões de crédito
    Cartão: [Todos os cartões ▼]

[ Conteúdo ]
[x] Lançamentos de contas
[x] Lançamentos de cartões
[x] Pagamentos de fatura
[x] Tags
[x] Dados de conciliação

[ Gerar Excel ]
```

### Regras cogitadas

- Valores monetários exportados como números reais utilizáveis em fórmulas do Excel, nunca como texto formatado (`R$ 1.234,56`); moeda sempre em coluna separada — decorrência direta de dinheiro ser armazenado em centavos (ver AGENTS.md, seção 3).
- Datas exportadas no formato de data nativo do Excel, não texto.
- Pagamentos de fatura nunca se misturam com despesas analíticas de cartão — mesma regra já estabelecida em [[relatorios]] (`invoice_month` para competência; pagamento de fatura excluído das análises de despesa). Por isso teriam aba própria.
- Sem fórmulas complexas na primeira versão — apenas dados tabulares prontos para tabela dinâmica externa.
- Exportação sempre restrita aos dados do usuário autenticado.

### Estrutura de planilha cogitada

**Aba Resumo** (metadados da exportação):

| Campo | Valor |
|---|---|
| Sistema | Sistema Financeiro |
| Usuário | e-mail do usuário |
| Gerado em | data/hora |
| Período | Todos ou intervalo |
| Contas | Todas ou lista |
| Cartões | Todos ou lista |
| Total de lançamentos | número |
| Total por moeda | BRL, USD etc. |

**Aba Lançamentos de Contas:**

| Coluna | Observação |
|---|---|
| ID | rastreabilidade |
| Data | ISO e/ou formatada |
| Tipo | Receita, despesa, transferência, investimento |
| Descrição | texto original |
| Conta | nome da conta |
| Moeda | BRL, USD etc. |
| Valor | número reaproveitável no Excel |
| Categoria | categoria |
| Subcategoria | subcategoria |
| Categoria/Subcategoria | caminho pronto para análise |
| Tags | separadas por vírgula |
| Conciliado | Sim/Não |
| Data de conciliação | se houver |
| É pagamento de fatura | Sim/Não |
| Observações | se existir |

**Aba Lançamentos de Cartões:**

| Coluna | Observação |
|---|---|
| ID | rastreabilidade |
| Data da compra | data real |
| Competência/Fatura | `invoice_month` |
| Cartão | nome do cartão |
| Moeda | moeda do cartão |
| Tipo | despesa/estorno/receita se aplicável |
| Descrição | texto original |
| Valor | número |
| Categoria | categoria |
| Subcategoria | subcategoria |
| Categoria/Subcategoria | caminho pronto |
| Tags | separadas por vírgula |
| Parcela | ex.: 2/10, se houver |
| Série/parcelamento | identificador ou descrição |
| Conciliado | Sim/Não |
| Data de conciliação | se houver |

**Aba Pagamentos de Fatura** (separada para não confundir com despesa analítica):

| Coluna | Observação |
|---|---|
| Data | data do pagamento |
| Conta de pagamento | conta de origem |
| Cartão | cartão pago |
| Fatura | mês da fatura |
| Valor | número |
| Moeda | moeda |
| Lançamento vinculado | ID do lançamento de conta |
| Observação | status/contexto |

**Aba Dicionário** (explicação de campos não autoexplicativos):

| Campo | Significado |
|---|---|
| Data da compra | data original do lançamento no cartão |
| Competência/Fatura | mês em que o cartão impacta análise |
| É pagamento de fatura | lançamento financeiro que reduz saldo, mas não entra como despesa analítica |
| Conciliado | lançamento conferido pelo usuário |
| Categoria/Subcategoria | agrupamento pronto para tabela dinâmica |

### MVP que teria sido recomendado

- Exportar somente `.xlsx`.
- Filtros: período, contas, cartões.
- Abas: Resumo, Lançamentos de Contas, Lançamentos de Cartões, Pagamentos de Fatura, Dicionário.
- Valores como números reais no Excel, moeda em coluna separada, datas em formato de data do Excel.
- Sem fórmulas complexas na primeira versão.

## Dados (hipotéticos, não implementados)

- `escopo`: `todos` ou `periodo` (com `data_inicio`/`data_fim`).
- `origem_contas` / `origem_cartoes`: lista de IDs ou `todas`/`todos`.
- `conteudo`: subconjunto de `lancamentos_contas`, `lancamentos_cartoes`, `pagamentos_fatura`, `tags`, `conciliacao`.

## API e dados (hipotéticos, não implementados)

| Método | Rota |
|---|---|
| `GET` | `/api/export/xlsx?scope=...&accounts=...&cards=...` |

Tabelas que seriam lidas (somente leitura): `transactions`, `credit_card_transactions`, `credit_card_payments`, `categories`, `subcategories`, `tags`, `transaction_tags`, `credit_card_transaction_tags`, `checking_accounts`, `credit_cards`.

## Critérios de aceite (hipotéticos, nunca implementados nem testados)

- Dado o usuário sem selecionar período, quando gera a exportação, o Excel inclui todos os lançamentos de contas e cartões do usuário autenticado.
- Dado um período específico selecionado (De/Até), quando gera a exportação, apenas lançamentos dentro do intervalo aparecem nas abas de detalhe.
- Dado contas e/ou cartões específicos selecionados, quando gera a exportação, apenas lançamentos das origens escolhidas aparecem.
- Dado um pagamento de fatura registrado em conta-corrente, quando exportado, ele aparece apenas na aba Pagamentos de Fatura, nunca na aba de Lançamentos de Contas como despesa analítica.
- Dado um lançamento de cartão parcelado, quando exportado, a aba de Lançamentos de Cartões mostra o índice de parcela (ex.: `2/10`).
- Dado valores monetários exportados, quando abertos no Excel, aparecem como números reais (não texto formatado), com a moeda em coluna separada.
- Dado datas exportadas, quando abertas no Excel, usam o formato de data nativo da planilha, não texto.
- Dado a aba Resumo, quando exibida, mostra metadados de usuário, data/hora de geração, escopo e totais por moeda.
- Dado a aba Dicionário, quando exibida, explica os campos que não são autoexplicativos.
- Dado dois usuários distintos, quando cada um gera sua exportação, cada um recebe apenas dados das próprias contas/cartões.
- Dado nenhum lançamento no escopo selecionado, quando o Excel é gerado, as abas de detalhe ficam vazias com cabeçalho, sem erro.

## Pendências

> [!question] Pendências
> Como a spec nasce em `depreciado`, nenhum item abaixo bloqueia implementação — ficam registrados apenas para o caso de a decisão ser revisitada.

- [ ] Se revisitado, decidir entre `xlsxwriter` (dependência nova, exige ADR) e alternativas sem dependência (ex.: gerar `.csv` puro com a biblioteca padrão, ou um `.xlsx` mínimo escrito manualmente como XML/zip) antes de comprometer a stack.
- [ ] Reavaliar se o ganho de uma tela dedicada ainda não compensa frente a leitores SQLite genéricos ou agentes de IA, caso o volume de lançamentos ou o número de usuários do app cresça.

## Fora de escopo

- Qualquer exportação embutida no app nesta versão — ver "Alternativa adotada" acima.
- Formatos além de `.xlsx` (o design cogitado já limitava o MVP a um único formato).
- Fórmulas ou dashboards dentro da planilha exportada.

## Plano de implementação (hipotético, nunca executado)

- [ ] Passo 1 — Registrar ADR comparando `xlsxwriter` (dependência nova) com alternativas sem dependência, resolvendo a pendência correspondente antes de codificar.
- [ ] Passo 2 — Implementar `financeiro/export.py` com as consultas somente leitura por escopo/origem/conteúdo.
- [ ] Passo 3 — Expor `GET /api/export/xlsx` com os filtros de escopo, contas e cartões.
- [ ] Passo 4 — Criar aba "Exportação de dados" em `web/modules/` dentro do menu Usuário/Preferências, seguindo a fábrica `createXxxView`.
- [ ] Passo 5 — Gerar as abas Resumo, Lançamentos de Contas, Lançamentos de Cartões, Pagamentos de Fatura e Dicionário conforme estrutura cogitada.
- [ ] Passo 6 — Cobrir cada critério de aceite com teste automatizado em `tests/`.

## Changelog

- `0.1` — 2026-07-27 — Spec criada diretamente em status `depreciado`: módulo de exportação embutida descartado porque o arquivo SQLite já é acessível por leitores genéricos ou por um agente de IA, sem justificar a dependência nova (`xlsxwriter`) que exigiria ADR. Design de referência (tela, abas do Excel, colunas, MVP) documentado para consulta futura.

## Relacionados

- [[lancamentos]]
- [[cartoes]]
- [[relatorios]]
- [[arquitetura]]
