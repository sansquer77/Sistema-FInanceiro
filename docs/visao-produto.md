# Visao do Produto

## Objetivo

Criar um sistema financeiro local, simples e confiavel para organizar contas, movimentacoes e classificacoes pessoais sem depender de servicos externos para operar no dia a dia.

## Inspiracao

O Organizze serve como referencia de clareza: modulos financeiros separados, saldos faceis de conferir, baixa friccao para cadastrar informacoes e relatorios por dimensoes financeiras. O app deve seguir essa direcao sem copiar interface, textos proprietarios ou dados de contas.

## Principios de experiencia

- A tela inicial deve responder rapidamente quanto existe, onde esta e o que mudou.
- Cada modulo deve ter uma responsabilidade clara.
- Valores monetarios nao devem aparecer duplicados quando representam o mesmo dado.
- A interface deve priorizar leitura, conferencia e cadastro rapido.
- O usuario deve conseguir operar o app localmente, mesmo sem internet.
- A navegacao deve separar visao geral, cadastros, lancamentos e relatorios.

## Modulos

### Implementados

- Autenticação e conta do usuário.
- Contas-correntes manuais (liquidez, carteira, investimentos) em múltiplas moedas.
- Categorias, subcategorias e tags.
- Lançamentos de receita, despesa, transferência e investimento.
- Lançamentos recorrentes e parcelamento de transações.
- Cartões de crédito, limites, faturas e fluxo de pagamentos de fatura.
- Limites e metas de gastos mensais por categoria e subcategoria.
- Cockpit com saldos por moeda, planejamento recorrente, dívidas parceladas, maiores receitas/despesas e portfólio por tipo.
- Relatórios por categoria, subcategoria, conta, tag e fluxo diário, com detalhamento dos lançamentos.
- Portfólio de investimentos com cotações integradas de mercado (ações, FIIs, criptos), indexadores do Banco Central (SGS para renda fixa), poupança, previdência privada, resgate, encerramento e ajuste manual de valor.
- Importação de lançamentos do Organizze e planilhas modelo do próprio sistema (.xlsx).
- Recuperação de senha por e-mail SMTP localmente configurado, com assistente para Gmail e Outlook/Microsoft usando senha de app.

### Planejados

- Integração ou exportação direta de dados em outros formatos.
- Conciliação automática de arquivos OFX bancários.

## Estado atual

O app já cobre todo o ciclo avançado de controle financeiro local: usuário entra, configura recuperação de senha por e-mail quando desejar, cadastra contas e cartões, define limites, cria categorias/tags, registra lançamentos normais, parcelados ou recorrentes, acompanha faturas, relatórios e Cockpit, realiza o acompanhamento de investimentos com precificação, valorização automática ou ajuste manual de ativos, e importa dados de planilhas locais. As próximas evoluções devem priorizar automações de conciliação/importação e refinamentos de precisão para classes específicas de ativos.
