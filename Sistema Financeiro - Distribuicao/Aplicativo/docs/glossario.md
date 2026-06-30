---
tipo: glossario
area: meta
status: implementado
versao: 1.0
atualizado: 2026-06-29
relacionados:
  - "[[sdd]]"
  - "[[requisitos]]"
  - "[[arquitetura]]"
tags: [glossario, meta]
---

# Glossário de domínio

> [!info] Status
> **implementado** · área: `meta` · atualizado em 2026-06-29

Vocabulário do Sistema Financeiro. Cada termo aponta para a spec onde a regra está descrita em detalhe — use este arquivo como ponto de partida no Obsidian (painel de backlinks mostra tudo que referencia cada termo).

## Contas e moedas

- **Conta-corrente**: cadastro manual de conta bancária com saldo, moeda e natureza. Ver [[contas-correntes]].
- **Natureza da conta** (`liquidity`, `wallet`, `investment`): define o comportamento esperado da conta — liquidez comum, carteira física (sem fatura nem recorrência) ou conta usada pelo portfólio de investimentos. Ver [[contas-correntes]], [[lancamentos]].
- **Carteira (`wallet`)**: conta que só aceita receita, despesa e transferência à vista. Ver [[lancamentos]].
- **Câmbio**: lançamento entre contas de moedas diferentes, com cotação ajustável. Ver [[lancamentos]].

## Lançamentos

- **Lançamento**: movimentação financeira manual ou importada (receita, despesa, transferência, câmbio ou investimento). Ver [[lancamentos]].
- **Recorrência**: série de lançamentos periódicos gerados a partir de uma regra de frequência. Ver [[lancamentos]], [[cartoes]].
- **Parcelamento**: série de lançamentos com índice e total (`1/12`, `2/12`...). Ver [[lancamentos]], [[cartoes]].
- **Conciliação** (`reconciled_at`): marcação de que um lançamento foi confirmado contra o extrato real. Lançamentos conciliados não são afetados por edição/exclusão em cascata. Ver [[lancamentos]], [[cartoes]].
- **Edição/Exclusão em cascata** (`apply_to_future` / `scope=future`): aplica uma mudança a todas as ocorrências futuras não conciliadas de uma série. Ver [[lancamentos]].

## Classificação

- **Categoria**: classificação obrigatória de um lançamento (receita, despesa ou investimento). Ver [[categorias-tags-gestao]].
- **Subcategoria**: classificação opcional, dependente de uma categoria. Ver [[categorias-tags-gestao]].
- **Tag**: marcador transversal, N:M com lançamentos. Ver [[categorias-tags-gestao]].

## Cartões de crédito

- **Fatura** (`invoice_month`, formato `AAAA-MM`): competência mensal de um lançamento de cartão, calculada pela data da compra e pelo dia de fechamento do cartão. Ver [[cartoes]].
- **Conta preferencial de pagamento**: conta-corrente padrão sugerida para pagar a fatura de um cartão, deve ter a mesma moeda do cartão. Ver [[cartoes]].

## Limites

- **Limite de gastos / meta**: valor-alvo de despesa por mês, categoria e (opcionalmente) subcategoria. Ver [[limites-gastos]].

## Investimentos

- **Posição inicial** (`opening position`): saldo histórico de um ativo cadastrado diretamente no portfólio, sem afetar saldo de conta. Ver [[investimentos-portfolio]].
- **Operação de investimento**: lançamento do tipo investimento que afeta o saldo da conta e a posição no portfólio. Ver [[investimentos-portfolio]], [[lancamentos]].
- **Indexador**: referência de rentabilidade de renda fixa pós-fixada/híbrida (CDI, SELIC, IPCA, IGP-M, TR), obtida via API do Banco Central (SGS). Ver [[investimentos-portfolio]].
- **IOF / IR regressivo**: tributos estimados e deduzidos do resgate de renda fixa conforme prazo de retenção. Ver [[investimentos-portfolio]].
- **Resgate / Encerramento**: devolução de valor à conta de origem (resgate) ou movimentação definitiva da posição para o histórico (encerramento), com consumo FIFO em posições com múltiplas origens. Ver [[investimentos-portfolio]].

## Relatórios e visão geral

- **Cockpit**: painel que consolida saldos por moeda, planejamento recorrente, dívidas parceladas e portfólio por tipo. Ver [[arquitetura]].
- **Relatório sintético / detalhado**: agregados sem detalhe de lançamento vs. com detalhe de lançamento. Ver [[relatorios]].

## Importação

- **Importação Organizze**: leitura de exportações `.xls`/`.csv` do Organizze. Ver [[importacao-organizze]].
- **Modelo do sistema**: planilha `.xlsx` própria do app para importação estruturada de contas/cartões. Ver [[importacao-organizze]].

## Segurança e acesso

- **Sessão**: token opaco validado no servidor, armazenado em cookie `HttpOnly`/`SameSite=Lax`. Ver [[seguranca-autenticacao]].
- **`auth_attempts`**: contador persistente de tentativas de login e recuperação de senha, usado para bloqueio temporário. Ver [[seguranca-autenticacao]].
- **Código de recuperação**: token temporário de 15 minutos para redefinir senha, enviado por e-mail SMTP. Ver [[recuperacao-senha]].

## Metodologia e arquitetura

- **SDD**: condução do desenvolvimento por especificações escritas antes da implementação. Ver [[sdd]].
- **ADR** (Architecture Decision Record): registro de uma decisão técnica e seu porquê. Ver [[adr/0001-stack-local-sem-framework]], [[adr/0002-modularizacao-frontend]].

## Relacionados

- [[sdd]]
- [[requisitos]]
- [[arquitetura]]
