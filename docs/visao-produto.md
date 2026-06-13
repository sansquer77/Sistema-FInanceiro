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

- Autenticacao e conta do usuario.
- Contas-correntes manuais.
- Categorias, subcategorias e tags.
- Lancamentos de receita, despesa e transferencia.
- Importacao de lancamentos do Organizze.
- Recuperacao de senha por email SMTP localmente configurado.

### Planejados

- Cartoes de credito, faturas, limites e pagamento.
- Relatorios por periodo, categoria, conta e tag.
- Recorrencia, parcelamento e lancamentos previstos.
- Limites de gastos por categoria.
- Visao geral consolidada.

## Estado atual

O app ja cobre o ciclo basico de controle financeiro local: usuario entra, cadastra contas, cria categorias/tags, registra lancamentos e acompanha o saldo atualizado. As proximas evolucoes devem priorizar relatorios e cartoes, pois dependem dos dados ja existentes.
