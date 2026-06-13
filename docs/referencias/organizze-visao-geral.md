# Referência: Organizze

Análise feita em 13/06/2026 a partir de uma conta de teste autorizada. Este documento registra apenas padrões de produto e arquitetura de informação, sem copiar dados financeiros, textos proprietários extensos ou detalhes privados da conta.

## Padrões observados

### Navegação

- Menu lateral com módulos financeiros persistentes.
- Visão geral como ponto de entrada.
- Módulos separados para lançamentos, relatórios, limite de gastos, conexão bancária, categorias, contas, cartões, preferências, tags, alertas e atividades.
- Links de gerenciamento próximos aos blocos resumidos, como "gerenciar contas" e "gerenciar cartões".

### Visão geral

- Saudação simples no topo.
- Resumo mensal com receitas e despesas.
- Atalhos diretos para ações frequentes: despesa, receita, transferência e importação.
- Blocos de acompanhamento para saldo geral, contas, maiores gastos, cartões, contas a receber, contas a pagar e limites de gastos.
- Listas curtas com opção de ver mais, evitando que a tela inicial vire uma tabela completa.

### Contas

- Página dedicada para contas.
- Ação de criar nova conta em destaque.
- Separação entre contas ativas e contas arquivadas.
- Diferenciação entre conta manual e conta conectada.
- Conta conectada é tratada como evolução ligada à integração bancária, não como requisito do cadastro manual.

## Decisões para o Sistema Financeiro

- Manter a tela atual de contas simples até existirem lançamentos e dashboard geral.
- Evitar duplicação de saldos: o mesmo total deve aparecer em apenas um bloco por tela.
- Preparar a arquitetura para uma futura "Visão geral", mas sem antecipar telas vazias.
- Tratar conexão bancária como módulo futuro e opcional.
- Separar contas arquivadas quando houver volume ou necessidade de restauração.

## Implicações para specs

- Cada módulo deve ter uma spec própria antes da implementação.
- A futura visão geral deve compor dados de contas, cartões, lançamentos e limites, em vez de concentrar regras próprias.
- Cadastros e relatórios devem ser módulos distintos.
