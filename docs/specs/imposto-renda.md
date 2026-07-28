---
tipo: spec
area: imposto-renda
status: depreciado
versao: 0.3
atualizado: 2026-07-27
relacionados:
  - "[[investimentos-portfolio]]"
  - "[[relatorios]]"
  - "[[lancamentos]]"
  - "[[arquitetura]]"
tags: [spec, "area/imposto-renda", "status/depreciado"]
aliases: ["IR", "IRPF", "DARF", "Módulo de IR"]
---

# Imposto de Renda sobre Investimentos (Módulo de IR)

> [!info] Status
> **depreciado** · área: `imposto-renda` · atualizado em 2026-07-27 (v0.3) · relacionados: [[investimentos-portfolio]], [[relatorios]], [[lancamentos]]

> [!warning] Decisão de não implementar
> Após especificar as regras (v0.1–v0.2), o custo de implantação e manutenção frente à complexidade e volatilidade da legislação fiscal — especialmente ativos no exterior (Lei 14.754/2023) e a necessidade de manter `ir_tax_rules` atualizada — foi considerado desproporcional ao ganho para um sistema de uso familiar/pessoal. Serviços especializados como o mycapital.com.br são mais robustos e têm integração direta com a B3 para captar dados na fonte, o que este app (sem framework web, sem dependências externas, ADR-0001/ADR-0004) não pretende replicar. Módulo descartado; este documento fica como registro histórico da decisão e das regras levantadas, caso seja revisitado.

## Problema

O usuário que opera o [[investimentos-portfolio|Portfólio]] precisa apurar mensalmente se houve ganho tributável em suas operações de renda variável e criptoativos, saber quando um DARF é devido (considerando isenções mensais por classe de ativo e compensação de prejuízos) e, na época da declaração anual, montar um resumo confiável de bens, rendimentos isentos e rendimentos sujeitos a tributação exclusiva. Hoje esse controle é feito manualmente fora do sistema, com risco de esquecer isenções, misturar operações comuns com day trade ou perder o histórico de prejuízo a compensar.

## Usuário

Qualquer usuário autenticado localmente que tenha posições ou operações no Portfólio sujeitas a apuração de ganho de capital (ações, ETFs, BDRs, FIIs, criptoativos) e queira apoio para gerir DARFs mensais e preencher a declaração anual de IRPF.

## Inspiração e limites de fidelidade

O serviço mycapital.com.br é referência apenas da **capacidade** esperada — acompanhamento de carteira acoplado a apuração fiscal e relatório de declaração —, não da interface. Como em todo o vault (ver critério de fidelidade em [[roadmap]]), este módulo reproduz capacidades, não a tela de terceiros. O app **não se conecta a Sicalc, GCAP, e-CAC ou ao programa da Receita Federal**: ele calcula e organiza a informação; a emissão oficial do DARF e a transmissão da declaração continuam sendo feitas pelo usuário nos sistemas oficiais.

## Jornada

1. O usuário abre o módulo **IR**, acessível a partir do Portfólio.
2. Na aba **Apuração Mensal**, vê, mês a mês e por classe de ativo, o resultado apurado a partir das operações já registradas no Portfólio: total vendido, resultado (ganho/prejuízo), se está dentro da faixa de isenção, prejuízo compensado de meses anteriores e, quando há imposto devido, o valor, o código de recolhimento e o vencimento do DARF.
3. O usuário marca um DARF como pago (registro manual de controle) e mantém histórico dos DARFs pagos e pendentes.
4. Na aba **IRPF**, o usuário seleciona o ano-calendário e obtém um relatório consolidado para apoiar o preenchimento da Declaração de Ajuste Anual: posições em aberto em 31/12 pelo custo de aquisição (Bens e Direitos), rendimentos isentos e não tributáveis, rendimentos sujeitos a tributação exclusiva/definitiva (renda fixa) e o resumo de ganhos de renda variável e criptoativos mês a mês, com os DARFs já pagos.
5. O usuário imprime ou exporta o relatório da aba IRPF para consulta enquanto preenche a declaração no programa oficial.

## Regras

**Escopo de apuração (o que gera cálculo de IR neste módulo):**
- Somente eventos já registrados no Portfólio geram apuração: resgates (`investment_redemptions`) e encerramentos (`investment_closed_positions`) de posições dos tipos `stock` (ações/ETFs/BDRs/FIIs) e `crypto`, custodiadas no Brasil **ou** no exterior (ver regra de ativos no exterior abaixo). Ver [[investimentos-portfolio]].
- Renda fixa (`fixed_income`) já tem IR e IOF regressivos retidos na fonte pelo cálculo existente do Portfólio; o módulo de IR apenas consolida esse valor na aba IRPF, sem gerar DARF para essa classe.
- Poupança (`savings`) e proventos nacionais (dividendos/JCP/rendimentos de FII) são rendimentos isentos ou de tributação exclusiva já na fonte; entram apenas no relatório anual, sem gerar DARF.
- Rendimentos recebidos de fontes no exterior (dividendos de ações/ETFs estrangeiros) **não são isentos** — entram na apuração da classe "Ativos custodiados no exterior", com regra própria de compensação de imposto retido lá fora. Hoje o Portfólio registra proventos apenas como lançamento de receita categorizado, sem vínculo com o ativo/país de origem nem com o imposto retido — ver Pendências.
- Previdência privada (`private_pension`) fica **fora do cálculo de DARF** nesta versão — ver Pendências.

**Ações, ETFs e BDRs (`stock`, exceto FIIs):**
- Operação comum (swing trade): alíquota de 15% sobre o ganho, com isenção de IR no mês em que a soma das vendas de ações no mercado à vista não ultrapassar R$ 20.000,00. A isenção é sobre o total vendido, não sobre o lucro, e não vale para ETFs, BDRs, FIIs nem day trade.
- Day trade (compra e venda do mesmo ativo no mesmo dia): alíquota de 20% sobre o ganho líquido do dia, sem qualquer isenção.
- FIIs: venda de cotas tributada a 20%, sem faixa de isenção; rendimentos distribuídos de FII são isentos e entram apenas no relatório anual.
- DARF de renda variável usa o código de receita `6015`.

**Criptoativos (`crypto`):**
- Isenção mensal quando a soma das vendas/alienações em exchanges nacionais no mês não ultrapassar R$ 35.000,00.
- Acima do limite, o ganho segue a tabela progressiva de ganho de capital (de 15% a 22,5% conforme a faixa de ganho).
- DARF de criptoativos usa o código de receita `4600`.
- Aplica-se apenas a criptoativos custodiados em exchange nacional. Custódia no exterior segue a regra de "Ativos custodiados no exterior" abaixo, não a regra de cripto nacional.

**Ativos custodiados no exterior (ações, ETFs, fundos ou cripto mantidos fora do Brasil):**
- O Portfólio já identifica esse cenário: uma posição em conta de moeda diferente de `BRL` recebe `market_label = "Exterior"`. O módulo de IR reaproveita esse mesmo sinal (conta/carteira em moeda estrangeira) para separar a apuração — não introduz um novo campo de "país de custódia".
- **Ganho de capital na venda** de ativo custodiado no exterior não usa as isenções de R$ 20.000,00 (ações) nem R$ 35.000,00 (cripto nacional) — essas isenções são exclusivas de operações em mercado/exchange nacional. Segue a tabela progressiva geral de ganho de capital (15% a 22,5% conforme a faixa), apurada mensalmente e com DARF próprio, sem separação entre swing e day trade.
- Conversão para reais usa a cotação de venda do dólar (ou moeda correspondente) divulgada pelo Banco Central (PTAX) na data de cada operação de compra e de venda — nunca uma taxa única do ano.
- **Rendimentos recebidos no exterior** (dividendos, JCP, juros de ativos estrangeiros) seguem regra de apuração distinta da venda do ativo, com possibilidade de compensar o imposto retido na fonte no país de origem (ex.: withholding tax dos EUA) até o limite do imposto brasileiro devido sobre o mesmo rendimento, condicionada a reciprocidade de tratamento — o Brasil reconhece essa reciprocidade com os EUA.
- **Cautela:** a separação exata entre "ganho de capital na alienação de bem no exterior" e "rendimento de aplicação financeira no exterior" (regras diferentes desde a Lei 14.754/2023) tem zonas cinzentas entre fontes tributárias e não deve ser travada no código sem revisão de um contador — ver Pendências.

**Compensação de prejuízos:**
- Prejuízo apurado em um mês, numa classe/modalidade, é acumulado e abate o ganho tributável de meses seguintes da **mesma** classe/modalidade (ações comuns compensam apenas com ações comuns; day trade só compensa com day trade; criptoativos nacionais compensam entre si).
- O saldo de prejuízo a compensar não expira e é reduzido conforme utilizado.
- A compensação nunca gera saldo de imposto negativo nem restituição automática — apenas reduz a base de cálculo do mês corrente.

**DARF:**
- O sistema calcula (não emite nem transmite) o DARF: competência, classe, código de receita, base de cálculo, valor do imposto e vencimento no último dia útil do mês seguinte ao da apuração.
- O usuário registra manualmente o pagamento (data e valor efetivamente pago) para manter o histórico; o app não integra com sistemas de pagamento.
- Um DARF só é gerado quando há ganho tributável líquido positivo após isenção e compensação de prejuízo.

**Parametrização:**
- Percentuais de alíquota, limites de isenção e códigos de receita ficam armazenados em tabela própria e versionados por vigência, nunca fixos no código, para permitir atualização quando a legislação mudar sem exigir nova implantação de código para simples mudança de valor.

**Relatório anual (aba IRPF):**
- Bens e Direitos exibe as posições em aberto em 31/12 do ano-calendário pelo **custo de aquisição acumulado**, nunca pelo valor de mercado — mesma orientação já seguida implicitamente pelo Portfólio para posições abertas.
- Rendimentos Isentos e Não Tributáveis reúne vendas de ações dentro da faixa de isenção mensal, vendas de cripto dentro da faixa de isenção mensal, proventos de ações/FIIs e rendimento de poupança.
- Rendimentos Sujeitos a Tributação Exclusiva/Definitiva reúne o IR retido na fonte de renda fixa apurado pelo Portfólio.
- Renda Variável apresenta o resumo mês a mês usado na aba Apuração Mensal, incluindo prejuízos a compensar no encerramento do ano.
- O relatório é organizado para leitura/impressão, seguindo o mesmo padrão de layout denso e imprimível já usado nos demonstrativos de [[relatorios]], sem pretender ser um formulário oficial da Receita Federal.

## Dados

- `competencia`: mês de apuração no formato `AAAA-MM`, derivado da data do resgate/encerramento.
- `mercado`: `nacional` ou `exterior`, derivado da moeda da conta/carteira que custodia o ativo (mesmo sinal já usado pelo Portfólio para exibir `market_label`), não de um cadastro novo de país.
- `classe_apuracao`: `acoes_comuns`, `acoes_day_trade`, `fii`, `cripto_nacional`, `ativos_exterior` (as demais combinações, como rendimentos recebidos no exterior, ficam fora do escopo desta versão — ver Pendências).
- `base_calculo_cents`: ganho líquido do mês na classe, após isenção (quando aplicável) e antes da compensação de prejuízo.
- `prejuizo_compensado_cents` / `saldo_prejuizo_cents`: valores consumidos e saldo remanescente de prejuízo por classe.
- `imposto_devido_cents`: valor do DARF calculado para a competência/classe.
- `imposto_retido_exterior_cents`: valor de imposto retido na fonte no exterior sobre um mesmo evento, usado para compensação — depende de captura ainda não modelada (ver Pendências).
- `darf_pago`, `darf_pago_em`, `darf_valor_pago_cents`: controle manual de pagamento informado pelo usuário.

## API e dados

| Método | Rota |
|---|---|
| `GET` | `/api/ir/monthly?year=AAAA` |
| `GET` | `/api/ir/darfs?year=AAAA` |
| `PUT` | `/api/ir/darfs/{id}/payment` |
| `GET` | `/api/ir/annual-report?year=AAAA` |

Tabelas novas: `ir_tax_rules` (parâmetros de alíquota/isenção/código versionados por vigência), `ir_darf_payments` (controle manual de pagamento por competência/classe).

Tabelas lidas (somente leitura, sem duplicar dado): `investment_redemptions`, `investment_closed_positions`, `investment_operations`, `investment_opening_positions`, `checking_accounts`, `transactions`.

## Critérios de aceite

- Dado um mês com vendas de ações comuns somando até R$ 20.000,00 e ganho positivo, quando a apuração mensal é exibida, o resultado aparece como isento e nenhum DARF é gerado.
- Dado um mês com vendas de ações comuns somando acima de R$ 20.000,00 e ganho positivo, quando a apuração mensal é exibida, o sistema calcula 15% sobre o ganho e gera um DARF com código `6015`.
- Dado um resgate identificado como day trade no mesmo dia, quando apurado, o sistema aplica 20% sobre o ganho líquido do dia sem considerar a isenção de R$ 20.000,00.
- Dado um resgate de cota de FII com ganho, quando apurado, o sistema aplica 20% independentemente do valor total vendido no mês.
- Dado vendas de criptoativos nacionais somando até R$ 35.000,00 no mês, quando apurado, o resultado aparece como isento e nenhum DARF é gerado.
- Dado vendas de criptoativos nacionais somando acima de R$ 35.000,00 com ganho, quando apurado, o sistema calcula o imposto pela tabela progressiva de 15% a 22,5% e gera um DARF com código `4600`.
- Dado um prejuízo apurado em ações comuns em um mês, quando há ganho de ações comuns em mês posterior, então o prejuízo é abatido da base de cálculo antes de aplicar a alíquota, e o saldo de prejuízo remanescente é atualizado.
- Dado um prejuízo em day trade, quando há ganho em ações comuns (não day trade) no mesmo mês, então o prejuízo de day trade não reduz a base de cálculo das ações comuns.
- Dado um DARF calculado, quando o usuário registra data e valor de pagamento, então o registro passa a aparecer como pago no histórico e no relatório anual.
- Dado o relatório anual da aba IRPF gerado para um ano-calendário, quando exibido, as posições em aberto em 31/12 aparecem pelo custo de aquisição acumulado, nunca pelo valor de mercado do dia.
- Dado o relatório anual gerado, quando exibido, rendimentos isentos (vendas dentro da faixa de isenção, proventos e poupança) aparecem separados dos rendimentos sujeitos a tributação exclusiva de renda fixa.
- Dado dois usuários com posições distintas no Portfólio, quando cada um acessa o módulo IR, cada um vê apenas a apuração e os DARFs derivados das próprias operações.
- Dado um mês sem nenhum resgate ou encerramento de renda variável/cripto, quando a apuração mensal é exibida, o mês aparece sem movimentação e sem DARF, sem erro.
- Dado um resgate de ativo custodiado em conta de moeda estrangeira com ganho, quando apurado, o sistema aplica a tabela progressiva de ganho de capital sem considerar as isenções de R$ 20.000,00 ou R$ 35.000,00, mesmo que o total vendido no mês fique abaixo desses valores.
- Dado um resgate de ativo custodiado no Brasil e outro no exterior no mesmo mês e classe equivalente (ex.: ambos `stock`), quando apurados, o sistema mantém a compensação de prejuízo separada entre `mercado = nacional` e `mercado = exterior`.

## Pendências

> [!question] Pendências
> Toda pergunta em aberto, decisão não tomada ou premissa não validada entra aqui. Nenhum agente de IA deve implementar uma seção que dependa de um item desta lista sem confirmação humana antes.

- [ ] Confirmar se o módulo nasce como `financeiro/ir.py` novo (lendo `portfolio.py` apenas por função exportada) ou como submódulo dentro de `investimentos-portfolio` — decisão de organização de módulo único do AGENTS.md.
- [ ] Definir a estrutura da tabela `ir_tax_rules` (parâmetros versionados por vigência) — decisão técnica não trivial que deve virar ADR antes da implementação, conforme passo 4 do fluxo SDD.
- [ ] Confirmar a regra de detecção de day trade: o modelo atual de `investment_operations`/`investment_redemptions` não marca explicitamente compra e venda no mesmo dia; será necessário comparar datas de aporte e resgate do mesmo ativo, o que pode não cobrir todos os casos (ex.: múltiplas compras no mesmo dia com resgate parcial).
- [ ] Decidir se a classe "Ativos custodiados no exterior" (ações, ETFs e cripto fora do Brasil) entra nesta primeira versão ou fica explicitamente fora de escopo — o regime de apuração é bem diferente do nacional e a separação entre "ganho de capital na alienação de bem no exterior" e "rendimento de aplicação financeira no exterior" (Lei 14.754/2023) precisa ser validada com um contador antes de virar regra de código.
- [ ] Definir como capturar rendimentos recebidos no exterior (dividendos/JCP de ações e ETFs estrangeiros) vinculados ao ativo e ao imposto retido na fonte lá fora — hoje esses valores só existem como lançamento de receita categorizado (`Dividendos / JCP`), sem relação com `investment_operations`, com o país de origem nem com o valor retido, o que impede calcular a compensação de imposto pago no exterior.
- [ ] Confirmar se a compensação do imposto retido no exterior fica limitada ao imposto brasileiro devido sobre o mesmo rendimento (regra geral de reciprocidade) ou se depende de comprovante que o usuário precisa anexar/informar manualmente.
- [ ] Definir como tratar prejuízo acumulado anterior à adoção do sistema (saldo inicial de compensação informado manualmente pelo usuário) — hoje não há esse campo em nenhuma tabela existente.
- [ ] Definir o regime de tributação de previdência privada (progressivo ou regressivo) e onde esse dado seria cadastrado, já que não existe hoje em `investment_opening_positions`/`investment_operations`.
- [ ] Confirmar formato de exportação/impressão do relatório da aba IRPF — reaproveitar o padrão de impressão dos demonstrativos de [[relatorios]] ou gerar arquivo separado.
- [ ] Confirmar fonte e processo de atualização dos parâmetros de `ir_tax_rules` quando a legislação mudar (edição manual pelo usuário vs. atualização futura via app).

## Fora de escopo

- Emissão ou transmissão eletrônica de DARF (Sicalc) ou da própria Declaração de Ajuste Anual — o app apoia o cálculo, o usuário executa nos sistemas oficiais da Receita Federal.
- Apuração de IRPF sobre rendas fora do Portfólio (salário, aluguel, carnê-leão de outras naturezas).
- Integração com o extrato da B3/corretoras para conciliação automática de operações.

## Plano de implementação

- [ ] Passo 1 — Registrar ADR sobre a modelagem de `ir_tax_rules` (parâmetros versionados por vigência) em `docs/adr/`, resolvendo a pendência correspondente antes de codificar. Fecha: pré-requisito dos critérios 1, 2, 5, 6.
- [ ] Passo 2 — Criar tabelas `ir_tax_rules` e `ir_darf_payments` de forma idempotente em `financeiro/database.py`. Fecha: pré-requisito de todos os critérios.
- [ ] Passo 3 — Implementar `financeiro/ir.py` com a apuração mensal por classe, lendo `investment_redemptions`/`investment_closed_positions`/`investment_operations` somente leitura. Fecha: critérios 1, 2, 3, 4, 5, 6, 13.
- [ ] Passo 4 — Implementar compensação de prejuízo por classe/modalidade dentro de `financeiro/ir.py`, mantendo `mercado` (`nacional`/`exterior`) como parte da chave de compensação. Fecha: critérios 7, 8, 15.
- [ ] Passo 4a — Implementar apuração da classe `ativos_exterior` reaproveitando `market_label` do Portfólio (moeda da conta) para segregar eventos, sem isenção mensal. Fecha: critério 14. Bloqueado pela pendência de validação contábil da separação ganho de capital vs. rendimento de aplicação financeira no exterior.
- [ ] Passo 5 — Expor rotas `GET /api/ir/monthly`, `GET /api/ir/darfs`, `PUT /api/ir/darfs/{id}/payment` em `app.py`, validando propriedade do usuário. Fecha: critérios 9, 12.
- [ ] Passo 6 — Implementar `GET /api/ir/annual-report`, consolidando Bens e Direitos (custo de aquisição), rendimentos isentos e tributação exclusiva. Fecha: critérios 10, 11.
- [ ] Passo 7 — Criar módulo frontend `web/modules/ir-view.js` seguindo a fábrica `createXxxView`, com abas "Apuração Mensal" e "IRPF" e ação de impressão/exportação reaproveitando o padrão de [[relatorios]].
- [ ] Passo 8 — Cobrir cada critério de aceite com teste automatizado em `tests/`, sinalizando na spec qualquer critério que só possa ser verificado manualmente (ex.: impressão).

## Changelog

- `0.3` — 2026-07-27 — Spec marcada como `depreciado`: decisão de não implementar o módulo. Complexidade de manter regras fiscais atualizadas (especialmente ativos no exterior) não compensa o ganho para um sistema de uso familiar; alternativas especializadas (mycapital.com.br) já resolvem isso com integração direta à B3, fora do escopo deste app local sem dependências externas.
- `0.2` — 2026-07-27 — Adicionada a classe "Ativos custodiados no exterior" (ações, ETFs e cripto fora do Brasil, identificados pelo `market_label`/moeda da conta já usado no Portfólio): ganho de capital sem isenção mensal via tabela progressiva, e nota sobre compensação de imposto retido no exterior sobre rendimentos (dividendos/JCP), com pendências de captura de dado e validação contábil da separação legal entre ganho de capital e rendimento de aplicação financeira no exterior (Lei 14.754/2023).
- `0.1` — 2026-07-27 — Spec inicial em status `em-implementacao`: apuração mensal de DARF por classe de ativo (ações comuns, day trade, FIIs, criptoativos nacionais), compensação de prejuízos e relatório anual de apoio à declaração IRPF, ancorados nos dados já existentes de [[investimentos-portfolio]].

## Relacionados

- [[investimentos-portfolio]]
- [[relatorios]]
- [[lancamentos]]
- [[arquitetura]]
