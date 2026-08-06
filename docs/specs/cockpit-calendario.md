---
tipo: spec
area: cockpit
status: em-implementacao
versao: 0.2
atualizado: 2026-08-06
relacionados:
  - "[[relatorios]]"
  - "[[lancamentos]]"
  - "[[investimentos-portfolio]]"
  - "[[cartoes]]"
  - "[[arquitetura]]"
tags: [spec, "area/cockpit", "status/em-implementacao"]
aliases: ["Calendário do Cockpit", "Aba Calendário"]
---

# Calendário do Cockpit

> [!info] Status
> **em-implementacao** · área: `cockpit` · atualizado em 2026-08-06 · relacionados: [[relatorios]], [[lancamentos]], [[investimentos-portfolio]], [[cartoes]]

## Problema

O Cockpit mostra a situação do mês, tendências e saúde financeira, mas não oferece uma visão centralizada de obrigações e recebimentos pendentes de datas passadas e de investimentos de renda fixa que vencem nos próximos 60 dias. O usuário precisa lembrar de verificar manualmente o extrato de contas e o Portfólio para identificar atrasos e vencimentos próximos.

## Usuário

Usuário autenticado que consulta o Cockpit e deseja uma visão rápida de contas a receber atrasadas, contas a pagar atrasadas e vencimentos de renda fixa nos próximos 30 e 60 dias.

## Jornada

1. O usuário acessa **Cockpit > Calendário**, em uma aba separada de **Situação do mês**, **Tendências** e **Saúde Financeira**.
2. O sistema calcula, a partir da data atual:
   - receitas de datas passadas que ainda não foram conciliadas;
   - despesas de datas passadas que ainda não foram conciliadas;
   - investimentos de renda fixa com vencimento nos próximos 30 dias;
   - investimentos de renda fixa com vencimento entre 31 e 60 dias.
3. O usuário visualiza quatro cards na tela: dois na parte superior (receber atrasadas à esquerda, pagar atrasadas à direita) e dois na parte inferior (vencimentos em 30 dias à esquerda, vencimentos em 60 dias à direita).
4. O usuário pode clicar em um item para navegar ao módulo correspondente (Extrato de Contas ou Portfólio).

## Dados

| Campo | Tipo | Descrição |
|---|---|---|
| `reference_date` | `AAAA-MM-DD` | Data de referência usada para calcular atrasos e janelas de vencimento. Usa a data atual do servidor. |
| `overdue_receivables` | lista | Receitas de datas anteriores a `reference_date` não conciliadas. |
| `overdue_payables` | lista | Despesas de datas anteriores a `reference_date` não conciliadas. |
| `maturity_30_days` | lista | Investimentos de renda fixa abertos com vencimento entre `reference_date` e `reference_date + 30 dias`. |
| `maturity_60_days` | lista | Investimentos de renda fixa abertos com vencimento entre `reference_date + 31 dias` e `reference_date + 60 dias`. |
| `total_overdue_receivables_cents` | inteiro | Soma total dos valores a receber atrasados, em centavos. |
| `total_overdue_payables_cents` | inteiro | Soma total dos valores a pagar atrasados, em centavos. |
| `totals_by_currency` | lista | Opcional. Totais atrasados e de vencimentos separados por moeda, para exibição multimoeda. |

Campos de cada item de lançamento atrasado:

| Campo | Tipo | Descrição |
|---|---|---|
| `id` | inteiro | Identificador do lançamento. |
| `description` | texto | Descrição do lançamento. |
| `date` | `AAAA-MM-DD` | Data prevista do lançamento. |
| `amount_cents` | inteiro | Valor em centavos. |
| `currency` | texto | Moeda da conta. |
| `account_id` | inteiro | Identificador da conta. |
| `account_name` | texto | Nome da conta. |
| `days_overdue` | inteiro | Dias de atraso em relação a `reference_date`. |

Campos de cada item de vencimento de investimento:

| Campo | Tipo | Descrição |
|---|---|---|
| `position_id` | inteiro | Identificador da posição aberta. |
| `asset_name` | texto | Nome do ativo. |
| `asset_identifier` | texto | Ticker ou código, quando houver. |
| `maturity_date` | `AAAA-MM-DD` | Data de vencimento. |
| `current_value_cents` | inteiro | Valor atual estimado em centavos. |
| `currency` | texto | Moeda da carteira. |
| `account_id` | inteiro | Identificador da carteira. |
| `account_name` | texto | Nome da carteira. |
| `days_to_maturity` | inteiro | Dias até o vencimento a partir de `reference_date`. |

## Regras

### Aba e layout

- A aba **Calendário** deve aparecer no Cockpit entre **Situação do mês** e **Tendências**, resultando na ordem: **Situação**, **Calendário**, **Tendências**, **Saúde Financeira**.
- A aba deve usar o seletor de mês compartilhado do Cockpit apenas como contexto de navegação; os cálculos de atraso e vencimento usam sempre a data atual do servidor, não o mês selecionado.
- O layout deve usar grid de duas colunas na parte superior e duas colunas na parte inferior:
  - **Metade esquerda superior**: Contas a receber atrasadas.
  - **Metade direita superior**: Contas a pagar atrasadas.
  - **Metade esquerda inferior**: Investimentos com vencimento em 30 dias.
  - **Metade direita inferior**: Investimentos com vencimento em 60 dias.
- Em telas estreitas, os cards devem empilhar verticalmente, mantendo a ordem: receber, pagar, 30 dias, 60 dias.

### Contas a receber atrasadas

- Consideram apenas lançamentos de conta (`transactions`) do tipo `income`.
- A data do lançamento (`date`) deve ser anterior a `reference_date`.
- O campo `reconciled_at` deve estar nulo ou vazio (não conciliado).
- Transferências, investimentos e despesas não entram neste card.
- Lançamentos de cartão de crédito não entram neste card.
- Itens devem ser ordenados pelo mais antigo para o mais recente.
- Deve ser exibido o total por moeda.
- Lançamentos parcelados devem aparecer apenas na parcela cuja data está atrasada e não conciliada.

### Contas a pagar atrasadas

- Consideram apenas lançamentos de conta (`transactions`) do tipo `expense`.
- A data do lançamento (`date`) deve ser anterior a `reference_date`.
- O campo `reconciled_at` deve estar nulo ou vazio (não conciliado).
- Transferências, investimentos e pagamentos de fatura não entram neste card.
- Lançamentos de cartão de crédito não entram neste card.
- Itens devem ser ordenados pelo mais antigo para o mais recente.
- Deve ser exibido o total por moeda.
- Lançamentos parcelados devem aparecer apenas na parcela cuja data está atrasada e não conciliada.

### Vencimentos de investimentos

- Consideram apenas posições abertas de renda fixa (`fixed_income`).
- Usam a data de vencimento cadastrada (`fixed_income_maturity_date`).
- Posições encerradas ou sem vencimento cadastrado não entram.
- Poupança, ações, fundos, cripto, previdência e outros tipos não entram neste card.
- **Card 30 dias**: vencimentos de `reference_date` até `reference_date + 30 dias`, inclusive.
- **Card 60 dias**: vencimentos de `reference_date + 31 dias` até `reference_date + 60 dias`, inclusive.
- Os mesmos ativos do card de 30 dias não devem ser replicados no card de 60 dias.
- Itens devem ser ordenados pelo vencimento mais próximo para o mais distante.
- Deve ser exibido o total por moeda para cada card.
- Se um ativo vencer exatamente no dia 30, entra apenas no card de 30 dias. Se vencer no dia 31, entra apenas no card de 60 dias.

### Valores e moedas

- Todos os valores financeiros são calculados em centavos inteiros no backend.
- A interface formata os valores na moeda original do item.
- Não deve ocorrer conversão de moeda para totalização; totais são apresentados por moeda.

### Navegação e ações

- Cada item de receber/pagar deve oferecer ação para abrir o lançamento no Extrato de Contas.
- Cada item de vencimento deve oferecer ação para abrir a posição no Portfólio.
- A aba não deve permitir edição de dados; é apenas leitura.

## API e dados

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/cockpit/calendar` | Retorna os dados da aba Calendário para o usuário autenticado. |

Tabelas consultadas:

- `transactions` — lançamentos de conta (receitas e despesas atrasadas não conciliadas).
- `checking_accounts` — nome e moeda da conta.
- `investment_opening_positions` — posições iniciais de renda fixa com vencimento.
- `investment_operations` — operações de aporte de renda fixa (para cálculo de valor atual, se necessário).
- `investment_value_overrides` — valores atuais informados manualmente.

A nova rota deve ser autenticada e validar `Host`/`Origin` conforme as regras de segurança do app.

## Critérios de aceite

- Dado um usuário autenticado, quando acessa o Cockpit, então a aba **Calendário** aparece entre **Situação** e **Tendências**.
- Dado um usuário na aba **Calendário**, quando a tela é carregada, então a data de referência usada nos cálculos é a data atual do servidor, independente do mês selecionado no Cockpit.
- Dado um usuário com receitas de datas passadas não conciliadas, quando acessa a aba **Calendário**, então o card **Contas a receber atrasadas** lista os lançamentos com descrição, data, valor, conta e dias de atraso, ordenados do mais antigo ao mais recente.
- Dado um usuário com despesas de datas passadas não conciliadas, quando acessa a aba **Calendário**, então o card **Contas a pagar atrasadas** lista os lançamentos com descrição, data, valor, conta e dias de atraso, ordenados do mais antigo ao mais recente.
- Dado um usuário sem contas a receber atrasadas, quando acessa a aba **Calendário**, então o card exibe estado vazio amigável.
- Dado um usuário sem contas a pagar atrasadas, quando acessa a aba **Calendário**, então o card exibe estado vazio amigável.
- Dado um usuário com investimentos de renda fixa vencendo nos próximos 30 dias, quando acessa a aba **Calendário**, então o card **Vencimentos em 30 dias** lista os ativos com nome, vencimento, valor atual, carteira e dias até o vencimento.
- Dado um usuário com investimentos de renda fixa vencendo entre 31 e 60 dias, quando acessa a aba **Calendário**, então o card **Vencimentos em 60 dias** lista os ativos com nome, vencimento, valor atual, carteira e dias até o vencimento.
- Dado um investimento de renda fixa vencendo exatamente em 30 dias, quando acessa a aba **Calendário**, então ele aparece apenas no card de 30 dias e não no card de 60 dias.
- Dado um investimento de renda fixa vencendo em 31 dias, quando acessa a aba **Calendário**, então ele aparece apenas no card de 60 dias.
- Dado um investimento já encerrado, quando acessa a aba **Calendário**, então ele não aparece em nenhum dos cards de vencimento.
- Dado um investimento de poupança, ações, fundos, cripto ou previdência, quando acessa a aba **Calendário**, então ele não aparece nos cards de vencimento.
- Dado uma transferência ou um investimento do tipo `investment`, quando acessa a aba **Calendário**, então ele não aparece nos cards de receber/pagar atrasadas.
- Dado um lançamento parcelado de receita com a segunda parcela atrasada e não conciliada, quando acessa a aba **Calendário**, então apenas essa parcela aparece no card de receber atrasadas.
- Dado um usuário em tela estreita, quando acessa a aba **Calendário**, então os cards empilham verticalmente mantendo a ordem: receber, pagar, 30 dias, 60 dias.
- Dado um usuário clicando em um item de receber/pagar, quando a ação é acionada, então o app navega para o Extrato de Contas com o lançamento em destaque.
- Dado um usuário clicando em um item de vencimento, quando a ação é acionada, então o app navega para o Portfólio com a posição em destaque.
- Dado uma requisição sem sessão válida, quando tenta acessar `/api/cockpit/calendar`, então o sistema retorna erro de autenticação.
- Dado uma requisição com `Host`/`Origin` inválidos, quando tenta acessar `/api/cockpit/calendar`, então o sistema retorna erro de segurança sem expor dados.

## Pendências

> [!question] Pendências
> Nenhuma pendência conhecida.

## Fora de escopo

- Editar lançamentos ou posições diretamente na aba Calendário.
- Incluir lançamentos de cartão de crédito como contas a pagar atrasadas.
- Calcular juros, multas ou projeção de rendimento de investimentos na aba Calendário.
- Enviar lembretes ou notificações por e-mail.
- Incluir eventos recorrentes futuros que ainda não geraram lançamento.
- Filtros por moeda ou conta na primeira versão.

## Plano de implementação

- [x] Passo 1 — Criar rota `GET /api/cockpit/calendar` em `app.py`, autenticada e validada contra `Host`/`Origin`. Fecha: critérios 17 e 18.
- [x] Passo 2 — Implementar função no núcleo (`financeiro/calendar.py` ou módulo equivalente) para calcular contas a receber/pagar atrasadas e vencimentos de renda fixa em 30 e 60 dias, usando centavos inteiros. Fecha: critérios 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14 e 15.
- [x] Passo 3 — Adicionar a aba **Calendário** na UI do Cockpit (`web/index.html`, `web/modules/cockpit-view.js`) na ordem correta e com layout responsivo. Fecha: critérios 1, 2, 16 e 17.
- [x] Passo 4 — Implementar renderização dos cards na aba Calendário (`web/modules/calendar-view.js` ou dentro de `cockpit-view.js`) com estados vazios, totais por moeda e ações de navegação. Fecha: critérios 3, 4, 5, 6, 7, 8, 16 e 17.
- [x] Passo 5 — Criar testes automatizados para os cálculos de atrasos e vencimentos, incluindo bordas de datas (30/31 dias), exclusão de tipos indevidos e ordenação. Fecha: critérios 3 a 15.
- [x] Passo 6 — Atualizar `docs/arquitetura.md`, `docs/specs/relatorios.md` e `docs/README.md` para refletir a nova aba e rota. Fecha: critérios 1 e 2.

## Changelog

- `0.2` — 2026-08-06 — Implementados no backend a rota `GET /api/cockpit/calendar` e o módulo `financeiro/calendar.py`, com testes automatizados para atrasos e vencimentos. Status avançado para `em-implementacao`; UI ainda pendente (passos 3 e 4).
- `0.1` — 2026-08-04 — Spec inicial em rascunho para a aba **Calendário** no Cockpit, com cards de contas a receber/pagar atrasadas e vencimentos de renda fixa em 30 e 60 dias.

## Relacionados

- [[relatorios]]
- [[lancamentos]]
- [[investimentos-portfolio]]
- [[cartoes]]
- [[arquitetura]]
