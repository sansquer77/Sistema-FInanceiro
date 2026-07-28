---
tipo: spec
area: score-saude-financeira
status: em-implementacao
versao: 0.2
atualizado: 2026-07-27
relacionados:
  - "[[relatorios]]"
  - "[[limites-gastos]]"
  - "[[investimentos-portfolio]]"
  - "[[cartoes]]"
  - "[[contas-correntes]]"
  - "[[arquitetura]]"
tags: [spec, "area/score-saude-financeira", "status/em-implementacao"]
aliases: ["Score de Saúde Financeira", "Diagnóstico Financeiro", "Financial Health Score"]
---

# Score de Saúde Financeira

> [!info] Status
> **em-implementacao** · área: `score-saude-financeira` · atualizado em 2026-07-27 · relacionados: [[relatorios]], [[limites-gastos]], [[investimentos-portfolio]], [[cartoes]], [[contas-correntes]]

## Problema

O usuário possui dados de contas, lançamentos, cartões, limites de gastos e investimentos espalhados pelo sistema, mas não conta com um indicador síntese (pontuação de 0 a 1000) que avalie seu estado financeiro geral nem orientações claras sobre quais pilares precisam de atenção.

## Usuário

Qualquer usuário autenticado localmente que deseje entender sua saúde financeira através de um diagnóstico consolidado e acionável.

## Jornada

1. O usuário acessa o **Cockpit** e clica na aba dedicada de **Saúde Financeira**.
2. O sistema calcula e exibe a pontuação total (0 a 1000) do mês consultado, categorizada em níveis (Crítico, Atenção, Bom, Excelente).
3. O usuário visualiza o detalhamento dos 5 pilares do score com seus pesos aprovados (Poupança 25%, Reserva 25%, Endividamento 20%, Limites 15%, Diversificação 15%), acompanhados de recomendações práticas para melhorar cada indicador.
4. O usuário pode consultar o histórico mensal da evolução do seu score e visualizar plano de ação com recomendações sem poluição visual do painel principal do Cockpit.

## Dados

| Campo | Tipo | Regra |
|---|---|---|
| `month` | `AAAA-MM` | Obrigatório. Mês de referência da avaliação. |
| `score_total` | inteiro | Pontuação consolidada entre `0` e `1000`. |
| `nivel` | texto | Categoria: `critico` (0-399), `atencao` (400-599), `bom` (600-799), `excelente` (800-1000). |
| `pilar_poupanca` | inteiro | Pontuação da Taxa de Poupança (0 a 250 pontos; peso 25%). |
| `pilar_reserva` | inteiro | Pontuação da Reserva de Emergência (0 a 250 pontos; peso 25%). |
| `pilar_endividamento` | inteiro | Pontuação do Comprometimento de Renda (0 a 200 pontos; peso 20%). |
| `pilar_limites` | inteiro | Pontuação de Aderência aos Limites de Gastos (0 a 150 pontos; peso 15%). |
| `pilar_diversificacao` | inteiro | Pontuação da Diversificação de Investimentos (0 a 150 pontos; peso 15%). |

## Regras

- **Cálculo dos Pilares (Núcleo Python em `financeiro/financial_health.py`)**:
  - **Taxa de Poupança / Aporte (250 pts / peso 25%)**: Calcula a proporção `(Receitas líquidas - Despesas líquidas) / Receitas`. Pontuação máxima de 250 pts alcançada ao poupar/aportar >= 30% da renda.
  - **Reserva de Emergência (250 pts / peso 25%)**: Calcula a liquidez imediata (saldo em contas + investimentos em renda fixa líquida/poupança) dividida pela média de despesas mensais dos últimos 3 meses. Pontuação máxima de 250 pts para reserva >= 6 meses.
  - **Comprometimento de Renda / Endividamento (200 pts / peso 20%)**: Calcula o comprometimento com faturas de cartão abertas e compras parceladas em relação às receitas. Pontuação máxima de 200 pts quando o comprometimento for <= 20%; cai para 0 pts se for >= 60%.
  - **Aderência aos Limites (150 pts / peso 15%)**: Calcula o percentual de categorias com limites cadastrados que não foram estourados no mês. Pontuação máxima de 150 pts se 100% das categorias estiverem dentro da meta. Se não houver limites cadastrados, atribui nota neutra proporcional (75 pts).
  - **Diversificação de Portfólio (150 pts / peso 15%)**: Avalia se os ativos estão distribuídos em mais de uma classe de investimento (Renda Fixa, Renda Variável, Poupança, Previdência) sem sobreconcentração (> 70% em um único ativo).
- **Interface e Navegação**: O Score de Saúde Financeira e suas recomendações acionáveis são exibidos em uma aba dedicada dentro do módulo **Cockpit**, permitindo visualização expandida dos pilares e histórico sem sobrecarregar a visão sintética inicial.
- **Normalização de Moedas**: Todos os cálculos utilizam os valores normalizados em BRL (centavos inteiros), conforme as regras já vigentes em [[investimentos-portfolio]] e [[relatorios]].
- **Isolamento por Usuário**: O score é calculated exclusivamente sobre os dados do usuário autenticado na sessão.
- **Sem Efeito Colateral**: A consulta do score é uma operação de leitura analítica idempotente que não altera saldos nem movimentações.

## API e dados

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/api/financial-health-score?month=AAAA-MM` | Retorna a pontuação detalhada do mês e sugestões de melhoria. |
| `GET` | `/api/financial-health-score/history?months=6` | Retorna o histórico da pontuação dos últimos N meses. |

Tabelas: consulta `transactions`, `credit_card_transactions`, `spending_limits`, `investment_opening_positions`, `investment_operations` e `checking_accounts`.

## Critérios de aceite

- Dado um usuário com receita de R$ 10.000,00 e despesas de R$ 6.000,00 (taxa de poupança de 40%), quando o score é consultado, então o pilar de taxa de poupança retorna a pontuação máxima de 250 pontos.
- Dado um usuário sem lançamentos no mês de referência, quando a API é acionada, então o sistema retorna um indicador com status neutro/dados insuficientes sem gerar divisão por zero.
- Dado um usuário com 3 limites cadastrados sendo 1 estourado no mês, quando avaliado a aderência aos limites, então a nota do pilar corresponde a 66.6% da pontuação máxima do pilar (100 de 150 pts).
- Dado um usuário autenticado A, quando tenta consultar a rota `/api/financial-health-score`, então somente os lançamentos e ativos associados ao `user_id` de A são considerados no cálculo.
- Dado o Cockpit carregado, quando o usuário seleciona a aba dedicada de Saúde Financeira no tema claro ou escuro, o medidor do Score utiliza a cor verde `#10B981` exclusivamente para indicar status saudável, respeitando o design system.

## Pendências

Nenhuma pendência conhecida.

## Fora de escopo

- Integração com órgãos de proteção ao crédito externos (Serasa, SPC, Registrato/Banco Central).
- Motor de inteligência artificial generativa externa para sugestões de investimento.

## Plano de implementação

- [ ] Passo 1 — Criar módulo Python `financeiro/financial_health.py` implementando as funções atômicas de cálculo de cada pilar (com a distribuição 25/25/20/15/15) em centavos inteiros. Fecha: critérios 1, 2, 3 e 4.
- [ ] Passo 2 — Adicionar as rotas `GET /api/financial-health-score` e `GET /api/financial-health-score/history` em `app.py` com validação de sessão e origem. Fecha: critério 4.
- [ ] Passo 3 — Criar os testes unitários automatizados em `tests/test_financial_health.py` validando os pilares e casos de borda. Fecha: critérios 1, 2 e 3.
- [ ] Passo 4 — Implementar a aba dedicada de Saúde Financeira na view do Cockpit (`web/modules/cockpit-view.js` / sub-view dedicada) utilizando CSS nativo e tokens do [[design-system]]. Fecha: critério 5.
- [ ] Passo 5 — Atualizar `docs/arquitetura.md` e `docs/requisitos.md` com as novas rotas e módulo.

## Changelog

- `0.2` — 2026-07-27 — Aprovada a distribuição de pesos dos 5 pilares (25/25/20/15/15) e definida a localização da interface como aba dedicada no Cockpit para permitir recomendações futuras sem poluir a visualização principal. Pendências resolvidas.
- `0.1` — 2026-07-27 — Especificação inicial em status `em-implementacao`.

## Relacionados

- [[relatorios]]
- [[limites-gastos]]
- [[investimentos-portfolio]]
- [[cartoes]]
- [[contas-correntes]]
- [[arquitetura]]
