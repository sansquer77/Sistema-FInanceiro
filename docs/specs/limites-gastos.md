---
tipo: spec
area: limites
status: implementado
versao: 1.10
atualizado: 2026-10-18
relacionados:
  - "[[categorias-tags-gestao]]"
  - "[[cartoes]]"
  - "[[relatorios]]"
  - "[[arquitetura]]"
  - "[[alertas-cockpit]]"
tags: [spec, "area/limites"]
aliases: ["Limites de Gastos", "Budgets", "Metas"]
---

# Limites de Gastos

> [!info] Status
> **implementado** · versão: `1.10` · área: `limites` · atualizado em 2026-10-19 · relacionados: [[categorias-tags-gestao]], [[cartoes]], [[relatorios]], [[alertas-cockpit]]

## Problema

O usuário precisa estabelecer limites recorrentes de gastos mensais por categoria e subcategoria, como restaurantes todos os meses, e monitorar o andamento do consumo em relação a esses limites.

## Usuário

Qualquer usuário autenticado localmente que queira controlar seu orçamento de despesas.

## Jornada

1. O usuário seleciona a funcionalidade de Limites de Gastos.
2. Define o mês inicial de vigência (`AAAA-MM`), a categoria de despesa (e opcionalmente uma subcategoria específica) e o valor limite.
3. Acompanha o progresso comparando a meta com o acumulado de transações reais do período.
4. Quando algum limite do mês corrente é ultrapassado, o menu de Limites exibe alerta visual e o Cockpit exibe um farol com link direto para a função.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Obrigatório. Mês inicial de vigência do limite recorrente. |
| `categoria_id` | FK | Obrigatório. Deve ter `group_type = expense`. |
| `subcategoria_id` | FK | Opcional. Se informado, limite é específico para ela. |
| `valor` | inteiro (centavos) | Obrigatório. Deve ser maior que zero. |

## Regras

- Os limites aplicam-se apenas a categorias cujo `group_type` seja `expense` (despesa).
- Se uma subcategoria for selecionada, o limite é específico para ela; caso contrário, aplica-se a toda a categoria.
- Um limite definido em um mês continua vigente nos meses seguintes até ser substituído por uma definição mais recente para a mesma categoria/subcategoria.
- Ao consultar um mês, o sistema usa o limite mais recente com `month <= mês consultado`.
- Criar um limite para um mês posterior funciona como reajuste recorrente a partir daquele mês, sem apagar o histórico do limite anterior.
- Ao editar um limite herdado para outra categoria/subcategoria em um mês posterior, se já houver uma definição para a nova identidade nesse mês, a operação retorna conflito e preserva ambas as definições existentes; a outra definição deve ser editada separadamente.
- O consumo considera despesas em contas pelo mês da data do lançamento.
- O consumo considera despesas em cartões pela fatura aberta do mês (`invoice_month`), mesmo quando a data da compra pertence ao mês anterior. Ver [[cartoes]].
- Pagamentos de fatura não removem o consumo do limite — o limite mede competência/gasto da fatura, não a quitação.
- O consumo mensal é agregado no SQLite por categoria e subcategoria e acompanha cada limite retornado pela API. A interface não depende da fatia de lançamentos mantida por Cockpit, Extrato ou Cartões.
- É permitida apenas uma única definição por mês inicial (`AAAA-MM`), categoria e subcategoria (restrição UNIQUE no banco).
- O limite deve ser um valor monetário positivo maior que zero.
- O seletor mensal da tela de Limites deve usar botões compactos por ícone e rótulo no formato `MM/AAAA`.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/spending-limits` |
| `GET` | `/api/spending-limits?month=AAAA-MM` |
| `POST` | `/api/spending-limits` |
| `PUT` | `/api/spending-limits/{id}` |
| `DELETE` | `/api/spending-limits/{id}` |

Tabelas: `spending_limits`, `categories`, `subcategories`.

## Critérios de aceite

- Dado a criação de uma meta de R$ 500,00 para "Alimentação" em "2026-06", quando julho de 2026 é consultado sem nova definição, então ela aparece como limite vigente com consumo de julho.
- Dado uma nova definição de R$ 750,00 para "Alimentação" em "2026-07", quando julho de 2026 é consultado, então o limite vigente é R$ 750,00.
- Dado um limite de R$ 500,00 vigente desde "2026-06", quando ele é alterado para R$ 750,00 a partir de "2026-07", então junho mantém a definição de R$ 500,00 e julho e os meses seguintes usam R$ 750,00.
- Dado uma tentativa de cadastrar meta duplicada para o mesmo mês inicial/categoria, quando executada, o sistema atualiza a meta existente ou retorna erro de conflito.
- Dado a exclusão de um limite, quando executada, nenhuma transação financeira é afetada.
- Dado despesas de cartão na fatura aberta do mês, quando computadas, impactam o limite da categoria/subcategoria correspondente.
- Dado um limite ultrapassado no mês corrente, quando exibido, o menu de Limites e o Cockpit exibem alertas visuais.
- Dado o usuário visualizando o seletor mensal de Limites, quando o mês é exibido, então o rótulo usa o formato `MM/AAAA`.
- Dado o usuário navegando entre competências de Limites, quando o mês muda, então cada limite apresenta o consumo daquele mês mesmo que nenhuma lista detalhada dessa competência esteja carregada no navegador.
- Dado o usuário criando ou ajustando um limite, quando o formulário é exibido, então o mês de início da vigência aparece como campo editável e é enviado como a competência da definição.
- Dado um limite herdado de uma categoria e uma definição futura existente para outra categoria, quando a edição tenta transferir o limite herdado para a identidade e mês já ocupados, então a API retorna conflito sem alterar valor, observações ou identidade do registro futuro.

## Changelog

- `1.3` — 2026-09-01 — Consumo por limite passa a ser agregado no SQLite para a competência consultada, removendo a dependência do estado mensal compartilhado do frontend.
- `1.2` — 2026-08-02 — Seletor mensal de Limites padronizado com botões compactos por ícone e rótulo `MM/AAAA`.
- `1.1` — 2026-07-08 — Limites passam a ser documentados como recorrentes, com `month` representando início de vigência.
- `1.0` — 2026-06-29 — Frontmatter e critérios formalizados.

## Changelog

- `1.10` — 2026-10-19 — Impede que a edição de um limite herdado sobrescreva uma definição futura independente de outra categoria/subcategoria; retorna conflito para edição explícita do registro existente.
- `1.9` — 2026-10-18 — Reforçada a regressão que mantém a definição futura vigente nos meses seguintes até novo reajuste.
- `1.8` — 2026-10-18 — Alterar o mês no formulário não recarrega nem limpa a edição; o novo mês é aplicado somente ao salvar.

- `1.7` — 2026-10-18 — Campo de mês de início da vigência passa a ser visível e editável no formulário de limites.

- `1.6` — 2026-10-18 — Edição de um limite em mês posterior preserva a definição histórica e cria ou atualiza apenas a vigência futura.

- `1.5` — 2026-09-13 — Corrigida a ausência de `limit_amount_cents` no retorno de `list_spending_limits_with_consumption`, que impedia o alerta de limite estourado na central de mensagens do Cockpit.
- `1.4` — 2026-09-04 — Limites entre 80% e 100% exibem estado textual e visual de atenção antes do estouro.

## Relacionados

- [[categorias-tags-gestao]]
- [[cartoes]]
- [[relatorios]]
- [[arquitetura]]
