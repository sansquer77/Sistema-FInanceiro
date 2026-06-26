# Referência: Lançamentos

Análise feita em 13/06/2026 com conta de teste autorizada. O objetivo é capturar comportamento e estrutura, não dados privados.

## Papel do módulo

Lançamentos são o centro operacional do sistema. Eles registram despesas, receitas e transferências, alimentam saldos de contas, faturas de cartão, relatórios, limites e visão geral.

## Estrutura observada

- Navegação mensal com período selecionado.
- Lista agrupada por data.
- Cada grupo de data exibe lançamentos do dia e saldo do dia.
- Rodapé/resumo com saldo realizado e saldo previsto.
- Busca textual por descrição.
- Filtros por período e outras dimensões.
- Ações rápidas para nova despesa, nova receita e nova transferência.
- Importação e exportação de arquivo como ações avançadas.

## Tipos de lançamento

### Despesa

Representa saída de dinheiro em conta ou cartão.

Campos esperados:

- Descrição.
- Valor.
- Data.
- Conta ou cartão.
- Categoria e subcategoria.
- Tags.
- Observação.
- Estado de pagamento ou efetivação.
- Recorrência ou parcelamento quando aplicável.

### Receita

Representa entrada de dinheiro em conta.

Campos esperados:

- Descrição.
- Valor.
- Data.
- Conta de destino.
- Categoria de receita.
- Tags.
- Observação.
- Estado de recebimento.
- Recorrência quando aplicável.

### Transferência

Move valor entre duas contas sem alterar patrimônio total.

Campos esperados:

- Descrição.
- Valor.
- Data.
- Conta de origem.
- Conta de destino.
- Tags ou observação opcionais.

## Estados

- Realizado: afeta o saldo atual.
- Previsto: aparece em projeções, mas não deve afetar o saldo realizado.
- Arquivado/excluído: não aparece nas listas principais, mas pode ser necessário manter rastreabilidade.

## Filtros esperados

- Hoje.
- Esta semana.
- Este mês.
- Este ano.
- Período personalizado.
- Conta.
- Cartão.
- Categoria.
- Tag.
- Texto livre.
- Tipo: despesa, receita ou transferência.
- Estado: realizado ou previsto.

## Regras para a réplica local

- Lançamentos de conta atualizam `current_balance_cents`.
- Lançamentos de cartão entram na fatura, não no saldo da conta até o pagamento da fatura.
- Transferências geram dois movimentos vinculados ou um registro com origem e destino.
- Parcelas devem manter vínculo com o lançamento original.
- Recorrências devem gerar instâncias futuras previsíveis.
- O saldo previsto considera lançamentos futuros dentro do período.

## Critérios de aceite futuros

- A lista de lançamentos agrupa itens por data.
- O usuário consegue alternar o período sem perder filtros ativos.
- O saldo do dia reflete lançamentos realizados até aquela data.
- Busca textual encontra lançamentos por descrição.
- Despesas, receitas e transferências aparecem com sinais visuais diferentes.
